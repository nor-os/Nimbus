"""
Overview: Networking services — CRUD for connectivity, peering, private endpoints, load balancers.
Architecture: Service layer for managed networking entities (Section 6)
Dependencies: sqlalchemy, app.models.networking
Concepts: Connectivity (VPN/ER/DC), peering (hub-spoke), private endpoints, load balancers.
    All operations are tenant-scoped with soft delete.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.networking import (
    ConnectivityConfig,
    EnvironmentLoadBalancer,
    EnvironmentPrivateEndpoint,
    PeeringConfig,
    PrivateEndpointPolicy,
    SharedLoadBalancer,
)


class ConnectivityService:
    """CRUD for hybrid connectivity configurations (VPN, ExpressRoute, etc.)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_landing_zone(
        self, landing_zone_id: uuid.UUID
    ) -> list[ConnectivityConfig]:
        stmt = (
            select(ConnectivityConfig)
            .where(
                ConnectivityConfig.landing_zone_id == landing_zone_id,
                ConnectivityConfig.deleted_at.is_(None),
            )
            .order_by(ConnectivityConfig.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, config_id: uuid.UUID) -> ConnectivityConfig | None:
        stmt = select(ConnectivityConfig).where(
            ConnectivityConfig.id == config_id,
            ConnectivityConfig.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID,
        *,
        name: str,
        connectivity_type: str,
        provider_type: str,
        description: str | None = None,
        status: str = "PLANNED",
        config: dict | None = None,
        remote_config: dict | None = None,
        created_by: uuid.UUID | None = None,
    ) -> ConnectivityConfig:
        obj = ConnectivityConfig(
            tenant_id=tenant_id,
            landing_zone_id=landing_zone_id,
            name=name,
            description=description,
            connectivity_type=connectivity_type,
            provider_type=provider_type,
            status=status,
            config=config,
            remote_config=remote_config,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, config_id: uuid.UUID, **kwargs) -> ConnectivityConfig | None:
        obj = await self.get(config_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "landing_zone_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete(self, config_id: uuid.UUID) -> bool:
        obj = await self.get(config_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True


class PeeringService:
    """CRUD for peering configurations (hub-spoke, inter-LZ)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_landing_zone(
        self, landing_zone_id: uuid.UUID
    ) -> list[PeeringConfig]:
        stmt = (
            select(PeeringConfig)
            .where(
                PeeringConfig.landing_zone_id == landing_zone_id,
                PeeringConfig.deleted_at.is_(None),
            )
            .order_by(PeeringConfig.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, config_id: uuid.UUID) -> PeeringConfig | None:
        stmt = select(PeeringConfig).where(
            PeeringConfig.id == config_id,
            PeeringConfig.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID,
        *,
        name: str,
        peering_type: str,
        environment_id: uuid.UUID | None = None,
        status: str = "PLANNED",
        hub_config: dict | None = None,
        spoke_config: dict | None = None,
        routing_config: dict | None = None,
        created_by: uuid.UUID | None = None,
    ) -> PeeringConfig:
        obj = PeeringConfig(
            tenant_id=tenant_id,
            landing_zone_id=landing_zone_id,
            environment_id=environment_id,
            name=name,
            peering_type=peering_type,
            status=status,
            hub_config=hub_config,
            spoke_config=spoke_config,
            routing_config=routing_config,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, config_id: uuid.UUID, **kwargs) -> PeeringConfig | None:
        obj = await self.get(config_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "landing_zone_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete(self, config_id: uuid.UUID) -> bool:
        obj = await self.get(config_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True


class PrivateEndpointService:
    """CRUD for private endpoint policies (LZ-level) and per-environment instances."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- LZ-level policies --

    async def list_policies(
        self, landing_zone_id: uuid.UUID
    ) -> list[PrivateEndpointPolicy]:
        stmt = (
            select(PrivateEndpointPolicy)
            .where(
                PrivateEndpointPolicy.landing_zone_id == landing_zone_id,
                PrivateEndpointPolicy.deleted_at.is_(None),
            )
            .order_by(PrivateEndpointPolicy.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_policy(self, policy_id: uuid.UUID) -> PrivateEndpointPolicy | None:
        stmt = select(PrivateEndpointPolicy).where(
            PrivateEndpointPolicy.id == policy_id,
            PrivateEndpointPolicy.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_policy(
        self,
        tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID,
        *,
        name: str,
        service_name: str,
        endpoint_type: str,
        provider_type: str,
        config: dict | None = None,
        status: str = "PLANNED",
        created_by: uuid.UUID | None = None,
    ) -> PrivateEndpointPolicy:
        obj = PrivateEndpointPolicy(
            tenant_id=tenant_id,
            landing_zone_id=landing_zone_id,
            name=name,
            service_name=service_name,
            endpoint_type=endpoint_type,
            provider_type=provider_type,
            config=config,
            status=status,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update_policy(self, policy_id: uuid.UUID, **kwargs) -> PrivateEndpointPolicy | None:
        obj = await self.get_policy(policy_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "landing_zone_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete_policy(self, policy_id: uuid.UUID) -> bool:
        obj = await self.get_policy(policy_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -- Per-environment endpoints --

    async def list_env_endpoints(
        self, environment_id: uuid.UUID
    ) -> list[EnvironmentPrivateEndpoint]:
        stmt = (
            select(EnvironmentPrivateEndpoint)
            .where(
                EnvironmentPrivateEndpoint.environment_id == environment_id,
                EnvironmentPrivateEndpoint.deleted_at.is_(None),
            )
            .order_by(EnvironmentPrivateEndpoint.service_name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_env_endpoint(self, endpoint_id: uuid.UUID) -> EnvironmentPrivateEndpoint | None:
        stmt = select(EnvironmentPrivateEndpoint).where(
            EnvironmentPrivateEndpoint.id == endpoint_id,
            EnvironmentPrivateEndpoint.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_env_endpoint(
        self,
        tenant_id: uuid.UUID,
        environment_id: uuid.UUID,
        *,
        service_name: str,
        endpoint_type: str,
        policy_id: uuid.UUID | None = None,
        config: dict | None = None,
        status: str = "PLANNED",
        created_by: uuid.UUID | None = None,
    ) -> EnvironmentPrivateEndpoint:
        obj = EnvironmentPrivateEndpoint(
            tenant_id=tenant_id,
            environment_id=environment_id,
            policy_id=policy_id,
            service_name=service_name,
            endpoint_type=endpoint_type,
            config=config,
            status=status,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update_env_endpoint(self, endpoint_id: uuid.UUID, **kwargs) -> EnvironmentPrivateEndpoint | None:
        obj = await self.get_env_endpoint(endpoint_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "environment_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete_env_endpoint(self, endpoint_id: uuid.UUID) -> bool:
        obj = await self.get_env_endpoint(endpoint_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True


class LoadBalancerService:
    """CRUD for shared (LZ-level) and per-environment load balancers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Shared LBs (LZ-level) --

    async def list_shared(
        self, landing_zone_id: uuid.UUID
    ) -> list[SharedLoadBalancer]:
        stmt = (
            select(SharedLoadBalancer)
            .where(
                SharedLoadBalancer.landing_zone_id == landing_zone_id,
                SharedLoadBalancer.deleted_at.is_(None),
            )
            .order_by(SharedLoadBalancer.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_shared(self, lb_id: uuid.UUID) -> SharedLoadBalancer | None:
        stmt = select(SharedLoadBalancer).where(
            SharedLoadBalancer.id == lb_id,
            SharedLoadBalancer.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_shared(
        self,
        tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID,
        *,
        name: str,
        lb_type: str,
        provider_type: str,
        config: dict | None = None,
        status: str = "PLANNED",
        created_by: uuid.UUID | None = None,
    ) -> SharedLoadBalancer:
        obj = SharedLoadBalancer(
            tenant_id=tenant_id,
            landing_zone_id=landing_zone_id,
            name=name,
            lb_type=lb_type,
            provider_type=provider_type,
            config=config,
            status=status,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update_shared(self, lb_id: uuid.UUID, **kwargs) -> SharedLoadBalancer | None:
        obj = await self.get_shared(lb_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "landing_zone_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete_shared(self, lb_id: uuid.UUID) -> bool:
        obj = await self.get_shared(lb_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -- Per-environment LBs --

    async def list_env_lbs(
        self, environment_id: uuid.UUID
    ) -> list[EnvironmentLoadBalancer]:
        stmt = (
            select(EnvironmentLoadBalancer)
            .where(
                EnvironmentLoadBalancer.environment_id == environment_id,
                EnvironmentLoadBalancer.deleted_at.is_(None),
            )
            .order_by(EnvironmentLoadBalancer.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_env_lb(self, lb_id: uuid.UUID) -> EnvironmentLoadBalancer | None:
        stmt = select(EnvironmentLoadBalancer).where(
            EnvironmentLoadBalancer.id == lb_id,
            EnvironmentLoadBalancer.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_env_lb(
        self,
        tenant_id: uuid.UUID,
        environment_id: uuid.UUID,
        *,
        name: str,
        lb_type: str,
        shared_lb_id: uuid.UUID | None = None,
        config: dict | None = None,
        status: str = "PLANNED",
        created_by: uuid.UUID | None = None,
    ) -> EnvironmentLoadBalancer:
        obj = EnvironmentLoadBalancer(
            tenant_id=tenant_id,
            environment_id=environment_id,
            shared_lb_id=shared_lb_id,
            name=name,
            lb_type=lb_type,
            config=config,
            status=status,
            created_by=created_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update_env_lb(self, lb_id: uuid.UUID, **kwargs) -> EnvironmentLoadBalancer | None:
        obj = await self.get_env_lb(lb_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "tenant_id", "environment_id", "created_at"):
                setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete_env_lb(self, lb_id: uuid.UUID) -> bool:
        obj = await self.get_env_lb(lb_id)
        if not obj:
            return False
        obj.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
