"""
Overview: Strawberry GraphQL types for architecture topologies.
Architecture: GraphQL type definitions for architecture planner (Section 7.2)
Dependencies: strawberry
Concepts: Topology types, validation results, input types, export format
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


@strawberry.enum
class TopologyStatusGQL(Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


@strawberry.type
class ArchitectureTopologyType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    graph: strawberry.scalars.JSON | None
    status: TopologyStatusGQL
    version: int
    is_template: bool
    is_system: bool
    tags: list[str] | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TopologyValidationErrorType:
    node_id: str | None
    message: str
    severity: str


@strawberry.type
class TopologyValidationResultType:
    valid: bool
    errors: list[TopologyValidationErrorType]
    warnings: list[TopologyValidationErrorType]


@strawberry.type
class TopologyExportType:
    data: strawberry.scalars.JSON
    format: str


@strawberry.input
class TopologyCreateInput:
    name: str
    description: str | None = None
    graph: strawberry.scalars.JSON | None = None
    tags: list[str] | None = None
    is_template: bool = False


@strawberry.input
class TopologyUpdateInput:
    name: str | None = None
    description: str | None = None
    graph: strawberry.scalars.JSON | None = None
    tags: list[str] | None = None


@strawberry.input
class TopologyImportInput:
    name: str
    description: str | None = None
    graph: strawberry.scalars.JSON | None = None
    tags: list[str] | None = None
    is_template: bool = False


# ── Resolution Types ────────────────────────────────────────────────

@strawberry.type
class ResolvedParameterType:
    name: str
    display_name: str
    value: strawberry.scalars.JSON | None
    source: str
    is_required: bool
    tag_key: str | None


@strawberry.type
class StackResolutionType:
    stack_id: str
    stack_label: str
    blueprint_id: str
    parameters: list[ResolvedParameterType]
    is_complete: bool
    unresolved_count: int


@strawberry.type
class ResolutionPreviewType:
    topology_id: str
    stacks: list[StackResolutionType]
    deployment_order: list[list[str]]
    all_complete: bool
    total_unresolved: int


@strawberry.type
class DeploymentOrderType:
    groups: list[list[str]]
