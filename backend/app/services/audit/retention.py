"""
Overview: Retention and archival service for audit log lifecycle management.
Architecture: Audit data lifecycle (Section 8)
Dependencies: sqlalchemy, minio, app.models.audit
Concepts: Data retention, hot/cold storage, MinIO archival, NDJSON compression, per-category overrides
"""

from __future__ import annotations

import gzip
import io
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit import AuditLog, CategoryRetentionOverride, EventCategory, RetentionPolicy


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

    # ── Category Override CRUD ───────────────────────────

    async def list_category_overrides(self, tenant_id: str) -> list[CategoryRetentionOverride]:
        result = await self.db.execute(
            select(CategoryRetentionOverride).where(
                CategoryRetentionOverride.tenant_id == tenant_id,
                CategoryRetentionOverride.deleted_at.is_(None),
            ).order_by(CategoryRetentionOverride.event_category)
        )
        return list(result.scalars().all())

    async def upsert_category_override(
        self,
        tenant_id: str,
        event_category: str,
        hot_days: int,
        cold_days: int,
    ) -> CategoryRetentionOverride:
        cat_enum = EventCategory(event_category)
        result = await self.db.execute(
            select(CategoryRetentionOverride).where(
                CategoryRetentionOverride.tenant_id == tenant_id,
                CategoryRetentionOverride.event_category == cat_enum,
                CategoryRetentionOverride.deleted_at.is_(None),
            )
        )
        override = result.scalar_one_or_none()
        if override:
            override.hot_days = hot_days
            override.cold_days = cold_days
        else:
            override = CategoryRetentionOverride(
                tenant_id=tenant_id,
                event_category=cat_enum,
                hot_days=hot_days,
                cold_days=cold_days,
            )
            self.db.add(override)
        await self.db.flush()
        return override

    async def delete_category_override(self, tenant_id: str, event_category: str) -> bool:
        cat_enum = EventCategory(event_category)
        result = await self.db.execute(
            select(CategoryRetentionOverride).where(
                CategoryRetentionOverride.tenant_id == tenant_id,
                CategoryRetentionOverride.event_category == cat_enum,
                CategoryRetentionOverride.deleted_at.is_(None),
            )
        )
        override = result.scalar_one_or_none()
        if not override:
            return False
        override.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def _get_hot_days_map(self, tenant_id: str) -> dict[EventCategory | None, int]:
        """Build a mapping of event_category → hot_days.  None key = global default."""
        policy = await self.get_or_create_policy(tenant_id)
        overrides = await self.list_category_overrides(tenant_id)
        result: dict[EventCategory | None, int] = {None: policy.hot_days}
        for ov in overrides:
            result[ov.event_category] = ov.hot_days
        return result

    async def _get_cold_days_map(self, tenant_id: str) -> dict[EventCategory | None, int]:
        """Build a mapping of event_category → cold_days.  None key = global default."""
        policy = await self.get_or_create_policy(tenant_id)
        overrides = await self.list_category_overrides(tenant_id)
        result: dict[EventCategory | None, int] = {None: policy.cold_days}
        for ov in overrides:
            result[ov.event_category] = ov.cold_days
        return result

    # ── Archival ────────────────────────────────────────

    async def archive_cold_logs(self, tenant_id: str) -> dict:
        """Move logs older than hot_days to MinIO as NDJSON.gz.

        Respects per-category overrides: each category uses its own hot_days
        cutoff when an override exists, falling back to the global default.
        """
        policy = await self.get_or_create_policy(tenant_id)
        if not policy.archive_enabled:
            return {"archived": 0, "skipped": True}

        hot_map = await self._get_hot_days_map(tenant_id)
        now = datetime.now(UTC)

        # Build per-cutoff filters.  Group categories by their cutoff date
        # to minimize the number of queries.
        cutoff_to_categories: dict[datetime, list[EventCategory]] = {}
        default_cutoff = now - timedelta(days=hot_map[None])

        for cat in EventCategory:
            days = hot_map.get(cat, hot_map[None])
            cutoff = now - timedelta(days=days)
            cutoff_to_categories.setdefault(cutoff, []).append(cat)

        # Collect all log IDs to archive
        all_logs: list[AuditLog] = []
        for cutoff, categories in cutoff_to_categories.items():
            result = await self.db.execute(
                select(AuditLog)
                .where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at < cutoff,
                    AuditLog.event_category.in_(categories),
                )
                .order_by(AuditLog.created_at.asc())
                .limit(10000)
            )
            all_logs.extend(result.scalars().all())

        # Also archive logs with NULL event_category using the global cutoff
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at < default_cutoff,
                AuditLog.event_category.is_(None),
            )
            .order_by(AuditLog.created_at.asc())
            .limit(10000)
        )
        all_logs.extend(result.scalars().all())

        if not all_logs:
            return {"archived": 0}

        # Deduplicate (in case of overlapping results)
        seen_ids: set = set()
        unique_logs: list[AuditLog] = []
        for log in all_logs:
            if log.id not in seen_ids:
                seen_ids.add(log.id)
                unique_logs.append(log)

        # Build NDJSON
        lines = []
        for log in unique_logs:
            lines.append(json.dumps({
                "id": str(log.id),
                "tenant_id": str(log.tenant_id),
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "actor_email": log.actor_email,
                "actor_ip": log.actor_ip,
                "action": log.action.value,
                "event_category": log.event_category.value if log.event_category else None,
                "event_type": log.event_type,
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
        object_key = f"{tenant_id}/{now.year}/{now.month:02d}/{now.day:02d}.ndjson.gz"
        _upload_to_minio("nimbus-audit-archives", object_key, compressed)

        # Delete archived logs from PostgreSQL
        log_ids = [log.id for log in unique_logs]
        await self.db.execute(
            delete(AuditLog).where(AuditLog.id.in_(log_ids))
        )
        await self.db.flush()

        return {"archived": len(unique_logs), "object_key": object_key}

    async def purge_expired(self, tenant_id: str) -> dict:
        """Delete archives past cold_days from MinIO.

        Uses the maximum cold_days across global default and all category
        overrides as the conservative cutoff for file-level purging.
        """
        cold_map = await self._get_cold_days_map(tenant_id)
        max_cold_days = max(cold_map.values())
        cutoff = datetime.now(UTC) - timedelta(days=max_cold_days)

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
