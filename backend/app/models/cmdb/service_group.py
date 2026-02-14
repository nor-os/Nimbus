"""
Overview: Service group models — organizational bundles of service offerings.
Architecture: Service group composition (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Service groups bundle multiple service offerings for organizational purposes.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ServiceGroup(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An organizational bundle of service offerings."""

    __tablename__ = "service_groups"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )

    items: Mapped[list["ServiceGroupItem"]] = relationship(
        back_populates="group", lazy="selectin", order_by="ServiceGroupItem.sort_order"
    )


class ServiceGroupItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Links a service offering to a group with ordering."""

    __tablename__ = "service_group_items"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_groups.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=False, index=True
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    group: Mapped["ServiceGroup"] = relationship(back_populates="items")
    offering: Mapped["ServiceOffering"] = relationship(lazy="selectin")
