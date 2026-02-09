"""
Overview: CI versioning service — snapshot management and point-in-time queries.
Architecture: Append-only snapshot history for CI change tracking (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.ci_snapshot
Concepts: Every CI mutation creates a snapshot with the full state. Snapshots are immutable
    and support point-in-time queries, version comparison, and change history.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.ci_snapshot import CISnapshot

logger = logging.getLogger(__name__)


class VersioningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_versions(
        self,
        ci_id: str,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CISnapshot], int]:
        """List all versions (snapshots) of a CI."""
        stmt = select(CISnapshot).where(
            CISnapshot.ci_id == ci_id,
            CISnapshot.tenant_id == tenant_id,
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(CISnapshot.version_number.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_version(
        self,
        ci_id: str,
        tenant_id: str,
        version_number: int,
    ) -> CISnapshot | None:
        """Get a specific version of a CI."""
        result = await self.db.execute(
            select(CISnapshot).where(
                CISnapshot.ci_id == ci_id,
                CISnapshot.tenant_id == tenant_id,
                CISnapshot.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(
        self,
        ci_id: str,
        tenant_id: str,
    ) -> CISnapshot | None:
        """Get the latest snapshot for a CI."""
        result = await self.db.execute(
            select(CISnapshot)
            .where(
                CISnapshot.ci_id == ci_id,
                CISnapshot.tenant_id == tenant_id,
            )
            .order_by(CISnapshot.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def diff_versions(
        self,
        ci_id: str,
        tenant_id: str,
        version_a: int,
        version_b: int,
    ) -> dict:
        """Compare two versions of a CI and return the differences."""
        snap_a = await self.get_version(ci_id, tenant_id, version_a)
        snap_b = await self.get_version(ci_id, tenant_id, version_b)

        if not snap_a or not snap_b:
            return {"error": "One or both versions not found"}

        data_a = snap_a.snapshot_data or {}
        data_b = snap_b.snapshot_data or {}

        diff: dict = {
            "version_a": version_a,
            "version_b": version_b,
            "changes": {},
        }

        all_keys = set(data_a.keys()) | set(data_b.keys())
        for key in all_keys:
            val_a = data_a.get(key)
            val_b = data_b.get(key)
            if val_a != val_b:
                diff["changes"][key] = {"from": val_a, "to": val_b}

        return diff
