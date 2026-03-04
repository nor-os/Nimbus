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
from app.api.graphql.types.deployment import (
    ComponentInstanceSourceTypeGQL,
    ComponentInstanceType,
    DeploymentCIType,
    DeploymentStatusGQL,
    DeploymentType,
    UpgradableCIType,
)


# ── Converters ─────────────────────────────────────────────────────────

def _deployment_ci_to_type(dc) -> DeploymentCIType:
    return DeploymentCIType(
        id=dc.id,
        deployment_id=dc.deployment_id,
        ci_id=dc.ci_id,
        component_id=dc.component_id,
        topology_node_id=dc.topology_node_id,
        component_version=dc.component_version,
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


def _component_instance_to_type(item: dict) -> ComponentInstanceType:
    return ComponentInstanceType(
        id=item["id"],
        component_id=item["component_id"],
        component_display_name=item["component_display_name"],
        component_version=item["component_version"],
        environment_id=item["environment_id"],
        status=item["status"],
        source_type=ComponentInstanceSourceTypeGQL(item["source_type"]),
        source_id=item["source_id"],
        source_name=item["source_name"],
        resolved_parameters=item["resolved_parameters"],
        outputs=item["outputs"],
        deployed_at=item["deployed_at"],
        created_at=item["created_at"],
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
        has_topology: bool | None = None,
    ) -> list[DeploymentType]:
        """List deployments for a tenant, optionally filtered by environment and topology presence."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        deployments = await svc.list_by_tenant(db, tenant_id, environment_id, has_topology)
        return [_deployment_to_type(d) for d in deployments]

    @strawberry.field
    async def topology_instances(
        self, info: Info, tenant_id: uuid.UUID,
        environment_id: uuid.UUID | None = None,
    ) -> list[DeploymentType]:
        """List topology-based deployments (convenience alias for deployments with hasTopology=true)."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        deployments = await svc.list_by_tenant(db, tenant_id, environment_id, has_topology=True)
        return [_deployment_to_type(d) for d in deployments]

    @strawberry.field
    async def component_instances(
        self, info: Info, tenant_id: uuid.UUID,
        environment_id: uuid.UUID | None = None,
    ) -> list[ComponentInstanceType]:
        """List all component instances across deployments and stack instances."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        items = await svc.list_component_instances(db, tenant_id, environment_id)
        return [_component_instance_to_type(item) for item in items]

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

    @strawberry.field
    async def upgradable_deployment_cis(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> list[UpgradableCIType]:
        """Find deployed CIs in an environment that have newer component versions available."""
        await check_graphql_permission(info, "deployment:deployment:read", str(tenant_id))

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        items = await svc.check_upgradable_cis(db, environment_id)
        return [
            UpgradableCIType(
                deployment_ci_id=item["deployment_ci_id"],
                ci_id=item["ci_id"],
                component_id=item["component_id"],
                component_display_name=item["component_display_name"],
                deployed_version=item["deployed_version"],
                latest_version=item["latest_version"],
                deployment_id=item["deployment_id"],
                changelog=item["changelog"],
            )
            for item in items
        ]
