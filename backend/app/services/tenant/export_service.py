"""
Overview: Service for exporting tenant data as ZIP archives to MinIO.
Architecture: Tenant data export (Section 4.2)
Dependencies: sqlalchemy, minio, app.models
Concepts: Data export, MinIO object storage, presigned URLs
"""

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.compartment import Compartment
from app.models.tenant import Tenant
from app.models.tenant_quota import TenantQuota
from app.models.tenant_settings import TenantSettings
from app.models.user_tenant import UserTenant


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_export_job(self, tenant_id: str) -> str:
        """Create an export job and return a job ID."""
        return str(uuid.uuid4())

    async def execute_export(self, tenant_id: str, job_id: str) -> str:
        """Execute the export: gather data, create ZIP, upload to MinIO."""
        data = await self._gather_tenant_data(tenant_id)
        zip_buffer = self._create_zip(data)

        object_name = f"exports/{tenant_id}/{job_id}.zip"
        settings = get_settings()

        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        # Ensure bucket exists
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)

        zip_bytes = zip_buffer.getvalue()
        client.put_object(
            settings.minio_bucket,
            object_name,
            io.BytesIO(zip_bytes),
            length=len(zip_bytes),
            content_type="application/zip",
        )

        return object_name

    async def get_download_url(self, tenant_id: str, job_id: str) -> str:
        """Get a presigned download URL for an export."""
        from datetime import timedelta

        from minio import Minio

        settings = get_settings()
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        object_name = f"exports/{tenant_id}/{job_id}.zip"
        return client.presigned_get_object(
            settings.minio_bucket, object_name, expires=timedelta(hours=1)
        )

    async def _gather_tenant_data(self, tenant_id: str) -> dict:
        """Gather all tenant data for export."""
        # Tenant info
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        tenant_data = {
            "id": str(tenant.id),
            "name": tenant.name,
            "level": tenant.level,
            "created_at": tenant.created_at.isoformat(),
        } if tenant else {}

        # Settings
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        settings_data = [
            {"key": s.key, "value": s.value, "value_type": s.value_type}
            for s in result.scalars().all()
        ]

        # Quotas
        result = await self.db.execute(
            select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        )
        quotas_data = [
            {
                "quota_type": q.quota_type,
                "limit_value": q.limit_value,
                "current_usage": q.current_usage,
                "enforcement": q.enforcement,
            }
            for q in result.scalars().all()
        ]

        # Users
        result = await self.db.execute(
            select(UserTenant).where(UserTenant.tenant_id == tenant_id)
        )
        users_data = [
            {
                "user_id": str(ut.user_id),
                "is_default": ut.is_default,
                "joined_at": ut.joined_at.isoformat(),
            }
            for ut in result.scalars().all()
        ]

        # Compartments
        result = await self.db.execute(
            select(Compartment).where(
                Compartment.tenant_id == tenant_id,
                Compartment.deleted_at.is_(None),
            )
        )
        compartments_data = [
            {
                "id": str(c.id),
                "name": c.name,
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "description": c.description,
            }
            for c in result.scalars().all()
        ]

        return {
            "tenant": tenant_data,
            "settings": settings_data,
            "quotas": quotas_data,
            "users": users_data,
            "compartments": compartments_data,
            "exported_at": datetime.now(UTC).isoformat(),
        }

    def _create_zip(self, data: dict) -> io.BytesIO:
        """Create a ZIP file from the export data."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for key, value in data.items():
                if key == "exported_at":
                    continue
                zf.writestr(
                    f"{key}.json",
                    json.dumps(value, indent=2, default=str),
                )
            zf.writestr(
                "metadata.json",
                json.dumps({"exported_at": data["exported_at"]}, indent=2),
            )
        buffer.seek(0)
        return buffer
