"""
Overview: Estimation engine — create, update, and manage service estimations with
    auto-populated line items, margin calculation, and approval workflow.
Architecture: Service delivery estimation with profitability analysis (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.estimation, app.services.cmdb.rate_card_service,
    app.services.cmdb.activity_service, app.services.cmdb.region_acceptance_service
Concepts: Estimations aggregate activity costs against sell prices. Status workflow:
    draft → submitted → approved/rejected. Compliance validated on creation.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.activity import (
    ActivityTemplate,
    ServiceProcess,
    ServiceProcessAssignment,
    ProcessActivityLink,
)
from app.models.cmdb.estimation import EstimationLineItem, ServiceEstimation
from app.services.cmdb.rate_card_service import RateCardService
from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

logger = logging.getLogger(__name__)


class EstimationServiceError(Exception):
    def __init__(self, message: str, code: str = "ESTIMATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class EstimationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_estimation(
        self, estimation_id: str, tenant_id: str
    ) -> ServiceEstimation | None:
        result = await self.db.execute(
            select(ServiceEstimation)
            .where(
                ServiceEstimation.id == estimation_id,
                ServiceEstimation.tenant_id == tenant_id,
                ServiceEstimation.deleted_at.is_(None),
            )
            .options(selectinload(ServiceEstimation.line_items))
        )
        return result.scalar_one_or_none()

    async def list_estimations(
        self,
        tenant_id: str,
        client_tenant_id: str | None = None,
        service_offering_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceEstimation], int]:
        stmt = select(ServiceEstimation).where(
            ServiceEstimation.tenant_id == tenant_id,
            ServiceEstimation.deleted_at.is_(None),
        )
        if client_tenant_id:
            stmt = stmt.where(ServiceEstimation.client_tenant_id == client_tenant_id)
        if service_offering_id:
            stmt = stmt.where(ServiceEstimation.service_offering_id == service_offering_id)
        if status:
            stmt = stmt.where(ServiceEstimation.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ServiceEstimation.line_items))
        stmt = stmt.order_by(ServiceEstimation.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_estimation(
        self, tenant_id: str, data: dict
    ) -> ServiceEstimation:
        # Check compliance if region specified
        region_id = data.get("delivery_region_id")
        if region_id:
            acceptance_svc = RegionAcceptanceService(self.db)
            await acceptance_svc.check_compliance(
                data["client_tenant_id"], str(region_id)
            )

        # Auto-resolve sell price from pricing engine when not explicitly given
        sell_price = data.get("sell_price_per_unit", Decimal("0"))
        price_list_id_val = data.get("price_list_id")

        if sell_price == 0 or sell_price is None:
            try:
                from app.services.cmdb.catalog_service import CatalogService
                catalog_svc = CatalogService(self.db)
                price = await catalog_svc.get_effective_price(
                    data["client_tenant_id"],
                    data["service_offering_id"],
                    delivery_region_id=str(region_id) if region_id else None,
                    coverage_model=data.get("coverage_model"),
                    price_list_id=str(price_list_id_val) if price_list_id_val else None,
                )
                if price:
                    sell_price = price["price_per_unit"]
            except Exception:
                logger.warning("Failed to auto-resolve sell price", exc_info=True)

        # Auto-resolve quantity from CI count when not explicitly given
        quantity = data.get("quantity", Decimal("1"))
        if quantity == Decimal("1"):
            try:
                from app.services.cmdb.catalog_service import CatalogService
                catalog_svc = CatalogService(self.db)
                ci_count = await catalog_svc.get_ci_count_for_offering(
                    data["client_tenant_id"], data["service_offering_id"]
                )
                if ci_count > 0:
                    quantity = Decimal(str(ci_count))
            except Exception:
                logger.warning("Failed to resolve CI count", exc_info=True)

        estimation = ServiceEstimation(
            tenant_id=tenant_id,
            client_tenant_id=data["client_tenant_id"],
            service_offering_id=data["service_offering_id"],
            delivery_region_id=region_id,
            coverage_model=data.get("coverage_model"),
            price_list_id=price_list_id_val,
            quantity=quantity,
            sell_price_per_unit=sell_price or Decimal("0"),
            sell_currency=data.get("sell_currency", "EUR"),
        )
        self.db.add(estimation)
        await self.db.flush()

        # Auto-populate line items from activity template + rate cards
        await self._auto_populate_line_items(
            estimation, tenant_id, region_id
        )

        # Calculate totals
        await self._recalculate(estimation)

        return estimation

    async def update_estimation(
        self, estimation_id: str, tenant_id: str, data: dict
    ) -> ServiceEstimation:
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "draft":
            raise EstimationServiceError(
                "Only draft estimations can be updated", "INVALID_STATUS"
            )

        price_list_changed = (
            "price_list_id" in data
            and data["price_list_id"] != estimation.price_list_id
        )

        for key, val in data.items():
            if hasattr(estimation, key) and key not in ("id", "tenant_id", "status"):
                setattr(estimation, key, val)

        # Re-resolve sell price when price_list_id changes and no explicit sell price
        if price_list_changed and "sell_price_per_unit" not in data:
            try:
                from app.services.cmdb.catalog_service import CatalogService
                catalog_svc = CatalogService(self.db)
                price = await catalog_svc.get_effective_price(
                    str(estimation.client_tenant_id),
                    str(estimation.service_offering_id),
                    delivery_region_id=str(estimation.delivery_region_id) if estimation.delivery_region_id else None,
                    coverage_model=estimation.coverage_model,
                    price_list_id=str(estimation.price_list_id) if estimation.price_list_id else None,
                )
                if price:
                    estimation.sell_price_per_unit = price["price_per_unit"]
            except Exception:
                logger.warning("Failed to re-resolve sell price", exc_info=True)

        await self._recalculate(estimation)
        return estimation

    async def add_line_item(
        self, estimation_id: str, tenant_id: str, data: dict
    ) -> EstimationLineItem:
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")

        hours = Decimal(str(data["estimated_hours"]))
        staff_profile_id = data["staff_profile_id"]
        delivery_region_id = data["delivery_region_id"]

        # Auto-resolve rate card
        rate_card_id = data.get("rate_card_id")
        hourly_rate = data.get("hourly_rate")
        rate_currency = data.get("rate_currency", "EUR")

        if hourly_rate is None:
            rate_svc = RateCardService(self.db)
            rate_card = await rate_svc.get_effective_rate(
                tenant_id, str(staff_profile_id), str(delivery_region_id)
            )
            if rate_card:
                rate_card_id = rate_card.id
                hourly_rate = rate_card.hourly_cost
                rate_currency = rate_card.currency
            else:
                hourly_rate = Decimal("0")

        rate = Decimal(str(hourly_rate))
        line_cost = hours * rate

        item = EstimationLineItem(
            estimation_id=estimation_id,
            activity_definition_id=data.get("activity_definition_id"),
            rate_card_id=rate_card_id,
            name=data["name"],
            staff_profile_id=staff_profile_id,
            delivery_region_id=delivery_region_id,
            estimated_hours=hours,
            hourly_rate=rate,
            rate_currency=rate_currency,
            line_cost=line_cost,
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(item)
        await self.db.flush()

        await self._recalculate(estimation)
        return item

    async def update_line_item(
        self, item_id: str, data: dict
    ) -> EstimationLineItem:
        result = await self.db.execute(
            select(EstimationLineItem).where(
                EstimationLineItem.id == item_id,
                EstimationLineItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise EstimationServiceError("Line item not found", "NOT_FOUND")

        for key, val in data.items():
            if hasattr(item, key):
                setattr(item, key, val)

        item.line_cost = item.estimated_hours * item.hourly_rate
        await self.db.flush()

        # Recalculate parent estimation
        est_result = await self.db.execute(
            select(ServiceEstimation)
            .where(ServiceEstimation.id == item.estimation_id)
            .options(selectinload(ServiceEstimation.line_items))
        )
        estimation = est_result.scalar_one_or_none()
        if estimation:
            await self._recalculate(estimation)

        return item

    async def delete_line_item(self, item_id: str) -> bool:
        result = await self.db.execute(
            select(EstimationLineItem).where(
                EstimationLineItem.id == item_id,
                EstimationLineItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise EstimationServiceError("Line item not found", "NOT_FOUND")

        estimation_id = item.estimation_id
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()

        est_result = await self.db.execute(
            select(ServiceEstimation)
            .where(ServiceEstimation.id == estimation_id)
            .options(selectinload(ServiceEstimation.line_items))
        )
        estimation = est_result.scalar_one_or_none()
        if estimation:
            await self._recalculate(estimation)

        return True

    async def submit_estimation(
        self, estimation_id: str, tenant_id: str
    ) -> ServiceEstimation:
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "draft":
            raise EstimationServiceError(
                "Only draft estimations can be submitted", "INVALID_STATUS"
            )
        estimation.status = "submitted"
        await self.db.flush()
        return estimation

    async def approve_estimation(
        self, estimation_id: str, tenant_id: str, approved_by: str
    ) -> ServiceEstimation:
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "submitted":
            raise EstimationServiceError(
                "Only submitted estimations can be approved", "INVALID_STATUS"
            )
        estimation.status = "approved"
        estimation.approved_by = approved_by
        estimation.approved_at = datetime.now(UTC)
        await self.db.flush()
        return estimation

    async def reject_estimation(
        self, estimation_id: str, tenant_id: str
    ) -> ServiceEstimation:
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "submitted":
            raise EstimationServiceError(
                "Only submitted estimations can be rejected", "INVALID_STATUS"
            )
        estimation.status = "rejected"
        await self.db.flush()
        return estimation

    # ── Process import & rate refresh ────────────────────────────────

    async def import_process_to_estimation(
        self,
        estimation_id: str,
        tenant_id: str,
        process_id: str,
        delivery_region_id: str | None = None,
    ) -> ServiceEstimation:
        """Import line items from a process into an existing draft estimation."""
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "draft":
            raise EstimationServiceError(
                "Only draft estimations can be modified", "INVALID_STATUS"
            )

        region_id = delivery_region_id or (
            str(estimation.delivery_region_id) if estimation.delivery_region_id else None
        )

        await self._import_process_line_items(
            estimation, tenant_id, process_id, region_id
        )
        await self._recalculate(estimation)
        return estimation

    async def refresh_estimation_rates(
        self, estimation_id: str, tenant_id: str
    ) -> ServiceEstimation:
        """Re-resolve rate cards for all line items in a draft estimation."""
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "draft":
            raise EstimationServiceError(
                "Only draft estimations can be modified", "INVALID_STATUS"
            )

        rate_svc = RateCardService(self.db)

        for item in estimation.line_items or []:
            if item.deleted_at:
                continue

            rate_card = await rate_svc.get_effective_rate(
                tenant_id,
                str(item.staff_profile_id),
                str(item.delivery_region_id),
            )
            if rate_card:
                item.rate_card_id = rate_card.id
                item.hourly_rate = rate_card.hourly_cost
                item.rate_currency = rate_card.currency
            else:
                item.rate_card_id = None

            item.line_cost = item.estimated_hours * item.hourly_rate

        await self.db.flush()
        await self._recalculate(estimation)
        return estimation

    async def refresh_estimation_prices(
        self, estimation_id: str, tenant_id: str
    ) -> ServiceEstimation:
        """Re-resolve sell price from pricing engine using estimation's price_list_id."""
        estimation = await self.get_estimation(estimation_id, tenant_id)
        if not estimation:
            raise EstimationServiceError("Estimation not found", "NOT_FOUND")
        if estimation.status != "draft":
            raise EstimationServiceError(
                "Only draft estimations can be modified", "INVALID_STATUS"
            )

        try:
            from app.services.cmdb.catalog_service import CatalogService
            catalog_svc = CatalogService(self.db)
            price = await catalog_svc.get_effective_price(
                str(estimation.client_tenant_id),
                str(estimation.service_offering_id),
                delivery_region_id=str(estimation.delivery_region_id) if estimation.delivery_region_id else None,
                coverage_model=estimation.coverage_model,
                price_list_id=str(estimation.price_list_id) if estimation.price_list_id else None,
            )
            if price:
                estimation.sell_price_per_unit = price["price_per_unit"]
                estimation.sell_currency = price.get("currency", estimation.sell_currency)
        except Exception:
            logger.warning("Failed to refresh sell price", exc_info=True)

        await self.db.flush()
        await self._recalculate(estimation)
        return estimation

    # ── Private helpers ──────────────────────────────────────────────

    async def _auto_populate_line_items(
        self,
        estimation: ServiceEstimation,
        tenant_id: str,
        region_id: str | None,
    ) -> None:
        """Auto-populate line items from the default process assignment."""
        # Find the default process assignment for this offering+coverage
        stmt = select(ServiceProcessAssignment).where(
            ServiceProcessAssignment.tenant_id == tenant_id,
            ServiceProcessAssignment.service_offering_id == estimation.service_offering_id,
            ServiceProcessAssignment.is_default.is_(True),
            ServiceProcessAssignment.deleted_at.is_(None),
        )
        if estimation.coverage_model:
            stmt = stmt.where(
                (ServiceProcessAssignment.coverage_model == estimation.coverage_model)
                | (ServiceProcessAssignment.coverage_model.is_(None))
            )
        result = await self.db.execute(stmt)
        assignment = result.scalar_one_or_none()
        if not assignment:
            return

        await self._import_process_line_items(
            estimation, tenant_id, str(assignment.process_id), region_id
        )

    async def _import_process_line_items(
        self,
        estimation: ServiceEstimation,
        tenant_id: str,
        process_id: str,
        region_id: str | None,
    ) -> None:
        """Import line items from a process → activity links → definitions."""
        # Load process with activity links
        proc_result = await self.db.execute(
            select(ServiceProcess)
            .where(
                ServiceProcess.id == process_id,
                ServiceProcess.deleted_at.is_(None),
            )
            .options(
                selectinload(ServiceProcess.activity_links)
                .selectinload(ProcessActivityLink.activity_template)
                .selectinload(ActivityTemplate.definitions)
            )
        )
        process = proc_result.scalar_one_or_none()
        if not process:
            return

        rate_svc = RateCardService(self.db)
        delivery_region = str(region_id) if region_id else None
        sort_counter = 0

        for link in process.activity_links or []:
            if link.deleted_at:
                continue
            template = link.activity_template
            if not template or template.deleted_at:
                continue

            for defn in template.definitions or []:
                if defn.deleted_at:
                    continue

                hourly_rate = Decimal("0")
                rate_currency = "EUR"
                rate_card_id = None

                if delivery_region:
                    rate_card = await rate_svc.get_effective_rate(
                        tenant_id, str(defn.staff_profile_id), delivery_region
                    )
                    if rate_card:
                        rate_card_id = rate_card.id
                        hourly_rate = rate_card.hourly_cost
                        rate_currency = rate_card.currency

                line_cost = defn.estimated_hours * hourly_rate

                item = EstimationLineItem(
                    estimation_id=estimation.id,
                    activity_definition_id=defn.id,
                    rate_card_id=rate_card_id,
                    name=defn.name,
                    staff_profile_id=defn.staff_profile_id,
                    delivery_region_id=region_id or defn.staff_profile_id,
                    estimated_hours=defn.estimated_hours,
                    hourly_rate=hourly_rate,
                    rate_currency=rate_currency,
                    line_cost=line_cost,
                    sort_order=sort_counter,
                )
                self.db.add(item)
                sort_counter += 1

        await self.db.flush()

    async def _recalculate(self, estimation: ServiceEstimation) -> None:
        """Recalculate estimation totals and margin."""
        # Re-fetch line items
        result = await self.db.execute(
            select(EstimationLineItem).where(
                EstimationLineItem.estimation_id == estimation.id,
                EstimationLineItem.deleted_at.is_(None),
            )
        )
        items = list(result.scalars().all())

        total_cost = sum(item.line_cost for item in items)
        total_sell = estimation.sell_price_per_unit * estimation.quantity

        estimation.total_estimated_cost = total_cost
        estimation.total_sell_price = total_sell
        estimation.margin_amount = total_sell - total_cost
        estimation.margin_percent = (
            (estimation.margin_amount / total_sell * Decimal("100"))
            if total_sell > 0
            else Decimal("0")
        )
        await self.db.flush()
