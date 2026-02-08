"""
Overview: Temporal workflow for tenant data export to MinIO.
Architecture: Durable tenant export workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.tenant_export
Concepts: Temporal workflows, data export, durable operations
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.tenant_export import (
        ExportInput,
        execute_tenant_export,
    )


@dataclass
class TenantExportParams:
    tenant_id: str
    job_id: str


@workflow.defn
class TenantExportWorkflow:
    @workflow.run
    async def run(self, params: TenantExportParams) -> dict:
        """Execute a tenant data export."""
        result = await workflow.execute_activity(
            execute_tenant_export,
            ExportInput(tenant_id=params.tenant_id, job_id=params.job_id),
            start_to_close_timeout=timedelta(minutes=10),
        )

        return {
            "tenant_id": result.tenant_id,
            "job_id": result.job_id,
            "object_name": result.object_name,
            "success": result.success,
            "error": result.error,
        }
