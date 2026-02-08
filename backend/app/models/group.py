"""
Overview: Group model for organizing users within a tenant.
Architecture: Group entity with many-to-many group membership (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, groups, flat group model, many-to-many nesting, multi-tenancy
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Group(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "groups"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    member_of: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        foreign_keys="GroupMembership.child_group_id",
        cascade="all, delete-orphan",
    )
    group_members: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        foreign_keys="GroupMembership.parent_group_id",
        cascade="all, delete-orphan",
    )
