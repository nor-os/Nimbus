"""
Overview: User model for authentication and identity.
Architecture: Core auth entity, linked to provider (Section 4.2, 5.1)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Authentication, multi-tenancy, soft delete, SSO external identity
"""

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_active", "email", unique=True, postgresql_where="deleted_at IS NULL"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False
    )
    identity_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_providers.id"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    provider: Mapped["Provider"] = relationship(back_populates="users")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")  # noqa: F821
    user_tenants: Mapped[list["UserTenant"]] = relationship(back_populates="user")  # noqa: F821
