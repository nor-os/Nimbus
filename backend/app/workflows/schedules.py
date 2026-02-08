"""
Overview: Declarative registry of Temporal Schedules for recurring workflows.
Architecture: Schedule definitions for Temporal worker registration (Section 9)
Dependencies: temporalio, app.workflows.audit_archive, app.workflows.tenant_purge
Concepts: Temporal Schedules, cron-based recurring workflows
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduleDefinition:
    """Describes a recurring Temporal Schedule to register at worker startup."""

    schedule_id: str
    workflow_name: str
    cron: str
    description: str


SCHEDULES: list[ScheduleDefinition] = [
    ScheduleDefinition(
        schedule_id="nimbus-audit-archive",
        workflow_name="AuditArchiveWorkflow",
        cron="0 3 * * *",
        description="Archive cold audit logs (daily 3 AM UTC)",
    ),
    ScheduleDefinition(
        schedule_id="nimbus-tenant-purge",
        workflow_name="TenantPurgeWorkflow",
        cron="0 4 * * *",
        description="Purge soft-deleted tenants past retention (daily 4 AM UTC)",
    ),
]
