"""
Overview: Architecture topology model — stores visual architecture designs with versioning and lifecycle.
Architecture: Data model for visual architecture planner (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Architecture topologies, JSONB graph storage, versioning, draft/published/archived lifecycle,
    tenant-scoped or system-level templates
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class TopologyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ArchitectureTopology(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A versioned visual architecture topology stored as a JSONB graph."""

    __tablename__ = "architecture_topologies"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[TopologyStatus] = mapped_column(
        Enum(
            TopologyStatus,
            name="topology_status",
            create_constraint=True,
        ),
        nullable=False,
        server_default="DRAFT",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_template: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_landing_zone: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    tags: Mapped[list | None] = mapped_column(ARRAY(String(100)), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name", "version",
            name="uq_topology_tenant_name_version",
        ),
        Index("ix_architecture_topologies_tenant", "tenant_id"),
        Index("ix_architecture_topologies_status", "tenant_id", "status"),
        Index("ix_architecture_topologies_created_by", "created_by"),
        Index("ix_architecture_topologies_template", "is_template"),
    )
