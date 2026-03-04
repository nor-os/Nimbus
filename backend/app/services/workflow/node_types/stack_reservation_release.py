"""
Overview: Stack reservation release node — releases a claimed DR reservation.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: DR reservation, failover capacity, reservation release
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


class StackReservationReleaseNodeExecutor(BaseNodeExecutor):
    """Releases a claimed DR reservation. STUBBED — Phase 12 wires in real reservation management."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        reservation_id = context.config.get("reservation_id", "")

        if not reservation_id:
            return NodeOutput(error="reservation_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "reservation_id": reservation_id,
                    "status": "MOCK_SUCCESS",
                    "released": True,
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real reservation release logic
        logger.info(
            "Stack reservation release STUB: reservation_id=%s",
            reservation_id,
        )

        return NodeOutput(
            data={
                "reservation_id": reservation_id,
                "status": "STUBBED_PENDING_PHASE_12",
                "released": False,
                "message": "Stack reservation release is stubbed. Phase 12 (Pulumi Integration) will provide real DR reservation management.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_reservation_release",
        label="Stack Reservation Release",
        category=NodeCategory.DEPLOYMENT,
        description="Release a claimed DR reservation.",
        icon="&#9989;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "DR reservation ID to release"},
            },
            "required": ["reservation_id"],
        },
        executor_class=StackReservationReleaseNodeExecutor,
    ))
