"""
Overview: HTTP request node — makes external HTTP calls with expression-interpolated config.
Architecture: Integration node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine, httpx
Concepts: HTTP client, REST API calls, expression interpolation, response handling
"""

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

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
REQUEST_TIMEOUT = 30.0


class HttpRequestNodeExecutor(BaseNodeExecutor):
    """Makes an HTTP request with expression-interpolated URL, headers, and body."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        method = context.config.get("method", "GET").upper()
        url_template = context.config.get("url", "")
        headers_config: dict = context.config.get("headers", {})
        body_template = context.config.get("body", "")
        timeout = context.config.get("timeout", REQUEST_TIMEOUT)

        if method not in ALLOWED_METHODS:
            return NodeOutput(error=f"Invalid HTTP method: {method}")

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        url = interpolate_string(url_template, expr_ctx, BUILTIN_FUNCTIONS)
        headers = {
            k: interpolate_string(v, expr_ctx, BUILTIN_FUNCTIONS)
            for k, v in headers_config.items()
        }
        body = interpolate_string(body_template, expr_ctx, BUILTIN_FUNCTIONS) if body_template else None

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

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body.encode() if body else None,
                )

            try:
                response_body = response.json()
            except (json.JSONDecodeError, ValueError):
                response_body = response.text

            return NodeOutput(
                data={
                    "status_code": response.status_code,
                    "body": response_body,
                    "headers": dict(response.headers),
                },
                next_port="out",
            )
        except httpx.TimeoutException:
            return NodeOutput(error=f"HTTP request timed out after {timeout}s")
        except httpx.RequestError as e:
            return NodeOutput(error=f"HTTP request failed: {e}")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="http_request",
        label="HTTP Request",
        category=NodeCategory.INTEGRATION,
        description="Makes an HTTP request with configurable method, URL, headers, and body.",
        icon="&#127760;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": list(ALLOWED_METHODS),
                    "default": "GET",
                },
                "url": {"type": "string", "description": "URL with ${expression} interpolation"},
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "x-ui-widget": "key-value-map",
                },
                "body": {"type": "string", "description": "Request body with interpolation"},
                "timeout": {"type": "number", "default": 30.0},
            },
            "required": ["url"],
        },
        executor_class=HttpRequestNodeExecutor,
    ))
