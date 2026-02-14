"""
Overview: Policy library model — reusable IAM policy definitions with parameterizable statements.
Architecture: Data model for governance policy library (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Policy library entries store abstract IAM policy statements using semantic actions/resources.
    Statements use effect/actions/resources/principals/condition structure. Variables enable
    parameterization via {{var}} placeholders substituted before ABAC evaluation.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class PolicyCategory(str, enum.Enum):
    IAM = "IAM"
    NETWORK = "NETWORK"
    ENCRYPTION = "ENCRYPTION"
    TAGGING = "TAGGING"
    COST = "COST"


class PolicySeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class PolicyLibraryEntry(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A reusable policy definition with parameterizable statements."""

    __tablename__ = "policy_library"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[PolicyCategory] = mapped_column(
        Enum(
            PolicyCategory,
            name="policy_category",
            create_constraint=True,
        ),
        nullable=False,
    )
    statements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[PolicySeverity] = mapped_column(
        Enum(
            PolicySeverity,
            name="policy_severity",
            create_constraint=True,
        ),
        nullable=False,
        server_default="MEDIUM",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    tags: Mapped[list | None] = mapped_column(ARRAY(String(100)), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name",
            name="uq_policy_library_tenant_name",
        ),
        Index("ix_policy_library_tenant", "tenant_id"),
        Index("ix_policy_library_category", "tenant_id", "category"),
        Index("ix_policy_library_created_by", "created_by"),
    )
