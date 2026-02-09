"""
Overview: Region acceptance models — templates, template rules, tenant acceptances,
    and tenant template assignments for compliance enforcement.
Architecture: Service delivery compliance with region acceptance rules (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Region acceptance defines which delivery regions a tenant accepts.
    Templates are reusable presets. Tenant-level overrides support compliance enforcement.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class RegionAcceptanceTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A reusable acceptance preset for delivery regions."""

    __tablename__ = "region_acceptance_templates"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )


class RegionAcceptanceTemplateRule(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A rule within an acceptance template."""

    __tablename__ = "region_acceptance_template_rules"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("region_acceptance_templates.id"),
        nullable=False,
        index=True,
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
    )
    acceptance_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantRegionAcceptance(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-tenant region acceptance rule (overrides templates)."""

    __tablename__ = "tenant_region_acceptances"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    delivery_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_regions.id"),
        nullable=False,
    )
    acceptance_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_compliance_enforced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )


class TenantRegionTemplateAssignment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Links a tenant to a region acceptance template."""

    __tablename__ = "tenant_region_template_assignments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("region_acceptance_templates.id"),
        nullable=False,
    )
