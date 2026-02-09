"""
Overview: GraphQL types and input types for the service catalog — offerings, pricing, overrides,
    CI class activity associations.
Architecture: GraphQL type definitions for service catalog operations (Section 8)
Dependencies: strawberry
Concepts: Service catalog types for pricing display and management.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

import strawberry

# ── Output types ──────────────────────────────────────────────────────


@strawberry.type
class ServiceOfferingType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    measuring_unit: str
    service_type: str
    operating_model: str | None
    default_coverage_model: str | None
    ci_class_ids: list[uuid.UUID] = strawberry.field(default_factory=list)
    is_active: bool
    region_ids: list[uuid.UUID] = strawberry.field(default_factory=list)
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceOfferingListType:
    items: list[ServiceOfferingType]
    total: int


@strawberry.type
class PriceListItemType:
    id: uuid.UUID
    price_list_id: uuid.UUID
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None
    coverage_model: str | None
    price_per_unit: Decimal
    currency: str
    min_quantity: Decimal | None
    max_quantity: Decimal | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PriceListType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    is_default: bool
    effective_from: date
    effective_to: date | None
    items: list[PriceListItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PriceListSummaryType:
    items: list[PriceListType]
    total: int


@strawberry.type
class TenantPriceOverrideType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None
    coverage_model: str | None
    price_per_unit: Decimal
    discount_percent: Decimal | None
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EffectivePriceType:
    service_offering_id: str
    service_name: str
    price_per_unit: Decimal
    currency: str
    measuring_unit: str
    has_override: bool
    discount_percent: Decimal | None
    delivery_region_id: str | None
    coverage_model: str | None
    compliance_status: str | None


@strawberry.type
class CIClassActivityAssociationType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    ci_class_id: uuid.UUID
    ci_class_name: str
    ci_class_display_name: str
    activity_template_id: uuid.UUID
    activity_template_name: str
    relationship_type: str | None
    created_at: datetime
    updated_at: datetime


# ── Input types ───────────────────────────────────────────────────────


@strawberry.input
class ServiceOfferingCreateInput:
    name: str
    description: str | None = None
    category: str | None = None
    measuring_unit: str = "month"
    service_type: str = "resource"
    operating_model: str | None = None
    default_coverage_model: str | None = None
    ci_class_ids: list[uuid.UUID] | None = None


@strawberry.input
class ServiceOfferingUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    category: str | None = strawberry.UNSET
    measuring_unit: str | None = None
    service_type: str | None = None
    operating_model: str | None = strawberry.UNSET
    default_coverage_model: str | None = strawberry.UNSET
    ci_class_ids: list[uuid.UUID] | None = strawberry.UNSET
    is_active: bool | None = None


@strawberry.input
class PriceListCreateInput:
    name: str
    is_default: bool = False
    effective_from: date
    effective_to: date | None = None
    client_tenant_id: uuid.UUID | None = None


@strawberry.input
class PriceListItemCreateInput:
    service_offering_id: uuid.UUID
    price_per_unit: Decimal
    currency: str = "EUR"
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


@strawberry.input
class PriceListItemUpdateInput:
    price_per_unit: Decimal | None = None
    currency: str | None = None
    min_quantity: Decimal | None = strawberry.UNSET
    max_quantity: Decimal | None = strawberry.UNSET


@strawberry.input
class TenantPriceOverrideCreateInput:
    service_offering_id: uuid.UUID
    price_per_unit: Decimal
    discount_percent: Decimal | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    effective_from: date
    effective_to: date | None = None


@strawberry.input
class CIClassActivityAssociationCreateInput:
    ci_class_id: uuid.UUID
    activity_template_id: uuid.UUID
    relationship_type: str | None = None
