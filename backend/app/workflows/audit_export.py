"""
Overview: Temporal workflow for on-demand audit log export.
Architecture: Durable audit export workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.audit
Concepts: Temporal workflows, on-demand export, MinIO storage
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.audit import (
        ExportInput,
        execute_audit_export,
    )


@dataclass
class AuditExportParams:
    tenant_id: str
    export_id: str
    format: str = "json"
    filters: dict | None = None


@workflow.defn
class AuditExportWorkflow:
    @workflow.run
    async def run(self, params: AuditExportParams) -> dict:
        """Execute an audit log export."""
        result = await workflow.execute_activity(
            execute_audit_export,
            ExportInput(
                tenant_id=params.tenant_id,
                export_id=params.export_id,
                format=params.format,
                filters=params.filters,
            ),
            start_to_close_timeout=timedelta(minutes=10),
        )

        return {
            "tenant_id": result.tenant_id,
            "export_id": result.export_id,
            "object_name": result.object_name,
            "success": result.success,
            "error": result.error,
        }
