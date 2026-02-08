"""
Overview: Temporal workflow for purging soft-deleted tenants past retention period.
Architecture: Durable tenant cleanup workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.tenant_purge
Concepts: Temporal workflows, tenant lifecycle, idempotent purge
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.tenant_purge import (
        find_purgeable_tenants,
        purge_single_tenant,
    )


@workflow.defn
class TenantPurgeWorkflow:
    @workflow.run
    async def run(self) -> dict:
        """Find and purge all eligible tenants."""
        tenant_ids = await workflow.execute_activity(
            find_purgeable_tenants,
            start_to_close_timeout=timedelta(seconds=60),
        )

        results = {"purged": 0, "failed": 0, "errors": []}

        for tenant_id in tenant_ids:
            result = await workflow.execute_activity(
                purge_single_tenant,
                tenant_id,
                start_to_close_timeout=timedelta(seconds=120),
            )
            if result.success:
                results["purged"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(
                    {"tenant_id": tenant_id, "error": result.error}
                )

        return results
