"""
Overview: Saved search model — persisted CMDB search queries for reuse.
Architecture: User-scoped saved searches within tenant context (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Users can save frequently used search queries with their filters and sorting
    preferences for quick reuse.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class SavedSearch(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A saved CMDB search query."""

    __tablename__ = "saved_searches"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
