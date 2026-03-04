"""
Overview: Stack reservation claim node — claims DR reservation capacity for failover.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: DR reservation, failover capacity, reservation claim
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


class StackReservationClaimNodeExecutor(BaseNodeExecutor):
    """Claims DR reservation capacity. STUBBED — Phase 12 wires in real reservation management."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        reservation_id = context.config.get("reservation_id", "")

        # Read DR config for reservation type, RPO/RTO targets
        stack_ctx = context.variables.get("stack_context", {})
        dr_config = stack_ctx.get("dr_config", {})
        rpo_target = dr_config.get("rpo_target_seconds")
        rto_target = dr_config.get("rto_target_seconds")
        reservation_type = dr_config.get("reservation_type")

        if not reservation_id:
            return NodeOutput(error="reservation_id is required")

        if context.is_test:
            return NodeOutput(
                data={
                    "reservation_id": reservation_id,
                    "status": "MOCK_SUCCESS",
                    "claim_id": "mock-claim-id",
                    "dr_config": dr_config,
                },
                next_port="out",
            )

        # STUB: Phase 12 will replace this with real reservation claim logic
        # DR config drives: reservation_type, rpo/rto targets, failover_priority
        logger.info(
            "Stack reservation claim STUB: reservation_id=%s, type=%s, rpo=%s, rto=%s",
            reservation_id, reservation_type, rpo_target, rto_target,
        )

        return NodeOutput(
            data={
                "reservation_id": reservation_id,
                "status": "STUBBED_PENDING_PHASE_12",
                "claim_id": "",
                "dr_config": dr_config,
                "message": "Stack reservation claim is stubbed. Phase 12 (Pulumi Integration) will provide real DR reservation management.",
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="stack_reservation_claim",
        label="Stack Reservation Claim",
        category=NodeCategory.DEPLOYMENT,
        description="Claim DR reservation capacity for failover.",
        icon="&#9888;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "DR reservation ID to claim"},
            },
            "required": ["reservation_id"],
        },
        executor_class=StackReservationClaimNodeExecutor,
    ))
