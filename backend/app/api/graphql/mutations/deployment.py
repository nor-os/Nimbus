"""
Overview: GraphQL mutations for deployments.
Architecture: Mutation resolvers for deployments (Section 7.2)
Dependencies: strawberry, app.services.deployment.deployment_service, app.api.graphql.auth
Concepts: Deployment CRUD, permission checks, soft delete
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.deployment import _deployment_to_type
from app.api.graphql.types.deployment import (
    DeploymentCreateInput,
    DeploymentType,
    DeploymentUpdateInput,
    ResolvedParameterInfo,
    ResolvedParametersPreview,
    ResolveParametersInput,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class DeploymentMutation:

    @strawberry.mutation
    async def create_deployment(
        self, info: Info, tenant_id: uuid.UUID, input: DeploymentCreateInput,
    ) -> DeploymentType:
        """Create a new deployment (starts in PLANNED status)."""
        user_id = await check_graphql_permission(
            info, "deployment:deployment:create", str(tenant_id)
        )

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        d = await svc.create(
            db, tenant_id=tenant_id,
            environment_id=input.environment_id,
            topology_id=input.topology_id,
            name=input.name,
            deployed_by=user_id,
            description=input.description,
            parameters=input.parameters,
        )
        await db.commit()
        return _deployment_to_type(d)

    @strawberry.mutation
    async def update_deployment(
        self, info: Info, tenant_id: uuid.UUID,
        deployment_id: uuid.UUID, input: DeploymentUpdateInput,
    ) -> DeploymentType:
        """Update a deployment."""
        await check_graphql_permission(
            info, "deployment:deployment:update", str(tenant_id)
        )

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.description is not None:
            kwargs["description"] = input.description
        if input.status is not None:
            kwargs["status"] = input.status.value
        if input.parameters is not None:
            kwargs["parameters"] = input.parameters
        d = await svc.update(db, deployment_id, **kwargs)
        await db.commit()
        return _deployment_to_type(d)

    @strawberry.mutation
    async def delete_deployment(
        self, info: Info, tenant_id: uuid.UUID, deployment_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a deployment."""
        await check_graphql_permission(
            info, "deployment:deployment:delete", str(tenant_id)
        )

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        await svc.delete(db, deployment_id)
        await db.commit()
        return True

    @strawberry.mutation
    async def preview_resolved_parameters(
        self, info: Info, tenant_id: uuid.UUID, input: ResolveParametersInput,
    ) -> ResolvedParametersPreview:
        """Preview parameter resolution without side effects (dry run)."""
        await check_graphql_permission(
            info, "deployment:deployment:preview", str(tenant_id)
        )

        from sqlalchemy import select

        from app.models.component import Component
        from app.services.resolver.registry import get_resolver_registry

        db = await _get_session(info)
        result = await db.execute(
            select(Component).where(
                Component.id == input.component_id,
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            raise ValueError(f"Component {input.component_id} not found")

        registry = get_resolver_registry()
        user_params = input.user_params or {}
        resolved = await registry.resolve_all(
            component, db, tenant_id, user_params,
            environment_id=input.environment_id,
            landing_zone_id=input.landing_zone_id,
            dry_run=True,
        )

        # Build detail annotations
        details: list[ResolvedParameterInfo] = []
        bindings = component.resolver_bindings or {}
        input_schema = component.input_schema or {}
        defaults = {
            k: v.get("default")
            for k, v in input_schema.get("properties", {}).items()
            if "default" in v
        }

        for key, value in resolved.items():
            if key in bindings:
                resolver_type = bindings[key].get("resolver_type", "unknown")
                source = f"resolver:{resolver_type}"
            elif key in user_params:
                source = "user"
            elif key in defaults:
                source = "default"
            else:
                source = "resolved"
            details.append(ResolvedParameterInfo(key=key, value=value, source=source))

        return ResolvedParametersPreview(parameters=resolved, details=details)

    @strawberry.mutation
    async def execute_deployment(
        self, info: Info, tenant_id: uuid.UUID, deployment_id: uuid.UUID,
    ) -> DeploymentType:
        """Transition deployment to DEPLOYING and start the Temporal workflow."""
        user_id = await check_graphql_permission(
            info, "deployment:deployment:execute", str(tenant_id)
        )

        from app.services.deployment.deployment_service import DeploymentService

        db = await _get_session(info)
        svc = DeploymentService()
        deployment = await svc.get(db, deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        if deployment.status.value not in ("PLANNED", "APPROVED"):
            raise ValueError(
                f"Cannot execute deployment in status {deployment.status.value}. "
                "Must be PLANNED or APPROVED."
            )

        deployment = await svc.transition_status(db, deployment_id, "DEPLOYING")
        await db.commit()

        # Start Temporal workflow (outside the DB session)
        from app.core.config import get_settings
        from app.core.temporal import get_temporal_client

        settings = get_settings()
        client = await get_temporal_client()
        await client.start_workflow(
            "DeploymentExecutionWorkflow",
            str(deployment_id),
            id=f"deploy-{deployment_id}",
            task_queue=settings.temporal_task_queue,
        )

        # Re-fetch to return fresh state
        db = await _get_session(info)
        svc = DeploymentService()
        deployment = await svc.get(db, deployment_id)
        return _deployment_to_type(deployment)
