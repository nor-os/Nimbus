"""
Overview: Central permission engine with tenant hierarchy inheritance and deny overrides.
Architecture: Permission resolution with RBAC + ABAC + tenant inheritance (Section 5.2)
Dependencies: sqlalchemy, app.models, app.services.permission.abac
Concepts: Permission checking, tenant hierarchy inheritance, explicit deny, ABAC, group membership
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abac_policy import ABACPolicy, PolicyEffect
from app.models.group import Group
from app.models.group_membership import GroupMembership
from app.models.group_role import GroupRole
from app.models.permission import Permission
from app.models.permission_override import PermissionOverride
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.user_group import UserGroup
from app.models.user_role import UserRole
from app.services.permission.abac.evaluator import EvaluationContext, Evaluator
from app.services.permission.abac.parser import Parser
from app.services.permission.abac.tokenizer import Tokenizer


@dataclass
class EffectivePermissionEntry:
    """Enriched effective permission with inheritance and deny metadata."""

    permission_key: str
    source: str
    role_name: str | None = None
    group_name: str | None = None
    source_tenant_id: str = ""
    source_tenant_name: str = ""
    is_inherited: bool = False
    is_denied: bool = False
    deny_source: str | None = None


class PermissionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_permission(
        self,
        user_id: str,
        permission_key: str,
        tenant_id: str,
        resource: dict | None = None,
        context: dict | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a user has a specific permission.

        Returns (allowed, source) where source describes how the permission was granted/denied.
        """
        effective = await self.get_effective_permissions(user_id, tenant_id)

        # Build lookup: key -> entry (prefer non-denied)
        key_map: dict[str, EffectivePermissionEntry] = {}
        for ep in effective:
            if ep.permission_key not in key_map or (
                key_map[ep.permission_key].is_denied and not ep.is_denied
            ):
                key_map[ep.permission_key] = ep

        parts = permission_key.split(":")
        matched_entry: EffectivePermissionEntry | None = None

        # Most-specific-wins: exact match first, then broader wildcard patterns
        for i in range(len(parts), 0, -1):
            check_key = ":".join(parts[:i])
            if check_key in key_map:
                matched_entry = key_map[check_key]
                break

            wildcard_key = ":".join(parts[: i - 1] + ["*"] * (len(parts) - i + 1))
            if wildcard_key in key_map:
                matched_entry = key_map[wildcard_key]
                break

        if not matched_entry and "*:*:*" in key_map:
            matched_entry = key_map["*:*:*"]

        if matched_entry and matched_entry.is_denied:
            return False, matched_entry.deny_source

        rbac_allowed = matched_entry is not None
        rbac_source = matched_entry.source if matched_entry else None

        # Apply ABAC policies (across ancestor chain)
        ancestor_chain = await self._get_tenant_ancestor_chain(tenant_id)
        tenant_ids = [tid for tid, _ in ancestor_chain]
        abac_result = await self._evaluate_abac(
            user_id, tenant_ids, permission_key, resource, context
        )

        if abac_result is not None:
            allowed, abac_source = abac_result
            if not allowed:
                return False, abac_source
            if rbac_allowed:
                return True, rbac_source
            return True, abac_source

        return rbac_allowed, rbac_source

    async def get_effective_permissions(
        self, user_id: str, tenant_id: str
    ) -> list[EffectivePermissionEntry]:
        """Get all effective permissions for a user with inheritance through tenant hierarchy."""
        now = datetime.now(UTC)

        # 1. Build ancestor chain: root-first list of (tenant_id, tenant_name)
        ancestor_chain = await self._get_tenant_ancestor_chain(tenant_id)

        # 2. For each tenant in the chain, collect role assignments and their permissions
        permissions: dict[str, EffectivePermissionEntry] = {}
        all_role_ids: set = set()
        all_group_ids: set = set()

        for chain_tenant_id, chain_tenant_name in ancestor_chain:
            is_inherited = chain_tenant_id != tenant_id

            # Direct role assignments for this tenant
            direct_roles = await self.db.execute(
                select(UserRole, Role)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRole.user_id == user_id,
                    UserRole.tenant_id == chain_tenant_id,
                    Role.deleted_at.is_(None),
                )
            )
            for ur, role in direct_roles.all():
                if ur.expires_at and ur.expires_at < now:
                    continue
                all_role_ids.add(role.id)
                source = f"role:{role.name}@{chain_tenant_name}"
                await self._collect_role_permissions_enriched(
                    role=role,
                    permissions=permissions,
                    source=source,
                    role_name=role.name,
                    group_name=None,
                    source_tenant_id=chain_tenant_id,
                    source_tenant_name=chain_tenant_name,
                    is_inherited=is_inherited,
                )

            # Group-based role assignments for this tenant
            group_roles = await self._get_group_role_ids(user_id, chain_tenant_id)
            for role_id, group_name in group_roles:
                all_group_ids.add(group_name)  # Track group names for deny lookup
                result = await self.db.execute(
                    select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
                )
                role = result.scalar_one_or_none()
                if not role:
                    continue
                all_role_ids.add(role.id)
                source = f"group:{group_name}->role:{role.name}@{chain_tenant_name}"
                await self._collect_role_permissions_enriched(
                    role=role,
                    permissions=permissions,
                    source=source,
                    role_name=role.name,
                    group_name=group_name,
                    source_tenant_id=chain_tenant_id,
                    source_tenant_name=chain_tenant_name,
                    is_inherited=is_inherited,
                )

        # 3. Apply deny overrides across all ancestor tenants
        tenant_ids = [tid for tid, _ in ancestor_chain]

        # Get user's group IDs for deny lookup
        user_group_result = await self.db.execute(
            select(UserGroup.group_id).where(UserGroup.user_id == user_id)
        )
        user_group_ids = [str(row[0]) for row in user_group_result.all()]

        deny_map = await self._get_deny_overrides(
            user_id=user_id,
            group_ids=user_group_ids,
            role_ids=[str(rid) for rid in all_role_ids],
            tenant_ids=tenant_ids,
        )

        for perm_key, deny_source in deny_map.items():
            if perm_key in permissions:
                permissions[perm_key].is_denied = True
                permissions[perm_key].deny_source = deny_source

        # 4. Apply ABAC deny policies across all ancestor tenants
        abac_denies = await self._get_abac_denies(user_id, tenant_ids)
        for perm_key, deny_source in abac_denies.items():
            if perm_key in permissions:
                permissions[perm_key].is_denied = True
                permissions[perm_key].deny_source = deny_source

        return list(permissions.values())

    async def _collect_role_permissions_enriched(
        self,
        role: Role,
        permissions: dict[str, EffectivePermissionEntry],
        source: str,
        role_name: str | None,
        group_name: str | None,
        source_tenant_id: str,
        source_tenant_name: str,
        is_inherited: bool,
    ) -> None:
        """Collect permissions from a role and its parent chain into enriched entries."""
        visited = set()
        current = role
        while current and current.id not in visited:
            visited.add(current.id)

            result = await self.db.execute(
                select(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == current.id)
            )
            for perm in result.scalars().all():
                # Union semantics: first source wins, but direct > inherited
                if perm.key not in permissions or (
                    permissions[perm.key].is_inherited and not is_inherited
                ):
                    permissions[perm.key] = EffectivePermissionEntry(
                        permission_key=perm.key,
                        source=source,
                        role_name=role_name,
                        group_name=group_name,
                        source_tenant_id=source_tenant_id,
                        source_tenant_name=source_tenant_name,
                        is_inherited=is_inherited,
                    )

            if current.parent_role_id:
                parent_result = await self.db.execute(
                    select(Role).where(
                        Role.id == current.parent_role_id, Role.deleted_at.is_(None)
                    )
                )
                current = parent_result.scalar_one_or_none()
            else:
                break

    async def _get_tenant_ancestor_chain(
        self, tenant_id: str
    ) -> list[tuple[str, str]]:
        """Walk up parent_id to build [root, ..., current] ancestor chain."""
        chain: list[tuple[str, str]] = []
        current_id = tenant_id

        while current_id:
            result = await self.db.execute(
                select(Tenant.id, Tenant.name, Tenant.parent_id).where(
                    Tenant.id == current_id, Tenant.deleted_at.is_(None)
                )
            )
            row = result.first()
            if not row:
                break
            chain.append((str(row[0]), row[1]))
            current_id = str(row[2]) if row[2] else None

        chain.reverse()  # Root-first
        return chain

    async def _get_group_role_ids(
        self, user_id: str, tenant_id: str
    ) -> list[tuple[str, str]]:
        """Get all role IDs from user's group memberships in this tenant (recursive via GroupMembership)."""
        # Get direct groups filtered to this tenant
        result = await self.db.execute(
            select(UserGroup.group_id)
            .join(Group, Group.id == UserGroup.group_id)
            .where(
                UserGroup.user_id == user_id,
                Group.tenant_id == tenant_id,
                Group.deleted_at.is_(None),
            )
        )
        group_ids = {row[0] for row in result.all()}

        # Recurse up parent chain via GroupMembership table (with tenant filter)
        all_group_ids = set(group_ids)
        to_process = list(group_ids)
        while to_process:
            gid = to_process.pop()
            parent_result = await self.db.execute(
                select(GroupMembership.parent_group_id)
                .join(Group, Group.id == GroupMembership.parent_group_id)
                .where(
                    GroupMembership.child_group_id == gid,
                    Group.tenant_id == tenant_id,
                    Group.deleted_at.is_(None),
                )
            )
            for row in parent_result.all():
                parent_id = row[0]
                if parent_id not in all_group_ids:
                    all_group_ids.add(parent_id)
                    to_process.append(parent_id)

        # Get roles for all groups
        role_pairs = []
        for gid in all_group_ids:
            result = await self.db.execute(
                select(GroupRole.role_id, Group.name)
                .join(Group, Group.id == GroupRole.group_id)
                .where(GroupRole.group_id == gid, Group.deleted_at.is_(None))
            )
            for role_id, group_name in result.all():
                role_pairs.append((role_id, group_name))

        return role_pairs

    async def _get_deny_overrides(
        self,
        user_id: str,
        group_ids: list[str],
        role_ids: list[str],
        tenant_ids: list[str],
    ) -> dict[str, str]:
        """Query PermissionOverride table for matching deny entries."""
        from sqlalchemy import or_

        if not tenant_ids:
            return {}

        # Build principal conditions
        conditions = [
            (PermissionOverride.principal_type == "user")
            & (PermissionOverride.principal_id == user_id),
        ]
        for gid in group_ids:
            conditions.append(
                (PermissionOverride.principal_type == "group")
                & (PermissionOverride.principal_id == gid)
            )
        for rid in role_ids:
            conditions.append(
                (PermissionOverride.principal_type == "role")
                & (PermissionOverride.principal_id == rid)
            )

        result = await self.db.execute(
            select(PermissionOverride, Permission)
            .join(Permission, Permission.id == PermissionOverride.permission_id)
            .where(
                PermissionOverride.tenant_id.in_(tenant_ids),
                or_(*conditions),
            )
        )

        deny_map: dict[str, str] = {}
        for override, perm in result.all():
            source = f"deny-override:{override.principal_type}:{override.principal_id}"
            if override.reason:
                source += f" ({override.reason})"
            deny_map[perm.key] = source

        return deny_map

    async def _get_abac_denies(
        self, user_id: str, tenant_ids: list[str]
    ) -> dict[str, str]:
        """Evaluate ABAC deny policies across ancestor tenants, return denied permission keys."""
        if not tenant_ids:
            return {}

        result = await self.db.execute(
            select(ABACPolicy)
            .where(
                ABACPolicy.tenant_id.in_(tenant_ids),
                ABACPolicy.is_enabled.is_(True),
                ABACPolicy.effect == PolicyEffect.DENY,
            )
            .order_by(ABACPolicy.priority.desc())
        )
        policies = result.scalars().all()

        deny_map: dict[str, str] = {}
        eval_context = EvaluationContext(
            user={"id": user_id},
            resource={},
            context={},
        )

        for policy in policies:
            try:
                tokens = Tokenizer(policy.expression).tokenize()
                ast = Parser(tokens).parse()
                result_val = Evaluator(eval_context).evaluate(ast)

                if bool(result_val) and policy.target_permission_id:
                    perm_result = await self.db.execute(
                        select(Permission).where(
                            Permission.id == policy.target_permission_id
                        )
                    )
                    perm = perm_result.scalar_one_or_none()
                    if perm:
                        deny_map[perm.key] = f"abac-deny:{policy.name}"
            except Exception:
                continue

        return deny_map

    async def _evaluate_abac(
        self,
        user_id: str,
        tenant_ids: list[str],
        permission_key: str,
        resource: dict | None,
        context: dict | None,
    ) -> tuple[bool, str] | None:
        """Evaluate ABAC policies across ancestor tenants."""
        if not tenant_ids:
            return None

        result = await self.db.execute(
            select(ABACPolicy)
            .where(
                ABACPolicy.tenant_id.in_(tenant_ids),
                ABACPolicy.is_enabled.is_(True),
            )
            .order_by(ABACPolicy.priority.desc())
        )
        policies = result.scalars().all()

        if not policies:
            return None

        eval_context = EvaluationContext(
            user={"id": user_id, "tenant_id": tenant_ids[-1] if tenant_ids else ""},
            resource=resource or {},
            context=context or {},
        )

        for policy in policies:
            if policy.target_permission_id:
                perm_result = await self.db.execute(
                    select(Permission).where(Permission.id == policy.target_permission_id)
                )
                target_perm = perm_result.scalar_one_or_none()
                if target_perm and target_perm.key != permission_key:
                    continue

            try:
                tokens = Tokenizer(policy.expression).tokenize()
                ast = Parser(tokens).parse()
                result_val = Evaluator(eval_context).evaluate(ast)

                if bool(result_val):
                    if policy.effect == PolicyEffect.DENY:
                        return False, f"abac-deny:{policy.name}"
                    else:
                        return True, f"abac-allow:{policy.name}"
            except Exception:
                continue

        return None
