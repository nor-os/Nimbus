"""
Overview: Service for finding and purging soft-deleted tenants past retention period.
Architecture: Tenant cleanup service (Section 4.2)
Dependencies: sqlalchemy, app.models.tenant, app.services.tenant.schema_manager
Concepts: Tenant lifecycle, data retention, schema cleanup
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant
from app.models.tenant_quota import TenantQuota
from app.models.tenant_settings import TenantSettings
from app.models.user_role import UserRole
from app.models.user_tenant import UserTenant
from app.services.tenant.schema_manager import SchemaManager


class PurgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_purgeable_tenants(self) -> list[str]:
        """Find tenants that were soft-deleted beyond the retention period."""
        settings = get_settings()
        cutoff = datetime.now(UTC) - timedelta(days=settings.tenant_retention_days)

        result = await self.db.execute(
            select(Tenant.id).where(
                Tenant.deleted_at.isnot(None),
                Tenant.deleted_at < cutoff,
            )
        )
        return [str(row[0]) for row in result.all()]

    async def purge_tenant(self, tenant_id: str) -> None:
        """Permanently purge a tenant: drop schema, delete all records."""
        # Drop the tenant schema
        schema_mgr = SchemaManager(self.db)
        await schema_mgr.drop_tenant_schema(tenant_id)

        # Delete related records in dependency order
        await self.db.execute(
            delete(UserRole).where(UserRole.tenant_id == tenant_id)
        )
        await self.db.execute(
            delete(UserTenant).where(UserTenant.tenant_id == tenant_id)
        )
        await self.db.execute(
            delete(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        await self.db.execute(
            delete(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        )

        # Hard-delete the tenant record itself
        await self.db.execute(
            delete(Tenant).where(Tenant.id == tenant_id)
        )
