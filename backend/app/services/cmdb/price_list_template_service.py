"""
Overview: Price list template service — CRUD for price list templates and cloning
    to real price lists for new client onboarding.
Architecture: Service delivery pricing template management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.price_list_template, app.models.cmdb.price_list
Concepts: Templates are blueprints cloneable to real price lists. Cloning creates a PriceList
    with PriceListItems from the template. May also assign region acceptance template.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.price_list import PriceList, PriceListItem
from app.models.cmdb.price_list_template import PriceListTemplate, PriceListTemplateItem

logger = logging.getLogger(__name__)


class PriceListTemplateServiceError(Exception):
    def __init__(self, message: str, code: str = "TEMPLATE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class PriceListTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(self, template_id: str) -> PriceListTemplate | None:
        result = await self.db.execute(
            select(PriceListTemplate)
            .where(
                PriceListTemplate.id == template_id,
                PriceListTemplate.deleted_at.is_(None),
            )
            .options(selectinload(PriceListTemplate.items))
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        tenant_id: str,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[PriceListTemplate], int]:
        stmt = select(PriceListTemplate).where(
            PriceListTemplate.tenant_id == tenant_id,
            PriceListTemplate.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(PriceListTemplate.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(PriceListTemplate.items))
        stmt = stmt.order_by(PriceListTemplate.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_template(
        self, tenant_id: str, data: dict
    ) -> PriceListTemplate:
        template = PriceListTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            region_acceptance_template_id=data.get("region_acceptance_template_id"),
            status=data.get("status", "draft"),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self, template_id: str, data: dict
    ) -> PriceListTemplate:
        template = await self.get_template(template_id)
        if not template:
            raise PriceListTemplateServiceError("Template not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(template, key) and key not in ("id", "tenant_id"):
                setattr(template, key, val)
        await self.db.flush()
        return template

    async def delete_template(self, template_id: str) -> bool:
        template = await self.get_template(template_id)
        if not template:
            raise PriceListTemplateServiceError("Template not found", "NOT_FOUND")
        template.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def add_template_item(
        self, template_id: str, data: dict
    ) -> PriceListTemplateItem:
        item = PriceListTemplateItem(
            template_id=template_id,
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

    async def delete_template_item(self, item_id: str) -> bool:
        result = await self.db.execute(
            select(PriceListTemplateItem).where(
                PriceListTemplateItem.id == item_id,
                PriceListTemplateItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise PriceListTemplateServiceError("Template item not found", "NOT_FOUND")
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def clone_to_price_list(
        self,
        template_id: str,
        tenant_id: str,
    ) -> PriceList:
        template = await self.get_template(template_id)
        if not template:
            raise PriceListTemplateServiceError("Template not found", "NOT_FOUND")

        price_list = PriceList(
            tenant_id=tenant_id,
            name=f"{template.name} (cloned)",
            is_default=False,
        )
        self.db.add(price_list)
        await self.db.flush()

        for tmpl_item in template.items or []:
            if tmpl_item.deleted_at:
                continue
            item = PriceListItem(
                price_list_id=price_list.id,
                service_offering_id=tmpl_item.service_offering_id,
                delivery_region_id=tmpl_item.delivery_region_id,
                coverage_model=tmpl_item.coverage_model,
                price_per_unit=tmpl_item.price_per_unit,
                currency=tmpl_item.currency,
                min_quantity=tmpl_item.min_quantity,
                max_quantity=tmpl_item.max_quantity,
            )
            self.db.add(item)

        await self.db.flush()
        return price_list
