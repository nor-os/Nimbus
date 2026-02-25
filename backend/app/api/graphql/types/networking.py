"""
Overview: GraphQL types for networking entities — connectivity, peering, private endpoints, load balancers.
Architecture: GraphQL type definitions for managed networking entities (Section 6)
Dependencies: strawberry
Concepts: All networking entity types and input types for CRUD operations.
"""

import uuid
from datetime import datetime

import strawberry
from strawberry.scalars import JSON


# ── Connectivity ─────────────────────────────────────────────────────

@strawberry.type
class ConnectivityConfigType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    name: str
    description: str | None
    connectivity_type: str
    provider_type: str
    status: str
    config: JSON | None
    remote_config: JSON | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class ConnectivityConfigInput:
    name: str
    connectivity_type: str
    provider_type: str
    description: str | None = None
    status: str = "PLANNED"
    config: JSON | None = None
    remote_config: JSON | None = None


@strawberry.input
class ConnectivityConfigUpdateInput:
    name: str | None = None
    description: str | None = strawberry.UNSET
    status: str | None = None
    config: JSON | None = strawberry.UNSET
    remote_config: JSON | None = strawberry.UNSET


# ── Peering ──────────────────────────────────────────────────────────

@strawberry.type
class PeeringConfigType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    environment_id: uuid.UUID | None
    name: str
    peering_type: str
    status: str
    hub_config: JSON | None
    spoke_config: JSON | None
    routing_config: JSON | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class PeeringConfigInput:
    name: str
    peering_type: str
    environment_id: uuid.UUID | None = None
    status: str = "PLANNED"
    hub_config: JSON | None = None
    spoke_config: JSON | None = None
    routing_config: JSON | None = None


@strawberry.input
class PeeringConfigUpdateInput:
    name: str | None = None
    status: str | None = None
    hub_config: JSON | None = strawberry.UNSET
    spoke_config: JSON | None = strawberry.UNSET
    routing_config: JSON | None = strawberry.UNSET


# ── Private Endpoints ────────────────────────────────────────────────

@strawberry.type
class PrivateEndpointPolicyType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    name: str
    service_name: str
    endpoint_type: str
    provider_type: str
    config: JSON | None
    status: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class PrivateEndpointPolicyInput:
    name: str
    service_name: str
    endpoint_type: str
    provider_type: str
    config: JSON | None = None
    status: str = "PLANNED"


@strawberry.input
class PrivateEndpointPolicyUpdateInput:
    name: str | None = None
    service_name: str | None = None
    config: JSON | None = strawberry.UNSET
    status: str | None = None


@strawberry.type
class EnvironmentPrivateEndpointType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    policy_id: uuid.UUID | None
    service_name: str
    endpoint_type: str
    config: JSON | None
    status: str
    cloud_resource_id: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class EnvironmentPrivateEndpointInput:
    service_name: str
    endpoint_type: str
    policy_id: uuid.UUID | None = None
    config: JSON | None = None
    status: str = "PLANNED"


@strawberry.input
class EnvironmentPrivateEndpointUpdateInput:
    config: JSON | None = strawberry.UNSET
    status: str | None = None
    cloud_resource_id: str | None = strawberry.UNSET


# ── Load Balancers ───────────────────────────────────────────────────

@strawberry.type
class SharedLoadBalancerType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    name: str
    lb_type: str
    provider_type: str
    config: JSON | None
    status: str
    cloud_resource_id: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class SharedLoadBalancerInput:
    name: str
    lb_type: str
    provider_type: str
    config: JSON | None = None
    status: str = "PLANNED"


@strawberry.input
class SharedLoadBalancerUpdateInput:
    name: str | None = None
    config: JSON | None = strawberry.UNSET
    status: str | None = None
    cloud_resource_id: str | None = strawberry.UNSET


@strawberry.type
class EnvironmentLoadBalancerType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    shared_lb_id: uuid.UUID | None
    name: str
    lb_type: str
    config: JSON | None
    status: str
    cloud_resource_id: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class EnvironmentLoadBalancerInput:
    name: str
    lb_type: str
    shared_lb_id: uuid.UUID | None = None
    config: JSON | None = None
    status: str = "PLANNED"


@strawberry.input
class EnvironmentLoadBalancerUpdateInput:
    name: str | None = None
    config: JSON | None = strawberry.UNSET
    status: str | None = None
    cloud_resource_id: str | None = strawberry.UNSET
