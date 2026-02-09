"""
Overview: Workflow definition model — stores visual workflow graphs with versioning and lifecycle.
Architecture: Data model for workflow editor definitions (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Workflow definitions, JSONB graph storage, versioning, draft/active/archived lifecycle
"""

import enum
import uuid

from sqlalchemy import Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class WorkflowDefinitionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class WorkflowDefinition(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A versioned visual workflow definition stored as a JSONB graph."""

    __tablename__ = "workflow_definitions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[WorkflowDefinitionStatus] = mapped_column(
        Enum(
            WorkflowDefinitionStatus,
            name="workflow_definition_status",
            create_constraint=True,
        ),
        nullable=False,
        server_default="DRAFT",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="3600"
    )
    max_concurrent: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="10"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name", "version",
            name="uq_workflow_def_tenant_name_version",
        ),
        Index("ix_workflow_definitions_tenant", "tenant_id"),
        Index("ix_workflow_definitions_status", "tenant_id", "status"),
        Index("ix_workflow_definitions_created_by", "created_by"),
    )
