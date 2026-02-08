"""
Overview: Impersonation configuration service — reads/writes tenant settings for impersonation.
Architecture: Service layer for tenant-scoped impersonation config (Section 5)
Dependencies: sqlalchemy, app.models.tenant_settings
Concepts: Tenant settings, impersonation configuration, key-value storage
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_settings import TenantSettings

_DEFAULTS = {
    "impersonation.standard.duration_minutes": ("30", "int"),
    "impersonation.override.duration_minutes": ("60", "int"),
    "impersonation.standard.requires_approval": ("true", "bool"),
    "impersonation.override.requires_approval": ("true", "bool"),
    "impersonation.max_duration_minutes": ("240", "int"),
}


class ImpersonationConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, tenant_id: str) -> dict:
        """Get impersonation config for a tenant, falling back to defaults."""
        result = await self.db.execute(
            select(TenantSettings).where(
                TenantSettings.tenant_id == tenant_id,
                TenantSettings.key.like("impersonation.%"),
            )
        )
        rows = {r.key: r.value for r in result.scalars().all()}

        return {
            "standard_duration_minutes": int(
                rows.get("impersonation.standard.duration_minutes", "30")
            ),
            "override_duration_minutes": int(
                rows.get("impersonation.override.duration_minutes", "60")
            ),
            "standard_requires_approval": _parse_bool(
                rows.get("impersonation.standard.requires_approval", "true")
            ),
            "override_requires_approval": _parse_bool(
                rows.get("impersonation.override.requires_approval", "true")
            ),
            "max_duration_minutes": int(
                rows.get("impersonation.max_duration_minutes", "240")
            ),
        }

    async def update_config(self, tenant_id: str, updates: dict) -> dict:
        """Update impersonation config settings for a tenant."""
        key_map = {
            "standard_duration_minutes": ("impersonation.standard.duration_minutes", "int"),
            "override_duration_minutes": ("impersonation.override.duration_minutes", "int"),
            "standard_requires_approval": ("impersonation.standard.requires_approval", "bool"),
            "override_requires_approval": ("impersonation.override.requires_approval", "bool"),
            "max_duration_minutes": ("impersonation.max_duration_minutes", "int"),
        }

        for field, value in updates.items():
            if value is None or field not in key_map:
                continue
            setting_key, value_type = key_map[field]
            str_value = str(value).lower() if isinstance(value, bool) else str(value)

            result = await self.db.execute(
                select(TenantSettings).where(
                    TenantSettings.tenant_id == tenant_id,
                    TenantSettings.key == setting_key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = str_value
            else:
                self.db.add(
                    TenantSettings(
                        tenant_id=tenant_id,
                        key=setting_key,
                        value=str_value,
                        value_type=value_type,
                    )
                )

        await self.db.flush()
        return await self.get_config(tenant_id)


def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")
