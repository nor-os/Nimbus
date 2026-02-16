"""
Overview: Resource Manager — per-environment service mediating all CMDB/IPAM interactions.
Architecture: Resource Manager service layer (Section 11)
Dependencies: app.services.resolver.base, app.services.resolver.registry, app.models
Concepts: The Resource Manager is the single entry point for resolver lifecycle operations
    (resolve, release, update, validate) and CI creation/management during deployments.
    It uses the ResolverRegistry for handler lookup and scoped configuration retrieval.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.resolver.base import BaseResolver, ResolverContext

logger = logging.getLogger(__name__)


class ResourceManager:
    """Per-environment resource manager — mediates CMDB/IPAM interactions.

    All resolver lifecycle operations and CI management flow through this service.
    """

    def __init__(
        self,
        environment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        *,
        landing_zone_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> None:
        self.environment_id = environment_id
        self.tenant_id = tenant_id
        self.db = db
        self.landing_zone_id = landing_zone_id
        self.provider_id = provider_id

    def _make_context(
        self,
        *,
        dry_run: bool = False,
        component_id: uuid.UUID | None = None,
        deployment_id: uuid.UUID | None = None,
    ) -> ResolverContext:
        return ResolverContext(
            tenant_id=self.tenant_id,
            environment_id=self.environment_id,
            landing_zone_id=self.landing_zone_id,
            provider_id=self.provider_id,
            db=self.db,
            dry_run=dry_run,
            component_id=component_id,
            deployment_id=deployment_id,
        )

    def _get_handler(self, resolver_type: str) -> BaseResolver:
        from app.services.resolver.registry import get_resolver_registry

        handler = get_resolver_registry().get(resolver_type)
        if not handler:
            raise ValueError(f"No handler registered for resolver type '{resolver_type}'")
        return handler

    async def _get_config(self, resolver_type: str) -> dict:
        from app.services.resolver.registry import get_resolver_registry

        registry = get_resolver_registry()
        return await registry._get_config(
            self.db, resolver_type, self.landing_zone_id, self.environment_id
        )

    async def resolve(
        self,
        resolver_type: str,
        params: dict,
        *,
        component_id: uuid.UUID | None = None,
        deployment_id: uuid.UUID | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Resolve parameters using the specified resolver handler."""
        handler = self._get_handler(resolver_type)
        config = await self._get_config(resolver_type)
        context = self._make_context(
            dry_run=dry_run,
            component_id=component_id,
            deployment_id=deployment_id,
        )
        return await handler.resolve(params, config, context)

    async def release(
        self,
        resolver_type: str,
        allocation_ref: dict,
    ) -> bool:
        """Release a previously allocated resource."""
        handler = self._get_handler(resolver_type)
        config = await self._get_config(resolver_type)
        context = self._make_context()
        return await handler.release(allocation_ref, config, context)

    async def update(
        self,
        resolver_type: str,
        current: dict,
        new_params: dict,
    ) -> dict:
        """Update an existing allocation with new parameters."""
        handler = self._get_handler(resolver_type)
        config = await self._get_config(resolver_type)
        context = self._make_context()
        return await handler.update(current, new_params, config, context)

    async def validate(
        self,
        resolver_type: str,
        params: dict,
    ) -> list[str]:
        """Validate parameters before resolution."""
        handler = self._get_handler(resolver_type)
        config = await self._get_config(resolver_type)
        context = self._make_context()
        return await handler.validate(params, config, context)

    async def create_ci(
        self,
        component_id: uuid.UUID,
        resolved_params: dict,
        deployment_id: uuid.UUID,
    ):
        """Create a Configuration Item from resolved parameters.

        Uses CIService to create the CI, auto-maps semantic_type from the component,
        and sets lifecycle to 'provisioning'.
        """
        from sqlalchemy import select

        from app.models.cmdb import CIClass, ConfigurationItem
        from app.models.component import Component

        result = await self.db.execute(
            select(Component).where(
                Component.id == component_id,
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            raise ValueError(f"Component {component_id} not found")

        # Find the CI class matching the component's semantic type
        ci_class_result = await self.db.execute(
            select(CIClass).where(
                CIClass.semantic_type_id == component.semantic_type_id,
                CIClass.deleted_at.is_(None),
            ).limit(1)
        )
        ci_class = ci_class_result.scalar_one_or_none()

        ci = ConfigurationItem(
            tenant_id=self.tenant_id,
            ci_class_id=ci_class.id if ci_class else None,
            name=resolved_params.get("name", {}).get("name", f"ci-{component.name}") if isinstance(resolved_params.get("name"), dict) else resolved_params.get("name", f"ci-{component.name}"),
            display_name=resolved_params.get("name", {}).get("name", component.display_name) if isinstance(resolved_params.get("name"), dict) else component.display_name,
            status="provisioning",
            attributes=resolved_params,
            environment_id=self.environment_id,
        )
        self.db.add(ci)
        await self.db.flush()
        await self.db.refresh(ci)
        return ci

    async def update_ci_state(self, ci_id: uuid.UUID, state: str) -> None:
        """Transition a CI's lifecycle state."""
        from sqlalchemy import select

        from app.models.cmdb import ConfigurationItem

        result = await self.db.execute(
            select(ConfigurationItem).where(ConfigurationItem.id == ci_id)
        )
        ci = result.scalar_one_or_none()
        if ci:
            ci.status = state
            await self.db.flush()

    async def delete_ci(self, ci_id: uuid.UUID) -> None:
        """Soft-delete a CI (used as compensation in saga)."""
        from datetime import datetime, timezone

        from sqlalchemy import select

        from app.models.cmdb import ConfigurationItem

        result = await self.db.execute(
            select(ConfigurationItem).where(ConfigurationItem.id == ci_id)
        )
        ci = result.scalar_one_or_none()
        if ci:
            ci.deleted_at = datetime.now(timezone.utc)
            await self.db.flush()
