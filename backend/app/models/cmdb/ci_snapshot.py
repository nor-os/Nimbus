"""
Overview: CI snapshot model — versioned point-in-time captures of configuration item state.
Architecture: Append-only snapshot history for CI versioning (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Each snapshot captures the full CI state (attributes, tags, lifecycle, compartment)
    at a specific version number. Snapshots are immutable and support point-in-time queries.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin


class CISnapshot(Base, IDMixin):
    """An immutable snapshot of a CI at a point in time."""

    __tablename__ = "ci_snapshots"

    ci_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration_items.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    change_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="update"
    )

    __table_args__ = (
        UniqueConstraint("ci_id", "version_number", name="uq_ci_snapshot_ci_version"),
    )
