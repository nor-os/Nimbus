"""
Overview: Strawberry GraphQL types for tenants, settings, quotas, stats, compartments.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: Multi-tenancy, GraphQL schema, tenant hierarchy
"""

import uuid
from datetime import datetime

import strawberry


@strawberry.type
class TenantType:
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    provider_id: uuid.UUID
    contact_email: str | None
    is_root: bool
    level: int
    description: str | None
    invoice_currency: str | None
    primary_region_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantSettingType:
    id: uuid.UUID
    key: str
    value: str
    value_type: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantQuotaType:
    id: uuid.UUID
    quota_type: str
    limit_value: int
    current_usage: int
    enforcement: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantStatsType:
    tenant_id: uuid.UUID
    name: str
    total_users: int
    total_compartments: int
    total_children: int
    quotas: list[TenantQuotaType]


@strawberry.type
class TenantHierarchyType:
    id: uuid.UUID
    name: str
    level: int
    is_root: bool
    children: list["TenantHierarchyType"]


@strawberry.type
class CompartmentType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CompartmentTreeType:
    id: uuid.UUID
    name: str
    description: str | None
    children: list["CompartmentTreeType"]


@strawberry.input
class TenantCreateInput:
    name: str
    parent_id: uuid.UUID | None = None
    contact_email: str | None = None
    description: str | None = None


@strawberry.input
class TenantUpdateInput:
    name: str | None = None
    contact_email: str | None = None
    description: str | None = None
    invoice_currency: str | None = strawberry.UNSET
    primary_region_id: uuid.UUID | None = strawberry.UNSET


@strawberry.input
class TenantSettingInput:
    key: str
    value: str
    value_type: str = "string"


@strawberry.input
class QuotaUpdateInput:
    limit_value: int | None = None
    enforcement: str | None = None


@strawberry.input
class CompartmentCreateInput:
    name: str
    parent_id: uuid.UUID | None = None
    description: str | None = None


@strawberry.input
class CompartmentUpdateInput:
    name: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None
