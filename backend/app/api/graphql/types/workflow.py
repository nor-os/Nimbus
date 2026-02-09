"""
Overview: Strawberry GraphQL types for workflow definitions, executions, and node types.
Architecture: GraphQL type definitions for workflow editor (Section 7.2)
Dependencies: strawberry
Concepts: Workflow types, execution types, node type info, validation results
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ────────────────────────────────────────────────


@strawberry.enum
class WorkflowDefinitionStatusGQL(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@strawberry.enum
class WorkflowExecutionStatusGQL(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class WorkflowNodeExecutionStatusGQL(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


# ── Output Types ─────────────────────────────────────────


@strawberry.type
class WorkflowDefinitionType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    version: int
    graph: strawberry.scalars.JSON | None
    status: WorkflowDefinitionStatusGQL
    created_by: uuid.UUID
    timeout_seconds: int
    max_concurrent: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class WorkflowNodeExecutionType:
    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: str
    node_type: str
    status: WorkflowNodeExecutionStatusGQL
    input: strawberry.scalars.JSON | None
    output: strawberry.scalars.JSON | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    attempt: int


@strawberry.type
class WorkflowExecutionType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    definition_id: uuid.UUID
    definition_version: int
    temporal_workflow_id: str | None
    status: WorkflowExecutionStatusGQL
    input: strawberry.scalars.JSON | None
    output: strawberry.scalars.JSON | None
    error: str | None
    started_by: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    is_test: bool
    node_executions: list[WorkflowNodeExecutionType]


@strawberry.type
class ValidationErrorType:
    node_id: str | None
    message: str
    severity: str


@strawberry.type
class ValidationResultType:
    valid: bool
    errors: list[ValidationErrorType]
    warnings: list[ValidationErrorType]


@strawberry.type
class PortDefType:
    name: str
    direction: str
    port_type: str
    label: str
    required: bool
    multiple: bool


@strawberry.type
class NodeTypeInfoType:
    type_id: str
    label: str
    category: str
    description: str
    icon: str
    ports: list[PortDefType]
    config_schema: strawberry.scalars.JSON
    is_marker: bool


# ── Input Types ──────────────────────────────────────────


@strawberry.input
class WorkflowDefinitionCreateInput:
    name: str
    description: str | None = None
    graph: strawberry.scalars.JSON | None = None
    timeout_seconds: int = 3600
    max_concurrent: int = 10


@strawberry.input
class WorkflowDefinitionUpdateInput:
    name: str | None = None
    description: str | None = None
    graph: strawberry.scalars.JSON | None = None
    timeout_seconds: int | None = None
    max_concurrent: int | None = None


@strawberry.input
class WorkflowExecutionStartInput:
    definition_id: uuid.UUID
    input: strawberry.scalars.JSON | None = None
    is_test: bool = False
    mock_configs: strawberry.scalars.JSON | None = None
