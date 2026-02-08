"""
Overview: Role model for RBAC with inheritance, scoped roles, and soft delete.
Architecture: Role-based access control with hierarchical roles (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, roles, role inheritance, scoped roles (provider/tenant)
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Role(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "roles"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="tenant"
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parent_role: Mapped["Role | None"] = relationship(
        remote_side="Role.id", back_populates="child_roles"
    )
    child_roles: Mapped[list["Role"]] = relationship(back_populates="parent_role")
