"""
Overview: Temporal activity for tenant data export.
Architecture: Tenant data export activity (Section 9)
Dependencies: temporalio, app.services.tenant.export_service
Concepts: Temporal activities, data export, MinIO storage
"""

from dataclasses import dataclass

from temporalio import activity


@dataclass
class ExportInput:
    tenant_id: str
    job_id: str


@dataclass
class ExportResult:
    tenant_id: str
    job_id: str
    object_name: str
    success: bool
    error: str | None = None


@activity.defn
async def execute_tenant_export(input: ExportInput) -> ExportResult:
    """Execute a tenant data export and upload to MinIO."""
    from app.db.session import async_session_factory
    from app.services.tenant.export_service import ExportService

    try:
        async with async_session_factory() as db:
            service = ExportService(db)
            object_name = await service.execute_export(input.tenant_id, input.job_id)
            activity.logger.info(
                f"Exported tenant {input.tenant_id} to {object_name}"
            )
            return ExportResult(
                tenant_id=input.tenant_id,
                job_id=input.job_id,
                object_name=object_name,
                success=True,
            )
    except Exception as e:
        activity.logger.error(
            f"Failed to export tenant {input.tenant_id}: {e}"
        )
        return ExportResult(
            tenant_id=input.tenant_id,
            job_id=input.job_id,
            object_name="",
            success=False,
            error=str(e),
        )
