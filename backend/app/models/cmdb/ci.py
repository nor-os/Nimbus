"""
Overview: Configuration Item model — the core entity of the CMDB.
Architecture: Tenant-scoped CI with class-based validation and lifecycle management (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: CIs represent infrastructure resources. Each CI belongs to a class (schema), may live
    in a compartment, tracks lifecycle state, and stores flexible attributes as JSONB. Cloud
    resource IDs and Pulumi URNs provide external linkage for discovery and IaC operations.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ConfigurationItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A configuration item — an infrastructure resource tracked in the CMDB."""

    __tablename__ = "configuration_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    ci_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=False, index=True
    )
    compartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compartments.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="planned"
    )
    attributes: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    tags: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    cloud_resource_id: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    pulumi_urn: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    ci_class: Mapped["CIClass"] = relationship(lazy="joined")  # noqa: F821
    compartment: Mapped["Compartment | None"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_ci_tenant_class", "tenant_id", "ci_class_id"),
        Index("ix_ci_tenant_compartment", "tenant_id", "compartment_id"),
        Index("ix_ci_cloud_resource_id", "cloud_resource_id"),
        Index("ix_ci_pulumi_urn", "pulumi_urn"),
        Index("ix_ci_lifecycle_state", "lifecycle_state"),
    )
