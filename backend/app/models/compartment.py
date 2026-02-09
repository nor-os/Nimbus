"""
Overview: Compartment model for organizing resources within a tenant.
Architecture: Resource organization hierarchy (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Compartments, resource organization, tenant-scoped hierarchy. Extended in Phase 8
    with cloud_id and provider_type for CMDB cloud resource mapping.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Compartment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "compartments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compartments.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cloud_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="compartments")  # noqa: F821
    parent: Mapped["Compartment | None"] = relationship(
        "Compartment", remote_side="Compartment.id", back_populates="children"
    )
    children: Mapped[list["Compartment"]] = relationship("Compartment", back_populates="parent")
