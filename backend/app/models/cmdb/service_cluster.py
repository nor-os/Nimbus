"""
Overview: Service cluster models — blueprint templates defining logical service units with role-based slots.
Architecture: CMDB service cluster layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Service clusters are pure templates that define slot shapes and constraints.
    CI assignment happens at deployment time (not on the blueprint itself).
    Evolved to full stack blueprints with versioning, components, governance, and DR.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ServiceCluster(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A blueprint template defining a logical service unit with role-based slots."""

    __tablename__ = "service_clusters"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="service_cluster"
    )
    architecture_topology_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_topologies.id"), nullable=True
    )
    topology_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    stack_tag_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Tag key on CIs that identifies deployments of this blueprint"
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # ── New blueprint evolution fields ─────────────────────────────────
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── HA/DR configuration schemas ───────────────────────────────────
    ha_config_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ha_config_defaults: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dr_config_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dr_config_defaults: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    slots: Mapped[list["ServiceClusterSlot"]] = relationship(
        back_populates="cluster", lazy="selectin", cascade="all, delete-orphan"
    )
    parameters: Mapped[list["StackBlueprintParameter"]] = relationship(  # noqa: F821
        back_populates="cluster", lazy="selectin", cascade="all, delete-orphan"
    )
    versions: Mapped[list["StackBlueprintVersion"]] = relationship(  # noqa: F821
        back_populates="blueprint", lazy="selectin", cascade="all, delete-orphan"
    )
    blueprint_components: Mapped[list["StackBlueprintComponent"]] = relationship(  # noqa: F821
        back_populates="blueprint", lazy="selectin", cascade="all, delete-orphan"
    )
    variable_bindings: Mapped[list["StackVariableBinding"]] = relationship(  # noqa: F821
        back_populates="blueprint", lazy="selectin", cascade="all, delete-orphan"
    )
    governance_rules: Mapped[list["StackBlueprintGovernance"]] = relationship(  # noqa: F821
        back_populates="blueprint", lazy="selectin", cascade="all, delete-orphan"
    )
    stack_workflows: Mapped[list["StackWorkflow"]] = relationship(  # noqa: F821
        back_populates="blueprint", lazy="selectin", cascade="all, delete-orphan"
    )
    reservation_template: Mapped["BlueprintReservationTemplate | None"] = relationship(  # noqa: F821
        lazy="selectin", cascade="all, delete-orphan", uselist=False,
        foreign_keys="BlueprintReservationTemplate.blueprint_id",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_service_cluster_tenant_name"),
        Index("ix_sc_tenant_type", "tenant_id", "cluster_type"),
    )


class ServiceClusterSlot(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A role slot within a blueprint that defines constraints for future CI assignment."""

    __tablename__ = "service_cluster_slots"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_ci_class_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    semantic_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_categories.id"), nullable=True
    )
    semantic_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_resource_types.id"), nullable=True
    )
    min_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    max_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # ── New slot evolution fields ──────────────────────────────────────
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("components.id"), nullable=True
    )
    default_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    depends_on: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    cluster: Mapped["ServiceCluster"] = relationship(back_populates="slots")
    semantic_category: Mapped["SemanticCategory | None"] = relationship(lazy="joined", foreign_keys=[semantic_category_id])  # noqa: F821
    semantic_type: Mapped["SemanticResourceType | None"] = relationship(lazy="joined", foreign_keys=[semantic_type_id])  # noqa: F821

    __table_args__ = (
        UniqueConstraint("cluster_id", "name", name="uq_slot_cluster_name"),
    )
