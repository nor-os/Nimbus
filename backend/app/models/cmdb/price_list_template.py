"""
Overview: Price list template models — blueprint price lists for cloning to new tenants.
Architecture: Service delivery onboarding with template-based pricing (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Price list templates are blueprints that can be cloned into real price lists
    for new client onboarding. Templates may link to region acceptance templates.
"""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PriceListTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A blueprint price list for cloning."""

    __tablename__ = "price_list_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    region_acceptance_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("region_acceptance_templates.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )

    items: Mapped[list["PriceListTemplateItem"]] = relationship(
        back_populates="template", lazy="selectin"
    )


class PriceListTemplateItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A pricing entry in a price list template."""

    __tablename__ = "price_list_template_items"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("price_list_templates.id"),
        nullable=False,
        index=True,
    )
    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id"),
        nullable=False,
    )
    delivery_region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_regions.id"), nullable=True
    )
    coverage_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    template: Mapped["PriceListTemplate"] = relationship(back_populates="items")
