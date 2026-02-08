"""
Overview: Webhook configuration model for tenant-level event delivery endpoints.
Architecture: Webhook data layer (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Webhooks, event delivery, authentication types, event filtering, batching
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class WebhookAuthType(enum.StrEnum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BASIC = "BASIC"
    BEARER = "BEARER"


class WebhookConfig(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Tenant-level webhook endpoint configuration with auth and event filtering."""

    __tablename__ = "webhook_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    auth_type: Mapped[WebhookAuthType] = mapped_column(
        Enum(WebhookAuthType, name="webhook_auth_type", create_constraint=True),
        nullable=False,
        server_default="NONE",
    )
    auth_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    event_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    batch_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        Index("ix_webhook_configs_tenant", "tenant_id"),
        Index("ix_webhook_configs_active", "tenant_id", "is_active"),
    )
