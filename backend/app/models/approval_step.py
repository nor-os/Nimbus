"""
Overview: Approval step model — one per approver in a chain, immutable audit artifact.
Architecture: Data model for individual approval decisions (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Approval chain steps, delegation, per-approver decisions, immutable records
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class ApprovalStepStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELEGATED = "DELEGATED"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"


class ApprovalStep(Base, IDMixin, TimestampMixin):
    """Immutable approval step record. No SoftDeleteMixin — full audit artifact."""

    __tablename__ = "approval_steps"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    delegate_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[ApprovalStepStatus] = mapped_column(
        Enum(ApprovalStepStatus, name="approval_step_status", create_constraint=True),
        nullable=False,
        server_default="PENDING",
    )
    decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    request = relationship("ApprovalRequest", back_populates="steps")

    __table_args__ = (
        Index("ix_approval_steps_request", "approval_request_id"),
        Index("ix_approval_steps_approver", "approver_id"),
        Index("ix_approval_steps_tenant_approver", "tenant_id", "approver_id", "status"),
        Index("ix_approval_steps_delegate", "delegate_to_id"),
    )
