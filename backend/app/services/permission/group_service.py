"""
Overview: Group management service for CRUD, user membership, group-in-group membership, and role assignment.
Architecture: Service layer for group lifecycle operations (Section 3.1, 5.2)
Dependencies: sqlalchemy, app.models
Concepts: RBAC, group management, flat groups with many-to-many nesting, cycle detection
"""

from collections import deque
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.group_membership import GroupMembership
from app.models.group_role import GroupRole
from app.models.user_group import UserGroup


class GroupError(Exception):
    def __init__(self, message: str, code: str = "GROUP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class GroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_groups(self, tenant_id: str) -> list[Group]:
        """List all active groups for a tenant."""
        result = await self.db.execute(
            select(Group)
            .where(Group.tenant_id == tenant_id, Group.deleted_at.is_(None))
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    async def get_group(self, group_id: str, tenant_id: str) -> Group | None:
        """Get a group by ID within a tenant."""
        result = await self.db.execute(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == tenant_id,
                Group.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_group(
        self,
        tenant_id: str,
        name: str,
        description: str | None = None,
    ) -> Group:
        """Create a new group."""
        group = Group(
            tenant_id=tenant_id,
            name=name,
            description=description,
        )
        self.db.add(group)
        await self.db.flush()
        return group

    async def update_group(
        self,
        group_id: str,
        tenant_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> Group:
        """Update a group."""
        group = await self.get_group(group_id, tenant_id)
        if not group:
            raise GroupError("Group not found", "GROUP_NOT_FOUND")

        if group.is_system:
            raise GroupError("Cannot modify system groups", "SYSTEM_GROUP")

        if name is not None:
            group.name = name
        if description is not None:
            group.description = description

        await self.db.flush()
        return group

    async def delete_group(self, group_id: str, tenant_id: str) -> None:
        """Soft-delete a group."""
        group = await self.get_group(group_id, tenant_id)
        if not group:
            raise GroupError("Group not found", "GROUP_NOT_FOUND")

        if group.is_system:
            raise GroupError("Cannot delete system groups", "SYSTEM_GROUP")

        group.deleted_at = datetime.now(UTC)
        await self.db.flush()

    # ── User members ─────────────────────────────────────────────────

    async def add_member(self, group_id: str, user_id: str) -> UserGroup:
        """Add a user to a group."""
        existing = await self.db.execute(
            select(UserGroup).where(
                UserGroup.user_id == user_id, UserGroup.group_id == group_id
            )
        )
        if existing.scalar_one_or_none():
            raise GroupError("User already in group", "ALREADY_MEMBER")

        user_group = UserGroup(user_id=user_id, group_id=group_id)
        self.db.add(user_group)
        await self.db.flush()
        return user_group

    async def remove_member(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group."""
        result = await self.db.execute(
            select(UserGroup).where(
                UserGroup.user_id == user_id, UserGroup.group_id == group_id
            )
        )
        user_group = result.scalar_one_or_none()
        if not user_group:
            raise GroupError("User not in group", "NOT_MEMBER")

        await self.db.delete(user_group)
        await self.db.flush()

    async def get_group_members(self, group_id: str) -> dict:
        """Get all members (users and child groups) of a group."""
        from app.models.user import User

        user_result = await self.db.execute(
            select(User)
            .join(UserGroup, UserGroup.user_id == User.id)
            .where(UserGroup.group_id == group_id, User.deleted_at.is_(None))
        )
        users = list(user_result.scalars().all())

        group_result = await self.db.execute(
            select(Group)
            .join(GroupMembership, GroupMembership.child_group_id == Group.id)
            .where(
                GroupMembership.parent_group_id == group_id,
                Group.deleted_at.is_(None),
            )
            .order_by(Group.name)
        )
        groups = list(group_result.scalars().all())

        return {"users": users, "groups": groups}

    # ── Group-in-group membership ────────────────────────────────────

    async def add_child_group(
        self, parent_group_id: str, child_group_id: str
    ) -> GroupMembership:
        """Add a group as a member of another group."""
        if parent_group_id == child_group_id:
            raise GroupError("A group cannot be a member of itself", "SELF_REFERENCE")

        # Check existing
        existing = await self.db.execute(
            select(GroupMembership).where(
                GroupMembership.parent_group_id == parent_group_id,
                GroupMembership.child_group_id == child_group_id,
            )
        )
        if existing.scalar_one_or_none():
            raise GroupError("Group is already a member", "ALREADY_MEMBER")

        # Cycle detection
        await self._validate_no_cycle(parent_group_id, child_group_id)

        membership = GroupMembership(
            parent_group_id=parent_group_id,
            child_group_id=child_group_id,
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def remove_child_group(
        self, parent_group_id: str, child_group_id: str
    ) -> None:
        """Remove a group membership."""
        result = await self.db.execute(
            select(GroupMembership).where(
                GroupMembership.parent_group_id == parent_group_id,
                GroupMembership.child_group_id == child_group_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise GroupError("Group membership not found", "NOT_MEMBER")

        await self.db.delete(membership)
        await self.db.flush()

    async def get_child_groups(self, group_id: str) -> list[Group]:
        """Get groups that are members of this group."""
        result = await self.db.execute(
            select(Group)
            .join(GroupMembership, GroupMembership.child_group_id == Group.id)
            .where(
                GroupMembership.parent_group_id == group_id,
                Group.deleted_at.is_(None),
            )
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    async def get_parent_groups(self, group_id: str) -> list[Group]:
        """Get groups this group is a member of."""
        result = await self.db.execute(
            select(Group)
            .join(GroupMembership, GroupMembership.parent_group_id == Group.id)
            .where(
                GroupMembership.child_group_id == group_id,
                Group.deleted_at.is_(None),
            )
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    # ── Roles ────────────────────────────────────────────────────────

    async def get_group_roles(self, group_id: str) -> list:
        """Get all roles assigned to a group."""
        from app.models.role import Role

        result = await self.db.execute(
            select(Role)
            .join(GroupRole, GroupRole.role_id == Role.id)
            .where(GroupRole.group_id == group_id, Role.deleted_at.is_(None))
            .order_by(Role.name)
        )
        return list(result.scalars().all())

    async def assign_role(self, group_id: str, role_id: str) -> GroupRole:
        """Assign a role to a group."""
        existing = await self.db.execute(
            select(GroupRole).where(
                GroupRole.group_id == group_id, GroupRole.role_id == role_id
            )
        )
        if existing.scalar_one_or_none():
            raise GroupError("Role already assigned to group", "ALREADY_ASSIGNED")

        group_role = GroupRole(group_id=group_id, role_id=role_id)
        self.db.add(group_role)
        await self.db.flush()
        return group_role

    async def unassign_role(self, group_id: str, role_id: str) -> None:
        """Remove a role from a group."""
        result = await self.db.execute(
            select(GroupRole).where(
                GroupRole.group_id == group_id, GroupRole.role_id == role_id
            )
        )
        group_role = result.scalar_one_or_none()
        if not group_role:
            raise GroupError("Role not assigned to group", "NOT_ASSIGNED")

        await self.db.delete(group_role)
        await self.db.flush()

    # ── User's groups ────────────────────────────────────────────────

    async def get_user_groups(
        self, user_id: str, tenant_id: str, recursive: bool = True
    ) -> list[Group]:
        """Get all groups a user belongs to, optionally including ancestor groups via group memberships."""
        result = await self.db.execute(
            select(Group)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(
                UserGroup.user_id == user_id,
                Group.tenant_id == tenant_id,
                Group.deleted_at.is_(None),
            )
        )
        direct_groups = list(result.scalars().all())

        if not recursive:
            return direct_groups

        all_groups = list(direct_groups)
        seen = {str(g.id) for g in all_groups}

        # BFS upward through group_memberships
        queue = deque(str(g.id) for g in direct_groups)
        while queue:
            current_id = queue.popleft()
            parents = await self.db.execute(
                select(Group)
                .join(
                    GroupMembership,
                    GroupMembership.parent_group_id == Group.id,
                )
                .where(
                    GroupMembership.child_group_id == current_id,
                    Group.tenant_id == tenant_id,
                    Group.deleted_at.is_(None),
                )
            )
            for parent in parents.scalars().all():
                pid = str(parent.id)
                if pid not in seen:
                    seen.add(pid)
                    all_groups.append(parent)
                    queue.append(pid)

        return all_groups

    # ── Private helpers ──────────────────────────────────────────────

    async def _validate_no_cycle(
        self, parent_id: str, child_id: str
    ) -> None:
        """BFS upward from parent through group_memberships; if we reach child_id, it's a cycle."""
        visited = set()
        queue = deque([parent_id])

        while queue:
            current = queue.popleft()
            if current == child_id:
                raise GroupError(
                    "Adding this group would create a circular membership",
                    "CIRCULAR_REF",
                )
            if current in visited:
                continue
            visited.add(current)

            result = await self.db.execute(
                select(GroupMembership.parent_group_id).where(
                    GroupMembership.child_group_id == current
                )
            )
            for row in result.all():
                pid = str(row[0])
                if pid not in visited:
                    queue.append(pid)
