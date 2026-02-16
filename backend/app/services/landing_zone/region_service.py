"""
Overview: Landing zone region service — manage multi-region configurations.
Architecture: Landing zone service layer (Section 6)
Dependencies: sqlalchemy, app.models.landing_zone
Concepts: Multi-region landing zones, primary/DR region designation
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.landing_zone import LandingZoneRegion


class LandingZoneRegionService:

    async def add_region(self, db: AsyncSession, *, landing_zone_id: uuid.UUID,
                         region_identifier: str, display_name: str,
                         is_primary: bool = False, is_dr: bool = False,
                         settings: dict | None = None) -> LandingZoneRegion:
        region = LandingZoneRegion(
            landing_zone_id=landing_zone_id, region_identifier=region_identifier,
            display_name=display_name, is_primary=is_primary, is_dr=is_dr, settings=settings,
        )
        db.add(region)
        await db.flush()
        await db.refresh(region)
        return region

    async def get(self, db: AsyncSession, region_id: uuid.UUID) -> LandingZoneRegion | None:
        result = await db.execute(
            select(LandingZoneRegion).where(LandingZoneRegion.id == region_id)
        )
        return result.scalar_one_or_none()

    async def list_by_zone(self, db: AsyncSession, landing_zone_id: uuid.UUID) -> list[LandingZoneRegion]:
        result = await db.execute(
            select(LandingZoneRegion)
            .where(LandingZoneRegion.landing_zone_id == landing_zone_id)
            .order_by(LandingZoneRegion.is_primary.desc(), LandingZoneRegion.display_name)
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, region_id: uuid.UUID, **kwargs) -> LandingZoneRegion:
        region = await self.get(db, region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")
        for key, value in kwargs.items():
            if hasattr(region, key) and key not in ("id", "landing_zone_id", "created_at"):
                setattr(region, key, value)
        await db.flush()
        await db.refresh(region)
        return region

    async def remove(self, db: AsyncSession, region_id: uuid.UUID) -> None:
        region = await self.get(db, region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")
        await db.delete(region)
        await db.flush()
