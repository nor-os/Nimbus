"""
Overview: GraphQL queries for deployments.
Architecture: Query resolvers for deployments (Section 7.2)
Dependencies: strawberry, app.services.deployment.deployment_service, app.api.graphql.auth
Concepts: Deployment queries, tenant-scoped listing, optional environment filter
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.deployment import DeploymentCIType, DeploymentStatusGQL, DeploymentType


# ── Converters ─────────────────────────────────────────────────────────

def _deployment_ci_to_type(dc) -> DeploymentCIType:
    return DeploymentCIType(
        id=dc.id,
        deployment_id=dc.deployment_id,
        ci_id=dc.ci_id,
        component_id=dc.component_id,
        topology_node_id=dc.topology_node_id,
        resolver_outputs=dc.resolver_outputs,
        created_at=dc.created_at,
    )


def _deployment_to_type(d) -> DeploymentType:
    cis = []
    if hasattr(d, "cis") and d.cis:
        cis = [_deployment_ci_to_type(dc) for dc in d.cis]
    return DeploymentType(
        id=d.id,
        tenant_id=d.tenant_id,
        environment_id=d.environment_id,
        topology_id=d.topology_id,
        name=d.name,
        description=d.description,
        status=DeploymentStatusGQL(d.status.value),
        parameters=d.parameters,
        resolved_parameters=d.resolved_parameters,
        resolution_status=d.resolution_status,
        resolution_error=d.resolution_error,
        deployed_by=d.deployed_by,
        deployed_at=d.deployed_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
        cis=cis,
    )


# ── Queries ────────────────────────────────────────────────────────────


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class DeploymentQuery:

    @strawberry.field
    async def deployments(
        self, info: Info, tenant_id: uuid.UUID,
        environment_id: uuid.UUID | None = None,
    ) -> list[DeploymentType]:
        """List deployments for a tenant, optionally filtered by environment."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        deployments = await svc.list_by_tenant(db, tenant_id, environment_id)
        return [_deployment_to_type(d) for d in deployments]

    @strawberry.field
    async def deployment(
        self, info: Info, tenant_id: uuid.UUID, deployment_id: uuid.UUID,
    ) -> DeploymentType | None:
        """Get a deployment by ID."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        d = await svc.get(db, deployment_id)
        return _deployment_to_type(d) if d else None

    @strawberry.field
    async def deployment_cis(
        self, info: Info, tenant_id: uuid.UUID, deployment_id: uuid.UUID,
    ) -> list[DeploymentCIType]:
        """Get all CIs linked to a deployment."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        items = await svc.get_deployment_cis(db, deployment_id)
        return [_deployment_ci_to_type(dc) for dc in items]
