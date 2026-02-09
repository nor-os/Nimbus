"""
Overview: Pydantic schemas for semantic layer API — request/response validation.
Architecture: API schema definitions for semantic type catalog (Section 5)
Dependencies: pydantic, uuid, datetime, enum
Concepts: Semantic types, categories, relationship kinds, providers, provider resource types,
    type mappings
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ProviderTypeEnum(StrEnum):
    CLOUD = "cloud"
    ON_PREM = "on_prem"
    SAAS = "saas"
    CUSTOM = "custom"


class ProviderResourceTypeStatusEnum(StrEnum):
    AVAILABLE = "available"
    PREVIEW = "preview"
    DEPRECATED = "deprecated"


class SemanticCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticResourceTypeResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    is_abstract: bool
    parent_type_id: uuid.UUID | None
    properties_schema: list | None
    allowed_relationship_kinds: list | None
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticRelationshipKindResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    inverse_name: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticProviderResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    provider_type: str
    website_url: str | None
    documentation_url: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticProviderResourceTypeResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    api_type: str
    display_name: str
    description: str | None
    documentation_url: str | None
    parameter_schema: dict | None
    status: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticTypeMappingResponse(BaseModel):
    id: uuid.UUID
    provider_resource_type_id: uuid.UUID
    semantic_type_id: uuid.UUID
    parameter_mapping: dict | None
    notes: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SemanticResourceTypeListResponse(BaseModel):
    items: list[SemanticResourceTypeResponse]
    total: int


class SemanticTypeFilter(BaseModel):
    category: str | None = None
    is_abstract: bool | None = None
    search: str | None = None
