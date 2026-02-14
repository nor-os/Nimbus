"""
Overview: Consumption record model — tracks resource usage for billing.
Architecture: Consumption tracking data model (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Consumption records track resource usage per SKU/activity/offering for billing periods.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ConsumptionRecord(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Tracks resource consumption for billing periods."""

    __tablename__ = "consumption_records"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    provider_sku_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_skus.id"), nullable=True
    )
    activity_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_definitions.id"), nullable=True
    )
    service_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="manual"
    )
