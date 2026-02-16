"""
Overview: IPAM service — address space CRUD, hierarchical allocation, IP reservation, utilization tracking.
Architecture: IPAM service layer (Section 6)
Dependencies: sqlalchemy, app.models.ipam, app.services.ipam.validation
Concepts: CIDR allocation, overlap detection, hierarchical address management, utilization tracking
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ipam import (
    AddressAllocation,
    AddressSpace,
    AddressSpaceStatus,
    AllocationStatus,
    AllocationType,
    IpReservation,
    ReservationStatus,
)
from app.services.ipam.validation import (
    calculate_usable_ips,
    find_overlaps,
    ip_in_cidr,
    is_contained_in,
    next_available_block,
    validate_cidr,
)

logger = logging.getLogger(__name__)


class IpamService:
    """Service for IP Address Management — address spaces, allocations, and reservations."""

    # ------------------------------------------------------------------ #
    # Address Space CRUD
    # ------------------------------------------------------------------ #

    async def create_address_space(
        self,
        db: AsyncSession,
        landing_zone_id: uuid.UUID,
        name: str,
        cidr: str,
        *,
        region_id: uuid.UUID | None = None,
        description: str | None = None,
        ip_version: int = 4,
    ) -> AddressSpace:
        """Create a new address space after validating CIDR and checking for overlaps."""
        validate_cidr(cidr)

        # Check for overlapping address spaces within the same landing zone
        result = await db.execute(
            select(AddressSpace.cidr).where(
                AddressSpace.landing_zone_id == landing_zone_id,
                AddressSpace.deleted_at.is_(None),
            )
        )
        existing_cidrs = list(result.scalars().all())

        overlaps = find_overlaps(cidr, existing_cidrs)
        if overlaps:
            raise ValueError(
                f"CIDR {cidr} overlaps with existing address spaces: {', '.join(overlaps)}"
            )

        space = AddressSpace(
            landing_zone_id=landing_zone_id,
            region_id=region_id,
            name=name,
            description=description,
            cidr=cidr,
            ip_version=ip_version,
            status=AddressSpaceStatus.ACTIVE,
        )
        db.add(space)
        await db.flush()
        return space

    async def get_address_space(
        self,
        db: AsyncSession,
        space_id: uuid.UUID,
    ) -> AddressSpace | None:
        """Get an address space by ID."""
        result = await db.execute(
            select(AddressSpace).where(
                AddressSpace.id == space_id,
                AddressSpace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_address_spaces(
        self,
        db: AsyncSession,
        landing_zone_id: uuid.UUID,
    ) -> list[AddressSpace]:
        """List all address spaces for a landing zone."""
        result = await db.execute(
            select(AddressSpace)
            .where(
                AddressSpace.landing_zone_id == landing_zone_id,
                AddressSpace.deleted_at.is_(None),
            )
            .order_by(AddressSpace.created_at)
        )
        return list(result.scalars().all())

    async def delete_address_space(
        self,
        db: AsyncSession,
        space_id: uuid.UUID,
    ) -> None:
        """Soft-delete an address space."""
        result = await db.execute(
            select(AddressSpace).where(
                AddressSpace.id == space_id,
                AddressSpace.deleted_at.is_(None),
            )
        )
        space = result.scalar_one_or_none()
        if not space:
            raise ValueError(f"Address space '{space_id}' not found")

        space.deleted_at = func.now()
        await db.flush()

    # ------------------------------------------------------------------ #
    # Allocation CRUD with hierarchy
    # ------------------------------------------------------------------ #

    async def allocate_block(
        self,
        db: AsyncSession,
        address_space_id: uuid.UUID,
        name: str,
        cidr: str,
        allocation_type: AllocationType,
        *,
        parent_allocation_id: uuid.UUID | None = None,
        tenant_environment_id: uuid.UUID | None = None,
        purpose: str | None = None,
        description: str | None = None,
    ) -> AddressAllocation:
        """Allocate a CIDR block within an address space, optionally under a parent allocation."""
        validate_cidr(cidr)

        # Fetch the address space
        space = await self.get_address_space(db, address_space_id)
        if not space:
            raise ValueError(f"Address space '{address_space_id}' not found")

        # Verify allocation fits within address space
        if not is_contained_in(cidr, space.cidr):
            raise ValueError(
                f"Allocation CIDR {cidr} is not contained within address space CIDR {space.cidr}"
            )

        # If parent allocation specified, verify containment
        if parent_allocation_id:
            parent = await self.get_allocation(db, parent_allocation_id)
            if not parent:
                raise ValueError(f"Parent allocation '{parent_allocation_id}' not found")
            if not is_contained_in(cidr, parent.cidr):
                raise ValueError(
                    f"Allocation CIDR {cidr} is not contained within parent CIDR {parent.cidr}"
                )

        # Check for overlapping sibling allocations
        sibling_query = select(AddressAllocation.cidr).where(
            AddressAllocation.address_space_id == address_space_id,
            AddressAllocation.parent_allocation_id == parent_allocation_id,
            AddressAllocation.deleted_at.is_(None),
        )
        result = await db.execute(sibling_query)
        existing_cidrs = list(result.scalars().all())

        overlaps = find_overlaps(cidr, existing_cidrs)
        if overlaps:
            raise ValueError(
                f"Allocation CIDR {cidr} overlaps with existing allocations: {', '.join(overlaps)}"
            )

        allocation = AddressAllocation(
            address_space_id=address_space_id,
            parent_allocation_id=parent_allocation_id,
            tenant_environment_id=tenant_environment_id,
            name=name,
            description=description,
            cidr=cidr,
            allocation_type=allocation_type,
            status=AllocationStatus.PLANNED,
            purpose=purpose,
        )
        db.add(allocation)
        await db.flush()
        return allocation

    async def get_allocation(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
    ) -> AddressAllocation | None:
        """Get an allocation by ID."""
        result = await db.execute(
            select(AddressAllocation).where(
                AddressAllocation.id == allocation_id,
                AddressAllocation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_allocations(
        self,
        db: AsyncSession,
        address_space_id: uuid.UUID,
        *,
        parent_id: uuid.UUID | None = None,
    ) -> list[AddressAllocation]:
        """List allocations for an address space, optionally filtered by parent.

        When parent_id is None, returns top-level allocations only.
        """
        result = await db.execute(
            select(AddressAllocation)
            .where(
                AddressAllocation.address_space_id == address_space_id,
                AddressAllocation.parent_allocation_id == parent_id,
                AddressAllocation.deleted_at.is_(None),
            )
            .order_by(AddressAllocation.cidr)
        )
        return list(result.scalars().all())

    async def update_allocation_status(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
        status: AllocationStatus,
    ) -> AddressAllocation:
        """Update the status of an allocation."""
        allocation = await self.get_allocation(db, allocation_id)
        if not allocation:
            raise ValueError(f"Allocation '{allocation_id}' not found")

        allocation.status = status
        await db.flush()
        return allocation

    async def release_allocation(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
    ) -> None:
        """Release an allocation — sets status to RELEASED and soft-deletes."""
        allocation = await self.get_allocation(db, allocation_id)
        if not allocation:
            raise ValueError(f"Allocation '{allocation_id}' not found")

        allocation.status = AllocationStatus.RELEASED
        allocation.deleted_at = func.now()
        await db.flush()

    async def suggest_next_block(
        self,
        db: AsyncSession,
        address_space_id: uuid.UUID,
        prefix_length: int,
        *,
        parent_allocation_id: uuid.UUID | None = None,
    ) -> str | None:
        """Suggest the next available CIDR block of the given prefix length.

        Searches within the parent allocation if specified, otherwise within
        the address space itself.
        """
        # Determine the parent CIDR
        if parent_allocation_id:
            parent = await self.get_allocation(db, parent_allocation_id)
            if not parent:
                raise ValueError(f"Parent allocation '{parent_allocation_id}' not found")
            parent_cidr = parent.cidr
        else:
            space = await self.get_address_space(db, address_space_id)
            if not space:
                raise ValueError(f"Address space '{address_space_id}' not found")
            parent_cidr = space.cidr

        # Get existing children CIDRs
        result = await db.execute(
            select(AddressAllocation.cidr).where(
                AddressAllocation.address_space_id == address_space_id,
                AddressAllocation.parent_allocation_id == parent_allocation_id,
                AddressAllocation.deleted_at.is_(None),
            )
        )
        existing_cidrs = list(result.scalars().all())

        return next_available_block(parent_cidr, existing_cidrs, prefix_length)

    # ------------------------------------------------------------------ #
    # IP Reservation
    # ------------------------------------------------------------------ #

    async def reserve_ip(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
        ip_address: str,
        purpose: str,
        reserved_by: uuid.UUID,
        *,
        hostname: str | None = None,
        ci_id: uuid.UUID | None = None,
    ) -> IpReservation:
        """Reserve a specific IP address within a subnet allocation."""
        allocation = await self.get_allocation(db, allocation_id)
        if not allocation:
            raise ValueError(f"Allocation '{allocation_id}' not found")

        if allocation.allocation_type != AllocationType.SUBNET:
            raise ValueError(
                f"IP reservations are only allowed in SUBNET allocations, "
                f"got {allocation.allocation_type.value}"
            )

        if not ip_in_cidr(ip_address, allocation.cidr):
            raise ValueError(
                f"IP address {ip_address} is not within allocation CIDR {allocation.cidr}"
            )

        # Check for duplicate reservation
        result = await db.execute(
            select(IpReservation).where(
                IpReservation.allocation_id == allocation_id,
                IpReservation.ip_address == ip_address,
                IpReservation.deleted_at.is_(None),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(
                f"IP address {ip_address} is already reserved in allocation '{allocation_id}'"
            )

        reservation = IpReservation(
            allocation_id=allocation_id,
            ip_address=ip_address,
            hostname=hostname,
            purpose=purpose,
            ci_id=ci_id,
            status=ReservationStatus.RESERVED,
            reserved_by=reserved_by,
        )
        db.add(reservation)
        await db.flush()
        return reservation

    async def list_reservations(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
    ) -> list[IpReservation]:
        """List all active IP reservations for an allocation."""
        result = await db.execute(
            select(IpReservation)
            .where(
                IpReservation.allocation_id == allocation_id,
                IpReservation.deleted_at.is_(None),
            )
            .order_by(IpReservation.ip_address)
        )
        return list(result.scalars().all())

    async def release_reservation(
        self,
        db: AsyncSession,
        reservation_id: uuid.UUID,
    ) -> None:
        """Release an IP reservation — sets status to RELEASED and soft-deletes."""
        result = await db.execute(
            select(IpReservation).where(
                IpReservation.id == reservation_id,
                IpReservation.deleted_at.is_(None),
            )
        )
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise ValueError(f"Reservation '{reservation_id}' not found")

        reservation.status = ReservationStatus.RELEASED
        reservation.deleted_at = func.now()
        await db.flush()

    # ------------------------------------------------------------------ #
    # Utilization
    # ------------------------------------------------------------------ #

    async def calculate_utilization(
        self,
        db: AsyncSession,
        allocation_id: uuid.UUID,
    ) -> float:
        """Calculate and update the utilization percentage for an allocation.

        Utilization is defined as the ratio of IP addresses consumed by child
        allocations to the total usable IPs in the parent allocation.
        """
        allocation = await self.get_allocation(db, allocation_id)
        if not allocation:
            raise ValueError(f"Allocation '{allocation_id}' not found")

        parent_usable = calculate_usable_ips(allocation.cidr)
        if parent_usable == 0:
            allocation.utilization_percent = 0.0
            await db.flush()
            return 0.0

        # Sum usable IPs across all child allocations
        result = await db.execute(
            select(AddressAllocation.cidr).where(
                AddressAllocation.parent_allocation_id == allocation_id,
                AddressAllocation.deleted_at.is_(None),
            )
        )
        child_cidrs = list(result.scalars().all())

        used_ips = sum(calculate_usable_ips(c) for c in child_cidrs)
        utilization = min((used_ips / parent_usable) * 100.0, 100.0)

        allocation.utilization_percent = round(utilization, 2)
        await db.flush()
        return allocation.utilization_percent
