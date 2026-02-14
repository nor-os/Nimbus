"""
Overview: Service offering model — items in the service catalog that can be priced.
Architecture: Service catalog with multi-CI-class linkage (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Service offerings represent orderable/billable items. Each may link to multiple
    CI classes via a junction table and has a measuring unit for pricing.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ServiceOffering(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A billable/orderable service in the catalog."""

    __tablename__ = "service_offerings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    measuring_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="month"
    )
    service_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="resource"
    )
    operating_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    default_coverage_model: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    cloned_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=True
    )
    base_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    fee_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    minimum_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    minimum_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    minimum_period: Mapped[str | None] = mapped_column(String(20), nullable=True)

    ci_classes: Mapped[list["ServiceOfferingCIClass"]] = relationship(  # noqa: F821
        back_populates="service_offering", cascade="all, delete-orphan"
    )

    regions: Mapped[list["ServiceOfferingRegion"]] = relationship(  # noqa: F821
        back_populates="service_offering", cascade="all, delete-orphan"
    )

    skus: Mapped[list["ServiceOfferingSku"]] = relationship(  # noqa: F821
        lazy="selectin"
    )
