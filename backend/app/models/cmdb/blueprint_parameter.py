"""
Overview: Stack blueprint parameter model — defines parameterized inputs for service cluster blueprints.
Architecture: CMDB blueprint parameter layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Parameters can be auto-derived from slot semantic types (source_type='slot_derived') or
    manually defined (source_type='custom'). Each parameter has an optional JSON Schema for validation.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class StackBlueprintParameter(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A parameter definition for a stack blueprint (service cluster)."""

    __tablename__ = "stack_blueprint_parameters"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameter_schema: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="JSON Schema for parameter validation"
    )
    default_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="custom",
        comment="slot_derived or custom"
    )
    source_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_cluster_slots.id"), nullable=True
    )
    source_property_path: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="JSON path within slot semantic type properties_schema"
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    cluster: Mapped["ServiceCluster"] = relationship(back_populates="parameters")  # noqa: F821
    source_slot: Mapped["ServiceClusterSlot | None"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("cluster_id", "name", name="uq_blueprint_param_name"),
    )
