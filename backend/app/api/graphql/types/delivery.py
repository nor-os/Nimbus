"""
Overview: GraphQL types and input types for the service delivery engine — regions, acceptance,
    staff profiles, rate cards, activities, estimations, price list templates, profitability.
Architecture: GraphQL type definitions for service delivery operations (Section 8)
Dependencies: strawberry
Concepts: Service delivery types covering the full delivery lifecycle from region management
    through estimation and profitability analysis.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

import strawberry


# ── Delivery Regions ─────────────────────────────────────────────────


@strawberry.type
class DeliveryRegionType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    parent_region_id: uuid.UUID | None
    name: str
    display_name: str
    code: str
    timezone: str | None
    country_code: str | None
    is_system: bool
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class DeliveryRegionListType:
    items: list[DeliveryRegionType]
    total: int


@strawberry.input
class DeliveryRegionCreateInput:
    name: str
    display_name: str
    code: str
    parent_region_id: uuid.UUID | None = None
    timezone: str | None = None
    country_code: str | None = None
    is_system: bool = False
    sort_order: int = 0


@strawberry.input
class DeliveryRegionUpdateInput:
    display_name: str | None = None
    timezone: str | None = strawberry.UNSET
    country_code: str | None = strawberry.UNSET
    is_active: bool | None = None
    sort_order: int | None = None


# ── Region Acceptance ────────────────────────────────────────────────


@strawberry.type
class RegionAcceptanceTemplateType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class RegionAcceptanceTemplateRuleType:
    id: uuid.UUID
    template_id: uuid.UUID
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantRegionAcceptanceType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None
    is_compliance_enforced: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EffectiveRegionAcceptanceType:
    acceptance_type: str
    reason: str | None
    is_compliance_enforced: bool
    source: str


@strawberry.input
class RegionAcceptanceTemplateCreateInput:
    name: str
    description: str | None = None
    is_system: bool = False


@strawberry.input
class RegionAcceptanceTemplateRuleCreateInput:
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None = None


@strawberry.input
class TenantRegionAcceptanceCreateInput:
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None = None
    is_compliance_enforced: bool = False


# ── Organizational Units ─────────────────────────────────────────────


@strawberry.type
class OrganizationalUnitType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    name: str
    display_name: str
    cost_center: str | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.input
class OrganizationalUnitCreateInput:
    name: str
    display_name: str
    parent_id: uuid.UUID | None = None
    cost_center: str | None = None
    sort_order: int = 0


@strawberry.input
class OrganizationalUnitUpdateInput:
    display_name: str | None = None
    cost_center: str | None = strawberry.UNSET
    is_active: bool | None = None
    sort_order: int | None = None


# ── Staff Profiles ───────────────────────────────────────────────────


@strawberry.type
class StaffProfileType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    org_unit_id: uuid.UUID | None
    name: str
    display_name: str
    profile_id: str | None
    cost_center: str | None
    default_hourly_cost: Decimal | None
    default_currency: str | None
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class StaffProfileListType:
    items: list[StaffProfileType]
    total: int


@strawberry.input
class StaffProfileCreateInput:
    name: str
    display_name: str
    org_unit_id: uuid.UUID | None = None
    profile_id: str | None = None
    cost_center: str | None = None
    default_hourly_cost: Decimal | None = None
    default_currency: str | None = None
    is_system: bool = False
    sort_order: int = 0


@strawberry.input
class StaffProfileUpdateInput:
    display_name: str | None = None
    org_unit_id: uuid.UUID | None = strawberry.UNSET
    profile_id: str | None = strawberry.UNSET
    cost_center: str | None = strawberry.UNSET
    default_hourly_cost: Decimal | None = strawberry.UNSET
    default_currency: str | None = strawberry.UNSET
    sort_order: int | None = None


# ── Internal Rate Cards ──────────────────────────────────────────────


@strawberry.type
class InternalRateCardType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    hourly_cost: Decimal
    hourly_sell_rate: Decimal | None
    currency: str
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class InternalRateCardCreateInput:
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    hourly_cost: Decimal
    hourly_sell_rate: Decimal | None = None
    currency: str = "EUR"
    effective_from: date
    effective_to: date | None = None


@strawberry.input
class InternalRateCardUpdateInput:
    hourly_cost: Decimal | None = None
    hourly_sell_rate: Decimal | None = strawberry.UNSET
    currency: str | None = None
    effective_from: date | None = None
    effective_to: date | None = strawberry.UNSET


# ── Activity Templates & Definitions ────────────────────────────────


@strawberry.type
class ActivityDefinitionType:
    id: uuid.UUID
    template_id: uuid.UUID
    name: str
    staff_profile_id: uuid.UUID
    estimated_hours: Decimal
    sort_order: int
    is_optional: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ActivityTemplateType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    version: int
    definitions: list[ActivityDefinitionType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ActivityTemplateListType:
    items: list[ActivityTemplateType]
    total: int


@strawberry.input
class ActivityTemplateCreateInput:
    name: str
    description: str | None = None


@strawberry.input
class ActivityDefinitionCreateInput:
    name: str
    staff_profile_id: uuid.UUID
    estimated_hours: Decimal
    sort_order: int = 0
    is_optional: bool = False


@strawberry.input
class ActivityDefinitionUpdateInput:
    name: str | None = None
    staff_profile_id: uuid.UUID | None = None
    estimated_hours: Decimal | None = None
    sort_order: int | None = None
    is_optional: bool | None = None


# ── Service Processes ────────────────────────────────────────────────


@strawberry.type
class ProcessActivityLinkType:
    id: uuid.UUID
    process_id: uuid.UUID
    activity_template_id: uuid.UUID
    sort_order: int
    is_required: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceProcessType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    version: int
    sort_order: int
    activity_links: list[ProcessActivityLinkType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceProcessListType:
    items: list[ServiceProcessType]
    total: int


@strawberry.input
class ServiceProcessCreateInput:
    name: str
    description: str | None = None
    sort_order: int = 0


@strawberry.input
class ServiceProcessUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    sort_order: int | None = None


@strawberry.input
class ProcessActivityLinkCreateInput:
    activity_template_id: uuid.UUID
    sort_order: int = 0
    is_required: bool = True


# ── Service Process Assignments ─────────────────────────────────────


@strawberry.type
class ServiceProcessAssignmentType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    process_id: uuid.UUID
    coverage_model: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


@strawberry.input
class ServiceProcessAssignmentCreateInput:
    service_offering_id: uuid.UUID
    process_id: uuid.UUID
    coverage_model: str | None = None
    is_default: bool = False


# ── Service Estimations ──────────────────────────────────────────────


@strawberry.type
class EstimationLineItemType:
    id: uuid.UUID
    estimation_id: uuid.UUID
    activity_definition_id: uuid.UUID | None
    rate_card_id: uuid.UUID | None
    name: str
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    estimated_hours: Decimal
    hourly_rate: Decimal
    rate_currency: str
    line_cost: Decimal
    actual_hours: Decimal | None
    actual_cost: Decimal | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceEstimationType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None
    coverage_model: str | None
    status: str
    quantity: Decimal
    sell_price_per_unit: Decimal
    sell_currency: str
    total_estimated_cost: Decimal | None
    total_sell_price: Decimal | None
    margin_amount: Decimal | None
    margin_percent: Decimal | None
    price_list_id: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    line_items: list[EstimationLineItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EstimationListType:
    items: list[ServiceEstimationType]
    total: int


@strawberry.input
class ServiceEstimationCreateInput:
    client_tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_list_id: uuid.UUID | None = None
    quantity: Decimal = Decimal("1")
    sell_price_per_unit: Decimal = Decimal("0")
    sell_currency: str = "EUR"


@strawberry.input
class ServiceEstimationUpdateInput:
    quantity: Decimal | None = None
    sell_price_per_unit: Decimal | None = None
    sell_currency: str | None = None
    delivery_region_id: uuid.UUID | None = strawberry.UNSET
    coverage_model: str | None = strawberry.UNSET
    price_list_id: uuid.UUID | None = strawberry.UNSET


@strawberry.input
class EstimationLineItemCreateInput:
    name: str
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    estimated_hours: Decimal
    hourly_rate: Decimal | None = None
    activity_definition_id: uuid.UUID | None = None
    rate_card_id: uuid.UUID | None = None
    rate_currency: str = "EUR"
    sort_order: int = 0


# ── Price List Templates ─────────────────────────────────────────────


@strawberry.type
class PriceListTemplateItemType:
    id: uuid.UUID
    template_id: uuid.UUID
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
class PriceListTemplateType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    region_acceptance_template_id: uuid.UUID | None
    status: str
    items: list[PriceListTemplateItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PriceListTemplateListType:
    items: list[PriceListTemplateType]
    total: int


@strawberry.input
class PriceListTemplateCreateInput:
    name: str
    description: str | None = None
    region_acceptance_template_id: uuid.UUID | None = None
    status: str = "draft"


@strawberry.input
class PriceListTemplateItemCreateInput:
    service_offering_id: uuid.UUID
    price_per_unit: Decimal
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    currency: str = "EUR"
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


# ── Profitability ────────────────────────────────────────────────────


@strawberry.type
class ProfitabilityOverviewType:
    total_revenue: Decimal
    total_cost: Decimal
    total_margin: Decimal
    margin_percent: Decimal
    estimation_count: int


@strawberry.type
class ProfitabilityByEntityType:
    entity_id: str
    entity_name: str
    total_revenue: Decimal
    total_cost: Decimal
    margin_amount: Decimal
    margin_percent: Decimal
    estimation_count: int
