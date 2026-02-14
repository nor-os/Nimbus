"""
Overview: Price list overlay item model — per-pin modifications to base price list items.
Architecture: Overlay pricing on tenant price list pins (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Overlay items modify, add, or exclude specific pricing items on a tenant's
    price list pin. This replaces standalone tenant price overrides with pin-scoped overlays.
"""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PriceListOverlayItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-pin overlay that modifies, adds, or excludes a price list item."""

    __tablename__ = "price_list_overlay_items"
    __table_args__ = (
        CheckConstraint(
            "overlay_action IN ('modify', 'add', 'exclude')",
            name="ck_price_list_overlay_action",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    pin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_price_list_pins.id"),
        nullable=False,
        index=True,
    )
    overlay_action: Mapped[str] = mapped_column(String(10), nullable=False)

    # For modify/exclude: references the base item being changed
    base_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_list_items.id"), nullable=True
    )

    # For 'add': what is being added
    service_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=True
    )
    provider_sku_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_skus.id"), nullable=True
    )
    activity_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_definitions.id"), nullable=True
    )
    delivery_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    coverage_model: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Pricing fields (required for modify/add, ignored for exclude)
    price_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    markup_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    discount_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
