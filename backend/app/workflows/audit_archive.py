"""
Overview: Temporal workflow for daily audit log archival across all tenants.
Architecture: Durable audit archival workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.audit
Concepts: Temporal workflows, scheduled archival, tenant iteration
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.audit import (
        ArchiveInput,
        archive_tenant_audit_logs,
        find_tenants_for_archival,
    )


@workflow.defn
class AuditArchiveWorkflow:
    @workflow.run
    async def run(self) -> dict:
        """Find all tenants with archival enabled and archive their cold logs."""
        tenant_ids = await workflow.execute_activity(
            find_tenants_for_archival,
            start_to_close_timeout=timedelta(seconds=60),
        )

        results = {"archived_total": 0, "purged_total": 0, "failed": 0, "errors": []}

        for tenant_id in tenant_ids:
            result = await workflow.execute_activity(
                archive_tenant_audit_logs,
                ArchiveInput(tenant_id=tenant_id),
                start_to_close_timeout=timedelta(minutes=5),
            )
            if result.success:
                results["archived_total"] += result.archived
                results["purged_total"] += result.purged
            else:
                results["failed"] += 1
                results["errors"].append({
                    "tenant_id": tenant_id,
                    "error": result.error,
                })

        return results
