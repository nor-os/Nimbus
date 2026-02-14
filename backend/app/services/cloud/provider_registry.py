"""
Overview: Provider registry — maps provider names to CloudProviderInterface implementations.
Architecture: Plugin registry for cloud provider drivers (Section 11)
Dependencies: None (protocol-based)
Concepts: Each provider (Proxmox, AWS, etc.) registers its implementation at startup.
    Phase 11 adds the first concrete driver (ProxmoxProvider). Until then, the registry
    is empty and connectivity tests fall back to credential-only validation.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class CloudProviderInterface(Protocol):
    """Protocol that all cloud provider drivers must implement."""

    async def validate_credentials(self, credentials: dict) -> bool:
        """Validate that credentials can connect to the provider."""
        ...

    async def list_resources(
        self, credentials: dict, resource_type: str, **kwargs: Any
    ) -> list[dict]:
        """List resources of a given type."""
        ...

    async def get_resource(
        self, credentials: dict, resource_type: str, resource_id: str
    ) -> dict | None:
        """Get a single resource by ID."""
        ...

    async def get_cost_data(
        self, credentials: dict, **kwargs: Any
    ) -> list[dict]:
        """Get cost/billing data."""
        ...


class ProviderRegistry:
    """Registry of cloud provider driver implementations."""

    def __init__(self) -> None:
        self._providers: dict[str, CloudProviderInterface] = {}

    def register(self, provider_name: str, implementation: CloudProviderInterface) -> None:
        """Register a provider driver implementation."""
        key = provider_name.lower()
        self._providers[key] = implementation
        logger.info("Registered cloud provider driver: %s", provider_name)

    def get(self, provider_name: str) -> CloudProviderInterface | None:
        """Get a registered provider driver, or None if not registered."""
        return self._providers.get(provider_name.lower())

    def list_registered(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def is_registered(self, provider_name: str) -> bool:
        """Check if a provider driver is registered."""
        return provider_name.lower() in self._providers


# Singleton registry instance
provider_registry = ProviderRegistry()
