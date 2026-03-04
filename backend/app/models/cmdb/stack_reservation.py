"""
Overview: Stack reservation models — DR capacity reservations and sync policies.
Architecture: CMDB stack DR layer (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: DR reservations, failover capacity, sync policies, RTO/RPO tracking.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────


class ReservationType(str, enum.Enum):
    HOT_STANDBY = "HOT_STANDBY"
    WARM_STANDBY = "WARM_STANDBY"
    COLD_STANDBY = "COLD_STANDBY"
    PILOT_LIGHT = "PILOT_LIGHT"


class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class SyncMethod(str, enum.Enum):
    REAL_TIME = "REAL_TIME"
    SCHEDULED = "SCHEDULED"
    ON_DEMAND = "ON_DEMAND"
    WORKFLOW = "WORKFLOW"


class TestResult(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NOT_TESTED = "NOT_TESTED"


# ── Models ────────────────────────────────────────────────────────────


class StackReservation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """DR capacity reservation for a stack instance."""

    __tablename__ = "stack_reservations"

    stack_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stack_instances.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    reservation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    target_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=True
    )
    reserved_resources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rto_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpo_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING", nullable=False)
    cost_per_hour: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    test_result: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    sync_policies: Mapped[list["ReservationSyncPolicy"]] = relationship(
        back_populates="reservation", lazy="selectin", cascade="all, delete-orphan"
    )


class ReservationSyncPolicy(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Sync configuration for a DR reservation's components."""

    __tablename__ = "reservation_sync_policies"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stack_reservations.id"), nullable=False, index=True
    )
    source_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sync_method: Mapped[str] = mapped_column(String(30), nullable=False)
    sync_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_lag_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reservation: Mapped["StackReservation"] = relationship(back_populates="sync_policies")
