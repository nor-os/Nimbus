"""
Overview: Deployment model — links architecture topologies to tenant environments.
Architecture: Deployment data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Deployment lifecycle, topology-to-environment binding, deployment sketching
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class DeploymentStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ResolutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class Deployment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "deployments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=False
    )
    topology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_topologies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status", create_constraint=False),
        nullable=False,
        default=DeploymentStatus.PLANNED,
        server_default="PLANNED",
    )
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    deployed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="PENDING", server_default="PENDING"
    )
    resolution_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(lazy="joined", foreign_keys=[tenant_id])  # noqa: F821
    environment: Mapped["TenantEnvironment"] = relationship(lazy="joined")  # noqa: F821
    topology: Mapped["ArchitectureTopology"] = relationship(lazy="joined")  # noqa: F821

    # Deployment-CI junction
    cis: Mapped[list["DeploymentCI"]] = relationship(
        back_populates="deployment", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_deployments_tenant", "tenant_id"),
        Index("ix_deployments_environment", "environment_id"),
        Index("ix_deployments_tenant_status", "tenant_id", "status"),
    )


class DeploymentCI(Base):
    """Junction table linking deployments to configuration items."""
    __tablename__ = "deployment_cis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False
    )
    ci_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_items.id"), nullable=False
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id"), nullable=False
    )
    topology_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolver_outputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    # Relationships
    deployment: Mapped["Deployment"] = relationship(back_populates="cis")
    ci: Mapped["ConfigurationItem"] = relationship(lazy="joined")  # noqa: F821
    component: Mapped["Component"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        sa.UniqueConstraint("deployment_id", "ci_id", name="uq_deployment_ci"),
        Index("ix_deployment_cis_deployment", "deployment_id"),
        Index("ix_deployment_cis_ci", "ci_id"),
    )
