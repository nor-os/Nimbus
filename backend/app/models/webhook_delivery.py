"""
Overview: Webhook delivery record model for tracking payload dispatch and retry state.
Architecture: Webhook delivery data layer (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Webhook delivery, retry logic, dead letter queue, delivery status tracking
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class WebhookDeliveryStatus(enum.StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class WebhookDelivery(Base, IDMixin, TimestampMixin):
    """Individual webhook delivery attempt record. No SoftDeleteMixin — deliveries are immutable."""

    __tablename__ = "webhook_deliveries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    webhook_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_configs.id"), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus, name="webhook_delivery_status", create_constraint=True),
        nullable=False,
        server_default="PENDING",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    last_attempt_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_webhook_deliveries_config", "webhook_config_id"),
        Index("ix_webhook_deliveries_status", "tenant_id", "status"),
        Index("ix_webhook_deliveries_next_retry", "status", "next_retry_at"),
    )
