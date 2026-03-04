"""
Overview: Blueprint reservation template models — defines default DR reservation settings
    at the blueprint level and per-component level.
Architecture: CMDB blueprint reservation template layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Reservation templates allow blueprint authors to define default DR reservation
    settings (type, resource percentage, RTO/RPO) that are auto-applied when instances deploy.
    ComponentReservationTemplate adds per-component reservation configuration.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class BlueprintReservationTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Default DR reservation settings for a blueprint."""

    __tablename__ = "blueprint_reservation_templates"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_clusters.id"), nullable=False, unique=True, index=True
    )
    reservation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_percentage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="80")
    target_environment_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=True
    )
    rto_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpo_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_create_on_deploy: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    sync_policies_template: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ComponentReservationTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-component DR reservation settings within a blueprint."""

    __tablename__ = "component_reservation_templates"

    blueprint_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stack_blueprint_components.id"), nullable=False, index=True
    )
    reservation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_percentage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="80")
    target_environment_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=True
    )
    rto_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpo_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_create_on_deploy: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    sync_policies_template: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "blueprint_component_id",
            name="uq_component_reservation_template",
        ),
    )
