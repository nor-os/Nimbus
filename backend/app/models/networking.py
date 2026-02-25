"""
Overview: Networking entity models — connectivity, peering, private endpoints, load balancers.
Architecture: Managed networking entities for landing zones and environments (Section 6)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Connectivity (VPN/ER/DC), peering (hub-spoke), private endpoints (PL/PE/PSC),
    load balancers (shared hub-level and per-environment). All tenant-scoped with soft delete.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class ConnectivityConfig(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """VPN, ExpressRoute, DirectConnect, FastConnect, or other hybrid connectivity."""

    __tablename__ = "connectivity_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    connectivity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    remote_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_connectivity_configs_tenant", "tenant_id"),
        Index("ix_connectivity_configs_lz", "landing_zone_id"),
    )


class PeeringConfig(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Hub-to-spoke or inter-LZ peering configuration."""

    __tablename__ = "peering_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    peering_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    hub_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    spoke_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    routing_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_peering_configs_tenant", "tenant_id"),
        Index("ix_peering_configs_lz", "landing_zone_id"),
    )


class PrivateEndpointPolicy(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """LZ-level private endpoint policy/template."""

    __tablename__ = "private_endpoint_policies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    endpoint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_pe_policies_tenant", "tenant_id"),
        Index("ix_pe_policies_lz", "landing_zone_id"),
    )


class EnvironmentPrivateEndpoint(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-environment private endpoint instance."""

    __tablename__ = "environment_private_endpoints"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=False
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("private_endpoint_policies.id"), nullable=True
    )
    service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    endpoint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    cloud_resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    policy: Mapped["PrivateEndpointPolicy | None"] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_env_pe_tenant", "tenant_id"),
        Index("ix_env_pe_environment", "environment_id"),
    )


class SharedLoadBalancer(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """LZ-level shared load balancer."""

    __tablename__ = "shared_load_balancers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    landing_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_zones.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lb_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    cloud_resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    landing_zone: Mapped["LandingZone"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_shared_lb_tenant", "tenant_id"),
        Index("ix_shared_lb_lz", "landing_zone_id"),
    )


class EnvironmentLoadBalancer(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Per-environment load balancer instance."""

    __tablename__ = "environment_load_balancers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_environments.id"), nullable=False
    )
    shared_lb_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_load_balancers.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lb_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PLANNED")
    cloud_resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    shared_lb: Mapped["SharedLoadBalancer | None"] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_env_lb_tenant", "tenant_id"),
        Index("ix_env_lb_environment", "environment_id"),
    )
