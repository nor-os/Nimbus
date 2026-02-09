"""
Overview: Notification node — sends notifications via the Phase 9 NotificationService.
Architecture: Integration node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Notification dispatch, template rendering, channel selection
"""

from __future__ import annotations

import logging

from app.services.workflow.expression_engine import (
    ExpressionContext,
    interpolate_string,
)
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS
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


class NotificationNodeExecutor(BaseNodeExecutor):
    """Sends a notification via the notification system."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        channel = context.config.get("channel", "in_app")
        title_template = context.config.get("title", "Workflow Notification")
        body_template = context.config.get("body", "")
        recipient_ids: list[str] = context.config.get("recipient_ids", [])
        recipient_role_names: list[str] = context.config.get("recipient_role_names", [])

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        title = interpolate_string(title_template, expr_ctx, BUILTIN_FUNCTIONS)
        body = interpolate_string(body_template, expr_ctx, BUILTIN_FUNCTIONS)

        if context.is_test:
            return NodeOutput(
                data={
                    "notification": {
                        "channel": channel,
                        "title": title,
                        "body": body,
                        "recipient_ids": recipient_ids,
                        "recipient_role_names": recipient_role_names,
                        "tenant_id": context.tenant_id,
                    },
                    "sent": False,
                },
                next_port="out",
            )

        # Live mode: resolve roles to user IDs and send via NotificationService
        try:
            from app.db.session import async_session_factory
            from app.models.notification import NotificationCategory
            from app.models.role import Role
            from app.models.user_role import UserRole
            from app.services.notification.service import NotificationService

            from sqlalchemy import select

            async with async_session_factory() as db:
                all_user_ids = list(recipient_ids)

                # Resolve role names to user IDs
                if recipient_role_names:
                    stmt = (
                        select(UserRole.user_id)
                        .join(Role, UserRole.role_id == Role.id)
                        .where(
                            Role.name.in_(recipient_role_names),
                            Role.tenant_id == context.tenant_id,
                        )
                    )
                    result = await db.execute(stmt)
                    role_user_ids = [str(row[0]) for row in result.all()]
                    all_user_ids.extend(role_user_ids)

                # Deduplicate
                all_user_ids = list(dict.fromkeys(all_user_ids))

                if all_user_ids:
                    service = NotificationService(db)
                    stats = await service.send(
                        tenant_id=context.tenant_id,
                        user_ids=all_user_ids,
                        category=NotificationCategory.WORKFLOW,
                        event_type="workflow.notification",
                        title=title,
                        body=body,
                        related_resource_type="workflow_execution",
                        related_resource_id=context.execution_id,
                    )
                    await db.commit()
                else:
                    stats = {"in_app": 0, "email": 0, "webhook": 0}

            return NodeOutput(
                data={
                    "notification": {
                        "channel": channel,
                        "title": title,
                        "body": body,
                        "recipient_count": len(all_user_ids),
                        "tenant_id": context.tenant_id,
                    },
                    "sent": True,
                    "stats": stats,
                },
                next_port="out",
            )
        except Exception as e:
            logger.exception("Notification node failed: %s", e)
            return NodeOutput(error=f"Notification failed: {e}")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="notification",
        label="Notification",
        category=NodeCategory.INTEGRATION,
        description="Sends a notification via the configured channel.",
        icon="&#128276;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "enum": ["in_app", "email", "webhook"],
                    "default": "in_app",
                },
                "title": {"type": "string"},
                "body": {"type": "string"},
                "recipient_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-ui-widget": "string-list",
                },
                "recipient_role_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-ui-widget": "string-list",
                },
            },
        },
        executor_class=NotificationNodeExecutor,
    ))
