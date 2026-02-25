"""
Overview: System event type and subscription registration at application startup.
Architecture: Populates in-memory registries with ~22 system event types (Section 11.6)
Dependencies: app.services.events.registry
Concepts: System event catalog, default subscriptions, startup registration
"""

from __future__ import annotations

import logging

from app.services.events.registry import (
    EventTypeDefinition,
    get_event_type_registry,
    get_subscription_registry,
)

logger = logging.getLogger(__name__)


def register_system_events() -> None:
    """Register all system event types in the in-memory registry."""
    registry = get_event_type_registry()

    events = [
        # Authentication
        EventTypeDefinition(
            name="auth.login.succeeded",
            category="AUTHENTICATION",
            description="User successfully logged in",
            source_validators=["auth_service"],
            payload_schema={"type": "object", "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"},
                "ip": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="auth.login.failed",
            category="AUTHENTICATION",
            description="Login attempt failed",
            source_validators=["auth_service"],
            payload_schema={"type": "object", "properties": {
                "email": {"type": "string"},
                "ip": {"type": "string"},
                "reason": {"type": "string"},
            }},
        ),
        # Impersonation
        EventTypeDefinition(
            name="impersonation.requested",
            category="AUTHENTICATION",
            description="Impersonation session requested",
            source_validators=["impersonation_service"],
            payload_schema={"type": "object", "properties": {
                "session_id": {"type": "string"},
                "requester_id": {"type": "string"},
                "target_user_id": {"type": "string"},
                "mode": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="impersonation.activated",
            category="AUTHENTICATION",
            description="Impersonation session activated",
            source_validators=["impersonation_service"],
        ),
        EventTypeDefinition(
            name="impersonation.ended",
            category="AUTHENTICATION",
            description="Impersonation session ended",
            source_validators=["impersonation_service"],
        ),
        # Approval
        EventTypeDefinition(
            name="approval.requested",
            category="APPROVAL",
            description="New approval request created",
            source_validators=["approval_service"],
            payload_schema={"type": "object", "properties": {
                "request_id": {"type": "string"},
                "operation_type": {"type": "string"},
                "requester_id": {"type": "string"},
                "title": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="approval.decided",
            category="APPROVAL",
            description="Approval step decided",
            source_validators=["approval_service"],
            payload_schema={"type": "object", "properties": {
                "request_id": {"type": "string"},
                "step_id": {"type": "string"},
                "decision": {"type": "string"},
                "approver_id": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="approval.expired",
            category="APPROVAL",
            description="Approval request expired",
            source_validators=["approval_service"],
        ),
        EventTypeDefinition(
            name="approval.cancelled",
            category="APPROVAL",
            description="Approval request cancelled",
            source_validators=["approval_service"],
        ),
        # Deployment
        EventTypeDefinition(
            name="deployment.status_changed",
            category="DEPLOYMENT",
            description="Deployment status changed",
            source_validators=["deployment_service"],
            payload_schema={"type": "object", "properties": {
                "deployment_id": {"type": "string"},
                "old_status": {"type": "string"},
                "new_status": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="deployment.config_changed",
            category="DEPLOYMENT",
            description="Deployment configuration mutated",
            source_validators=["mutation_engine"],
        ),
        # Environment
        EventTypeDefinition(
            name="environment.status_changed",
            category="ENVIRONMENT",
            description="Environment status changed",
            source_validators=["environment_service"],
            payload_schema={"type": "object", "properties": {
                "environment_id": {"type": "string"},
                "old_status": {"type": "string"},
                "new_status": {"type": "string"},
            }},
        ),
        # CMDB
        EventTypeDefinition(
            name="cmdb.ci.created",
            category="CMDB",
            description="Configuration item created",
            source_validators=["cmdb_service"],
        ),
        EventTypeDefinition(
            name="cmdb.ci.updated",
            category="CMDB",
            description="Configuration item updated",
            source_validators=["cmdb_service"],
        ),
        EventTypeDefinition(
            name="cmdb.ci.deleted",
            category="CMDB",
            description="Configuration item deleted",
            source_validators=["cmdb_service"],
        ),
        # Automation
        EventTypeDefinition(
            name="activity.execution.started",
            category="AUTOMATION",
            description="Activity execution started",
            source_validators=["execution_service"],
            payload_schema={"type": "object", "properties": {
                "execution_id": {"type": "string"},
                "activity_id": {"type": "string"},
                "activity_name": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="activity.execution.completed",
            category="AUTOMATION",
            description="Activity execution completed successfully",
            source_validators=["execution_service"],
        ),
        EventTypeDefinition(
            name="activity.execution.failed",
            category="AUTOMATION",
            description="Activity execution failed",
            source_validators=["execution_service"],
        ),
        EventTypeDefinition(
            name="activity.version.published",
            category="AUTOMATION",
            description="Activity version published",
            source_validators=["activity_service"],
        ),
        # Workflow
        EventTypeDefinition(
            name="workflow.execution.started",
            category="WORKFLOW",
            description="Workflow execution started",
            source_validators=["workflow_execution_service"],
            payload_schema={"type": "object", "properties": {
                "execution_id": {"type": "string"},
                "definition_id": {"type": "string"},
                "definition_name": {"type": "string"},
            }},
        ),
        EventTypeDefinition(
            name="workflow.execution.completed",
            category="WORKFLOW",
            description="Workflow execution completed successfully",
            source_validators=["workflow_execution_service"],
        ),
        EventTypeDefinition(
            name="workflow.execution.failed",
            category="WORKFLOW",
            description="Workflow execution failed",
            source_validators=["workflow_execution_service"],
        ),
    ]

    for evt in events:
        registry.register(evt)

    logger.info("Registered %d system event types", len(events))


def register_system_subscriptions() -> None:
    """Register default system subscriptions (code-defined handlers)."""
    _registry = get_subscription_registry()
    # No default system subscriptions yet — tenants create their own via UI
    logger.info("System subscription registration complete")
