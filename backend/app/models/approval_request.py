"""
Overview: Approval request model — one per approval workflow instance, immutable audit artifact.
Architecture: Data model for approval request tracking (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Approval lifecycle, workflow correlation, policy snapshot, immutable records
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class ApprovalRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalRequest(Base, IDMixin, TimestampMixin):
    """Immutable approval request record. No SoftDeleteMixin — full audit artifact."""

    __tablename__ = "approval_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    workflow_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parent_workflow_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chain_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    quorum_required: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[ApprovalRequestStatus] = mapped_column(
        Enum(ApprovalRequestStatus, name="approval_request_status", create_constraint=True),
        nullable=False,
        server_default="PENDING",
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    steps = relationship("ApprovalStep", back_populates="request", lazy="selectin")

    __table_args__ = (
        Index("ix_approval_requests_tenant", "tenant_id"),
        Index("ix_approval_requests_requester", "requester_id"),
        Index("ix_approval_requests_status", "tenant_id", "status"),
        Index("ix_approval_requests_workflow", "workflow_id"),
        Index("ix_approval_requests_parent_workflow", "parent_workflow_id"),
        Index("ix_approval_requests_operation", "tenant_id", "operation_type"),
    )
