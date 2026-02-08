"""
Overview: Notification template model for Jinja2-based message rendering per channel.
Architecture: Notification template data layer (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base, app.models.notification
Concepts: Notification templates, Jinja2 rendering, tenant/system template inheritance
"""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin
from app.models.notification import NotificationCategory, NotificationChannel


class NotificationTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Jinja2 template for rendering notifications per category/event/channel.

    tenant_id=NULL means a system-level default template.
    Tenant-specific templates override system templates for the same
    (category, event_type, channel) combination.
    """

    __tablename__ = "notification_templates"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, name="notification_category", create_constraint=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", create_constraint=True),
        nullable=False,
    )
    subject_template: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        Index(
            "ix_notification_templates_unique_active",
            "tenant_id", "category", "event_type", "channel",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )
