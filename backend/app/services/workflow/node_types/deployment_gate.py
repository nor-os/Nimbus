"""
Overview: Deployment gate node — deployment-specific approval gate with deployment context.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Deployment approval, preview confirmation, deployment-scoped gating
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


class DeploymentGateNodeExecutor(BaseNodeExecutor):
    """Deployment-specific approval gate with deployment context in title/description."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        title = context.config.get("title", "Deployment Approval Required")
        description = context.config.get("description", "")
        deployment_context = context.config.get("deployment_context", "")
        require_preview_confirmation = context.config.get("require_preview_confirmation", False)
        approver_role_names: list[str] = context.config.get("approver_role_names", [])
        approver_user_ids: list[str] = context.config.get("approver_user_ids", [])
        chain_mode = context.config.get("chain_mode", "SEQUENTIAL")
        timeout_minutes = context.config.get("timeout_minutes", 1440)

        # Enrich title/description with deployment context
        full_title = f"[Deployment] {title}"
        full_description = description
        if deployment_context:
            full_description = f"{description}\n\nDeployment Context: {deployment_context}".strip()
        if require_preview_confirmation:
            full_description += "\n\nNote: Preview confirmation is required before approval."

        if context.is_test:
            mock_decision = (context.mock_config or {}).get("decision", "approve")
            approved = mock_decision == "approve"
            return NodeOutput(
                data={
                    "approved": approved,
                    "decision": mock_decision,
                    "deployment_context": deployment_context,
                    "is_mock": True,
                },
                next_port="approved" if approved else "rejected",
            )

        return NodeOutput(
            data={
                "approval_config": {
                    "title": full_title,
                    "description": full_description,
                    "approver_role_names": approver_role_names,
                    "approver_user_ids": approver_user_ids,
                    "chain_mode": chain_mode,
                    "timeout_minutes": timeout_minutes,
                    "deployment_context": deployment_context,
                    "require_preview_confirmation": require_preview_confirmation,
                },
                "input": context.input_data,
            },
            next_port="pending",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="deployment_gate",
        label="Deployment Gate",
        category=NodeCategory.DEPLOYMENT,
        description="Deployment-specific approval gate with deployment context.",
        icon="&#128737;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("approved", PortDirection.OUTPUT, PortType.FLOW, "Approved"),
            PortDef("rejected", PortDirection.OUTPUT, PortType.FLOW, "Rejected"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "default": "Deployment Approval Required"},
                "description": {"type": "string"},
                "deployment_context": {
                    "type": "string",
                    "description": "Deployment context info shown to approvers",
                },
                "require_preview_confirmation": {
                    "type": "boolean",
                    "default": False,
                    "description": "Require approvers to confirm deployment preview",
                },
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
                "chain_mode": {
                    "type": "string",
                    "enum": ["SEQUENTIAL", "PARALLEL", "QUORUM"],
                    "default": "SEQUENTIAL",
                },
                "timeout_minutes": {"type": "integer", "minimum": 1, "default": 1440},
            },
        },
        executor_class=DeploymentGateNodeExecutor,
    ))
