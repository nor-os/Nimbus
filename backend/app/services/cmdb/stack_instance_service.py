"""
Overview: Stack instance service — deploy, manage, and decommission stack instances.
Architecture: Service layer for runtime stack instance management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.stack_instance, app.models.cmdb.service_cluster
Concepts: Stack instances are deployed runtimes of published blueprints. Components
    are resolved from variable bindings during deployment.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.service_cluster import ServiceCluster
from app.models.cmdb.stack_blueprint import StackBlueprintGovernance
from app.models.cmdb.stack_instance import StackInstance, StackInstanceComponent

logger = logging.getLogger(__name__)


class StackInstanceServiceError(Exception):
    def __init__(self, message: str, code: str = "STACK_INSTANCE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StackInstanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_instance(
        self, tenant_id: str, data: dict, user_id: str | None = None
    ) -> StackInstance:
        """Create a PLANNED stack instance from a published blueprint."""
        # Validate blueprint exists and is published
        result = await self.db.execute(
            select(ServiceCluster).where(
                ServiceCluster.id == data["blueprint_id"],
                ServiceCluster.deleted_at.is_(None),
            )
        )
        blueprint = result.scalar_one_or_none()
        if not blueprint:
            raise StackInstanceServiceError("Blueprint not found", "BLUEPRINT_NOT_FOUND")
        if not blueprint.is_published:
            raise StackInstanceServiceError("Blueprint not published", "BLUEPRINT_NOT_PUBLISHED")

        # Check governance
        gov_result = await self.db.execute(
            select(StackBlueprintGovernance).where(
                StackBlueprintGovernance.blueprint_id == data["blueprint_id"],
                StackBlueprintGovernance.tenant_id == tenant_id,
                StackBlueprintGovernance.deleted_at.is_(None),
            )
        )
        gov = gov_result.scalar_one_or_none()
        if gov and not gov.is_allowed:
            raise StackInstanceServiceError(
                "Blueprint not allowed for this tenant", "GOVERNANCE_DENIED"
            )

        # Check max instances if governance limits set
        if gov and gov.max_instances:
            count_result = await self.db.execute(
                select(func.count()).select_from(
                    select(StackInstance).where(
                        StackInstance.blueprint_id == data["blueprint_id"],
                        StackInstance.tenant_id == tenant_id,
                        StackInstance.deleted_at.is_(None),
                        StackInstance.status.notin_(["DECOMMISSIONED", "FAILED"]),
                    ).subquery()
                )
            )
            current = count_result.scalar() or 0
            if current >= gov.max_instances:
                raise StackInstanceServiceError(
                    f"Max instances ({gov.max_instances}) reached", "MAX_INSTANCES"
                )

        # Merge blueprint HA/DR defaults with user overrides
        ha_config = dict(blueprint.ha_config_defaults or {})
        if data.get("ha_config"):
            ha_config.update(data["ha_config"])

        dr_config = dict(blueprint.dr_config_defaults or {})
        if data.get("dr_config"):
            dr_config.update(data["dr_config"])

        instance = StackInstance(
            blueprint_id=data["blueprint_id"],
            blueprint_version=blueprint.version - 1,  # Latest published version
            tenant_id=tenant_id,
            environment_id=data.get("environment_id"),
            name=data["name"],
            status="PLANNED",
            input_values=data.get("input_values"),
            health_status="UNKNOWN",
            deployed_by=user_id,
            ha_config=ha_config or None,
            dr_config=dr_config or None,
        )
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def deploy_instance(
        self, instance_id: uuid.UUID, tenant_id: str
    ) -> StackInstance:
        """Transition PLANNED → PROVISIONING and create component records."""
        instance = await self.get_instance(instance_id, tenant_id)
        if not instance:
            raise StackInstanceServiceError("Instance not found", "INSTANCE_NOT_FOUND")
        if instance.status != "PLANNED":
            raise StackInstanceServiceError(
                f"Cannot deploy from status {instance.status}", "INVALID_STATUS"
            )

        # Load blueprint components
        result = await self.db.execute(
            select(ServiceCluster)
            .where(ServiceCluster.id == instance.blueprint_id)
            .options(selectinload(ServiceCluster.blueprint_components))
        )
        blueprint = result.scalar_one_or_none()

        # Create component instance records
        if blueprint and blueprint.blueprint_components:
            for bc in blueprint.blueprint_components:
                if bc.deleted_at:
                    continue
                comp_instance = StackInstanceComponent(
                    stack_instance_id=instance.id,
                    blueprint_component_id=bc.id,
                    component_id=bc.component_id,
                    status="PENDING",
                    resolved_parameters=bc.default_parameters,
                )
                self.db.add(comp_instance)

        instance.status = "PROVISIONING"
        instance.deployed_at = datetime.now(UTC)
        await self.db.flush()
        return instance

    async def update_instance_status(
        self, instance_id: uuid.UUID, tenant_id: str, status: str
    ) -> StackInstance:
        """Update instance status."""
        instance = await self.get_instance(instance_id, tenant_id)
        if not instance:
            raise StackInstanceServiceError("Instance not found", "INSTANCE_NOT_FOUND")
        instance.status = status
        await self.db.flush()
        return instance

    async def update_health_status(
        self, instance_id: uuid.UUID, tenant_id: str, health_status: str
    ) -> StackInstance:
        """Update instance health status."""
        instance = await self.get_instance(instance_id, tenant_id)
        if not instance:
            raise StackInstanceServiceError("Instance not found", "INSTANCE_NOT_FOUND")
        instance.health_status = health_status
        await self.db.flush()
        return instance

    async def decommission_instance(
        self, instance_id: uuid.UUID, tenant_id: str
    ) -> StackInstance:
        """Mark instance for decommissioning."""
        instance = await self.get_instance(instance_id, tenant_id)
        if not instance:
            raise StackInstanceServiceError("Instance not found", "INSTANCE_NOT_FOUND")
        if instance.status == "DECOMMISSIONED":
            raise StackInstanceServiceError(
                "Instance already decommissioned", "ALREADY_DECOMMISSIONED"
            )
        instance.status = "DECOMMISSIONING"
        await self.db.flush()
        return instance

    async def get_instance(
        self, instance_id: uuid.UUID, tenant_id: str
    ) -> StackInstance | None:
        """Get a stack instance with components."""
        result = await self.db.execute(
            select(StackInstance)
            .where(
                StackInstance.id == instance_id,
                StackInstance.tenant_id == tenant_id,
                StackInstance.deleted_at.is_(None),
            )
            .options(selectinload(StackInstance.instance_components))
        )
        return result.scalar_one_or_none()

    async def list_instances(
        self,
        tenant_id: str,
        blueprint_id: str | None = None,
        environment_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StackInstance], int]:
        """List stack instances with pagination and filtering."""
        base = select(StackInstance).where(
            StackInstance.tenant_id == tenant_id,
            StackInstance.deleted_at.is_(None),
        )

        if blueprint_id:
            base = base.where(StackInstance.blueprint_id == blueprint_id)
        if environment_id:
            base = base.where(StackInstance.environment_id == environment_id)
        if status:
            base = base.where(StackInstance.status == status)

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        query = (
            base
            .options(selectinload(StackInstance.instance_components))
            .order_by(StackInstance.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all()), total
