"""
Overview: Stack blueprint composition models — versions, components, variable bindings, governance, workflows.
Architecture: CMDB stack blueprint layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Blueprint versioning, component composition, variable wiring, governance rules,
    operational workflow bindings.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────


class BlueprintCategory(str, enum.Enum):
    COMPUTE = "COMPUTE"
    DATABASE = "DATABASE"
    NETWORKING = "NETWORKING"
    STORAGE = "STORAGE"
    PLATFORM = "PLATFORM"
    SECURITY = "SECURITY"
    MONITORING = "MONITORING"
    CUSTOM = "CUSTOM"


class BindingDirection(str, enum.Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class StackWorkflowKind(str, enum.Enum):
    PROVISION = "PROVISION"
    DEPROVISION = "DEPROVISION"
    UPDATE = "UPDATE"
    SCALE = "SCALE"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"
    FAILOVER = "FAILOVER"
    HEALTH_CHECK = "HEALTH_CHECK"
    CUSTOM = "CUSTOM"


# ── Models ────────────────────────────────────────────────────────────


class StackBlueprintVersion(Base, IDMixin):
    """Immutable version snapshot of a blueprint."""

    __tablename__ = "stack_blueprint_versions"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    component_graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    variable_bindings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    blueprint: Mapped["ServiceCluster"] = relationship(back_populates="versions")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("blueprint_id", "version", name="uq_blueprint_version"),
    )


class StackBlueprintComponent(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A component node within a blueprint's composition graph."""

    __tablename__ = "stack_blueprint_components"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    default_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    depends_on: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    blueprint: Mapped["ServiceCluster"] = relationship(back_populates="blueprint_components")  # noqa: F821
    component: Mapped["Component"] = relationship(foreign_keys=[component_id], lazy="selectin")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("blueprint_id", "node_id", name="uq_blueprint_component_node"),
    )


class StackVariableBinding(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Maps a blueprint input/output variable to a specific component parameter."""

    __tablename__ = "stack_variable_bindings"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    variable_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_parameter: Mapped[str] = mapped_column(String(255), nullable=False)
    transform_expression: Mapped[str | None] = mapped_column(Text, nullable=True)

    blueprint: Mapped["ServiceCluster"] = relationship(back_populates="variable_bindings")  # noqa: F821


class StackBlueprintGovernance(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-tenant governance rules for a blueprint."""

    __tablename__ = "stack_blueprint_governance"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    is_allowed: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    parameter_constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_instances: Mapped[int | None] = mapped_column(Integer, nullable=True)

    blueprint: Mapped["ServiceCluster"] = relationship(back_populates="governance_rules")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("blueprint_id", "tenant_id", name="uq_blueprint_governance_tenant"),
    )


class StackWorkflow(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An operational workflow bound to a blueprint."""

    __tablename__ = "stack_workflows"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False
    )
    workflow_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    trigger_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    blueprint: Mapped["ServiceCluster"] = relationship(back_populates="stack_workflows")  # noqa: F821
