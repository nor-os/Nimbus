"""
Overview: Landing zone service — CRUD, lifecycle management, publish workflow.
Architecture: Landing zone service layer (Section 6)
Dependencies: sqlalchemy, app.models.landing_zone
Concepts: Provider landing zones, lifecycle (DRAFT→PUBLISHED→ARCHIVED), topology binding
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.landing_zone import LandingZone, LandingZoneStatus


class LandingZoneService:

    async def create(self, db: AsyncSession, *, tenant_id: uuid.UUID, backend_id: uuid.UUID,
                     name: str, created_by: uuid.UUID,
                     topology_id: uuid.UUID | None = None,
                     description: str | None = None, cloud_tenancy_id: uuid.UUID | None = None,
                     settings: dict | None = None,
                     hierarchy: dict | None = None,
                     region_id: uuid.UUID | None = None) -> LandingZone:
        zone = LandingZone(
            tenant_id=tenant_id, backend_id=backend_id, topology_id=topology_id,
            region_id=region_id,
            name=name, description=description, cloud_tenancy_id=cloud_tenancy_id,
            settings=settings, hierarchy=hierarchy,
            created_by=created_by, status=LandingZoneStatus.DRAFT, version=0,
        )
        db.add(zone)
        await db.flush()
        await db.refresh(zone)
        return zone

    async def get(self, db: AsyncSession, zone_id: uuid.UUID) -> LandingZone | None:
        result = await db.execute(
            select(LandingZone)
            .options(selectinload(LandingZone.tag_policies))
            .where(LandingZone.id == zone_id, LandingZone.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_backend(self, db: AsyncSession, backend_id: uuid.UUID) -> LandingZone | None:
        """Get the first landing zone for a backend (backward compat)."""
        result = await db.execute(
            select(LandingZone)
            .options(selectinload(LandingZone.tag_policies))
            .where(LandingZone.backend_id == backend_id, LandingZone.deleted_at.is_(None))
            .order_by(LandingZone.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_region(self, db: AsyncSession, region_id: uuid.UUID) -> list[LandingZone]:
        result = await db.execute(
            select(LandingZone)
            .options(selectinload(LandingZone.tag_policies))
            .where(LandingZone.region_id == region_id, LandingZone.deleted_at.is_(None))
            .order_by(LandingZone.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_tenant(self, db: AsyncSession, tenant_id: uuid.UUID,
                             status: str | None = None, search: str | None = None,
                             offset: int | None = None, limit: int | None = None) -> list[LandingZone]:
        stmt = (
            select(LandingZone)
            .options(selectinload(LandingZone.tag_policies))
            .where(LandingZone.tenant_id == tenant_id, LandingZone.deleted_at.is_(None))
        )
        if status:
            stmt = stmt.where(LandingZone.status == LandingZoneStatus(status))
        if search:
            stmt = stmt.where(LandingZone.name.ilike(f"%{search}%"))
        stmt = stmt.order_by(LandingZone.created_at.desc())
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_backend(self, db: AsyncSession, backend_id: uuid.UUID) -> list[LandingZone]:
        result = await db.execute(
            select(LandingZone)
            .options(selectinload(LandingZone.tag_policies))
            .where(LandingZone.backend_id == backend_id, LandingZone.deleted_at.is_(None))
            .order_by(LandingZone.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, zone_id: uuid.UUID, **kwargs) -> LandingZone:
        zone = await self.get(db, zone_id)
        if not zone:
            raise ValueError(f"Landing zone {zone_id} not found")
        if zone.status == LandingZoneStatus.ARCHIVED:
            raise ValueError("Cannot update an archived landing zone")
        for key, value in kwargs.items():
            if hasattr(zone, key) and key not in ("id", "created_at", "created_by", "tenant_id"):
                setattr(zone, key, value)
        await db.flush()
        await db.refresh(zone)
        return zone

    async def publish(self, db: AsyncSession, zone_id: uuid.UUID) -> LandingZone:
        zone = await self.get(db, zone_id)
        if not zone:
            raise ValueError(f"Landing zone {zone_id} not found")
        if zone.status != LandingZoneStatus.DRAFT:
            raise ValueError(f"Can only publish DRAFT zones, current status: {zone.status.value}")
        zone.status = LandingZoneStatus.PUBLISHED
        zone.version += 1
        await db.flush()
        await db.refresh(zone)
        return zone

    async def archive(self, db: AsyncSession, zone_id: uuid.UUID) -> LandingZone:
        zone = await self.get(db, zone_id)
        if not zone:
            raise ValueError(f"Landing zone {zone_id} not found")
        zone.status = LandingZoneStatus.ARCHIVED
        await db.flush()
        await db.refresh(zone)
        return zone

    async def delete(self, db: AsyncSession, zone_id: uuid.UUID) -> None:
        zone = await self.get(db, zone_id)
        if not zone:
            raise ValueError(f"Landing zone {zone_id} not found")
        if zone.status == LandingZoneStatus.PUBLISHED:
            raise ValueError("Cannot delete a published landing zone; archive it first")
        zone.deleted_at = datetime.now(timezone.utc)
        await db.flush()
