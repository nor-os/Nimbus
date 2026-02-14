"""
Overview: GraphQL types for service catalogs, provider SKUs, service groups, tenant minimums,
    and offering cost breakdowns.
Architecture: GraphQL type definitions for catalog redesign (Section 8)
Dependencies: strawberry
Concepts: Versioned catalogs, provider SKUs, service groups, tenant minimum charges.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

import strawberry


# ── Service Catalogs ─────────────────────────────────────────────────


@strawberry.type
class ServiceCatalogItemType:
    id: uuid.UUID
    catalog_id: uuid.UUID
    service_offering_id: uuid.UUID | None
    service_group_id: uuid.UUID | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceCatalogType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    group_id: uuid.UUID | None
    version_major: int
    version_minor: int
    version_label: str
    status: str
    parent_version_id: uuid.UUID | None
    cloned_from_catalog_id: uuid.UUID | None
    region_constraint_ids: list[uuid.UUID] = strawberry.field(default_factory=list)
    items: list[ServiceCatalogItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceCatalogListType:
    items: list[ServiceCatalogType]
    total: int


@strawberry.type
class CatalogOverlayItemType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    pin_id: uuid.UUID
    overlay_action: str
    base_item_id: uuid.UUID | None
    service_offering_id: uuid.UUID | None = None
    service_group_id: uuid.UUID | None = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantCatalogPinType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    catalog_id: uuid.UUID
    catalog: ServiceCatalogType | None
    overlay_items: list[CatalogOverlayItemType] = strawberry.field(default_factory=list)
    effective_from: date
    effective_to: date
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TenantCatalogAssignmentType:
    tenant_id: uuid.UUID
    assignment_type: str
    catalog_id: uuid.UUID
    clone_catalog_id: uuid.UUID | None
    additions: int
    deletions: int
    is_customized: bool


@strawberry.type
class CatalogDiffItemType:
    id: uuid.UUID
    catalog_id: uuid.UUID
    service_offering_id: uuid.UUID | None
    service_group_id: uuid.UUID | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CatalogDiffType:
    source_catalog_id: uuid.UUID
    clone_catalog_id: uuid.UUID
    additions: list[CatalogDiffItemType]
    deletions: list[CatalogDiffItemType]
    common: list[CatalogDiffItemType]


# ── Provider SKUs ────────────────────────────────────────────────────


@strawberry.type
class ProviderSkuType:
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
    attributes: strawberry.scalars.JSON | None
    is_active: bool
    semantic_type_id: uuid.UUID | None
    semantic_type_name: str | None
    resource_type: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ProviderSkuListType:
    items: list[ProviderSkuType]
    total: int


@strawberry.type
class ServiceOfferingSkuType:
    id: uuid.UUID
    service_offering_id: uuid.UUID
    provider_sku_id: uuid.UUID
    default_quantity: int
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ── Service Groups ───────────────────────────────────────────────────


@strawberry.type
class ServiceGroupItemType:
    id: uuid.UUID
    group_id: uuid.UUID
    service_offering_id: uuid.UUID
    offering_name: str | None
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceGroupType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str | None
    description: str | None
    status: str
    items: list[ServiceGroupItemType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ServiceGroupListType:
    items: list[ServiceGroupType]
    total: int


# ── Offering Cost Breakdown ──────────────────────────────────────────


@strawberry.type
class OfferingCostBreakdownItemType:
    source_type: str
    source_id: str
    source_name: str
    quantity: int
    is_required: bool
    price_per_unit: Decimal
    currency: str
    measuring_unit: str
    markup_percent: Decimal | None


# ── Input types ──────────────────────────────────────────────────────


@strawberry.input
class ServiceCatalogCreateInput:
    name: str
    description: str | None = None


@strawberry.input
class ServiceCatalogVersionInput:
    catalog_id: uuid.UUID
    bump: str = "minor"


@strawberry.input
class ProviderSkuCreateInput:
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
    attributes: strawberry.scalars.JSON | None = None
    semantic_type_id: uuid.UUID | None = None
    resource_type: str | None = None


@strawberry.input
class ProviderSkuUpdateInput:
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    ci_class_id: uuid.UUID | None = strawberry.UNSET
    measuring_unit: str | None = None
    category: str | None = strawberry.UNSET
    unit_cost: Decimal | None = strawberry.UNSET
    cost_currency: str | None = None
    attributes: strawberry.scalars.JSON | None = strawberry.UNSET
    semantic_type_id: uuid.UUID | None = strawberry.UNSET
    resource_type: str | None = strawberry.UNSET


@strawberry.input
class ServiceGroupCreateInput:
    name: str
    display_name: str | None = None
    description: str | None = None


@strawberry.input
class ServiceGroupUpdateInput:
    name: str | None = None
    display_name: str | None = strawberry.UNSET
    description: str | None = strawberry.UNSET


@strawberry.input
class CatalogOverlayItemCreateInput:
    overlay_action: str
    base_item_id: uuid.UUID | None = None
    service_offering_id: uuid.UUID | None = None
    service_group_id: uuid.UUID | None = None
    sort_order: int = 0
