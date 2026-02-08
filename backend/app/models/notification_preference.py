"""
Overview: Per-user notification preference model for channel opt-in/opt-out per category.
Architecture: Notification preferences data layer (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base, app.models.notification
Concepts: Notification preferences, per-user channel control, category-based routing
"""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin
from app.models.notification import NotificationCategory, NotificationChannel


class NotificationPreference(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-user channel preference for a notification category."""

    __tablename__ = "notification_preferences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, name="notification_category", create_constraint=True),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", create_constraint=True),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "category", "channel",
            name="uq_notification_pref_user_cat_chan",
        ),
    )
