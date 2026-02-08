"""
Overview: Audit logging config service — reads/writes tenant settings
    for middleware log filtering.
Architecture: Service layer for tenant-scoped audit logging config (Section 8)
Dependencies: sqlalchemy, app.models.tenant_settings
Concepts: Tenant settings, audit configuration, key-value storage
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_settings import TenantSettings

_DEFAULTS = {
    "audit.log_api_reads": ("false", "bool"),
    "audit.log_api_writes": ("true", "bool"),
    "audit.log_auth_events": ("true", "bool"),
    "audit.log_graphql": ("true", "bool"),
    "audit.log_errors": ("true", "bool"),
}


class AuditLoggingConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, tenant_id: str) -> dict:
        """Get audit logging config for a tenant, falling back to defaults."""
        result = await self.db.execute(
            select(TenantSettings).where(
                TenantSettings.tenant_id == tenant_id,
                TenantSettings.key.like("audit.log_%"),
            )
        )
        rows = {r.key: r.value for r in result.scalars().all()}

        return {
            "log_api_reads": _parse_bool(
                rows.get("audit.log_api_reads", "false")
            ),
            "log_api_writes": _parse_bool(
                rows.get("audit.log_api_writes", "true")
            ),
            "log_auth_events": _parse_bool(
                rows.get("audit.log_auth_events", "true")
            ),
            "log_graphql": _parse_bool(
                rows.get("audit.log_graphql", "true")
            ),
            "log_errors": _parse_bool(
                rows.get("audit.log_errors", "true")
            ),
        }

    async def update_config(self, tenant_id: str, updates: dict) -> dict:
        """Update audit logging config settings for a tenant."""
        key_map = {
            "log_api_reads": ("audit.log_api_reads", "bool"),
            "log_api_writes": ("audit.log_api_writes", "bool"),
            "log_auth_events": ("audit.log_auth_events", "bool"),
            "log_graphql": ("audit.log_graphql", "bool"),
            "log_errors": ("audit.log_errors", "bool"),
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
