"""
Overview: Audit log export service for generating downloadable exports in JSON/CSV format.
Architecture: Audit export path (Section 8)
Dependencies: sqlalchemy, minio, app.models.audit
Concepts: Data export, NDJSON, CSV generation, MinIO storage, presigned URLs
"""

import csv
import io
import json
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit import AuditAction, AuditLog, AuditPriority

EXPORT_BUCKET = "nimbus-audit-exports"


class AuditExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_export(
        self,
        tenant_id: str,
        format: str = "json",
        filters: dict | None = None,
    ) -> str:
        """Start an export and return an export_id. The actual work is done via Temporal."""
        return str(uuid.uuid4())

    async def execute_export(
        self,
        tenant_id: str,
        export_id: str,
        format: str = "json",
        filters: dict | None = None,
    ) -> str:
        """Execute the export: query logs, format, upload to MinIO."""
        logs = await self._query_logs(tenant_id, filters or {})

        if format == "csv":
            data = self._to_csv(logs)
            content_type = "text/csv"
            ext = "csv"
        else:
            data = self._to_ndjson(logs)
            content_type = "application/x-ndjson"
            ext = "ndjson"

        object_name = f"{tenant_id}/{export_id}.{ext}"
        self._upload(object_name, data, content_type)

        return object_name

    def get_download_url(self, tenant_id: str, export_id: str) -> str | None:
        """Get a presigned download URL for an export."""
        settings = get_settings()
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        # Try both extensions
        for ext in ("ndjson", "csv"):
            object_name = f"{tenant_id}/{export_id}.{ext}"
            try:
                client.stat_object(EXPORT_BUCKET, object_name)
                return client.presigned_get_object(
                    EXPORT_BUCKET, object_name, expires=timedelta(hours=24)
                )
            except Exception:
                continue
        return None

    async def _query_logs(self, tenant_id: str, filters: dict) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if filters.get("date_from"):
            query = query.where(AuditLog.created_at >= filters["date_from"])
        if filters.get("date_to"):
            query = query.where(AuditLog.created_at <= filters["date_to"])
        if filters.get("action"):
            query = query.where(AuditLog.action == AuditAction(filters["action"]))
        if filters.get("resource_type"):
            query = query.where(AuditLog.resource_type == filters["resource_type"])
        if filters.get("priority"):
            query = query.where(AuditLog.priority == AuditPriority(filters["priority"]))

        query = query.order_by(AuditLog.created_at.desc()).limit(50000)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _to_ndjson(self, logs: list[AuditLog]) -> bytes:
        lines = []
        for log in logs:
            lines.append(json.dumps(_log_to_dict(log), default=str))
        return "\n".join(lines).encode("utf-8")

    def _to_csv(self, logs: list[AuditLog]) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "actor_email", "actor_ip", "action",
            "resource_type", "resource_id", "resource_name",
            "priority", "trace_id", "created_at",
        ])
        for log in logs:
            writer.writerow([
                str(log.id), str(log.tenant_id), log.actor_email, log.actor_ip,
                log.action.value, log.resource_type, log.resource_id, log.resource_name,
                log.priority.value, log.trace_id, log.created_at.isoformat(),
            ])
        return output.getvalue().encode("utf-8")

    def _upload(self, object_name: str, data: bytes, content_type: str) -> None:
        settings = get_settings()
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        if not client.bucket_exists(EXPORT_BUCKET):
            client.make_bucket(EXPORT_BUCKET)

        client.put_object(
            EXPORT_BUCKET,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )


def _log_to_dict(log: AuditLog) -> dict:
    return {
        "id": str(log.id),
        "tenant_id": str(log.tenant_id),
        "actor_id": str(log.actor_id) if log.actor_id else None,
        "actor_email": log.actor_email,
        "actor_ip": log.actor_ip,
        "action": log.action.value,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "old_values": log.old_values,
        "new_values": log.new_values,
        "trace_id": log.trace_id,
        "priority": log.priority.value,
        "hash": log.hash,
        "previous_hash": log.previous_hash,
        "metadata": log.metadata_,
        "created_at": log.created_at.isoformat(),
    }
