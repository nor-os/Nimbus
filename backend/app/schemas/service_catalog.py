"""
Overview: Pydantic schemas for service catalog — offerings, price lists, pricing overrides.
Architecture: Validation schemas for service catalog operations (Section 8)
Dependencies: pydantic
Concepts: Service catalog pricing, price lists with date ranges, tenant overrides, measuring units.
"""

import uuid
from datetime import date, datetime
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


class PriceListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    is_default: bool
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


class PriceListCreate(BaseModel):
    name: str
    is_default: bool = False
    effective_from: date
    effective_to: date | None = None


class PriceListItemResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class PriceListItemCreate(BaseModel):
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal
    currency: str = "EUR"
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None


class TenantPriceOverrideResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class TenantPriceOverrideCreate(BaseModel):
    service_offering_id: uuid.UUID
    delivery_region_id: uuid.UUID | None = None
    coverage_model: str | None = None
    price_per_unit: Decimal
    discount_percent: Decimal | None = None
    effective_from: date
    effective_to: date | None = None


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
