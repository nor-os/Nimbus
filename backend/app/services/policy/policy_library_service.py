"""
Overview: Policy library service — CRUD operations, statement validation, and variable substitution.
Architecture: Service layer for policy library management (Section 5)
Dependencies: sqlalchemy, app.models.policy_library, app.services.permission.abac
Concepts: Policy CRUD, statement validation, variable substitution with {{var}} placeholders
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_library import PolicyCategory, PolicyLibraryEntry, PolicySeverity

logger = logging.getLogger(__name__)

VALID_EFFECTS = {"allow", "deny"}
ACTION_PATTERN = re.compile(r"^[\w*]+:[\w*]+$")
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class PolicyLibraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: str,
        created_by: str,
        data: dict[str, Any],
    ) -> PolicyLibraryEntry:
        """Create a new policy library entry."""
        entry = PolicyLibraryEntry(
            tenant_id=tenant_id,
            name=data["name"],
            display_name=data["display_name"],
            description=data.get("description"),
            category=PolicyCategory(data["category"]),
            statements=data["statements"],
            variables=data.get("variables"),
            severity=PolicySeverity(data.get("severity", "MEDIUM")),
            is_system=False,
            tags=data.get("tags"),
            created_by=created_by,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def update(
        self,
        tenant_id: str,
        policy_id: str,
        data: dict[str, Any],
    ) -> PolicyLibraryEntry | None:
        """Update a policy library entry. Cannot update system policies."""
        entry = await self.get(tenant_id, policy_id)
        if not entry:
            return None
        if entry.is_system:
            raise ValueError("Cannot modify system policies")

        if "name" in data:
            entry.name = data["name"]
        if "display_name" in data:
            entry.display_name = data["display_name"]
        if "description" in data:
            entry.description = data["description"]
        if "category" in data:
            entry.category = PolicyCategory(data["category"])
        if "statements" in data:
            entry.statements = data["statements"]
        if "variables" in data:
            entry.variables = data["variables"]
        if "severity" in data:
            entry.severity = PolicySeverity(data["severity"])
        if "tags" in data:
            entry.tags = data["tags"]

        await self.db.flush()
        return entry

    async def get(
        self, tenant_id: str, policy_id: str
    ) -> PolicyLibraryEntry | None:
        """Get a policy by ID — returns tenant-scoped or system policies."""
        stmt = select(PolicyLibraryEntry).where(
            PolicyLibraryEntry.id == policy_id,
            PolicyLibraryEntry.deleted_at.is_(None),
            or_(
                PolicyLibraryEntry.tenant_id == tenant_id,
                PolicyLibraryEntry.tenant_id.is_(None),
            ),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        category: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[PolicyLibraryEntry]:
        """List policies — includes system policies (tenant_id IS NULL)."""
        stmt = select(PolicyLibraryEntry).where(
            PolicyLibraryEntry.deleted_at.is_(None),
            or_(
                PolicyLibraryEntry.tenant_id == tenant_id,
                PolicyLibraryEntry.tenant_id.is_(None),
            ),
        )

        if category:
            stmt = stmt.where(PolicyLibraryEntry.category == PolicyCategory(category))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    PolicyLibraryEntry.name.ilike(pattern),
                    PolicyLibraryEntry.display_name.ilike(pattern),
                    PolicyLibraryEntry.description.ilike(pattern),
                )
            )

        stmt = stmt.order_by(PolicyLibraryEntry.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, tenant_id: str, policy_id: str) -> bool:
        """Soft-delete a policy. Blocks if is_system=True."""
        entry = await self.get(tenant_id, policy_id)
        if not entry:
            return False
        if entry.is_system:
            raise ValueError("Cannot delete system policies")

        entry.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    @staticmethod
    def validate_statements(statements: list[dict[str, Any]]) -> list[str]:
        """Validate statement structure and ABAC conditions. Returns list of errors."""
        errors: list[str] = []

        if not statements:
            errors.append("At least one statement is required")
            return errors

        sids: set[str] = set()
        for i, stmt in enumerate(statements):
            prefix = f"Statement {i}"

            sid = stmt.get("sid")
            if not sid:
                errors.append(f"{prefix}: missing 'sid'")
            elif sid in sids:
                errors.append(f"{prefix}: duplicate sid '{sid}'")
            else:
                sids.add(sid)
                prefix = f"Statement '{sid}'"

            effect = stmt.get("effect")
            if effect not in VALID_EFFECTS:
                errors.append(f"{prefix}: effect must be 'allow' or 'deny', got '{effect}'")

            actions = stmt.get("actions", [])
            if not actions:
                errors.append(f"{prefix}: at least one action is required")
            for action in actions:
                if not ACTION_PATTERN.match(action):
                    errors.append(
                        f"{prefix}: invalid action format '{action}' "
                        "(expected 'category:verb' e.g. 'compute:create')"
                    )

            resources = stmt.get("resources", [])
            if not resources:
                errors.append(f"{prefix}: at least one resource is required")

            condition = stmt.get("condition")
            if condition:
                try:
                    from app.services.permission.abac.tokenizer import tokenize

                    # Strip variable placeholders before parsing
                    clean_condition = VARIABLE_PATTERN.sub("null", condition)
                    from app.services.permission.abac.parser import ABACParser

                    tokens = tokenize(clean_condition)
                    ABACParser(tokens).parse()
                except Exception as e:
                    errors.append(f"{prefix}: invalid condition expression: {e}")

        return errors

    @staticmethod
    def substitute_variables(
        statements: list[dict[str, Any]],
        variables_schema: dict[str, Any] | None,
        overrides: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Replace {{var}} placeholders in conditions. Returns new statement list."""
        if not variables_schema:
            return statements

        values: dict[str, Any] = {}
        for var_name, var_def in variables_schema.items():
            if overrides and var_name in overrides:
                values[var_name] = overrides[var_name]
            elif "default" in var_def:
                values[var_name] = var_def["default"]

        result = []
        for stmt in statements:
            new_stmt = dict(stmt)
            condition = new_stmt.get("condition")
            if condition and isinstance(condition, str):
                for var_name, var_value in values.items():
                    placeholder = "{{" + var_name + "}}"
                    if placeholder in condition:
                        replacement = (
                            repr(var_value) if isinstance(var_value, str) else str(var_value)
                        )
                        condition = condition.replace(placeholder, replacement)
                new_stmt["condition"] = condition
            result.append(new_stmt)
        return result
