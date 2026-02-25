"""
Overview: GraphQL types and input types for cloud backends and IAM mappings.
Architecture: GraphQL type definitions for cloud backend management (Section 11)
Dependencies: strawberry
Concepts: CloudBackend types expose all fields except encrypted credentials (only hasCredentials).
    IAM mapping types expose the role-to-cloud-identity link. Input types support CRUD.
"""

import uuid
from datetime import datetime

import strawberry
from strawberry.scalars import JSON


# -- Output types -----------------------------------------------------------


@strawberry.type
class BackendRegionType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    backend_id: uuid.UUID
    region_identifier: str
    display_name: str
    provider_region_code: str | None
    is_enabled: bool
    availability_zones: JSON | None
    settings: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class BackendRegionInput:
    region_identifier: str
    display_name: str
    provider_region_code: str | None = None
    is_enabled: bool = True
    availability_zones: JSON | None = None
    settings: JSON | None = None


@strawberry.input
class BackendRegionUpdateInput:
    display_name: str | None = None
    provider_region_code: str | None = strawberry.UNSET
    is_enabled: bool | None = None
    availability_zones: JSON | None = strawberry.UNSET
    settings: JSON | None = strawberry.UNSET


@strawberry.type
class CloudBackendType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    provider_display_name: str
    provider_icon: str | None
    name: str
    description: str | None
    status: str
    has_credentials: bool
    credentials_schema_version: int
    scope_config: JSON | None
    endpoint_url: str | None
    is_shared: bool
    last_connectivity_check: datetime | None
    last_connectivity_status: str | None
    last_connectivity_error: str | None
    regions: list[BackendRegionType]
    iam_mapping_count: int
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CloudBackendIAMMappingType:
    id: uuid.UUID
    backend_id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    cloud_identity: JSON
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ConnectivityTestResult:
    success: bool
    message: str
    checked_at: str | None


# -- Input types ------------------------------------------------------------


@strawberry.input
class CloudBackendInput:
    provider_id: uuid.UUID
    name: str
    description: str | None = None
    status: str = "active"
    credentials: JSON | None = None
    scope_config: JSON | None = None
    endpoint_url: str | None = None
    is_shared: bool = False


@strawberry.input
class CloudBackendUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    status: str | None = None
    credentials: JSON | None = strawberry.UNSET
    scope_config: JSON | None = strawberry.UNSET
    endpoint_url: str | None = strawberry.UNSET
    is_shared: bool | None = None


@strawberry.input
class CloudBackendIAMMappingInput:
    role_id: uuid.UUID
    cloud_identity: JSON
    description: str | None = None
    is_active: bool = True


@strawberry.type
class ConfigOptionType:
    id: str
    domain: str
    category: str
    provider_name: str
    name: str
    display_name: str
    description: str
    detail: str
    icon: str
    implications: list[str]
    config_values: JSON
    conflicts_with: list[str]
    requires: list[str]
    related_resolver_types: list[str]
    related_component_names: list[str]
    sort_order: int
    is_default: bool
    tags: list[str]
    hierarchy_implications: JSON | None = None


@strawberry.type
class ConfigOptionCategoryType:
    name: str
    display_name: str
    description: str
    icon: str


@strawberry.input
class CloudBackendIAMMappingUpdateInput:
    cloud_identity: JSON | None = strawberry.UNSET
    description: str | None = strawberry.UNSET
    is_active: bool | None = None
