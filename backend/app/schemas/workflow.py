"""
Overview: Pydantic schemas for workflow definition and execution endpoints.
Architecture: API schema definitions for workflow editor (Section 7.1, 7.2)
Dependencies: pydantic
Concepts: Workflow definitions, executions, node executions, graph validation
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


# ── Status Enums ─────────────────────────────────────────


class WorkflowDefinitionStatusEnum(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class WorkflowExecutionStatusEnum(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowNodeExecutionStatusEnum(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


# ── Definition Schemas ───────────────────────────────────


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    graph: dict | None = None
    timeout_seconds: int = Field(3600, ge=1, le=86400)
    max_concurrent: int = Field(10, ge=1, le=100)


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    graph: dict | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=86400)
    max_concurrent: int | None = Field(None, ge=1, le=100)


class WorkflowDefinitionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    version: int
    graph: dict | None = None
    status: WorkflowDefinitionStatusEnum
    created_by: uuid.UUID
    timeout_seconds: int
    max_concurrent: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Node Execution Schemas ───────────────────────────────


class WorkflowNodeExecutionResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: str
    node_type: str
    status: WorkflowNodeExecutionStatusEnum
    input: dict | None = None
    output: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempt: int

    model_config = {"from_attributes": True}


# ── Execution Schemas ────────────────────────────────────


class WorkflowExecutionCreate(BaseModel):
    definition_id: uuid.UUID
    input: dict | None = None
    is_test: bool = False


class WorkflowExecutionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    definition_id: uuid.UUID
    definition_version: int
    temporal_workflow_id: str | None = None
    status: WorkflowExecutionStatusEnum
    input: dict | None = None
    output: dict | None = None
    error: str | None = None
    started_by: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    is_test: bool
    node_executions: list[WorkflowNodeExecutionResponse] = []

    model_config = {"from_attributes": True}


# ── Validation Schemas ───────────────────────────────────


class ValidationError(BaseModel):
    node_id: str | None = None
    message: str
    severity: str = "error"


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
