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
    ) -> list[Deployment]:
        stmt = select(Deployment).where(
            Deployment.tenant_id == tenant_id,
            Deployment.deleted_at.is_(None),
        )
        if environment_id:
            stmt = stmt.where(Deployment.environment_id == environment_id)
        stmt = stmt.order_by(Deployment.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

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
    ) -> DeploymentCI:
        """Link a CI to a deployment."""
        link = DeploymentCI(
            deployment_id=deployment_id,
            ci_id=ci_id,
            component_id=component_id,
            resolver_outputs=resolver_outputs,
            topology_node_id=topology_node_id,
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
