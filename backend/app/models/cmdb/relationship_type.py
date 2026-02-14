"""
Overview: Relationship type model — defines the kinds of edges between CIs and activities.
Architecture: System + custom relationship types for the CI graph (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Relationship types have a name and inverse_name for bidirectional semantics
    (e.g. contains/contained_by). Domain (infrastructure/operational/both) distinguishes
    CI-to-CI vs activity-to-CI edges. Source/target entity type, semantic type, and
    semantic category constraints restrict which entities may participate.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class RelationshipType(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A type of relationship between CIs and/or activities."""

    __tablename__ = "relationship_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    inverse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_class_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_class_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # Domain and entity constraints (added in migration 030)
    domain: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="infrastructure"
    )
    source_entity_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ci"
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ci"
    )
    source_semantic_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_semantic_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_semantic_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_semantic_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
