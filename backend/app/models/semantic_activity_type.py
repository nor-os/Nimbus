"""
Overview: Semantic activity type model — abstract activity archetypes for service delivery.
Architecture: Semantic layer activity classification (Section 5)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Semantic activity types define abstract categories of operational activities
    (provisioning, backup, patching, etc.) with applicable semantic category/type constraints.
    Each type has a default relationship kind FK to relationship_types.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class SemanticActivityType(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An abstract activity archetype for operational processes."""

    __tablename__ = "semantic_activity_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applicable_semantic_categories: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )
    applicable_semantic_types: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )
    default_relationship_kind_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relationship_types.id"),
        nullable=True,
    )
    properties_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    default_relationship_kind = relationship(
        "RelationshipType", lazy="joined"
    )
