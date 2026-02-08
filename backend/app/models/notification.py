"""
Overview: Notification model and shared enums for the notification subsystem.
Architecture: Notification data layer (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: In-app notifications, notification categories, multi-channel delivery
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class NotificationCategory(enum.StrEnum):
    APPROVAL = "APPROVAL"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AUDIT = "AUDIT"
    DRIFT = "DRIFT"
    WORKFLOW = "WORKFLOW"
    USER = "USER"


class NotificationChannel(enum.StrEnum):
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"


class Notification(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """In-app notification delivered to a specific user."""

    __tablename__ = "notifications"

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
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_resource_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    read_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notifications_tenant_user", "tenant_id", "user_id"),
        Index("ix_notifications_category", "category"),
        Index("ix_notifications_is_read", "tenant_id", "user_id", "is_read"),
        Index("ix_notifications_created", "tenant_id", "created_at"),
    )
