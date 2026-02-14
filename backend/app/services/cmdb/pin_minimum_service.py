"""
Overview: Pin minimum charge service — CRUD for minimum billing thresholds scoped to price
    list pins, replacing standalone tenant minimum charges.
Architecture: Per-pin minimum charge management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.pin_minimum_charge, app.models.cmdb.price_list
Concepts: Pin minimum charges define billing floors per category or globally, tied to a
    specific tenant price list pin. Effective date ranges control when minimums apply.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.pin_minimum_charge import PinMinimumCharge
from app.models.cmdb.price_list import TenantPriceListPin
from app.services.cmdb.catalog_service import CatalogServiceError


class PinMinimumChargeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_minimum(
        self, tenant_id: str, pin_id: str, data: dict
    ) -> PinMinimumCharge:
        # Validate pin exists for tenant
        result = await self.db.execute(
            select(TenantPriceListPin).where(
                TenantPriceListPin.id == pin_id,
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pin = result.scalar_one_or_none()
        if not pin:
            raise CatalogServiceError("Price list pin not found", "NOT_FOUND")

        charge = PinMinimumCharge(
            tenant_id=tenant_id,
            pin_id=pin_id,
            category=data.get("category"),
            minimum_amount=data["minimum_amount"],
            currency=data.get("currency", "EUR"),
            period=data.get("period", "monthly"),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )
        self.db.add(charge)
        await self.db.flush()
        return charge

    async def list_minimums(
        self, pin_id: str
    ) -> list[PinMinimumCharge]:
        result = await self.db.execute(
            select(PinMinimumCharge)
            .where(
                PinMinimumCharge.pin_id == pin_id,
                PinMinimumCharge.deleted_at.is_(None),
            )
            .order_by(PinMinimumCharge.effective_from)
        )
        return list(result.scalars().all())

    async def update_minimum(
        self, charge_id: str, tenant_id: str, data: dict
    ) -> PinMinimumCharge:
        result = await self.db.execute(
            select(PinMinimumCharge).where(
                PinMinimumCharge.id == charge_id,
                PinMinimumCharge.tenant_id == tenant_id,
                PinMinimumCharge.deleted_at.is_(None),
            )
        )
        charge = result.scalar_one_or_none()
        if not charge:
            raise CatalogServiceError("Pin minimum charge not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(charge, key) and val is not None:
                setattr(charge, key, val)
        await self.db.flush()
        return charge

    async def delete_minimum(
        self, charge_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(PinMinimumCharge).where(
                PinMinimumCharge.id == charge_id,
                PinMinimumCharge.tenant_id == tenant_id,
                PinMinimumCharge.deleted_at.is_(None),
            )
        )
        charge = result.scalar_one_or_none()
        if not charge:
            raise CatalogServiceError("Pin minimum charge not found", "NOT_FOUND")
        charge.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_effective_minimums(
        self, tenant_id: str, as_of: date | None = None
    ) -> list[PinMinimumCharge]:
        check_date = as_of or date.today()

        # Get all active pins for this tenant
        pin_result = await self.db.execute(
            select(TenantPriceListPin.id).where(
                TenantPriceListPin.tenant_id == tenant_id,
                TenantPriceListPin.deleted_at.is_(None),
            )
        )
        pin_ids = [row for row in pin_result.scalars().all()]
        if not pin_ids:
            return []

        # Get effective minimums across all pins
        result = await self.db.execute(
            select(PinMinimumCharge)
            .where(
                PinMinimumCharge.pin_id.in_(pin_ids),
                PinMinimumCharge.deleted_at.is_(None),
                PinMinimumCharge.effective_from <= check_date,
                (PinMinimumCharge.effective_to.is_(None))
                | (PinMinimumCharge.effective_to >= check_date),
            )
            .order_by(PinMinimumCharge.category)
        )
        return list(result.scalars().all())
