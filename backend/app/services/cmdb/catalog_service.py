"""
Overview: Service catalog service — CRUD for service offerings, price lists, and pricing engine
    with region-aware + coverage-aware specificity cascade.
Architecture: Catalog and pricing management with tenant overrides (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_offering, app.models.cmdb.price_list
Concepts: Service offerings are billable items. Price lists group pricing with date ranges.
    Tenant overrides apply custom pricing or discounts. The pricing engine resolves the effective
    price for a tenant+service combination using a 12-level specificity cascade across
    region, coverage model, and pricing tier (override → tenant list → default list).
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.price_list import PriceList, PriceListItem, TenantPriceOverride
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
    ) -> tuple[list[PriceList], int]:
        stmt = select(PriceList).where(PriceList.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (PriceList.tenant_id == tenant_id) | (PriceList.tenant_id.is_(None))
            )

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
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )
        self.db.add(price_list)
        await self.db.flush()
        return price_list

    async def delete_price_list(
        self, price_list_id: str, tenant_id: str | None
    ) -> bool:
        pl = await self.get_price_list(price_list_id, tenant_id)
        if not pl:
            raise CatalogServiceError("Price list not found", "NOT_FOUND")
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
            effective_from=source.effective_from,
            effective_to=source.effective_to,
        )
        self.db.add(new_pl)
        await self.db.flush()

        for item in source.items or []:
            if item.deleted_at:
                continue
            new_item = PriceListItem(
                price_list_id=new_pl.id,
                service_offering_id=item.service_offering_id,
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
        item = PriceListItem(
            price_list_id=price_list_id,
            service_offering_id=data["service_offering_id"],
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
            select(PriceListItem).where(
                PriceListItem.id == item_id,
                PriceListItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError("Price list item not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(item, key):
                setattr(item, key, val)
        await self.db.flush()
        return item

    # ── Tenant Overrides ──────────────────────────────────────────────

    async def create_override(
        self, tenant_id: str, data: dict
    ) -> TenantPriceOverride:
        override = TenantPriceOverride(
            tenant_id=tenant_id,
            service_offering_id=data["service_offering_id"],
            delivery_region_id=data.get("delivery_region_id"),
            coverage_model=data.get("coverage_model"),
            price_per_unit=data["price_per_unit"],
            discount_percent=data.get("discount_percent"),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )
        self.db.add(override)
        await self.db.flush()
        return override

    async def list_overrides(
        self, tenant_id: str
    ) -> list[TenantPriceOverride]:
        result = await self.db.execute(
            select(TenantPriceOverride)
            .where(
                TenantPriceOverride.tenant_id == tenant_id,
                TenantPriceOverride.deleted_at.is_(None),
            )
            .order_by(TenantPriceOverride.effective_from)
        )
        return list(result.scalars().all())

    async def delete_override(
        self, override_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(TenantPriceOverride).where(
                TenantPriceOverride.id == override_id,
                TenantPriceOverride.tenant_id == tenant_id,
                TenantPriceOverride.deleted_at.is_(None),
            )
        )
        override = result.scalar_one_or_none()
        if not override:
            raise CatalogServiceError("Override not found", "NOT_FOUND")
        override.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Pricing Engine (Region + Coverage Cascade) ─────────────────────

    async def get_effective_price(
        self,
        tenant_id: str,
        service_offering_id: str,
        delivery_region_id: str | None = None,
        coverage_model: str | None = None,
        as_of: date | None = None,
    ) -> dict | None:
        """Calculate the effective price using 12-level specificity cascade.

        TIER 1 — Tenant Overrides:
          1a. (tenant + offering + region + coverage + date)
          1b. (tenant + offering + region + date)
          1c. (tenant + offering + coverage + date)
          1d. (tenant + offering + date)

        TIER 2 — Tenant Price Lists:
          2a-2d: same specificity pattern

        TIER 3 — Default Price Lists:
          3a-3d: same specificity pattern

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

        # TIER 1: Tenant overrides (most specific first)
        override = await self._find_override(
            tenant_id, service_offering_id, delivery_region_id,
            coverage_model, check_date
        )
        if override:
            effective_price = override.price_per_unit
            if override.discount_percent:
                effective_price = effective_price * (
                    Decimal("1") - override.discount_percent / Decimal("100")
                )
            return {
                "service_offering_id": str(offering.id),
                "service_name": offering.name,
                "price_per_unit": effective_price,
                "currency": "EUR",
                "measuring_unit": offering.measuring_unit,
                "has_override": True,
                "discount_percent": override.discount_percent,
                "delivery_region_id": str(override.delivery_region_id) if override.delivery_region_id else None,
                "coverage_model": override.coverage_model,
                "compliance_status": compliance_status,
            }

        # TIER 2 & 3: Price list items (tenant-specific, then default)
        price_item = await self._find_price_item(
            tenant_id, service_offering_id, delivery_region_id,
            coverage_model, check_date
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

    async def _find_override(
        self,
        tenant_id: str,
        service_offering_id: str,
        delivery_region_id: str | None,
        coverage_model: str | None,
        check_date: date,
    ) -> TenantPriceOverride | None:
        """Find best matching override using specificity cascade."""
        base_filters = [
            TenantPriceOverride.tenant_id == tenant_id,
            TenantPriceOverride.service_offering_id == service_offering_id,
            TenantPriceOverride.effective_from <= check_date,
            (TenantPriceOverride.effective_to.is_(None))
            | (TenantPriceOverride.effective_to >= check_date),
            TenantPriceOverride.deleted_at.is_(None),
        ]

        specificity_levels = []
        if delivery_region_id and coverage_model:
            # 1a: region + coverage
            specificity_levels.append([
                TenantPriceOverride.delivery_region_id == delivery_region_id,
                TenantPriceOverride.coverage_model == coverage_model,
            ])
        if delivery_region_id:
            # 1b: region only
            specificity_levels.append([
                TenantPriceOverride.delivery_region_id == delivery_region_id,
                TenantPriceOverride.coverage_model.is_(None),
            ])
        if coverage_model:
            # 1c: coverage only
            specificity_levels.append([
                TenantPriceOverride.delivery_region_id.is_(None),
                TenantPriceOverride.coverage_model == coverage_model,
            ])
        # 1d: generic
        specificity_levels.append([
            TenantPriceOverride.delivery_region_id.is_(None),
            TenantPriceOverride.coverage_model.is_(None),
        ])

        for level_filters in specificity_levels:
            result = await self.db.execute(
                select(TenantPriceOverride)
                .where(*base_filters, *level_filters)
                .order_by(TenantPriceOverride.effective_from.desc())
                .limit(1)
            )
            override = result.scalar_one_or_none()
            if override:
                return override
        return None

    async def _find_price_item(
        self,
        tenant_id: str,
        service_offering_id: str,
        delivery_region_id: str | None,
        coverage_model: str | None,
        check_date: date,
    ) -> PriceListItem | None:
        """Find best matching price list item using specificity cascade."""
        specificity_levels = []
        if delivery_region_id and coverage_model:
            specificity_levels.append(
                (delivery_region_id, coverage_model)
            )
        if delivery_region_id:
            specificity_levels.append((delivery_region_id, None))
        if coverage_model:
            specificity_levels.append((None, coverage_model))
        specificity_levels.append((None, None))

        # Try tenant-specific price lists first, then default
        for is_tenant in [True, False]:
            for region_val, coverage_val in specificity_levels:
                base_filters = [
                    PriceList.effective_from <= check_date,
                    (PriceList.effective_to.is_(None))
                    | (PriceList.effective_to >= check_date),
                    PriceList.deleted_at.is_(None),
                    PriceListItem.service_offering_id == service_offering_id,
                    PriceListItem.deleted_at.is_(None),
                ]
                if is_tenant:
                    base_filters.append(PriceList.tenant_id == tenant_id)
                else:
                    base_filters.append(PriceList.is_default.is_(True))

                if region_val:
                    base_filters.append(
                        PriceListItem.delivery_region_id == region_val
                    )
                else:
                    base_filters.append(
                        PriceListItem.delivery_region_id.is_(None)
                    )

                if coverage_val:
                    base_filters.append(
                        PriceListItem.coverage_model == coverage_val
                    )
                else:
                    base_filters.append(
                        PriceListItem.coverage_model.is_(None)
                    )

                result = await self.db.execute(
                    select(PriceListItem)
                    .join(PriceList)
                    .where(*base_filters)
                    .order_by(PriceList.effective_from.desc())
                    .limit(1)
                )
                item = result.scalar_one_or_none()
                if item:
                    return item

        return None
