"""
Overview: GraphQL mutations for OS image catalog CRUD.
Architecture: GraphQL mutation resolvers for OS image management (Section 5)
Dependencies: strawberry, app.services.semantic.image_service
Concepts: Create/update/delete with permission checks, system record protection
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.os_image import _mapping_to_gql, _os_image_to_gql
from app.api.graphql.types.os_image import (
    OsImageInput,
    OsImageProviderMappingInput,
    OsImageProviderMappingType,
    OsImageProviderMappingUpdateInput,
    OsImageType,
    OsImageUpdateInput,
    SetImageTenantsInput,
)

logger = logging.getLogger(__name__)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class OsImageMutation:
    # -- Image mutations -----------------------------------------------------

    @strawberry.mutation
    async def create_os_image(
        self, info: Info, tenant_id: uuid.UUID, input: OsImageInput
    ) -> OsImageType:
        """Create a new OS image."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        image = await service.create_image(
            name=input.name,
            display_name=input.display_name,
            os_family=input.os_family,
            version=input.version,
            architecture=input.architecture,
            description=input.description,
            icon=input.icon,
            sort_order=input.sort_order,
        )
        await db.commit()
        image = await service.get_image(image.id)
        return _os_image_to_gql(image)

    @strawberry.mutation
    async def update_os_image(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: OsImageUpdateInput,
    ) -> OsImageType | None:
        """Update an OS image."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        kwargs = {}
        if input.display_name is not None:
            kwargs["display_name"] = input.display_name
        if input.os_family is not None:
            kwargs["os_family"] = input.os_family
        if input.version is not None:
            kwargs["version"] = input.version
        if input.architecture is not None:
            kwargs["architecture"] = input.architecture
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.icon is not strawberry.UNSET:
            kwargs["icon"] = input.icon
        if input.sort_order is not None:
            kwargs["sort_order"] = input.sort_order

        db = await _get_session(info)
        service = ImageService(db)
        image = await service.update_image(id, **kwargs)
        if not image:
            return None
        await db.commit()
        return _os_image_to_gql(image)

    @strawberry.mutation
    async def delete_os_image(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an OS image (soft delete)."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        deleted = await service.delete_image(id)
        await db.commit()
        return deleted

    # -- Tenant assignment mutations -----------------------------------------

    @strawberry.mutation
    async def set_os_image_tenants(
        self, info: Info, tenant_id: uuid.UUID, input: SetImageTenantsInput
    ) -> OsImageType | None:
        """Set tenant assignments for an OS image (diff-based)."""
        await check_graphql_permission(info, "semantic:image:assign", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        await service.set_image_tenants(input.os_image_id, input.tenant_ids)
        await db.commit()
        image = await service.get_image(input.os_image_id)
        if not image:
            return None
        return _os_image_to_gql(image)

    # -- Provider mapping mutations ------------------------------------------

    @strawberry.mutation
    async def create_os_image_provider_mapping(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: OsImageProviderMappingInput,
    ) -> OsImageProviderMappingType:
        """Create a new OS image provider mapping."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        mapping = await service.create_provider_mapping(
            os_image_id=input.os_image_id,
            provider_id=input.provider_id,
            image_reference=input.image_reference,
            notes=input.notes,
        )
        await db.commit()
        mapping = await service.get_provider_mapping(mapping.id)
        return _mapping_to_gql(mapping)

    @strawberry.mutation
    async def update_os_image_provider_mapping(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: OsImageProviderMappingUpdateInput,
    ) -> OsImageProviderMappingType | None:
        """Update an OS image provider mapping."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        kwargs = {}
        if input.image_reference is not None:
            kwargs["image_reference"] = input.image_reference
        if input.notes is not strawberry.UNSET:
            kwargs["notes"] = input.notes

        db = await _get_session(info)
        service = ImageService(db)
        mapping = await service.update_provider_mapping(id, **kwargs)
        if not mapping:
            return None
        await db.commit()
        return _mapping_to_gql(mapping)

    @strawberry.mutation
    async def delete_os_image_provider_mapping(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an OS image provider mapping (soft delete)."""
        await check_graphql_permission(info, "semantic:image:manage", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        deleted = await service.delete_provider_mapping(id)
        await db.commit()
        return deleted
