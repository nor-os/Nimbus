"""
Overview: Cloud API node — makes authenticated HTTP calls to cloud backends.
Architecture: Integration node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine,
    app.services.cloud.backend_service, app.services.crypto.credential_encryption, httpx
Concepts: Cloud backend authentication, provider-specific auth headers, credential decryption
"""

from __future__ import annotations

import json
import logging

import httpx

from app.services.workflow.expression_engine import (
    ExpressionContext,
    interpolate_string,
)
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS
from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput

logger = logging.getLogger(__name__)

ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
DEFAULT_TIMEOUT = 30.0


class CloudApiNodeExecutor(BaseNodeExecutor):
    """Makes an authenticated HTTP call to a configured cloud backend."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        backend_id = context.config.get("backend_id", "")
        method = context.config.get("method", "GET").upper()
        path_template = context.config.get("path", "")
        query_params_config: dict = context.config.get("query_params", {})
        body_template = context.config.get("body", "")
        extra_headers_config: dict = context.config.get("extra_headers", {})
        timeout = context.config.get("timeout", DEFAULT_TIMEOUT)

        if method not in ALLOWED_METHODS:
            return NodeOutput(error=f"Invalid HTTP method: {method}")

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        # Interpolate expressions in config values
        backend_id = interpolate_string(str(backend_id), expr_ctx, BUILTIN_FUNCTIONS)
        path = interpolate_string(path_template, expr_ctx, BUILTIN_FUNCTIONS)
        query_params = {
            k: interpolate_string(str(v), expr_ctx, BUILTIN_FUNCTIONS)
            for k, v in query_params_config.items()
        }
        body = (
            interpolate_string(body_template, expr_ctx, BUILTIN_FUNCTIONS)
            if body_template
            else None
        )
        extra_headers = {
            k: interpolate_string(str(v), expr_ctx, BUILTIN_FUNCTIONS)
            for k, v in extra_headers_config.items()
        }

        if context.is_test:
            mock_response = (context.mock_config or {}).get("response", {})
            return NodeOutput(
                data={
                    "status_code": mock_response.get("status_code", 200),
                    "body": mock_response.get("body", {}),
                    "headers": mock_response.get("headers", {}),
                    "is_mock": True,
                },
                next_port="out",
            )

        # Resolve backend and build auth headers
        try:
            from sqlalchemy import select

            from app.db.session import async_session_factory
            from app.models.cloud_backend import CloudBackend
            from app.services.crypto.credential_encryption import decrypt_credentials

            async with async_session_factory() as db:
                stmt = select(CloudBackend).where(CloudBackend.id == backend_id)
                result = await db.execute(stmt)
                backend = result.scalar_one_or_none()

            if not backend:
                return NodeOutput(error=f"Cloud backend not found: {backend_id}")

            if not backend.credentials_encrypted:
                return NodeOutput(error=f"No credentials configured for backend: {backend.name}")

            credentials = decrypt_credentials(backend.credentials_encrypted)
            base_url = (backend.endpoint_url or "").rstrip("/")
            provider_name = backend.provider.name.lower() if backend.provider else ""

            auth_headers = _build_auth_headers(provider_name, credentials)
        except Exception as e:
            logger.exception("Failed to resolve cloud backend: %s", e)
            return NodeOutput(error=f"Backend resolution failed: {e}")

        # Build the full URL
        url = f"{base_url}/{path.lstrip('/')}" if path else base_url

        # Merge headers: auth first, then extra headers override
        headers = {**auth_headers, **extra_headers}

        try:
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params if query_params else None,
                    content=body.encode() if body else None,
                )

            try:
                response_body = response.json()
            except (json.JSONDecodeError, ValueError):
                response_body = response.text

            output_data = {
                "status_code": response.status_code,
                "body": response_body,
                "headers": dict(response.headers),
            }

            if response.status_code >= 400:
                return NodeOutput(
                    data=output_data,
                    next_port="error",
                    error=f"HTTP {response.status_code}: {response_body}",
                )

            return NodeOutput(data=output_data, next_port="out")

        except httpx.TimeoutException:
            return NodeOutput(error=f"Cloud API request timed out after {timeout}s")
        except httpx.RequestError as e:
            return NodeOutput(error=f"Cloud API request failed: {e}")


def _build_auth_headers(provider_name: str, credentials: dict) -> dict[str, str]:
    """Build provider-specific authentication headers from decrypted credentials."""
    if provider_name == "proxmox":
        # Proxmox VE API token auth: "PVEAPIToken=user@realm!tokenid=secret"
        token_id = credentials.get("token_id", "")
        secret = credentials.get("secret", "")
        if token_id and secret:
            return {"Authorization": f"PVEAPIToken={token_id}={secret}"}
        # Fall back to ticket-based auth if present
        ticket = credentials.get("ticket", "")
        if ticket:
            return {"Cookie": f"PVEAuthCookie={ticket}"}
        return {}

    if provider_name in ("azure", "gcp"):
        # Bearer token auth
        access_token = credentials.get("access_token", "")
        if access_token:
            return {"Authorization": f"Bearer {access_token}"}
        return {}

    if provider_name == "aws":
        # AWS SigV4 — stubbed for Phase 18
        # Real implementation needs request signing, not a static header
        logger.warning("AWS SigV4 signing not yet implemented — using static credentials header")
        return {}

    if provider_name == "oci":
        # OCI HTTP signature — stubbed for Phase 18
        # Real implementation needs per-request signing
        logger.warning("OCI HTTP signature signing not yet implemented — using static credentials")
        return {}

    # Unknown provider — try bearer token as generic fallback
    access_token = credentials.get("access_token", "")
    if access_token:
        return {"Authorization": f"Bearer {access_token}"}
    return {}


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="cloud_api",
        label="Cloud API",
        category=NodeCategory.INTEGRATION,
        description="Makes an authenticated HTTP call to a configured cloud backend.",
        icon="&#9729;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Success"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error (4xx/5xx)"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "backend_id": {
                    "type": "string",
                    "description": "UUID of the CloudBackend to authenticate against",
                    "x-ui-widget": "backend-picker",
                },
                "method": {
                    "type": "string",
                    "enum": list(ALLOWED_METHODS),
                    "default": "GET",
                },
                "path": {
                    "type": "string",
                    "description": "API path appended to backend endpoint URL",
                },
                "query_params": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "x-ui-widget": "key-value-map",
                    "description": "Query parameters (values support ${expression})",
                },
                "body": {
                    "type": "string",
                    "description": "JSON request body (supports ${expression})",
                    "x-ui-widget": "json-body",
                },
                "extra_headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "x-ui-widget": "key-value-map",
                    "description": "Additional headers merged after auth headers",
                },
                "timeout": {
                    "type": "number",
                    "default": 30,
                    "description": "Request timeout in seconds",
                },
            },
            "required": ["backend_id", "path"],
        },
        executor_class=CloudApiNodeExecutor,
    ))
