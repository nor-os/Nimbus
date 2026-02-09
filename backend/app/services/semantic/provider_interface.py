"""
Overview: Abstract interface contract that all cloud provider implementations must follow.
Architecture: Provider abstraction layer (Section 5). Proxmox (Phase 11), AWS/Azure/GCP/OCI
    (Phase 18) implement this interface.
Dependencies: abc, uuid, app.services.semantic.data_classes
Concepts: Each provider implements 6 properties/methods: provider_name, provider_id, display_name,
    capabilities, plus list_resources, get_resource, get_cost_data, map_to_semantic,
    validate_credentials. Credentials are opaque dicts — actual credential models are defined
    in Phase 11+.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.services.semantic.data_classes import (
    CostData,
    ProviderCapability,
    ProviderResource,
    ResourceFilter,
    SemanticResource,
)


class CloudProviderInterface(ABC):
    """Abstract base class for cloud provider implementations.

    Every provider (Proxmox, AWS, Azure, GCP, OCI) must implement these
    methods and properties to integrate with the Nimbus semantic layer.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'proxmox', 'aws')."""
        ...

    @property
    @abstractmethod
    def provider_id(self) -> uuid.UUID:
        """The UUID of this provider's record in the semantic_providers table."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g. 'Proxmox VE', 'Amazon Web Services')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[ProviderCapability]:
        """List of capability categories this provider supports."""
        ...

    @abstractmethod
    async def validate_credentials(self, credential: dict) -> bool:
        """Validate that the given credentials can connect to the provider.

        Args:
            credential: Provider-specific credential dict (API key, token, etc.)

        Returns:
            True if credentials are valid and the provider is reachable.
        """
        ...

    @abstractmethod
    async def list_resources(
        self,
        credential: dict,
        filters: ResourceFilter | None = None,
    ) -> list[ProviderResource]:
        """List resources from the provider, optionally filtered.

        Args:
            credential: Provider-specific credential dict.
            filters: Optional filters to narrow the resource list.

        Returns:
            List of raw provider resources.
        """
        ...

    @abstractmethod
    async def get_resource(
        self,
        credential: dict,
        resource_id: str,
    ) -> ProviderResource | None:
        """Get a single resource by its provider-specific ID.

        Args:
            credential: Provider-specific credential dict.
            resource_id: Provider-specific resource identifier.

        Returns:
            The resource if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_cost_data(
        self,
        credential: dict,
        resource_id: str,
        period_start: str,
        period_end: str,
    ) -> CostData | None:
        """Get cost/billing data for a resource over a time period.

        Args:
            credential: Provider-specific credential dict.
            resource_id: Provider-specific resource identifier.
            period_start: ISO-8601 date string for period start.
            period_end: ISO-8601 date string for period end.

        Returns:
            Cost data if available, None otherwise.
        """
        ...

    @abstractmethod
    async def map_to_semantic(
        self,
        resource: ProviderResource,
    ) -> SemanticResource:
        """Map a provider resource to the semantic model.

        Providers should use the MappingEngine for the actual resolution,
        but may add provider-specific attribute transformations.

        Args:
            resource: A raw provider resource.

        Returns:
            The resource normalized into the semantic model.
        """
        ...
