"""
Overview: Strawberry GraphQL types for deployments.
Architecture: GraphQL type definitions for deployments (Section 7.2)
Dependencies: strawberry
Concepts: Deployment types, status enum, input types
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ──────────────────────────────────────────────────────────────

@strawberry.enum
class DeploymentStatusGQL(Enum):
    PLANNED = "PLANNED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


# ── Types ──────────────────────────────────────────────────────────────

@strawberry.enum
class ResolutionStatusGQL(Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


@strawberry.type
class DeploymentCIType:
    id: uuid.UUID
    deployment_id: uuid.UUID
    ci_id: uuid.UUID
    component_id: uuid.UUID
    topology_node_id: str | None
    resolver_outputs: strawberry.scalars.JSON | None
    created_at: datetime


@strawberry.type
class DeploymentType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    topology_id: uuid.UUID
    name: str
    description: str | None
    status: DeploymentStatusGQL
    parameters: strawberry.scalars.JSON | None
    resolved_parameters: strawberry.scalars.JSON | None
    resolution_status: str | None
    resolution_error: str | None
    deployed_by: uuid.UUID
    deployed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    cis: list[DeploymentCIType]


@strawberry.type
class ResolvedParameterInfo:
    key: str
    value: strawberry.scalars.JSON | None
    source: str  # "resolver:ipam", "resolver:naming", "default", "user"


@strawberry.type
class ResolvedParametersPreview:
    parameters: strawberry.scalars.JSON
    details: list[ResolvedParameterInfo]


@strawberry.input
class ResolveParametersInput:
    component_id: uuid.UUID
    environment_id: uuid.UUID | None = None
    landing_zone_id: uuid.UUID | None = None
    user_params: strawberry.scalars.JSON | None = None


# ── Input Types ────────────────────────────────────────────────────────

@strawberry.input
class DeploymentCreateInput:
    environment_id: uuid.UUID
    topology_id: uuid.UUID
    name: str
    description: str | None = None
    parameters: strawberry.scalars.JSON | None = None


@strawberry.input
class DeploymentUpdateInput:
    name: str | None = None
    description: str | None = None
    status: DeploymentStatusGQL | None = None
    parameters: strawberry.scalars.JSON | None = None
