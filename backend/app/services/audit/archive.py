"""
Overview: Archive retrieval service for accessing cold-stored audit logs from MinIO.
Architecture: Audit archive read path (Section 8)
Dependencies: minio, app.core.config
Concepts: Cold storage retrieval, MinIO object listing, presigned URLs
"""

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings


class ArchiveService:
    def list_archives(
        self,
        tenant_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """List available archive objects for a tenant, optionally filtered by date range."""
        settings = get_settings()
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        bucket = "nimbus-audit-archives"
        if not client.bucket_exists(bucket):
            return []

        archives = []
        objects = client.list_objects(bucket, prefix=f"{tenant_id}/", recursive=True)
        for obj in objects:
            if start and obj.last_modified and obj.last_modified < start:
                continue
            if end and obj.last_modified and obj.last_modified > end:
                continue
            archives.append({
                "key": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified or datetime.now(UTC),
            })

        return archives

    def get_download_url(self, key: str) -> str:
        """Get a presigned download URL for an archive object."""
        settings = get_settings()
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        return client.presigned_get_object(
            "nimbus-audit-archives",
            key,
            expires=timedelta(hours=1),
        )
