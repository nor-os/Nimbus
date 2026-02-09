"""
Overview: Approval policy model — per-tenant, per-operation approval chain configuration.
Architecture: Data model for approval workflow configuration (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Approval chains, chain modes (sequential/parallel/quorum), tenant isolation
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ApprovalChainMode(str, enum.Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    QUORUM = "QUORUM"


class ApprovalPolicy(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-tenant configuration defining how approvals work for a given operation type."""

    __tablename__ = "approval_policies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    chain_mode: Mapped[ApprovalChainMode] = mapped_column(
        Enum(ApprovalChainMode, name="approval_chain_mode", create_constraint=True),
        nullable=False,
    )
    quorum_required: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    timeout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1440")
    escalation_user_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approver_role_names: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approver_user_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approver_group_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "operation_type",
            name="uq_approval_policy_tenant_op",
        ),
        Index("ix_approval_policies_tenant", "tenant_id"),
        Index("ix_approval_policies_operation", "tenant_id", "operation_type"),
    )
