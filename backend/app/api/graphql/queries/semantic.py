"""
Overview: GraphQL queries for browsing the semantic type catalog — categories, types,
    relationships, and providers.
Architecture: GraphQL query resolvers for the semantic layer (Section 5)
Dependencies: strawberry, app.services.semantic.service
Concepts: Read-only catalog queries with permission checks and converter helpers.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.semantic import (
    ProviderTypeGQL,
    SemanticActivityTypeType,
    SemanticCategoryType,
    SemanticCategoryWithTypesType,
    SemanticProviderType,
    SemanticRelationshipKindType,
    SemanticResourceTypeListType,
    SemanticResourceTypeType,
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
        is_infrastructure=c.is_infrastructure,
        created_at=c.created_at,
        updated_at=c.updated_at,
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
        children=[_type_to_gql(c) for c in (t.children or [])],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _provider_to_gql(p) -> SemanticProviderType:
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
        resource_type_count=0,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _activity_type_to_gql(at) -> SemanticActivityTypeType:
    drk = getattr(at, "default_relationship_kind", None)
    return SemanticActivityTypeType(
        id=at.id,
        name=at.name,
        display_name=at.display_name,
        category=at.category,
        description=at.description,
        icon=at.icon,
        applicable_semantic_categories=at.applicable_semantic_categories,
        applicable_semantic_types=at.applicable_semantic_types,
        default_relationship_kind_id=at.default_relationship_kind_id,
        default_relationship_kind_name=drk.display_name if drk else None,
        properties_schema=at.properties_schema,
        is_system=at.is_system,
        sort_order=at.sort_order,
        created_at=at.created_at,
        updated_at=at.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class SemanticQuery:
    @strawberry.field
    async def semantic_categories(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[SemanticCategoryWithTypesType]:
        """List all semantic categories with nested types."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
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
                is_infrastructure=c.is_infrastructure,
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
        infrastructure_only: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SemanticResourceTypeListType:
        """List semantic types with filtering and pagination."""
        await check_graphql_permission(info, "semantic:type:read", str(tenant_id))

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
        service = SemanticService(db)
        items, total = await service.list_types(
            category=category,
            is_abstract=is_abstract,
            infrastructure_only=infrastructure_only,
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

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
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

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
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

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
        service = SemanticService(db)
        providers = await service.list_providers()
        return [_provider_to_gql(p) for p in providers]

    @strawberry.field
    async def semantic_provider(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> SemanticProviderType | None:
        """Get a single provider by ID."""
        await check_graphql_permission(info, "semantic:provider:read", str(tenant_id))

        from app.services.semantic.service import SemanticService

        db = await _get_session(info)
        service = SemanticService(db)
        p = await service.get_provider(id)
        if not p:
            return None
        return _provider_to_gql(p)

    # -- Activity type queries ---------------------------------------------

    @strawberry.field
    async def semantic_activity_types(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
    ) -> list[SemanticActivityTypeType]:
        """List semantic activity types, optionally filtered by category."""
        await check_graphql_permission(info, "semantic:activity-type:read", str(tenant_id))

        from app.services.semantic.activity_type_service import ActivityTypeService

        db = await _get_session(info)
        service = ActivityTypeService(db)
        types = await service.list_activity_types(category)
        return [_activity_type_to_gql(t) for t in types]

    @strawberry.field
    async def semantic_activity_type(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> SemanticActivityTypeType | None:
        """Get a single semantic activity type by ID."""
        await check_graphql_permission(info, "semantic:activity-type:read", str(tenant_id))

        from app.services.semantic.activity_type_service import ActivityTypeService

        db = await _get_session(info)
        service = ActivityTypeService(db)
        at = await service.get_activity_type(str(id))
        return _activity_type_to_gql(at) if at else None
