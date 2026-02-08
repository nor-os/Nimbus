"""
Overview: GraphQL queries for user data.
Architecture: GraphQL query resolvers for user management (Section 7.2)
Dependencies: strawberry, app.services.user
Concepts: GraphQL queries, user management
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.user import UserDetailType, UserType


@strawberry.type
class UserQuery:
    @strawberry.field
    async def users(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
    ) -> list[UserType]:
        """List users for a tenant."""
        await check_graphql_permission(info, "users:user:list", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.user.service import UserService

        async with async_session_factory() as db:
            service = UserService(db)
            users, _total = await service.list_users(
                str(tenant_id), offset, limit, search
            )
            return [
                UserType(
                    id=u.id,
                    email=u.email,
                    display_name=u.display_name,
                    is_active=u.is_active,
                    provider_id=u.provider_id,
                    identity_provider_id=u.identity_provider_id,
                    external_id=u.external_id,
                    created_at=u.created_at,
                    updated_at=u.updated_at,
                )
                for u in users
            ]

    @strawberry.field
    async def user(
        self, info: Info, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> UserType | None:
        """Get a single user by ID."""
        await check_graphql_permission(info, "users:user:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.user.service import UserService

        async with async_session_factory() as db:
            service = UserService(db)
            user = await service.get_user(str(user_id), str(tenant_id))
            if not user:
                return None
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
