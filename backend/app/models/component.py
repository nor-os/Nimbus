"""
Overview: Component models — typed Pulumi scripts bound to semantic types with versioning and governance.
Architecture: Component data layer (Section 11)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Components are versioned infrastructure-as-code scripts. Each component targets a specific
    provider + semantic type combination. Governance rules control per-tenant allow/deny and constraints.
"""

from __future__ import annotations

import enum
import uuid

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ComponentLanguage(str, enum.Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"


class OperationCategory(str, enum.Enum):
    DEPLOYMENT = "DEPLOYMENT"
    DAY2 = "DAY2"


class OperationKind(str, enum.Enum):
    CREATE = "CREATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"
    UPDATE = "UPDATE"
    VALIDATE = "VALIDATE"
    READ = "READ"


class EstimatedDowntime(str, enum.Enum):
    NONE = "NONE"
    BRIEF = "BRIEF"
    EXTENDED = "EXTENDED"


class Component(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "components"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=False
    )
    semantic_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_resource_types.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[ComponentLanguage] = mapped_column(
        Enum(ComponentLanguage, name="component_language", create_constraint=False),
        nullable=False,
        default=ComponentLanguage.TYPESCRIPT,
        server_default="typescript",
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolver_bindings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    upgrade_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(lazy="joined", foreign_keys=[tenant_id])  # noqa: F821
    provider: Mapped["SemanticProvider"] = relationship(lazy="joined")  # noqa: F821
    semantic_type: Mapped["SemanticResourceType"] = relationship(lazy="joined")  # noqa: F821
    versions: Mapped[list["ComponentVersion"]] = relationship(
        back_populates="component", lazy="selectin"
    )
    governance_rules: Mapped[list["ComponentGovernance"]] = relationship(
        back_populates="component", lazy="selectin"
    )
    operations: Mapped[list["ComponentOperation"]] = relationship(
        back_populates="component", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_components_tenant", "tenant_id"),
        Index("ix_components_provider", "provider_id"),
        Index("ix_components_semantic_type", "semantic_type_id"),
    )


class ComponentVersion(Base, IDMixin):
    __tablename__ = "component_versions"

    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolver_bindings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    published_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    component: Mapped["Component"] = relationship(back_populates="versions")

    __table_args__ = (
        Index("uq_component_versions_component_version", "component_id", "version", unique=True),
    )


class ComponentGovernance(Base, IDMixin, TimestampMixin):
    __tablename__ = "component_governance"

    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    is_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    parameter_constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_instances: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    component: Mapped["Component"] = relationship(back_populates="governance_rules")
    tenant: Mapped["Tenant"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("uq_component_governance_component_tenant", "component_id", "tenant_id", unique=True),
    )


class ComponentOperation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "component_operations"

    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False
    )
    is_destructive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    estimated_downtime: Mapped[EstimatedDowntime] = mapped_column(
        Enum(EstimatedDowntime, name="estimated_downtime", create_constraint=False, native_enum=False),
        nullable=False,
        default=EstimatedDowntime.NONE,
        server_default="NONE",
    )
    operation_category: Mapped[OperationCategory] = mapped_column(
        Enum(OperationCategory, name="operation_category", create_constraint=False, native_enum=False),
        nullable=False,
        default=OperationCategory.DAY2,
        server_default="DAY2",
    )
    operation_kind: Mapped[OperationKind | None] = mapped_column(
        Enum(OperationKind, name="operation_kind", create_constraint=False, native_enum=False),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Relationships
    component: Mapped["Component"] = relationship(back_populates="operations")
    workflow_definition: Mapped["WorkflowDefinition"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_component_operations_category", "component_id", "operation_category"),
    )
