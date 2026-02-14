"""
Overview: Region constraint models — many-to-many links between price lists/catalogs and regions.
Architecture: Geographic constraints for price lists and service catalogs (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Region constraints restrict which delivery regions a price list or catalog applies to.
    A tenant with a matching primary_region_id (or ancestor) can use the constrained entity.
    No constraints means the entity is globally applicable.
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class PriceListRegionConstraint(Base, IDMixin, TimestampMixin):
    """Links a price list to a delivery region constraint."""

    __tablename__ = "price_list_region_constraints"
    __table_args__ = (
        UniqueConstraint(
            "price_list_id", "delivery_region_id",
            name="uq_price_list_region_constraint",
        ),
    )

    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False, index=True
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
        index=True,
    )


class CatalogRegionConstraint(Base, IDMixin, TimestampMixin):
    """Links a service catalog to a delivery region constraint."""

    __tablename__ = "catalog_region_constraints"
    __table_args__ = (
        UniqueConstraint(
            "catalog_id", "delivery_region_id",
            name="uq_catalog_region_constraint",
        ),
    )

    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_catalogs.id"),
        nullable=False,
        index=True,
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
        index=True,
    )
