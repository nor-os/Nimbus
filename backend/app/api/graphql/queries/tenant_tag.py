"""
Overview: GraphQL queries for tenant tags — list, get by ID, get by key.
Architecture: GraphQL query resolvers for tag read operations (Section 3.2)
Dependencies: strawberry, app.services.tenant.tag_service
Concepts: Read-only queries with permission checks. Secret tag values are masked.
"""

from __future__ import annotations

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.tenant_tag import TenantTagListType, TenantTagType


def _tag_to_gql(tag, mask_secrets: bool = True) -> TenantTagType:
    value = tag.value
    if mask_secrets and tag.is_secret and value is not None:
        value = "***"
    return TenantTagType(
        id=tag.id,
        tenant_id=tag.tenant_id,
        key=tag.key,
        display_name=tag.display_name,
        description=tag.description,
        value_schema=tag.value_schema,
        value=value,
        is_secret=tag.is_secret,
        sort_order=tag.sort_order,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


@strawberry.type
class TenantTagQuery:

    @strawberry.field
    async def tenant_tags(
        self, info: Info, tenant_id: uuid.UUID, search: str | None = None
    ) -> TenantTagListType:
        """List all tags for a tenant."""
        await check_graphql_permission(info, "settings:tag:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.tenant.tag_service import TenantTagService

        async with async_session_factory() as db:
            service = TenantTagService(db)
            tags = await service.list_tags(str(tenant_id), search)
            return TenantTagListType(
                items=[_tag_to_gql(t) for t in tags],
                total=len(tags),
            )

    @strawberry.field
    async def tenant_tag(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> TenantTagType | None:
        """Get a single tag by ID."""
        await check_graphql_permission(info, "settings:tag:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.tenant.tag_service import TenantTagService

        async with async_session_factory() as db:
            service = TenantTagService(db)
            tag = await service.get_tag(id, str(tenant_id))
            if not tag:
                return None
            return _tag_to_gql(tag)

    @strawberry.field
    async def tenant_tag_by_key(
        self, info: Info, tenant_id: uuid.UUID, key: str
    ) -> TenantTagType | None:
        """Get a tag by its unique key."""
        await check_graphql_permission(info, "settings:tag:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.tenant.tag_service import TenantTagService

        async with async_session_factory() as db:
            service = TenantTagService(db)
            tag = await service.get_tag_by_key(str(tenant_id), key)
            if not tag:
                return None
            return _tag_to_gql(tag)
