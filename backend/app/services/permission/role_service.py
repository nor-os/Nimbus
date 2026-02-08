"""
Overview: Role management service for CRUD, global system role seeding, and custom role creation.
Architecture: Service layer for role lifecycle operations (Section 3.1, 5.2)
Dependencies: sqlalchemy, app.models
Concepts: RBAC, role management, global system roles, scoped roles (provider/tenant)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole


class RoleError(Exception):
    def __init__(self, message: str, code: str = "ROLE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# System permissions to seed
SYSTEM_PERMISSIONS = [
    ("users", "user", "list", None, "List users"),
    ("users", "user", "read", None, "Read user details"),
    ("users", "user", "create", None, "Create users"),
    ("users", "user", "update", None, "Update users"),
    ("users", "user", "delete", None, "Deactivate users"),
    ("users", "role", "list", None, "List roles"),
    ("users", "role", "read", None, "Read role details"),
    ("users", "role", "create", None, "Create roles"),
    ("users", "role", "update", None, "Update roles"),
    ("users", "role", "delete", None, "Delete roles"),
    ("users", "role", "assign", None, "Assign roles to users"),
    ("users", "group", "list", None, "List groups"),
    ("users", "group", "read", None, "Read group details"),
    ("users", "group", "create", None, "Create groups"),
    ("users", "group", "update", None, "Update groups"),
    ("users", "group", "delete", None, "Delete groups"),
    ("users", "group", "manage_members", None, "Manage group members"),
    ("settings", "idp", "list", None, "List identity providers"),
    ("settings", "idp", "read", None, "Read IdP details"),
    ("settings", "idp", "create", None, "Create identity providers"),
    ("settings", "idp", "update", None, "Update identity providers"),
    ("settings", "idp", "delete", None, "Delete identity providers"),
    ("settings", "scim", "manage", None, "Manage SCIM tokens"),
    ("settings", "tenant", "read", None, "Read tenant settings"),
    ("settings", "tenant", "update", None, "Update tenant settings"),
    ("settings", "tenant", "create", None, "Create tenants"),
    ("settings", "tenant", "delete", None, "Delete tenants"),
    ("permissions", "abac", "list", None, "List ABAC policies"),
    ("permissions", "abac", "create", None, "Create ABAC policies"),
    ("permissions", "abac", "update", None, "Update ABAC policies"),
    ("permissions", "abac", "delete", None, "Delete ABAC policies"),
    ("permissions", "permission", "check", None, "Check permissions"),
    ("permissions", "permission", "simulate", None, "Simulate permissions"),
    ("cmdb", "ci", "list", None, "List configuration items"),
    ("cmdb", "ci", "read", None, "Read configuration items"),
    ("cmdb", "ci", "create", None, "Create configuration items"),
    ("cmdb", "ci", "update", None, "Update configuration items"),
    ("cmdb", "ci", "delete", None, "Delete configuration items"),
    ("audit", "log", "read", None, "Read audit logs"),
    ("*", "*", "*", None, "Full access (wildcard)"),
]

# Provider-scoped roles (root tenant only)
PROVIDER_ROLES = [
    ("Provider Admin", "Full system access", ["*:*:*"]),
    ("Provider Auditor", "Read-only system access", [
        "users:user:list", "users:user:read", "users:role:list", "users:role:read",
        "users:group:list", "users:group:read", "settings:tenant:read",
        "settings:idp:list", "settings:idp:read", "audit:log:read",
        "cmdb:ci:list", "cmdb:ci:read",
    ]),
]

# Tenant-scoped roles (created per tenant)
TENANT_ROLES = [
    ("Tenant Admin", "Full tenant administration", [
        "users:user:list", "users:user:read", "users:user:create",
        "users:user:update", "users:user:delete",
        "users:role:list", "users:role:read", "users:role:create",
        "users:role:update", "users:role:delete", "users:role:assign",
        "users:group:list", "users:group:read", "users:group:create",
        "users:group:update", "users:group:delete", "users:group:manage_members",
        "settings:idp:list", "settings:idp:read", "settings:idp:create",
        "settings:idp:update", "settings:idp:delete",
        "settings:scim:manage", "settings:tenant:read", "settings:tenant:update",
        "permissions:abac:list", "permissions:abac:create",
        "permissions:abac:update", "permissions:abac:delete",
        "permissions:permission:check", "permissions:permission:simulate",
        "cmdb:ci:list", "cmdb:ci:read", "cmdb:ci:create",
        "cmdb:ci:update", "cmdb:ci:delete",
        "audit:log:read",
    ]),
    ("Security Admin", "Security and identity management", [
        "users:user:list", "users:user:read", "users:user:create",
        "users:user:update", "users:user:delete",
        "users:role:list", "users:role:read", "users:role:create",
        "users:role:update", "users:role:assign",
        "users:group:list", "users:group:read", "users:group:create",
        "users:group:update", "users:group:manage_members",
        "settings:idp:list", "settings:idp:read", "settings:idp:create",
        "settings:idp:update", "settings:idp:delete",
        "settings:scim:manage",
        "permissions:abac:list", "permissions:abac:create",
        "permissions:abac:update", "permissions:abac:delete",
        "permissions:permission:check", "permissions:permission:simulate",
        "audit:log:read",
    ]),
    ("Network Admin", "Network and infrastructure management", [
        "cmdb:ci:list", "cmdb:ci:read", "cmdb:ci:create", "cmdb:ci:update",
        "users:user:list", "users:user:read",
    ]),
    ("Power User", "Extended user access", [
        "cmdb:ci:list", "cmdb:ci:read", "cmdb:ci:create", "cmdb:ci:update",
        "users:user:list", "users:user:read",
        "users:group:list", "users:group:read",
        "users:role:list", "users:role:read",
    ]),
    ("Member", "Standard user access", [
        "cmdb:ci:list", "cmdb:ci:read",
        "users:user:list", "users:user:read",
    ]),
    ("Read Only", "Read-only access", [
        "cmdb:ci:list", "cmdb:ci:read",
        "users:user:list", "users:user:read",
        "users:role:list", "users:role:read",
        "users:group:list", "users:group:read",
    ]),
]


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(
        self, tenant_id: str | None = None, include_system: bool = True
    ) -> list[Role]:
        """List roles for a tenant. Returns global system roles plus tenant-specific custom roles."""
        from sqlalchemy import or_

        query = select(Role).where(Role.deleted_at.is_(None))

        if tenant_id:
            # Global system roles (tenant_id IS NULL) + custom roles for this tenant
            query = query.where(
                or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id)
            )

        return list((await self.db.execute(query.order_by(Role.name))).scalars().all())

    async def get_role(self, role_id: str) -> Role | None:
        """Get a role by ID."""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_role(
        self,
        tenant_id: str,
        name: str,
        description: str | None = None,
        scope: str = "tenant",
        parent_role_id: str | None = None,
        permission_ids: list[str] | None = None,
        max_level: int | None = None,
    ) -> Role:
        """Create a custom role."""
        role = Role(
            tenant_id=tenant_id,
            name=name,
            description=description,
            scope=scope,
            parent_role_id=parent_role_id,
            is_custom=True,
            max_level=max_level,
        )
        self.db.add(role)
        await self.db.flush()

        if permission_ids:
            for pid in permission_ids:
                self.db.add(RolePermission(role_id=role.id, permission_id=pid))
            await self.db.flush()

        return role

    async def update_role(
        self,
        role_id: str,
        name: str | None = None,
        description: str | None = None,
        permission_ids: list[str] | None = None,
        max_level: int | None = None,
    ) -> Role:
        """Update a role."""
        role = await self.get_role(role_id)
        if not role:
            raise RoleError("Role not found", "ROLE_NOT_FOUND")

        if role.is_system:
            raise RoleError("Cannot modify system roles", "SYSTEM_ROLE")

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if max_level is not None:
            role.max_level = max_level

        if permission_ids is not None:
            # Replace permissions
            await self.db.execute(
                RolePermission.__table__.delete().where(RolePermission.role_id == role.id)
            )
            for pid in permission_ids:
                self.db.add(RolePermission(role_id=role.id, permission_id=pid))

        await self.db.flush()
        return role

    async def delete_role(self, role_id: str) -> None:
        """Soft-delete a role."""
        from datetime import UTC, datetime

        role = await self.get_role(role_id)
        if not role:
            raise RoleError("Role not found", "ROLE_NOT_FOUND")
        if role.is_system:
            raise RoleError("Cannot delete system roles", "SYSTEM_ROLE")

        role.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        tenant_id: str,
        compartment_id: str | None = None,
        granted_by: str | None = None,
        expires_at=None,
    ) -> UserRole:
        """Assign a role to a user."""
        existing = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none():
            raise RoleError("Role already assigned", "ALREADY_ASSIGNED")

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            compartment_id=compartment_id,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        self.db.add(user_role)
        await self.db.flush()
        return user_role

    async def unassign_role(self, user_id: str, role_id: str, tenant_id: str) -> None:
        """Remove a role assignment from a user."""
        result = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        )
        user_role = result.scalar_one_or_none()
        if not user_role:
            raise RoleError("Role assignment not found", "NOT_ASSIGNED")

        await self.db.delete(user_role)
        await self.db.flush()

    async def get_role_permissions(self, role_id: str) -> list[Permission]:
        """Get all permissions for a role (direct + inherited)."""
        permissions = []
        visited = set()
        role = await self.get_role(role_id)

        while role and role.id not in visited:
            visited.add(role.id)
            result = await self.db.execute(
                select(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role.id)
            )
            permissions.extend(result.scalars().all())

            if role.parent_role_id:
                role = await self.get_role(str(role.parent_role_id))
            else:
                break

        return permissions

    async def seed_system_roles(self) -> list[Role]:
        """Seed all global system roles (provider + tenant scoped) with tenant_id=None."""
        await self._seed_permissions()
        created = []
        created.extend(await self._seed_roles(PROVIDER_ROLES, scope="provider"))
        created.extend(await self._seed_roles(TENANT_ROLES, scope="tenant"))
        return created

    async def _seed_roles(
        self,
        role_definitions: list[tuple[str, str, list[str]]],
        scope: str,
    ) -> list[Role]:
        """Seed global system roles from a definition list with dedup."""
        created_roles = []
        for name, description, perm_keys in role_definitions:
            # Dedup check: same name + system + global (tenant_id IS NULL)
            existing = await self.db.execute(
                select(Role).where(
                    Role.name == name,
                    Role.is_system.is_(True),
                    Role.tenant_id.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                continue

            role = Role(
                tenant_id=None,
                name=name,
                description=description,
                scope=scope,
                is_system=True,
                is_custom=False,
            )
            self.db.add(role)
            await self.db.flush()

            # Assign permissions
            for perm_key in perm_keys:
                parts = perm_key.split(":")
                query = select(Permission).where(
                    Permission.domain == parts[0],
                    Permission.resource == parts[1],
                    Permission.action == parts[2],
                )
                if len(parts) > 3:
                    query = query.where(Permission.subtype == parts[3])
                else:
                    query = query.where(Permission.subtype.is_(None))

                perm_result = await self.db.execute(query)
                perm = perm_result.scalar_one_or_none()
                if perm:
                    self.db.add(RolePermission(role_id=role.id, permission_id=perm.id))

            await self.db.flush()
            created_roles.append(role)

        return created_roles

    async def _seed_permissions(self) -> None:
        """Ensure all system permissions exist."""
        for domain, resource, action, subtype, description in SYSTEM_PERMISSIONS:
            existing = await self.db.execute(
                select(Permission).where(
                    Permission.domain == domain,
                    Permission.resource == resource,
                    Permission.action == action,
                    Permission.subtype == subtype if subtype else Permission.subtype.is_(None),
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(
                    Permission(
                        domain=domain,
                        resource=resource,
                        action=action,
                        subtype=subtype,
                        description=description,
                        is_system=True,
                    )
                )
        await self.db.flush()
