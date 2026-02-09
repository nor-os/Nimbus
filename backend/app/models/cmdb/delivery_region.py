"""
Overview: Delivery region model — hierarchical MSP delivery centers/geographies.
Architecture: Service delivery engine with region-based pricing (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Delivery regions represent MSP delivery centers (e.g. Manila, Frankfurt).
    Hierarchical: top-level continents (APAC, EMEA, AMER) contain city-level centers.
    System-seeded regions cannot be deleted. Tenant-specific regions are optional.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class DeliveryRegion(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A delivery center or geographic region for service delivery."""

    __tablename__ = "delivery_regions"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    parent_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
