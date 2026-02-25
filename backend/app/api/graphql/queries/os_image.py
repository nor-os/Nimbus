"""
Overview: GraphQL queries for the OS image catalog.
Architecture: GraphQL query resolvers for OS image management (Section 5)
Dependencies: strawberry, app.services.semantic.image_service
Concepts: Read-only catalog queries with permission checks and converter helpers.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.os_image import (
    OsImageListType,
    OsImageProviderMappingType,
    OsImageTenantAssignmentType,
    OsImageType,
)


def _mapping_to_gql(m) -> OsImageProviderMappingType:
    return OsImageProviderMappingType(
        id=m.id,
        os_image_id=m.os_image_id,
        provider_id=m.provider_id,
        provider_name=m.provider.name if m.provider else "",
        provider_display_name=m.provider.display_name if m.provider else "",
        image_reference=m.image_reference,
        notes=m.notes,
        is_system=m.is_system,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _assignment_to_gql(a) -> OsImageTenantAssignmentType:
    return OsImageTenantAssignmentType(
        id=a.id,
        os_image_id=a.os_image_id,
        tenant_id=a.tenant_id,
        tenant_name=a.tenant.name if a.tenant else "",
        created_at=a.created_at,
    )


def _os_image_to_gql(img) -> OsImageType:
    active_mappings = [
        m for m in (img.provider_mappings or []) if m.deleted_at is None
    ]
    return OsImageType(
        id=img.id,
        name=img.name,
        display_name=img.display_name,
        os_family=img.os_family,
        version=img.version,
        architecture=img.architecture,
        description=img.description,
        icon=img.icon,
        sort_order=img.sort_order,
        is_system=img.is_system,
        provider_mappings=[_mapping_to_gql(m) for m in active_mappings],
        tenant_assignments=[_assignment_to_gql(a) for a in (img.tenant_assignments or [])],
        created_at=img.created_at,
        updated_at=img.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class OsImageQuery:
    @strawberry.field
    async def os_images(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        os_family: str | None = None,
        architecture: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> OsImageListType:
        """List OS images with filtering and pagination."""
        await check_graphql_permission(info, "semantic:image:read", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        items, total = await service.list_images(
            os_family=os_family,
            architecture=architecture,
            search=search,
            offset=offset,
            limit=limit,
        )
        return OsImageListType(
            items=[_os_image_to_gql(img) for img in items],
            total=total,
        )

    @strawberry.field
    async def os_image(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> OsImageType | None:
        """Get a single OS image by ID."""
        await check_graphql_permission(info, "semantic:image:read", str(tenant_id))

        from app.services.semantic.image_service import ImageService

        db = await _get_session(info)
        service = ImageService(db)
        img = await service.get_image(id)
        if not img:
            return None
        return _os_image_to_gql(img)
