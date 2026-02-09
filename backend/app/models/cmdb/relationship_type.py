"""
Overview: Relationship type model — defines the kinds of edges between CIs.
Architecture: System + custom relationship types for the CI graph (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Relationship types have a name and inverse_name for bidirectional semantics
    (e.g. contains/contained_by). Source/target class constraints restrict which CI classes
    may participate.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class RelationshipType(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A type of relationship between CIs."""

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
