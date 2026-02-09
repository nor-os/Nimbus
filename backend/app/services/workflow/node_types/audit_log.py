"""
Overview: Audit log node — creates a custom audit entry in the audit system.
Architecture: Integration node type using Phase 4 audit system (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Custom audit entries, audit trail, workflow action logging
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


class AuditLogNodeExecutor(BaseNodeExecutor):
    """Creates a custom audit log entry."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        action_template = context.config.get("action", "workflow.custom_action")
        resource_type = context.config.get("resource_type", "workflow")
        details_config: dict = context.config.get("details", {})
        priority_str = context.config.get("priority", "INFO")

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        action = interpolate_string(action_template, expr_ctx, BUILTIN_FUNCTIONS)
        details: dict = {}
        for key, value_template in details_config.items():
            if isinstance(value_template, str):
                details[key] = interpolate_string(value_template, expr_ctx, BUILTIN_FUNCTIONS)
            else:
                details[key] = value_template

        if context.is_test:
            return NodeOutput(
                data={
                    "audit_entry": {
                        "action": action,
                        "resource_type": resource_type,
                        "details": details,
                        "priority": priority_str,
                        "tenant_id": context.tenant_id,
                        "execution_id": context.execution_id,
                    },
                    "logged": False,
                },
                next_port="out",
            )

        # Live mode: write to real audit service
        try:
            from app.db.session import async_session_factory
            from app.models.audit import ActorType, AuditPriority
            from app.services.audit.service import AuditService

            priority = AuditPriority(priority_str) if priority_str in AuditPriority.__members__ else AuditPriority.INFO

            async with async_session_factory() as db:
                audit = AuditService(db)
                await audit.log(
                    tenant_id=context.tenant_id,
                    event_type=action,
                    actor_type=ActorType.SYSTEM,
                    resource_type=resource_type,
                    resource_id=context.execution_id,
                    new_values=details,
                    priority=priority,
                    metadata={
                        "workflow_execution_id": context.execution_id,
                        "node_id": context.node_id,
                    },
                )
                await db.commit()

            return NodeOutput(
                data={
                    "audit_entry": {
                        "action": action,
                        "resource_type": resource_type,
                        "details": details,
                        "priority": priority_str,
                        "tenant_id": context.tenant_id,
                        "execution_id": context.execution_id,
                    },
                    "logged": True,
                },
                next_port="out",
            )
        except Exception as e:
            logger.exception("Audit log node failed: %s", e)
            return NodeOutput(error=f"Audit log failed: {e}")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="audit_log",
        label="Audit Log",
        category=NodeCategory.ACTION,
        description="Creates a custom audit log entry.",
        icon="&#128203;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Audit action name"},
                "resource_type": {"type": "string", "default": "workflow"},
                "details": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "x-ui-widget": "key-value-map",
                },
                "priority": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARN", "ERR", "CRITICAL"],
                    "default": "INFO",
                    "description": "Audit priority level",
                },
            },
            "required": ["action"],
        },
        executor_class=AuditLogNodeExecutor,
    ))
