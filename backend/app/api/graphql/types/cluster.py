"""
Overview: GraphQL types for service clusters — output types, input types, and enums.
Architecture: GraphQL type definitions for cluster operations (Section 8)
Dependencies: strawberry
Concepts: Service clusters are blueprint templates with slots and parameters.
    CI assignment is a deployment-time concern, not part of the blueprint.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON


# ── Enums ─────────────────────────────────────────────────────────────


@strawberry.enum
class ClusterTypeGQL(Enum):
    SERVICE_CLUSTER = "service_cluster"
    SERVICE_GROUP = "service_group"


# ── Output Types ──────────────────────────────────────────────────────


@strawberry.type
class ServiceClusterSlotType:
    id: uuid.UUID
    cluster_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    allowed_ci_class_ids: JSON | None
    semantic_category_id: uuid.UUID | None
    semantic_category_name: str | None
    semantic_type_id: uuid.UUID | None
    semantic_type_name: str | None
    min_count: int
    max_count: int | None
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackBlueprintParameterType:
    id: uuid.UUID
    cluster_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    parameter_schema: JSON | None
    default_value: JSON | None
    source_type: str
    source_slot_id: uuid.UUID | None
    source_slot_name: str | None
    source_property_path: str | None
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceClusterType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    cluster_type: str
    architecture_topology_id: uuid.UUID | None
    topology_node_id: str | None
    tags: JSON
    stack_tag_key: str | None
    metadata_: JSON | None = strawberry.field(name="metadata", default=None)
    slots: list[ServiceClusterSlotType]
    parameters: list[StackBlueprintParameterType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceClusterListType:
    items: list[ServiceClusterType]
    total: int


# ── Stack Types ──────────────────────────────────────────────────────


@strawberry.type
class StackInstanceType:
    tag_value: str
    ci_count: int
    active_count: int
    planned_count: int
    maintenance_count: int


@strawberry.type
class StackListType:
    blueprint_id: str
    blueprint_name: str
    tag_key: str
    stacks: list[StackInstanceType]
    total: int


# ── Input Types ───────────────────────────────────────────────────────


@strawberry.input
class ServiceClusterSlotInput:
    name: str
    display_name: str | None = None
    description: str | None = None
    allowed_ci_class_ids: JSON | None = None
    semantic_category_id: uuid.UUID | None = None
    semantic_type_id: uuid.UUID | None = None
    min_count: int = 1
    max_count: int | None = None
    is_required: bool = True
    sort_order: int = 0


@strawberry.input
class ServiceClusterCreateInput:
    name: str
    description: str | None = None
    cluster_type: str = "service_cluster"
    architecture_topology_id: uuid.UUID | None = None
    topology_node_id: str | None = None
    tags: JSON | None = None
    stack_tag_key: str | None = None
    metadata_: JSON | None = strawberry.field(name="metadata", default=None)
    slots: list[ServiceClusterSlotInput] | None = None


@strawberry.input
class ServiceClusterUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    cluster_type: str | None = None
    architecture_topology_id: uuid.UUID | None = strawberry.UNSET
    topology_node_id: str | None = strawberry.UNSET
    tags: JSON | None = None
    stack_tag_key: str | None = strawberry.UNSET
    metadata_: JSON | None = strawberry.field(name="metadata", default=strawberry.UNSET)


@strawberry.input
class BlueprintParameterCreateInput:
    name: str
    display_name: str | None = None
    description: str | None = None
    parameter_schema: JSON | None = None
    default_value: JSON | None = None
    is_required: bool = False
    sort_order: int = 0


@strawberry.input
class BlueprintParameterUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    parameter_schema: JSON | None = strawberry.UNSET
    default_value: JSON | None = strawberry.UNSET
    is_required: bool | None = None
    sort_order: int | None = None


@strawberry.input
class ServiceClusterSlotUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    allowed_ci_class_ids: JSON | None = strawberry.UNSET
    semantic_category_id: uuid.UUID | None = strawberry.UNSET
    semantic_type_id: uuid.UUID | None = strawberry.UNSET
    min_count: int | None = None
    max_count: int | None = strawberry.UNSET
    is_required: bool | None = None
    sort_order: int | None = None
