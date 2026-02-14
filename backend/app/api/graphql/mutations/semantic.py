"""
Overview: GraphQL mutations for semantic layer CRUD — categories, types, providers,
    and relationship kinds with is_system protection.
Architecture: GraphQL mutation resolvers for the semantic layer (Section 5)
Dependencies: strawberry, app.services.semantic.service
Concepts: Create/update/delete with permission checks, system record protection, FK validation
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.semantic import (
    _activity_type_to_gql,
    _category_to_type,
    _provider_to_gql,
    _type_to_gql,
)
from app.api.graphql.types.semantic import (
    SemanticCategoryInput,
    SemanticCategoryType,
    SemanticCategoryUpdateInput,
    SemanticProviderInput,
    SemanticProviderType,
    SemanticProviderUpdateInput,
    SemanticActivityTypeInput,
    SemanticActivityTypeType,
    SemanticActivityTypeUpdateInput,
    SemanticRelationshipKindInput,
    SemanticRelationshipKindType,
    SemanticRelationshipKindUpdateInput,
    SemanticResourceTypeInput,
    SemanticResourceTypeType,
    SemanticResourceTypeUpdateInput,
)

logger = logging.getLogger(__name__)


def _relationship_kind_to_type(k) -> SemanticRelationshipKindType:
    return SemanticRelationshipKindType(
        id=k.id,
        name=k.name,
        display_name=k.display_name,
        description=k.description,
        inverse_name=k.inverse_name,
        is_system=k.is_system,
        created_at=k.created_at,
        updated_at=k.updated_at,
    )


@strawberry.type
class SemanticMutation:
    # -- Category mutations ------------------------------------------------

    @strawberry.mutation
    async def create_semantic_category(
        self, info: Info, tenant_id: uuid.UUID, input: SemanticCategoryInput
    ) -> SemanticCategoryType:
        """Create a new semantic category."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            category = await service.create_category(
                name=input.name,
                display_name=input.display_name,
                description=input.description,
                icon=input.icon,
                sort_order=input.sort_order,
            )
            await db.commit()
            return _category_to_type(category)

    @strawberry.mutation
    async def update_semantic_category(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: SemanticCategoryUpdateInput,
    ) -> SemanticCategoryType | None:
        """Update a semantic category."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        kwargs = {}
        if input.display_name is not None:
            kwargs["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.icon is not strawberry.UNSET:
            kwargs["icon"] = input.icon
        if input.sort_order is not None:
            kwargs["sort_order"] = input.sort_order

        async with async_session_factory() as db:
            service = SemanticService(db)
            category = await service.update_category(id, **kwargs)
            if not category:
                return None
            await db.commit()
            return _category_to_type(category)

    @strawberry.mutation
    async def delete_semantic_category(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a semantic category (soft delete)."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            deleted = await service.delete_category(id)
            await db.commit()
            return deleted

    # -- Type mutations ----------------------------------------------------

    @strawberry.mutation
    async def create_semantic_type(
        self, info: Info, tenant_id: uuid.UUID, input: SemanticResourceTypeInput
    ) -> SemanticResourceTypeType:
        """Create a new semantic resource type."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            stype = await service.create_type(
                name=input.name,
                display_name=input.display_name,
                category_id=input.category_id,
                description=input.description,
                icon=input.icon,
                is_abstract=input.is_abstract,
                parent_type_id=input.parent_type_id,
                properties_schema=input.properties_schema,
                allowed_relationship_kinds=input.allowed_relationship_kinds,
                sort_order=input.sort_order,
            )
            await db.commit()
            return _type_to_gql(stype)

    @strawberry.mutation
    async def update_semantic_type(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: SemanticResourceTypeUpdateInput,
    ) -> SemanticResourceTypeType | None:
        """Update a semantic resource type."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        kwargs = {}
        if input.display_name is not None:
            kwargs["display_name"] = input.display_name
        if input.category_id is not None:
            kwargs["category_id"] = input.category_id
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.icon is not strawberry.UNSET:
            kwargs["icon"] = input.icon
        if input.is_abstract is not None:
            kwargs["is_abstract"] = input.is_abstract
        if input.parent_type_id is not strawberry.UNSET:
            kwargs["parent_type_id"] = input.parent_type_id
        if input.properties_schema is not strawberry.UNSET:
            kwargs["properties_schema"] = input.properties_schema
        if input.allowed_relationship_kinds is not strawberry.UNSET:
            kwargs["allowed_relationship_kinds"] = input.allowed_relationship_kinds
        if input.sort_order is not None:
            kwargs["sort_order"] = input.sort_order

        async with async_session_factory() as db:
            service = SemanticService(db)
            stype = await service.update_type(id, **kwargs)
            if not stype:
                return None
            await db.commit()
            return _type_to_gql(stype)

    @strawberry.mutation
    async def delete_semantic_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a semantic resource type (soft delete)."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            deleted = await service.delete_type(id)
            await db.commit()
            return deleted

    # -- Provider mutations ------------------------------------------------

    @strawberry.mutation
    async def create_semantic_provider(
        self, info: Info, tenant_id: uuid.UUID, input: SemanticProviderInput
    ) -> SemanticProviderType:
        """Create a new provider."""
        await check_graphql_permission(
            info, "semantic:provider:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            provider = await service.create_provider(
                name=input.name,
                display_name=input.display_name,
                description=input.description,
                icon=input.icon,
                provider_type=input.provider_type.value,
                website_url=input.website_url,
                documentation_url=input.documentation_url,
            )
            await db.commit()
            # Re-fetch with relationships for full GQL type
            provider = await service.get_provider(provider.id)
            return _provider_to_gql(provider)

    @strawberry.mutation
    async def update_semantic_provider(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: SemanticProviderUpdateInput,
    ) -> SemanticProviderType | None:
        """Update a provider."""
        await check_graphql_permission(
            info, "semantic:provider:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        kwargs = {}
        if input.display_name is not None:
            kwargs["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.icon is not strawberry.UNSET:
            kwargs["icon"] = input.icon
        if input.provider_type is not None:
            kwargs["provider_type"] = input.provider_type.value
        if input.website_url is not strawberry.UNSET:
            kwargs["website_url"] = input.website_url
        if input.documentation_url is not strawberry.UNSET:
            kwargs["documentation_url"] = input.documentation_url

        async with async_session_factory() as db:
            service = SemanticService(db)
            provider = await service.update_provider(id, **kwargs)
            if not provider:
                return None
            await db.commit()
            return _provider_to_gql(provider)

    @strawberry.mutation
    async def delete_semantic_provider(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a provider (soft delete)."""
        await check_graphql_permission(
            info, "semantic:provider:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            deleted = await service.delete_provider(id)
            await db.commit()
            return deleted

    # -- Relationship kind mutations ---------------------------------------

    @strawberry.mutation
    async def create_relationship_kind(
        self, info: Info, tenant_id: uuid.UUID, input: SemanticRelationshipKindInput
    ) -> SemanticRelationshipKindType:
        """Create a new relationship kind."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            kind = await service.create_relationship_kind(
                name=input.name,
                display_name=input.display_name,
                inverse_name=input.inverse_name,
                description=input.description,
            )
            await db.commit()
            return _relationship_kind_to_type(kind)

    @strawberry.mutation
    async def update_relationship_kind(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: SemanticRelationshipKindUpdateInput,
    ) -> SemanticRelationshipKindType | None:
        """Update a relationship kind."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        kwargs = {}
        if input.display_name is not None:
            kwargs["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.inverse_name is not None:
            kwargs["inverse_name"] = input.inverse_name

        async with async_session_factory() as db:
            service = SemanticService(db)
            kind = await service.update_relationship_kind(id, **kwargs)
            if not kind:
                return None
            await db.commit()
            return _relationship_kind_to_type(kind)

    @strawberry.mutation
    async def delete_relationship_kind(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a relationship kind (soft delete)."""
        await check_graphql_permission(
            info, "semantic:type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.service import SemanticService

        async with async_session_factory() as db:
            service = SemanticService(db)
            deleted = await service.delete_relationship_kind(id)
            await db.commit()
            return deleted

    # -- Activity type mutations -------------------------------------------

    @strawberry.mutation
    async def create_semantic_activity_type(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: SemanticActivityTypeInput,
    ) -> SemanticActivityTypeType:
        """Create a semantic activity type."""
        await check_graphql_permission(
            info, "semantic:activity-type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.activity_type_service import ActivityTypeService

        data = {
            "name": input.name,
            "display_name": input.display_name,
            "category": input.category,
            "description": input.description,
            "icon": input.icon,
            "applicable_semantic_categories": input.applicable_semantic_categories,
            "applicable_semantic_types": input.applicable_semantic_types,
            "default_relationship_kind_id": str(input.default_relationship_kind_id) if input.default_relationship_kind_id else None,
            "properties_schema": input.properties_schema,
            "sort_order": input.sort_order,
        }
        async with async_session_factory() as db:
            service = ActivityTypeService(db)
            at = await service.create_activity_type(data)
            await db.commit()
            await db.refresh(at, ["default_relationship_kind"])
            return _activity_type_to_gql(at)

    @strawberry.mutation
    async def update_semantic_activity_type(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: SemanticActivityTypeUpdateInput,
    ) -> SemanticActivityTypeType | None:
        """Update a semantic activity type."""
        await check_graphql_permission(
            info, "semantic:activity-type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.activity_type_service import ActivityTypeService

        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.category is not strawberry.UNSET:
            data["category"] = input.category
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.icon is not strawberry.UNSET:
            data["icon"] = input.icon
        if input.applicable_semantic_categories is not strawberry.UNSET:
            data["applicable_semantic_categories"] = input.applicable_semantic_categories
        if input.applicable_semantic_types is not strawberry.UNSET:
            data["applicable_semantic_types"] = input.applicable_semantic_types
        if input.default_relationship_kind_id is not strawberry.UNSET:
            data["default_relationship_kind_id"] = str(input.default_relationship_kind_id) if input.default_relationship_kind_id else None
        if input.properties_schema is not strawberry.UNSET:
            data["properties_schema"] = input.properties_schema
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        async with async_session_factory() as db:
            service = ActivityTypeService(db)
            at = await service.update_activity_type(str(id), data)
            if not at:
                return None
            await db.commit()
            await db.refresh(at, ["default_relationship_kind"])
            return _activity_type_to_gql(at)

    @strawberry.mutation
    async def delete_semantic_activity_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a semantic activity type (soft delete)."""
        await check_graphql_permission(
            info, "semantic:activity-type:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.semantic.activity_type_service import ActivityTypeService

        async with async_session_factory() as db:
            service = ActivityTypeService(db)
            deleted = await service.delete_activity_type(str(id))
            await db.commit()
            return deleted
