"""
Overview: Service estimation and line item models — quotes for client delivery
    with profitability analysis.
Architecture: Service delivery estimation engine (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Estimations aggregate line items (activity costs) against sell prices
    to calculate margin. Status workflow: draft → submitted → approved/rejected.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ServiceEstimation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A quote/estimation for a client delivery."""

    __tablename__ = "service_estimations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    client_tenant_id: Mapped[uuid.UUID] = mapped_column(
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
    price_list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="1"
    )
    sell_price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="0"
    )
    sell_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    total_estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    total_sell_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    margin_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    margin_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    line_items: Mapped[list["EstimationLineItem"]] = relationship(
        back_populates="estimation", lazy="selectin",
        order_by="EstimationLineItem.sort_order"
    )


class EstimationLineItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An activity cost line within an estimation."""

    __tablename__ = "estimation_line_items"

    estimation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_estimations.id"),
        nullable=False,
        index=True,
    )
    activity_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_definitions.id"),
        nullable=True,
    )
    rate_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internal_rate_cards.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    staff_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_profiles.id"),
        nullable=False,
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
    )
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    rate_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    line_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    estimation: Mapped["ServiceEstimation"] = relationship(
        back_populates="line_items"
    )
