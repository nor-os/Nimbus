"""
Overview: Service catalog service — CRUD for service offerings, price lists, and pricing engine
    with region-aware + coverage-aware specificity cascade and semantic versioning.
Architecture: Catalog and pricing management with tenant overrides, version lifecycle,
    region-default lists, and tenant-to-version pin assignments (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_offering, app.models.cmdb.price_list
Concepts: Service offerings are billable items. Price lists group pricing with date ranges.
    Versioning: price lists have group_id, major.minor versions, and draft→published→archived
    lifecycle. Tenant pins bind tenants to specific price list versions. The pricing engine
    resolves the effective price using a 16-level (4-tier × 4-specificity) cascade:
    override → pinned client list → pinned region list → global default.
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.price_list import (
    PriceList,
    PriceListItem,
    TenantPriceListPin,
)
from app.models.cmdb.price_list_overlay import PriceListOverlayItem
from app.models.cmdb.service_offering import ServiceOffering
from app.models.cmdb.service_offering_ci_class import ServiceOfferingCIClass
from app.models.cmdb.service_offering_region import ServiceOfferingRegion

logger = logging.getLogger(__name__)


class CatalogServiceError(Exception):
    def __init__(self, message: str, code: str = "CATALOG_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Service Offerings ─────────────────────────────────────────────

    async def get_offering(
        self, offering_id: str, tenant_id: str
    ) -> ServiceOffering | None:
        result = await self.db.execute(
            select(ServiceOffering)
            .where(
                ServiceOffering.id == offering_id,
                ServiceOffering.tenant_id == tenant_id,
                ServiceOffering.deleted_at.is_(None),
            )
            .options(
                selectinload(ServiceOffering.regions),
                selectinload(ServiceOffering.ci_classes),
            )
        )
        return result.scalar_one_or_none()

    async def list_offerings(
        self,
        tenant_id: str,
        category: str | None = None,
        service_type: str | None = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceOffering], int]:
        stmt = select(ServiceOffering).where(
            ServiceOffering.tenant_id == tenant_id,
            ServiceOffering.deleted_at.is_(None),
        )
        if active_only:
            stmt = stmt.where(ServiceOffering.is_active.is_(True))
        if category:
            stmt = stmt.where(ServiceOffering.category == category)
        if service_type:
            stmt = stmt.where(ServiceOffering.service_type == service_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(ServiceOffering.name)
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.options(
            selectinload(ServiceOffering.regions),
            selectinload(ServiceOffering.ci_classes),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_offering(
        self, tenant_id: str, data: dict
    ) -> ServiceOffering:
        offering = ServiceOffering(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            measuring_unit=data.get("measuring_unit", "month"),
            service_type=data.get("service_type", "resource"),
            operating_model=data.get("operating_model"),
            default_coverage_model=data.get("default_coverage_model"),
            base_fee=data.get("base_fee"),
            fee_period=data.get("fee_period"),
            minimum_amount=data.get("minimum_amount"),
            minimum_currency=data.get("minimum_currency"),
            minimum_period=data.get("minimum_period"),
        )
        self.db.add(offering)
        await self.db.flush()
        return offering

    async def update_offering(
        self, offering_id: str, tenant_id: str, data: dict
    ) -> ServiceOffering:
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")
        if getattr(offering, "status", "draft") == "published":
            raise CatalogServiceError(
                "Published offerings cannot be modified. Clone it first.",
                "IMMUTABLE",
            )
        for key, val in data.items():
            if hasattr(offering, key):
                setattr(offering, key, val)
        await self.db.flush()
        return offering

    async def delete_offering(
        self, offering_id: str, tenant_id: str
    ) -> bool:
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")
        offering.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def clone_offering(
        self, offering_id: str, tenant_id: str
    ) -> ServiceOffering:
        """Clone an offering (typically a published one) into a new draft."""
        source = await self.get_offering(offering_id, tenant_id)
        if not source:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")

        clone = ServiceOffering(
            tenant_id=tenant_id,
            name=source.name,
            description=source.description,
            category=source.category,
            measuring_unit=source.measuring_unit,
            service_type=source.service_type,
            operating_model=source.operating_model,
            default_coverage_model=source.default_coverage_model,
            status="draft",
            cloned_from_id=source.id,
            base_fee=getattr(source, "base_fee", None),
            fee_period=getattr(source, "fee_period", None),
            minimum_amount=getattr(source, "minimum_amount", None),
            minimum_currency=getattr(source, "minimum_currency", None),
            minimum_period=getattr(source, "minimum_period", None),
        )
        self.db.add(clone)
        await self.db.flush()

        # Clone CI class links
        for link in getattr(source, "ci_classes", []) or []:
            new_link = ServiceOfferingCIClass(
                service_offering_id=clone.id,
                ci_class_id=link.ci_class_id,
            )
            self.db.add(new_link)

        # Clone region links
        for link in getattr(source, "regions", []) or []:
            new_link = ServiceOfferingRegion(
                service_offering_id=clone.id,
                delivery_region_id=link.delivery_region_id,
            )
            self.db.add(new_link)

        await self.db.flush()
        return await self.get_offering(str(clone.id), tenant_id)

    async def publish_offering(
        self, offering_id: str, tenant_id: str
    ) -> ServiceOffering:
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")
        if getattr(offering, "status", "draft") != "draft":
            raise CatalogServiceError(
                "Only draft offerings can be published", "INVALID_STATUS"
            )
        offering.status = "published"
        await self.db.flush()
        return offering

    async def archive_offering(
        self, offering_id: str, tenant_id: str
    ) -> ServiceOffering:
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")
        offering.status = "archived"
        await self.db.flush()
        return offering

    # ── Offering Regions ──────────────────────────────────────────────

    async def set_offering_regions(
        self, offering_id: str, tenant_id: str, region_ids: list[str]
    ) -> list[str]:
        """Replace all region links for an offering (delete + insert)."""
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")

        # Delete existing
        existing = await self.db.execute(
            select(ServiceOfferingRegion).where(
                ServiceOfferingRegion.service_offering_id == offering_id,
            )
        )
        for row in existing.scalars().all():
            await self.db.delete(row)

        # Insert new
        for region_id in region_ids:
            link = ServiceOfferingRegion(
                service_offering_id=offering.id,
                delivery_region_id=region_id,
            )
            self.db.add(link)

        await self.db.flush()
        return region_ids

    async def get_offering_regions(
        self, offering_id: str
    ) -> list[str]:
        """Return delivery region IDs linked to an offering."""
        result = await self.db.execute(
            select(ServiceOfferingRegion.delivery_region_id).where(
                ServiceOfferingRegion.service_offering_id == offering_id,
            )
        )
        return [str(row) for row in result.scalars().all()]

    # ── Offering CI Classes ───────────────────────────────────────────

    async def set_offering_ci_classes(
        self, offering_id: str, tenant_id: str, ci_class_ids: list[str]
    ) -> list[str]:
        """Replace all CI class links for an offering (delete + insert)."""
        offering = await self.get_offering(offering_id, tenant_id)
        if not offering:
            raise CatalogServiceError("Service offering not found", "NOT_FOUND")

        # Delete existing
        existing = await self.db.execute(
            select(ServiceOfferingCIClass).where(
                ServiceOfferingCIClass.service_offering_id == offering_id,
            )
        )
        for row in existing.scalars().all():
            await self.db.delete(row)

        # Insert new
        for ci_class_id in ci_class_ids:
            link = ServiceOfferingCIClass(
                service_offering_id=offering.id,
                ci_class_id=ci_class_id,
            )
            self.db.add(link)

        await self.db.flush()
        return ci_class_ids

    async def get_offering_ci_classes(
        self, offering_id: str
    ) -> list[str]:
        """Return CI class IDs linked to an offering."""
        result = await self.db.execute(
            select(ServiceOfferingCIClass.ci_class_id).where(
                ServiceOfferingCIClass.service_offering_id == offering_id,
            )
        )
        return [str(row) for row in result.scalars().all()]

    # ── Distinct Categories ───────────────────────────────────────────

    async def list_distinct_categories(
        self, tenant_id: str
    ) -> list[str]:
        """Return distinct non-null categories for a tenant's offerings."""
        result = await self.db.execute(
            select(ServiceOffering.category)
            .where(
                ServiceOffering.tenant_id == tenant_id,
                ServiceOffering.deleted_at.is_(None),
                ServiceOffering.category.isnot(None),
                ServiceOffering.category != "",
            )
            .distinct()
            .order_by(ServiceOffering.category)
        )
        return [str(row) for row in result.scalars().all()]

    # ── Price Lists ───────────────────────────────────────────────────

    async def get_price_list(
        self, price_list_id: str, tenant_id: str | None = None
    ) -> PriceList | None:
        stmt = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.deleted_at.is_(None),
        )
        if tenant_id:
            stmt = stmt.where(PriceList.tenant_id == tenant_id)
        stmt = stmt.options(selectinload(PriceList.items))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_price_lists(
        self,
        tenant_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        delivery_region_id: str | None = None,
    ) -> tuple[list[PriceList], int]:
        stmt = select(PriceList).where(PriceList.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (PriceList.tenant_id == tenant_id) | (PriceList.tenant_id.is_(None))
            )
        if status:
            stmt = stmt.where(PriceList.status == status)
        if delivery_region_id:
            stmt = stmt.where(PriceList.delivery_region_id == delivery_region_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(PriceList.items))
        stmt = stmt.order_by(PriceList.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_price_list(
        self, tenant_id: str | None, data: dict
    ) -> PriceList:
        price_list = PriceList(
            tenant_id=tenant_id,
            name=data["name"],
            is_default=data.get("is_default", False),
            delivery_region_id=data.get("delivery_region_id"),
            version_major=1,
            version_minor=0,
            status="draft",
        )
        self.db.add(price_list)
        await self.db.flush()
        # Set group_id = id for the first version in the group
        price_list.group_id = price_list.id
        await self.db.flush()
        return price_list

    async def delete_price_list(
        self, price_list_id: str, tenant_id: str | None
    ) -> bool:
        pl = await self.get_price_list(price_list_id, tenant_id)
        if not pl:
            raise CatalogServiceError("Price list not found", "NOT_FOUND")
        if pl.status == "published":
            raise CatalogServiceError(
                "Published price lists cannot be deleted. Archive it first.",
                "IMMUTABLE",
            )
        pl.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def copy_price_list(
        self,
        source_id: str,
        tenant_id: str | None,
        new_name: str,
        client_tenant_id: str | None = None,
    ) -> PriceList:
        """Copy a price list with all its items."""
        source = await self.get_price_list(source_id)
        if not source:
            raise CatalogServiceError("Source price list not found", "NOT_FOUND")

        target_tenant = client_tenant_id or tenant_id
        new_pl = PriceList(
            tenant_id=target_tenant,
            name=new_name,
            is_default=False,
            cloned_from_price_list_id=source.id if client_tenant_id else None,
        )
        self.db.add(new_pl)
        await self.db.flush()

        for item in source.items or []:
            if item.deleted_at:
                continue
            new_item = PriceListItem(
                price_list_id=new_pl.id,
                service_offering_id=item.service_offering_id,
                provider_sku_id=getattr(item, "provider_sku_id", None),
                activity_definition_id=getattr(item, "activity_definition_id", None),
                markup_percent=getattr(item, "markup_percent", None),
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
            )
            self.db.add(new_item)

        await self.db.flush()

        # Re-fetch with items loaded
        return await self.get_price_list(str(new_pl.id))

    # ── Price List Items ──────────────────────────────────────────────

    async def add_price_item(
        self, price_list_id: str, data: dict
    ) -> PriceListItem:
        pl = await self.get_price_list(price_list_id)
        if not pl:
            raise CatalogServiceError("Price list not found", "NOT_FOUND")
        if pl.status != "draft":
            raise CatalogServiceError(
                "Only draft price lists can be modified", "IMMUTABLE"
            )
        item = PriceListItem(
            price_list_id=price_list_id,
            service_offering_id=data.get("service_offering_id"),
            provider_sku_id=data.get("provider_sku_id"),
            activity_definition_id=data.get("activity_definition_id"),
            markup_percent=data.get("markup_percent"),
            delivery_region_id=data.get("delivery_region_id"),
            coverage_model=data.get("coverage_model"),
            price_per_unit=data["price_per_unit"],
            currency=data.get("currency", "EUR"),
            min_quantity=data.get("min_quantity"),
            max_quantity=data.get("max_quantity"),
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def update_price_item(
        self, item_id: str, data: dict
    ) -> PriceListItem:
        result = await self.db.execute(
            select(PriceListItem)
            .where(
                PriceListItem.id == item_id,
                PriceListItem.deleted_at.is_(None),
            )
            .options(selectinload(PriceListItem.price_list))
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError("Price list item not found", "NOT_FOUND")
        if item.price_list and item.price_list.status != "draft":
            raise CatalogServiceError(
                "Only draft price lists can be modified", "IMMUTABLE"
            )
        for key, val in data.items():
            if hasattr(item, key):
                setattr(item, key, val)
        await self.db.flush()
        return item

    # ── Version Management ──────────────────────────────────────────────

    async def create_price_list_version(
        self, price_list_id: str, bump: str = "minor"
    ) -> PriceList:
        """Clone a price list as a new draft version with bumped major or minor."""
        source = await self.get_price_list(price_list_id)
        if not source:
            raise CatalogServiceError("Source price list not found", "NOT_FOUND")

        group_id = source.group_id or source.id
        if bump == "major":
            new_major = source.version_major + 1
            new_minor = 0
        else:
            new_major = source.version_major
            new_minor = source.version_minor + 1

        new_pl = PriceList(
            tenant_id=source.tenant_id,
            name=source.name,
            is_default=source.is_default,
            group_id=group_id,
            version_major=new_major,
            version_minor=new_minor,
            status="draft",
            delivery_region_id=source.delivery_region_id,
            parent_version_id=source.id,
        )
        self.db.add(new_pl)
        await self.db.flush()

        # Clone items
        for item in source.items or []:
            if item.deleted_at:
                continue
            new_item = PriceListItem(
                price_list_id=new_pl.id,
                service_offering_id=item.service_offering_id,
                provider_sku_id=getattr(item, "provider_sku_id", None),
                activity_definition_id=getattr(item, "activity_definition_id", None),
                markup_percent=getattr(item, "markup_percent", None),
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
            )
            self.db.add(new_item)
        await self.db.flush()

        return await self.get_price_list(str(new_pl.id))

    async def publish_price_list(self, price_list_id: str) -> PriceList:
        """Publish a draft price list; archives the previously published version in the group."""
        result = await self.db.execute(
            select(PriceList).where(
                PriceList.id == price_list_id,
                PriceList.deleted_at.is_(None),
            )
        )
        pl = result.scalar_one_or_none()
        if not pl:
            raise CatalogServiceError("Price list not found", "NOT_FOUND")
        if pl.status != "draft":
            raise CatalogServiceError(
                "Only draft price lists can be published", "INVALID_STATUS"
            )

        # Archive currently published version(s) in same group
        if pl.group_id:
            published = await self.db.execute(
                select(PriceList).where(
                    PriceList.group_id == pl.group_id,
                    PriceList.status == "published",
                    PriceList.deleted_at.is_(None),
                    PriceList.id != pl.id,
                )
            )
            for old in published.scalars().all():
                old.status = "archived"

        pl.status = "published"
        await self.db.flush()
        return pl

    async def archive_price_list(self, price_list_id: str) -> PriceList:
        """Archive a price list."""
        result = await self.db.execute(
            select(PriceList).where(
                PriceList.id == price_list_id,
                PriceList.deleted_at.is_(None),
            )
        )
        pl = result.scalar_one_or_none()
        if not pl:
            raise CatalogServiceError("Price list not found", "NOT_FOUND")
        pl.status = "archived"
        await self.db.flush()
        return pl

    async def list_price_list_versions(
        self, group_id: str
    ) -> list[PriceList]:
        """List all versions of a price list group, newest first."""
        result = await self.db.execute(
            select(PriceList)
            .where(
                PriceList.group_id == group_id,
                PriceList.deleted_at.is_(None),
            )
            .options(selectinload(PriceList.items))
            .order_by(
                PriceList.version_major.desc(),
                PriceList.version_minor.desc(),
            )
        )
        return list(result.scalars().unique().all())

    # ── Tenant Price List Pins ───────────────────────────────────────

    async def pin_tenant_to_price_list(
        self,
        tenant_id: str,
        price_list_id: str,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> TenantPriceListPin:
        """Pin a tenant to a specific price list version for a date range."""
        pin_from = effective_from or date.today()
        pin_to = effective_to or date(2999, 12, 31)

        # Overlap check: find any active pin for this tenant whose date range overlaps
        overlap_stmt = select(TenantPriceListPin).where(
            TenantPriceListPin.tenant_id == tenant_id,
            TenantPriceListPin.deleted_at.is_(None),
            TenantPriceListPin.effective_from <= pin_to,
            TenantPriceListPin.effective_to >= pin_from,
        )
        result = await self.db.execute(overlap_stmt)
        conflict = result.scalar_one_or_none()
        if conflict:
            raise CatalogServiceError(
                "Overlaps with existing price list pin for this tenant",
                "OVERLAP",
            )

        pin = TenantPriceListPin(
            tenant_id=tenant_id,
            price_list_id=price_list_id,
            effective_from=pin_from,
            effective_to=pin_to,
        )
        self.db.add(pin)
        await self.db.flush()
        return pin

    async def unpin_tenant_from_price_list(
        self, tenant_id: str, price_list_id: str
    ) -> bool:
        """Soft-delete a tenant pin."""
        result = await self.db.execute(
            select(TenantPriceListPin).where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.price_list_id == price_list_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError("Pin not found", "NOT_FOUND")
        pin.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_tenant_pins(
        self, tenant_id: str
    ) -> list[TenantPriceListPin]:
        """List all active pins for a tenant."""
        result = await self.db.execute(
            select(TenantPriceListPin)
            .where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
            .options(selectinload(TenantPriceListPin.price_list))
        )
        return list(result.scalars().all())

    async def get_pinned_tenants(
        self, price_list_id: str
    ) -> list[TenantPriceListPin]:
        """List tenants pinned to a specific price list version."""
        result = await self.db.execute(
            select(TenantPriceListPin).where(
                TenantPriceListPin.price_list_id == price_list_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # ── Price List Tenant Assignments & Diff ────────────────────────────

    async def get_price_list_tenant_assignments(
        self, price_list_id: str
    ) -> list[dict]:
        """Return combined pin + clone assignments for a price list."""
        # Pins
        pin_result = await self.db.execute(
            select(TenantPriceListPin).where(
                TenantPriceListPin.price_list_id == price_list_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pins = pin_result.scalars().all()

        # Clones
        clone_result = await self.db.execute(
            select(PriceList)
            .where(
                PriceList.cloned_from_price_list_id == price_list_id,
                PriceList.deleted_at.is_(None),
            )
            .options(selectinload(PriceList.items))
        )
        clones = clone_result.scalars().unique().all()

        # Load source items for diff counts
        source = await self.get_price_list(price_list_id)
        source_keys: set[tuple[str, str, str]] = set()
        if source:
            for item in source.items or []:
                if item.deleted_at:
                    continue
                source_keys.add((
                    str(item.service_offering_id or ""),
                    str(item.provider_sku_id or ""),
                    str(item.activity_definition_id or ""),
                ))

        assignments: list[dict] = []

        for pin in pins:
            assignments.append({
                "tenant_id": str(pin.tenant_id),
                "assignment_type": "pin",
                "price_list_id": str(pin.price_list_id),
                "clone_price_list_id": None,
                "additions": 0,
                "deletions": 0,
                "is_customized": False,
            })

        for clone in clones:
            clone_keys: set[tuple[str, str, str]] = set()
            for item in clone.items or []:
                if item.deleted_at:
                    continue
                clone_keys.add((
                    str(item.service_offering_id or ""),
                    str(item.provider_sku_id or ""),
                    str(item.activity_definition_id or ""),
                ))
            additions = len(clone_keys - source_keys)
            deletions = len(source_keys - clone_keys)
            assignments.append({
                "tenant_id": str(clone.tenant_id),
                "assignment_type": "clone",
                "price_list_id": price_list_id,
                "clone_price_list_id": str(clone.id),
                "additions": additions,
                "deletions": deletions,
                "is_customized": additions > 0 or deletions > 0,
            })

        return assignments

    async def get_price_list_diff(
        self, source_id: str, clone_id: str
    ) -> dict:
        """Compare items between source and clone price lists."""
        source = await self.get_price_list(source_id)
        clone = await self.get_price_list(clone_id)
        if not source:
            raise CatalogServiceError("Source price list not found", "NOT_FOUND")
        if not clone:
            raise CatalogServiceError("Clone price list not found", "NOT_FOUND")

        def item_key(item: PriceListItem) -> str:
            return f"{item.service_offering_id or ''}/{item.provider_sku_id or ''}/{item.activity_definition_id or ''}"

        source_map: dict[str, PriceListItem] = {}
        for item in source.items or []:
            if not item.deleted_at:
                source_map[item_key(item)] = item

        clone_map: dict[str, PriceListItem] = {}
        for item in clone.items or []:
            if not item.deleted_at:
                clone_map[item_key(item)] = item

        source_set = set(source_map.keys())
        clone_set = set(clone_map.keys())

        additions = [clone_map[k] for k in sorted(clone_set - source_set)]
        deletions = [source_map[k] for k in sorted(source_set - clone_set)]
        common = [clone_map[k] for k in sorted(source_set & clone_set)]

        return {
            "source_price_list_id": source_id,
            "clone_price_list_id": clone_id,
            "additions": additions,
            "deletions": deletions,
            "common": common,
        }

    # ── Pricing Engine (Region + Coverage Cascade) ─────────────────────

    async def get_effective_price(
        self,
        tenant_id: str,
        service_offering_id: str,
        delivery_region_id: str | None = None,
        coverage_model: str | None = None,
        as_of: date | None = None,
        price_list_id: str | None = None,
    ) -> dict | None:
        """Calculate the effective price using overlay-aware cascade.

        TIER 1 — Pin overlay items:
          Check 'modify' and 'add' overlays on active pins for this offering.

        TIER 2 — Pinned client-specific price list:
          Via tenant_price_list_pins → published price lists with tenant_id = tenant

        TIER 3 — Pinned region-default price list:
          Via tenant_price_list_pins → published price lists with delivery_region_id = region

        TIER 4 — Global default price list:
          is_default=true, status=published

        Before returning: check region acceptance compliance.
        """
        check_date = as_of or date.today()

        offering = await self.get_offering(service_offering_id, tenant_id)
        if not offering:
            return None

        # Check compliance if region specified
        compliance_status = None
        if delivery_region_id:
            try:
                from app.services.cmdb.region_acceptance_service import (
                    ComplianceViolationError,
                    RegionAcceptanceService,
                )
                acceptance_svc = RegionAcceptanceService(self.db)
                acceptance = await acceptance_svc.get_effective_region_acceptance(
                    tenant_id, delivery_region_id
                )
                compliance_status = acceptance["acceptance_type"]
                if (
                    acceptance["acceptance_type"] == "blocked"
                    and acceptance["is_compliance_enforced"]
                ):
                    return {
                        "service_offering_id": str(offering.id),
                        "service_name": offering.name,
                        "price_per_unit": Decimal("0"),
                        "currency": "EUR",
                        "measuring_unit": offering.measuring_unit,
                        "has_override": False,
                        "discount_percent": None,
                        "delivery_region_id": delivery_region_id,
                        "coverage_model": coverage_model,
                        "compliance_status": "blocked",
                    }
            except Exception:
                logger.warning("Failed to check compliance", exc_info=True)

        # Direct price list lookup — skip cascade when a specific list is given
        if price_list_id:
            direct_item = await self._search_price_item_in_list(
                price_list_id, service_offering_id, delivery_region_id, coverage_model
            )
            if direct_item:
                return {
                    "service_offering_id": str(offering.id),
                    "service_name": offering.name,
                    "price_per_unit": direct_item.price_per_unit,
                    "currency": direct_item.currency,
                    "measuring_unit": offering.measuring_unit,
                    "has_override": False,
                    "discount_percent": None,
                    "delivery_region_id": str(direct_item.delivery_region_id) if direct_item.delivery_region_id else None,
                    "coverage_model": direct_item.coverage_model,
                    "compliance_status": compliance_status,
                    "source_type": "direct_price_list",
                    "markup_percent": getattr(direct_item, "markup_percent", None),
                    "price_list_id": price_list_id,
                }
            # Fall through to cascade if not found in the specific list

        # TIER 1: Check 'modify' overlay items on active pins
        modify_result = await self.db.execute(
            select(PriceListOverlayItem)
            .join(TenantPriceListPin, PriceListOverlayItem.pin_id == TenantPriceListPin.id)
            .join(PriceListItem, PriceListOverlayItem.base_item_id == PriceListItem.id)
            .where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
                TenantPriceListPin.effective_from <= check_date,
                TenantPriceListPin.effective_to >= check_date,
                PriceListOverlayItem.deleted_at.is_(None),
                PriceListOverlayItem.overlay_action == "modify",
                PriceListItem.service_offering_id == service_offering_id,
            )
        )
        for overlay in modify_result.scalars().all():
            o_region = str(overlay.delivery_region_id) if overlay.delivery_region_id else None
            o_coverage = overlay.coverage_model
            if self._overlay_matches(o_region, o_coverage, delivery_region_id, coverage_model):
                effective_price = overlay.price_per_unit
                if overlay.discount_percent:
                    effective_price = effective_price * (
                        Decimal("1") - overlay.discount_percent / Decimal("100")
                    )
                return {
                    "service_offering_id": str(offering.id),
                    "service_name": offering.name,
                    "price_per_unit": effective_price,
                    "currency": overlay.currency or "EUR",
                    "measuring_unit": offering.measuring_unit,
                    "has_override": True,
                    "discount_percent": overlay.discount_percent,
                    "delivery_region_id": o_region,
                    "coverage_model": o_coverage,
                    "compliance_status": compliance_status,
                }

        # Check 'add' overlay items that target this offering directly
        add_result = await self.db.execute(
            select(PriceListOverlayItem)
            .join(TenantPriceListPin, PriceListOverlayItem.pin_id == TenantPriceListPin.id)
            .where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
                TenantPriceListPin.effective_from <= check_date,
                TenantPriceListPin.effective_to >= check_date,
                PriceListOverlayItem.deleted_at.is_(None),
                PriceListOverlayItem.overlay_action == "add",
                PriceListOverlayItem.service_offering_id == service_offering_id,
            )
        )
        for overlay in add_result.scalars().all():
            o_region = str(overlay.delivery_region_id) if overlay.delivery_region_id else None
            o_coverage = overlay.coverage_model
            if self._overlay_matches(o_region, o_coverage, delivery_region_id, coverage_model):
                return {
                    "service_offering_id": str(offering.id),
                    "service_name": offering.name,
                    "price_per_unit": overlay.price_per_unit,
                    "currency": overlay.currency or "EUR",
                    "measuring_unit": offering.measuring_unit,
                    "has_override": True,
                    "discount_percent": overlay.discount_percent,
                    "delivery_region_id": o_region,
                    "coverage_model": o_coverage,
                    "compliance_status": compliance_status,
                }

        # TIER 2-4: Price list items via pinned lists and defaults
        price_item = await self._find_price_item(
            tenant_id, service_offering_id, delivery_region_id,
            coverage_model,
        )
        if price_item:
            return {
                "service_offering_id": str(offering.id),
                "service_name": offering.name,
                "price_per_unit": price_item.price_per_unit,
                "currency": price_item.currency,
                "measuring_unit": offering.measuring_unit,
                "has_override": False,
                "discount_percent": None,
                "delivery_region_id": str(price_item.delivery_region_id) if price_item.delivery_region_id else None,
                "coverage_model": price_item.coverage_model,
                "compliance_status": compliance_status,
            }

        return None

    def _overlay_matches(
        self,
        overlay_region: str | None,
        overlay_coverage: str | None,
        requested_region: str | None,
        requested_coverage: str | None,
    ) -> bool:
        """Check if overlay's region/coverage matches the request."""
        if overlay_region and overlay_region != requested_region:
            return False
        if overlay_coverage and overlay_coverage != requested_coverage:
            return False
        return True

    async def _find_price_item(
        self,
        tenant_id: str,
        service_offering_id: str,
        delivery_region_id: str | None,
        coverage_model: str | None,
    ) -> PriceListItem | None:
        """Find best matching price list item using 4-tier specificity cascade.

        TIER 2: Pinned client-specific price lists (tenant_id matches, pinned)
        TIER 3: Pinned region-default price lists (delivery_region_id matches, pinned)
        TIER 4: Global default price lists (is_default=true)

        Each tier checks 4 specificity levels: region+coverage → region → coverage → base.
        All price list tiers filter by status='published'.
        """
        specificity_levels = []
        if delivery_region_id and coverage_model:
            specificity_levels.append((delivery_region_id, coverage_model))
        if delivery_region_id:
            specificity_levels.append((delivery_region_id, None))
        if coverage_model:
            specificity_levels.append((None, coverage_model))
        specificity_levels.append((None, None))

        # Get pinned price list IDs for this tenant
        pin_result = await self.db.execute(
            select(TenantPriceListPin.price_list_id).where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pinned_ids = [row for row in pin_result.scalars().all()]

        # TIER 2: Pinned client-specific lists (tenant_id matches, no region default)
        if pinned_ids:
            for region_val, coverage_val in specificity_levels:
                item = await self._search_price_item(
                    service_offering_id, region_val, coverage_val,
                    extra_filters=[
                        PriceList.id.in_(pinned_ids),
                        PriceList.tenant_id == tenant_id,
                        PriceList.status == "published",
                    ],
                )
                if item:
                    return item

        # TIER 3: Pinned region-default lists (delivery_region_id matches)
        if pinned_ids and delivery_region_id:
            for region_val, coverage_val in specificity_levels:
                item = await self._search_price_item(
                    service_offering_id, region_val, coverage_val,
                    extra_filters=[
                        PriceList.id.in_(pinned_ids),
                        PriceList.delivery_region_id == delivery_region_id,
                        PriceList.status == "published",
                    ],
                )
                if item:
                    return item

        # TIER 4: Global default price lists (is_default=true, published)
        for region_val, coverage_val in specificity_levels:
            item = await self._search_price_item(
                service_offering_id, region_val, coverage_val,
                extra_filters=[
                    PriceList.is_default.is_(True),
                    PriceList.status == "published",
                ],
            )
            if item:
                return item

        # Fallback: legacy price lists without status (treat as published)
        for region_val, coverage_val in specificity_levels:
            item = await self._search_price_item(
                service_offering_id, region_val, coverage_val,
                extra_filters=[
                    PriceList.is_default.is_(True),
                    PriceList.status.is_(None) | (PriceList.status == "published"),
                ],
            )
            if item:
                return item

        return None

    async def get_offering_cost_breakdown(
        self,
        tenant_id: str,
        offering_id: str,
        delivery_region_id: str | None = None,
        coverage_model: str | None = None,
        price_list_id: str | None = None,
    ) -> list[dict]:
        """Return cost breakdown for an offering: list of (sku/activity, price, markup)."""
        from app.models.cmdb.provider_sku import ProviderSku, ServiceOfferingSku

        # Get SKUs linked to the offering
        result = await self.db.execute(
            select(ServiceOfferingSku, ProviderSku)
            .join(ProviderSku, ServiceOfferingSku.provider_sku_id == ProviderSku.id)
            .where(
                ServiceOfferingSku.service_offering_id == offering_id,
                ServiceOfferingSku.deleted_at.is_(None),
                ProviderSku.deleted_at.is_(None),
            )
            .order_by(ServiceOfferingSku.sort_order)
        )
        rows = result.all()

        breakdown = []
        for offering_sku, sku in rows:
            # Try to find SKU-level pricing
            sku_price = await self._find_sku_price(
                tenant_id, str(sku.id), delivery_region_id, coverage_model,
                price_list_id=price_list_id,
            )
            price_per_unit = sku_price.price_per_unit if sku_price else (sku.unit_cost or Decimal("0"))
            markup = getattr(sku_price, "markup_percent", None) if sku_price else None

            breakdown.append({
                "source_type": "sku",
                "source_id": str(sku.id),
                "source_name": sku.display_name or sku.name,
                "quantity": offering_sku.default_quantity,
                "is_required": offering_sku.is_required,
                "price_per_unit": price_per_unit,
                "currency": getattr(sku_price, "currency", sku.cost_currency) if sku_price else sku.cost_currency,
                "measuring_unit": sku.measuring_unit,
                "markup_percent": markup,
            })

        return breakdown

    async def _find_sku_price(
        self,
        tenant_id: str,
        sku_id: str,
        delivery_region_id: str | None,
        coverage_model: str | None,
        price_list_id: str | None = None,
    ) -> PriceListItem | None:
        """Find a price list item for a specific provider SKU."""
        # Direct price list lookup (no status filter — supports drafts)
        if price_list_id:
            result = await self.db.execute(
                select(PriceListItem)
                .join(PriceList)
                .where(
                    PriceList.id == price_list_id,
                    PriceList.deleted_at.is_(None),
                    PriceListItem.provider_sku_id == sku_id,
                    PriceListItem.deleted_at.is_(None),
                )
                .order_by(PriceList.created_at.desc())
                .limit(1)
            )
            item = result.scalar_one_or_none()
            if item:
                return item

        pin_result = await self.db.execute(
            select(TenantPriceListPin.price_list_id).where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pinned_ids = [row for row in pin_result.scalars().all()]

        # Search pinned lists then defaults
        for extra_filters in [
            [PriceList.id.in_(pinned_ids), PriceList.status == "published"] if pinned_ids else None,
            [PriceList.is_default.is_(True), PriceList.status == "published"],
        ]:
            if extra_filters is None:
                continue
            result = await self.db.execute(
                select(PriceListItem)
                .join(PriceList)
                .where(
                    PriceList.deleted_at.is_(None),
                    PriceListItem.provider_sku_id == sku_id,
                    PriceListItem.deleted_at.is_(None),
                    *extra_filters,
                )
                .order_by(PriceList.created_at.desc())
                .limit(1)
            )
            item = result.scalar_one_or_none()
            if item:
                return item
        return None

    async def _search_price_item(
        self,
        service_offering_id: str,
        region_val: str | None,
        coverage_val: str | None,
        extra_filters: list,
    ) -> PriceListItem | None:
        """Search for a price list item with given filters and specificity."""
        base_filters = [
            PriceList.deleted_at.is_(None),
            PriceListItem.service_offering_id == service_offering_id,
            PriceListItem.deleted_at.is_(None),
            *extra_filters,
        ]

        if region_val:
            base_filters.append(PriceListItem.delivery_region_id == region_val)
        else:
            base_filters.append(PriceListItem.delivery_region_id.is_(None))

        if coverage_val:
            base_filters.append(PriceListItem.coverage_model == coverage_val)
        else:
            base_filters.append(PriceListItem.coverage_model.is_(None))

        result = await self.db.execute(
            select(PriceListItem)
            .join(PriceList)
            .where(*base_filters)
            .order_by(PriceList.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _search_price_item_in_list(
        self,
        price_list_id: str,
        service_offering_id: str,
        delivery_region_id: str | None,
        coverage_model: str | None,
    ) -> PriceListItem | None:
        """Search a specific price list with 4-level specificity cascade.

        No status filter — allows draft simulation.
        """
        specificity_levels = []
        if delivery_region_id and coverage_model:
            specificity_levels.append((delivery_region_id, coverage_model))
        if delivery_region_id:
            specificity_levels.append((delivery_region_id, None))
        if coverage_model:
            specificity_levels.append((None, coverage_model))
        specificity_levels.append((None, None))

        for region_val, coverage_val in specificity_levels:
            filters = [
                PriceList.id == price_list_id,
                PriceList.deleted_at.is_(None),
                PriceListItem.service_offering_id == service_offering_id,
                PriceListItem.deleted_at.is_(None),
            ]
            if region_val:
                filters.append(PriceListItem.delivery_region_id == region_val)
            else:
                filters.append(PriceListItem.delivery_region_id.is_(None))

            if coverage_val:
                filters.append(PriceListItem.coverage_model == coverage_val)
            else:
                filters.append(PriceListItem.coverage_model.is_(None))

            result = await self.db.execute(
                select(PriceListItem)
                .join(PriceList)
                .where(*filters)
                .limit(1)
            )
            item = result.scalar_one_or_none()
            if item:
                return item
        return None

    async def get_ci_count_for_offering(
        self,
        tenant_id: str,
        offering_id: str,
    ) -> int:
        """Count CIs in a tenant matching an offering's linked CI classes."""
        from app.models.cmdb.ci import ConfigurationItem

        # Get CI class IDs linked to the offering
        class_result = await self.db.execute(
            select(ServiceOfferingCIClass.ci_class_id).where(
                ServiceOfferingCIClass.service_offering_id == offering_id,
            )
        )
        ci_class_ids = [row for row in class_result.scalars().all()]
        if not ci_class_ids:
            return 0

        count_result = await self.db.execute(
            select(func.count()).select_from(
                select(ConfigurationItem.id).where(
                    ConfigurationItem.tenant_id == tenant_id,
                    ConfigurationItem.ci_class_id.in_(ci_class_ids),
                    ConfigurationItem.lifecycle_state.in_(
                        ["planned", "active", "maintenance"]
                    ),
                    ConfigurationItem.deleted_at.is_(None),
                ).subquery()
            )
        )
        return count_result.scalar() or 0
