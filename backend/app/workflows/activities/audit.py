"""
Overview: Temporal activities for audit archival and export operations.
Architecture: Audit workflow activities (Section 9)
Dependencies: temporalio, app.services.audit
Concepts: Temporal activities, audit archival, data export
"""

from dataclasses import dataclass

from temporalio import activity


@dataclass
class ArchiveInput:
    tenant_id: str


@dataclass
class ArchiveResult:
    tenant_id: str
    archived: int
    purged: int
    success: bool
    error: str | None = None


@dataclass
class ExportInput:
    tenant_id: str
    export_id: str
    format: str = "json"
    filters: dict | None = None


@dataclass
class ExportResult:
    tenant_id: str
    export_id: str
    object_name: str
    success: bool
    error: str | None = None


@activity.defn
async def archive_tenant_audit_logs(input: ArchiveInput) -> ArchiveResult:
    """Archive cold audit logs for a tenant and purge expired archives."""
    from app.db.session import async_session_factory
    from app.services.audit.retention import RetentionService

    try:
        async with async_session_factory() as db:
            service = RetentionService(db)
            archive_result = await service.archive_cold_logs(input.tenant_id)
            purge_result = await service.purge_expired(input.tenant_id)
            await db.commit()

            activity.logger.info(
                f"Archived {archive_result.get('archived', 0)} logs, "
                f"purged {purge_result.get('purged', 0)} archives for tenant {input.tenant_id}"
            )

            return ArchiveResult(
                tenant_id=input.tenant_id,
                archived=archive_result.get("archived", 0),
                purged=purge_result.get("purged", 0),
                success=True,
            )
    except Exception as e:
        activity.logger.error(f"Audit archive failed for tenant {input.tenant_id}: {e}")
        return ArchiveResult(
            tenant_id=input.tenant_id,
            archived=0,
            purged=0,
            success=False,
            error=str(e),
        )


@activity.defn
async def find_tenants_for_archival() -> list[str]:
    """Find all tenants with archive-enabled retention policies."""
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.audit import RetentionPolicy

    async with async_session_factory() as db:
        result = await db.execute(
            select(RetentionPolicy.tenant_id).where(
                RetentionPolicy.archive_enabled.is_(True),
                RetentionPolicy.deleted_at.is_(None),
            )
        )
        return [str(row[0]) for row in result.all()]


@activity.defn
async def execute_audit_export(input: ExportInput) -> ExportResult:
    """Execute an audit log export and upload to MinIO."""
    from app.db.session import async_session_factory
    from app.services.audit.export import AuditExportService

    try:
        async with async_session_factory() as db:
            service = AuditExportService(db)
            object_name = await service.execute_export(
                tenant_id=input.tenant_id,
                export_id=input.export_id,
                format=input.format,
                filters=input.filters,
            )
            activity.logger.info(
                f"Exported audit logs for tenant {input.tenant_id} to {object_name}"
            )
            return ExportResult(
                tenant_id=input.tenant_id,
                export_id=input.export_id,
                object_name=object_name,
                success=True,
            )
    except Exception as e:
        activity.logger.error(f"Audit export failed for tenant {input.tenant_id}: {e}")
        return ExportResult(
            tenant_id=input.tenant_id,
            export_id=input.export_id,
            object_name="",
            success=False,
            error=str(e),
        )
