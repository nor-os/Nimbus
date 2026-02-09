"""
Overview: GraphQL types and input types for the semantic layer catalog — categories, types,
    relationships, providers, provider resource types, and type mappings with full CRUD support.
Architecture: GraphQL type definitions for semantic layer (Section 5)
Dependencies: strawberry
Concepts: Semantic types, providers, provider resource types, type mappings, type hierarchy,
    is_system protection, CRUD inputs
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class ProviderTypeGQL(Enum):
    CLOUD = "cloud"
    ON_PREM = "on_prem"
    SAAS = "saas"
    CUSTOM = "custom"


@strawberry.enum
class ProviderResourceTypeStatusGQL(Enum):
    AVAILABLE = "available"
    PREVIEW = "preview"
    DEPRECATED = "deprecated"


# -- Output types -------------------------------------------------------


@strawberry.type
class SemanticCategoryType:
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticProviderType:
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    provider_type: ProviderTypeGQL
    website_url: str | None
    documentation_url: str | None
    is_system: bool
    resource_type_count: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticProviderResourceTypeType:
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    api_type: str
    display_name: str
    description: str | None
    documentation_url: str | None
    parameter_schema: JSON | None
    status: ProviderResourceTypeStatusGQL
    is_system: bool
    semantic_type_name: str | None
    semantic_type_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticTypeMappingType:
    id: uuid.UUID
    provider_resource_type_id: uuid.UUID
    semantic_type_id: uuid.UUID
    provider_name: str
    provider_api_type: str
    provider_display_name: str
    semantic_type_name: str
    semantic_type_display_name: str
    parameter_mapping: JSON | None
    notes: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticResourceTypeType:
    id: uuid.UUID
    name: str
    display_name: str
    category: SemanticCategoryType
    description: str | None
    icon: str | None
    is_abstract: bool
    parent_type_name: str | None
    properties_schema: JSON | None
    allowed_relationship_kinds: JSON | None
    sort_order: int
    is_system: bool
    mappings: list[SemanticTypeMappingType]
    children: list["SemanticResourceTypeType"]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticResourceTypeListType:
    items: list[SemanticResourceTypeType]
    total: int


@strawberry.type
class SemanticCategoryWithTypesType:
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    sort_order: int
    is_system: bool
    types: list[SemanticResourceTypeType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SemanticRelationshipKindType:
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    inverse_name: str
    is_system: bool
    created_at: datetime
    updated_at: datetime


# -- Input types --------------------------------------------------------


@strawberry.input
class SemanticCategoryInput:
    name: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    sort_order: int = 0


@strawberry.input
class SemanticCategoryUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    sort_order: int | None = None


@strawberry.input
class SemanticResourceTypeInput:
    name: str
    display_name: str
    category_id: uuid.UUID
    description: str | None = None
    icon: str | None = None
    is_abstract: bool = False
    parent_type_id: uuid.UUID | None = None
    properties_schema: JSON | None = None
    allowed_relationship_kinds: JSON | None = None
    sort_order: int = 0


@strawberry.input
class SemanticResourceTypeUpdateInput:
    display_name: str | None = None
    category_id: uuid.UUID | None = None
    description: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    is_abstract: bool | None = None
    parent_type_id: uuid.UUID | None = strawberry.UNSET
    properties_schema: JSON | None = strawberry.UNSET
    allowed_relationship_kinds: JSON | None = strawberry.UNSET
    sort_order: int | None = None


@strawberry.input
class SemanticProviderInput:
    name: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    provider_type: ProviderTypeGQL = ProviderTypeGQL.CUSTOM
    website_url: str | None = None
    documentation_url: str | None = None


@strawberry.input
class SemanticProviderUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    provider_type: ProviderTypeGQL | None = None
    website_url: str | None = strawberry.UNSET
    documentation_url: str | None = strawberry.UNSET


@strawberry.input
class SemanticProviderResourceTypeInput:
    provider_id: uuid.UUID
    api_type: str
    display_name: str
    description: str | None = None
    documentation_url: str | None = None
    parameter_schema: JSON | None = None
    status: ProviderResourceTypeStatusGQL = ProviderResourceTypeStatusGQL.AVAILABLE


@strawberry.input
class SemanticProviderResourceTypeUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    documentation_url: str | None = strawberry.UNSET
    parameter_schema: JSON | None = strawberry.UNSET
    status: ProviderResourceTypeStatusGQL | None = None


@strawberry.input
class SemanticTypeMappingInput:
    provider_resource_type_id: uuid.UUID
    semantic_type_id: uuid.UUID
    parameter_mapping: JSON | None = None
    notes: str | None = None


@strawberry.input
class SemanticTypeMappingUpdateInput:
    parameter_mapping: JSON | None = strawberry.UNSET
    notes: str | None = strawberry.UNSET


@strawberry.input
class SemanticRelationshipKindInput:
    name: str
    display_name: str
    description: str | None = None
    inverse_name: str


@strawberry.input
class SemanticRelationshipKindUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    inverse_name: str | None = None
