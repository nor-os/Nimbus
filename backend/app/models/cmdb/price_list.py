"""
Overview: Price list models — price lists with semantic versioning, line items, tenant-specific
    overrides, and tenant-to-version pin assignments.
Architecture: Hierarchical pricing with date-range effectiveness, version lifecycle, region
    defaults, and tenant overrides (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Price lists group pricing for service offerings. Each line item specifies a per-unit
    price with optional quantity tiers. Tenant overrides provide custom pricing or discounts.
    Versioning: price lists belong to a group_id; each group has major.minor versions with
    draft→published→archived lifecycle. Region defaults and tenant pins control the cascade.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PriceList(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A collection of prices for service offerings with semantic versioning."""

    __tablename__ = "price_lists"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # ── Versioning ────────────────────────────────────────────────────
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    version_major: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    version_minor: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft"
    )
    delivery_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True
    )
    cloned_from_price_list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True, index=True
    )

    items: Mapped[list["PriceListItem"]] = relationship(
        back_populates="price_list", lazy="selectin"
    )
    cloned_from: Mapped["PriceList | None"] = relationship(
        "PriceList",
        lazy="select",
        foreign_keys=[cloned_from_price_list_id],
        remote_side="PriceList.id",
    )
    region_constraints: Mapped[list["PriceListRegionConstraint"]] = relationship(  # noqa: F821
        lazy="selectin"
    )

    @property
    def version_label(self) -> str:
        return f"v{self.version_major}.{self.version_minor}"


class PriceListItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A per-service price within a price list."""

    __tablename__ = "price_list_items"

    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id"),
        nullable=True,
        index=True,
    )
    provider_sku_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_skus.id"), nullable=True, index=True
    )
    activity_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_definitions.id"), nullable=True, index=True
    )
    delivery_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    coverage_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    markup_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    price_list: Mapped["PriceList"] = relationship(back_populates="items")
    service_offering: Mapped["ServiceOffering"] = relationship(lazy="joined")  # noqa: F821


class TenantPriceListPin(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Pins a tenant to a specific price list version for a date range."""

    __tablename__ = "tenant_price_list_pins"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)

    price_list: Mapped["PriceList"] = relationship(lazy="joined")
    overlay_items: Mapped[list["PriceListOverlayItem"]] = relationship(  # noqa: F821
        lazy="selectin"
    )
    minimum_charges: Mapped[list["PinMinimumCharge"]] = relationship(  # noqa: F821
        lazy="selectin"
    )
