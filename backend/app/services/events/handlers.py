"""
Overview: Handler dispatchers — routes event deliveries to workflows, activities, notifications, webhooks.
Architecture: Handler dispatch layer for event subscriptions (Section 11.6)
Dependencies: app.services.events.event_bus, app.models.event
Concepts: Handler dispatch, workflow trigger, activity execution, webhook delivery
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.event import EventDelivery, EventLog, EventSubscription

logger = logging.getLogger(__name__)


async def dispatch(
    subscription: EventSubscription,
    event_log: EventLog,
    delivery: EventDelivery,
) -> dict[str, Any]:
    """Route a delivery to the appropriate handler based on handler_type."""
    handler_type = subscription.handler_type
    config = subscription.handler_config or {}

    try:
        if handler_type == "INTERNAL":
            return await _handle_internal(config, event_log)
        elif handler_type == "WORKFLOW":
            return await _handle_workflow(config, event_log)
        elif handler_type == "NOTIFICATION":
            return await _handle_notification(config, event_log)
        elif handler_type == "ACTIVITY":
            return await _handle_activity(config, event_log)
        elif handler_type == "WEBHOOK":
            return await _handle_webhook(config, event_log)
        else:
            return {"error": f"Unknown handler type: {handler_type}"}
    except Exception as e:
        logger.error("Handler dispatch failed for %s: %s", handler_type, e)
        return {"error": str(e)}


async def _handle_internal(
    config: dict[str, Any], event_log: EventLog
) -> dict[str, Any]:
    """Import and call a Python function from handler_config['function']."""
    func_path = config.get("function", "")
    if not func_path:
        return {"error": "No function path configured"}

    try:
        module_path, func_name = func_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        result = await func(event_log.payload, event_log)
        return {"result": result}
    except Exception as e:
        return {"error": f"Internal handler error: {e}"}


async def _handle_workflow(
    config: dict[str, Any], event_log: EventLog
) -> dict[str, Any]:
    """Start a workflow execution via WorkflowExecutionService."""
    definition_id = config.get("workflow_definition_id")
    if not definition_id:
        return {"error": "No workflow_definition_id configured"}

    try:
        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            execution = await svc.start(
                tenant_id=str(event_log.tenant_id),
                definition_id=definition_id,
                input_data=event_log.payload,
                started_by=str(event_log.emitted_by) if event_log.emitted_by else "event_system",
            )
            await db.commit()
            return {"workflow_execution_id": str(execution.id)}
    except Exception as e:
        return {"error": f"Workflow handler error: {e}"}


async def _handle_notification(
    config: dict[str, Any], event_log: EventLog
) -> dict[str, Any]:
    """Send a notification via NotificationService."""
    template_id = config.get("notification_template_id")

    try:
        from app.db.session import async_session_factory
        from app.services.notification.service import NotificationService

        async with async_session_factory() as db:
            svc = NotificationService(db)
            notification = await svc.create_notification(
                tenant_id=str(event_log.tenant_id),
                user_id=config.get("recipient_user_id"),
                title=config.get("title", f"Event: {event_log.event_type_name}"),
                message=config.get("message", f"Event triggered: {event_log.event_type_name}"),
                category=config.get("category", "event"),
                priority=config.get("priority", "MEDIUM"),
                metadata={"event_log_id": str(event_log.id), "payload": event_log.payload},
            )
            await db.commit()
            return {"notification_id": str(notification.id) if notification else None}
    except Exception as e:
        return {"error": f"Notification handler error: {e}"}


async def _handle_activity(
    config: dict[str, Any], event_log: EventLog
) -> dict[str, Any]:
    """Start an activity execution via ExecutionService."""
    activity_id = config.get("activity_id")
    if not activity_id:
        return {"error": "No activity_id configured"}

    try:
        from app.db.session import async_session_factory
        from app.services.automation.execution_service import ExecutionService

        async with async_session_factory() as db:
            svc = ExecutionService(db)
            execution = await svc.start_execution(
                tenant_id=str(event_log.tenant_id),
                activity_id=activity_id,
                version_id=config.get("version_id"),
                started_by=str(event_log.emitted_by) if event_log.emitted_by else "event_system",
                input_data=event_log.payload,
            )
            await db.commit()
            return {"activity_execution_id": str(execution.id)}
    except Exception as e:
        return {"error": f"Activity handler error: {e}"}


async def _handle_webhook(
    config: dict[str, Any], event_log: EventLog
) -> dict[str, Any]:
    """POST event payload to a webhook URL."""
    url = config.get("url") or config.get("webhook_url")
    if not url:
        return {"error": "No webhook URL configured"}

    try:
        import httpx

        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={
                    "event_type": event_log.event_type_name,
                    "payload": event_log.payload,
                    "event_log_id": str(event_log.id),
                    "source": event_log.source,
                    "emitted_at": event_log.emitted_at.isoformat() if event_log.emitted_at else None,
                    "trace_id": event_log.trace_id,
                },
                headers=headers,
            )
            return {
                "status_code": response.status_code,
                "response_body": response.text[:1000],
            }
    except Exception as e:
        return {"error": f"Webhook handler error: {e}"}
