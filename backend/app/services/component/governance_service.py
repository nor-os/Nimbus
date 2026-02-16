"""
Overview: Component governance service — per-tenant allow/deny rules and parameter constraints.
Architecture: Governance service layer (Section 11)
Dependencies: sqlalchemy, app.models.component
Concepts: Governance rules control which components are available to which tenants, with optional
    parameter constraints (min/max values, allowed choices) and instance limits.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.component import ComponentGovernance

logger = logging.getLogger(__name__)


class ComponentGovernanceService:
    """Service for managing component governance rules."""

    async def get_governance(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ComponentGovernance | None:
        """Get the governance rule for a component + tenant pair."""
        result = await db.execute(
            select(ComponentGovernance).where(
                ComponentGovernance.component_id == component_id,
                ComponentGovernance.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_governance(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        is_allowed: bool = True,
        parameter_constraints: dict | None = None,
        max_instances: int | None = None,
    ) -> ComponentGovernance:
        """Create or update a governance rule."""
        existing = await self.get_governance(db, component_id, tenant_id)
        if existing:
            existing.is_allowed = is_allowed
            existing.parameter_constraints = parameter_constraints
            existing.max_instances = max_instances
            await db.flush()
            await db.refresh(existing)
            return existing

        rule = ComponentGovernance(
            component_id=component_id,
            tenant_id=tenant_id,
            is_allowed=is_allowed,
            parameter_constraints=parameter_constraints,
            max_instances=max_instances,
        )
        db.add(rule)
        await db.flush()
        await db.refresh(rule)
        return rule

    async def delete_governance(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Remove a governance rule (hard delete — these are config, not data)."""
        existing = await self.get_governance(db, component_id, tenant_id)
        if not existing:
            raise ValueError(f"No governance rule for component '{component_id}' / tenant '{tenant_id}'")
        await db.delete(existing)
        await db.flush()

    async def list_governance_for_tenant(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[ComponentGovernance]:
        """List all governance rules for a tenant."""
        result = await db.execute(
            select(ComponentGovernance)
            .where(ComponentGovernance.tenant_id == tenant_id)
            .order_by(ComponentGovernance.created_at)
        )
        return list(result.scalars().all())

    async def list_governance_for_component(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> list[ComponentGovernance]:
        """List all tenant governance rules for a component."""
        result = await db.execute(
            select(ComponentGovernance)
            .where(ComponentGovernance.component_id == component_id)
            .order_by(ComponentGovernance.created_at)
        )
        return list(result.scalars().all())

    async def check_allowed(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Check if a component is allowed for a tenant. Default: allowed (no rule = allow)."""
        rule = await self.get_governance(db, component_id, tenant_id)
        if rule is None:
            return True  # No rule means allowed
        return rule.is_allowed

    def validate_parameters(
        self,
        governance: ComponentGovernance,
        params: dict,
    ) -> tuple[bool, list[str]]:
        """Validate parameters against governance constraints.

        Returns (valid, errors).
        """
        errors: list[str] = []
        constraints = governance.parameter_constraints or {}

        for param_name, constraint in constraints.items():
            value = params.get(param_name)
            if value is None:
                continue

            if "min" in constraint and value < constraint["min"]:
                errors.append(f"Parameter '{param_name}' value {value} below minimum {constraint['min']}")
            if "max" in constraint and value > constraint["max"]:
                errors.append(f"Parameter '{param_name}' value {value} above maximum {constraint['max']}")
            if "allowed_values" in constraint and value not in constraint["allowed_values"]:
                errors.append(
                    f"Parameter '{param_name}' value '{value}' not in allowed: {constraint['allowed_values']}"
                )

        return (len(errors) == 0, errors)

    async def check_max_instances(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_count: int,
    ) -> bool:
        """Check if deploying one more instance would exceed the max_instances limit."""
        rule = await self.get_governance(db, component_id, tenant_id)
        if rule is None or rule.max_instances is None:
            return True  # No limit
        return current_count < rule.max_instances
