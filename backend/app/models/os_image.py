"""
Overview: OS Image catalog models — abstract OS image definitions and per-provider image mappings.
Architecture: System-level models (not tenant-scoped) for the OS image catalog (Section 5)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: OS images define abstract operating system choices. Provider mappings link images to
    provider-specific references (AMI IDs, Azure URNs, template names, etc.).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class OsImage(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An abstract OS image definition (e.g. Ubuntu 22.04 LTS)."""

    __tablename__ = "os_images"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    os_family: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    architecture: Mapped[str] = mapped_column(String(20), nullable=False, server_default="x86_64")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    provider_mappings: Mapped[list["OsImageProviderMapping"]] = relationship(
        back_populates="os_image",
        lazy="selectin",
    )
    tenant_assignments: Mapped[list["OsImageTenantAssignment"]] = relationship(
        back_populates="os_image",
        lazy="selectin",
    )


class OsImageProviderMapping(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Maps an OS image to a provider-specific image reference."""

    __tablename__ = "os_image_provider_mappings"

    os_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("os_images.id"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_providers.id"),
        nullable=False,
    )
    image_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    os_image: Mapped["OsImage"] = relationship(
        back_populates="provider_mappings",
        lazy="joined",
    )
    provider: Mapped["SemanticProvider"] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "os_image_id", "provider_id",
            name="uq_os_image_provider_mapping",
        ),
        Index("ix_os_image_provider_mappings_image", "os_image_id"),
        Index("ix_os_image_provider_mappings_provider", "provider_id"),
    )


class OsImageTenantAssignment(Base, IDMixin):
    """Assigns an OS image to a specific tenant for visibility."""

    __tablename__ = "os_image_tenant_assignments"

    os_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("os_images.id"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    os_image: Mapped["OsImage"] = relationship(
        back_populates="tenant_assignments",
        lazy="joined",
    )
    tenant: Mapped["Tenant"] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "os_image_id", "tenant_id",
            name="uq_os_image_tenant_assignment",
        ),
        Index("ix_os_image_tenant_assignments_image", "os_image_id"),
        Index("ix_os_image_tenant_assignments_tenant", "tenant_id"),
    )
