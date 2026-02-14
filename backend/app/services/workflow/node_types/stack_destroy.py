"""
Overview: Stack destroy node — destroys stack resources (STUBBED for Phase 12 Pulumi integration).
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack teardown, Pulumi integration stub, reverse deployment order
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


class StackDestroyNodeExecutor(BaseNodeExecutor):
    """Destroys stack resources. STUBBED — Phase 12 wires in Pulumi Automation API."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_id = context.config.get("stack_id", "")
        topology_id = context.config.get("topology_id", "")

        if not stack_id:
            return NodeOutput(error="stack_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_id": stack_id,
                    "topology_id": topology_id,
                    "status": "MOCK_DESTROYED",
                    "resources_removed": 0,
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real Pulumi destroy operations
        logger.info(
            "Stack destroy STUB: stack_id=%s, topology_id=%s",
            stack_id, topology_id,
        )

        return NodeOutput(
            data={
                "stack_id": stack_id,
                "topology_id": topology_id,
                "status": "STUBBED_PENDING_PHASE_12",
                "resources_removed": 0,
                "message": "Stack destroy is stubbed. Phase 12 (Pulumi Integration) will provide real teardown.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_destroy",
        label="Stack Destroy",
        category=NodeCategory.DEPLOYMENT,
        description="Destroys stack resources via Pulumi (stubbed until Phase 12).",
        icon="&#128681;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "stack_id": {"type": "string", "description": "Stack node ID from the topology"},
                "topology_id": {"type": "string", "description": "Source topology ID"},
            },
            "required": ["stack_id"],
        },
        executor_class=StackDestroyNodeExecutor,
    ))
