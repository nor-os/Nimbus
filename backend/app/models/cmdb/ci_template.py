"""
Overview: CI template model — reusable templates for creating configuration items.
Architecture: Templates store pre-filled attributes and relationship blueprints (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Templates accelerate CI creation by pre-populating attributes, tags, and relationship
    templates. Constraints define validation rules for template instantiation.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CITemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A reusable template for creating CIs."""

    __tablename__ = "ci_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ci_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=False
    )
    attributes: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    tags: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    relationship_templates: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )

    ci_class: Mapped["CIClass"] = relationship(lazy="joined")  # noqa: F821
