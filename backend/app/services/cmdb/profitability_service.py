"""
Overview: Profitability service — aggregation queries on approved estimations for
    per-client, per-region, and per-service profitability analysis.
Architecture: Service delivery profitability reporting (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.estimation
Concepts: Aggregates approved estimations to calculate revenue, cost, and margin
    breakdowns by client, region, and service offering.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.estimation import ServiceEstimation
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class ProfitabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self, tenant_id: str) -> dict:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(ServiceEstimation.total_sell_price), 0),
                func.coalesce(func.sum(ServiceEstimation.total_estimated_cost), 0),
                func.coalesce(func.sum(ServiceEstimation.margin_amount), 0),
                func.count(ServiceEstimation.id),
            ).where(
                ServiceEstimation.tenant_id == tenant_id,
                ServiceEstimation.status == "approved",
                ServiceEstimation.deleted_at.is_(None),
            )
        )
        row = result.one()
        revenue = row[0] or Decimal("0")
        cost = row[1] or Decimal("0")
        margin = row[2] or Decimal("0")
        count = row[3] or 0
        margin_pct = (margin / revenue * Decimal("100")) if revenue > 0 else Decimal("0")

        return {
            "total_revenue": revenue,
            "total_cost": cost,
            "total_margin": margin,
            "margin_percent": margin_pct,
            "estimation_count": count,
        }

    async def get_by_client(self, tenant_id: str) -> list[dict]:
        result = await self.db.execute(
            select(
                ServiceEstimation.client_tenant_id,
                func.coalesce(func.sum(ServiceEstimation.total_sell_price), 0),
                func.coalesce(func.sum(ServiceEstimation.total_estimated_cost), 0),
                func.coalesce(func.sum(ServiceEstimation.margin_amount), 0),
                func.count(ServiceEstimation.id),
            )
            .where(
                ServiceEstimation.tenant_id == tenant_id,
                ServiceEstimation.status == "approved",
                ServiceEstimation.deleted_at.is_(None),
            )
            .group_by(ServiceEstimation.client_tenant_id)
        )
        rows = result.all()
        items = []
        for row in rows:
            revenue = row[1] or Decimal("0")
            cost = row[2] or Decimal("0")
            margin = row[3] or Decimal("0")
            margin_pct = (margin / revenue * Decimal("100")) if revenue > 0 else Decimal("0")

            # Get tenant name
            tenant_result = await self.db.execute(
                select(Tenant.name).where(Tenant.id == row[0])
            )
            tenant_name = tenant_result.scalar_one_or_none() or str(row[0])

            items.append({
                "entity_id": str(row[0]),
                "entity_name": tenant_name,
                "total_revenue": revenue,
                "total_cost": cost,
                "margin_amount": margin,
                "margin_percent": margin_pct,
                "estimation_count": row[4],
            })
        return items

    async def get_by_region(self, tenant_id: str) -> list[dict]:
        from app.models.cmdb.delivery_region import DeliveryRegion

        result = await self.db.execute(
            select(
                ServiceEstimation.delivery_region_id,
                func.coalesce(func.sum(ServiceEstimation.total_sell_price), 0),
                func.coalesce(func.sum(ServiceEstimation.total_estimated_cost), 0),
                func.coalesce(func.sum(ServiceEstimation.margin_amount), 0),
                func.count(ServiceEstimation.id),
            )
            .where(
                ServiceEstimation.tenant_id == tenant_id,
                ServiceEstimation.status == "approved",
                ServiceEstimation.delivery_region_id.isnot(None),
                ServiceEstimation.deleted_at.is_(None),
            )
            .group_by(ServiceEstimation.delivery_region_id)
        )
        rows = result.all()
        items = []
        for row in rows:
            revenue = row[1] or Decimal("0")
            cost = row[2] or Decimal("0")
            margin = row[3] or Decimal("0")
            margin_pct = (margin / revenue * Decimal("100")) if revenue > 0 else Decimal("0")

            region_result = await self.db.execute(
                select(DeliveryRegion.display_name).where(DeliveryRegion.id == row[0])
            )
            region_name = region_result.scalar_one_or_none() or str(row[0])

            items.append({
                "entity_id": str(row[0]),
                "entity_name": region_name,
                "total_revenue": revenue,
                "total_cost": cost,
                "margin_amount": margin,
                "margin_percent": margin_pct,
                "estimation_count": row[4],
            })
        return items

    async def get_by_service(self, tenant_id: str) -> list[dict]:
        from app.models.cmdb.service_offering import ServiceOffering

        result = await self.db.execute(
            select(
                ServiceEstimation.service_offering_id,
                func.coalesce(func.sum(ServiceEstimation.total_sell_price), 0),
                func.coalesce(func.sum(ServiceEstimation.total_estimated_cost), 0),
                func.coalesce(func.sum(ServiceEstimation.margin_amount), 0),
                func.count(ServiceEstimation.id),
            )
            .where(
                ServiceEstimation.tenant_id == tenant_id,
                ServiceEstimation.status == "approved",
                ServiceEstimation.deleted_at.is_(None),
            )
            .group_by(ServiceEstimation.service_offering_id)
        )
        rows = result.all()
        items = []
        for row in rows:
            revenue = row[1] or Decimal("0")
            cost = row[2] or Decimal("0")
            margin = row[3] or Decimal("0")
            margin_pct = (margin / revenue * Decimal("100")) if revenue > 0 else Decimal("0")

            svc_result = await self.db.execute(
                select(ServiceOffering.name).where(ServiceOffering.id == row[0])
            )
            svc_name = svc_result.scalar_one_or_none() or str(row[0])

            items.append({
                "entity_id": str(row[0]),
                "entity_name": svc_name,
                "total_revenue": revenue,
                "total_cost": cost,
                "margin_amount": margin,
                "margin_percent": margin_pct,
                "estimation_count": row[4],
            })
        return items
