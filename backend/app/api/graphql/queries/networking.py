"""
Overview: GraphQL queries for networking entities — connectivity, peering, private endpoints, load balancers.
Architecture: GraphQL query resolvers for managed networking entities (Section 6)
Dependencies: strawberry, app.services.landing_zone.networking_service
Concepts: List queries scoped by landing zone or environment.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.networking import (
    ConnectivityConfigType,
    EnvironmentLoadBalancerType,
    EnvironmentPrivateEndpointType,
    PeeringConfigType,
    PrivateEndpointPolicyType,
    SharedLoadBalancerType,
)


def _connectivity_to_gql(c) -> ConnectivityConfigType:
    return ConnectivityConfigType(
        id=c.id, tenant_id=c.tenant_id, landing_zone_id=c.landing_zone_id,
        name=c.name, description=c.description,
        connectivity_type=c.connectivity_type, provider_type=c.provider_type,
        status=c.status, config=c.config, remote_config=c.remote_config,
        created_by=c.created_by, created_at=c.created_at, updated_at=c.updated_at,
    )


def _peering_to_gql(p) -> PeeringConfigType:
    return PeeringConfigType(
        id=p.id, tenant_id=p.tenant_id, landing_zone_id=p.landing_zone_id,
        environment_id=p.environment_id, name=p.name,
        peering_type=p.peering_type, status=p.status,
        hub_config=p.hub_config, spoke_config=p.spoke_config,
        routing_config=p.routing_config,
        created_by=p.created_by, created_at=p.created_at, updated_at=p.updated_at,
    )


def _pe_policy_to_gql(p) -> PrivateEndpointPolicyType:
    return PrivateEndpointPolicyType(
        id=p.id, tenant_id=p.tenant_id, landing_zone_id=p.landing_zone_id,
        name=p.name, service_name=p.service_name,
        endpoint_type=p.endpoint_type, provider_type=p.provider_type,
        config=p.config, status=p.status,
        created_by=p.created_by, created_at=p.created_at, updated_at=p.updated_at,
    )


def _env_pe_to_gql(e) -> EnvironmentPrivateEndpointType:
    return EnvironmentPrivateEndpointType(
        id=e.id, tenant_id=e.tenant_id, environment_id=e.environment_id,
        policy_id=e.policy_id, service_name=e.service_name,
        endpoint_type=e.endpoint_type, config=e.config, status=e.status,
        cloud_resource_id=e.cloud_resource_id,
        created_by=e.created_by, created_at=e.created_at, updated_at=e.updated_at,
    )


def _shared_lb_to_gql(lb) -> SharedLoadBalancerType:
    return SharedLoadBalancerType(
        id=lb.id, tenant_id=lb.tenant_id, landing_zone_id=lb.landing_zone_id,
        name=lb.name, lb_type=lb.lb_type, provider_type=lb.provider_type,
        config=lb.config, status=lb.status, cloud_resource_id=lb.cloud_resource_id,
        created_by=lb.created_by, created_at=lb.created_at, updated_at=lb.updated_at,
    )


def _env_lb_to_gql(lb) -> EnvironmentLoadBalancerType:
    return EnvironmentLoadBalancerType(
        id=lb.id, tenant_id=lb.tenant_id, environment_id=lb.environment_id,
        shared_lb_id=lb.shared_lb_id, name=lb.name, lb_type=lb.lb_type,
        config=lb.config, status=lb.status, cloud_resource_id=lb.cloud_resource_id,
        created_by=lb.created_by, created_at=lb.created_at, updated_at=lb.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class NetworkingQuery:

    @strawberry.field
    async def connectivity_configs(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
    ) -> list[ConnectivityConfigType]:
        await check_graphql_permission(info, "cloud:connectivity:read", str(tenant_id))
        from app.services.landing_zone.networking_service import ConnectivityService
        db = await _get_session(info)
        svc = ConnectivityService(db)
        items = await svc.list_by_landing_zone(landing_zone_id)
        return [_connectivity_to_gql(c) for c in items]

    @strawberry.field
    async def peering_configs(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
    ) -> list[PeeringConfigType]:
        await check_graphql_permission(info, "cloud:peering:read", str(tenant_id))
        from app.services.landing_zone.networking_service import PeeringService
        db = await _get_session(info)
        svc = PeeringService(db)
        items = await svc.list_by_landing_zone(landing_zone_id)
        return [_peering_to_gql(p) for p in items]

    @strawberry.field
    async def private_endpoint_policies(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
    ) -> list[PrivateEndpointPolicyType]:
        await check_graphql_permission(info, "cloud:privateendpoint:read", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        items = await svc.list_policies(landing_zone_id)
        return [_pe_policy_to_gql(p) for p in items]

    @strawberry.field
    async def environment_private_endpoints(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> list[EnvironmentPrivateEndpointType]:
        await check_graphql_permission(info, "cloud:privateendpoint:read", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        items = await svc.list_env_endpoints(environment_id)
        return [_env_pe_to_gql(e) for e in items]

    @strawberry.field
    async def shared_load_balancers(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
    ) -> list[SharedLoadBalancerType]:
        await check_graphql_permission(info, "cloud:loadbalancer:read", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        items = await svc.list_shared(landing_zone_id)
        return [_shared_lb_to_gql(lb) for lb in items]

    @strawberry.field
    async def environment_load_balancers(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> list[EnvironmentLoadBalancerType]:
        await check_graphql_permission(info, "cloud:loadbalancer:read", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        items = await svc.list_env_lbs(environment_id)
        return [_env_lb_to_gql(lb) for lb in items]
