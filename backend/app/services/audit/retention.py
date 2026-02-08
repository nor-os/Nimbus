"""
Overview: Retention and archival service for audit log lifecycle management.
Architecture: Audit data lifecycle (Section 8)
Dependencies: sqlalchemy, minio, app.models.audit
Concepts: Data retention, hot/cold storage, MinIO archival, NDJSON compression
"""

import gzip
import io
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit import AuditLog, RetentionPolicy


class RetentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Policy CRUD ─────────────────────────────────────

    async def get_policy(self, tenant_id: str) -> RetentionPolicy | None:
        result = await self.db.execute(
            select(RetentionPolicy).where(
                RetentionPolicy.tenant_id == tenant_id,
                RetentionPolicy.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_policy(self, tenant_id: str) -> RetentionPolicy:
        policy = await self.get_policy(tenant_id)
        if policy:
            return policy
        policy = RetentionPolicy(tenant_id=tenant_id)
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def update_policy(
        self,
        tenant_id: str,
        hot_days: int | None = None,
        cold_days: int | None = None,
        archive_enabled: bool | None = None,
    ) -> RetentionPolicy:
        policy = await self.get_or_create_policy(tenant_id)
        if hot_days is not None:
            policy.hot_days = hot_days
        if cold_days is not None:
            policy.cold_days = cold_days
        if archive_enabled is not None:
            policy.archive_enabled = archive_enabled
        await self.db.flush()
        return policy

    # ── Archival ────────────────────────────────────────

    async def archive_cold_logs(self, tenant_id: str) -> dict:
        """Move logs older than hot_days to MinIO as NDJSON.gz."""
        policy = await self.get_or_create_policy(tenant_id)
        if not policy.archive_enabled:
            return {"archived": 0, "skipped": True}

        cutoff = datetime.now(UTC) - timedelta(days=policy.hot_days)

        # Fetch logs to archive
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at < cutoff,
            )
            .order_by(AuditLog.created_at.asc())
            .limit(10000)
        )
        logs = list(result.scalars().all())

        if not logs:
            return {"archived": 0}

        # Build NDJSON
        lines = []
        for log in logs:
            lines.append(json.dumps({
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
            }, default=str))

        ndjson_data = "\n".join(lines).encode("utf-8")
        compressed = gzip.compress(ndjson_data)

        # Upload to MinIO
        now = datetime.now(UTC)
        object_key = f"{tenant_id}/{now.year}/{now.month:02d}/{now.day:02d}.ndjson.gz"
        _upload_to_minio("nimbus-audit-archives", object_key, compressed)

        # Delete archived logs from PostgreSQL
        log_ids = [log.id for log in logs]
        await self.db.execute(
            delete(AuditLog).where(AuditLog.id.in_(log_ids))
        )
        await self.db.flush()

        return {"archived": len(logs), "object_key": object_key}

    async def purge_expired(self, tenant_id: str) -> dict:
        """Delete archives past cold_days from MinIO."""
        policy = await self.get_or_create_policy(tenant_id)
        cutoff = datetime.now(UTC) - timedelta(days=policy.cold_days)

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
            return {"purged": 0}

        purged = 0
        objects = client.list_objects(bucket, prefix=f"{tenant_id}/", recursive=True)
        for obj in objects:
            if obj.last_modified and obj.last_modified < cutoff:
                client.remove_object(bucket, obj.object_name)
                purged += 1

        return {"purged": purged}


def _upload_to_minio(bucket: str, key: str, data: bytes) -> None:
    """Upload bytes to MinIO, creating bucket if needed."""
    settings = get_settings()
    from minio import Minio

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )

    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type="application/gzip",
    )
