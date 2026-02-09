"""
Overview: Price list models — price lists, line items, and tenant-specific overrides.
Architecture: Hierarchical pricing with date-range effectiveness and tenant overrides (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Price lists group pricing for service offerings. Each line item specifies a per-unit
    price with optional quantity tiers. Tenant overrides provide custom pricing or discounts.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PriceList(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A collection of prices for service offerings."""

    __tablename__ = "price_lists"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    items: Mapped[list["PriceListItem"]] = relationship(
        back_populates="price_list", lazy="selectin"
    )


class PriceListItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A per-service price within a price list."""

    __tablename__ = "price_list_items"

    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id"),
        nullable=False,
        index=True,
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
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    price_list: Mapped["PriceList"] = relationship(back_populates="items")
    service_offering: Mapped["ServiceOffering"] = relationship(lazy="joined")  # noqa: F821


class TenantPriceOverride(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Tenant-specific pricing override for a service offering."""

    __tablename__ = "tenant_price_overrides"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id"),
        nullable=False,
        index=True,
    )
    delivery_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    coverage_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    discount_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
