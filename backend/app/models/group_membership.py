"""
Overview: Group membership model for many-to-many group-in-group relationships.
Architecture: Junction table for group hierarchy (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, group nesting, many-to-many membership
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class GroupMembership(Base, IDMixin, TimestampMixin):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("parent_group_id", "child_group_id"),
        CheckConstraint("parent_group_id != child_group_id"),
    )

    parent_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    child_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
