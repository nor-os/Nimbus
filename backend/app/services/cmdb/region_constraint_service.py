"""
Overview: Region constraint service — manages geographic constraints on price lists and catalogs.
Architecture: Region-based filtering for pricing and catalog applicability (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.region_constraint, app.models.cmdb.delivery_region
Concepts: Region constraints restrict which delivery regions a price list or catalog applies to.
    A tenant with a primary_region_id matching any constraint (including ancestors) can use it.
    No constraints means globally applicable.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.delivery_region import DeliveryRegion
from app.models.cmdb.price_list import PriceList
from app.models.cmdb.region_constraint import (
    CatalogRegionConstraint,
    PriceListRegionConstraint,
)
from app.models.cmdb.service_catalog import ServiceCatalog


class RegionConstraintService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Price List Region Constraints ─────────────────────────────────

    async def set_price_list_regions(
        self, price_list_id: str, region_ids: list[str]
    ) -> list[str]:
        """Replace all region constraints for a price list."""
        existing = await self.db.execute(
            select(PriceListRegionConstraint).where(
                PriceListRegionConstraint.price_list_id == price_list_id,
            )
        )
        for row in existing.scalars().all():
            await self.db.delete(row)

        for region_id in region_ids:
            link = PriceListRegionConstraint(
                price_list_id=price_list_id,
                delivery_region_id=region_id,
            )
            self.db.add(link)

        await self.db.flush()
        return region_ids

    async def get_price_list_regions(
        self, price_list_id: str
    ) -> list[str]:
        """Return delivery region IDs constrained to a price list."""
        result = await self.db.execute(
            select(PriceListRegionConstraint.delivery_region_id).where(
                PriceListRegionConstraint.price_list_id == price_list_id,
            )
        )
        return [str(row) for row in result.scalars().all()]

    # ── Catalog Region Constraints ────────────────────────────────────

    async def set_catalog_regions(
        self, catalog_id: str, region_ids: list[str]
    ) -> list[str]:
        """Replace all region constraints for a service catalog."""
        existing = await self.db.execute(
            select(CatalogRegionConstraint).where(
                CatalogRegionConstraint.catalog_id == catalog_id,
            )
        )
        for row in existing.scalars().all():
            await self.db.delete(row)

        for region_id in region_ids:
            link = CatalogRegionConstraint(
                catalog_id=catalog_id,
                delivery_region_id=region_id,
            )
            self.db.add(link)

        await self.db.flush()
        return region_ids

    async def get_catalog_regions(
        self, catalog_id: str
    ) -> list[str]:
        """Return delivery region IDs constrained to a catalog."""
        result = await self.db.execute(
            select(CatalogRegionConstraint.delivery_region_id).where(
                CatalogRegionConstraint.catalog_id == catalog_id,
            )
        )
        return [str(row) for row in result.scalars().all()]

    # ── Region Hierarchy Helpers ──────────────────────────────────────

    async def _get_region_ancestor_ids(
        self, region_id: str
    ) -> list[str]:
        """Build the full ancestor chain for a region (self + parents)."""
        ancestor_ids = [region_id]
        current_id = region_id
        while current_id:
            result = await self.db.execute(
                select(DeliveryRegion.parent_id).where(
                    DeliveryRegion.id == current_id
                )
            )
            parent_id = result.scalar_one_or_none()
            if parent_id:
                ancestor_ids.append(str(parent_id))
                current_id = str(parent_id)
            else:
                break
        return ancestor_ids

    # ── Applicability Queries ─────────────────────────────────────────

    async def get_applicable_price_lists(
        self,
        primary_region_id: str | None,
        tenant_id: str | None = None,
    ) -> list[PriceList]:
        """Return price lists applicable for a tenant's primary region.

        A price list is applicable if:
        - It has no region constraints (global), OR
        - Any of its region constraints matches the tenant's region or ancestors
        """
        # Get all active price lists
        stmt = select(PriceList).where(
            PriceList.deleted_at.is_(None),
            PriceList.status == "published",
        )
        if tenant_id:
            stmt = stmt.where(
                (PriceList.tenant_id == tenant_id) | (PriceList.tenant_id.is_(None))
            )
        result = await self.db.execute(stmt)
        all_lists = list(result.scalars().unique().all())

        if not primary_region_id:
            return all_lists

        ancestor_ids = await self._get_region_ancestor_ids(primary_region_id)

        applicable = []
        for pl in all_lists:
            constraints = getattr(pl, "region_constraints", None) or []
            if not constraints:
                # No constraints = global
                applicable.append(pl)
            else:
                constraint_region_ids = [
                    str(c.delivery_region_id) for c in constraints
                ]
                if any(rid in ancestor_ids for rid in constraint_region_ids):
                    applicable.append(pl)

        return applicable

    async def get_applicable_catalogs(
        self,
        primary_region_id: str | None,
        tenant_id: str | None = None,
    ) -> list[ServiceCatalog]:
        """Return catalogs applicable for a tenant's primary region."""
        stmt = select(ServiceCatalog).where(
            ServiceCatalog.deleted_at.is_(None),
            ServiceCatalog.status == "published",
        )
        if tenant_id:
            stmt = stmt.where(
                (ServiceCatalog.tenant_id == tenant_id)
                | (ServiceCatalog.tenant_id.is_(None))
            )
        result = await self.db.execute(stmt)
        all_catalogs = list(result.scalars().unique().all())

        if not primary_region_id:
            return all_catalogs

        ancestor_ids = await self._get_region_ancestor_ids(primary_region_id)

        applicable = []
        for cat in all_catalogs:
            constraints = getattr(cat, "region_constraints", None) or []
            if not constraints:
                applicable.append(cat)
            else:
                constraint_region_ids = [
                    str(c.delivery_region_id) for c in constraints
                ]
                if any(rid in ancestor_ids for rid in constraint_region_ids):
                    applicable.append(cat)

        return applicable
