"""
Overview: Landing zone models — provider landing zones with regions and tag policies.
Architecture: Landing zone data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Provider landing zones, multi-region, tag governance, topology reuse
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class LandingZoneStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class LandingZone(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "landing_zones"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    backend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_backends.id"), nullable=False
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backend_regions.id"), nullable=True
    )
    topology_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_topologies.id"), nullable=True
    )
    hierarchy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cloud_tenancy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_items.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LandingZoneStatus] = mapped_column(
        Enum(LandingZoneStatus, name="landing_zone_status", create_constraint=False),
        nullable=False,
        default=LandingZoneStatus.DRAFT,
        server_default="DRAFT",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    network_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    iam_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    security_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    naming_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(lazy="joined", foreign_keys=[tenant_id])  # noqa: F821
    backend: Mapped["CloudBackend"] = relationship(lazy="joined")  # noqa: F821
    region: Mapped["BackendRegion | None"] = relationship(lazy="joined")  # noqa: F821
    topology: Mapped["ArchitectureTopology | None"] = relationship(lazy="joined")  # noqa: F821
    tag_policies: Mapped[list["LandingZoneTagPolicy"]] = relationship(
        back_populates="landing_zone", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_landing_zones_tenant", "tenant_id"),
        Index("ix_landing_zones_backend", "backend_id"),
        Index("ix_landing_zones_status", "tenant_id", "status"),
    )


class LandingZoneTagPolicy(Base, IDMixin, TimestampMixin):
    __tablename__ = "landing_zone_tag_policies"

    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    tag_key: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    allowed_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inherited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Relationships
    landing_zone: Mapped["LandingZone"] = relationship(back_populates="tag_policies", lazy="joined")

    __table_args__ = (
        Index("uq_lz_tag_key", "landing_zone_id", "tag_key", unique=True),
    )
