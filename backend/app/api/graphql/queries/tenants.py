"""
Overview: GraphQL queries for tenants, hierarchy, stats, compartments.
Architecture: GraphQL query resolvers (Section 7.2)
Dependencies: strawberry, app.services.tenant
Concepts: Multi-tenancy, GraphQL queries, tenant data access
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.tenant import (
    CompartmentTreeType,
    CompartmentType,
    TenantHierarchyType,
    TenantQuotaType,
    TenantStatsType,
    TenantType,
)


@strawberry.type
class TenantQuery:
    @strawberry.field
    async def tenant(self, info: Info, tenant_id: uuid.UUID) -> TenantType | None:
        """Get a single tenant by ID."""
        await check_graphql_permission(info, "settings:tenant:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.tenant.service import TenantService

        async with async_session_factory() as db:
            service = TenantService(db)
            tenant = await service.get_tenant(str(tenant_id))
            if not tenant:
                return None
            return TenantType(
                id=tenant.id,
                name=tenant.name,
                parent_id=tenant.parent_id,
                provider_id=tenant.provider_id,
                contact_email=tenant.contact_email,
                is_root=tenant.is_root,
                level=tenant.level,
                description=tenant.description,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
            )

    @strawberry.field
    async def tenants(
        self,
        info: Info,
        provider_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TenantType]:
        """List tenants for a provider."""
        from app.db.session import async_session_factory
        from app.services.tenant.service import TenantService

        async with async_session_factory() as db:
            service = TenantService(db)
            results, _total = await service.list_tenants(
                provider_id=str(provider_id), offset=offset, limit=limit
            )
            return [
                TenantType(
                    id=t.id,
                    name=t.name,
                    parent_id=t.parent_id,
                    provider_id=t.provider_id,
                    contact_email=t.contact_email,
                    is_root=t.is_root,
                    level=t.level,
                    description=t.description,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in results
            ]

    @strawberry.field
    async def tenant_hierarchy(
        self, info: Info, tenant_id: uuid.UUID
    ) -> TenantHierarchyType | None:
        """Get the tenant hierarchy tree."""
        await check_graphql_permission(info, "settings:tenant:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.tenant.service import TenantService

        async with async_session_factory() as db:
            service = TenantService(db)
            tenant = await service.get_tenant_hierarchy(str(tenant_id))
            if not tenant:
                return None
            return _build_hierarchy(tenant)

    @strawberry.field
    async def tenant_stats(self, info: Info, tenant_id: uuid.UUID) -> TenantStatsType | None:
        """Get stats for a tenant."""
        await check_graphql_permission(info, "settings:tenant:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.tenant.service import TenantService

        async with async_session_factory() as db:
            service = TenantService(db)
            try:
                stats = await service.get_tenant_stats(str(tenant_id))
            except Exception:
                return None
            return TenantStatsType(
                tenant_id=stats["tenant_id"],
                name=stats["name"],
                total_users=stats["total_users"],
                total_compartments=stats["total_compartments"],
                total_children=stats["total_children"],
                quotas=[
                    TenantQuotaType(
                        id=q.id,
                        quota_type=q.quota_type,
                        limit_value=q.limit_value,
                        current_usage=q.current_usage,
                        enforcement=q.enforcement,
                        created_at=q.created_at,
                        updated_at=q.updated_at,
                    )
                    for q in stats["quotas"]
                ],
            )

    @strawberry.field
    async def compartments(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[CompartmentType]:
        """List compartments for a tenant."""
        await check_graphql_permission(info, "settings:tenant:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.tenant.compartment_service import CompartmentService

        async with async_session_factory() as db:
            service = CompartmentService(db)
            results = await service.list_compartments(str(tenant_id))
            return [
                CompartmentType(
                    id=c.id,
                    tenant_id=c.tenant_id,
                    parent_id=c.parent_id,
                    name=c.name,
                    description=c.description,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in results
            ]

    @strawberry.field
    async def compartment_tree(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[CompartmentTreeType]:
        """Get the full compartment tree for a tenant."""
        await check_graphql_permission(info, "settings:tenant:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.tenant.compartment_service import CompartmentService

        async with async_session_factory() as db:
            service = CompartmentService(db)
            tree = await service.get_compartment_tree(str(tenant_id))
            return [_build_compartment_tree(node) for node in tree]


def _build_hierarchy(tenant) -> TenantHierarchyType:
    children = [
        _build_hierarchy(child)
        for child in (tenant.children or [])
        if child.deleted_at is None
    ]
    return TenantHierarchyType(
        id=tenant.id,
        name=tenant.name,
        level=tenant.level,
        is_root=tenant.is_root,
        children=children,
    )


def _build_compartment_tree(node: dict) -> CompartmentTreeType:
    return CompartmentTreeType(
        id=node["id"],
        name=node["name"],
        description=node["description"],
        children=[_build_compartment_tree(c) for c in node.get("children", [])],
    )
