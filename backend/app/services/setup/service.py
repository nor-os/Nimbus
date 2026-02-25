"""
Overview: Setup service for first-run wizard — creates provider, admin, and root tenant.
Architecture: Service layer for initial system setup (Section 3.1)
Dependencies: sqlalchemy, app.models, app.services.auth, app.services.tenant
Concepts: First-run setup, provider creation, admin bootstrap, root tenant
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.group_role import GroupRole

from app.models.provider import Provider
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User
from app.models.user_group import UserGroup
from app.models.user_tenant import UserTenant
from app.services.auth.password import hash_password
from app.services.permission.role_service import RoleService
from app.services.tenant.service import TenantService


class SetupError(Exception):
    def __init__(self, message: str, code: str = "SETUP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SetupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_setup_complete(self) -> bool:
        """Check if the initial setup has been completed."""
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.key == "setup_complete")
        )
        config = result.scalar_one_or_none()
        return config is not None and config.value == "true"

    async def initialize(
        self,
        admin_email: str,
        admin_password: str,
        organization_name: str,
    ) -> tuple[Provider, User]:
        """Complete the first-run setup: create provider, admin user, and root tenant."""
        if await self.is_setup_complete():
            raise SetupError("Setup has already been completed", "ALREADY_SETUP")

        admin_email = admin_email.lower()

        # Create provider (organization)
        provider = Provider(name=organization_name)
        self.db.add(provider)
        await self.db.flush()

        # Create admin user
        user = User(
            email=admin_email,
            password_hash=hash_password(admin_password),
            display_name="Admin",
            provider_id=provider.id,
        )
        self.db.add(user)
        await self.db.flush()

        # Create virtual root tenant
        tenant_service = TenantService(self.db)
        root_tenant = await tenant_service.create_root_tenant(
            name=organization_name,
            provider_id=str(provider.id),
        )

        # Associate admin with root tenant
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=root_tenant.id,
            is_default=True,
        )
        self.db.add(user_tenant)
        await self.db.flush()

        # Local IdP already created by TenantService.create_tenant()

        # Seed all global system roles (provider + tenant scoped)
        role_service = RoleService(self.db)
        await role_service.seed_system_roles()

        # Create "Global Admins" system group
        global_admins = Group(
            tenant_id=root_tenant.id,
            name="Global Admins",
            description="System group with full access",
            is_system=True,
        )
        self.db.add(global_admins)
        await self.db.flush()

        # Assign Provider Admin role to Global Admins
        result = await self.db.execute(
            select(Role).where(
                Role.name == "Provider Admin",
                Role.is_system.is_(True),
                Role.tenant_id.is_(None),
            )
        )
        provider_admin_role = result.scalar_one()
        group_role = GroupRole(group_id=global_admins.id, role_id=provider_admin_role.id)
        self.db.add(group_role)

        # Add admin user to Global Admins
        user_group = UserGroup(user_id=user.id, group_id=global_admins.id)
        self.db.add(user_group)
        await self.db.flush()

        # Mark setup as complete
        self.db.add(SystemConfig(key="setup_complete", value="true"))
        self.db.add(SystemConfig(key="organization_name", value=organization_name))

        await self.db.flush()
        return provider, user
