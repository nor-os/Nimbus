"""
Overview: Stack health check node — performs health check on one or all components in a stack instance.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack health monitoring, component health, multi-port branching
"""

from __future__ import annotations

import logging

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


class StackHealthCheckNodeExecutor(BaseNodeExecutor):
    """Health check on stack components. STUBBED — Phase 12 wires in real health probes."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_instance_id = context.config.get("stack_instance_id", "")
        node_id = context.config.get("node_id", "")
        timeout_seconds = context.config.get("timeout_seconds", 30)

        # Read HA config for check intervals and thresholds
        stack_ctx = context.variables.get("stack_context", {})
        ha_config = stack_ctx.get("ha_config", {})
        health_check_interval = ha_config.get("health_check_interval_seconds", timeout_seconds)
        health_probe_interval = ha_config.get("health_probe_interval_seconds", timeout_seconds)
        effective_timeout = min(health_check_interval, health_probe_interval, timeout_seconds)

        if not stack_instance_id:
            return NodeOutput(error="stack_instance_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_instance_id": stack_instance_id,
                    "node_id": node_id or "ALL",
                    "timeout_seconds": effective_timeout,
                    "status": "MOCK_SUCCESS",
                    "health": "healthy",
                    "ha_config": ha_config,
                    "components": {},
                },
                next_port="healthy",
            )

        # STUB: Phase 12 will replace this with real health checks
        # HA config drives: health_check_interval, quorum_size, health_probe_interval
        logger.info(
            "Stack health check STUB: stack_instance_id=%s, node_id=%s, timeout=%ds (ha-driven)",
            stack_instance_id, node_id or "ALL", effective_timeout,
        )

        return NodeOutput(
            data={
                "stack_instance_id": stack_instance_id,
                "node_id": node_id or "ALL",
                "timeout_seconds": effective_timeout,
                "status": "STUBBED_PENDING_PHASE_12",
                "health": "healthy",
                "ha_config": ha_config,
                "components": {},
                "message": "Stack health check is stubbed. Phase 12 (Pulumi Integration) will provide real health probes.",
            },
            next_port="healthy",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_health_check",
        label="Stack Health Check",
        category=NodeCategory.DEPLOYMENT,
        description="Health check on one or all components in a stack instance.",
        icon="&#9829;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("healthy", PortDirection.OUTPUT, PortType.FLOW, "Healthy"),
            PortDef("degraded", PortDirection.OUTPUT, PortType.FLOW, "Degraded"),
            PortDef("unhealthy", PortDirection.OUTPUT, PortType.FLOW, "Unhealthy"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "stack_instance_id": {"type": "string", "description": "Stack instance ID to check"},
                "node_id": {
                    "type": "string",
                    "description": "Specific component node ID (omit to check all components)",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 30,
                    "description": "Health check timeout in seconds",
                },
            },
            "required": ["stack_instance_id"],
        },
        executor_class=StackHealthCheckNodeExecutor,
    ))
