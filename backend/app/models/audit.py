"""
Overview: Audit log data models for immutable event recording with hash chain integrity.
Architecture: Audit logging data layer (Section 4, 8)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Immutable audit logs, hash chain, retention policies, redaction rules, saved queries, event taxonomy
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    BREAK_GLASS = "BREAK_GLASS"
    EXPORT = "EXPORT"
    ARCHIVE = "ARCHIVE"
    SYSTEM = "SYSTEM"
    IMPERSONATE = "IMPERSONATE"
    OVERRIDE = "OVERRIDE"


class AuditPriority(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERR = "ERR"
    CRITICAL = "CRITICAL"


class EventCategory(str, enum.Enum):
    API = "API"
    AUTH = "AUTH"
    DATA = "DATA"
    PERMISSION = "PERMISSION"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    TENANT = "TENANT"
    USER = "USER"


class ActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"
    ANONYMOUS = "ANONYMOUS"


class AuditLog(Base, IDMixin, TimestampMixin):
    """Immutable audit log entry with hash chain integrity. No SoftDeleteMixin."""

    __tablename__ = "audit_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Legacy action (deprecated, still populated for backward compatibility)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", create_constraint=True),
        nullable=False,
    )

    # New taxonomy fields
    event_category: Mapped[EventCategory | None] = mapped_column(
        Enum(EventCategory, name="audit_event_category", create_constraint=True),
        nullable=True,
    )
    event_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[ActorType | None] = mapped_column(
        Enum(ActorType, name="audit_actor_type", create_constraint=True),
        nullable=True,
    )
    impersonator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    resource_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    priority: Mapped[AuditPriority] = mapped_column(
        Enum(AuditPriority, name="audit_priority", create_constraint=True),
        nullable=False,
        server_default="INFO",
    )

    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Request context fields
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    request_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    archived_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor", "actor_id"),
        Index("ix_audit_logs_event_category", "event_category"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_actor_type", "actor_type"),
    )


class RetentionPolicy(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-tenant audit log retention configuration."""

    __tablename__ = "retention_policies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True
    )
    hot_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    cold_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="365")
    archive_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class RedactionRule(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Regex-based field redaction rule for audit log data."""

    __tablename__ = "redaction_rules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    field_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    replacement: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="[REDACTED]"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SavedQuery(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """User-saved audit log query for quick access."""

    __tablename__ = "saved_queries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
