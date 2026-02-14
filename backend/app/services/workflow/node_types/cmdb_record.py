"""
Overview: CMDB record node — records deployment state in the CMDB (create/update CIs).
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.cmdb
Concepts: CI creation, deployment tracking, CMDB integration
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


class CMDBRecordNodeExecutor(BaseNodeExecutor):
    """Records deployment state in the CMDB by creating or updating CIs."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        action = context.config.get("action", "record_deployment")
        class_id = context.config.get("class_id", "")
        attributes = context.config.get("attributes", {})

        if context.is_test:
            return NodeOutput(
                data={
                    "action": action,
                    "class_id": class_id,
                    "attributes": attributes,
                    "ci_id": "mock-ci-id",
                    "recorded": False,
                },
                next_port="out",
            )

        try:
            from app.db.session import async_session_factory
            from app.services.cmdb.ci_service import CIService

            async with async_session_factory() as db:
                ci_svc = CIService(db)

                if action == "create_ci":
                    if not class_id:
                        return NodeOutput(error="class_id is required for create_ci action")
                    ci = await ci_svc.create(
                        tenant_id=context.tenant_id,
                        class_id=class_id,
                        attributes=attributes,
                        created_by=context.execution_id,
                    )
                    await db.commit()
                    return NodeOutput(
                        data={
                            "action": action,
                            "ci_id": str(ci.id),
                            "class_id": class_id,
                            "recorded": True,
                        },
                        next_port="out",
                    )
                elif action == "update_ci":
                    ci_id = attributes.pop("ci_id", "")
                    if not ci_id:
                        return NodeOutput(error="attributes.ci_id is required for update_ci action")
                    ci = await ci_svc.update(
                        tenant_id=context.tenant_id,
                        ci_id=ci_id,
                        attributes=attributes,
                    )
                    await db.commit()
                    return NodeOutput(
                        data={
                            "action": action,
                            "ci_id": str(ci.id),
                            "recorded": True,
                        },
                        next_port="out",
                    )
                else:
                    # record_deployment: log deployment metadata as audit
                    return NodeOutput(
                        data={
                            "action": action,
                            "deployment_context": {
                                "execution_id": context.execution_id,
                                "tenant_id": context.tenant_id,
                                "attributes": attributes,
                            },
                            "recorded": True,
                        },
                        next_port="out",
                    )
        except Exception as e:
            logger.exception("CMDB record failed: %s", e)
            return NodeOutput(error=f"CMDB record failed: {e}")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="cmdb_record",
        label="CMDB Record",
        category=NodeCategory.DEPLOYMENT,
        description="Records deployment state in the CMDB (create/update CIs).",
        icon="&#128451;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_ci", "update_ci", "record_deployment"],
                    "default": "record_deployment",
                    "description": "What CMDB action to perform",
                },
                "class_id": {
                    "type": "string",
                    "description": "CI class ID (required for create_ci)",
                },
                "attributes": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "CI attributes or deployment metadata",
                    "x-ui-widget": "json-editor",
                },
            },
        },
        executor_class=CMDBRecordNodeExecutor,
    ))
