"""
Overview: Provider SKU models — provider-specific billable resource units and offering composition.
Architecture: Provider SKU tracking and offering-SKU linkage (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Provider SKUs represent granular billable units from cloud providers. Offering SKUs
    compose service offerings from multiple SKUs with quantities.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ProviderSku(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A provider-specific billable resource unit."""

    __tablename__ = "provider_skus"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=False, index=True
    )
    external_sku_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ci_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=True, index=True
    )
    measuring_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="month"
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="EUR"
    )
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    semantic_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_resource_types.id"), nullable=True, index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    semantic_type_rel = relationship(
        "SemanticResourceType", foreign_keys=[semantic_type_id], lazy="joined"
    )


class ServiceOfferingSku(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Links a service offering to provider SKUs with quantity and ordering."""

    __tablename__ = "service_offering_skus"

    service_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_offerings.id"), nullable=False, index=True
    )
    provider_sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_skus.id"), nullable=False, index=True
    )
    default_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
