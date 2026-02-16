"""
Overview: Service catalog service — CRUD for versioned service catalogs, catalog items, and tenant pins.
Architecture: Catalog versioning with tenant-scoped pins (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_catalog
Concepts: Service catalogs group offerings into versioned collections. Version management mirrors
    the price list pattern: create → draft → publish → archive. Tenant pins bind consumers.
"""
from __future__ import annotations

import uuid as uuid_mod
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.service_catalog import (
    ServiceCatalog,
    ServiceCatalogItem,
    TenantCatalogPin,
)
from app.services.cmdb.catalog_service import CatalogServiceError


class ServiceCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Catalog CRUD ─────────────────────────────────────────────────

    async def create_catalog(
        self, tenant_id: str | None, data: dict
    ) -> ServiceCatalog:
        catalog = ServiceCatalog(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            version_major=1,
            version_minor=0,
            status="draft",
        )
        self.db.add(catalog)
        await self.db.flush()
        catalog.group_id = catalog.id
        await self.db.flush()
        return catalog

    async def get_catalog(self, catalog_id: str) -> ServiceCatalog | None:
        result = await self.db.execute(
            select(ServiceCatalog)
            .where(
                ServiceCatalog.id == catalog_id,
                ServiceCatalog.deleted_at.is_(None),
            )
            .options(selectinload(ServiceCatalog.items))
        )
        return result.scalar_one_or_none()

    async def list_catalogs(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceCatalog], int]:
        stmt = select(ServiceCatalog).where(ServiceCatalog.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (ServiceCatalog.tenant_id == tenant_id)
                | (ServiceCatalog.tenant_id.is_(None))
            )
        if status:
            stmt = stmt.where(ServiceCatalog.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            stmt.options(selectinload(ServiceCatalog.items))
            .order_by(ServiceCatalog.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def delete_catalog(self, catalog_id: str) -> bool:
        catalog = await self.get_catalog(catalog_id)
        if not catalog:
            raise CatalogServiceError("Service catalog not found", "NOT_FOUND")
        catalog.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Version Management ───────────────────────────────────────────

    async def create_version(
        self, catalog_id: str, bump: str = "minor"
    ) -> ServiceCatalog:
        source = await self.get_catalog(catalog_id)
        if not source:
            raise CatalogServiceError("Source catalog not found", "NOT_FOUND")

        group_id = source.group_id or source.id
        if bump == "major":
            new_major = source.version_major + 1
            new_minor = 0
        else:
            new_major = source.version_major
            new_minor = source.version_minor + 1

        new_cat = ServiceCatalog(
            tenant_id=source.tenant_id,
            name=source.name,
            description=source.description,
            group_id=group_id,
            version_major=new_major,
            version_minor=new_minor,
            status="draft",
            parent_version_id=source.id,
        )
        self.db.add(new_cat)
        await self.db.flush()

        for item in source.items or []:
            new_item = ServiceCatalogItem(
                catalog_id=new_cat.id,
                service_offering_id=item.service_offering_id,
                service_group_id=item.service_group_id,
                sort_order=item.sort_order,
            )
            self.db.add(new_item)
        await self.db.flush()

        return await self.get_catalog(str(new_cat.id))

    async def publish_catalog(self, catalog_id: str) -> ServiceCatalog:
        result = await self.db.execute(
            select(ServiceCatalog).where(
                ServiceCatalog.id == catalog_id,
                ServiceCatalog.deleted_at.is_(None),
            )
        )
        catalog = result.scalar_one_or_none()
        if not catalog:
            raise CatalogServiceError("Catalog not found", "NOT_FOUND")
        if catalog.status != "draft":
            raise CatalogServiceError(
                "Only draft catalogs can be published", "INVALID_STATUS"
            )

        if catalog.group_id:
            published = await self.db.execute(
                select(ServiceCatalog).where(
                    ServiceCatalog.group_id == catalog.group_id,
                    ServiceCatalog.status == "published",
                    ServiceCatalog.deleted_at.is_(None),
                    ServiceCatalog.id != catalog.id,
                )
            )
            for old in published.scalars().all():
                old.status = "archived"

        catalog.status = "published"
        await self.db.flush()
        return catalog

    async def archive_catalog(self, catalog_id: str) -> ServiceCatalog:
        result = await self.db.execute(
            select(ServiceCatalog).where(
                ServiceCatalog.id == catalog_id,
                ServiceCatalog.deleted_at.is_(None),
            )
        )
        catalog = result.scalar_one_or_none()
        if not catalog:
            raise CatalogServiceError("Catalog not found", "NOT_FOUND")
        catalog.status = "archived"
        await self.db.flush()
        return catalog

    async def list_versions(self, group_id: str) -> list[ServiceCatalog]:
        result = await self.db.execute(
            select(ServiceCatalog)
            .where(
                ServiceCatalog.group_id == group_id,
                ServiceCatalog.deleted_at.is_(None),
            )
            .options(selectinload(ServiceCatalog.items))
            .order_by(
                ServiceCatalog.version_major.desc(),
                ServiceCatalog.version_minor.desc(),
            )
        )
        return list(result.scalars().unique().all())

    async def clone_for_tenant(
        self, catalog_id: str, target_tenant_id: str
    ) -> ServiceCatalog:
        source = await self.get_catalog(catalog_id)
        if not source:
            raise CatalogServiceError("Source catalog not found", "NOT_FOUND")

        clone = ServiceCatalog(
            tenant_id=target_tenant_id,
            name=source.name,
            description=source.description,
            version_major=1,
            version_minor=0,
            status="draft",
            cloned_from_catalog_id=source.id,
        )
        self.db.add(clone)
        await self.db.flush()
        clone.group_id = clone.id
        await self.db.flush()

        for item in source.items or []:
            new_item = ServiceCatalogItem(
                catalog_id=clone.id,
                service_offering_id=item.service_offering_id,
                service_group_id=item.service_group_id,
                sort_order=item.sort_order,
            )
            self.db.add(new_item)
        await self.db.flush()

        return await self.get_catalog(str(clone.id))

    # ── Tenant Assignments & Diff ────────────────────────────────────

    async def get_tenant_assignments(
        self, catalog_id: str
    ) -> list[dict]:
        """Return combined pin + clone assignments for a catalog."""
        # Pins
        pins = await self.get_pinned_tenants_for_catalog(catalog_id)
        assignments: list[dict] = []
        for pin in pins:
            assignments.append({
                "tenant_id": str(pin.tenant_id),
                "assignment_type": "pin",
                "catalog_id": catalog_id,
                "clone_catalog_id": None,
                "additions": 0,
                "deletions": 0,
                "is_customized": False,
            })

        # Clones
        source = await self.get_catalog(catalog_id)
        source_items = source.items if source else []
        source_keys = {
            (str(i.service_offering_id), str(i.service_group_id))
            for i in source_items
        }

        result = await self.db.execute(
            select(ServiceCatalog)
            .where(
                ServiceCatalog.cloned_from_catalog_id == catalog_id,
                ServiceCatalog.deleted_at.is_(None),
            )
            .options(selectinload(ServiceCatalog.items))
        )
        clones = list(result.scalars().unique().all())

        for clone in clones:
            clone_keys = {
                (str(i.service_offering_id), str(i.service_group_id))
                for i in (clone.items or [])
            }
            additions = len(clone_keys - source_keys)
            deletions = len(source_keys - clone_keys)
            assignments.append({
                "tenant_id": str(clone.tenant_id),
                "assignment_type": "clone",
                "catalog_id": catalog_id,
                "clone_catalog_id": str(clone.id),
                "additions": additions,
                "deletions": deletions,
                "is_customized": additions > 0 or deletions > 0,
            })

        return assignments

    async def get_catalog_diff(
        self, source_catalog_id: str, clone_catalog_id: str
    ) -> dict:
        """Compare items between a source catalog and its clone."""
        source = await self.get_catalog(source_catalog_id)
        clone = await self.get_catalog(clone_catalog_id)

        if not source or not clone:
            raise CatalogServiceError("Catalog not found", "NOT_FOUND")

        source_keys = {
            (str(i.service_offering_id), str(i.service_group_id)): i
            for i in (source.items or [])
        }
        clone_keys = {
            (str(i.service_offering_id), str(i.service_group_id)): i
            for i in (clone.items or [])
        }

        additions = [
            clone_keys[k] for k in clone_keys if k not in source_keys
        ]
        deletions = [
            source_keys[k] for k in source_keys if k not in clone_keys
        ]
        common = [
            clone_keys[k] for k in clone_keys if k in source_keys
        ]

        return {
            "source_catalog_id": source_catalog_id,
            "clone_catalog_id": clone_catalog_id,
            "additions": additions,
            "deletions": deletions,
            "common": common,
        }

    # ── Catalog Items ────────────────────────────────────────────────

    async def add_item(
        self,
        catalog_id: str,
        service_offering_id: str | None = None,
        service_group_id: str | None = None,
        sort_order: int = 0,
    ) -> ServiceCatalogItem:
        if not service_offering_id and not service_group_id:
            raise CatalogServiceError(
                "Must provide either service_offering_id or service_group_id",
                "VALIDATION_ERROR",
            )
        item = ServiceCatalogItem(
            catalog_id=catalog_id,
            service_offering_id=service_offering_id,
            service_group_id=service_group_id,
            sort_order=sort_order,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def remove_item(self, item_id: str) -> bool:
        result = await self.db.execute(
            select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError("Catalog item not found", "NOT_FOUND")
        await self.db.delete(item)
        await self.db.flush()
        return True

    async def list_items(self, catalog_id: str) -> list[ServiceCatalogItem]:
        result = await self.db.execute(
            select(ServiceCatalogItem)
            .where(ServiceCatalogItem.catalog_id == catalog_id)
            .order_by(ServiceCatalogItem.sort_order)
        )
        return list(result.scalars().all())

    # ── Tenant Pins ──────────────────────────────────────────────────

    async def pin_tenant(
        self,
        tenant_id: str,
        catalog_id: str,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> TenantCatalogPin:
        pin_from = effective_from or date.today()
        pin_to = effective_to or date(2999, 12, 31)

        # Overlap check: find any active pin for this tenant whose date range overlaps
        overlap_stmt = select(TenantCatalogPin).where(
            TenantCatalogPin.tenant_id == tenant_id,
            TenantCatalogPin.deleted_at.is_(None),
            TenantCatalogPin.effective_from <= pin_to,
            TenantCatalogPin.effective_to >= pin_from,
        )
        result = await self.db.execute(overlap_stmt)
        conflict = result.scalar_one_or_none()
        if conflict:
            raise CatalogServiceError(
                "Overlaps with existing catalog pin for this tenant",
                "OVERLAP",
            )

        pin = TenantCatalogPin(
            tenant_id=tenant_id,
            catalog_id=catalog_id,
            effective_from=pin_from,
            effective_to=pin_to,
        )
        self.db.add(pin)
        await self.db.flush()
        return pin

    async def unpin_tenant(
        self, tenant_id: str, catalog_id: str
    ) -> bool:
        result = await self.db.execute(
            select(TenantCatalogPin).where(
                TenantCatalogPin.tenant_id == tenant_id,
                TenantCatalogPin.catalog_id == catalog_id,
                TenantCatalogPin.deleted_at.is_(None),
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError("Pin not found", "NOT_FOUND")
        pin.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_pins(self, tenant_id: str) -> list[TenantCatalogPin]:
        result = await self.db.execute(
            select(TenantCatalogPin)
            .join(TenantCatalogPin.catalog)
            .where(
                TenantCatalogPin.tenant_id == tenant_id,
                TenantCatalogPin.deleted_at.is_(None),
                ServiceCatalog.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantCatalogPin.catalog),
                selectinload(TenantCatalogPin.overlay_items),
            )
        )
        return list(result.scalars().all())

    async def get_pinned_tenants_for_catalog(
        self, catalog_id: str
    ) -> list[TenantCatalogPin]:
        """List tenants pinned to a specific catalog."""
        result = await self.db.execute(
            select(TenantCatalogPin)
            .join(TenantCatalogPin.catalog)
            .where(
                TenantCatalogPin.catalog_id == catalog_id,
                TenantCatalogPin.deleted_at.is_(None),
                ServiceCatalog.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantCatalogPin.catalog),
                selectinload(TenantCatalogPin.overlay_items),
            )
        )
        return list(result.scalars().all())
