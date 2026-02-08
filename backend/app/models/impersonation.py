"""
Overview: Impersonation session model for tracking standard and override impersonation.
Architecture: Data model for impersonation lifecycle (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Impersonation, immutable audit artifact, override mode, session lifecycle
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class ImpersonationMode(str, enum.Enum):
    STANDARD = "STANDARD"
    OVERRIDE = "OVERRIDE"


class ImpersonationStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ImpersonationSession(Base, IDMixin, TimestampMixin):
    """Immutable impersonation session record. No SoftDeleteMixin — full audit artifact."""

    __tablename__ = "impersonation_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    mode: Mapped[ImpersonationMode] = mapped_column(
        Enum(ImpersonationMode, name="impersonation_mode", create_constraint=True),
        nullable=False,
    )
    status: Mapped[ImpersonationStatus] = mapped_column(
        Enum(ImpersonationStatus, name="impersonation_status", create_constraint=True),
        nullable=False,
        server_default="PENDING_APPROVAL",
    )

    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approval_decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    original_password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    token_jti: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_impersonation_sessions_tenant", "tenant_id"),
        Index("ix_impersonation_sessions_requester", "requester_id"),
        Index("ix_impersonation_sessions_target", "target_user_id"),
        Index("ix_impersonation_sessions_status", "status"),
        Index("ix_impersonation_sessions_workflow", "workflow_id"),
    )
