"""
Overview: Tenant tag model — per-tenant key-value configuration with JSON Schema validation.
Architecture: Tenant configuration layer (Section 3.2)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Tags provide typed configuration indirection. Stack parameter overrides can reference
    tag keys, enabling environment-variable-like configuration across topology deployments.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class TenantTag(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A tenant-scoped configuration tag with optional JSON Schema validation."""

    __tablename__ = "tenant_tags"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_schema: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="JSON Schema for value validation"
    )
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_tag_key"),
    )
