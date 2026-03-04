"""
Overview: Stack workflow service — manage workflow bindings and build stack context.
Architecture: Service layer for stack operational workflows (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.stack_blueprint
Concepts: Operational workflows (provision, deprovision, scale, backup, etc.) are bound
    to blueprints. Stack context is assembled for workflow execution injection.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.stack_blueprint import StackWorkflow
from app.models.cmdb.stack_instance import StackInstance

logger = logging.getLogger(__name__)


class StackWorkflowServiceError(Exception):
    def __init__(self, message: str, code: str = "STACK_WORKFLOW_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StackWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workflow(
        self, workflow_id: uuid.UUID
    ) -> StackWorkflow | None:
        """Get a stack workflow by ID."""
        result = await self.db.execute(
            select(StackWorkflow).where(
                StackWorkflow.id == workflow_id,
                StackWorkflow.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_workflows(
        self, blueprint_id: uuid.UUID, workflow_kind: str | None = None
    ) -> list[StackWorkflow]:
        """List workflows for a blueprint, optionally filtered by kind."""
        base = select(StackWorkflow).where(
            StackWorkflow.blueprint_id == blueprint_id,
            StackWorkflow.deleted_at.is_(None),
        )
        if workflow_kind:
            base = base.where(StackWorkflow.workflow_kind == workflow_kind)

        result = await self.db.execute(base.order_by(StackWorkflow.sort_order))
        return list(result.scalars().all())

    async def build_stack_context(
        self, instance_id: uuid.UUID, tenant_id: str
    ) -> dict:
        """Assemble full stack context for workflow execution injection."""
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(StackInstance)
            .where(
                StackInstance.id == instance_id,
                StackInstance.tenant_id == tenant_id,
                StackInstance.deleted_at.is_(None),
            )
            .options(selectinload(StackInstance.instance_components))
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise StackWorkflowServiceError("Instance not found", "INSTANCE_NOT_FOUND")

        return {
            "stack_instance_id": str(instance.id),
            "blueprint_id": str(instance.blueprint_id),
            "blueprint_version": instance.blueprint_version,
            "tenant_id": str(instance.tenant_id),
            "environment_id": str(instance.environment_id) if instance.environment_id else None,
            "name": instance.name,
            "status": instance.status,
            "health_status": instance.health_status,
            "input_values": instance.input_values or {},
            "output_values": instance.output_values or {},
            "ha_config": instance.ha_config or {},
            "dr_config": instance.dr_config or {},
            "components": [
                {
                    "id": str(c.id),
                    "component_id": str(c.component_id),
                    "status": c.status,
                    "resolved_parameters": c.resolved_parameters or {},
                    "outputs": c.outputs or {},
                }
                for c in (instance.instance_components or [])
            ],
        }

    async def execute_stack_workflow(
        self,
        instance_id: uuid.UUID,
        tenant_id: str,
        workflow_kind: str,
        config_overrides: dict | None = None,
    ) -> dict:
        """Trigger a bound workflow for an instance with HA/DR config merged with overrides."""
        instance_result = await self.db.execute(
            select(StackInstance).where(
                StackInstance.id == instance_id,
                StackInstance.tenant_id == tenant_id,
                StackInstance.deleted_at.is_(None),
            )
        )
        instance = instance_result.scalar_one_or_none()
        if not instance:
            raise StackWorkflowServiceError("Instance not found", "INSTANCE_NOT_FOUND")

        # Find the bound workflow of the requested kind
        wf_result = await self.db.execute(
            select(StackWorkflow).where(
                StackWorkflow.blueprint_id == instance.blueprint_id,
                StackWorkflow.workflow_kind == workflow_kind,
                StackWorkflow.deleted_at.is_(None),
            ).order_by(StackWorkflow.sort_order).limit(1)
        )
        workflow = wf_result.scalar_one_or_none()
        if not workflow:
            raise StackWorkflowServiceError(
                f"No {workflow_kind} workflow bound to blueprint",
                "WORKFLOW_NOT_FOUND",
            )

        # Build context with HA/DR config, merging any overrides
        context = await self.build_stack_context(instance_id, tenant_id)
        if config_overrides:
            if "ha_config" in config_overrides:
                context["ha_config"] = {**context["ha_config"], **config_overrides["ha_config"]}
            if "dr_config" in config_overrides:
                context["dr_config"] = {**context["dr_config"], **config_overrides["dr_config"]}

        logger.info(
            "Executing stack workflow: kind=%s, instance=%s, workflow_def=%s",
            workflow_kind, instance_id, workflow.workflow_definition_id,
        )

        return {
            "workflow_definition_id": str(workflow.workflow_definition_id),
            "workflow_kind": workflow_kind,
            "stack_context": context,
            "status": "TRIGGERED",
        }
