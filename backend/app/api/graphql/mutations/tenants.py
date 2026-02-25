"""
Overview: GraphQL mutations for tenant CRUD, settings, quotas, and compartments.
Architecture: GraphQL mutation resolvers (Section 7.2)
Dependencies: strawberry, app.services.tenant
Concepts: Multi-tenancy, GraphQL mutations, tenant lifecycle
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.tenant import (
    CompartmentCreateInput,
    CompartmentType,
    CompartmentUpdateInput,
    QuotaUpdateInput,
    TenantCreateInput,
    TenantQuotaType,
    TenantSettingInput,
    TenantSettingType,
    TenantType,
    TenantUpdateInput,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class TenantMutation:
    @strawberry.mutation
    async def create_tenant(
        self, info: Info, input: TenantCreateInput, provider_id: uuid.UUID
    ) -> TenantType:
        """Create a new tenant."""
        from app.services.tenant.service import TenantService

        db = await _get_session(info)
        service = TenantService(db)
        tenant = await service.create_tenant(
            name=input.name,
            provider_id=str(provider_id),
            parent_id=str(input.parent_id) if input.parent_id else None,
            contact_email=input.contact_email,
            description=input.description,
            invoice_currency=input.invoice_currency,
            primary_region_id=str(input.primary_region_id) if input.primary_region_id else None,
        )

        # Auto-create skeleton cloud backend if provider selected
        if input.provider_id_for_backend:
            from app.models.cloud_backend import CloudBackend

            skeleton_backend = CloudBackend(
                tenant_id=tenant.id,
                provider_id=input.provider_id_for_backend,
                name=f"{input.name} Backend",
                status="disabled",
            )
            db.add(skeleton_backend)

        await db.commit()
        return TenantType(
            id=tenant.id,
            name=tenant.name,
            parent_id=tenant.parent_id,
            provider_id=tenant.provider_id,
            contact_email=tenant.contact_email,
            is_root=tenant.is_root,
            level=tenant.level,
            description=tenant.description,
            invoice_currency=tenant.invoice_currency,
            primary_region_id=tenant.primary_region_id,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    @strawberry.mutation
    async def update_tenant(
        self, info: Info, tenant_id: uuid.UUID, input: TenantUpdateInput
    ) -> TenantType:
        """Update an existing tenant."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.service import TenantService

        db = await _get_session(info)
        service = TenantService(db)
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.contact_email is not None:
            kwargs["contact_email"] = input.contact_email
        if input.description is not None:
            kwargs["description"] = input.description
        if input.invoice_currency is not strawberry.UNSET:
            kwargs["invoice_currency"] = input.invoice_currency
        if input.primary_region_id is not strawberry.UNSET:
            kwargs["primary_region_id"] = str(input.primary_region_id) if input.primary_region_id else None

        tenant = await service.update_tenant(str(tenant_id), **kwargs)
        await db.commit()
        return TenantType(
            id=tenant.id,
            name=tenant.name,
            parent_id=tenant.parent_id,
            provider_id=tenant.provider_id,
            contact_email=tenant.contact_email,
            is_root=tenant.is_root,
            level=tenant.level,
            description=tenant.description,
            invoice_currency=tenant.invoice_currency,
            primary_region_id=tenant.primary_region_id,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    @strawberry.mutation
    async def delete_tenant(self, info: Info, tenant_id: uuid.UUID) -> bool:
        """Soft-delete a tenant."""
        await check_graphql_permission(info, "settings:tenant:delete", str(tenant_id))
        from app.services.tenant.service import TenantService

        db = await _get_session(info)
        service = TenantService(db)
        await service.delete_tenant(str(tenant_id))
        await db.commit()
        return True

    @strawberry.mutation
    async def update_tenant_settings(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        settings: list[TenantSettingInput],
    ) -> list[TenantSettingType]:
        """Create or update tenant settings."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.service import TenantService

        db = await _get_session(info)
        service = TenantService(db)
        results = await service.update_settings(
            str(tenant_id),
            [{"key": s.key, "value": s.value, "value_type": s.value_type} for s in settings],
        )
        await db.commit()
        return [
            TenantSettingType(
                id=s.id,
                key=s.key,
                value=s.value,
                value_type=s.value_type,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in results
        ]

    @strawberry.mutation
    async def update_tenant_quotas(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        quota_type: str,
        input: QuotaUpdateInput,
    ) -> TenantQuotaType | None:
        """Update a quota for a tenant."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.quota_service import QuotaService

        db = await _get_session(info)
        service = QuotaService(db)
        quota = await service.update_quota(
            str(tenant_id),
            quota_type,
            limit_value=input.limit_value,
            enforcement=input.enforcement,
        )
        if not quota:
            return None
        await db.commit()
        return TenantQuotaType(
            id=quota.id,
            quota_type=quota.quota_type,
            limit_value=quota.limit_value,
            current_usage=quota.current_usage,
            enforcement=quota.enforcement,
            created_at=quota.created_at,
            updated_at=quota.updated_at,
        )

    @strawberry.mutation
    async def create_compartment(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CompartmentCreateInput,
    ) -> CompartmentType:
        """Create a new compartment."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.compartment_service import CompartmentService

        db = await _get_session(info)
        service = CompartmentService(db)
        compartment = await service.create_compartment(
            tenant_id=str(tenant_id),
            name=input.name,
            parent_id=str(input.parent_id) if input.parent_id else None,
            description=input.description,
        )
        await db.commit()
        return CompartmentType(
            id=compartment.id,
            tenant_id=compartment.tenant_id,
            parent_id=compartment.parent_id,
            name=compartment.name,
            description=compartment.description,
            created_at=compartment.created_at,
            updated_at=compartment.updated_at,
        )

    @strawberry.mutation
    async def update_compartment(
        self,
        info: Info,
        compartment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        input: CompartmentUpdateInput,
    ) -> CompartmentType:
        """Update a compartment."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.compartment_service import CompartmentService

        db = await _get_session(info)
        service = CompartmentService(db)
        compartment = await service.update_compartment(
            compartment_id=str(compartment_id),
            tenant_id=str(tenant_id),
            name=input.name,
            parent_id=str(input.parent_id) if input.parent_id else None,
            description=input.description,
        )
        await db.commit()
        return CompartmentType(
            id=compartment.id,
            tenant_id=compartment.tenant_id,
            parent_id=compartment.parent_id,
            name=compartment.name,
            description=compartment.description,
            created_at=compartment.created_at,
            updated_at=compartment.updated_at,
        )

    @strawberry.mutation
    async def delete_compartment(
        self, info: Info, compartment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        """Soft-delete a compartment."""
        await check_graphql_permission(info, "settings:tenant:update", str(tenant_id))
        from app.services.tenant.compartment_service import CompartmentService

        db = await _get_session(info)
        service = CompartmentService(db)
        await service.delete_compartment(str(compartment_id), str(tenant_id))
        await db.commit()
        return True
