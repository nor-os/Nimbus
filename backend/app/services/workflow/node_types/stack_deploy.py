"""
Overview: Stack deploy node — deploys a single stack (STUBBED for Phase 12 Pulumi integration).
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack deployment, Pulumi integration stub, preview mode
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


class StackDeployNodeExecutor(BaseNodeExecutor):
    """Deploys a single stack. STUBBED — Phase 12 wires in Pulumi Automation API."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_id = context.config.get("stack_id", "")
        topology_id = context.config.get("topology_id", "")
        preview_only = context.config.get("preview_only", False)

        if not stack_id:
            return NodeOutput(error="stack_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_id": stack_id,
                    "topology_id": topology_id,
                    "status": "MOCK_SUCCESS",
                    "preview_only": preview_only,
                    "outputs": {},
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real Pulumi stack operations
        logger.info(
            "Stack deploy STUB: stack_id=%s, topology_id=%s, preview_only=%s",
            stack_id, topology_id, preview_only,
        )

        return NodeOutput(
            data={
                "stack_id": stack_id,
                "topology_id": topology_id,
                "status": "STUBBED_PENDING_PHASE_12",
                "preview_only": preview_only,
                "outputs": {},
                "message": "Stack deployment is stubbed. Phase 12 (Pulumi Integration) will provide real provisioning.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_deploy",
        label="Stack Deploy",
        category=NodeCategory.DEPLOYMENT,
        description="Deploys a single stack via Pulumi (stubbed until Phase 12).",
        icon="&#128640;",
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
                "preview_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, only preview changes without applying",
                },
            },
            "required": ["stack_id"],
        },
        executor_class=StackDeployNodeExecutor,
    ))
