"""
Overview: Activity template, definition, service process, and process assignment models —
    reusable process step collections for service delivery.
Architecture: Service delivery activity tracking (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Activity templates group process steps. Each definition specifies a staff
    profile and estimated hours. Processes group activity templates into delivery workflows.
    Process assignments link service offerings to processes.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ActivityTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A reusable collection of process steps."""

    __tablename__ = "activity_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    semantic_activity_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_activity_types.id"),
        nullable=True,
    )

    definitions: Mapped[list["ActivityDefinition"]] = relationship(
        back_populates="template", lazy="selectin", order_by="ActivityDefinition.sort_order"
    )
    semantic_activity_type = relationship("SemanticActivityType", lazy="joined")


class ActivityDefinition(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An individual step within an activity template."""

    __tablename__ = "activity_definitions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_templates.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    staff_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_profiles.id"),
        nullable=False,
    )
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    step_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    template: Mapped["ActivityTemplate"] = relationship(back_populates="definitions")


class ServiceProcess(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A delivery workflow that groups activity templates."""

    __tablename__ = "service_processes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    activity_links: Mapped[list["ProcessActivityLink"]] = relationship(
        back_populates="process",
        lazy="selectin",
        order_by="ProcessActivityLink.sort_order",
    )


class ProcessActivityLink(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Links an activity template to a service process with ordering."""

    __tablename__ = "process_activity_links"

    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_processes.id"),
        nullable=False,
        index=True,
    )
    activity_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_templates.id"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    process: Mapped["ServiceProcess"] = relationship(back_populates="activity_links")
    activity_template: Mapped["ActivityTemplate"] = relationship()


class ServiceProcessAssignment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Links a service offering to a process."""

    __tablename__ = "service_process_assignments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id"),
        nullable=False,
        index=True,
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_processes.id"),
        nullable=False,
    )
    coverage_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
