"""
Overview: GraphQL types and input types for the CMDB — CI classes, configuration items,
    relationships, snapshots, templates, graph traversal, and compartments.
Architecture: GraphQL type definitions for CMDB operations (Section 8)
Dependencies: strawberry
Concepts: CMDB types mirror the model layer with denormalized display fields for the frontend.
    Input types use strawberry.UNSET for optional update fields.
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class LifecycleStateGQL(Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    DELETED = "deleted"


@strawberry.enum
class MeasuringUnitGQL(Enum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    GB = "gb"
    REQUEST = "request"
    USER = "user"
    INSTANCE = "instance"


# ── Output types ──────────────────────────────────────────────────────


@strawberry.type
class CIClassType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str
    parent_class_id: uuid.UUID | None
    semantic_type_id: uuid.UUID | None
    schema_def: JSON | None
    icon: str | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CIAttributeDefinitionType:
    id: uuid.UUID
    ci_class_id: uuid.UUID
    name: str
    display_name: str
    data_type: str
    is_required: bool
    default_value: JSON | None
    validation_rules: JSON | None
    sort_order: int


@strawberry.type
class CIClassDetailType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str
    parent_class_id: uuid.UUID | None
    semantic_type_id: uuid.UUID | None
    schema_def: JSON | None
    icon: str | None
    is_system: bool
    is_active: bool
    attribute_definitions: list[CIAttributeDefinitionType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CIType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    ci_class_id: uuid.UUID
    ci_class_name: str
    compartment_id: uuid.UUID | None
    name: str
    description: str | None
    lifecycle_state: LifecycleStateGQL
    attributes: JSON
    tags: JSON
    cloud_resource_id: str | None
    pulumi_urn: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CIListType:
    items: list[CIType]
    total: int


@strawberry.type
class RelationshipTypeType:
    id: uuid.UUID
    name: str
    display_name: str
    inverse_name: str
    description: str | None
    source_class_ids: JSON | None
    target_class_ids: JSON | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CIRelationshipType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    source_ci_id: uuid.UUID
    source_ci_name: str
    target_ci_id: uuid.UUID
    target_ci_name: str
    relationship_type_id: uuid.UUID
    relationship_type_name: str
    attributes: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CISnapshotType:
    id: uuid.UUID
    ci_id: uuid.UUID
    tenant_id: uuid.UUID
    version_number: int
    snapshot_data: JSON
    changed_by: uuid.UUID | None
    changed_at: datetime
    change_reason: str | None
    change_type: str


@strawberry.type
class CIVersionListType:
    items: list[CISnapshotType]
    total: int


@strawberry.type
class CITemplateType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    ci_class_id: uuid.UUID
    ci_class_name: str
    attributes: JSON
    tags: JSON
    relationship_templates: JSON | None
    constraints: JSON | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CITemplateListType:
    items: list[CITemplateType]
    total: int


@strawberry.type
class GraphNodeType:
    ci_id: str
    name: str
    ci_class: str
    depth: int
    path: list[str]


@strawberry.type
class VersionDiffType:
    version_a: int
    version_b: int
    changes: JSON


@strawberry.type
class CompartmentNodeType:
    id: str
    name: str
    description: str | None
    cloud_id: str | None
    provider_type: str | None
    children: list["CompartmentNodeType"]


@strawberry.type
class SavedSearchType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    query_text: str | None
    filters: JSON | None
    sort_config: JSON | None
    is_default: bool


# ── Input types ───────────────────────────────────────────────────────


@strawberry.input
class CICreateInput:
    ci_class_id: uuid.UUID
    name: str
    description: str | None = None
    compartment_id: uuid.UUID | None = None
    lifecycle_state: str = "planned"
    attributes: JSON | None = None
    tags: JSON | None = None
    cloud_resource_id: str | None = None
    pulumi_urn: str | None = None


@strawberry.input
class CIUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    attributes: JSON | None = None
    tags: JSON | None = None
    cloud_resource_id: str | None = strawberry.UNSET
    pulumi_urn: str | None = strawberry.UNSET


@strawberry.input
class CIClassCreateInput:
    name: str
    display_name: str
    parent_class_id: uuid.UUID | None = None
    schema_def: JSON | None = None
    icon: str | None = None


@strawberry.input
class CIClassUpdateInput:
    display_name: str | None = None
    icon: str | None = strawberry.UNSET
    is_active: bool | None = None
    schema_def: JSON | None = strawberry.UNSET


@strawberry.input
class CIRelationshipInput:
    source_ci_id: uuid.UUID
    target_ci_id: uuid.UUID
    relationship_type_id: uuid.UUID
    attributes: JSON | None = None


@strawberry.input
class CITemplateCreateInput:
    name: str
    ci_class_id: uuid.UUID
    description: str | None = None
    attributes: JSON | None = None
    tags: JSON | None = None
    relationship_templates: JSON | None = None
    constraints: JSON | None = None


@strawberry.input
class CITemplateUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    attributes: JSON | None = None
    tags: JSON | None = None
    relationship_templates: JSON | None = strawberry.UNSET
    constraints: JSON | None = strawberry.UNSET
    is_active: bool | None = None


@strawberry.input
class CIFromTemplateInput:
    template_id: uuid.UUID
    name: str
    compartment_id: uuid.UUID | None = None
    description: str | None = None
    attributes: JSON | None = None
    tags: JSON | None = None
    lifecycle_state: str = "planned"


@strawberry.input
class CompartmentCreateInput:
    name: str
    description: str | None = None
    parent_id: uuid.UUID | None = None
    cloud_id: str | None = None
    provider_type: str | None = None


@strawberry.input
class CompartmentUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    cloud_id: str | None = strawberry.UNSET
    provider_type: str | None = strawberry.UNSET


@strawberry.input
class SavedSearchInput:
    name: str
    query_text: str | None = None
    filters: JSON | None = None
    sort_config: JSON | None = None
