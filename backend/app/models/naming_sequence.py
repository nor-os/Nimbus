"""
Overview: NamingSequence model — durable counters for the naming resolver.
Architecture: Resolver data layer (Section 11)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Each row tracks a per-scope auto-increment counter used by the naming resolver.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class NamingSequence(Base, IDMixin, TimestampMixin):
    __tablename__ = "naming_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    scope_key: Mapped[str] = mapped_column(String(512), nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint("tenant_id", "scope_key", name="uq_naming_sequences_tenant_scope"),
    )
