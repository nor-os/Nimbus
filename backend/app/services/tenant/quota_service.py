"""
Overview: Quota enforcement service — check, increment, decrement, and initialize tenant quotas.
Architecture: Quota management layer (Section 4.2)
Dependencies: sqlalchemy, app.models.tenant_quota
Concepts: Resource quotas, hard/soft enforcement, tenant resource limits
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_quota import QuotaEnforcement, QuotaType, TenantQuota

logger = logging.getLogger(__name__)

DEFAULT_QUOTAS = {
    QuotaType.MAX_USERS: (50, QuotaEnforcement.HARD),
    QuotaType.MAX_COMPARTMENTS: (20, QuotaEnforcement.HARD),
    QuotaType.MAX_RESOURCES: (500, QuotaEnforcement.SOFT),
    QuotaType.MAX_STORAGE_GB: (100, QuotaEnforcement.SOFT),
    QuotaType.MAX_CHILD_TENANTS: (10, QuotaEnforcement.HARD),
}


class QuotaExceededError(Exception):
    def __init__(self, quota_type: str, limit: int, current: int):
        self.quota_type = quota_type
        self.limit = limit
        self.current = current
        super().__init__(
            f"Quota exceeded for {quota_type}: {current}/{limit}"
        )


class QuotaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_quota(self, tenant_id: str, quota_type: str) -> bool:
        """Check if a quota allows increment. Raises QuotaExceededError for hard limits."""
        result = await self.db.execute(
            select(TenantQuota).where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.quota_type == quota_type,
            )
        )
        quota = result.scalar_one_or_none()
        if not quota:
            return True  # No quota set = unlimited

        if quota.current_usage >= quota.limit_value:
            if quota.enforcement == QuotaEnforcement.HARD.value:
                raise QuotaExceededError(quota_type, quota.limit_value, quota.current_usage)
            else:
                logger.warning(
                    "Soft quota exceeded for tenant %s: %s (%d/%d)",
                    tenant_id, quota_type, quota.current_usage, quota.limit_value,
                )
        return True

    async def increment_usage(self, tenant_id: str, quota_type: str, amount: int = 1) -> None:
        """Increment the usage counter for a quota."""
        result = await self.db.execute(
            select(TenantQuota).where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.quota_type == quota_type,
            )
        )
        quota = result.scalar_one_or_none()
        if quota:
            quota.current_usage += amount

    async def decrement_usage(self, tenant_id: str, quota_type: str, amount: int = 1) -> None:
        """Decrement the usage counter for a quota (floor at 0)."""
        result = await self.db.execute(
            select(TenantQuota).where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.quota_type == quota_type,
            )
        )
        quota = result.scalar_one_or_none()
        if quota:
            quota.current_usage = max(0, quota.current_usage - amount)

    async def initialize_quotas(self, tenant_id: str) -> list[TenantQuota]:
        """Create default quotas for a new tenant."""
        quotas = []
        for qtype, (limit, enforcement) in DEFAULT_QUOTAS.items():
            quota = TenantQuota(
                tenant_id=tenant_id,
                quota_type=qtype.value,
                limit_value=limit,
                enforcement=enforcement.value,
            )
            self.db.add(quota)
            quotas.append(quota)
        await self.db.flush()
        return quotas

    async def get_quotas(self, tenant_id: str) -> list[TenantQuota]:
        """Get all quotas for a tenant."""
        result = await self.db.execute(
            select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def update_quota(
        self,
        tenant_id: str,
        quota_type: str,
        limit_value: int | None = None,
        enforcement: str | None = None,
    ) -> TenantQuota | None:
        """Update a specific quota for a tenant."""
        result = await self.db.execute(
            select(TenantQuota).where(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.quota_type == quota_type,
            )
        )
        quota = result.scalar_one_or_none()
        if not quota:
            return None

        if limit_value is not None:
            quota.limit_value = limit_value
        if enforcement is not None:
            quota.enforcement = enforcement
        return quota
