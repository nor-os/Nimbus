"""
Overview: Base resolver class and context for deploy-time parameter pre-resolution.
Architecture: Resolver framework base (Section 11)
Dependencies: abc, dataclasses, sqlalchemy
Concepts: Resolvers transform abstract parameter requests into concrete values at deploy time.
    Each resolver type handles a specific domain (IPAM, naming, image selection).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ResolverContext:
    """Context passed to resolvers during parameter resolution."""

    tenant_id: uuid.UUID
    environment_id: uuid.UUID | None
    landing_zone_id: uuid.UUID | None
    provider_id: uuid.UUID | None
    db: AsyncSession
    dry_run: bool = False
    component_id: uuid.UUID | None = None
    deployment_id: uuid.UUID | None = None


class BaseResolver(ABC):
    """Abstract base for all resolvers."""

    resolver_type: str

    @abstractmethod
    async def resolve(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Resolve parameters.

        Args:
            params: Input parameters matching the resolver's input_schema.
            config: Configuration from resolver_configurations for the current scope.
            context: Deployment context (tenant, environment, landing zone, db session).

        Returns:
            Dict matching the resolver's output_schema.
        """

    async def release(
        self,
        allocation_ref: dict,
        config: dict,
        context: ResolverContext,
    ) -> bool:
        """Release a previously allocated resource.

        Args:
            allocation_ref: Reference dict identifying the allocation to release.
            config: Resolver configuration for the current scope.
            context: Deployment context.

        Returns:
            True if release was successful.
        """
        raise NotImplementedError(
            f"Resolver '{self.resolver_type}' does not support release"
        )

    async def update(
        self,
        current: dict,
        new_params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Update an existing allocation with new parameters.

        Args:
            current: Current resolver output (from previous resolve).
            new_params: New input parameters.
            config: Resolver configuration for the current scope.
            context: Deployment context.

        Returns:
            Updated output dict.
        """
        raise NotImplementedError(
            f"Resolver '{self.resolver_type}' does not support update"
        )

    async def validate(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> list[str]:
        """Validate parameters before resolution.

        Args:
            params: Input parameters to validate.
            config: Resolver configuration for the current scope.
            context: Deployment context.

        Returns:
            List of validation error strings. Empty list means valid.
        """
        raise NotImplementedError(
            f"Resolver '{self.resolver_type}' does not support validate"
        )
