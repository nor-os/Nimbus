"""
Overview: Stack snapshot node — snapshots entire stack state for backup or migration.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Stack snapshots, state backup, migration preparation
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


class StackSnapshotNodeExecutor(BaseNodeExecutor):
    """Snapshots entire stack state. STUBBED — Phase 12 wires in real snapshot operations."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        stack_instance_id = context.config.get("stack_instance_id", "")
        snapshot_label = context.config.get("snapshot_label", "")
        include_data = context.config.get("include_data", False)

        # Read DR config for backup frequency, retention, PITR settings
        stack_ctx = context.variables.get("stack_context", {})
        dr_config = stack_ctx.get("dr_config", {})
        backup_frequency = dr_config.get("backup_frequency_hours")
        pitr_retention = dr_config.get("pitr_retention_days")

        if not stack_instance_id:
            return NodeOutput(error="stack_instance_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "stack_instance_id": stack_instance_id,
                    "snapshot_label": snapshot_label,
                    "include_data": include_data,
                    "status": "MOCK_SUCCESS",
                    "snapshot_id": "mock-snapshot-id",
                    "dr_config": dr_config,
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real snapshot operations
        # DR config drives: backup_frequency, pitr_retention, replication_mode
        logger.info(
            "Stack snapshot STUB: stack_instance_id=%s, label=%s, include_data=%s, backup_freq=%s",
            stack_instance_id, snapshot_label, include_data, backup_frequency,
        )

        return NodeOutput(
            data={
                "stack_instance_id": stack_instance_id,
                "snapshot_label": snapshot_label,
                "include_data": include_data,
                "status": "STUBBED_PENDING_PHASE_12",
                "snapshot_id": "",
                "dr_config": dr_config,
                "message": "Stack snapshot is stubbed. Phase 12 (Pulumi Integration) will provide real snapshot operations.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_snapshot",
        label="Stack Snapshot",
        category=NodeCategory.DEPLOYMENT,
        description="Snapshot entire stack state for backup or migration.",
        icon="&#128247;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "stack_instance_id": {"type": "string", "description": "Stack instance ID to snapshot"},
                "snapshot_label": {
                    "type": "string",
                    "description": "Optional human-readable label for the snapshot",
                },
                "include_data": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include application data in addition to infrastructure state",
                },
            },
            "required": ["stack_instance_id"],
        },
        executor_class=StackSnapshotNodeExecutor,
    ))
