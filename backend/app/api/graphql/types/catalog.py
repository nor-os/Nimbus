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
    status: str = "draft"
    cloned_from_id: uuid.UUID | None = None
    base_fee: Decimal | None = None
    fee_period: str | None = None
    minimum_amount: Decimal | None = None
    minimum_currency: str | None = None
    minimum_period: str | None = None
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
    service_offering_id: uuid.UUID | None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    markup_percent: Decimal | None = None
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
    group_id: uuid.UUID | None
    version_major: int
    version_minor: int
    version_label: str
    status: str
    delivery_region_id: uuid.UUID | None
    parent_version_id: uuid.UUID | None
    cloned_from_price_list_id: uuid.UUID | None = None
    region_constraint_ids: list[uuid.UUID] = strawberry.field(default_factory=list)
    items: list[PriceListItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PriceListSummaryType:
    items: list[PriceListType]
    total: int


@strawberry.type
class PriceListOverlayItemType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    pin_id: uuid.UUID
    overlay_action: str
    base_item_id: uuid.UUID | None
    service_offering_id: uuid.UUID | None = None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal | None = None
    currency: str | None = None
    markup_percent: Decimal | None = None
    discount_percent: Decimal | None = None
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PinMinimumChargeType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    pin_id: uuid.UUID
    category: str | None
    minimum_amount: Decimal
    currency: str
    period: str
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
    source_type: str | None = None
    markup_percent: Decimal | None = None
    price_list_id: str | None = None


@strawberry.type
class TenantPriceListPinType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    price_list_id: uuid.UUID
    price_list: PriceListType | None
    overlay_items: list[PriceListOverlayItemType] = strawberry.field(default_factory=list)
    minimum_charges: list[PinMinimumChargeType] = strawberry.field(default_factory=list)
    effective_from: date
    effective_to: date
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantPriceListAssignmentType:
    tenant_id: uuid.UUID
    assignment_type: str
    price_list_id: uuid.UUID
    clone_price_list_id: uuid.UUID | None
    additions: int
    deletions: int
    is_customized: bool


@strawberry.type
class PriceListDiffItemType:
    id: uuid.UUID
    price_list_id: uuid.UUID
    service_offering_id: uuid.UUID | None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal
    markup_percent: Decimal | None = None
    currency: str
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PriceListDiffType:
    source_price_list_id: uuid.UUID
    clone_price_list_id: uuid.UUID
    additions: list[PriceListDiffItemType]
    deletions: list[PriceListDiffItemType]
    common: list[PriceListDiffItemType]


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
    relationship_type_id: uuid.UUID | None
    relationship_type_name: str | None
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
    minimum_amount: Decimal | None = None
    minimum_currency: str | None = None
    minimum_period: str | None = None


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
    minimum_amount: Decimal | None = strawberry.UNSET
    minimum_currency: str | None = strawberry.UNSET
    minimum_period: str | None = strawberry.UNSET


@strawberry.input
class PriceListCreateInput:
    name: str
    is_default: bool = False
    client_tenant_id: uuid.UUID | None = None
    delivery_region_id: uuid.UUID | None = None


@strawberry.input
class PriceListVersionInput:
    price_list_id: uuid.UUID
    bump: str = "minor"


@strawberry.input
class PriceListItemCreateInput:
    service_offering_id: uuid.UUID | None = None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    markup_percent: Decimal | None = None
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
class PriceListOverlayItemCreateInput:
    overlay_action: str
    base_item_id: uuid.UUID | None = None
    service_offering_id: uuid.UUID | None = None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal | None = None
    currency: str | None = None
    markup_percent: Decimal | None = None
    discount_percent: Decimal | None = None
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


@strawberry.input
class PriceListOverlayItemUpdateInput:
    price_per_unit: Decimal | None = None
    currency: str | None = None
    markup_percent: Decimal | None = strawberry.UNSET
    discount_percent: Decimal | None = strawberry.UNSET
    min_quantity: Decimal | None = strawberry.UNSET
    max_quantity: Decimal | None = strawberry.UNSET
    coverage_model: str | None = strawberry.UNSET
    delivery_region_id: uuid.UUID | None = strawberry.UNSET


@strawberry.input
class PinMinimumChargeCreateInput:
    category: str | None = None
    minimum_amount: Decimal
    currency: str = "EUR"
    period: str = "monthly"
    effective_from: date
    effective_to: date | None = None


@strawberry.input
class PinMinimumChargeUpdateInput:
    minimum_amount: Decimal | None = None
    currency: str | None = None
    period: str | None = None
    effective_from: date | None = None
    effective_to: date | None = strawberry.UNSET


@strawberry.input
class CIClassActivityAssociationCreateInput:
    ci_class_id: uuid.UUID
    activity_template_id: uuid.UUID
    relationship_type: str | None = None
    relationship_type_id: uuid.UUID | None = None
