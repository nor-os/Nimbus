"""
Overview: GraphQL mutations for networking entities — connectivity, peering, private endpoints, load balancers.
Architecture: GraphQL mutation resolvers for managed networking entities (Section 6)
Dependencies: strawberry, app.services.landing_zone.networking_service
Concepts: Full CRUD with permission checks for all networking entity types.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.networking import (
    _connectivity_to_gql,
    _env_lb_to_gql,
    _env_pe_to_gql,
    _peering_to_gql,
    _pe_policy_to_gql,
    _shared_lb_to_gql,
)
from app.api.graphql.types.networking import (
    ConnectivityConfigInput,
    ConnectivityConfigType,
    ConnectivityConfigUpdateInput,
    EnvironmentLoadBalancerInput,
    EnvironmentLoadBalancerType,
    EnvironmentLoadBalancerUpdateInput,
    EnvironmentPrivateEndpointInput,
    EnvironmentPrivateEndpointType,
    EnvironmentPrivateEndpointUpdateInput,
    PeeringConfigInput,
    PeeringConfigType,
    PeeringConfigUpdateInput,
    PrivateEndpointPolicyInput,
    PrivateEndpointPolicyType,
    PrivateEndpointPolicyUpdateInput,
    SharedLoadBalancerInput,
    SharedLoadBalancerType,
    SharedLoadBalancerUpdateInput,
)


def _get_user_id(info: Info) -> uuid.UUID | None:
    request = info.context.get("request")
    if request and hasattr(request, "state") and hasattr(request.state, "user_id"):
        import uuid as _uuid
        return _uuid.UUID(request.state.user_id)
    return None


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class NetworkingMutation:

    # ── Connectivity ────────────────────────────────────────────────

    @strawberry.mutation
    async def create_connectivity_config(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
        input: ConnectivityConfigInput,
    ) -> ConnectivityConfigType:
        await check_graphql_permission(info, "cloud:connectivity:create", str(tenant_id))
        from app.services.landing_zone.networking_service import ConnectivityService
        db = await _get_session(info)
        svc = ConnectivityService(db)
        obj = await svc.create(
            tenant_id, landing_zone_id,
            name=input.name, connectivity_type=input.connectivity_type,
            provider_type=input.provider_type, description=input.description,
            status=input.status, config=input.config,
            remote_config=input.remote_config, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _connectivity_to_gql(obj)

    @strawberry.mutation
    async def update_connectivity_config(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: ConnectivityConfigUpdateInput,
    ) -> ConnectivityConfigType | None:
        await check_graphql_permission(info, "cloud:connectivity:update", str(tenant_id))
        from app.services.landing_zone.networking_service import ConnectivityService
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.status is not None:
            kwargs["status"] = input.status
        if input.config is not strawberry.UNSET:
            kwargs["config"] = input.config
        if input.remote_config is not strawberry.UNSET:
            kwargs["remote_config"] = input.remote_config
        db = await _get_session(info)
        svc = ConnectivityService(db)
        obj = await svc.update(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _connectivity_to_gql(obj)

    @strawberry.mutation
    async def delete_connectivity_config(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:connectivity:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import ConnectivityService
        db = await _get_session(info)
        svc = ConnectivityService(db)
        deleted = await svc.delete(id)
        await db.commit()
        return deleted

    # ── Peering ─────────────────────────────────────────────────────

    @strawberry.mutation
    async def create_peering_config(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
        input: PeeringConfigInput,
    ) -> PeeringConfigType:
        await check_graphql_permission(info, "cloud:peering:create", str(tenant_id))
        from app.services.landing_zone.networking_service import PeeringService
        db = await _get_session(info)
        svc = PeeringService(db)
        obj = await svc.create(
            tenant_id, landing_zone_id,
            name=input.name, peering_type=input.peering_type,
            environment_id=input.environment_id, status=input.status,
            hub_config=input.hub_config, spoke_config=input.spoke_config,
            routing_config=input.routing_config, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _peering_to_gql(obj)

    @strawberry.mutation
    async def update_peering_config(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: PeeringConfigUpdateInput,
    ) -> PeeringConfigType | None:
        await check_graphql_permission(info, "cloud:peering:update", str(tenant_id))
        from app.services.landing_zone.networking_service import PeeringService
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.status is not None:
            kwargs["status"] = input.status
        if input.hub_config is not strawberry.UNSET:
            kwargs["hub_config"] = input.hub_config
        if input.spoke_config is not strawberry.UNSET:
            kwargs["spoke_config"] = input.spoke_config
        if input.routing_config is not strawberry.UNSET:
            kwargs["routing_config"] = input.routing_config
        db = await _get_session(info)
        svc = PeeringService(db)
        obj = await svc.update(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _peering_to_gql(obj)

    @strawberry.mutation
    async def delete_peering_config(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:peering:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import PeeringService
        db = await _get_session(info)
        svc = PeeringService(db)
        deleted = await svc.delete(id)
        await db.commit()
        return deleted

    # ── Private Endpoint Policies ────────────────────────────────────

    @strawberry.mutation
    async def create_private_endpoint_policy(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
        input: PrivateEndpointPolicyInput,
    ) -> PrivateEndpointPolicyType:
        await check_graphql_permission(info, "cloud:privateendpoint:create", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        obj = await svc.create_policy(
            tenant_id, landing_zone_id,
            name=input.name, service_name=input.service_name,
            endpoint_type=input.endpoint_type, provider_type=input.provider_type,
            config=input.config, status=input.status, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _pe_policy_to_gql(obj)

    @strawberry.mutation
    async def update_private_endpoint_policy(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: PrivateEndpointPolicyUpdateInput,
    ) -> PrivateEndpointPolicyType | None:
        await check_graphql_permission(info, "cloud:privateendpoint:update", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.service_name is not None:
            kwargs["service_name"] = input.service_name
        if input.config is not strawberry.UNSET:
            kwargs["config"] = input.config
        if input.status is not None:
            kwargs["status"] = input.status
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        obj = await svc.update_policy(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _pe_policy_to_gql(obj)

    @strawberry.mutation
    async def delete_private_endpoint_policy(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:privateendpoint:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        deleted = await svc.delete_policy(id)
        await db.commit()
        return deleted

    # ── Environment Private Endpoints ─────────────────────────────────

    @strawberry.mutation
    async def create_environment_private_endpoint(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
        input: EnvironmentPrivateEndpointInput,
    ) -> EnvironmentPrivateEndpointType:
        await check_graphql_permission(info, "cloud:privateendpoint:create", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        obj = await svc.create_env_endpoint(
            tenant_id, environment_id,
            service_name=input.service_name, endpoint_type=input.endpoint_type,
            policy_id=input.policy_id, config=input.config,
            status=input.status, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _env_pe_to_gql(obj)

    @strawberry.mutation
    async def update_environment_private_endpoint(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: EnvironmentPrivateEndpointUpdateInput,
    ) -> EnvironmentPrivateEndpointType | None:
        await check_graphql_permission(info, "cloud:privateendpoint:update", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        kwargs = {}
        if input.config is not strawberry.UNSET:
            kwargs["config"] = input.config
        if input.status is not None:
            kwargs["status"] = input.status
        if input.cloud_resource_id is not strawberry.UNSET:
            kwargs["cloud_resource_id"] = input.cloud_resource_id
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        obj = await svc.update_env_endpoint(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _env_pe_to_gql(obj)

    @strawberry.mutation
    async def delete_environment_private_endpoint(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:privateendpoint:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import PrivateEndpointService
        db = await _get_session(info)
        svc = PrivateEndpointService(db)
        deleted = await svc.delete_env_endpoint(id)
        await db.commit()
        return deleted

    # ── Shared Load Balancers ────────────────────────────────────────

    @strawberry.mutation
    async def create_shared_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
        input: SharedLoadBalancerInput,
    ) -> SharedLoadBalancerType:
        await check_graphql_permission(info, "cloud:loadbalancer:create", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        obj = await svc.create_shared(
            tenant_id, landing_zone_id,
            name=input.name, lb_type=input.lb_type,
            provider_type=input.provider_type, config=input.config,
            status=input.status, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _shared_lb_to_gql(obj)

    @strawberry.mutation
    async def update_shared_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: SharedLoadBalancerUpdateInput,
    ) -> SharedLoadBalancerType | None:
        await check_graphql_permission(info, "cloud:loadbalancer:update", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.config is not strawberry.UNSET:
            kwargs["config"] = input.config
        if input.status is not None:
            kwargs["status"] = input.status
        if input.cloud_resource_id is not strawberry.UNSET:
            kwargs["cloud_resource_id"] = input.cloud_resource_id
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        obj = await svc.update_shared(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _shared_lb_to_gql(obj)

    @strawberry.mutation
    async def delete_shared_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:loadbalancer:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        deleted = await svc.delete_shared(id)
        await db.commit()
        return deleted

    # ── Environment Load Balancers ────────────────────────────────────

    @strawberry.mutation
    async def create_environment_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
        input: EnvironmentLoadBalancerInput,
    ) -> EnvironmentLoadBalancerType:
        await check_graphql_permission(info, "cloud:loadbalancer:create", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        obj = await svc.create_env_lb(
            tenant_id, environment_id,
            name=input.name, lb_type=input.lb_type,
            shared_lb_id=input.shared_lb_id, config=input.config,
            status=input.status, created_by=_get_user_id(info),
        )
        await db.commit()
        await db.refresh(obj)
        return _env_lb_to_gql(obj)

    @strawberry.mutation
    async def update_environment_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: EnvironmentLoadBalancerUpdateInput,
    ) -> EnvironmentLoadBalancerType | None:
        await check_graphql_permission(info, "cloud:loadbalancer:update", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.config is not strawberry.UNSET:
            kwargs["config"] = input.config
        if input.status is not None:
            kwargs["status"] = input.status
        if input.cloud_resource_id is not strawberry.UNSET:
            kwargs["cloud_resource_id"] = input.cloud_resource_id
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        obj = await svc.update_env_lb(id, **kwargs)
        if not obj:
            return None
        await db.commit()
        await db.refresh(obj)
        return _env_lb_to_gql(obj)

    @strawberry.mutation
    async def delete_environment_load_balancer(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "cloud:loadbalancer:delete", str(tenant_id))
        from app.services.landing_zone.networking_service import LoadBalancerService
        db = await _get_session(info)
        svc = LoadBalancerService(db)
        deleted = await svc.delete_env_lb(id)
        await db.commit()
        return deleted
