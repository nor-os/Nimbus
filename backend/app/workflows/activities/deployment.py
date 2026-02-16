"""
Overview: Temporal activities for deployment execution — resolve parameters and update status.
Architecture: Deployment workflow activities (Section 9.1)
Dependencies: temporalio, app.services.deployment, app.services.resolver
Concepts: Activities run actual I/O (DB queries, resolver calls) outside the workflow sandbox.
    Includes both legacy resolve_deployment_parameters and new saga-based activities.
"""

from __future__ import annotations

import logging
import uuid

from temporalio import activity

logger = logging.getLogger(__name__)


@activity.defn
async def resolve_deployment_parameters(deployment_id: str) -> dict:
    """Legacy: Load deployment + component + environment, run resolve_all(), persist results."""
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.component import Component
    from app.models.deployment import Deployment
    from app.services.deployment.deployment_service import DeploymentService
    from app.services.resolver.registry import get_resolver_registry

    dep_uuid = uuid.UUID(deployment_id)
    registry = get_resolver_registry()
    svc = DeploymentService()

    async with async_session_factory() as db:
        deployment = await svc.get(db, dep_uuid)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        params = deployment.parameters or {}
        component_id = params.get("component_id")

        if not component_id:
            await svc.set_resolved_parameters(
                db, dep_uuid,
                resolved_parameters=params,
                resolution_status="RESOLVED",
            )
            await db.commit()
            return params

        result = await db.execute(
            select(Component).where(
                Component.id == uuid.UUID(str(component_id)),
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            await svc.set_resolved_parameters(
                db, dep_uuid,
                resolved_parameters={},
                resolution_status="FAILED",
                resolution_error=f"Component {component_id} not found",
            )
            await db.commit()
            raise ValueError(f"Component {component_id} not found")

        user_params = {k: v for k, v in params.items() if k != "component_id"}

        try:
            resolved = await registry.resolve_all(
                component, db, deployment.tenant_id, user_params,
                environment_id=deployment.environment_id,
            )
            await svc.set_resolved_parameters(
                db, dep_uuid,
                resolved_parameters=resolved,
                resolution_status="RESOLVED",
            )
            await db.commit()
            return resolved
        except Exception as e:
            logger.exception("Parameter resolution failed for deployment %s", deployment_id)
            await svc.set_resolved_parameters(
                db, dep_uuid,
                resolved_parameters={},
                resolution_status="FAILED",
                resolution_error=str(e),
            )
            await db.commit()
            raise


@activity.defn
async def update_deployment_status(deployment_id: str, status: str) -> None:
    """Transition a deployment to a new status."""
    from app.db.session import async_session_factory
    from app.services.deployment.deployment_service import DeploymentService

    dep_uuid = uuid.UUID(deployment_id)
    svc = DeploymentService()

    async with async_session_factory() as db:
        await svc.transition_status(db, dep_uuid, status)
        await db.commit()


# ── Saga Activities ────────────────────────────────────────────────────


@activity.defn
async def resolve_parameters_via_rm(deployment_id: str) -> dict:
    """Resolve deployment parameters using the Resource Manager."""
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.component import Component
    from app.services.deployment.deployment_service import DeploymentService
    from app.services.resolver.registry import get_resolver_registry

    dep_uuid = uuid.UUID(deployment_id)
    svc = DeploymentService()
    registry = get_resolver_registry()

    async with async_session_factory() as db:
        deployment = await svc.get(db, dep_uuid)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        params = deployment.parameters or {}
        component_id = params.get("component_id")

        if not component_id:
            await svc.set_resolved_parameters(
                db, dep_uuid,
                resolved_parameters=params,
                resolution_status="RESOLVED",
            )
            await db.commit()
            return params

        result = await db.execute(
            select(Component).where(
                Component.id == uuid.UUID(str(component_id)),
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            raise ValueError(f"Component {component_id} not found")

        # Use Resource Manager for resolution
        rm = registry.get_resource_manager(
            environment_id=deployment.environment_id,
            tenant_id=deployment.tenant_id,
            db=db,
            provider_id=component.provider_id,
        )

        # Resolve each binding individually via RM
        bindings = component.resolver_bindings or {}
        user_params = {k: v for k, v in params.items() if k != "component_id"}

        # Start with defaults + user params
        resolved = {}
        input_schema = component.input_schema or {}
        properties = input_schema.get("properties", {})
        for param_name, param_def in properties.items():
            if "default" in param_def:
                resolved[param_name] = param_def["default"]
        resolved.update(user_params)

        # Resolve bindings via RM
        for param_name, binding in bindings.items():
            resolver_type = binding.get("resolver_type")
            if not resolver_type:
                continue

            resolver_input = binding.get("params", {})
            for key, value in resolver_input.items():
                if isinstance(value, str) and value.startswith("$"):
                    ref_param = value[1:]
                    if ref_param in resolved:
                        resolver_input[key] = resolved[ref_param]

            try:
                output = await rm.resolve(
                    resolver_type, resolver_input,
                    component_id=component.id,
                    deployment_id=dep_uuid,
                )
                target = binding.get("target", param_name)
                if isinstance(output, dict) and isinstance(target, str):
                    resolved[target] = output
                elif isinstance(output, dict):
                    resolved.update(output)
            except Exception:
                logger.exception(
                    "RM resolver '%s' failed for param '%s'", resolver_type, param_name
                )
                raise

        await svc.set_resolved_parameters(
            db, dep_uuid,
            resolved_parameters=resolved,
            resolution_status="RESOLVED",
        )
        await db.commit()
        return resolved


@activity.defn
async def release_all_allocations(deployment_id: str) -> None:
    """Compensation: release all resolver allocations for a deployment."""
    from app.db.session import async_session_factory
    from app.services.deployment.deployment_service import DeploymentService
    from app.services.resolver.registry import get_resolver_registry

    dep_uuid = uuid.UUID(deployment_id)
    svc = DeploymentService()

    async with async_session_factory() as db:
        deployment = await svc.get(db, dep_uuid)
        if not deployment:
            return

        deployment_cis = await svc.get_deployment_cis(db, dep_uuid)
        if not deployment_cis:
            return

        registry = get_resolver_registry()
        rm = registry.get_resource_manager(
            environment_id=deployment.environment_id,
            tenant_id=deployment.tenant_id,
            db=db,
        )

        for dc in deployment_cis:
            resolver_outputs = dc.resolver_outputs or {}
            for resolver_type, output in resolver_outputs.items():
                try:
                    await rm.release(resolver_type, output)
                except Exception:
                    logger.exception(
                        "Failed to release %s allocation for deployment %s",
                        resolver_type, deployment_id,
                    )

        await db.commit()


@activity.defn
async def create_deployment_ci(deployment_id: str) -> str | None:
    """Create a CI for the deployment and link it."""
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.component import Component
    from app.services.deployment.deployment_service import DeploymentService
    from app.services.resolver.registry import get_resolver_registry

    dep_uuid = uuid.UUID(deployment_id)
    svc = DeploymentService()

    async with async_session_factory() as db:
        deployment = await svc.get(db, dep_uuid)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        params = deployment.parameters or {}
        component_id = params.get("component_id")
        if not component_id:
            return None

        component_uuid = uuid.UUID(str(component_id))

        result = await db.execute(
            select(Component).where(
                Component.id == component_uuid,
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            return None

        registry = get_resolver_registry()
        rm = registry.get_resource_manager(
            environment_id=deployment.environment_id,
            tenant_id=deployment.tenant_id,
            db=db,
            provider_id=component.provider_id,
        )

        resolved_params = deployment.resolved_parameters or {}
        ci = await rm.create_ci(
            component_id=component_uuid,
            resolved_params=resolved_params,
            deployment_id=dep_uuid,
        )

        # Collect resolver outputs for the junction
        bindings = component.resolver_bindings or {}
        resolver_outputs = {}
        for param_name, binding in bindings.items():
            resolver_type = binding.get("resolver_type")
            target = binding.get("target", param_name)
            if resolver_type and target in resolved_params:
                resolver_outputs[resolver_type] = resolved_params[target]

        await svc.link_ci(
            db, dep_uuid, ci.id, component_uuid,
            resolver_outputs=resolver_outputs,
        )

        await db.commit()
        return str(ci.id)


@activity.defn
async def delete_deployment_ci(deployment_id: str, ci_id: str) -> None:
    """Compensation: soft-delete a CI created during deployment."""
    from app.db.session import async_session_factory
    from app.services.resolver.registry import get_resolver_registry
    from app.services.deployment.deployment_service import DeploymentService

    dep_uuid = uuid.UUID(deployment_id)
    ci_uuid = uuid.UUID(ci_id)

    async with async_session_factory() as db:
        deployment = DeploymentService()
        dep = await deployment.get(db, dep_uuid)
        if not dep:
            return

        registry = get_resolver_registry()
        rm = registry.get_resource_manager(
            environment_id=dep.environment_id,
            tenant_id=dep.tenant_id,
            db=db,
        )
        await rm.delete_ci(ci_uuid)
        await db.commit()


@activity.defn
async def finalize_deployment(deployment_id: str) -> None:
    """Mark deployment as DEPLOYED and transition CIs to active."""
    from app.db.session import async_session_factory
    from app.services.deployment.deployment_service import DeploymentService
    from app.services.resolver.registry import get_resolver_registry

    dep_uuid = uuid.UUID(deployment_id)
    svc = DeploymentService()

    async with async_session_factory() as db:
        deployment = await svc.get(db, dep_uuid)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Transition all linked CIs to active
        deployment_cis = await svc.get_deployment_cis(db, dep_uuid)
        if deployment_cis:
            registry = get_resolver_registry()
            rm = registry.get_resource_manager(
                environment_id=deployment.environment_id,
                tenant_id=deployment.tenant_id,
                db=db,
            )
            for dc in deployment_cis:
                await rm.update_ci_state(dc.ci_id, "active")

        # Mark deployment as DEPLOYED
        await svc.transition_status(db, dep_uuid, "DEPLOYED")
        await db.commit()
