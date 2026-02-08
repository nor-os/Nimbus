"""
Overview: Junction table linking groups to roles.
Architecture: Group-role assignment for inherited permissions (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, group-role assignment, permission inheritance
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class GroupRole(Base, IDMixin, TimestampMixin):
    __tablename__ = "group_roles"
    __table_args__ = (
        UniqueConstraint("group_id", "role_id", name="uq_group_role"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True
    )
