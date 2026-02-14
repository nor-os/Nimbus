"""
Overview: Provider SKU service — CRUD for provider SKUs and offering-SKU composition.
Architecture: Provider SKU management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.provider_sku
Concepts: Provider SKUs represent granular billable units. Offering-SKU composition links
    service offerings to their infrastructure SKU components.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.provider_sku import ProviderSku, ServiceOfferingSku
from app.services.cmdb.catalog_service import CatalogServiceError


class SkuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Provider SKU CRUD ────────────────────────────────────────────

    async def create_sku(self, data: dict) -> ProviderSku:
        sku = ProviderSku(
            provider_id=data["provider_id"],
            external_sku_id=data["external_sku_id"],
            name=data["name"],
            display_name=data.get("display_name"),
            description=data.get("description"),
            ci_class_id=data.get("ci_class_id"),
            measuring_unit=data.get("measuring_unit", "month"),
            category=data.get("category"),
            unit_cost=data.get("unit_cost"),
            cost_currency=data.get("cost_currency", "EUR"),
            attributes=data.get("attributes"),
            semantic_type_id=data.get("semantic_type_id"),
            resource_type=data.get("resource_type"),
        )
        self.db.add(sku)
        await self.db.flush()
        return sku

    async def get_sku(self, sku_id: str) -> ProviderSku | None:
        result = await self.db.execute(
            select(ProviderSku).where(
                ProviderSku.id == sku_id,
                ProviderSku.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_skus(
        self,
        provider_id: str | None = None,
        category: str | None = None,
        semantic_type_id: str | None = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProviderSku], int]:
        stmt = select(ProviderSku).where(ProviderSku.deleted_at.is_(None))
        if provider_id:
            stmt = stmt.where(ProviderSku.provider_id == provider_id)
        if category:
            stmt = stmt.where(ProviderSku.category == category)
        if semantic_type_id:
            stmt = stmt.where(ProviderSku.semantic_type_id == semantic_type_id)
        if active_only:
            stmt = stmt.where(ProviderSku.is_active.is_(True))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(ProviderSku.name).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_sku(self, sku_id: str, data: dict) -> ProviderSku:
        sku = await self.get_sku(sku_id)
        if not sku:
            raise CatalogServiceError("Provider SKU not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(sku, key) and val is not None:
                setattr(sku, key, val)
        await self.db.flush()
        return sku

    async def deactivate_sku(self, sku_id: str) -> ProviderSku:
        sku = await self.get_sku(sku_id)
        if not sku:
            raise CatalogServiceError("Provider SKU not found", "NOT_FOUND")
        sku.is_active = False
        await self.db.flush()
        return sku

    # ── Offering-SKU Composition ─────────────────────────────────────

    async def add_sku_to_offering(
        self,
        service_offering_id: str,
        provider_sku_id: str,
        default_quantity: int = 1,
        is_required: bool = True,
        sort_order: int = 0,
    ) -> ServiceOfferingSku:
        link = ServiceOfferingSku(
            service_offering_id=service_offering_id,
            provider_sku_id=provider_sku_id,
            default_quantity=default_quantity,
            is_required=is_required,
            sort_order=sort_order,
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def remove_sku_from_offering(
        self, link_id: str
    ) -> bool:
        result = await self.db.execute(
            select(ServiceOfferingSku).where(
                ServiceOfferingSku.id == link_id,
                ServiceOfferingSku.deleted_at.is_(None),
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise CatalogServiceError("Offering-SKU link not found", "NOT_FOUND")
        link.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_offering_skus(
        self, service_offering_id: str
    ) -> list[ServiceOfferingSku]:
        result = await self.db.execute(
            select(ServiceOfferingSku)
            .where(
                ServiceOfferingSku.service_offering_id == service_offering_id,
                ServiceOfferingSku.deleted_at.is_(None),
            )
            .order_by(ServiceOfferingSku.sort_order)
        )
        return list(result.scalars().all())
