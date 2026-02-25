"""
Overview: GraphQL mutations for user management.
Architecture: GraphQL mutation resolvers for user lifecycle (Section 7.2)
Dependencies: strawberry, app.services.user
Concepts: GraphQL mutations, user management
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.user import UserType


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory

    return async_session_factory()


@strawberry.input
class UserCreateInput:
    email: str
    password: str | None = None
    display_name: str | None = None
    role_ids: list[uuid.UUID] = strawberry.field(default_factory=list)
    group_ids: list[uuid.UUID] = strawberry.field(default_factory=list)


@strawberry.input
class UserUpdateInput:
    display_name: str | None = None
    is_active: bool | None = None


@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def create_user(
        self, info: Info, tenant_id: uuid.UUID, input: UserCreateInput
    ) -> UserType:
        """Create a new user in a tenant."""
        await check_graphql_permission(info, "users:user:create", str(tenant_id))
        from app.services.user.service import UserService

        db = await _get_session(info)
        service = UserService(db)
        user = await service.create_user(
            tenant_id=str(tenant_id),
            email=input.email,
            password=input.password,
            display_name=input.display_name,
            role_ids=[str(rid) for rid in input.role_ids],
            group_ids=[str(gid) for gid in input.group_ids],
        )
        await db.commit()
        return UserType(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            provider_id=user.provider_id,
            identity_provider_id=user.identity_provider_id,
            external_id=user.external_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @strawberry.mutation
    async def update_user(
        self,
        info: Info,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        input: UserUpdateInput,
    ) -> UserType:
        """Update a user."""
        await check_graphql_permission(info, "users:user:update", str(tenant_id))
        from app.services.user.service import UserService

        db = await _get_session(info)
        service = UserService(db)
        user = await service.update_user(
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            display_name=input.display_name,
            is_active=input.is_active,
        )
        await db.commit()
        return UserType(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            provider_id=user.provider_id,
            identity_provider_id=user.identity_provider_id,
            external_id=user.external_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @strawberry.mutation
    async def deactivate_user(
        self, info: Info, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        """Deactivate (soft-delete) a user."""
        await check_graphql_permission(info, "users:user:delete", str(tenant_id))
        from app.services.user.service import UserService

        db = await _get_session(info)
        service = UserService(db)
        await service.deactivate_user(str(user_id), str(tenant_id))
        await db.commit()
        return True
