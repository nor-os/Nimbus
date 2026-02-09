"""
Overview: Workflow execution models — tracks runtime state of workflow and individual node executions.
Architecture: Data models for workflow execution tracking (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Workflow execution, node execution, immutable execution records, Temporal correlation
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin


class WorkflowExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowNodeExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowExecution(Base, IDMixin):
    """Immutable record of a workflow execution linked to a Temporal workflow run."""

    __tablename__ = "workflow_executions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id"),
        nullable=False,
    )
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    temporal_workflow_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    status: Mapped[WorkflowExecutionStatus] = mapped_column(
        Enum(
            WorkflowExecutionStatus,
            name="workflow_execution_status",
            create_constraint=True,
        ),
        nullable=False,
        server_default="PENDING",
    )
    input: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_test: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    node_executions: Mapped[list["WorkflowNodeExecution"]] = relationship(
        "WorkflowNodeExecution", back_populates="execution", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_workflow_executions_tenant", "tenant_id"),
        Index("ix_workflow_executions_definition", "definition_id"),
        Index("ix_workflow_executions_status", "tenant_id", "status"),
        Index("ix_workflow_executions_temporal", "temporal_workflow_id"),
        Index("ix_workflow_executions_started_by", "started_by"),
    )


class WorkflowNodeExecution(Base, IDMixin):
    """Tracks the execution state of an individual node within a workflow run."""

    __tablename__ = "workflow_node_executions"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[WorkflowNodeExecutionStatus] = mapped_column(
        Enum(
            WorkflowNodeExecutionStatus,
            name="workflow_node_execution_status",
            create_constraint=True,
        ),
        nullable=False,
        server_default="PENDING",
    )
    input: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution", back_populates="node_executions"
    )

    __table_args__ = (
        Index("ix_workflow_node_executions_execution", "execution_id"),
        Index(
            "ix_workflow_node_executions_node",
            "execution_id", "node_id",
        ),
    )
