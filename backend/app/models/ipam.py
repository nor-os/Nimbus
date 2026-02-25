"""
Overview: IPAM models — address spaces, hierarchical allocations, IP reservations.
Architecture: IP address management data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: CIDR hierarchy, address allocation, IP reservation, utilization tracking
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class AddressSpaceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    RESERVED = "RESERVED"


class AllocationType(str, enum.Enum):
    REGION = "REGION"
    PROVIDER_RESERVED = "PROVIDER_RESERVED"
    TENANT_POOL = "TENANT_POOL"
    VCN = "VCN"
    SUBNET = "SUBNET"


class AllocationStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    ALLOCATED = "ALLOCATED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"


class ReservationStatus(str, enum.Enum):
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"


class AddressSpace(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "address_spaces"

    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backend_regions.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidr: Mapped[str] = mapped_column(String(43), nullable=False)
    ip_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=4, server_default="4")
    status: Mapped[AddressSpaceStatus] = mapped_column(
        Enum(AddressSpaceStatus, name="address_space_status", create_constraint=False),
        nullable=False,
        default=AddressSpaceStatus.ACTIVE,
        server_default="ACTIVE",
    )

    # Relationships
    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821
    region: Mapped["BackendRegion | None"] = relationship(lazy="joined")  # noqa: F821
    allocations: Mapped[list["AddressAllocation"]] = relationship(
        back_populates="address_space", lazy="selectin"
    )


class AddressAllocation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "address_allocations"

    address_space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("address_spaces.id"), nullable=False
    )
    parent_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("address_allocations.id"), nullable=True
    )
    tenant_environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidr: Mapped[str] = mapped_column(String(43), nullable=False)
    allocation_type: Mapped[AllocationType] = mapped_column(
        Enum(AllocationType, name="allocation_type", create_constraint=False),
        nullable=False,
    )
    status: Mapped[AllocationStatus] = mapped_column(
        Enum(AllocationStatus, name="allocation_status", create_constraint=False),
        nullable=False,
        default=AllocationStatus.PLANNED,
        server_default="PLANNED",
    )
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    semantic_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_resource_types.id"), nullable=True
    )
    cloud_resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    utilization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    allocation_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    address_space: Mapped["AddressSpace"] = relationship(back_populates="allocations")
    parent: Mapped["AddressAllocation | None"] = relationship(
        "AddressAllocation", remote_side="AddressAllocation.id", back_populates="children"
    )
    children: Mapped[list["AddressAllocation"]] = relationship(
        "AddressAllocation", back_populates="parent"
    )
    tenant_environment: Mapped["TenantEnvironment | None"] = relationship(lazy="joined")  # noqa: F821
    reservations: Mapped[list["IpReservation"]] = relationship(
        back_populates="allocation", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_addr_alloc_space", "address_space_id"),
        Index("ix_addr_alloc_parent", "parent_allocation_id"),
        Index("ix_addr_alloc_tenant_env", "tenant_environment_id"),
    )


class IpReservation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ip_reservations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("address_allocations.id"), nullable=False
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    ci_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_items.id"), nullable=True
    )
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status", create_constraint=False),
        nullable=False,
        default=ReservationStatus.RESERVED,
        server_default="RESERVED",
    )
    reserved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    allocation: Mapped["AddressAllocation"] = relationship(back_populates="reservations")

    __table_args__ = (
        Index("ix_ip_res_allocation", "allocation_id"),
        Index("ix_ip_res_ci", "ci_id"),
    )
