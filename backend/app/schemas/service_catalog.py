"""
Overview: Pydantic schemas for service catalog — offerings, price lists, pricing overrides,
    service catalogs, provider SKUs, service groups, and tenant minimum charges.
Architecture: Validation schemas for service catalog operations (Section 8)
Dependencies: pydantic
Concepts: Service catalog pricing, versioned catalogs, provider SKUs, service groups,
    tenant minimums, price lists with date ranges, tenant overrides, measuring units.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class MeasuringUnit(StrEnum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    GB = "gb"
    REQUEST = "request"
    USER = "user"
    INSTANCE = "instance"


class ServiceType(StrEnum):
    RESOURCE = "resource"
    LABOR = "labor"


class OperatingModel(StrEnum):
    REGIONAL = "regional"
    GLOBAL = "global"
    FOLLOW_THE_SUN = "follow_the_sun"


class CoverageModel(StrEnum):
    BUSINESS_HOURS = "business_hours"
    EXTENDED = "extended"
    TWENTY_FOUR_SEVEN = "24x7"


class RegionAcceptanceType(StrEnum):
    PREFERRED = "preferred"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class EstimationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PriceListTemplateStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class OfferingStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class MinimumPeriod(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


# ── Service Offerings ────────────────────────────────────────────────


class ServiceOfferingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    measuring_unit: str
    service_type: str
    operating_model: str | None
    default_coverage_model: str | None
    ci_class_id: uuid.UUID | None
    is_active: bool
    status: str = "draft"
    cloned_from_id: uuid.UUID | None = None
    base_fee: Decimal | None = None
    fee_period: str | None = None
    minimum_amount: Decimal | None = None
    minimum_currency: str | None = None
    minimum_period: str | None = None
    created_at: datetime
    updated_at: datetime


class ServiceOfferingCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    measuring_unit: str = "month"
    service_type: str = "resource"
    operating_model: str | None = None
    default_coverage_model: str | None = None
    ci_class_id: uuid.UUID | None = None
    base_fee: Decimal | None = None
    fee_period: str | None = None
    minimum_amount: Decimal | None = None
    minimum_currency: str | None = None
    minimum_period: str | None = None


# ── Price Lists ──────────────────────────────────────────────────────


class PriceListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    is_default: bool
    group_id: uuid.UUID | None = None
    version_major: int = 1
    version_minor: int = 0
    status: str = "draft"
    delivery_region_id: uuid.UUID | None = None
    parent_version_id: uuid.UUID | None = None
    version_label: str = "v1.0"
    created_at: datetime
    updated_at: datetime


class PriceListCreate(BaseModel):
    name: str
    is_default: bool = False
    delivery_region_id: uuid.UUID | None = None


class PriceListVersionCreateInput(BaseModel):
    price_list_id: uuid.UUID
    bump: str = "minor"  # "minor" or "major"


class TenantPriceListPinResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    price_list_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TenantPriceListPinCreate(BaseModel):
    tenant_id: uuid.UUID
    price_list_id: uuid.UUID


# ── Price List Items ─────────────────────────────────────────────────


class PriceListItemResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class PriceListItemCreate(BaseModel):
    service_offering_id: uuid.UUID | None = None
    provider_sku_id: uuid.UUID | None = None
    activity_definition_id: uuid.UUID | None = None
    markup_percent: Decimal | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal
    currency: str = "EUR"
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


# ── Effective Pricing ────────────────────────────────────────────────


class EffectivePrice(BaseModel):
    service_offering_id: uuid.UUID
    service_name: str
    price_per_unit: Decimal
    currency: str
    measuring_unit: str
    has_override: bool
    discount_percent: Decimal | None = None
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    compliance_status: str | None = None
    source_type: str | None = None
    markup_percent: Decimal | None = None


# ── Service Catalogs ─────────────────────────────────────────────────


class ServiceCatalogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    group_id: uuid.UUID | None
    version_major: int
    version_minor: int
    version_label: str = "v1.0"
    status: str
    parent_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ServiceCatalogCreate(BaseModel):
    name: str
    description: str | None = None


class ServiceCatalogItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    catalog_id: uuid.UUID
    service_offering_id: uuid.UUID | None
    service_group_id: uuid.UUID | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class TenantCatalogPinResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    catalog_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Provider SKUs ────────────────────────────────────────────────────


class ProviderSkuResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    provider_id: uuid.UUID
    external_sku_id: str
    name: str
    display_name: str | None
    description: str | None
    ci_class_id: uuid.UUID | None
    measuring_unit: str
    category: str | None
    unit_cost: Decimal | None
    cost_currency: str
    attributes: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProviderSkuCreate(BaseModel):
    provider_id: uuid.UUID
    external_sku_id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    ci_class_id: uuid.UUID | None = None
    measuring_unit: str = "month"
    category: str | None = None
    unit_cost: Decimal | None = None
    cost_currency: str = "EUR"
    attributes: dict | None = None


class ProviderSkuUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    ci_class_id: uuid.UUID | None = None
    measuring_unit: str | None = None
    category: str | None = None
    unit_cost: Decimal | None = None
    cost_currency: str | None = None
    attributes: dict | None = None


class ServiceOfferingSkuResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    service_offering_id: uuid.UUID
    provider_sku_id: uuid.UUID
    default_quantity: int
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ── Service Groups ───────────────────────────────────────────────────


class ServiceGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceGroupCreate(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None


class ServiceGroupUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ServiceGroupItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    group_id: uuid.UUID
    service_offering_id: uuid.UUID
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


