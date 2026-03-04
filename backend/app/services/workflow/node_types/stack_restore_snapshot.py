"""
Overview: Stack restore snapshot node — restores a stack from a previously taken snapshot.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack restore, snapshot recovery, cross-environment restore
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


class StackRestoreSnapshotNodeExecutor(BaseNodeExecutor):
    """Restores a stack from a snapshot. STUBBED — Phase 12 wires in real restore operations."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_instance_id = context.config.get("stack_instance_id", "")
        snapshot_id = context.config.get("snapshot_id", "")
        target_environment_id = context.config.get("target_environment_id", "")

        if not stack_instance_id:
            return NodeOutput(error="stack_instance_id is required")

        if not snapshot_id:
            return NodeOutput(error="snapshot_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_instance_id": stack_instance_id,
                    "snapshot_id": snapshot_id,
                    "target_environment_id": target_environment_id or stack_instance_id,
                    "status": "MOCK_SUCCESS",
                    "restored": True,
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real restore operations
        logger.info(
            "Stack restore snapshot STUB: stack_instance_id=%s, snapshot_id=%s, target_env=%s",
            stack_instance_id, snapshot_id, target_environment_id or "same",
        )

        return NodeOutput(
            data={
                "stack_instance_id": stack_instance_id,
                "snapshot_id": snapshot_id,
                "target_environment_id": target_environment_id,
                "status": "STUBBED_PENDING_PHASE_12",
                "restored": False,
                "message": "Stack restore snapshot is stubbed. Phase 12 (Pulumi Integration) will provide real restore operations.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_restore_snapshot",
        label="Stack Restore Snapshot",
        category=NodeCategory.DEPLOYMENT,
        description="Restore a stack from a previously taken snapshot.",
        icon="&#128260;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "stack_instance_id": {"type": "string", "description": "Stack instance ID to restore into"},
                "snapshot_id": {"type": "string", "description": "Snapshot ID to restore from"},
                "target_environment_id": {
                    "type": "string",
                    "description": "Optional target environment (defaults to original environment)",
                },
            },
            "required": ["stack_instance_id", "snapshot_id"],
        },
        executor_class=StackRestoreSnapshotNodeExecutor,
    ))
