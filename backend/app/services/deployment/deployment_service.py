"""
Overview: Deployment service — CRUD for topology-to-environment deployments.
Architecture: Deployment service layer (Section 6)
Dependencies: sqlalchemy, app.models.deployment
Concepts: Deployment lifecycle (PLANNED→DEPLOYED), tenant scoping, soft deletes
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment, DeploymentCI, DeploymentStatus


class DeploymentService:

    async def create(
        self, db: AsyncSession, *, tenant_id: uuid.UUID,
        environment_id: uuid.UUID, topology_id: uuid.UUID,
        name: str, deployed_by: uuid.UUID,
        description: str | None = None,
        parameters: dict | None = None,
    ) -> Deployment:
        deployment = Deployment(
            tenant_id=tenant_id,
            environment_id=environment_id,
            topology_id=topology_id,
            name=name,
            description=description,
            status=DeploymentStatus.PLANNED,
            parameters=parameters,
            deployed_by=deployed_by,
        )
        db.add(deployment)
        await db.flush()
        await db.refresh(deployment)
        return deployment

    async def get(self, db: AsyncSession, deployment_id: uuid.UUID) -> Deployment | None:
        result = await db.execute(
            select(Deployment)
            .where(Deployment.id == deployment_id, Deployment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        environment_id: uuid.UUID | None = None,
        has_topology: bool | None = None,
    ) -> list[Deployment]:
        stmt = select(Deployment).where(
            Deployment.tenant_id == tenant_id,
            Deployment.deleted_at.is_(None),
        )
        if environment_id:
            stmt = stmt.where(Deployment.environment_id == environment_id)
        if has_topology is True:
            stmt = stmt.where(Deployment.topology_id.isnot(None))
        elif has_topology is False:
            stmt = stmt.where(Deployment.topology_id.is_(None))
        stmt = stmt.order_by(Deployment.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_component_instances(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        environment_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Return unified component instances from deployments and stack instances."""
        from app.models.cmdb.stack_instance import StackInstance, StackInstanceComponent
        from app.models.component import Component

        results: list[dict] = []

        # 1. DeploymentCI-based instances (standalone + topology)
        stmt = (
            select(
                DeploymentCI.id,
                DeploymentCI.component_id,
                DeploymentCI.component_version,
                DeploymentCI.resolver_outputs,
                DeploymentCI.created_at,
                Component.display_name.label("component_display_name"),
                Deployment.id.label("deployment_id"),
                Deployment.name.label("deployment_name"),
                Deployment.environment_id,
                Deployment.topology_id,
                Deployment.status,
                Deployment.deployed_at,
            )
            .join(Deployment, Deployment.id == DeploymentCI.deployment_id)
            .join(Component, Component.id == DeploymentCI.component_id)
            .where(
                Deployment.tenant_id == tenant_id,
                Deployment.deleted_at.is_(None),
            )
        )
        if environment_id:
            stmt = stmt.where(Deployment.environment_id == environment_id)
        result = await db.execute(stmt)
        for row in result.all():
            source_type = "topology" if row.topology_id else "standalone"
            results.append({
                "id": row.id,
                "component_id": row.component_id,
                "component_display_name": row.component_display_name,
                "component_version": row.component_version,
                "environment_id": row.environment_id,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "source_type": source_type,
                "source_id": row.deployment_id,
                "source_name": row.deployment_name,
                "resolved_parameters": row.resolver_outputs,
                "outputs": None,
                "deployed_at": row.deployed_at,
                "created_at": row.created_at,
            })

        # 2. StackInstanceComponent-based instances
        stmt2 = (
            select(
                StackInstanceComponent.id,
                StackInstanceComponent.component_id,
                StackInstanceComponent.component_version,
                StackInstanceComponent.status,
                StackInstanceComponent.resolved_parameters,
                StackInstanceComponent.outputs,
                StackInstanceComponent.created_at,
                Component.display_name.label("component_display_name"),
                StackInstance.id.label("stack_instance_id"),
                StackInstance.name.label("stack_instance_name"),
                StackInstance.environment_id,
                StackInstance.deployed_at,
            )
            .join(StackInstance, StackInstance.id == StackInstanceComponent.stack_instance_id)
            .join(Component, Component.id == StackInstanceComponent.component_id)
            .where(
                StackInstance.tenant_id == tenant_id,
                StackInstance.deleted_at.is_(None),
            )
        )
        if environment_id:
            stmt2 = stmt2.where(StackInstance.environment_id == environment_id)
        result2 = await db.execute(stmt2)
        for row in result2.all():
            results.append({
                "id": row.id,
                "component_id": row.component_id,
                "component_display_name": row.component_display_name,
                "component_version": row.component_version,
                "environment_id": row.environment_id,
                "status": row.status,
                "source_type": "stack",
                "source_id": row.stack_instance_id,
                "source_name": row.stack_instance_name,
                "resolved_parameters": row.resolved_parameters,
                "outputs": row.outputs,
                "deployed_at": row.deployed_at,
                "created_at": row.created_at,
            })

        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results

    async def update(self, db: AsyncSession, deployment_id: uuid.UUID, **kwargs) -> Deployment:
        deployment = await self.get(db, deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        for key, value in kwargs.items():
            if hasattr(deployment, key) and key not in ("id", "tenant_id", "environment_id", "topology_id", "created_at", "deployed_by"):
                setattr(deployment, key, value)
        await db.flush()
        await db.refresh(deployment)
        return deployment

    async def set_resolved_parameters(
        self, db: AsyncSession, deployment_id: uuid.UUID,
        resolved_parameters: dict, resolution_status: str = "RESOLVED",
        resolution_error: str | None = None,
    ) -> Deployment:
        deployment = await self.get(db, deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        deployment.resolved_parameters = resolved_parameters
        deployment.resolution_status = resolution_status
        deployment.resolution_error = resolution_error
        await db.flush()
        await db.refresh(deployment)
        return deployment

    async def transition_status(
        self, db: AsyncSession, deployment_id: uuid.UUID, new_status: str,
    ) -> Deployment:
        deployment = await self.get(db, deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        deployment.status = DeploymentStatus(new_status)
        if new_status == "DEPLOYED":
            deployment.deployed_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(deployment)
        return deployment

    async def delete(self, db: AsyncSession, deployment_id: uuid.UUID) -> None:
        deployment = await self.get(db, deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        deployment.deleted_at = datetime.now(timezone.utc)
        await db.flush()

    # ── Deployment-CI Linkage ──────────────────────────────────────────

    async def link_ci(
        self,
        db: AsyncSession,
        deployment_id: uuid.UUID,
        ci_id: uuid.UUID,
        component_id: uuid.UUID,
        resolver_outputs: dict | None = None,
        topology_node_id: str | None = None,
        component_version: int | None = None,
    ) -> DeploymentCI:
        """Link a CI to a deployment.

        If component_version is not provided, auto-resolves to the component's
        latest published version (or current version if none published).
        """
        if component_version is None:
            from sqlalchemy import func

            from app.models.component import Component, ComponentVersion

            # Try latest published version first
            result = await db.execute(
                select(func.max(ComponentVersion.version)).where(
                    ComponentVersion.component_id == component_id,
                )
            )
            max_published = result.scalar_one_or_none()
            if max_published is not None:
                component_version = max_published
            else:
                # Fall back to component.version
                result = await db.execute(
                    select(Component.version).where(Component.id == component_id)
                )
                component_version = result.scalar_one_or_none() or 1

        link = DeploymentCI(
            deployment_id=deployment_id,
            ci_id=ci_id,
            component_id=component_id,
            resolver_outputs=resolver_outputs,
            topology_node_id=topology_node_id,
            component_version=component_version,
        )
        db.add(link)
        await db.flush()
        await db.refresh(link)
        return link

    async def get_deployment_cis(
        self, db: AsyncSession, deployment_id: uuid.UUID,
    ) -> list[DeploymentCI]:
        """Get all CIs linked to a deployment."""
        result = await db.execute(
            select(DeploymentCI)
            .where(DeploymentCI.deployment_id == deployment_id)
            .order_by(DeploymentCI.created_at)
        )
        return list(result.scalars().all())

    async def get_ci_deployments(
        self, db: AsyncSession, ci_id: uuid.UUID,
    ) -> list[Deployment]:
        """Get all deployments linked to a CI (reverse lookup)."""
        result = await db.execute(
            select(Deployment)
            .join(DeploymentCI, DeploymentCI.deployment_id == Deployment.id)
            .where(
                DeploymentCI.ci_id == ci_id,
                Deployment.deleted_at.is_(None),
            )
            .order_by(Deployment.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Upgrade Detection ──────────────────────────────────────────────

    async def check_upgradable_cis(
        self, db: AsyncSession, environment_id: uuid.UUID,
    ) -> list[dict]:
        """Find deployed CIs where a newer component version is available.

        Returns list of dicts with deployment_ci_id, ci_id, component_id,
        component_display_name, deployed_version, latest_version, deployment_id, changelog.
        """
        from sqlalchemy import func

        from app.models.component import Component, ComponentVersion

        # Subquery: max published version per component
        max_version_sq = (
            select(
                ComponentVersion.component_id,
                func.max(ComponentVersion.version).label("max_version"),
            )
            .group_by(ComponentVersion.component_id)
            .subquery()
        )

        # Main query: find deployment_cis where deployed_version < max published version
        stmt = (
            select(
                DeploymentCI.id.label("deployment_ci_id"),
                DeploymentCI.ci_id,
                DeploymentCI.component_id,
                Component.display_name.label("component_display_name"),
                DeploymentCI.component_version.label("deployed_version"),
                max_version_sq.c.max_version.label("latest_version"),
                DeploymentCI.deployment_id,
            )
            .join(Deployment, Deployment.id == DeploymentCI.deployment_id)
            .join(Component, Component.id == DeploymentCI.component_id)
            .join(
                max_version_sq,
                max_version_sq.c.component_id == DeploymentCI.component_id,
            )
            .where(
                Deployment.environment_id == environment_id,
                Deployment.status == DeploymentStatus.DEPLOYED,
                Deployment.deleted_at.is_(None),
                DeploymentCI.component_version.isnot(None),
                DeploymentCI.component_version < max_version_sq.c.max_version,
            )
        )

        result = await db.execute(stmt)
        rows = result.all()

        upgradable = []
        for row in rows:
            # Get latest changelog
            changelog_result = await db.execute(
                select(ComponentVersion.changelog).where(
                    ComponentVersion.component_id == row.component_id,
                    ComponentVersion.version == row.latest_version,
                )
            )
            changelog = changelog_result.scalar_one_or_none()

            upgradable.append({
                "deployment_ci_id": row.deployment_ci_id,
                "ci_id": row.ci_id,
                "component_id": row.component_id,
                "component_display_name": row.component_display_name,
                "deployed_version": row.deployed_version,
                "latest_version": row.latest_version,
                "deployment_id": row.deployment_id,
                "changelog": changelog,
            })

        return upgradable

    async def update_ci_version(
        self, db: AsyncSession, deployment_ci_id: uuid.UUID, target_version: int,
    ) -> DeploymentCI:
        """Update the component_version on a DeploymentCI record."""
        result = await db.execute(
            select(DeploymentCI).where(DeploymentCI.id == deployment_ci_id)
        )
        dc = result.scalar_one_or_none()
        if not dc:
            raise ValueError(f"DeploymentCI {deployment_ci_id} not found")
        dc.component_version = target_version
        await db.flush()
        await db.refresh(dc)
        return dc

    async def trigger_component_upgrade(
        self, db: AsyncSession, deployment_ci_id: uuid.UUID,
        target_version: int | None = None,
    ) -> DeploymentCI:
        """Upgrade a deployed component to a newer version (plumbing only — no Temporal yet).

        Validates the version delta, confirms the upgrade workflow exists,
        then updates the DeploymentCI.component_version directly.
        """
        from sqlalchemy import func

        from app.models.component import Component, ComponentOperation, ComponentVersion

        # 1. Look up the DeploymentCI
        result = await db.execute(
            select(DeploymentCI).where(DeploymentCI.id == deployment_ci_id)
        )
        dc = result.scalar_one_or_none()
        if not dc:
            raise ValueError(f"DeploymentCI {deployment_ci_id} not found")

        component_id = dc.component_id

        # 2. Resolve target_version if not provided
        if target_version is None:
            result = await db.execute(
                select(func.max(ComponentVersion.version)).where(
                    ComponentVersion.component_id == component_id,
                )
            )
            target_version = result.scalar_one_or_none()
            if target_version is None:
                raise ValueError("No published versions found for this component")

        # 3. Validate version delta
        current_version = dc.component_version or 0
        if target_version <= current_version:
            raise ValueError(
                f"Target version {target_version} is not newer than "
                f"deployed version {current_version}"
            )

        # 4. Confirm upgrade workflow exists
        from app.models.component import OperationKind as CompOperationKind

        result = await db.execute(
            select(ComponentOperation).where(
                ComponentOperation.component_id == component_id,
                ComponentOperation.operation_kind == CompOperationKind.UPDATE,
                ComponentOperation.deleted_at.is_(None),
            )
        )
        upgrade_op = result.scalar_one_or_none()
        if not upgrade_op:
            raise ValueError(
                "No upgrade workflow defined for this component. "
                "Cannot trigger upgrade."
            )

        # 5. TODO (Phase 12): Start Temporal workflow execution with context
        # For now: directly update the version
        dc.component_version = target_version
        await db.flush()
        await db.refresh(dc)
        return dc

    async def deploy_component(
        self, db: AsyncSession, *, tenant_id: uuid.UUID,
        environment_id: uuid.UUID, component_id: uuid.UUID,
        deployed_by: uuid.UUID,
        component_version: int | None = None,
        parameters: dict | None = None,
    ) -> Deployment:
        """Deploy a single component into an environment (no topology required).

        Creates a Deployment record and a DeploymentCI record. Plumbing only —
        no Temporal execution yet.
        """
        from sqlalchemy import func

        from app.models.component import Component, ComponentVersion

        # Validate component exists
        result = await db.execute(
            select(Component).where(
                Component.id == component_id,
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            raise ValueError(f"Component {component_id} not found")

        # Resolve version
        if component_version is None:
            result = await db.execute(
                select(func.max(ComponentVersion.version)).where(
                    ComponentVersion.component_id == component_id,
                )
            )
            component_version = result.scalar_one_or_none()
            if component_version is None:
                component_version = component.version

        # Create deployment (topology_id=None for component-only deployments)
        deployment = Deployment(
            tenant_id=tenant_id,
            environment_id=environment_id,
            topology_id=None,
            name=f"component-deploy-{component.display_name}",
            description=f"Direct component deployment: {component.display_name} v{component_version}",
            status=DeploymentStatus.DEPLOYED,
            parameters=parameters,
            deployed_by=deployed_by,
        )
        db.add(deployment)
        await db.flush()

        # Create DeploymentCI (ci_id=None — real CI created by Temporal in Phase 12)
        dc = DeploymentCI(
            deployment_id=deployment.id,
            ci_id=None,
            component_id=component_id,
            component_version=component_version,
        )
        db.add(dc)
        await db.flush()
        await db.refresh(deployment)
        return deployment
