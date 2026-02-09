"""
Overview: GraphQL queries for browsing the semantic type catalog — categories, types,
    relationships, providers, provider resource types, and type mappings.
Architecture: GraphQL query resolvers for the semantic layer (Section 5)
Dependencies: strawberry, app.services.semantic.service
Concepts: Read-only catalog queries with permission checks and converter helpers.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.semantic import (
    ProviderResourceTypeStatusGQL,
    ProviderTypeGQL,
    SemanticCategoryType,
    SemanticCategoryWithTypesType,
    SemanticProviderResourceTypeType,
    SemanticProviderType,
    SemanticRelationshipKindType,
    SemanticResourceTypeListType,
    SemanticResourceTypeType,
    SemanticTypeMappingType,
)


def _category_to_type(c) -> SemanticCategoryType:
    return SemanticCategoryType(
        id=c.id,
        name=c.name,
        display_name=c.display_name,
        description=c.description,
        icon=c.icon,
        sort_order=c.sort_order,
        is_system=c.is_system,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _type_mapping_to_gql(m) -> SemanticTypeMappingType:
    prt = m.provider_resource_type_rel
    stype = m.semantic_type_rel
    return SemanticTypeMappingType(
        id=m.id,
        provider_resource_type_id=m.provider_resource_type_id,
        semantic_type_id=m.semantic_type_id,
        provider_name=prt.provider_rel.name if prt and prt.provider_rel else "",
        provider_api_type=prt.api_type if prt else "",
        provider_display_name=prt.display_name if prt else "",
        semantic_type_name=stype.name if stype else "",
        semantic_type_display_name=stype.display_name if stype else "",
        parameter_mapping=m.parameter_mapping,
        notes=m.notes,
        is_system=m.is_system,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _type_to_gql(t) -> SemanticResourceTypeType:
    return SemanticResourceTypeType(
        id=t.id,
        name=t.name,
        display_name=t.display_name,
        category=_category_to_type(t.category_rel),
        description=t.description,
        icon=t.icon,
        is_abstract=t.is_abstract,
        parent_type_name=t.parent_type.name if t.parent_type else None,
        properties_schema=t.properties_schema,
        allowed_relationship_kinds=t.allowed_relationship_kinds,
        sort_order=t.sort_order,
        is_system=t.is_system,
        mappings=[_type_mapping_to_gql(m) for m in (t.type_mappings or [])],
        children=[_type_to_gql(c) for c in (t.children or [])],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _provider_to_gql(p) -> SemanticProviderType:
    active_types = [
        rt for rt in (p.resource_types or []) if rt.deleted_at is None
    ]
    return SemanticProviderType(
        id=p.id,
        name=p.name,
        display_name=p.display_name,
        description=p.description,
        icon=p.icon,
        provider_type=ProviderTypeGQL(p.provider_type),
        website_url=p.website_url,
        documentation_url=p.documentation_url,
        is_system=p.is_system,
        resource_type_count=len(active_types),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _prt_to_gql(prt) -> SemanticProviderResourceTypeType:
    # Find the first active mapping's semantic type, if any
    active_mappings = [
        tm for tm in (prt.type_mappings or []) if tm.deleted_at is None
    ]
    first_mapping = active_mappings[0] if active_mappings else None
    return SemanticProviderResourceTypeType(
        id=prt.id,
        provider_id=prt.provider_id,
        provider_name=prt.provider_rel.name if prt.provider_rel else "",
        api_type=prt.api_type,
        display_name=prt.display_name,
        description=prt.description,
        documentation_url=prt.documentation_url,
        parameter_schema=prt.parameter_schema,
        status=ProviderResourceTypeStatusGQL(prt.status),
        is_system=prt.is_system,
        semantic_type_name=(
            first_mapping.semantic_type_rel.name
            if first_mapping and first_mapping.semantic_type_rel
            else None
        ),
        semantic_type_id=(
            first_mapping.semantic_type_id if first_mapping else None
        ),
        created_at=prt.created_at,
        updated_at=prt.updated_at,
    )


@strawberry.type
class SemanticQuery:
    @strawberry.field
    async def semantic_categories(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[SemanticCategoryWithTypesType]:
        """List all semantic categories with nested types."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            categories = await service.list_categories()
            return [
                SemanticCategoryWithTypesType(
                    id=c.id,
                    name=c.name,
                    display_name=c.display_name,
                    description=c.description,
                    icon=c.icon,
                    sort_order=c.sort_order,
                    is_system=c.is_system,
                    types=[
                        _type_to_gql(t)
                        for t in sorted(c.types, key=lambda x: x.sort_order)
                        if t.deleted_at is None
                    ],
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in categories
            ]

    @strawberry.field
    async def semantic_types(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
        is_abstract: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SemanticResourceTypeListType:
        """List semantic types with filtering and pagination."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            items, total = await service.list_types(
                category=category,
                is_abstract=is_abstract,
                search=search,
                offset=offset,
                limit=limit,
            )
            return SemanticResourceTypeListType(
                items=[_type_to_gql(t) for t in items],
                total=total,
            )

    @strawberry.field
    async def semantic_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> SemanticResourceTypeType | None:
        """Get a single semantic type with its mappings."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            t = await service.get_type_with_mappings(id)
            if not t:
                return None
            return _type_to_gql(t)

    @strawberry.field
    async def semantic_relationship_kinds(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[SemanticRelationshipKindType]:
        """List all semantic relationship kinds."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            kinds = await service.list_relationship_kinds()
            return [
                SemanticRelationshipKindType(
                    id=k.id,
                    name=k.name,
                    display_name=k.display_name,
                    description=k.description,
                    inverse_name=k.inverse_name,
                    is_system=k.is_system,
                    created_at=k.created_at,
                    updated_at=k.updated_at,
                )
                for k in kinds
            ]

    # -- Provider queries --------------------------------------------------

    @strawberry.field
    async def semantic_providers(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[SemanticProviderType]:
        """List all semantic providers."""
        await check_graphql_permission(info, "semantic:provider:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            providers = await service.list_providers()
            return [_provider_to_gql(p) for p in providers]

    @strawberry.field
    async def semantic_provider(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> SemanticProviderType | None:
        """Get a single provider by ID."""
        await check_graphql_permission(info, "semantic:provider:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            p = await service.get_provider(id)
            if not p:
                return None
            return _provider_to_gql(p)

    # -- Provider resource type queries ------------------------------------

    @strawberry.field
    async def semantic_provider_resource_types(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[SemanticProviderResourceTypeType]:
        """List provider resource types, optionally filtered by provider and status."""
        await check_graphql_permission(info, "semantic:provider:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            prts = await service.list_provider_resource_types(
                provider_id=provider_id,
                status=status,
            )
            return [_prt_to_gql(prt) for prt in prts]

    # -- Type mapping queries ----------------------------------------------

    @strawberry.field
    async def semantic_type_mappings(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_resource_type_id: uuid.UUID | None = None,
        semantic_type_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> list[SemanticTypeMappingType]:
        """List type mappings, optionally filtered."""
        await check_graphql_permission(info, "semantic:mapping:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            mappings = await service.list_type_mappings(
                provider_resource_type_id=provider_resource_type_id,
                semantic_type_id=semantic_type_id,
                provider_id=provider_id,
            )
            return [_type_mapping_to_gql(m) for m in mappings]
