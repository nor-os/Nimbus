"""
Overview: Activity node — executes an automated activity within a workflow.
Architecture: Action node type for activity execution (Section 11.5)
Dependencies: app.services.workflow.node_types.base, app.services.automation
Concepts: Activity execution, parameter binding, version pinning, workflow integration
"""

from __future__ import annotations

from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput


class ActivityNodeExecutor(BaseNodeExecutor):
    """Executes an automated activity as a workflow node."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        activity_id = context.config.get("activity_id")
        version_id = context.config.get("version_id")
        deployment_id = context.config.get("deployment_id")
        ci_id = context.config.get("ci_id")

        # Slug fallback: resolve activity_slug → activity_id at runtime if unresolved
        if not activity_id:
            activity_slug = context.config.get("activity_slug")
            if activity_slug:
                try:
                    from app.db.session import async_session_factory
                    from app.models.automated_activity import AutomatedActivity
                    from sqlalchemy import select as sa_select

                    async with async_session_factory() as db:
                        result = await db.execute(
                            sa_select(AutomatedActivity).where(
                                AutomatedActivity.slug == activity_slug,
                                AutomatedActivity.is_system.is_(True),
                                AutomatedActivity.deleted_at.is_(None),
                            )
                        )
                        activity = result.scalar_one_or_none()
                        if activity:
                            activity_id = str(activity.id)
                except Exception:
                    pass

        if not activity_id:
            return NodeOutput(error="No activity_id configured", next_port="error")

        # Build input from parameter bindings
        bindings = context.config.get("parameter_bindings", {})
        input_data = {}
        for param_name, binding in bindings.items():
            if isinstance(binding, str) and binding.startswith("$"):
                # Expression reference — resolve from context
                ref = binding[1:]
                if ref.startswith("input."):
                    input_data[param_name] = context.workflow_input.get(ref[6:])
                elif ref.startswith("vars."):
                    input_data[param_name] = context.variables.get(ref[5:])
                elif "." in ref:
                    node_id, key = ref.split(".", 1)
                    node_out = context.node_outputs.get(node_id, {})
                    input_data[param_name] = node_out.get(key)
                else:
                    input_data[param_name] = context.variables.get(ref)
            else:
                input_data[param_name] = binding

        if context.is_test:
            # In test mode, return mock output
            mock = context.mock_config or {}
            return NodeOutput(
                data=mock.get("output", {"mock": True, "activity_id": activity_id}),
                next_port="out",
            )

        # Execute via execution service
        try:
            from app.db.session import async_session_factory
            from app.services.automation.execution_service import ExecutionService

            async with async_session_factory() as db:
                svc = ExecutionService(db)
                execution = await svc.start_execution(
                    tenant_id=context.tenant_id,
                    activity_id=activity_id,
                    version_id=version_id,
                    started_by="workflow",
                    input_data=input_data,
                    ci_id=ci_id,
                    deployment_id=deployment_id,
                    workflow_execution_id=context.execution_id,
                )
                await db.commit()

                from app.models.automated_activity import ActivityExecutionStatus

                if execution.status == ActivityExecutionStatus.SUCCEEDED:
                    return NodeOutput(
                        data={
                            "execution_id": str(execution.id),
                            "output": execution.output_snapshot or {},
                            **(execution.output_snapshot or {}),
                        },
                        next_port="out",
                    )
                else:
                    return NodeOutput(
                        data={"execution_id": str(execution.id), "error": execution.error},
                        error=execution.error,
                        next_port="error",
                    )
        except Exception as e:
            return NodeOutput(error=str(e), next_port="error")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="activity",
        label="Activity",
        category=NodeCategory.ACTION,
        description="Executes an automated activity from the catalog.",
        icon="&#9881;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Success"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
            PortDef("result", PortDirection.OUTPUT, PortType.DATA, "Result Data", required=False),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "string",
                    "x-ui-widget": "activity-selector",
                    "description": "Activity to execute (UUID, resolved at clone time)",
                },
                "activity_slug": {
                    "type": "string",
                    "description": "Activity slug for template-time reference (resolved to activity_id at clone time)",
                },
                "version_id": {
                    "type": "string",
                    "x-ui-widget": "version-selector",
                    "description": "Pin to specific version (empty = latest published)",
                },
                "deployment_id": {
                    "type": "string",
                    "description": "Deployment to apply config mutations to",
                },
                "ci_id": {
                    "type": "string",
                    "description": "Target configuration item",
                },
                "parameter_bindings": {
                    "type": "object",
                    "x-ui-widget": "parameter-bindings",
                    "description": "Map activity input parameters to workflow data",
                },
            },
            "required": ["activity_id"],
        },
        executor_class=ActivityNodeExecutor,
    ))
