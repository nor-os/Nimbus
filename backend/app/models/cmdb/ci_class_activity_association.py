"""
Overview: CI class ↔ activity template association model — tenant-scoped many-to-many
    with configurable relationship types.
Architecture: Catalog CI class / activity linkage (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Associates CI classes with activity templates using a free-text relationship type
    (seeded from semantic relationship kinds, extendable by users).
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CIClassActivityAssociation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Associates a CI class with an activity template via a relationship type."""

    __tablename__ = "ci_class_activity_associations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    ci_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=False, index=True
    )
    activity_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_templates.id"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    relationship_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relationship_types.id"),
        nullable=True,
    )

    ci_class: Mapped["CIClass"] = relationship(lazy="joined", foreign_keys=[ci_class_id])  # noqa: F821
    activity_template: Mapped["ActivityTemplate"] = relationship(lazy="joined", foreign_keys=[activity_template_id])  # noqa: F821
    relationship_type_ref = relationship("RelationshipType", lazy="joined", foreign_keys=[relationship_type_id])  # noqa: F821

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ci_class_id",
            "activity_template_id",
            "relationship_type",
            name="uq_ci_class_activity_assoc",
        ),
    )
