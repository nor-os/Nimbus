"""
Overview: Environment models — templates and tenant environment instances.
Architecture: Tenant environment data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Environment templates, tenant environments, lifecycle management, tag inheritance
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class EnvironmentStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DECOMMISSIONING = "DECOMMISSIONING"
    DECOMMISSIONED = "DECOMMISSIONED"


class EnvironmentTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "environment_templates"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    default_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_policies: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Relationships
    provider: Mapped["Provider"] = relationship(lazy="joined")  # noqa: F821


class TenantEnvironment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenant_environments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environment_templates.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EnvironmentStatus] = mapped_column(
        Enum(EnvironmentStatus, name="environment_status", create_constraint=False),
        nullable=False,
        default=EnvironmentStatus.PLANNED,
        server_default="PLANNED",
    )
    root_compartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compartments.id"), nullable=True
    )
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    policies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    network_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    iam_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    security_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    monitoring_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backend_regions.id"), nullable=True
    )
    dr_source_env_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    dr_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(lazy="joined", foreign_keys=[tenant_id])  # noqa: F821
    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821
    template: Mapped["EnvironmentTemplate | None"] = relationship(lazy="joined")
    root_compartment: Mapped["Compartment | None"] = relationship(lazy="joined")  # noqa: F821
    region: Mapped["BackendRegion | None"] = relationship(lazy="joined", foreign_keys=[region_id])  # noqa: F821
    dr_source_env: Mapped["TenantEnvironment | None"] = relationship(
        "TenantEnvironment", remote_side="TenantEnvironment.id",
        foreign_keys=[dr_source_env_id], lazy="joined",
    )

    __table_args__ = (
        Index("ix_tenant_envs_tenant", "tenant_id"),
        Index("ix_tenant_envs_lz", "landing_zone_id"),
        Index("ix_tenant_envs_status", "tenant_id", "status"),
        Index("ix_tenant_envs_region", "region_id"),
        Index("ix_tenant_envs_dr_source", "dr_source_env_id"),
    )
