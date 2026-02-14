"""
Overview: Pydantic schemas for policy library CRUD and compartment policy references.
Architecture: Validation schemas for policy API (Section 5)
Dependencies: pydantic
Concepts: Policy statements, variable definitions, compartment policy attachment, validation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyStatementSchema(BaseModel):
    sid: str = Field(min_length=1, max_length=100)
    effect: Literal["allow", "deny"]
    actions: list[str] = Field(min_length=1)
    resources: list[str] = Field(min_length=1)
    principals: list[str] = Field(default=["*"])
    condition: str | None = None


class PolicyVariableSchema(BaseModel):
    type: str = Field(description="string, integer, float, boolean, array")
    default: Any | None = None
    description: str | None = None


class PolicyLibraryCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str
    statements: list[PolicyStatementSchema] = Field(min_length=1)
    variables: dict[str, PolicyVariableSchema] | None = None
    severity: str = "MEDIUM"
    tags: list[str] | None = None


class PolicyLibraryUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    statements: list[PolicyStatementSchema] | None = None
    variables: dict[str, PolicyVariableSchema] | None = None
    severity: str | None = None
    tags: list[str] | None = None


class PolicyLibraryResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    name: str
    display_name: str
    description: str | None
    category: str
    statements: list[dict]
    variables: dict | None
    severity: str
    is_system: bool
    tags: list[str] | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class CompartmentPolicyRefSchema(BaseModel):
    policyId: str | None = None
    inline: dict | None = None
    inherit: bool = True
    variableOverrides: dict[str, Any] | None = None
