"""
Overview: GraphQL mutations for roles, groups, and role assignments.
Architecture: GraphQL mutation resolvers for RBAC (Section 7.2)
Dependencies: strawberry, app.services.permission
Concepts: GraphQL mutations, RBAC, role management
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.permission import GroupType, RoleType


@strawberry.input
class RoleCreateInput:
    name: str
    description: str | None = None
    scope: str | None = None
    parent_role_id: uuid.UUID | None = None
    permission_ids: list[uuid.UUID] = strawberry.field(default_factory=list)


@strawberry.input
class GroupCreateInput:
    name: str
    description: str | None = None


@strawberry.input
class RoleAssignInput:
    user_id: uuid.UUID
    role_id: uuid.UUID
    compartment_id: uuid.UUID | None = None


@strawberry.input
class GroupMemberInput:
    user_id: uuid.UUID
    group_id: uuid.UUID


@strawberry.type
class PermissionMutation:
    @strawberry.mutation
    async def create_role(
        self, info: Info, tenant_id: uuid.UUID, input: RoleCreateInput
    ) -> RoleType:
        """Create a custom role."""
        await check_graphql_permission(info, "users:role:create", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.role_service import RoleService

        async with async_session_factory() as db:
            service = RoleService(db)
            role = await service.create_role(
                tenant_id=str(tenant_id),
                name=input.name,
                description=input.description,
                scope=input.scope or "tenant",
                parent_role_id=str(input.parent_role_id) if input.parent_role_id else None,
                permission_ids=[str(pid) for pid in input.permission_ids],
            )
            await db.commit()
            return RoleType(
                id=role.id,
                tenant_id=role.tenant_id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                is_custom=role.is_custom,
                scope=role.scope,
                parent_role_id=role.parent_role_id,
                max_level=role.max_level,
                created_at=role.created_at,
                updated_at=role.updated_at,
            )

    @strawberry.mutation
    async def assign_role(
        self, info: Info, tenant_id: uuid.UUID, input: RoleAssignInput
    ) -> bool:
        """Assign a role to a user."""
        await check_graphql_permission(info, "users:role:assign", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.role_service import RoleService

        async with async_session_factory() as db:
            service = RoleService(db)
            await service.assign_role(
                user_id=str(input.user_id),
                role_id=str(input.role_id),
                tenant_id=str(tenant_id),
                compartment_id=str(input.compartment_id) if input.compartment_id else None,
            )
            await db.commit()
            return True

    @strawberry.mutation
    async def create_group(
        self, info: Info, tenant_id: uuid.UUID, input: GroupCreateInput
    ) -> GroupType:
        """Create a new group."""
        await check_graphql_permission(info, "users:group:create", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.group_service import GroupService

        async with async_session_factory() as db:
            service = GroupService(db)
            group = await service.create_group(
                tenant_id=str(tenant_id),
                name=input.name,
                description=input.description,
            )
            await db.commit()
            return GroupType(
                id=group.id,
                tenant_id=group.tenant_id,
                name=group.name,
                description=group.description,
                created_at=group.created_at,
                updated_at=group.updated_at,
            )

    @strawberry.mutation
    async def add_group_member(
        self, info: Info, input: GroupMemberInput
    ) -> bool:
        """Add a user to a group."""
        from app.db.session import async_session_factory
        from app.services.permission.group_service import GroupService

        async with async_session_factory() as db:
            service = GroupService(db)
            await service.add_member(str(input.group_id), str(input.user_id))
            await db.commit()
            return True
