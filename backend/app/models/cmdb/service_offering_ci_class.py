"""
Overview: Service offering CI class junction model — links offerings to multiple CI classes.
Architecture: Catalog CI class linkage for multi-select (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Service offerings can be linked to multiple CI classes (both resource and labor).
    This replaces the old single ci_class_id FK with a many-to-many junction table.
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class ServiceOfferingCIClass(Base, IDMixin, TimestampMixin):
    """Links a service offering to a CI class."""

    __tablename__ = "service_offering_ci_classes"

    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ci_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ci_classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    service_offering: Mapped["ServiceOffering"] = relationship(  # noqa: F821
        back_populates="ci_classes",
    )

    __table_args__ = (
        UniqueConstraint(
            "service_offering_id", "ci_class_id", name="uq_offering_ci_class"
        ),
    )
