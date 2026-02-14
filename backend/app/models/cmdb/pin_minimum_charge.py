"""
Overview: Pin minimum charge model — minimum billing thresholds tied to price list pins.
Architecture: Per-pin minimum charges (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Pin minimum charges define billing floors per category or globally, scoped to a
    specific tenant price list pin rather than standalone per-tenant records.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PinMinimumCharge(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Minimum billing threshold tied to a price list pin."""

    __tablename__ = "pin_minimum_charges"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    pin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_price_list_pins.id"),
        nullable=False,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    minimum_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
