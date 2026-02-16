"""
Overview: Resolver models — built-in resolver type definitions and per-scope configurations.
Architecture: Resolver data layer (Section 11)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Resolvers handle deploy-time parameter pre-resolution. Each resolver type has a handler
    class and schema definitions. Configurations bind resolver settings to landing zones/environments.
    Provider compatibility tracks which providers each resolver supports.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Resolver(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "resolvers"

    resolver_type: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    handler_class: Mapped[str] = mapped_column(String(500), nullable=False)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    instance_config_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supports_release: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    supports_update: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Relationships
    configurations: Mapped[list["ResolverConfiguration"]] = relationship(
        back_populates="resolver", lazy="selectin"
    )
    compatible_providers: Mapped[list["ResolverProviderCompatibility"]] = relationship(
        back_populates="resolver", lazy="selectin"
    )


class ResolverProviderCompatibility(Base):
    __tablename__ = "resolver_provider_compatibility"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    resolver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolvers.id"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    # Relationships
    resolver: Mapped["Resolver"] = relationship(back_populates="compatible_providers")
    provider: Mapped["SemanticProvider"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("resolver_id", "provider_id", name="uq_resolver_provider_compat"),
        Index("ix_resolver_compat_resolver", "resolver_id"),
        Index("ix_resolver_compat_provider", "provider_id"),
    )


class ResolverConfiguration(Base, IDMixin, TimestampMixin):
    __tablename__ = "resolver_configurations"

    resolver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolvers.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=True
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    # Relationships
    resolver: Mapped["Resolver"] = relationship(back_populates="configurations", lazy="joined")
    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined", foreign_keys=[landing_zone_id])  # noqa: F821
    environment: Mapped["TenantEnvironment"] = relationship(lazy="joined", foreign_keys=[environment_id])  # noqa: F821

    __table_args__ = (
        Index("ix_resolver_config_resolver", "resolver_id"),
        Index("ix_resolver_config_zone", "landing_zone_id"),
    )
