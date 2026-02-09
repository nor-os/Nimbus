"""
Overview: Organizational unit, staff profile, and internal rate card models — org hierarchy,
    roles/seniority levels, and cost/sell rates per profile per delivery region.
Architecture: Service delivery cost model (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Organizational units form a hierarchy with cost centers. Staff profiles define
    seniority levels (Junior Engineer, Architect, etc.). Internal rate cards specify
    the hourly cost and sell rate for each profile in each delivery region.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class OrganizationalUnit(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A hierarchical organizational unit with optional cost center."""

    __tablename__ = "organizational_units"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_center: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )


class StaffProfile(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A role/seniority level for staffing and rate cards."""

    __tablename__ = "staff_profiles"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizational_units.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    cost_center: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_hourly_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    default_currency: Mapped[str | None] = mapped_column(
        String(3), nullable=True, server_default="EUR"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )


class InternalRateCard(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Cost per staff profile per delivery region with date-range effectiveness."""

    __tablename__ = "internal_rate_cards"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    staff_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_profiles.id"),
        nullable=False,
        index=True,
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
        index=True,
    )
    hourly_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    hourly_sell_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
