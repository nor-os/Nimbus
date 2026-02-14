"""
Overview: GraphQL types for tenant tags — output types and input types.
Architecture: GraphQL type definitions for tag operations (Section 3.2)
Dependencies: strawberry
Concepts: Tenant tags provide typed configuration per tenant with JSON Schema validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class TenantTagType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    key: str
    display_name: str
    description: str | None
    value_schema: JSON | None
    value: JSON | None
    is_secret: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantTagListType:
    items: list[TenantTagType]
    total: int


@strawberry.input
class TenantTagCreateInput:
    key: str
    display_name: str | None = None
    description: str | None = None
    value_schema: JSON | None = None
    value: JSON | None = None
    is_secret: bool = False
    sort_order: int = 0


@strawberry.input
class TenantTagUpdateInput:
    display_name: str | None = None
    description: str | None = strawberry.UNSET
    value_schema: JSON | None = strawberry.UNSET
    value: JSON | None = strawberry.UNSET
    is_secret: bool | None = None
    sort_order: int | None = None
