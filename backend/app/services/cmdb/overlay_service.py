"""
Overview: Overlay service — CRUD and effective-item resolution for price list and catalog
    overlay items scoped to tenant pins.
Architecture: Pin-scoped overlays modify, add, or exclude base items without cloning
    entire price lists or catalogs (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.price_list_overlay, app.models.cmdb.catalog_overlay,
    app.models.cmdb.price_list, app.models.cmdb.service_catalog,
    app.services.cmdb.catalog_service
Concepts: Overlay items are per-pin modifications. Price list overlays support modify, add,
    and exclude actions. Catalog overlays support include and exclude actions. The effective
    item list merges base items with overlays to produce the tenant-visible view.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.catalog_overlay import CatalogOverlayItem
from app.models.cmdb.price_list import PriceListItem, TenantPriceListPin
from app.models.cmdb.price_list_overlay import PriceListOverlayItem
from app.models.cmdb.service_catalog import TenantCatalogPin
from app.services.cmdb.catalog_service import CatalogServiceError

_VALID_PRICE_LIST_ACTIONS = {"modify", "add", "exclude"}
_VALID_CATALOG_ACTIONS = {"include", "exclude"}

_PRICE_LIST_OVERLAY_FIELDS = {
    "service_offering_id",
    "provider_sku_id",
    "activity_definition_id",
    "delivery_region_id",
    "coverage_model",
    "price_per_unit",
    "currency",
    "markup_percent",
    "discount_percent",
    "min_quantity",
    "max_quantity",
}


class OverlayService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Price List Overlays ──────────────────────────────────────────

    async def create_price_list_overlay(
        self, tenant_id: str, pin_id: str, data: dict
    ) -> PriceListOverlayItem:
        """Create an overlay item on a tenant's price list pin."""
        # Validate pin exists for this tenant
        result = await self.db.execute(
            select(TenantPriceListPin).where(
                TenantPriceListPin.id == pin_id,
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError(
                "Price list pin not found for this tenant", "NOT_FOUND"
            )

        overlay_action = data.get("overlay_action", "")
        if overlay_action not in _VALID_PRICE_LIST_ACTIONS:
            raise CatalogServiceError(
                f"Invalid overlay action '{overlay_action}'. "
                f"Must be one of: {', '.join(sorted(_VALID_PRICE_LIST_ACTIONS))}",
                "INVALID_ACTION",
            )

        if overlay_action in ("modify", "exclude") and not data.get("base_item_id"):
            raise CatalogServiceError(
                "base_item_id is required for modify and exclude actions",
                "MISSING_BASE_ITEM",
            )

        item = PriceListOverlayItem(
            tenant_id=tenant_id,
            pin_id=pin_id,
            overlay_action=overlay_action,
            base_item_id=data.get("base_item_id"),
            service_offering_id=data.get("service_offering_id"),
            provider_sku_id=data.get("provider_sku_id"),
            activity_definition_id=data.get("activity_definition_id"),
            delivery_region_id=data.get("delivery_region_id"),
            coverage_model=data.get("coverage_model"),
            price_per_unit=data.get("price_per_unit"),
            currency=data.get("currency"),
            markup_percent=data.get("markup_percent"),
            discount_percent=data.get("discount_percent"),
            min_quantity=data.get("min_quantity"),
            max_quantity=data.get("max_quantity"),
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_price_list_overlays(
        self, pin_id: str
    ) -> list[PriceListOverlayItem]:
        """List all active overlay items for a price list pin."""
        result = await self.db.execute(
            select(PriceListOverlayItem)
            .where(
                PriceListOverlayItem.pin_id == pin_id,
                PriceListOverlayItem.deleted_at.is_(None),
            )
            .order_by(PriceListOverlayItem.created_at)
        )
        return list(result.scalars().all())

    async def update_price_list_overlay(
        self, item_id: str, tenant_id: str, data: dict
    ) -> PriceListOverlayItem:
        """Update an existing price list overlay item."""
        result = await self.db.execute(
            select(PriceListOverlayItem).where(
                PriceListOverlayItem.id == item_id,
                PriceListOverlayItem.tenant_id == tenant_id,
                PriceListOverlayItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError(
                "Price list overlay item not found", "NOT_FOUND"
            )

        for key, val in data.items():
            if key in _PRICE_LIST_OVERLAY_FIELDS and hasattr(item, key):
                setattr(item, key, val)

        await self.db.flush()
        return item

    async def delete_price_list_overlay(
        self, item_id: str, tenant_id: str
    ) -> bool:
        """Soft-delete a price list overlay item."""
        result = await self.db.execute(
            select(PriceListOverlayItem).where(
                PriceListOverlayItem.id == item_id,
                PriceListOverlayItem.tenant_id == tenant_id,
                PriceListOverlayItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError(
                "Price list overlay item not found", "NOT_FOUND"
            )
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_effective_pin_items(self, pin_id: str) -> list[dict]:
        """Merge base price list items with overlay items for a pin.

        Resolution order:
        1. Start with all base items from the pinned price list.
        2. Apply 'exclude' overlays — remove matching base items.
        3. Apply 'modify' overlays — update price fields on matching base items.
        4. Apply 'add' overlays — append new items with source='overlay'.
        """
        # Load pin with price_list.items eagerly
        result = await self.db.execute(
            select(TenantPriceListPin)
            .where(
                TenantPriceListPin.id == pin_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantPriceListPin.price_list)
                .selectinload(PriceListItem.price_list.__class__.items)  # noqa: type ignore
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError("Price list pin not found", "NOT_FOUND")

        # Load overlay items for this pin
        overlays = await self.list_price_list_overlays(pin_id)

        # Build base item list from price list
        base_items: dict[str, dict] = {}
        for item in (pin.price_list.items or []):
            if getattr(item, "deleted_at", None):
                continue
            base_items[str(item.id)] = {
                "id": str(item.id),
                "service_offering_id": str(item.service_offering_id) if item.service_offering_id else None,
                "provider_sku_id": str(item.provider_sku_id) if item.provider_sku_id else None,
                "activity_definition_id": str(item.activity_definition_id) if item.activity_definition_id else None,
                "delivery_region_id": str(item.delivery_region_id) if item.delivery_region_id else None,
                "coverage_model": item.coverage_model,
                "price_per_unit": item.price_per_unit,
                "currency": item.currency,
                "markup_percent": item.markup_percent,
                "min_quantity": item.min_quantity,
                "max_quantity": item.max_quantity,
                "source": "base",
            }

        # Process overlays
        for overlay in overlays:
            base_id = str(overlay.base_item_id) if overlay.base_item_id else None

            if overlay.overlay_action == "exclude" and base_id:
                base_items.pop(base_id, None)

            elif overlay.overlay_action == "modify" and base_id and base_id in base_items:
                target = base_items[base_id]
                if overlay.price_per_unit is not None:
                    target["price_per_unit"] = overlay.price_per_unit
                if overlay.currency is not None:
                    target["currency"] = overlay.currency
                if overlay.markup_percent is not None:
                    target["markup_percent"] = overlay.markup_percent
                if overlay.discount_percent is not None:
                    target["discount_percent"] = overlay.discount_percent
                if overlay.min_quantity is not None:
                    target["min_quantity"] = overlay.min_quantity
                if overlay.max_quantity is not None:
                    target["max_quantity"] = overlay.max_quantity
                if overlay.coverage_model is not None:
                    target["coverage_model"] = overlay.coverage_model
                if overlay.delivery_region_id is not None:
                    target["delivery_region_id"] = str(overlay.delivery_region_id)

            elif overlay.overlay_action == "add":
                base_items[str(overlay.id)] = {
                    "id": str(overlay.id),
                    "service_offering_id": str(overlay.service_offering_id) if overlay.service_offering_id else None,
                    "provider_sku_id": str(overlay.provider_sku_id) if overlay.provider_sku_id else None,
                    "activity_definition_id": str(overlay.activity_definition_id) if overlay.activity_definition_id else None,
                    "delivery_region_id": str(overlay.delivery_region_id) if overlay.delivery_region_id else None,
                    "coverage_model": overlay.coverage_model,
                    "price_per_unit": overlay.price_per_unit,
                    "currency": overlay.currency,
                    "markup_percent": overlay.markup_percent,
                    "min_quantity": overlay.min_quantity,
                    "max_quantity": overlay.max_quantity,
                    "source": "overlay",
                }

        return list(base_items.values())

    # ── Catalog Overlays ─────────────────────────────────────────────

    async def create_catalog_overlay(
        self, tenant_id: str, pin_id: str, data: dict
    ) -> CatalogOverlayItem:
        """Create an overlay item on a tenant's catalog pin."""
        # Validate pin exists for this tenant
        result = await self.db.execute(
            select(TenantCatalogPin).where(
                TenantCatalogPin.id == pin_id,
                TenantCatalogPin.tenant_id == tenant_id,
                TenantCatalogPin.deleted_at.is_(None),
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError(
                "Catalog pin not found for this tenant", "NOT_FOUND"
            )

        overlay_action = data.get("overlay_action", "")
        if overlay_action not in _VALID_CATALOG_ACTIONS:
            raise CatalogServiceError(
                f"Invalid overlay action '{overlay_action}'. "
                f"Must be one of: {', '.join(sorted(_VALID_CATALOG_ACTIONS))}",
                "INVALID_ACTION",
            )

        if overlay_action == "exclude" and not data.get("base_item_id"):
            raise CatalogServiceError(
                "base_item_id is required for exclude actions",
                "MISSING_BASE_ITEM",
            )

        item = CatalogOverlayItem(
            tenant_id=tenant_id,
            pin_id=pin_id,
            overlay_action=overlay_action,
            base_item_id=data.get("base_item_id"),
            service_offering_id=data.get("service_offering_id"),
            service_group_id=data.get("service_group_id"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_catalog_overlays(
        self, pin_id: str
    ) -> list[CatalogOverlayItem]:
        """List all active overlay items for a catalog pin."""
        result = await self.db.execute(
            select(CatalogOverlayItem)
            .where(
                CatalogOverlayItem.pin_id == pin_id,
                CatalogOverlayItem.deleted_at.is_(None),
            )
            .order_by(CatalogOverlayItem.sort_order)
        )
        return list(result.scalars().all())

    async def delete_catalog_overlay(
        self, item_id: str, tenant_id: str
    ) -> bool:
        """Soft-delete a catalog overlay item."""
        result = await self.db.execute(
            select(CatalogOverlayItem).where(
                CatalogOverlayItem.id == item_id,
                CatalogOverlayItem.tenant_id == tenant_id,
                CatalogOverlayItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError(
                "Catalog overlay item not found", "NOT_FOUND"
            )
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_effective_catalog_items(self, pin_id: str) -> list[dict]:
        """Merge base catalog items with overlay items for a pin.

        Resolution order:
        1. Start with all base items from the pinned catalog.
        2. Apply 'exclude' overlays — remove matching base items.
        3. Apply 'include' overlays — append new items with source='overlay'.
        """
        # Load pin with catalog.items eagerly
        result = await self.db.execute(
            select(TenantCatalogPin)
            .where(
                TenantCatalogPin.id == pin_id,
                TenantCatalogPin.deleted_at.is_(None),
            )
            .options(selectinload(TenantCatalogPin.catalog))
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError("Catalog pin not found", "NOT_FOUND")

        # Load overlay items for this pin
        overlays = await self.list_catalog_overlays(pin_id)

        # Build base item list from catalog
        base_items: dict[str, dict] = {}
        for item in (pin.catalog.items or []):
            base_items[str(item.id)] = {
                "id": str(item.id),
                "service_offering_id": str(item.service_offering_id) if item.service_offering_id else None,
                "service_group_id": str(item.service_group_id) if item.service_group_id else None,
                "sort_order": item.sort_order,
                "source": "base",
            }

        # Process overlays
        for overlay in overlays:
            base_id = str(overlay.base_item_id) if overlay.base_item_id else None

            if overlay.overlay_action == "exclude" and base_id:
                base_items.pop(base_id, None)

            elif overlay.overlay_action == "include":
                base_items[str(overlay.id)] = {
                    "id": str(overlay.id),
                    "service_offering_id": str(overlay.service_offering_id) if overlay.service_offering_id else None,
                    "service_group_id": str(overlay.service_group_id) if overlay.service_group_id else None,
                    "sort_order": overlay.sort_order,
                    "source": "overlay",
                }

        return list(base_items.values())
