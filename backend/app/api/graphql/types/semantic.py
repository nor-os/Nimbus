"""
Overview: GraphQL types and input types for the semantic layer catalog — categories, types,
    relationships, and providers with full CRUD support.
Architecture: GraphQL type definitions for semantic layer (Section 5)
Dependencies: strawberry
Concepts: Semantic types, providers, type hierarchy, is_system protection, CRUD inputs
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


@strawberry.type
class SemanticActivityTypeType:
    id: uuid.UUID
    name: str
    display_name: str
    category: str | None
    description: str | None
    icon: str | None
    applicable_semantic_categories: JSON | None
    applicable_semantic_types: JSON | None
    default_relationship_kind_id: uuid.UUID | None
    default_relationship_kind_name: str | None
    properties_schema: JSON | None
    is_system: bool
    sort_order: int
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


@strawberry.input
class SemanticActivityTypeInput:
    name: str
    display_name: str
    category: str | None = None
    description: str | None = None
    icon: str | None = None
    applicable_semantic_categories: JSON | None = None
    applicable_semantic_types: JSON | None = None
    default_relationship_kind_id: uuid.UUID | None = None
    properties_schema: JSON | None = None
    sort_order: int = 0


@strawberry.input
class SemanticActivityTypeUpdateInput:
    display_name: str | None = None
    category: str | None = strawberry.UNSET
    description: str | None = strawberry.UNSET
    icon: str | None = strawberry.UNSET
    applicable_semantic_categories: JSON | None = strawberry.UNSET
    applicable_semantic_types: JSON | None = strawberry.UNSET
    default_relationship_kind_id: uuid.UUID | None = strawberry.UNSET
    properties_schema: JSON | None = strawberry.UNSET
    sort_order: int | None = None
