"""
Overview: Stack reservation service — DR capacity reservations and sync policies.
Architecture: Service layer for stack DR management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.stack_reservation
Concepts: DR reservations (hot/warm/cold standby, pilot light), sync policies,
    failover testing with RTO/RPO tracking.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.stack_reservation import ReservationSyncPolicy, StackReservation

logger = logging.getLogger(__name__)


class StackReservationServiceError(Exception):
    def __init__(self, message: str, code: str = "RESERVATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StackReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_reservation(
        self, tenant_id: str, data: dict
    ) -> StackReservation:
        """Create a DR capacity reservation."""
        reservation = StackReservation(
            stack_instance_id=data["stack_instance_id"],
            tenant_id=tenant_id,
            reservation_type=data["reservation_type"],
            target_environment_id=data.get("target_environment_id"),
            target_provider_id=data.get("target_provider_id"),
            reserved_resources=data.get("reserved_resources"),
            rto_seconds=data.get("rto_seconds"),
            rpo_seconds=data.get("rpo_seconds"),
            status="PENDING",
            cost_per_hour=data.get("cost_per_hour"),
        )
        self.db.add(reservation)
        await self.db.flush()
        return reservation

    async def update_reservation(
        self, reservation_id: uuid.UUID, tenant_id: str, data: dict
    ) -> StackReservation:
        """Update a DR reservation."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")

        for key in ("reservation_type", "target_environment_id", "target_provider_id",
                     "reserved_resources", "rto_seconds", "rpo_seconds", "cost_per_hour",
                     "status"):
            if key in data:
                setattr(reservation, key, data[key])

        await self.db.flush()
        return reservation

    async def claim_reservation(
        self, reservation_id: uuid.UUID, tenant_id: str
    ) -> StackReservation:
        """Claim a DR reservation (activate failover)."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")
        if reservation.status != "ACTIVE":
            raise StackReservationServiceError(
                f"Cannot claim from status {reservation.status}", "INVALID_STATUS"
            )
        reservation.status = "CLAIMED"
        await self.db.flush()
        return reservation

    async def release_reservation(
        self, reservation_id: uuid.UUID, tenant_id: str
    ) -> StackReservation:
        """Release a claimed DR reservation."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")
        if reservation.status != "CLAIMED":
            raise StackReservationServiceError(
                f"Cannot release from status {reservation.status}", "INVALID_STATUS"
            )
        reservation.status = "ACTIVE"
        await self.db.flush()
        return reservation

    async def record_test_result(
        self, reservation_id: uuid.UUID, tenant_id: str, test_result: str
    ) -> StackReservation:
        """Record a failover test result."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")
        reservation.last_tested_at = datetime.now(UTC)
        reservation.test_result = test_result
        await self.db.flush()
        return reservation

    async def get_reservation(
        self, reservation_id: uuid.UUID, tenant_id: str
    ) -> StackReservation | None:
        """Get a reservation with sync policies."""
        result = await self.db.execute(
            select(StackReservation)
            .where(
                StackReservation.id == reservation_id,
                StackReservation.tenant_id == tenant_id,
                StackReservation.deleted_at.is_(None),
            )
            .options(selectinload(StackReservation.sync_policies))
        )
        return result.scalar_one_or_none()

    async def list_reservations(
        self,
        tenant_id: str,
        stack_instance_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StackReservation], int]:
        """List reservations with pagination and filtering."""
        base = select(StackReservation).where(
            StackReservation.tenant_id == tenant_id,
            StackReservation.deleted_at.is_(None),
        )

        if stack_instance_id:
            base = base.where(StackReservation.stack_instance_id == stack_instance_id)
        if status:
            base = base.where(StackReservation.status == status)

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        query = (
            base
            .options(selectinload(StackReservation.sync_policies))
            .order_by(StackReservation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all()), total

    # ── Sync Policies ─────────────────────────────────────────────────

    async def add_sync_policy(
        self, reservation_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ReservationSyncPolicy:
        """Add a sync policy to a reservation."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")

        policy = ReservationSyncPolicy(
            reservation_id=reservation.id,
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            sync_method=data["sync_method"],
            sync_interval_seconds=data.get("sync_interval_seconds"),
            sync_workflow_id=data.get("sync_workflow_id"),
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def update_sync_policy(
        self, policy_id: uuid.UUID, reservation_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ReservationSyncPolicy:
        """Update a sync policy."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")

        result = await self.db.execute(
            select(ReservationSyncPolicy).where(
                ReservationSyncPolicy.id == policy_id,
                ReservationSyncPolicy.reservation_id == reservation_id,
                ReservationSyncPolicy.deleted_at.is_(None),
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise StackReservationServiceError("Sync policy not found", "POLICY_NOT_FOUND")

        for key in ("sync_method", "sync_interval_seconds", "sync_workflow_id"):
            if key in data:
                setattr(policy, key, data[key])

        await self.db.flush()
        return policy

    async def remove_sync_policy(
        self, policy_id: uuid.UUID, reservation_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a sync policy."""
        reservation = await self.get_reservation(reservation_id, tenant_id)
        if not reservation:
            raise StackReservationServiceError("Reservation not found", "NOT_FOUND")

        result = await self.db.execute(
            select(ReservationSyncPolicy).where(
                ReservationSyncPolicy.id == policy_id,
                ReservationSyncPolicy.reservation_id == reservation_id,
                ReservationSyncPolicy.deleted_at.is_(None),
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise StackReservationServiceError("Sync policy not found", "POLICY_NOT_FOUND")

        policy.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
