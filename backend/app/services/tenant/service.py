"""
Overview: Core tenant service — CRUD, hierarchy, settings, stats for tenant management.
Architecture: Service layer for tenant lifecycle (Section 3.1, 4.2)
Dependencies: sqlalchemy, app.models.tenant, app.services.tenant.schema_manager, quota_service
Concepts: Multi-tenancy, tenant hierarchy (3-level max), schema-per-tenant
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compartment import Compartment
from app.models.tenant import Tenant
from app.models.tenant_settings import TenantSettings
from app.models.user_tenant import UserTenant
from app.services.tenant.quota_service import QuotaService
from app.services.tenant.rls_manager import RLSManager
from app.services.tenant.schema_manager import SchemaManager


class TenantError(Exception):
    def __init__(self, message: str, code: str = "TENANT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(
        self,
        name: str,
        provider_id: str,
        parent_id: str | None = None,
        contact_email: str | None = None,
        billing_info: dict | None = None,
        description: str | None = None,
    ) -> Tenant:
        """Create a new tenant with schema, quotas, and RLS policies."""
        level = 0
        if parent_id:
            parent = await self.get_tenant(parent_id)
            if not parent:
                raise TenantError("Parent tenant not found", "PARENT_NOT_FOUND")
            if parent.level >= 2:
                raise TenantError(
                    "Maximum hierarchy depth (3 levels) reached", "MAX_DEPTH_EXCEEDED"
                )
            level = parent.level + 1

            # Check child tenant quota on parent
            quota_service = QuotaService(self.db)
            await quota_service.check_quota(parent_id, "max_child_tenants")

        tenant = Tenant(
            name=name,
            parent_id=parent_id,
            provider_id=provider_id,
            contact_email=contact_email,
            billing_info=billing_info,
            description=description,
            is_root=parent_id is None,
            level=level,
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create tenant schema
        schema_mgr = SchemaManager(self.db)
        await schema_mgr.create_tenant_schema(str(tenant.id))

        # Set up RLS policies
        rls_mgr = RLSManager(self.db)
        await rls_mgr.setup_rls_for_all_tenant_tables()

        # Initialize default quotas
        quota_service = QuotaService(self.db)
        await quota_service.initialize_quotas(str(tenant.id))

        # Increment parent's child tenant usage
        if parent_id:
            await quota_service.increment_usage(parent_id, "max_child_tenants")

        # Seed default Local Authentication provider
        from app.models.identity_provider import IdPType, IdentityProvider

        local_idp = IdentityProvider(
            tenant_id=tenant.id,
            name="Local Authentication",
            idp_type=IdPType.LOCAL,
            is_enabled=True,
            is_default=True,
            config={},
        )
        self.db.add(local_idp)
        await self.db.flush()

        return tenant

    async def create_root_tenant(self, name: str, provider_id: str) -> Tenant:
        """Create the virtual root tenant for a provider."""
        return await self.create_tenant(
            name=name,
            provider_id=provider_id,
            parent_id=None,
        )

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID (excluding soft-deleted)."""
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        contact_email: str | None = None,
        billing_info: dict | None = None,
        description: str | None = None,
        **kwargs,
    ) -> Tenant:
        """Update tenant properties."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantError("Tenant not found", "TENANT_NOT_FOUND")

        if name is not None:
            tenant.name = name
        if contact_email is not None:
            tenant.contact_email = contact_email
        if billing_info is not None:
            tenant.billing_info = billing_info
        if description is not None:
            tenant.description = description
        if "invoice_currency" in kwargs:
            tenant.invoice_currency = kwargs["invoice_currency"]
        if "primary_region_id" in kwargs:
            tenant.primary_region_id = kwargs["primary_region_id"]
        return tenant

    async def delete_tenant(self, tenant_id: str) -> Tenant:
        """Soft-delete a tenant. Blocks if it has active children."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantError("Tenant not found", "TENANT_NOT_FOUND")

        # Check for active children
        result = await self.db.execute(
            select(func.count()).select_from(Tenant).where(
                Tenant.parent_id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        child_count = result.scalar_one()
        if child_count > 0:
            raise TenantError(
                "Cannot delete tenant with active children", "HAS_ACTIVE_CHILDREN"
            )

        tenant.deleted_at = datetime.now(UTC)

        # Decrement parent's child tenant usage
        if tenant.parent_id:
            quota_service = QuotaService(self.db)
            await quota_service.decrement_usage(str(tenant.parent_id), "max_child_tenants")

        return tenant

    async def list_tenants(
        self,
        provider_id: str,
        offset: int = 0,
        limit: int = 50,
        parent_id: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination. Returns (tenants, total_count)."""
        query = select(Tenant).where(Tenant.provider_id == provider_id)

        if not include_deleted:
            query = query.where(Tenant.deleted_at.is_(None))
        if parent_id is not None:
            query = query.where(Tenant.parent_id == parent_id)

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # Paginated results
        result = await self.db.execute(
            query.order_by(Tenant.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_tenant_hierarchy(self, tenant_id: str) -> Tenant | None:
        """Get a tenant with its full hierarchy (children loaded eagerly, up to 3 levels)."""
        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
            .options(
                selectinload(Tenant.children)
                .selectinload(Tenant.children)
            )
        )
        return result.scalar_one_or_none()

    async def get_tenant_stats(self, tenant_id: str) -> dict:
        """Get statistics for a tenant."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantError("Tenant not found", "TENANT_NOT_FOUND")

        # Count users
        user_count = (
            await self.db.execute(
                select(func.count()).select_from(UserTenant).where(
                    UserTenant.tenant_id == tenant_id
                )
            )
        ).scalar_one()

        # Count compartments
        compartment_count = (
            await self.db.execute(
                select(func.count()).select_from(Compartment).where(
                    Compartment.tenant_id == tenant_id,
                    Compartment.deleted_at.is_(None),
                )
            )
        ).scalar_one()

        # Count children
        child_count = (
            await self.db.execute(
                select(func.count()).select_from(Tenant).where(
                    Tenant.parent_id == tenant_id,
                    Tenant.deleted_at.is_(None),
                )
            )
        ).scalar_one()

        # Get quotas
        quota_service = QuotaService(self.db)
        quotas = await quota_service.get_quotas(tenant_id)

        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "total_users": user_count,
            "total_compartments": compartment_count,
            "total_children": child_count,
            "quotas": quotas,
        }

    async def update_settings(
        self, tenant_id: str, settings: list[dict]
    ) -> list[TenantSettings]:
        """Create or update tenant settings."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantError("Tenant not found", "TENANT_NOT_FOUND")

        results = []
        for setting_data in settings:
            result = await self.db.execute(
                select(TenantSettings).where(
                    TenantSettings.tenant_id == tenant_id,
                    TenantSettings.key == setting_data["key"],
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = setting_data["value"]
                existing.value_type = setting_data.get("value_type", existing.value_type)
                results.append(existing)
            else:
                new_setting = TenantSettings(
                    tenant_id=tenant_id,
                    key=setting_data["key"],
                    value=setting_data["value"],
                    value_type=setting_data.get("value_type", "string"),
                )
                self.db.add(new_setting)
                results.append(new_setting)
        await self.db.flush()
        return results

    async def get_settings(self, tenant_id: str) -> list[TenantSettings]:
        """Get all settings for a tenant."""
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return list(result.scalars().all())
