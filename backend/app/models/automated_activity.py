"""
Overview: Automated activity models — catalog, versioned implementations, executions, and config changes.
Architecture: Activity catalog data layer (Section 11.5)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Activity lifecycle, version immutability, config mutation ledger, execution tracking
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OperationKind(str, enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    REMEDIATE = "REMEDIATE"
    VALIDATE = "VALIDATE"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"


class ImplementationType(str, enum.Enum):
    PYTHON_SCRIPT = "PYTHON_SCRIPT"
    HTTP_WEBHOOK = "HTTP_WEBHOOK"
    PULUMI_OPERATION = "PULUMI_OPERATION"
    SHELL_SCRIPT = "SHELL_SCRIPT"
    MANUAL = "MANUAL"


class MutationType(str, enum.Enum):
    SET = "SET"
    SET_FROM_INPUT = "SET_FROM_INPUT"
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    APPEND = "APPEND"
    REMOVE = "REMOVE"


class ActivityScope(str, enum.Enum):
    COMPONENT = "COMPONENT"
    WORKFLOW = "WORKFLOW"


class ActivityExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AutomatedActivity(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A cataloged automated activity with versioned implementations."""

    __tablename__ = "automated_activities"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    semantic_activity_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_activity_types.id"),
        nullable=True,
    )
    semantic_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_resource_types.id"),
        nullable=True,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_providers.id"),
        nullable=True,
    )
    operation_kind: Mapped[OperationKind] = mapped_column(
        Enum(OperationKind, name="operation_kind_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=OperationKind.UPDATE,
        server_default="UPDATE",
    )
    implementation_type: Mapped[ImplementationType] = mapped_column(
        Enum(ImplementationType, name="implementation_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=ImplementationType.PYTHON_SCRIPT,
        server_default="PYTHON_SCRIPT",
    )
    idempotent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="300"
    )
    scope: Mapped[ActivityScope] = mapped_column(
        Enum(ActivityScope, name="activity_scope_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=ActivityScope.WORKFLOW,
        server_default="WORKFLOW",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    versions: Mapped[list["AutomatedActivityVersion"]] = relationship(
        back_populates="activity",
        lazy="selectin",
        order_by="AutomatedActivityVersion.version",
    )
    semantic_activity_type = relationship("SemanticActivityType", lazy="joined")
    semantic_type = relationship("SemanticResourceType", lazy="joined")
    provider = relationship("SemanticProvider", lazy="joined")


class AutomatedActivityVersion(Base, IDMixin, TimestampMixin):
    """An immutable snapshot of an activity's implementation."""

    __tablename__ = "automated_activity_versions"

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automated_activities.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    config_mutations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rollback_mutations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    runtime_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    activity: Mapped["AutomatedActivity"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("activity_id", "version", name="uq_activity_version"),
    )


class ActivityExecution(Base, IDMixin, TimestampMixin):
    """Runtime execution record for an activity."""

    __tablename__ = "activity_executions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    activity_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automated_activity_versions.id"),
        nullable=False,
    )
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id"),
        nullable=True,
    )
    ci_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration_items.id"),
        nullable=True,
    )
    deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployments.id"),
        nullable=True,
    )
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ActivityExecutionStatus] = mapped_column(
        Enum(ActivityExecutionStatus, name="activity_execution_status_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=ActivityExecutionStatus.PENDING,
        server_default="PENDING",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    activity_version: Mapped["AutomatedActivityVersion"] = relationship(lazy="joined")
    config_changes: Mapped[list["ConfigurationChange"]] = relationship(
        back_populates="execution", lazy="selectin"
    )


class ConfigurationChange(Base, IDMixin):
    """A recorded change to deployment parameters."""

    __tablename__ = "configuration_changes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False
    )
    activity_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_executions.id"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parameter_path: Mapped[str] = mapped_column(Text, nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    applied_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rollback_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration_changes.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    # Relationships
    execution: Mapped["ActivityExecution"] = relationship(back_populates="config_changes")

    __table_args__ = (
        UniqueConstraint("deployment_id", "version", name="uq_config_change_version"),
    )
