"""
Overview: Strawberry GraphQL types for landing zones, environments, and IPAM.
Architecture: GraphQL type definitions for landing zones & IPAM (Section 7.2)
Dependencies: strawberry
Concepts: Landing zone types, environment types, IPAM types, input types
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ──────────────────────────────────────────────────────────────

@strawberry.enum
class LandingZoneStatusGQL(Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


@strawberry.enum
class EnvironmentStatusGQL(Enum):
    PLANNED = "PLANNED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DECOMMISSIONING = "DECOMMISSIONING"
    DECOMMISSIONED = "DECOMMISSIONED"


@strawberry.enum
class AddressSpaceStatusGQL(Enum):
    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    RESERVED = "RESERVED"


@strawberry.enum
class AllocationTypeGQL(Enum):
    REGION = "REGION"
    PROVIDER_RESERVED = "PROVIDER_RESERVED"
    TENANT_POOL = "TENANT_POOL"
    VCN = "VCN"
    SUBNET = "SUBNET"


@strawberry.enum
class AllocationStatusGQL(Enum):
    PLANNED = "PLANNED"
    ALLOCATED = "ALLOCATED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"


@strawberry.enum
class ReservationStatusGQL(Enum):
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"


# ── Landing Zone Types ─────────────────────────────────────────────────

@strawberry.type
class LandingZoneTagPolicyType:
    id: uuid.UUID
    landing_zone_id: uuid.UUID
    tag_key: str
    display_name: str
    description: str | None
    is_required: bool
    allowed_values: strawberry.scalars.JSON | None
    default_value: str | None
    inherited: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class LandingZoneRegionType:
    id: uuid.UUID
    landing_zone_id: uuid.UUID
    region_identifier: str
    display_name: str
    is_primary: bool
    is_dr: bool
    settings: strawberry.scalars.JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class HierarchyLevelType:
    type_id: str
    label: str
    icon: str
    allowed_children: list[str]
    supports_ipam: bool
    supports_tags: bool
    supports_environment: bool


@strawberry.type
class ProviderHierarchyType:
    provider_name: str
    root_type: str
    levels: list[HierarchyLevelType]


@strawberry.type
class LandingZoneType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    backend_id: uuid.UUID
    topology_id: uuid.UUID | None
    cloud_tenancy_id: uuid.UUID | None
    name: str
    description: str | None
    status: LandingZoneStatusGQL
    version: int
    settings: strawberry.scalars.JSON | None
    network_config: strawberry.scalars.JSON | None
    iam_config: strawberry.scalars.JSON | None
    security_config: strawberry.scalars.JSON | None
    naming_config: strawberry.scalars.JSON | None
    hierarchy: strawberry.scalars.JSON | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    regions: list[LandingZoneRegionType]
    tag_policies: list[LandingZoneTagPolicyType]


# ── Environment Types ──────────────────────────────────────────────────

@strawberry.type
class EnvironmentTemplateType:
    id: uuid.UUID
    provider_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    color: str | None
    default_tags: strawberry.scalars.JSON | None
    default_policies: strawberry.scalars.JSON | None
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantEnvironmentType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    template_id: uuid.UUID | None
    name: str
    display_name: str
    description: str | None
    status: EnvironmentStatusGQL
    root_compartment_id: uuid.UUID | None
    tags: strawberry.scalars.JSON
    policies: strawberry.scalars.JSON
    settings: strawberry.scalars.JSON | None
    network_config: strawberry.scalars.JSON | None
    iam_config: strawberry.scalars.JSON | None
    security_config: strawberry.scalars.JSON | None
    monitoring_config: strawberry.scalars.JSON | None
    provider_name: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── IPAM Types ─────────────────────────────────────────────────────────

@strawberry.type
class IpReservationType:
    id: uuid.UUID
    allocation_id: uuid.UUID
    ip_address: str
    hostname: str | None
    purpose: str
    ci_id: uuid.UUID | None
    status: ReservationStatusGQL
    reserved_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class AddressAllocationType:
    id: uuid.UUID
    address_space_id: uuid.UUID
    parent_allocation_id: uuid.UUID | None
    tenant_environment_id: uuid.UUID | None
    name: str
    description: str | None
    cidr: str
    allocation_type: AllocationTypeGQL
    status: AllocationStatusGQL
    purpose: str | None
    semantic_type_id: uuid.UUID | None
    cloud_resource_id: str | None
    utilization_percent: float | None
    metadata: strawberry.scalars.JSON | None
    created_at: datetime
    updated_at: datetime
    children: list["AddressAllocationType"]
    reservations: list[IpReservationType]


@strawberry.type
class AddressSpaceType:
    id: uuid.UUID
    landing_zone_id: uuid.UUID
    region_id: uuid.UUID | None
    name: str
    description: str | None
    cidr: str
    ip_version: int
    status: AddressSpaceStatusGQL
    created_at: datetime
    updated_at: datetime
    allocations: list[AddressAllocationType]


@strawberry.type
class CidrSuggestionType:
    cidr: str | None
    available: bool


@strawberry.type
class CidrSummaryType:
    network: str
    broadcast: str
    prefix_length: int
    total_addresses: int
    usable_addresses: int
    ip_version: int
    is_private: bool


# ── Input Types ────────────────────────────────────────────────────────

@strawberry.input
class LandingZoneCreateInput:
    name: str
    backend_id: uuid.UUID
    topology_id: uuid.UUID | None = None
    description: str | None = None
    cloud_tenancy_id: uuid.UUID | None = None
    settings: strawberry.scalars.JSON | None = None
    hierarchy: strawberry.scalars.JSON | None = None


@strawberry.input
class LandingZoneUpdateInput:
    name: str | None = None
    description: str | None = None
    settings: strawberry.scalars.JSON | None = None
    network_config: strawberry.scalars.JSON | None = None
    iam_config: strawberry.scalars.JSON | None = None
    security_config: strawberry.scalars.JSON | None = None
    naming_config: strawberry.scalars.JSON | None = None
    hierarchy: strawberry.scalars.JSON | None = None


@strawberry.input
class LandingZoneRegionInput:
    region_identifier: str
    display_name: str
    is_primary: bool = False
    is_dr: bool = False
    settings: strawberry.scalars.JSON | None = None


@strawberry.input
class TagPolicyInput:
    tag_key: str
    display_name: str
    description: str | None = None
    is_required: bool = False
    allowed_values: strawberry.scalars.JSON | None = None
    default_value: str | None = None
    inherited: bool = True


@strawberry.input
class EnvironmentTemplateCreateInput:
    provider_id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    default_tags: strawberry.scalars.JSON | None = None
    default_policies: strawberry.scalars.JSON | None = None
    sort_order: int = 0


@strawberry.input
class TenantEnvironmentCreateInput:
    landing_zone_id: uuid.UUID | None = None
    name: str
    display_name: str
    template_id: uuid.UUID | None = None
    description: str | None = None
    root_compartment_id: uuid.UUID | None = None
    tags: strawberry.scalars.JSON | None = None
    policies: strawberry.scalars.JSON | None = None
    settings: strawberry.scalars.JSON | None = None
    network_config: strawberry.scalars.JSON | None = None
    iam_config: strawberry.scalars.JSON | None = None
    security_config: strawberry.scalars.JSON | None = None
    monitoring_config: strawberry.scalars.JSON | None = None


@strawberry.input
class TenantEnvironmentUpdateInput:
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    tags: strawberry.scalars.JSON | None = None
    policies: strawberry.scalars.JSON | None = None
    settings: strawberry.scalars.JSON | None = None
    network_config: strawberry.scalars.JSON | None = None
    iam_config: strawberry.scalars.JSON | None = None
    security_config: strawberry.scalars.JSON | None = None
    monitoring_config: strawberry.scalars.JSON | None = None


@strawberry.input
class AddressSpaceCreateInput:
    landing_zone_id: uuid.UUID
    name: str
    cidr: str
    region_id: uuid.UUID | None = None
    description: str | None = None
    ip_version: int = 4


@strawberry.input
class AllocationCreateInput:
    address_space_id: uuid.UUID
    name: str
    cidr: str
    allocation_type: AllocationTypeGQL
    parent_allocation_id: uuid.UUID | None = None
    tenant_environment_id: uuid.UUID | None = None
    purpose: str | None = None
    description: str | None = None


@strawberry.input
class IpReservationCreateInput:
    allocation_id: uuid.UUID
    ip_address: str
    purpose: str
    hostname: str | None = None
    ci_id: uuid.UUID | None = None


# ── Blueprint Types ───────────────────────────────────────────────────

@strawberry.type
class LandingZoneBlueprintType:
    id: str
    name: str
    provider_name: str
    description: str
    complexity: str
    features: list[str]
    hierarchy: strawberry.scalars.JSON
    network_config: strawberry.scalars.JSON
    iam_config: strawberry.scalars.JSON
    security_config: strawberry.scalars.JSON
    naming_config: strawberry.scalars.JSON
    default_tags: strawberry.scalars.JSON
    default_address_spaces: strawberry.scalars.JSON


# ── Validation Types ─────────────────────────────────────────────────

@strawberry.type
class LandingZoneCheckType:
    key: str
    label: str
    status: str
    message: str


@strawberry.type
class LandingZoneValidationType:
    ready: bool
    checks: list[LandingZoneCheckType]
