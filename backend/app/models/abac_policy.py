"""
Overview: ABAC policy model for attribute-based access control rules.
Architecture: ABAC policy entity with DSL expressions (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: ABAC, access control policies, DSL expressions, multi-tenancy
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class PolicyEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class ABACPolicy(Base, IDMixin, TimestampMixin):
    __tablename__ = "abac_policies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    effect: Mapped[PolicyEffect] = mapped_column(
        Enum(
            PolicyEffect,
            name="policy_effect_enum",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_permission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=True
    )
