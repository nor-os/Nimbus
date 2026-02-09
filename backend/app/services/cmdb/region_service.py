"""
Overview: Delivery region service — CRUD and hierarchy traversal for delivery regions.
Architecture: Service delivery engine region management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.delivery_region
Concepts: Hierarchical regions with system-seeded defaults. Supports get children, get ancestors.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.delivery_region import DeliveryRegion

logger = logging.getLogger(__name__)


class RegionServiceError(Exception):
    def __init__(self, message: str, code: str = "REGION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class DeliveryRegionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_region(self, region_id: str) -> DeliveryRegion | None:
        result = await self.db.execute(
            select(DeliveryRegion).where(
                DeliveryRegion.id == region_id,
                DeliveryRegion.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_regions(
        self,
        tenant_id: str | None = None,
        parent_region_id: str | None = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[DeliveryRegion], int]:
        stmt = select(DeliveryRegion).where(DeliveryRegion.deleted_at.is_(None))

        if tenant_id:
            stmt = stmt.where(
                (DeliveryRegion.tenant_id == tenant_id) | (DeliveryRegion.tenant_id.is_(None))
            )
        else:
            stmt = stmt.where(DeliveryRegion.tenant_id.is_(None))

        if parent_region_id:
            stmt = stmt.where(DeliveryRegion.parent_region_id == parent_region_id)

        if active_only:
            stmt = stmt.where(DeliveryRegion.is_active.is_(True))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(DeliveryRegion.sort_order, DeliveryRegion.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_top_level_regions(
        self, tenant_id: str | None = None
    ) -> list[DeliveryRegion]:
        stmt = select(DeliveryRegion).where(
            DeliveryRegion.parent_region_id.is_(None),
            DeliveryRegion.deleted_at.is_(None),
            DeliveryRegion.is_active.is_(True),
        )
        if tenant_id:
            stmt = stmt.where(
                (DeliveryRegion.tenant_id == tenant_id) | (DeliveryRegion.tenant_id.is_(None))
            )
        stmt = stmt.order_by(DeliveryRegion.sort_order, DeliveryRegion.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_children(self, region_id: str) -> list[DeliveryRegion]:
        result = await self.db.execute(
            select(DeliveryRegion).where(
                DeliveryRegion.parent_region_id == region_id,
                DeliveryRegion.deleted_at.is_(None),
                DeliveryRegion.is_active.is_(True),
            ).order_by(DeliveryRegion.sort_order, DeliveryRegion.name)
        )
        return list(result.scalars().all())

    async def get_ancestors(self, region_id: str) -> list[DeliveryRegion]:
        ancestors: list[DeliveryRegion] = []
        current = await self.get_region(region_id)
        while current and current.parent_region_id:
            parent = await self.get_region(str(current.parent_region_id))
            if parent:
                ancestors.append(parent)
            current = parent
        return list(reversed(ancestors))

    async def create_region(self, tenant_id: str | None, data: dict) -> DeliveryRegion:
        region = DeliveryRegion(
            tenant_id=tenant_id,
            parent_region_id=data.get("parent_region_id"),
            name=data["name"],
            display_name=data["display_name"],
            code=data["code"],
            timezone=data.get("timezone"),
            country_code=data.get("country_code"),
            is_system=data.get("is_system", False),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(region)
        await self.db.flush()
        return region

    async def update_region(self, region_id: str, data: dict) -> DeliveryRegion:
        region = await self.get_region(region_id)
        if not region:
            raise RegionServiceError("Delivery region not found", "NOT_FOUND")
        if region.is_system:
            allowed = {"display_name", "timezone", "country_code", "is_active", "sort_order"}
            for key in data:
                if key not in allowed:
                    raise RegionServiceError(
                        f"Cannot modify '{key}' on system region", "SYSTEM_PROTECTED"
                    )
        for key, val in data.items():
            if hasattr(region, key):
                setattr(region, key, val)
        await self.db.flush()
        return region

    async def delete_region(self, region_id: str) -> bool:
        region = await self.get_region(region_id)
        if not region:
            raise RegionServiceError("Delivery region not found", "NOT_FOUND")
        if region.is_system:
            raise RegionServiceError("Cannot delete system region", "SYSTEM_PROTECTED")
        region.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
