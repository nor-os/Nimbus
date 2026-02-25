"""
Overview: SCIM v2 service implementing user and group provisioning operations.
Architecture: SCIM protocol implementation with Nimbus model mapping (Section 5.1)
Dependencies: sqlalchemy, app.models, app.services.scim.filter_parser
Concepts: SCIM, user provisioning, group provisioning, PATCH operations
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.user import User
from app.models.user_group import UserGroup
from app.models.user_tenant import UserTenant
from app.services.auth.password import hash_password
from app.services.scim.filter_parser import (
    get_group_attr_map,
    get_user_attr_map,
    parse_scim_filter,
)


class SCIMError(Exception):
    def __init__(self, message: str, status: int = 400, scim_type: str | None = None):
        self.message = message
        self.status = status
        self.scim_type = scim_type
        super().__init__(message)


class SCIMService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ── Users ────────────────────────────────────────────────────────

    async def list_users(
        self,
        filter_str: str | None = None,
        start_index: int = 1,
        count: int = 100,
    ) -> tuple[list[dict], int]:
        """List users with optional SCIM filtering."""
        query = (
            select(User)
            .join(UserTenant, UserTenant.user_id == User.id)
            .where(UserTenant.tenant_id == self.tenant_id, User.deleted_at.is_(None))
        )

        if filter_str:
            condition = parse_scim_filter(filter_str, User, get_user_attr_map())
            if condition is not None:
                query = query.where(condition)

        total_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_query)).scalar() or 0

        result = await self.db.execute(
            query.offset(start_index - 1).limit(count)
        )
        users = result.scalars().all()

        return [self._user_to_scim(u) for u in users], total

    async def get_user(self, user_id: str) -> dict:
        """Get a single user as SCIM resource."""
        user = await self._get_tenant_user(user_id)
        if not user:
            raise SCIMError("User not found", 404)
        return self._user_to_scim(user)

    async def _check_email_domain(self, email: str) -> None:
        """Validate the email domain against the tenant's configured domain mappings."""
        from app.models.domain_mapping import DomainMapping

        parts = email.rsplit("@", 1)
        if len(parts) != 2 or not parts[1]:
            raise SCIMError("Invalid email format — must contain @domain", 400, "invalidValue")

        email_domain = parts[1].lower()

        result = await self.db.execute(
            select(DomainMapping.domain).where(DomainMapping.tenant_id == self.tenant_id)
        )
        allowed_domains = [row[0] for row in result.all()]

        if not allowed_domains:
            return

        if email_domain not in allowed_domains:
            raise SCIMError(
                f"Email domain '{email_domain}' is not allowed for this tenant. "
                f"Allowed domains: {', '.join(sorted(allowed_domains))}",
                400,
                "invalidValue",
            )

    async def create_user(self, scim_data: dict) -> dict:
        """Create a user from SCIM resource."""
        email = scim_data.get("userName")
        if not email:
            emails = scim_data.get("emails", [])
            if emails:
                email = emails[0].get("value") if isinstance(emails[0], dict) else emails[0]

        if not email:
            raise SCIMError("userName or emails.value is required", 400, "invalidValue")

        email = email.lower()

        # Validate email domain against tenant's configured domains
        await self._check_email_domain(email)

        # Check for existing user (exclude soft-deleted)
        existing = await self.db.execute(
            select(User).where(
                func.lower(User.email) == email, User.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise SCIMError("User already exists", 409, "uniqueness")

        display_name = scim_data.get("displayName")
        name = scim_data.get("name", {})
        if not display_name and name:
            display_name = name.get("formatted") or f"{name.get('givenName', '')} {name.get('familyName', '')}".strip()

        external_id = scim_data.get("externalId")
        active = scim_data.get("active", True)

        # Resolve provider_id from tenant
        from app.models.tenant import Tenant

        tenant_result = await self.db.execute(
            select(Tenant.provider_id).where(Tenant.id == self.tenant_id)
        )
        provider_id = tenant_result.scalar_one()

        user = User(
            email=email,
            display_name=display_name,
            is_active=active,
            provider_id=provider_id,
            external_id=external_id,
        )
        self.db.add(user)
        await self.db.flush()

        # Associate with tenant
        self.db.add(UserTenant(user_id=user.id, tenant_id=self.tenant_id, is_default=True))
        await self.db.flush()

        return self._user_to_scim(user)

    async def update_user(self, user_id: str, scim_data: dict) -> dict:
        """Full replace (PUT) a user from SCIM resource."""
        user = await self._get_tenant_user(user_id)
        if not user:
            raise SCIMError("User not found", 404)

        if "userName" in scim_data:
            await self._check_email_domain(scim_data["userName"])
            user.email = scim_data["userName"]
        if "displayName" in scim_data:
            user.display_name = scim_data["displayName"]
        if "active" in scim_data:
            user.is_active = scim_data["active"]
        if "externalId" in scim_data:
            user.external_id = scim_data["externalId"]

        name = scim_data.get("name", {})
        if name and not scim_data.get("displayName"):
            user.display_name = name.get("formatted") or f"{name.get('givenName', '')} {name.get('familyName', '')}".strip()

        await self.db.flush()
        return self._user_to_scim(user)

    async def patch_user(self, user_id: str, operations: list[dict]) -> dict:
        """PATCH a user with SCIM PatchOp."""
        user = await self._get_tenant_user(user_id)
        if not user:
            raise SCIMError("User not found", 404)

        for op in operations:
            await self._apply_user_patch(user, op)

        await self.db.flush()
        return self._user_to_scim(user)

    async def delete_user(self, user_id: str) -> None:
        """Soft-delete a user via SCIM."""
        user = await self._get_tenant_user(user_id)
        if not user:
            raise SCIMError("User not found", 404)

        user.is_active = False
        user.deleted_at = datetime.now(UTC)
        await self.db.flush()

    # ── Groups ───────────────────────────────────────────────────────

    async def list_groups(
        self,
        filter_str: str | None = None,
        start_index: int = 1,
        count: int = 100,
    ) -> tuple[list[dict], int]:
        """List groups with optional SCIM filtering."""
        query = select(Group).where(
            Group.tenant_id == self.tenant_id, Group.deleted_at.is_(None)
        )

        if filter_str:
            condition = parse_scim_filter(filter_str, Group, get_group_attr_map())
            if condition is not None:
                query = query.where(condition)

        total_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_query)).scalar() or 0

        result = await self.db.execute(query.offset(start_index - 1).limit(count))
        groups = result.scalars().all()

        return [await self._group_to_scim(g) for g in groups], total

    async def get_group(self, group_id: str) -> dict:
        """Get a single group as SCIM resource."""
        group = await self._get_tenant_group(group_id)
        if not group:
            raise SCIMError("Group not found", 404)
        return await self._group_to_scim(group)

    async def create_group(self, scim_data: dict) -> dict:
        """Create a group from SCIM resource."""
        display_name = scim_data.get("displayName")
        if not display_name:
            raise SCIMError("displayName is required", 400, "invalidValue")

        group = Group(
            tenant_id=self.tenant_id,
            name=display_name,
        )
        self.db.add(group)
        await self.db.flush()

        # Add members
        members = scim_data.get("members", [])
        for member in members:
            self.db.add(UserGroup(user_id=member["value"], group_id=group.id))
        await self.db.flush()

        return await self._group_to_scim(group)

    async def update_group(self, group_id: str, scim_data: dict) -> dict:
        """Full replace (PUT) a group from SCIM resource."""
        group = await self._get_tenant_group(group_id)
        if not group:
            raise SCIMError("Group not found", 404)

        if "displayName" in scim_data:
            group.name = scim_data["displayName"]

        # Replace members
        await self.db.execute(
            UserGroup.__table__.delete().where(UserGroup.group_id == group.id)
        )
        members = scim_data.get("members", [])
        for member in members:
            self.db.add(UserGroup(user_id=member["value"], group_id=group.id))

        await self.db.flush()
        return await self._group_to_scim(group)

    async def patch_group(self, group_id: str, operations: list[dict]) -> dict:
        """PATCH a group with SCIM PatchOp."""
        group = await self._get_tenant_group(group_id)
        if not group:
            raise SCIMError("Group not found", 404)

        for op in operations:
            await self._apply_group_patch(group, op)

        await self.db.flush()
        return await self._group_to_scim(group)

    async def delete_group(self, group_id: str) -> None:
        """Soft-delete a group via SCIM."""
        group = await self._get_tenant_group(group_id)
        if not group:
            raise SCIMError("Group not found", 404)

        group.deleted_at = datetime.now(UTC)
        await self.db.flush()

    # ── Private helpers ──────────────────────────────────────────────

    async def _get_tenant_user(self, user_id: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .join(UserTenant, UserTenant.user_id == User.id)
            .where(
                User.id == user_id,
                UserTenant.tenant_id == self.tenant_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_group(self, group_id: str) -> Group | None:
        result = await self.db.execute(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == self.tenant_id,
                Group.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def _user_to_scim(self, user: User) -> dict:
        """Convert a Nimbus User to a SCIM User resource."""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": str(user.id),
            "userName": user.email,
            "displayName": user.display_name,
            "active": user.is_active,
            "externalId": user.external_id,
            "emails": [{"value": user.email, "type": "work", "primary": True}],
            "name": {"formatted": user.display_name} if user.display_name else None,
            "meta": {
                "resourceType": "User",
                "created": user.created_at.isoformat() if user.created_at else None,
                "lastModified": user.updated_at.isoformat() if user.updated_at else None,
            },
        }

    async def _group_to_scim(self, group: Group) -> dict:
        """Convert a Nimbus Group to a SCIM Group resource."""
        result = await self.db.execute(
            select(UserGroup, User.email)
            .join(User, User.id == UserGroup.user_id)
            .where(UserGroup.group_id == group.id)
        )
        members = [
            {"value": str(ug.user_id), "display": email}
            for ug, email in result.all()
        ]

        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "id": str(group.id),
            "displayName": group.name,
            "members": members,
            "meta": {
                "resourceType": "Group",
                "created": group.created_at.isoformat() if group.created_at else None,
                "lastModified": group.updated_at.isoformat() if group.updated_at else None,
            },
        }

    async def _apply_user_patch(self, user: User, op: dict) -> None:
        """Apply a single SCIM PatchOp to a user."""
        operation = op.get("op", "").lower()
        path = op.get("path", "")
        value = op.get("value")

        if operation in ("add", "replace"):
            if path == "userName":
                await self._check_email_domain(value)
                user.email = value
            elif path == "displayName":
                user.display_name = value
            elif path == "active":
                user.is_active = value
            elif path == "externalId":
                user.external_id = value
            elif path == "name.formatted":
                user.display_name = value

    async def _apply_group_patch(self, group: Group, op: dict) -> None:
        """Apply a single SCIM PatchOp to a group."""
        operation = op.get("op", "").lower()
        path = op.get("path", "")
        value = op.get("value")

        if operation in ("add", "replace"):
            if path == "displayName":
                group.name = value
            elif path == "members" and isinstance(value, list):
                for member in value:
                    member_id = member.get("value") if isinstance(member, dict) else member
                    existing = await self.db.execute(
                        select(UserGroup).where(
                            UserGroup.user_id == member_id,
                            UserGroup.group_id == group.id,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        self.db.add(UserGroup(user_id=member_id, group_id=group.id))
        elif operation == "remove":
            if path and path.startswith("members[value eq"):
                import re

                match = re.search(r'"([^"]+)"', path)
                if match:
                    member_id = match.group(1)
                    result = await self.db.execute(
                        select(UserGroup).where(
                            UserGroup.user_id == member_id,
                            UserGroup.group_id == group.id,
                        )
                    )
                    ug = result.scalar_one_or_none()
                    if ug:
                        await self.db.delete(ug)
