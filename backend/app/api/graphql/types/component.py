"""
Overview: Strawberry GraphQL types for components, resolvers, and governance.
Architecture: GraphQL type definitions for component framework (Section 11)
Dependencies: strawberry
Concepts: Component types, version snapshots, resolver definitions, governance rules, input types
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ──────────────────────────────────────────────────────────────

@strawberry.enum
class ComponentLanguageGQL(Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"


@strawberry.enum
class EstimatedDowntimeGQL(Enum):
    NONE = "NONE"
    BRIEF = "BRIEF"
    EXTENDED = "EXTENDED"


# ── Output Types ───────────────────────────────────────────────────────

@strawberry.type
class ComponentVersionType:
    id: uuid.UUID
    component_id: uuid.UUID
    version: int
    code: str
    input_schema: strawberry.scalars.JSON | None
    output_schema: strawberry.scalars.JSON | None
    resolver_bindings: strawberry.scalars.JSON | None
    changelog: str | None
    published_at: datetime
    published_by: uuid.UUID


@strawberry.type
class ComponentGovernanceType:
    id: uuid.UUID
    component_id: uuid.UUID
    tenant_id: uuid.UUID
    is_allowed: bool
    parameter_constraints: strawberry.scalars.JSON | None
    max_instances: int | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ComponentOperationType:
    id: uuid.UUID
    component_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    input_schema: strawberry.scalars.JSON | None
    output_schema: strawberry.scalars.JSON | None
    workflow_definition_id: uuid.UUID
    workflow_definition_name: str | None
    is_destructive: bool
    requires_approval: bool
    estimated_downtime: EstimatedDowntimeGQL
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ComponentType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    provider_id: uuid.UUID
    semantic_type_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    language: ComponentLanguageGQL
    code: str
    input_schema: strawberry.scalars.JSON | None
    output_schema: strawberry.scalars.JSON | None
    resolver_bindings: strawberry.scalars.JSON | None
    version: int
    is_published: bool
    is_system: bool
    upgrade_workflow_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    versions: list[ComponentVersionType]
    governance_rules: list[ComponentGovernanceType]
    operations: list[ComponentOperationType]
    # Resolved relation names
    provider_name: str | None
    semantic_type_name: str | None


@strawberry.type
class ResolverType:
    id: uuid.UUID
    resolver_type: str
    display_name: str
    description: str | None
    input_schema: strawberry.scalars.JSON | None
    output_schema: strawberry.scalars.JSON | None
    handler_class: str
    is_system: bool
    instance_config_schema: strawberry.scalars.JSON | None
    code: str | None
    category: str | None
    supports_release: bool
    supports_update: bool
    compatible_provider_ids: list[uuid.UUID]


@strawberry.type
class ResolverConfigurationType:
    id: uuid.UUID
    resolver_id: uuid.UUID
    resolver_type: str
    landing_zone_id: uuid.UUID | None
    environment_id: uuid.UUID | None
    config: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime


# ── Input Types ────────────────────────────────────────────────────────

@strawberry.input
class ComponentCreateInput:
    name: str
    display_name: str
    provider_id: uuid.UUID
    semantic_type_id: uuid.UUID
    language: ComponentLanguageGQL
    description: str | None = None
    code: str = ""
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    resolver_bindings: strawberry.scalars.JSON | None = None


@strawberry.input
class ComponentUpdateInput:
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    code: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    resolver_bindings: strawberry.scalars.JSON | None = None
    language: ComponentLanguageGQL | None = None


@strawberry.input
class ComponentPublishInput:
    changelog: str | None = None


@strawberry.input
class ResolverConfigurationInput:
    resolver_id: uuid.UUID
    config: strawberry.scalars.JSON
    landing_zone_id: uuid.UUID | None = None
    environment_id: uuid.UUID | None = None


@strawberry.input
class GovernanceInput:
    component_id: uuid.UUID
    tenant_id: uuid.UUID
    is_allowed: bool = True
    parameter_constraints: strawberry.scalars.JSON | None = None
    max_instances: int | None = None


@strawberry.input
class ComponentOperationCreateInput:
    name: str
    display_name: str
    workflow_definition_id: uuid.UUID
    description: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    is_destructive: bool = False
    requires_approval: bool = False
    estimated_downtime: EstimatedDowntimeGQL = EstimatedDowntimeGQL.NONE
    sort_order: int = 0


@strawberry.input
class ResolverDefinitionCreateInput:
    resolver_type: str
    display_name: str
    handler_class: str
    description: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    instance_config_schema: strawberry.scalars.JSON | None = None
    code: str | None = None
    category: str | None = None
    supports_release: bool = False
    supports_update: bool = False
    compatible_provider_ids: list[uuid.UUID] | None = None


@strawberry.input
class ResolverDefinitionUpdateInput:
    display_name: str | None = None
    description: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    instance_config_schema: strawberry.scalars.JSON | None = None
    code: str | None = None
    category: str | None = None
    supports_release: bool | None = None
    supports_update: bool | None = None
    compatible_provider_ids: list[uuid.UUID] | None = None


@strawberry.input
class ComponentOperationUpdateInput:
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    workflow_definition_id: uuid.UUID | None = None
    is_destructive: bool | None = None
    requires_approval: bool | None = None
    estimated_downtime: EstimatedDowntimeGQL | None = None
    sort_order: int | None = None
