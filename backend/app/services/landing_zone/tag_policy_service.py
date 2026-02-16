"""
Overview: Tag policy service — manage landing zone tagging governance rules.
Architecture: Landing zone service layer (Section 6)
Dependencies: sqlalchemy, app.models.landing_zone
Concepts: Tag governance, required tags, allowed values, inheritance
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.landing_zone import LandingZoneTagPolicy


class TagPolicyService:

    async def create(self, db: AsyncSession, *, landing_zone_id: uuid.UUID,
                     tag_key: str, display_name: str, description: str | None = None,
                     is_required: bool = False, allowed_values: dict | None = None,
                     default_value: str | None = None, inherited: bool = True) -> LandingZoneTagPolicy:
        policy = LandingZoneTagPolicy(
            landing_zone_id=landing_zone_id, tag_key=tag_key, display_name=display_name,
            description=description, is_required=is_required, allowed_values=allowed_values,
            default_value=default_value, inherited=inherited,
        )
        db.add(policy)
        await db.flush()
        await db.refresh(policy)
        return policy

    async def get(self, db: AsyncSession, policy_id: uuid.UUID) -> LandingZoneTagPolicy | None:
        result = await db.execute(
            select(LandingZoneTagPolicy).where(LandingZoneTagPolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def list_by_zone(self, db: AsyncSession, landing_zone_id: uuid.UUID) -> list[LandingZoneTagPolicy]:
        result = await db.execute(
            select(LandingZoneTagPolicy)
            .where(LandingZoneTagPolicy.landing_zone_id == landing_zone_id)
            .order_by(LandingZoneTagPolicy.is_required.desc(), LandingZoneTagPolicy.tag_key)
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, policy_id: uuid.UUID, **kwargs) -> LandingZoneTagPolicy:
        policy = await self.get(db, policy_id)
        if not policy:
            raise ValueError(f"Tag policy {policy_id} not found")
        for key, value in kwargs.items():
            if hasattr(policy, key) and key not in ("id", "landing_zone_id", "created_at"):
                setattr(policy, key, value)
        await db.flush()
        await db.refresh(policy)
        return policy

    async def delete(self, db: AsyncSession, policy_id: uuid.UUID) -> None:
        policy = await self.get(db, policy_id)
        if not policy:
            raise ValueError(f"Tag policy {policy_id} not found")
        await db.delete(policy)
        await db.flush()
