"""
Overview: Tenant model representing organizations within a provider hierarchy (3 levels max).
Architecture: Multi-tenancy data model (Section 4.1, 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Multi-tenancy, tenant hierarchy, provider→tenant→sub-tenant
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Tenant(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True
    )
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    billing_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_root: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str | None] = mapped_column(String(63), unique=True, nullable=True)
    invoice_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    primary_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )

    # Relationships
    parent: Mapped["Tenant | None"] = relationship(
        "Tenant", remote_side="Tenant.id", back_populates="children"
    )
    children: Mapped[list["Tenant"]] = relationship("Tenant", back_populates="parent")
    provider: Mapped["Provider"] = relationship(back_populates="tenants")  # noqa: F821
    settings: Mapped[list["TenantSettings"]] = relationship(back_populates="tenant")  # noqa: F821
    quotas: Mapped[list["TenantQuota"]] = relationship(back_populates="tenant")  # noqa: F821
    user_tenants: Mapped[list["UserTenant"]] = relationship(back_populates="tenant")  # noqa: F821
    compartments: Mapped[list["Compartment"]] = relationship(back_populates="tenant")  # noqa: F821
    domain_mappings: Mapped[list["DomainMapping"]] = relationship(back_populates="tenant")  # noqa: F821
