"""
Overview: HTTP request/response audit middleware for automatic API action logging.
Architecture: Middleware layer capturing request metadata for audit trail (Section 3.1, 8)
Dependencies: starlette, asyncio, app.services.audit.service, app.services.audit.taxonomy
Concepts: Request auditing, non-blocking logging, event taxonomy, actor type detection
"""

import asyncio
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.models.audit import AuditPriority

logger = logging.getLogger(__name__)

# In-memory TTL cache: {tenant_id: (config_dict, timestamp)}
_CONFIG_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
_CONFIG_TTL_SECONDS = 60

# Default config used when cache is empty and DB is unreachable
_DEFAULT_CONFIG = {
    "log_api_reads": False,
    "log_api_writes": True,
    "log_auth_events": True,
    "log_graphql": True,
    "log_errors": True,
}

# Paths to skip auditing (health checks, docs, static)
_SKIP_PATHS = {"/health", "/ready", "/live", "/docs", "/redoc", "/openapi.json"}

# Auth endpoint patterns -> specific event_type
_AUTH_EVENT_MAP: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/auth/login"): "auth.login",
    ("POST", "/api/v1/auth/logout"): "auth.logout",
    ("POST", "/api/v1/auth/refresh"): "auth.token.refresh",
    ("POST", "/api/v1/auth/revoke"): "auth.token.revoke",
    ("POST", "/api/v1/auth/register"): "user.create",
    ("POST", "/api/v1/auth/setup"): "user.create",
}


def _detect_event_type(method: str, path: str) -> str:
    """Detect a specific event_type from HTTP method + path, falling back to api.request."""
    key = (method, path.rstrip("/"))
    if key in _AUTH_EVENT_MAP:
        return _AUTH_EVENT_MAP[key]
    if path.startswith("/graphql"):
        return "api.graphql"
    return "api.request"


async def _get_logging_config(tenant_id: str) -> dict[str, Any]:
    """Get audit logging config with in-memory TTL cache."""
    now = time.monotonic()
    cached = _CONFIG_CACHE.get(tenant_id)
    if cached and (now - cached[1]) < _CONFIG_TTL_SECONDS:
        return cached[0]

    try:
        from app.db.session import async_session_factory
        from app.services.audit.logging_config import AuditLoggingConfigService

        async with async_session_factory() as db:
            service = AuditLoggingConfigService(db)
            config = await service.get_config(tenant_id)
            _CONFIG_CACHE[tenant_id] = (config, now)
            return config
    except Exception:
        logger.debug("Failed to load audit logging config for tenant %s, using defaults", tenant_id)
        return _DEFAULT_CONFIG


def _should_log(
    config: dict[str, Any],
    event_type: str,
    method: str,
    status_code: int,
) -> bool:
    """Determine whether to log this request based on tenant config."""
    is_error = status_code >= 400
    if is_error and config.get("log_errors", True):
        return True

    if event_type.startswith("auth."):
        return config.get("log_auth_events", True)

    if event_type == "api.graphql":
        return config.get("log_graphql", True)

    if event_type == "api.request":
        if method in ("GET", "HEAD", "OPTIONS"):
            return config.get("log_api_reads", False)
        return config.get("log_api_writes", True)

    return True


class AuditMiddleware(BaseHTTPMiddleware):
    """Captures request metadata and logs audit entries after response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip health and docs endpoints
        if path in _SKIP_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        # Extract request context
        tenant_id = getattr(request.state, "current_tenant_id", None)
        if not tenant_id:
            return response

        trace_id = getattr(request.state, "trace_id", None)
        actor_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        # Extract actor info from JWT payload if available
        actor_id = None
        actor_email = None
        actor_type = "ANONYMOUS"
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from app.services.auth.jwt import decode_token

                payload = decode_token(auth_header[7:])
                actor_id = payload.get("sub")
                actor_email = payload.get("email")
                actor_type = "USER"
        except Exception:
            pass

        event_type = _detect_event_type(request.method, path)

        # Failed login detection
        if event_type == "auth.login" and response.status_code >= 400:
            event_type = "auth.login.failed"

        # Check tenant logging config before firing audit log
        config = await _get_logging_config(tenant_id)
        if not _should_log(config, event_type, request.method, response.status_code):
            return response

        priority = AuditPriority.INFO
        if response.status_code >= 500:
            priority = AuditPriority.ERR
        elif response.status_code >= 400:
            priority = AuditPriority.WARN

        # Fire-and-forget audit log
        asyncio.create_task(
            _log_request(
                tenant_id=tenant_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_email=actor_email,
                actor_ip=actor_ip,
                trace_id=trace_id,
                priority=priority,
                user_agent=user_agent,
                request_method=request.method,
                request_path=path,
                response_status=response.status_code,
                metadata={
                    "duration_ms": round(duration_ms, 2),
                    "query_params": str(request.query_params) if request.query_params else None,
                },
            )
        )

        return response


async def _log_request(
    *,
    tenant_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    actor_email: str | None,
    actor_ip: str | None,
    trace_id: str | None,
    priority: AuditPriority,
    user_agent: str | None,
    request_method: str,
    request_path: str,
    response_status: int,
    metadata: dict | None,
) -> None:
    """Background task to write request audit log entry."""
    try:
        from app.db.session import async_session_factory
        from app.services.audit.service import AuditService

        async with async_session_factory() as db:
            service = AuditService(db)
            await service.log(
                tenant_id=tenant_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_email=actor_email,
                actor_ip=actor_ip,
                trace_id=trace_id,
                priority=priority,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                response_status=response_status,
                metadata=metadata,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to write request audit log")
