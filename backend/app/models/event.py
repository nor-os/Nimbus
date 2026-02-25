"""
Overview: Event system models — event types, subscriptions, log, and delivery tracking.
Architecture: Event bus data layer (Section 11.6)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Event-driven architecture, subscription-based dispatch, delivery tracking
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EventHandlerType(str, enum.Enum):
    INTERNAL = "INTERNAL"
    WORKFLOW = "WORKFLOW"
    NOTIFICATION = "NOTIFICATION"
    ACTIVITY = "ACTIVITY"
    WEBHOOK = "WEBHOOK"


class EventDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class EventCategory(str, enum.Enum):
    AUTHENTICATION = "AUTHENTICATION"
    APPROVAL = "APPROVAL"
    DEPLOYMENT = "DEPLOYMENT"
    ENVIRONMENT = "ENVIRONMENT"
    CMDB = "CMDB"
    AUTOMATION = "AUTOMATION"
    WORKFLOW = "WORKFLOW"
    CUSTOM = "CUSTOM"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class EventType(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A registered event type that can be emitted and subscribed to."""

    __tablename__ = "event_types"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_validators: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # Relationships
    subscriptions: Mapped[list["EventSubscription"]] = relationship(
        back_populates="event_type", lazy="selectin"
    )


class EventSubscription(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A subscription that triggers a handler when a matching event fires."""

    __tablename__ = "event_subscriptions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    event_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_types.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    handler_type: Mapped[str] = mapped_column(String(20), nullable=False)
    handler_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    filter_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # Relationships
    event_type: Mapped["EventType"] = relationship(back_populates="subscriptions")


class EventLog(Base, IDMixin):
    """An immutable record of a single event emission."""

    __tablename__ = "event_log"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    event_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_types.id"), nullable=False
    )
    event_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    emitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    emitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    deliveries: Mapped[list["EventDelivery"]] = relationship(
        back_populates="event_log", lazy="selectin"
    )


class EventDelivery(Base, IDMixin):
    """Per-subscription dispatch tracking for an event."""

    __tablename__ = "event_deliveries"

    event_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_log.id"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_subscriptions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDING"
    )
    handler_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    # Relationships
    event_log: Mapped["EventLog"] = relationship(back_populates="deliveries")
