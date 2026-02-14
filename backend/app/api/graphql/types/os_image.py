"""
Overview: GraphQL types and input types for the OS image catalog.
Architecture: GraphQL type definitions for OS image management (Section 5)
Dependencies: strawberry
Concepts: OS images, provider mappings, CRUD inputs
"""

import uuid
from datetime import datetime

import strawberry


@strawberry.type
class OsImageProviderMappingType:
    id: uuid.UUID
    os_image_id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    provider_display_name: str
    image_reference: str
    notes: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class OsImageTenantAssignmentType:
    id: uuid.UUID
    os_image_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    created_at: datetime


@strawberry.type
class OsImageType:
    id: uuid.UUID
    name: str
    display_name: str
    os_family: str
    version: str
    architecture: str
    description: str | None
    icon: str | None
    sort_order: int
    is_system: bool
    provider_mappings: list[OsImageProviderMappingType]
    tenant_assignments: list[OsImageTenantAssignmentType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class OsImageListType:
    items: list[OsImageType]
    total: int


# -- Input types --------------------------------------------------------


@strawberry.input
class OsImageInput:
    name: str
    display_name: str
    os_family: str
    version: str
    architecture: str = "x86_64"
    description: str | None = None
    icon: str | None = None
    sort_order: int = 0


@strawberry.input
class OsImageUpdateInput:
    display_name: str | None = None
    os_family: str | None = None
    version: str | None = None
    architecture: str | None = None
    description: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    sort_order: int | None = None


@strawberry.input
class OsImageProviderMappingInput:
    os_image_id: uuid.UUID
    provider_id: uuid.UUID
    image_reference: str
    notes: str | None = None


@strawberry.input
class OsImageProviderMappingUpdateInput:
    image_reference: str | None = None
    notes: str | None = strawberry.UNSET


@strawberry.input
class SetImageTenantsInput:
    os_image_id: uuid.UUID
    tenant_ids: list[uuid.UUID]
