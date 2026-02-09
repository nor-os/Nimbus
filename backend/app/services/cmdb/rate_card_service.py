"""
Overview: Staff profile, rate card, and organizational unit service — CRUD for org units,
    staff profiles, and internal rate cards with date-range effective rate lookup.
Architecture: Service delivery cost model (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.staff_profile
Concepts: Organizational units form a hierarchy with cost centers. Staff profiles define
    seniority levels. Rate cards specify hourly cost and sell rate per profile per region.
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.staff_profile import InternalRateCard, OrganizationalUnit, StaffProfile

logger = logging.getLogger(__name__)


class RateCardServiceError(Exception):
    def __init__(self, message: str, code: str = "RATE_CARD_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class RateCardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Organizational Units ─────────────────────────────────────────

    async def list_org_units(
        self, tenant_id: str | None = None
    ) -> list[OrganizationalUnit]:
        stmt = select(OrganizationalUnit).where(OrganizationalUnit.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (OrganizationalUnit.tenant_id == tenant_id)
                | (OrganizationalUnit.tenant_id.is_(None))
            )
        stmt = stmt.order_by(OrganizationalUnit.sort_order, OrganizationalUnit.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_org_unit(self, org_unit_id: str) -> OrganizationalUnit | None:
        result = await self.db.execute(
            select(OrganizationalUnit).where(
                OrganizationalUnit.id == org_unit_id,
                OrganizationalUnit.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_org_unit(
        self, tenant_id: str | None, data: dict
    ) -> OrganizationalUnit:
        ou = OrganizationalUnit(
            tenant_id=tenant_id,
            parent_id=data.get("parent_id"),
            name=data["name"],
            display_name=data["display_name"],
            cost_center=data.get("cost_center"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(ou)
        await self.db.flush()
        return ou

    async def update_org_unit(self, org_unit_id: str, data: dict) -> OrganizationalUnit:
        ou = await self.get_org_unit(org_unit_id)
        if not ou:
            raise RateCardServiceError("Organizational unit not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(ou, key):
                setattr(ou, key, val)
        await self.db.flush()
        return ou

    async def delete_org_unit(self, org_unit_id: str) -> bool:
        ou = await self.get_org_unit(org_unit_id)
        if not ou:
            raise RateCardServiceError("Organizational unit not found", "NOT_FOUND")
        ou.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Staff Profiles ───────────────────────────────────────────────

    async def get_profile(self, profile_id: str) -> StaffProfile | None:
        result = await self.db.execute(
            select(StaffProfile).where(
                StaffProfile.id == profile_id,
                StaffProfile.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self, tenant_id: str | None = None
    ) -> list[StaffProfile]:
        stmt = select(StaffProfile).where(StaffProfile.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (StaffProfile.tenant_id == tenant_id) | (StaffProfile.tenant_id.is_(None))
            )
        stmt = stmt.order_by(StaffProfile.sort_order, StaffProfile.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_profile(
        self, tenant_id: str | None, data: dict
    ) -> StaffProfile:
        profile = StaffProfile(
            tenant_id=tenant_id,
            org_unit_id=data.get("org_unit_id"),
            name=data["name"],
            display_name=data["display_name"],
            is_system=data.get("is_system", False),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def update_profile(self, profile_id: str, data: dict) -> StaffProfile:
        profile = await self.get_profile(profile_id)
        if not profile:
            raise RateCardServiceError("Staff profile not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(profile, key):
                setattr(profile, key, val)
        await self.db.flush()
        return profile

    async def delete_profile(self, profile_id: str) -> bool:
        profile = await self.get_profile(profile_id)
        if not profile:
            raise RateCardServiceError("Staff profile not found", "NOT_FOUND")
        if profile.is_system:
            raise RateCardServiceError("Cannot delete system profile", "SYSTEM_PROTECTED")
        profile.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Rate Cards ───────────────────────────────────────────────────

    async def list_rate_cards(
        self,
        tenant_id: str,
        staff_profile_id: str | None = None,
        delivery_region_id: str | None = None,
    ) -> list[InternalRateCard]:
        stmt = select(InternalRateCard).where(
            InternalRateCard.tenant_id == tenant_id,
            InternalRateCard.deleted_at.is_(None),
        )
        if staff_profile_id:
            stmt = stmt.where(InternalRateCard.staff_profile_id == staff_profile_id)
        if delivery_region_id:
            stmt = stmt.where(InternalRateCard.delivery_region_id == delivery_region_id)
        stmt = stmt.order_by(InternalRateCard.effective_from.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rate_card(
        self, tenant_id: str, data: dict
    ) -> InternalRateCard:
        card = InternalRateCard(
            tenant_id=tenant_id,
            staff_profile_id=data["staff_profile_id"],
            delivery_region_id=data["delivery_region_id"],
            hourly_cost=data["hourly_cost"],
            hourly_sell_rate=data.get("hourly_sell_rate"),
            currency=data.get("currency", "EUR"),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )
        self.db.add(card)
        await self.db.flush()
        return card

    async def update_rate_card(self, card_id: str, data: dict) -> InternalRateCard:
        result = await self.db.execute(
            select(InternalRateCard).where(
                InternalRateCard.id == card_id,
                InternalRateCard.deleted_at.is_(None),
            )
        )
        card = result.scalar_one_or_none()
        if not card:
            raise RateCardServiceError("Rate card not found", "NOT_FOUND")
        for key, val in data.items():
            if hasattr(card, key):
                setattr(card, key, val)
        await self.db.flush()
        return card

    async def delete_rate_card(self, card_id: str) -> bool:
        result = await self.db.execute(
            select(InternalRateCard).where(
                InternalRateCard.id == card_id,
                InternalRateCard.deleted_at.is_(None),
            )
        )
        card = result.scalar_one_or_none()
        if not card:
            raise RateCardServiceError("Rate card not found", "NOT_FOUND")
        card.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_effective_rate(
        self, tenant_id: str, staff_profile_id: str, region_id: str, as_of: date | None = None
    ) -> InternalRateCard | None:
        check_date = as_of or date.today()
        result = await self.db.execute(
            select(InternalRateCard).where(
                InternalRateCard.tenant_id == tenant_id,
                InternalRateCard.staff_profile_id == staff_profile_id,
                InternalRateCard.delivery_region_id == region_id,
                InternalRateCard.effective_from <= check_date,
                (InternalRateCard.effective_to.is_(None))
                | (InternalRateCard.effective_to >= check_date),
                InternalRateCard.deleted_at.is_(None),
            ).order_by(InternalRateCard.effective_from.desc()).limit(1)
        )
        return result.scalar_one_or_none()
