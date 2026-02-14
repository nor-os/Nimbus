"""
Overview: Catalog overlay item model — per-pin include/exclude modifications to catalog items.
Architecture: Overlay items on tenant catalog pins (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Catalog overlay items include or exclude specific offerings/groups from a tenant's
    catalog pin. This provides per-tenant catalog customisation without cloning.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CatalogOverlayItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-pin overlay that includes or excludes a catalog item."""

    __tablename__ = "catalog_overlay_items"
    __table_args__ = (
        CheckConstraint(
            "overlay_action IN ('include', 'exclude')",
            name="ck_catalog_overlay_action",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    pin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_catalog_pins.id"),
        nullable=False,
        index=True,
    )
    overlay_action: Mapped[str] = mapped_column(String(10), nullable=False)

    # For exclude: references the base catalog item being removed
    base_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalog_items.id"), nullable=True
    )

    # For include: what is being added
    service_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=True
    )
    service_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_groups.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
