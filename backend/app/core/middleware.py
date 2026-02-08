"""
Overview: Request middleware for trace ID injection, security headers, and tenant context.
Architecture: Middleware layer in request pipeline (Section 3.1, 5.5)
Dependencies: fastapi, uuid, app.core.tenant_context
Concepts: Observability, trace correlation, security headers, tenant context propagation
"""

import uuid

from jose import JWTError

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.tenant_context import clear_tenant_context, set_current_tenant_id


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique trace ID into every request/response for log correlation."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extracts current_tenant_id from JWT and sets it in request state + contextvar."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from app.services.auth.jwt import decode_token

                try:
                    payload = decode_token(auth_header[7:])
                    tenant_id = payload.get("current_tenant_id")
                    if tenant_id:
                        set_current_tenant_id(tenant_id)
                        request.state.current_tenant_id = tenant_id
                        request.state.tenant_ids = payload.get("tenant_ids", [])
                except (JWTError, ValueError):
                    pass

            response = await call_next(request)
            return response
        finally:
            clear_tenant_context()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
