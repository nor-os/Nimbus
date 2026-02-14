"""
Overview: Service catalog models — versioned containers, catalog items, and tenant pins.
Architecture: Service catalog versioning with tenant-scoped pins (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Service catalogs group offerings into versioned collections. Tenant pins bind
    tenants to specific catalog versions.
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ServiceCatalog(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A versioned container of service offerings and groups."""

    __tablename__ = "service_catalogs"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    version_major: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    version_minor: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft"
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalogs.id"), nullable=True
    )
    cloned_from_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalogs.id"), nullable=True, index=True
    )

    items: Mapped[list["ServiceCatalogItem"]] = relationship(
        back_populates="catalog", lazy="selectin"
    )
    cloned_from: Mapped["ServiceCatalog | None"] = relationship(
        remote_side="ServiceCatalog.id",
        foreign_keys=[cloned_from_catalog_id],
        lazy="select",
    )
    region_constraints: Mapped[list["CatalogRegionConstraint"]] = relationship(  # noqa: F821
        lazy="selectin"
    )

    @property
    def version_label(self) -> str:
        return f"v{self.version_major}.{self.version_minor}"


class ServiceCatalogItem(Base, IDMixin, TimestampMixin):
    """Junction: links a catalog to an offering or group."""

    __tablename__ = "service_catalog_items"

    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalogs.id"), nullable=False, index=True
    )
    service_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=True
    )
    service_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_groups.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    catalog: Mapped["ServiceCatalog"] = relationship(back_populates="items")


class TenantCatalogPin(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Pins a tenant to a specific service catalog version for a date range."""

    __tablename__ = "tenant_catalog_pins"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalogs.id"), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)

    catalog: Mapped["ServiceCatalog"] = relationship(lazy="joined")
    overlay_items: Mapped[list["CatalogOverlayItem"]] = relationship(  # noqa: F821
        lazy="selectin"
    )
