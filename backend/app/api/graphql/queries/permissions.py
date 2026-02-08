"""
Overview: GraphQL queries for roles, groups, and permissions.
Architecture: GraphQL query resolvers for RBAC (Section 7.2)
Dependencies: strawberry, app.services.permission
Concepts: GraphQL queries, RBAC, permission checking
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.permission import (
    EffectivePermissionType,
    GroupType,
    PermissionCheckResultType,
    PermissionType,
    RoleType,
)


@strawberry.type
class PermissionQuery:
    @strawberry.field
    async def roles(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[RoleType]:
        """List roles for a tenant."""
        await check_graphql_permission(info, "users:role:list", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.role_service import RoleService

        async with async_session_factory() as db:
            service = RoleService(db)
            roles = await service.list_roles(str(tenant_id))
            return [
                RoleType(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    name=r.name,
                    description=r.description,
                    is_system=r.is_system,
                    is_custom=r.is_custom,
                    scope=r.scope,
                    parent_role_id=r.parent_role_id,
                    max_level=r.max_level,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in roles
            ]

    @strawberry.field
    async def groups(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[GroupType]:
        """List groups for a tenant."""
        await check_graphql_permission(info, "users:group:list", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.group_service import GroupService

        async with async_session_factory() as db:
            service = GroupService(db)
            groups = await service.list_groups(str(tenant_id))
            return [
                GroupType(
                    id=g.id,
                    tenant_id=g.tenant_id,
                    name=g.name,
                    description=g.description,
                    created_at=g.created_at,
                    updated_at=g.updated_at,
                )
                for g in groups
            ]

    @strawberry.field
    async def my_permissions(
        self, info: Info, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[EffectivePermissionType]:
        """Get effective permissions for a user."""
        from app.db.session import async_session_factory
        from app.services.permission.engine import PermissionEngine

        async with async_session_factory() as db:
            engine = PermissionEngine(db)
            effective = await engine.get_effective_permissions(str(user_id), str(tenant_id))
            return [
                EffectivePermissionType(
                    permission_key=ep.permission_key,
                    source=ep.source,
                    role_name=ep.role_name,
                    group_name=ep.group_name,
                    source_tenant_id=ep.source_tenant_id or None,
                    source_tenant_name=ep.source_tenant_name or None,
                    is_inherited=ep.is_inherited,
                    is_denied=ep.is_denied,
                    deny_source=ep.deny_source,
                )
                for ep in effective
            ]

    @strawberry.field
    async def check_permission(
        self,
        info: Info,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        permission_key: str,
    ) -> PermissionCheckResultType:
        """Check if a user has a specific permission."""
        await check_graphql_permission(info, "permissions:permission:check", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.permission.engine import PermissionEngine

        async with async_session_factory() as db:
            engine = PermissionEngine(db)
            allowed, source = await engine.check_permission(
                str(user_id), permission_key, str(tenant_id)
            )
            return PermissionCheckResultType(
                allowed=allowed, permission_key=permission_key, source=source
            )
