"""
Overview: Naming convention resolver — generates resource names following configurable patterns.
Architecture: Resolver implementation for naming (Section 11)
Dependencies: app.services.resolver.base, app.models.naming_sequence
Concepts: Naming patterns use placeholders like {env}, {type}, {seq:03d}. The resolver auto-increments
    sequence numbers per scope using durable DB-backed counters (SELECT ... FOR UPDATE).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.naming_sequence import NamingSequence
from app.services.resolver.base import BaseResolver, ResolverContext

logger = logging.getLogger(__name__)


class NamingResolver(BaseResolver):
    """Resolves naming parameters using configurable patterns."""

    resolver_type = "naming"

    async def resolve(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Resolve naming parameters.

        Input params:
            resource_type: str (e.g., 'vm', 'subnet', 'lb')
            environment_name: str (e.g., 'prod', 'staging')
            sequence: int (optional — auto-incremented if not provided)

        Config:
            pattern: str (e.g., '{env}-{type}-{seq:03d}')
            domain: str (optional, e.g., 'example.com')
            counter_scope: str ('environment' or 'global')

        Returns:
            {name, fqdn}
        """
        pattern = config.get("pattern", "{env}-{type}-{seq:03d}")
        domain = config.get("domain")
        counter_scope = config.get("counter_scope", "environment")

        resource_type = params.get("resource_type", "res")
        env_name = params.get("environment_name", "default")
        sequence = params.get("sequence")

        if sequence is None:
            if context.dry_run:
                sequence = await self._peek_sequence(context.db, context.tenant_id, counter_scope, env_name, resource_type)
            else:
                sequence = await self._next_sequence(context.db, context.tenant_id, counter_scope, env_name, resource_type)

        # Format the name using the pattern
        name = pattern.format(
            env=env_name,
            type=resource_type,
            seq=sequence,
        )

        result: dict = {"name": name}
        if domain:
            result["fqdn"] = f"{name}.{domain}"

        return result

    async def _next_sequence(
        self, db: AsyncSession, tenant_id, counter_scope: str, env_name: str, resource_type: str,
    ) -> int:
        """Atomically increment and return the next sequence value."""
        scope_key = self._scope_key(tenant_id, counter_scope, env_name, resource_type)

        stmt = (
            select(NamingSequence)
            .where(NamingSequence.tenant_id == tenant_id, NamingSequence.scope_key == scope_key)
            .with_for_update()
        )
        result = await db.execute(stmt)
        seq = result.scalar_one_or_none()

        if seq is None:
            seq = NamingSequence(tenant_id=tenant_id, scope_key=scope_key, current_value=1)
            db.add(seq)
            await db.flush()
            return 1

        seq.current_value += 1
        await db.flush()
        return seq.current_value

    async def _peek_sequence(
        self, db: AsyncSession, tenant_id, counter_scope: str, env_name: str, resource_type: str,
    ) -> int:
        """Return the next sequence value without incrementing (for dry-run previews)."""
        scope_key = self._scope_key(tenant_id, counter_scope, env_name, resource_type)

        stmt = select(NamingSequence.current_value).where(
            NamingSequence.tenant_id == tenant_id, NamingSequence.scope_key == scope_key
        )
        result = await db.execute(stmt)
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def release(
        self,
        allocation_ref: dict,
        config: dict,
        context: ResolverContext,
    ) -> bool:
        """Release a naming allocation — no-op since names are not pooled."""
        return True

    async def update(
        self,
        current: dict,
        new_params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Update naming — re-resolve with new params."""
        return await self.resolve(new_params, config, context)

    async def validate(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> list[str]:
        """Validate naming parameters — verify pattern validity."""
        errors: list[str] = []
        pattern = config.get("pattern", "{env}-{type}-{seq:03d}")

        try:
            # Test-format the pattern with dummy values to check syntax
            pattern.format(env="test", type="vm", seq=1)
        except (KeyError, ValueError, IndexError) as e:
            errors.append(f"Invalid naming pattern '{pattern}': {e}")

        return errors

    @staticmethod
    def _scope_key(tenant_id, counter_scope: str, env_name: str, resource_type: str) -> str:
        if counter_scope == "global":
            return f"global:{resource_type}"
        return f"{tenant_id}:{env_name}:{resource_type}"
