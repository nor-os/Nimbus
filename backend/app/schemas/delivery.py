"""
Overview: Pydantic schemas for service delivery — regions, staff, activities, estimations,
    price list templates, and profitability.
Architecture: Validation schemas for service delivery engine (Section 8)
Dependencies: pydantic
Concepts: Delivery regions, region acceptance, staff profiles, rate cards, activity templates,
    service estimations, profitability analysis.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


# ── Delivery Regions ─────────────────────────────────────────────────


class DeliveryRegionResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class DeliveryRegionCreate(BaseModel):
    parent_region_id: uuid.UUID | None = None
    name: str
    display_name: str
    code: str
    timezone: str | None = None
    country_code: str | None = None
    is_system: bool = False
    sort_order: int = 0


class DeliveryRegionUpdate(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    country_code: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


# ── Region Acceptance ────────────────────────────────────────────────


class RegionAcceptanceTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class RegionAcceptanceTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    is_system: bool = False


class RegionAcceptanceTemplateRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    template_id: uuid.UUID
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None
    created_at: datetime
    updated_at: datetime


class RegionAcceptanceTemplateRuleCreate(BaseModel):
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None = None


class TenantRegionAcceptanceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None
    is_compliance_enforced: bool
    created_at: datetime
    updated_at: datetime


class TenantRegionAcceptanceCreate(BaseModel):
    delivery_region_id: uuid.UUID
    acceptance_type: str
    reason: str | None = None
    is_compliance_enforced: bool = False


class TenantRegionTemplateAssignmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Organizational Units ─────────────────────────────────────────────


class OrganizationalUnitResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class OrganizationalUnitCreate(BaseModel):
    parent_id: uuid.UUID | None = None
    name: str
    display_name: str
    cost_center: str | None = None
    sort_order: int = 0


class OrganizationalUnitUpdate(BaseModel):
    display_name: str | None = None
    cost_center: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


# ── Staff Profiles & Rate Cards ──────────────────────────────────────


class StaffProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class StaffProfileCreate(BaseModel):
    name: str
    display_name: str
    org_unit_id: uuid.UUID | None = None
    profile_id: str | None = None
    cost_center: str | None = None
    default_hourly_cost: Decimal | None = None
    default_currency: str | None = None
    is_system: bool = False
    sort_order: int = 0


class StaffProfileUpdate(BaseModel):
    display_name: str | None = None
    org_unit_id: uuid.UUID | None = None
    profile_id: str | None = None
    cost_center: str | None = None
    default_hourly_cost: Decimal | None = None
    default_currency: str | None = None
    sort_order: int | None = None


class InternalRateCardResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class InternalRateCardCreate(BaseModel):
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    hourly_cost: Decimal
    hourly_sell_rate: Decimal | None = None
    currency: str = "EUR"
    effective_from: date
    effective_to: date | None = None


class InternalRateCardUpdate(BaseModel):
    hourly_cost: Decimal | None = None
    hourly_sell_rate: Decimal | None = None
    currency: str | None = None
    effective_to: date | None = None


# ── Activity Templates & Definitions ────────────────────────────────


class ActivityTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ActivityTemplateCreate(BaseModel):
    name: str
    description: str | None = None


class ActivityTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ActivityDefinitionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    template_id: uuid.UUID
    name: str
    staff_profile_id: uuid.UUID
    estimated_hours: Decimal
    sort_order: int
    is_optional: bool
    created_at: datetime
    updated_at: datetime


class ActivityDefinitionCreate(BaseModel):
    name: str
    staff_profile_id: uuid.UUID
    estimated_hours: Decimal
    sort_order: int = 0
    is_optional: bool = False


class ActivityDefinitionUpdate(BaseModel):
    name: str | None = None
    staff_profile_id: uuid.UUID | None = None
    estimated_hours: Decimal | None = None
    sort_order: int | None = None
    is_optional: bool | None = None


class ServiceProcessResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    version: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ServiceProcessCreate(BaseModel):
    name: str
    description: str | None = None
    sort_order: int = 0


class ServiceProcessUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class ProcessActivityLinkResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    process_id: uuid.UUID
    activity_template_id: uuid.UUID
    sort_order: int
    is_required: bool
    created_at: datetime
    updated_at: datetime


class ProcessActivityLinkCreate(BaseModel):
    activity_template_id: uuid.UUID
    sort_order: int = 0
    is_required: bool = True


class ServiceProcessAssignmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    process_id: uuid.UUID
    coverage_model: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ServiceProcessAssignmentCreate(BaseModel):
    service_offering_id: uuid.UUID
    process_id: uuid.UUID
    coverage_model: str | None = None
    is_default: bool = False


# ── Service Estimations ──────────────────────────────────────────────


class ServiceEstimationResponse(BaseModel):
    model_config = {"from_attributes": True}

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
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ServiceEstimationCreate(BaseModel):
    client_tenant_id: uuid.UUID
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    quantity: Decimal = Decimal("1")
    sell_price_per_unit: Decimal = Decimal("0")
    sell_currency: str = "EUR"


class ServiceEstimationUpdate(BaseModel):
    quantity: Decimal | None = None
    sell_price_per_unit: Decimal | None = None
    sell_currency: str | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None


class EstimationLineItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    estimation_id: uuid.UUID
    activity_definition_id: uuid.UUID | None
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


class EstimationLineItemCreate(BaseModel):
    name: str
    staff_profile_id: uuid.UUID
    delivery_region_id: uuid.UUID
    estimated_hours: Decimal
    hourly_rate: Decimal
    rate_currency: str = "EUR"
    sort_order: int = 0
    activity_definition_id: uuid.UUID | None = None


class EstimationLineItemUpdate(BaseModel):
    name: str | None = None
    estimated_hours: Decimal | None = None
    hourly_rate: Decimal | None = None
    sort_order: int | None = None


# ── Price List Templates ─────────────────────────────────────────────


class PriceListTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    region_acceptance_template_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class PriceListTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    region_acceptance_template_id: uuid.UUID | None = None
    status: str = "draft"


class PriceListTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class PriceListTemplateItemResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class PriceListTemplateItemCreate(BaseModel):
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal
    currency: str = "EUR"
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


# ── Profitability ────────────────────────────────────────────────────


class ProfitabilitySummary(BaseModel):
    total_revenue: Decimal
    total_cost: Decimal
    total_margin: Decimal
    margin_percent: Decimal


class ProfitabilityByEntity(BaseModel):
    entity_id: uuid.UUID
    entity_name: str
    total_revenue: Decimal
    total_cost: Decimal
    margin_amount: Decimal
    margin_percent: Decimal
    estimation_count: int
