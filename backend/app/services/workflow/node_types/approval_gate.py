"""
Overview: Approval gate node — creates an ApprovalChainWorkflow and blocks until decision.
Architecture: Integration node type using Phase 10 approval system (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Approval gate, blocking approval, Phase 10 integration
"""

from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput


class ApprovalGateNodeExecutor(BaseNodeExecutor):
    """Creates an approval request and blocks until approved/rejected.
    The DynamicWorkflowExecutor starts the ApprovalChainWorkflow as a child workflow."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        title = context.config.get("title", "Workflow Approval Required")
        description = context.config.get("description", "")
        approver_role_names: list[str] = context.config.get("approver_role_names", [])
        approver_user_ids: list[str] = context.config.get("approver_user_ids", [])
        chain_mode = context.config.get("chain_mode", "SEQUENTIAL")
        timeout_minutes = context.config.get("timeout_minutes", 1440)

        if context.is_test:
            mock_decision = (context.mock_config or {}).get("decision", "approve")
            approved = mock_decision == "approve"
            return NodeOutput(
                data={
                    "approved": approved,
                    "decision": mock_decision,
                    "is_mock": True,
                },
                next_port="approved" if approved else "rejected",
            )

        return NodeOutput(
            data={
                "approval_config": {
                    "title": title,
                    "description": description,
                    "approver_role_names": approver_role_names,
                    "approver_user_ids": approver_user_ids,
                    "chain_mode": chain_mode,
                    "timeout_minutes": timeout_minutes,
                },
                "input": context.input_data,
            },
            next_port="pending",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="approval_gate",
        label="Approval Gate",
        category=NodeCategory.INTEGRATION,
        description="Blocks until an approval chain completes.",
        icon="&#9745;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("approved", PortDirection.OUTPUT, PortType.FLOW, "Approved"),
            PortDef("rejected", PortDirection.OUTPUT, PortType.FLOW, "Rejected"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "approver_role_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-ui-widget": "string-list",
                },
                "approver_user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-ui-widget": "string-list",
                },
                "chain_mode": {"type": "string", "enum": ["SEQUENTIAL", "PARALLEL", "QUORUM"]},
                "timeout_minutes": {"type": "integer", "minimum": 1},
            },
        },
        executor_class=ApprovalGateNodeExecutor,
    ))
