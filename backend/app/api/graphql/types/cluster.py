"""
Overview: GraphQL types for service clusters — output types, input types, and enums.
Architecture: GraphQL type definitions for cluster operations (Section 8)
Dependencies: strawberry
Concepts: Service clusters are blueprint templates with slots and parameters.
    Evolved to full stack blueprints with versioning, components, instances,
    governance, operational workflows, and DR reservations.
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


@strawberry.enum
class BlueprintCategoryGQL(Enum):
    COMPUTE = "COMPUTE"
    DATABASE = "DATABASE"
    NETWORKING = "NETWORKING"
    STORAGE = "STORAGE"
    PLATFORM = "PLATFORM"
    SECURITY = "SECURITY"
    MONITORING = "MONITORING"
    CUSTOM = "CUSTOM"


@strawberry.enum
class BindingDirectionGQL(Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


@strawberry.enum
class StackWorkflowKindGQL(Enum):
    PROVISION = "PROVISION"
    DEPROVISION = "DEPROVISION"
    UPDATE = "UPDATE"
    SCALE = "SCALE"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"
    FAILOVER = "FAILOVER"
    HEALTH_CHECK = "HEALTH_CHECK"
    CUSTOM = "CUSTOM"


@strawberry.enum
class StackInstanceStatusGQL(Enum):
    PLANNED = "PLANNED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DEGRADED = "DEGRADED"
    DECOMMISSIONING = "DECOMMISSIONING"
    DECOMMISSIONED = "DECOMMISSIONED"
    FAILED = "FAILED"


@strawberry.enum
class HealthStatusGQL(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@strawberry.enum
class ReservationTypeGQL(Enum):
    HOT_STANDBY = "HOT_STANDBY"
    WARM_STANDBY = "WARM_STANDBY"
    COLD_STANDBY = "COLD_STANDBY"
    PILOT_LIGHT = "PILOT_LIGHT"


@strawberry.enum
class ReservationStatusGQL(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


@strawberry.enum
class SyncMethodGQL(Enum):
    REAL_TIME = "REAL_TIME"
    SCHEDULED = "SCHEDULED"
    ON_DEMAND = "ON_DEMAND"
    WORKFLOW = "WORKFLOW"


@strawberry.enum
class TestResultGQL(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NOT_TESTED = "NOT_TESTED"


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
    component_id: uuid.UUID | None = None
    default_parameters: JSON | None = None
    depends_on: JSON | None = None
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
class StackBlueprintVersionType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    version: int
    input_schema: JSON | None
    output_schema: JSON | None
    component_graph: JSON | None
    variable_bindings: JSON | None
    changelog: str | None
    published_by: uuid.UUID | None
    created_at: datetime


@strawberry.type
class StackBlueprintComponentType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    component_id: uuid.UUID
    node_id: str
    label: str
    description: str | None
    sort_order: int
    is_optional: bool
    default_parameters: JSON | None
    depends_on: JSON | None
    # Resolved from Component FK
    component_name: str | None = None
    component_version: int | None = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackVariableBindingType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    direction: str
    variable_name: str
    target_node_id: str
    target_parameter: str
    transform_expression: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackBlueprintGovernanceType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    tenant_id: uuid.UUID
    is_allowed: bool
    parameter_constraints: JSON | None
    max_instances: int | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackWorkflowType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    workflow_definition_id: uuid.UUID
    workflow_kind: str
    name: str
    display_name: str | None
    is_required: bool
    trigger_conditions: JSON | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackInstanceComponentType:
    id: uuid.UUID
    stack_instance_id: uuid.UUID
    blueprint_component_id: uuid.UUID | None
    component_id: uuid.UUID
    component_version: int | None
    ci_id: uuid.UUID | None
    deployment_id: uuid.UUID | None
    status: str
    resolved_parameters: JSON | None
    outputs: JSON | None
    pulumi_state_url: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackRuntimeInstanceType:
    """Deployed runtime stack instance (renamed from StackInstanceType to avoid collision)."""
    id: uuid.UUID
    blueprint_id: uuid.UUID
    blueprint_version: int
    tenant_id: uuid.UUID
    environment_id: uuid.UUID | None
    name: str
    status: str
    input_values: JSON | None
    output_values: JSON | None
    component_states: JSON | None
    health_status: str
    deployed_by: uuid.UUID | None
    deployed_at: datetime | None
    ha_config: JSON | None = None
    dr_config: JSON | None = None
    components: list[StackInstanceComponentType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackRuntimeInstanceListType:
    items: list[StackRuntimeInstanceType]
    total: int


@strawberry.type
class ReservationSyncPolicyType:
    id: uuid.UUID
    reservation_id: uuid.UUID
    source_node_id: str
    target_node_id: str
    sync_method: str
    sync_interval_seconds: int | None
    sync_workflow_id: uuid.UUID | None
    last_synced_at: datetime | None
    sync_lag_seconds: int | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackReservationType:
    id: uuid.UUID
    stack_instance_id: uuid.UUID
    tenant_id: uuid.UUID
    reservation_type: str
    target_environment_id: uuid.UUID | None
    target_provider_id: uuid.UUID | None
    reserved_resources: JSON | None
    rto_seconds: int | None
    rpo_seconds: int | None
    status: str
    cost_per_hour: float | None
    last_tested_at: datetime | None
    test_result: str | None
    sync_policies: list[ReservationSyncPolicyType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StackReservationListType:
    items: list[StackReservationType]
    total: int


@strawberry.type
class BlueprintReservationTemplateType:
    id: uuid.UUID
    blueprint_id: uuid.UUID
    reservation_type: str
    resource_percentage: int
    target_environment_label: str | None
    target_provider_id: uuid.UUID | None
    rto_seconds: int | None
    rpo_seconds: int | None
    auto_create_on_deploy: bool
    sync_policies_template: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ComponentReservationTemplateType:
    id: uuid.UUID
    blueprint_component_id: uuid.UUID
    reservation_type: str
    resource_percentage: int
    target_environment_label: str | None
    target_provider_id: uuid.UUID | None
    rto_seconds: int | None
    rpo_seconds: int | None
    auto_create_on_deploy: bool
    sync_policies_template: JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceClusterType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    cluster_type: str
    architecture_topology_id: uuid.UUID | None
    topology_node_id: str | None
    tags: JSON
    stack_tag_key: str | None
    metadata_: JSON | None = strawberry.field(name="metadata", default=None)
    # New blueprint evolution fields
    provider_id: uuid.UUID | None = None
    category: str | None = None
    icon: str | None = None
    input_schema: JSON | None = None
    output_schema: JSON | None = None
    version: int = 1
    is_published: bool = False
    is_system: bool = False
    display_name: str | None = None
    created_by: uuid.UUID | None = None
    # HA/DR config schemas
    ha_config_schema: JSON | None = None
    ha_config_defaults: JSON | None = None
    dr_config_schema: JSON | None = None
    dr_config_defaults: JSON | None = None
    # Nested collections
    slots: list[ServiceClusterSlotType] = strawberry.field(default_factory=list)
    parameters: list[StackBlueprintParameterType] = strawberry.field(default_factory=list)
    blueprint_components: list[StackBlueprintComponentType] = strawberry.field(default_factory=list)
    variable_bindings: list[StackVariableBindingType] = strawberry.field(default_factory=list)
    reservation_template: BlueprintReservationTemplateType | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@strawberry.type
class ServiceClusterListType:
    items: list[ServiceClusterType]
    total: int


# ── Stack Tag Types (legacy — tag-based deployed instances) ───────────


@strawberry.type
class StackTagGroupType:
    """Tag-based deployed stack (legacy tag-key approach)."""
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
    stacks: list[StackTagGroupType]
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
    # New blueprint fields
    provider_id: uuid.UUID | None = None
    category: str | None = None
    icon: str | None = None
    input_schema: JSON | None = None
    output_schema: JSON | None = None
    display_name: str | None = None
    # HA/DR config schemas
    ha_config_schema: JSON | None = None
    ha_config_defaults: JSON | None = None
    dr_config_schema: JSON | None = None
    dr_config_defaults: JSON | None = None


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
    # New blueprint fields
    provider_id: uuid.UUID | None = strawberry.UNSET
    category: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    input_schema: JSON | None = strawberry.UNSET
    output_schema: JSON | None = strawberry.UNSET
    display_name: str | None = strawberry.UNSET
    # HA/DR config schemas
    ha_config_schema: JSON | None = strawberry.UNSET
    ha_config_defaults: JSON | None = strawberry.UNSET
    dr_config_schema: JSON | None = strawberry.UNSET
    dr_config_defaults: JSON | None = strawberry.UNSET


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


@strawberry.input
class BlueprintComponentInput:
    component_id: uuid.UUID
    node_id: str
    label: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_optional: bool = False
    default_parameters: JSON | None = None
    depends_on: JSON | None = None


@strawberry.input
class BlueprintComponentUpdateInput:
    label: str | None = None
    description: str | None = strawberry.UNSET
    sort_order: int | None = None
    is_optional: bool | None = None
    default_parameters: JSON | None = strawberry.UNSET
    depends_on: JSON | None = strawberry.UNSET


@strawberry.input
class VariableBindingInput:
    direction: str
    variable_name: str
    target_node_id: str
    target_parameter: str
    transform_expression: str | None = None


@strawberry.input
class ClusterGovernanceInput:
    governance_tenant_id: uuid.UUID
    is_allowed: bool = True
    parameter_constraints: JSON | None = None
    max_instances: int | None = None


@strawberry.input
class StackWorkflowInput:
    workflow_definition_id: uuid.UUID
    workflow_kind: str
    name: str
    display_name: str | None = None
    is_required: bool = False
    trigger_conditions: JSON | None = None
    sort_order: int = 0


@strawberry.input
class DeployStackInput:
    blueprint_id: uuid.UUID
    name: str
    environment_id: uuid.UUID | None = None
    input_values: JSON | None = None
    ha_config: JSON | None = None
    dr_config: JSON | None = None


@strawberry.input
class UpdateStackInstanceInput:
    status: str | None = None
    health_status: str | None = None
    output_values: JSON | None = strawberry.UNSET


@strawberry.input
class CreateReservationInput:
    stack_instance_id: uuid.UUID
    reservation_type: str
    target_environment_id: uuid.UUID | None = None
    target_provider_id: uuid.UUID | None = None
    reserved_resources: JSON | None = None
    rto_seconds: int | None = None
    rpo_seconds: int | None = None
    cost_per_hour: float | None = None


@strawberry.input
class UpdateReservationInput:
    reservation_type: str | None = None
    target_environment_id: uuid.UUID | None = strawberry.UNSET
    target_provider_id: uuid.UUID | None = strawberry.UNSET
    reserved_resources: JSON | None = strawberry.UNSET
    rto_seconds: int | None = strawberry.UNSET
    rpo_seconds: int | None = strawberry.UNSET
    cost_per_hour: float | None = strawberry.UNSET
    status: str | None = None


@strawberry.input
class ReservationTemplateInput:
    reservation_type: str
    resource_percentage: int = 80
    target_environment_label: str | None = None
    target_provider_id: uuid.UUID | None = None
    rto_seconds: int | None = None
    rpo_seconds: int | None = None
    auto_create_on_deploy: bool = True
    sync_policies_template: JSON | None = None


@strawberry.input
class ComponentReservationTemplateInput:
    reservation_type: str
    resource_percentage: int = 80
    target_environment_label: str | None = None
    target_provider_id: uuid.UUID | None = None
    rto_seconds: int | None = None
    rpo_seconds: int | None = None
    auto_create_on_deploy: bool = True
    sync_policies_template: JSON | None = None


@strawberry.input
class SyncPolicyInput:
    source_node_id: str
    target_node_id: str
    sync_method: str
    sync_interval_seconds: int | None = None
    sync_workflow_id: uuid.UUID | None = None
