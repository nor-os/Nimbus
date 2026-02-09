"""
Overview: Service offering region model — links offerings to delivery regions.
Architecture: Catalog region linkage for regional operating model (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: When a service offering uses the 'regional' operating model, this junction
    table records which delivery regions it is available in.
"""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class ServiceOfferingRegion(Base, IDMixin, TimestampMixin):
    """Links a service offering to a delivery region."""

    __tablename__ = "service_offering_regions"

    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    service_offering: Mapped["ServiceOffering"] = relationship(  # noqa: F821
        back_populates="regions",
    )
