"""
Overview: EventTrigger node — starts a workflow when a matching event fires.
Architecture: Integration node type for event-driven workflows (Section 11.6)
Dependencies: app.services.workflow.node_types.base, app.services.events
Concepts: Event-driven workflows, auto-subscription, reactive execution
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


class EventTriggerNodeExecutor(BaseNodeExecutor):
    """Receives event payload as workflow input and passes it to the output port.

    When a workflow containing this node is published, a DB subscription
    (handler_type=WORKFLOW) is auto-created. When the workflow is archived
    or deleted, the subscription is removed.
    """

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        # The event payload is injected as workflow_input by the event handler
        event_data = context.workflow_input or {}

        return NodeOutput(
            data={
                "event_type": context.config.get("event_type_name", ""),
                "payload": event_data,
                **event_data,
            },
            next_port="out",
        )


async def on_workflow_publish(
    definition_id: str, tenant_id: str, nodes: list[dict],
) -> None:
    """Auto-create event subscriptions for EventTrigger nodes in the workflow."""
    for node in nodes:
        if node.get("type") != "event_trigger":
            continue

        config = node.get("config", {})
        event_type_name = config.get("event_type_name")
        filter_expr = config.get("filter_expression")

        if not event_type_name:
            continue

        try:
            from app.db.session import async_session_factory
            from app.services.events.event_service import EventService

            async with async_session_factory() as db:
                svc = EventService(db)

                # Find the event type
                types = await svc.list_event_types(tenant_id=tenant_id)
                event_type = next(
                    (et for et in types if et.name == event_type_name), None
                )
                if not event_type:
                    continue

                # Create subscription
                await svc.create_subscription(tenant_id, {
                    "event_type_id": str(event_type.id),
                    "name": f"Workflow trigger: {definition_id} (node {node.get('id', 'unknown')})",
                    "handler_type": "WORKFLOW",
                    "handler_config": {"workflow_definition_id": definition_id},
                    "filter_expression": filter_expr,
                    "priority": 50,
                    "is_active": True,
                })
                await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "Failed to create event subscription for workflow %s: %s",
                definition_id, e,
            )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="event_trigger",
        label="Event Trigger",
        category=NodeCategory.INTEGRATION,
        description="Starts workflow execution when a matching event fires.",
        icon="&#9889;",
        ports=[
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("event", PortDirection.OUTPUT, PortType.DATA, "Event Data", required=False),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "event_type_name": {
                    "type": "string",
                    "x-ui-widget": "event-type-selector",
                    "description": "Event type to listen for",
                },
                "filter_expression": {
                    "type": "string",
                    "x-ui-widget": "expression-editor",
                    "description": "Optional filter (e.g., payload.status == 'DEPLOYED')",
                },
            },
            "required": ["event_type_name"],
        },
        executor_class=EventTriggerNodeExecutor,
    ))
