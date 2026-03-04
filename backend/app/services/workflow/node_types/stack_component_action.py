"""
Overview: Stack component action node — executes an operation on a specific stack component by node_id.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack component operations, node-level actions, Pulumi integration stub
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


class StackComponentActionNodeExecutor(BaseNodeExecutor):
    """Executes an operation on a specific stack component. STUBBED — Phase 12 wires in real operations."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_instance_id = context.config.get("stack_instance_id", "")
        node_id = context.config.get("node_id", "")
        operation = context.config.get("operation", "")
        parameters = context.config.get("parameters", {})

        if not stack_instance_id:
            return NodeOutput(error="stack_instance_id is required")

        if not node_id:
            return NodeOutput(error="node_id is required")

        if not operation:
            return NodeOutput(error="operation is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_instance_id": stack_instance_id,
                    "node_id": node_id,
                    "operation": operation,
                    "parameters": parameters,
                    "status": "MOCK_SUCCESS",
                    "result": {},
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real component operations
        logger.info(
            "Stack component action STUB: stack_instance_id=%s, node_id=%s, operation=%s",
            stack_instance_id, node_id, operation,
        )

        return NodeOutput(
            data={
                "stack_instance_id": stack_instance_id,
                "node_id": node_id,
                "operation": operation,
                "parameters": parameters,
                "status": "STUBBED_PENDING_PHASE_12",
                "result": {},
                "message": "Stack component action is stubbed. Phase 12 (Pulumi Integration) will provide real operations.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_component_action",
        label="Stack Component Action",
        category=NodeCategory.DEPLOYMENT,
        description="Execute operation on a specific stack component by node_id.",
        icon="&#9881;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "stack_instance_id": {"type": "string", "description": "Stack instance ID to target"},
                "node_id": {"type": "string", "description": "Component node ID within the stack"},
                "operation": {"type": "string", "description": "Operation to execute (e.g. restart, scale, update)"},
                "parameters": {
                    "type": "object",
                    "default": {},
                    "description": "Operation-specific parameters",
                },
            },
            "required": ["stack_instance_id", "node_id", "operation"],
        },
        executor_class=StackComponentActionNodeExecutor,
    ))
