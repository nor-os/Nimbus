"""
Overview: System workflow seeder — seeds editable system workflow templates for tenants.
Architecture: Service for seeding pre-built system workflows (Section 5)
Dependencies: app.services.workflow.definition_service
Concepts: System workflows, impersonation workflow, break-glass workflow, idempotent seeding
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_definition import WorkflowDefinition, WorkflowType
from app.services.workflow.definition_service import WorkflowDefinitionService

logger = logging.getLogger(__name__)


# ── System Workflow Templates ────────────────────────────────

IMPERSONATION_WORKFLOW: dict[str, Any] = {
    "name": "System: Impersonation Request",
    "description": "Handles impersonation requests with approval, time-limited access, and automatic revocation.",
    "graph": {
        "nodes": [
            {"id": "start", "type": "start", "config": {}, "position": {"x": 100, "y": 300}, "label": "Start"},
            {
                "id": "validate", "type": "script", "position": {"x": 350, "y": 300},
                "label": "Validate Request",
                "config": {
                    "assignments": [
                        {"variable": "target_user_id", "expression": "input.target_user_id"},
                        {"variable": "reason", "expression": "input.reason"},
                        {"variable": "duration_minutes", "expression": "input.duration_minutes || 60"},
                        {"variable": "is_valid", "expression": "input.target_user_id != null && input.reason != null"},
                    ],
                },
            },
            {
                "id": "approval", "type": "approval_gate", "position": {"x": 600, "y": 300},
                "label": "Impersonation Approval",
                "config": {
                    "title": "Impersonation Access Request",
                    "description": "A user has requested impersonation access. Review the justification carefully.",
                    "approver_role_names": ["Tenant Admin"],
                    "chain_mode": "SEQUENTIAL",
                    "timeout_minutes": 60,
                },
            },
            {
                "id": "grant", "type": "script", "position": {"x": 850, "y": 250},
                "label": "Grant Access",
                "config": {
                    "assignments": [
                        {"variable": "access_granted", "expression": "true"},
                        {"variable": "granted_at", "expression": "now()"},
                    ],
                },
            },
            {
                "id": "wait", "type": "delay", "position": {"x": 1100, "y": 250},
                "label": "Access Duration",
                "config": {"seconds": "vars.duration_minutes * 60"},
            },
            {
                "id": "revoke", "type": "script", "position": {"x": 1350, "y": 250},
                "label": "Revoke Access",
                "config": {
                    "assignments": [
                        {"variable": "access_revoked", "expression": "true"},
                        {"variable": "revoked_at", "expression": "now()"},
                    ],
                },
            },
            {
                "id": "audit", "type": "audit_log", "position": {"x": 1600, "y": 250},
                "label": "Audit Trail",
                "config": {
                    "action": "impersonation.completed",
                    "resource_type": "user",
                    "priority": "WARN",
                    "details": {
                        "target_user_id": "{{vars.target_user_id}}",
                        "reason": "{{vars.reason}}",
                        "duration_minutes": "{{vars.duration_minutes}}",
                    },
                },
            },
            {
                "id": "denied_notify", "type": "notification", "position": {"x": 850, "y": 400},
                "label": "Request Denied",
                "config": {
                    "channel": "in_app",
                    "title": "Impersonation Request Denied",
                    "body": "Your impersonation request has been denied.",
                },
            },
            {"id": "end", "type": "end", "config": {}, "position": {"x": 1850, "y": 300}, "label": "End"},
        ],
        "connections": [
            {"source": "start", "target": "validate", "sourcePort": "out", "targetPort": "in"},
            {"source": "validate", "target": "approval", "sourcePort": "out", "targetPort": "in"},
            {"source": "approval", "target": "grant", "sourcePort": "approved", "targetPort": "in"},
            {"source": "approval", "target": "denied_notify", "sourcePort": "rejected", "targetPort": "in"},
            {"source": "grant", "target": "wait", "sourcePort": "out", "targetPort": "in"},
            {"source": "wait", "target": "revoke", "sourcePort": "out", "targetPort": "in"},
            {"source": "revoke", "target": "audit", "sourcePort": "out", "targetPort": "in"},
            {"source": "audit", "target": "end", "sourcePort": "out", "targetPort": "in"},
            {"source": "denied_notify", "target": "end", "sourcePort": "out", "targetPort": "in"},
        ],
    },
}

BREAK_GLASS_WORKFLOW: dict[str, Any] = {
    "name": "System: Break-Glass Emergency Access",
    "description": "Emergency access escalation with multi-approval, time-limited elevation, and mandatory audit.",
    "graph": {
        "nodes": [
            {"id": "start", "type": "start", "config": {}, "position": {"x": 100, "y": 300}, "label": "Start"},
            {
                "id": "validate", "type": "script", "position": {"x": 350, "y": 300},
                "label": "Validate Emergency",
                "config": {
                    "assignments": [
                        {"variable": "incident_id", "expression": "input.incident_id"},
                        {"variable": "justification", "expression": "input.justification"},
                        {"variable": "time_limit_minutes", "expression": "input.time_limit_minutes || 120"},
                        {"variable": "is_valid", "expression": "input.incident_id != null && input.justification != null"},
                    ],
                },
            },
            {
                "id": "approval", "type": "approval_gate", "position": {"x": 600, "y": 300},
                "label": "Emergency Approval",
                "config": {
                    "title": "Break-Glass Emergency Access Request",
                    "description": "EMERGENCY: A user has requested break-glass elevated access. Requires multi-approval.",
                    "approver_role_names": ["Tenant Admin", "Provider Admin"],
                    "chain_mode": "PARALLEL",
                    "timeout_minutes": 30,
                },
            },
            {
                "id": "elevate", "type": "script", "position": {"x": 850, "y": 250},
                "label": "Elevate Permissions",
                "config": {
                    "assignments": [
                        {"variable": "elevated", "expression": "true"},
                        {"variable": "elevated_at", "expression": "now()"},
                    ],
                },
            },
            {
                "id": "timer", "type": "delay", "position": {"x": 1100, "y": 250},
                "label": "Time Limit",
                "config": {"seconds": "vars.time_limit_minutes * 60"},
            },
            {
                "id": "revoke", "type": "script", "position": {"x": 1350, "y": 250},
                "label": "Revoke Elevation",
                "config": {
                    "assignments": [
                        {"variable": "elevated", "expression": "false"},
                        {"variable": "revoked_at", "expression": "now()"},
                    ],
                },
            },
            {
                "id": "audit", "type": "audit_log", "position": {"x": 1600, "y": 250},
                "label": "Audit Trail",
                "config": {
                    "action": "break_glass.completed",
                    "resource_type": "access",
                    "priority": "CRITICAL",
                    "details": {
                        "incident_id": "{{vars.incident_id}}",
                        "justification": "{{vars.justification}}",
                        "time_limit_minutes": "{{vars.time_limit_minutes}}",
                    },
                },
            },
            {
                "id": "notify_complete", "type": "notification", "position": {"x": 1850, "y": 250},
                "label": "Notify Complete",
                "config": {
                    "channel": "in_app",
                    "title": "Break-Glass Session Ended",
                    "body": "Emergency access for incident {{vars.incident_id}} has been automatically revoked.",
                    "recipient_role_names": ["Tenant Admin"],
                },
            },
            {"id": "end", "type": "end", "config": {}, "position": {"x": 2100, "y": 300}, "label": "End"},
        ],
        "connections": [
            {"source": "start", "target": "validate", "sourcePort": "out", "targetPort": "in"},
            {"source": "validate", "target": "approval", "sourcePort": "out", "targetPort": "in"},
            {"source": "approval", "target": "elevate", "sourcePort": "approved", "targetPort": "in"},
            {"source": "approval", "target": "end", "sourcePort": "rejected", "targetPort": "in"},
            {"source": "elevate", "target": "timer", "sourcePort": "out", "targetPort": "in"},
            {"source": "timer", "target": "revoke", "sourcePort": "out", "targetPort": "in"},
            {"source": "revoke", "target": "audit", "sourcePort": "out", "targetPort": "in"},
            {"source": "audit", "target": "notify_complete", "sourcePort": "out", "targetPort": "in"},
            {"source": "notify_complete", "target": "end", "sourcePort": "out", "targetPort": "in"},
        ],
    },
}

SYSTEM_WORKFLOWS = [IMPERSONATION_WORKFLOW, BREAK_GLASS_WORKFLOW]


class SystemWorkflowSeeder:
    """Seeds editable system workflow templates for tenants."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._definition_svc = WorkflowDefinitionService(db)

    async def seed_for_tenant(
        self, tenant_id: str, system_user_id: str
    ) -> list[WorkflowDefinition]:
        """Seed all system workflows for a tenant. Idempotent — skips existing."""
        created: list[WorkflowDefinition] = []

        for template in SYSTEM_WORKFLOWS:
            name = template["name"]

            # Check if already exists (including soft-deleted, since unique constraint
            # covers all rows regardless of deleted_at)
            existing = await self.db.execute(
                select(WorkflowDefinition).where(
                    WorkflowDefinition.tenant_id == tenant_id,
                    WorkflowDefinition.name == name,
                    WorkflowDefinition.is_system.is_(True),
                )
            )
            row = existing.scalar_one_or_none()
            if row and row.deleted_at is None:
                logger.info("System workflow '%s' already exists for tenant %s, skipping", name, tenant_id)
                continue
            if row and row.deleted_at is not None:
                # Restore soft-deleted system workflow
                row.deleted_at = None
                row.description = template["description"]
                row.graph = template["graph"]
                created.append(row)
                logger.info("Restored soft-deleted system workflow '%s' for tenant %s", name, tenant_id)
                continue

            definition = await self._definition_svc.create(
                tenant_id=tenant_id,
                created_by=system_user_id,
                data={
                    "name": name,
                    "description": template["description"],
                    "graph": template["graph"],
                    "workflow_type": WorkflowType.SYSTEM,
                    "is_system": True,
                    "timeout_seconds": 7200,
                },
            )
            created.append(definition)
            logger.info("Seeded system workflow '%s' for tenant %s", name, tenant_id)

        return created
