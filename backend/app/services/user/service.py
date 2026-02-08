"""
Overview: User service handling user lifecycle within tenant context.
Architecture: Service layer for user CRUD (Section 3.1, 5.1)
Dependencies: sqlalchemy, app.models, app.services.auth.password
Concepts: User management, tenant-scoped users, SSO user provisioning
"""

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.user_group import UserGroup
from app.models.user_role import UserRole
from app.models.user_tenant import UserTenant
from app.services.auth.password import hash_password


class UserError(Exception):
    def __init__(self, message: str, code: str = "USER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        """List users belonging to a tenant with optional search."""
        base_query = (
            select(User)
            .join(UserTenant, UserTenant.user_id == User.id)
            .where(UserTenant.tenant_id == tenant_id, User.deleted_at.is_(None))
        )

        if search:
            base_query = base_query.where(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.display_name.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        result = await self.db.execute(
            base_query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        users = list(result.scalars().all())
        return users, total

    async def get_user(self, user_id: str, tenant_id: str) -> User | None:
        """Get a user by ID, verifying tenant membership."""
        result = await self.db.execute(
            select(User)
            .join(UserTenant, UserTenant.user_id == User.id)
            .where(
                User.id == user_id,
                UserTenant.tenant_id == tenant_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _check_email_domain(self, email: str, tenant_id: str) -> None:
        """Ensure the email domain matches one of the tenant's configured domain mappings.

        Skips validation when the tenant has no domain mappings configured (e.g. root
        tenant during initial setup).
        """
        from app.models.domain_mapping import DomainMapping

        parts = email.rsplit("@", 1)
        if len(parts) != 2 or not parts[1]:
            raise UserError("Invalid email format — must contain @domain", "INVALID_EMAIL")

        email_domain = parts[1].lower()

        result = await self.db.execute(
            select(DomainMapping.domain).where(DomainMapping.tenant_id == tenant_id)
        )
        allowed_domains = [row[0] for row in result.all()]

        if not allowed_domains:
            return

        if email_domain not in allowed_domains:
            raise UserError(
                f"Email domain '{email_domain}' is not allowed for this tenant. "
                f"Allowed domains: {', '.join(sorted(allowed_domains))}",
                "EMAIL_DOMAIN_NOT_ALLOWED",
            )

    async def create_user(
        self,
        tenant_id: str,
        email: str,
        password: str | None = None,
        display_name: str | None = None,
        role_ids: list[str] | None = None,
        group_ids: list[str] | None = None,
        identity_provider_id: str | None = None,
        external_id: str | None = None,
        provider_id: str | None = None,
    ) -> User:
        """Create a new user and associate with the tenant."""
        # Check for existing user with same email (exclude soft-deleted)
        existing = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise UserError("User with this email already exists", "EMAIL_EXISTS")

        # Validate email domain against tenant's configured domains
        await self._check_email_domain(email, tenant_id)

        if not identity_provider_id and not password:
            raise UserError(
                "Password is required for local authentication", "PASSWORD_REQUIRED"
            )

        # Resolve provider_id from tenant if not given
        if not provider_id:
            from app.models.tenant import Tenant

            tenant_result = await self.db.execute(
                select(Tenant.provider_id).where(Tenant.id == tenant_id)
            )
            provider_id = str(tenant_result.scalar_one())

        user = User(
            email=email,
            password_hash=hash_password(password) if password else None,
            display_name=display_name,
            provider_id=provider_id,
            identity_provider_id=identity_provider_id,
            external_id=external_id,
        )
        self.db.add(user)
        await self.db.flush()

        # Associate with tenant
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            is_default=True,
        )
        self.db.add(user_tenant)

        # Assign roles
        if role_ids:
            for role_id in role_ids:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role_id,
                    tenant_id=tenant_id,
                )
                self.db.add(user_role)

        # Assign groups
        if group_ids:
            for group_id in group_ids:
                user_group = UserGroup(
                    user_id=user.id,
                    group_id=group_id,
                )
                self.db.add(user_group)

        await self.db.flush()
        return user

    async def update_user(
        self,
        user_id: str,
        tenant_id: str,
        display_name: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update user attributes."""
        user = await self.get_user(user_id, tenant_id)
        if not user:
            raise UserError("User not found", "USER_NOT_FOUND")

        if display_name is not None:
            user.display_name = display_name
        if is_active is not None:
            user.is_active = is_active

        await self.db.flush()
        return user

    async def deactivate_user(self, user_id: str, tenant_id: str) -> User:
        """Soft-delete a user (deactivate)."""
        user = await self.get_user(user_id, tenant_id)
        if not user:
            raise UserError("User not found", "USER_NOT_FOUND")

        user.is_active = False
        user.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return user

    async def assign_user_to_tenant(
        self, user_id: str, tenant_id: str, is_default: bool = False
    ) -> UserTenant:
        """Assign a user to a tenant."""
        existing = await self.db.execute(
            select(UserTenant).where(
                UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id
            )
        )
        if existing.scalar_one_or_none():
            raise UserError("User already assigned to this tenant", "ALREADY_ASSIGNED")

        user_tenant = UserTenant(
            user_id=user_id,
            tenant_id=tenant_id,
            is_default=is_default,
        )
        self.db.add(user_tenant)
        await self.db.flush()
        return user_tenant

    async def remove_user_from_tenant(self, user_id: str, tenant_id: str) -> None:
        """Remove a user from a tenant."""
        result = await self.db.execute(
            select(UserTenant).where(
                UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id
            )
        )
        user_tenant = result.scalar_one_or_none()
        if not user_tenant:
            raise UserError("User not assigned to this tenant", "NOT_ASSIGNED")

        await self.db.delete(user_tenant)
        await self.db.flush()

    async def get_user_by_external_id(
        self, identity_provider_id: str, external_id: str
    ) -> User | None:
        """Find a user by their external identity provider ID."""
        result = await self.db.execute(
            select(User).where(
                User.identity_provider_id == identity_provider_id,
                User.external_id == external_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_sso_user(
        self,
        tenant_id: str,
        idp_id: str,
        external_id: str,
        email: str,
        display_name: str | None = None,
    ) -> tuple[User, bool]:
        """Get or create a user from SSO login (JIT provisioning)."""
        user = await self.get_user_by_external_id(idp_id, external_id)
        if user:
            # Update display name if changed
            if display_name and user.display_name != display_name:
                user.display_name = display_name
                await self.db.flush()
            return user, False

        # Also check by email
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user:
            # Link existing user to this IdP
            user.identity_provider_id = idp_id
            user.external_id = external_id
            if display_name:
                user.display_name = display_name
            await self.db.flush()

            # Ensure tenant association
            existing_tenant = await self.db.execute(
                select(UserTenant).where(
                    UserTenant.user_id == user.id, UserTenant.tenant_id == tenant_id
                )
            )
            if not existing_tenant.scalar_one_or_none():
                self.db.add(
                    UserTenant(user_id=user.id, tenant_id=tenant_id, is_default=False)
                )
                await self.db.flush()

            return user, False

        # Create new user
        user = await self.create_user(
            tenant_id=tenant_id,
            email=email,
            display_name=display_name,
            identity_provider_id=idp_id,
            external_id=external_id,
        )
        return user, True
