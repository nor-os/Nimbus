"""
Overview: Stack instance models — deployed runtime instances of stack blueprints.
Architecture: CMDB stack instance layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Runtime stack instances with per-component state tracking, health monitoring.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────


class StackInstanceStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DEGRADED = "DEGRADED"
    DECOMMISSIONING = "DECOMMISSIONING"
    DECOMMISSIONED = "DECOMMISSIONED"
    FAILED = "FAILED"


class HealthStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class ComponentInstanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    FAILED = "FAILED"
    DECOMMISSIONED = "DECOMMISSIONED"


# ── Models ────────────────────────────────────────────────────────────


class StackInstance(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A deployed runtime instance of a stack blueprint."""

    __tablename__ = "stack_instances"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    blueprint_version: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), server_default="PLANNED", nullable=False)
    input_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    component_states: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), server_default="UNKNOWN", nullable=False)
    deployed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ha_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dr_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    instance_components: Mapped[list["StackInstanceComponent"]] = relationship(
        back_populates="stack_instance", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "environment_id", "name", name="uq_stack_instance_tenant_env_name"),
    )


class StackInstanceComponent(Base, IDMixin, TimestampMixin):
    """Per-component state within a deployed stack instance."""

    __tablename__ = "stack_instance_components"

    stack_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stack_instances.id"), nullable=False, index=True
    )
    blueprint_component_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stack_blueprint_components.id"), nullable=True
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id"), nullable=False
    )
    component_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ci_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_items.id"), nullable=True
    )
    deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), server_default="PENDING", nullable=False)
    resolved_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pulumi_state_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    stack_instance: Mapped["StackInstance"] = relationship(back_populates="instance_components")
