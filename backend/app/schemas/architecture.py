"""
Overview: Pydantic schemas for architecture topology operations.
Architecture: Schema definitions for topology validation and serialization (Section 5)
Dependencies: pydantic
Concepts: Topology input/output schemas, graph validation, export format
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TopologyNodeSchema(BaseModel):
    id: str
    semantic_type_id: str
    label: str | None = None
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyConnectionSchema(BaseModel):
    id: str
    source: str
    target: str
    relationship_kind_id: str
    label: str | None = None


class TopologyGraphSchema(BaseModel):
    nodes: list[TopologyNodeSchema] = Field(default_factory=list)
    connections: list[TopologyConnectionSchema] = Field(default_factory=list)


class TopologyCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    graph: dict[str, Any] | None = None
    tags: list[str] | None = None
    is_template: bool = False


class TopologyUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    graph: dict[str, Any] | None = None
    tags: list[str] | None = None


class TopologyExportSchema(BaseModel):
    name: str
    description: str | None
    graph: dict[str, Any] | None
    tags: list[str] | None
    version: int
    is_template: bool


class TopologyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    graph: dict[str, Any] | None
    status: str
    version: int
    is_template: bool
    is_system: bool
    tags: list[str] | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
