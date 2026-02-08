"""
Overview: REST API endpoints for tenant data export via Temporal workflow.
Architecture: Tenant export endpoints (Section 7.1)
Dependencies: fastapi, temporalio, app.services.tenant.export_service
Concepts: Data export, Temporal workflows, MinIO presigned URLs
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/tenants/{tenant_id}/export", tags=["tenant-export"])


class ExportJobResponse(BaseModel):
    job_id: str
    status: str = "started"


class ExportDownloadResponse(BaseModel):
    download_url: str


@router.post("", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_export(
    tenant_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> ExportJobResponse:
    """Start an async tenant data export via Temporal workflow."""
    from app.core.temporal import get_temporal_client
    from app.services.tenant.export_service import ExportService
    from app.workflows.tenant_export import TenantExportParams, TenantExportWorkflow

    service = ExportService(db)
    job_id = await service.create_export_job(tenant_id)

    try:
        client = await get_temporal_client()
        settings_mod = __import__("app.core.config", fromlist=["get_settings"])
        settings = settings_mod.get_settings()

        await client.start_workflow(
            TenantExportWorkflow.run,
            TenantExportParams(tenant_id=tenant_id, job_id=job_id),
            id=f"tenant-export-{job_id}",
            task_queue=settings.temporal_task_queue,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "EXPORT_START_FAILED",
                    "message": str(e),
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    return ExportJobResponse(job_id=job_id)


@router.get("/{job_id}/download", response_model=ExportDownloadResponse)
async def get_export_download(
    tenant_id: str,
    job_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> ExportDownloadResponse:
    """Get a presigned download URL for a completed export."""
    from app.services.tenant.export_service import ExportService

    service = ExportService(db)
    try:
        url = await service.get_download_url(tenant_id, job_id)
        return ExportDownloadResponse(download_url=url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "EXPORT_NOT_FOUND",
                    "message": str(e),
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
