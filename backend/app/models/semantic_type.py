"""
Overview: Semantic layer models — categories, resource types, relationship kinds, and providers
    for the cloud abstraction layer.
Architecture: System-level models (not tenant-scoped) that define the semantic catalog (Section 5)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Semantic types normalize provider-specific resources into a unified model. Categories
    group types. Relationship kinds define how types connect. Providers are first-class entities.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class SemanticCategory(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A top-level grouping of semantic types (Compute, Network, etc.)."""

    __tablename__ = "semantic_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_infrastructure: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    types: Mapped[list["SemanticResourceType"]] = relationship(
        back_populates="category_rel",
        lazy="selectin",
    )


class SemanticResourceType(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An abstract resource type (VirtualMachine, Subnet, etc.)."""

    __tablename__ = "semantic_resource_types"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_abstract: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    parent_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_resource_types.id"),
        nullable=True,
    )
    properties_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    allowed_relationship_kinds: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    category_rel: Mapped["SemanticCategory"] = relationship(
        back_populates="types",
        lazy="joined",
    )
    parent_type: Mapped["SemanticResourceType | None"] = relationship(
        remote_side="SemanticResourceType.id",
        lazy="joined",
        foreign_keys=[parent_type_id],
    )
    children: Mapped[list["SemanticResourceType"]] = relationship(
        back_populates="parent_type",
        lazy="selectin",
        foreign_keys=[parent_type_id],
    )
    __table_args__ = (
        Index("ix_semantic_resource_types_category", "category_id"),
    )


class SemanticRelationshipKind(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A kind of relationship between semantic types."""

    __tablename__ = "semantic_relationship_kinds"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    inverse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class SemanticProvider(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A cloud/infrastructure provider (Proxmox, AWS, Azure, etc.)."""

    __tablename__ = "semantic_providers"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="custom")
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    documentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
