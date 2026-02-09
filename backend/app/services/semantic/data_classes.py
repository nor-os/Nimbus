"""
Overview: Data transfer objects for provider-to-semantic resource mapping pipeline.
Architecture: Data classes used by CloudProviderInterface and MappingEngine (Section 5)
Dependencies: dataclasses, enum, datetime
Concepts: ProviderResource = raw cloud resource, SemanticResource = normalized resource,
    CostData = billing info, ResourceFilter = query filter for provider APIs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ProviderCapability(StrEnum):
    """Capabilities that a cloud provider may support."""
    COMPUTE = "compute"
    NETWORK = "network"
    STORAGE = "storage"
    DATABASE = "database"
    SECURITY = "security"
    MONITORING = "monitoring"
    APPLICATION = "application"


@dataclass
class ProviderResource:
    """A resource as returned by a cloud provider's API (raw form)."""
    provider_name: str
    resource_type: str
    resource_id: str
    name: str
    region: str | None = None
    raw_attributes: dict = field(default_factory=dict)
    discovered_at: datetime | None = None


@dataclass
class SemanticResource:
    """A provider resource normalized into the semantic model."""
    semantic_type: str
    provider_resource_id: str
    attributes: dict = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)


@dataclass
class CostData:
    """Billing/cost information for a provider resource."""
    resource_id: str
    period_start: datetime
    period_end: datetime
    amount: float
    currency: str = "USD"
    breakdown: dict = field(default_factory=dict)


@dataclass
class ResourceFilter:
    """Filter criteria for querying provider resources."""
    resource_types: list[str] | None = None
    regions: list[str] | None = None
    tags: dict[str, str] | None = None
    name_pattern: str | None = None
