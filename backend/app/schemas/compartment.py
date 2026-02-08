"""
Overview: Pydantic schemas for compartment CRUD and tree responses.
Architecture: API schema definitions for compartment endpoints (Section 7.1, 7.2)
Dependencies: pydantic
Concepts: Compartments, resource organization, tree hierarchy
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CompartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    description: str | None = None


class CompartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    description: str | None = None


class CompartmentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompartmentTreeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    children: list["CompartmentTreeResponse"] = []

    model_config = {"from_attributes": True}
