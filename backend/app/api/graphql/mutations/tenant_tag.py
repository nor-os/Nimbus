"""
Overview: GraphQL mutations for tenant tags — create, update, delete.
Architecture: GraphQL mutation resolvers for tag write operations (Section 3.2)
Dependencies: strawberry, app.services.tenant.tag_service
Concepts: All mutations enforce permission checks and return the updated tag.
"""

from __future__ import annotations

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.tenant_tag import _tag_to_gql
from app.api.graphql.types.tenant_tag import (
    TenantTagCreateInput,
    TenantTagType,
    TenantTagUpdateInput,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class TenantTagMutation:

    @strawberry.mutation
    async def create_tenant_tag(
        self, info: Info, tenant_id: uuid.UUID, input: TenantTagCreateInput
    ) -> TenantTagType:
        """Create a new tenant tag."""
        await check_graphql_permission(info, "settings:tag:create", str(tenant_id))

        from app.services.tenant.tag_service import TenantTagService

        db = await _get_session(info)
        service = TenantTagService(db)
        tag = await service.create_tag(str(tenant_id), {
            "key": input.key,
            "display_name": input.display_name or input.key,
            "description": input.description,
            "value_schema": input.value_schema,
            "value": input.value,
            "is_secret": input.is_secret,
            "sort_order": input.sort_order,
        })
        await db.commit()
        return _tag_to_gql(tag, mask_secrets=False)

    @strawberry.mutation
    async def update_tenant_tag(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID, input: TenantTagUpdateInput
    ) -> TenantTagType:
        """Update an existing tenant tag."""
        await check_graphql_permission(info, "settings:tag:update", str(tenant_id))

        from app.services.tenant.tag_service import TenantTagService

        db = await _get_session(info)
        service = TenantTagService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.value_schema is not strawberry.UNSET:
            data["value_schema"] = input.value_schema
        if input.value is not strawberry.UNSET:
            data["value"] = input.value
        if input.is_secret is not None:
            data["is_secret"] = input.is_secret
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        tag = await service.update_tag(id, str(tenant_id), data)
        await db.commit()
        return _tag_to_gql(tag, mask_secrets=False)

    @strawberry.mutation
    async def delete_tenant_tag(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete a tenant tag."""
        await check_graphql_permission(info, "settings:tag:delete", str(tenant_id))

        from app.services.tenant.tag_service import TenantTagService

        db = await _get_session(info)
        service = TenantTagService(db)
        result = await service.delete_tag(id, str(tenant_id))
        await db.commit()
        return result
