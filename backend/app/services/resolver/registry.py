"""
Overview: Resolver registry — registers resolver handlers and orchestrates the resolution pipeline.
Architecture: Resolver registry (Section 11)
Dependencies: app.services.resolver.base, app.models.resolver, sqlalchemy
Concepts: The registry maps resolver types to their handlers and runs the full pre-resolution
    pipeline: defaults → user params → resolver outputs.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.component import Component
from app.models.resolver import Resolver, ResolverConfiguration
from app.services.resolver.base import BaseResolver, ResolverContext

logger = logging.getLogger(__name__)


class ResolverRegistry:
    """Registry for resolver handlers and orchestration of the resolution pipeline."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseResolver] = {}

    def register(self, resolver_type: str, handler: BaseResolver) -> None:
        """Register a resolver handler."""
        self._handlers[resolver_type] = handler

    def get(self, resolver_type: str) -> BaseResolver | None:
        """Get a resolver handler by type."""
        return self._handlers.get(resolver_type)

    def list_types(self) -> list[str]:
        """List all registered resolver types."""
        return list(self._handlers.keys())

    async def resolve_all(
        self,
        component: Component,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_params: dict,
        *,
        environment_id: uuid.UUID | None = None,
        landing_zone_id: uuid.UUID | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Run the full pre-resolution pipeline for a component.

        1. Start with input_schema defaults
        2. Override with user_params
        3. For each param in resolver_bindings: call the bound resolver, inject output
        4. Return fully resolved parameter dict
        """
        # Step 1: Extract defaults from input_schema
        resolved = {}
        input_schema = component.input_schema or {}
        properties = input_schema.get("properties", {})
        for param_name, param_def in properties.items():
            if "default" in param_def:
                resolved[param_name] = param_def["default"]

        # Step 2: Override with user-provided params
        resolved.update(user_params)

        # Step 3: Run resolver bindings
        bindings = component.resolver_bindings or {}
        context = ResolverContext(
            tenant_id=tenant_id,
            environment_id=environment_id,
            landing_zone_id=landing_zone_id,
            provider_id=component.provider_id,
            db=db,
            dry_run=dry_run,
        )

        for param_name, binding in bindings.items():
            resolver_type = binding.get("resolver_type")
            if not resolver_type:
                continue

            handler = self.get(resolver_type)
            if not handler:
                logger.warning(f"No handler registered for resolver type '{resolver_type}'")
                continue

            # Fetch config for this resolver + scope
            config = await self._get_config(
                db, resolver_type, landing_zone_id, environment_id
            )

            # Build resolver input from binding params + resolved values
            resolver_input = binding.get("params", {})
            # Allow referencing other resolved params in resolver input
            for key, value in resolver_input.items():
                if isinstance(value, str) and value.startswith("$"):
                    ref_param = value[1:]
                    if ref_param in resolved:
                        resolver_input[key] = resolved[ref_param]

            try:
                output = await handler.resolve(resolver_input, config, context)
                # Inject resolver output into resolved params
                target = binding.get("target", param_name)
                if isinstance(output, dict) and isinstance(target, str):
                    resolved[target] = output
                elif isinstance(output, dict):
                    resolved.update(output)
            except Exception:
                logger.exception(
                    f"Resolver '{resolver_type}' failed for param '{param_name}'"
                )

        return resolved

    async def _get_config(
        self,
        db: AsyncSession,
        resolver_type: str,
        landing_zone_id: uuid.UUID | None,
        environment_id: uuid.UUID | None,
    ) -> dict:
        """Fetch resolver configuration for the given scope, falling back to broader scopes."""
        # Look up the resolver ID
        result = await db.execute(
            select(Resolver.id).where(Resolver.resolver_type == resolver_type)
        )
        resolver_id = result.scalar_one_or_none()
        if not resolver_id:
            return {}

        # Try environment-specific first, then zone-level, then global
        for lz_id, env_id in [
            (landing_zone_id, environment_id),
            (landing_zone_id, None),
            (None, None),
        ]:
            stmt = select(ResolverConfiguration.config).where(
                ResolverConfiguration.resolver_id == resolver_id,
            )
            if lz_id is not None:
                stmt = stmt.where(ResolverConfiguration.landing_zone_id == lz_id)
            else:
                stmt = stmt.where(ResolverConfiguration.landing_zone_id.is_(None))
            if env_id is not None:
                stmt = stmt.where(ResolverConfiguration.environment_id == env_id)
            else:
                stmt = stmt.where(ResolverConfiguration.environment_id.is_(None))

            result = await db.execute(stmt)
            config = result.scalar_one_or_none()
            if config is not None:
                return config

        return {}


    def get_resource_manager(
        self,
        environment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        *,
        landing_zone_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
    ):
        """Create a ResourceManager instance scoped to an environment."""
        from app.services.resolver.resource_manager import ResourceManager

        return ResourceManager(
            environment_id=environment_id,
            tenant_id=tenant_id,
            db=db,
            landing_zone_id=landing_zone_id,
            provider_id=provider_id,
        )


# Global registry instance
resolver_registry = ResolverRegistry()


def get_resolver_registry() -> ResolverRegistry:
    """Get the global resolver registry."""
    return resolver_registry
