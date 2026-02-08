"""
Overview: Permission override model for explicit deny entries on permissions.
Architecture: Deny override layer in permission resolution (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, explicit deny, permission overrides, principal-scoped deny
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class PermissionOverride(Base, IDMixin, TimestampMixin):
    __tablename__ = "permission_overrides"
    __table_args__ = (
        UniqueConstraint("tenant_id", "permission_id", "principal_type", "principal_id"),
        CheckConstraint(
            "principal_type IN ('user', 'group', 'role')",
            name="ck_perm_overrides_principal_type",
        ),
        CheckConstraint("effect IN ('deny')", name="ck_perm_overrides_effect"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False
    )
    principal_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    effect: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default="deny"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
