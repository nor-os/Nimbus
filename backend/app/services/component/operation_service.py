"""
Overview: Component operation service — CRUD for day-2 and deployment operations declared on components.
Architecture: Component service layer (Section 11)
Dependencies: sqlalchemy, app.models.component, app.services.workflow.definition_service
Concepts: Operations are workflow-backed actions on deployed resources. Deployment operations
    (deploy, decommission, rollback, upgrade, validate, dry-run) are auto-provisioned from
    system workflow templates. Activities are referenced by slug in templates and resolved
    to UUIDs at clone time via _resolve_template_activity_slugs().
"""

from __future__ import annotations

import copy
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.component import (
    ComponentOperation,
    EstimatedDowntime,
    OperationCategory,
    OperationKind,
)

logger = logging.getLogger(__name__)

# The 6 standard deployment operations and their defaults
DEPLOYMENT_ACTIVITIES = [
    {
        "name": "deploy",
        "display_name": "Deploy",
        "operation_kind": OperationKind.CREATE,
        "is_destructive": False,
        "requires_approval": True,
        "estimated_downtime": EstimatedDowntime.EXTENDED,
        "sort_order": 0,
    },
    {
        "name": "decommission",
        "display_name": "Decommission",
        "operation_kind": OperationKind.DELETE,
        "is_destructive": True,
        "requires_approval": True,
        "estimated_downtime": EstimatedDowntime.EXTENDED,
        "sort_order": 1,
    },
    {
        "name": "rollback",
        "display_name": "Rollback",
        "operation_kind": OperationKind.RESTORE,
        "is_destructive": True,
        "requires_approval": True,
        "estimated_downtime": EstimatedDowntime.BRIEF,
        "sort_order": 2,
    },
    {
        "name": "upgrade",
        "display_name": "Upgrade",
        "operation_kind": OperationKind.UPDATE,
        "is_destructive": False,
        "requires_approval": True,
        "estimated_downtime": EstimatedDowntime.BRIEF,
        "sort_order": 3,
    },
    {
        "name": "validate",
        "display_name": "Validate",
        "operation_kind": OperationKind.VALIDATE,
        "is_destructive": False,
        "requires_approval": False,
        "estimated_downtime": EstimatedDowntime.NONE,
        "sort_order": 4,
    },
    {
        "name": "dry-run",
        "display_name": "Dry Run",
        "operation_kind": OperationKind.READ,
        "is_destructive": False,
        "requires_approval": False,
        "estimated_downtime": EstimatedDowntime.NONE,
        "sort_order": 5,
    },
]


async def _resolve_template_activity_slugs(
    db: AsyncSession,
    graph: dict,
    component_id: uuid.UUID,
    provider_id: uuid.UUID | None = None,
    semantic_type_id: uuid.UUID | None = None,
) -> dict:
    """Resolve activity_slug references in a cloned workflow graph to activity_id UUIDs.

    Iterates activity nodes in the graph, looks up each activity_slug against
    the system activity catalog, and populates activity_id. Also injects
    component context into parameter_bindings where $input references exist.
    """
    from app.models.automated_activity import AutomatedActivity

    graph = copy.deepcopy(graph)
    nodes = graph.get("nodes", [])

    for node in nodes:
        if node.get("type") != "activity":
            continue

        data = node.get("data", {})
        slug = data.get("activity_slug")
        if not slug or data.get("activity_id"):
            continue

        # Resolve slug to activity UUID
        result = await db.execute(
            select(AutomatedActivity).where(
                AutomatedActivity.slug == slug,
                AutomatedActivity.is_system.is_(True),
                AutomatedActivity.deleted_at.is_(None),
            )
        )
        activity = result.scalar_one_or_none()
        if activity:
            data["activity_id"] = str(activity.id)
            logger.debug("Resolved activity slug '%s' → %s", slug, activity.id)
        else:
            logger.warning("System activity with slug '%s' not found", slug)

    return graph


class ComponentOperationService:
    """Service for managing component operations (deployment + day-2)."""

    async def list_operations(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        category: str | None = None,
    ) -> list[ComponentOperation]:
        query = (
            select(ComponentOperation)
            .where(
                ComponentOperation.component_id == component_id,
                ComponentOperation.deleted_at.is_(None),
            )
            .order_by(ComponentOperation.sort_order, ComponentOperation.name)
        )
        if category:
            query = query.where(
                ComponentOperation.operation_category == OperationCategory(category)
            )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
    ) -> ComponentOperation | None:
        result = await db.execute(
            select(ComponentOperation).where(
                ComponentOperation.id == operation_id,
                ComponentOperation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_operation(
        self,
        db: AsyncSession,
        *,
        component_id: uuid.UUID,
        name: str,
        display_name: str,
        workflow_definition_id: uuid.UUID,
        description: str | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        is_destructive: bool = False,
        requires_approval: bool = False,
        estimated_downtime: EstimatedDowntime = EstimatedDowntime.NONE,
        sort_order: int = 0,
        operation_category: OperationCategory = OperationCategory.DAY2,
        operation_kind: OperationKind | None = None,
    ) -> ComponentOperation:
        op = ComponentOperation(
            component_id=component_id,
            name=name,
            display_name=display_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            workflow_definition_id=workflow_definition_id,
            is_destructive=is_destructive,
            requires_approval=requires_approval,
            estimated_downtime=estimated_downtime,
            sort_order=sort_order,
            operation_category=operation_category,
            operation_kind=operation_kind,
        )
        db.add(op)
        await db.flush()
        await db.refresh(op)
        return op

    async def update_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
        **kwargs,
    ) -> ComponentOperation:
        op = await self.get_operation(db, operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found")

        allowed = {
            "name", "display_name", "description", "input_schema", "output_schema",
            "workflow_definition_id", "is_destructive", "requires_approval",
            "estimated_downtime", "sort_order",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(op, key, value)

        await db.flush()
        await db.refresh(op)
        return op

    async def delete_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
    ) -> None:
        from sqlalchemy import func

        op = await self.get_operation(db, operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found")

        if op.operation_category == OperationCategory.DEPLOYMENT:
            raise ValueError(
                "Cannot delete deployment operations. Use 'Reset to Default' to restore the template workflow."
            )

        op.deleted_at = func.now()
        await db.flush()

    async def provision_deployment_operations(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: str,
        created_by: str,
        provider_id: str | None = None,
        semantic_type_id: str | None = None,
    ) -> list[ComponentOperation]:
        """Auto-provision 6 deployment operations by cloning system workflow templates.

        If deployment operations already exist for this component, they are soft-deleted
        first and re-created fresh. Activity nodes in the cloned template graphs are
        resolved from slug to UUID via the system activity catalog.
        """
        import time
        from datetime import UTC, datetime

        from app.services.workflow.definition_service import WorkflowDefinitionService

        # Soft-delete any existing deployment operations for this component
        existing = await self.list_operations(db, component_id, category="DEPLOYMENT")
        reinit_suffix = f"-{int(time.time())}" if existing else ""
        if existing:
            now = datetime.now(UTC)
            for old_op in existing:
                old_op.deleted_at = now
            await db.flush()
            logger.info(
                "Soft-deleted %d existing deployment operations for component %s",
                len(existing),
                component_id,
            )

        wf_service = WorkflowDefinitionService(db)

        operations: list[ComponentOperation] = []
        for activity_def in DEPLOYMENT_ACTIVITIES:
            # Resolve best-matching template (provider+type → provider → global)
            template = await wf_service.resolve_template(
                operation_name=activity_def["name"],
                provider_id=provider_id,
                semantic_type_id=semantic_type_id,
            )
            if not template:
                logger.warning(
                    "Deployment template for '%s' not found, skipping",
                    activity_def["name"],
                )
                continue

            # Clone the template workflow for this component
            cloned_wf = await wf_service.clone_from_template(
                tenant_id=tenant_id,
                template_id=str(template.id),
                created_by=created_by,
                name=f"{activity_def['name']}:{component_id}{reinit_suffix}",
                description=template.description,
            )

            # Resolve activity slugs in the cloned graph to UUIDs
            if cloned_wf.graph:
                resolved_graph = await _resolve_template_activity_slugs(
                    db, cloned_wf.graph, component_id,
                    provider_id=uuid.UUID(provider_id) if provider_id else None,
                    semantic_type_id=uuid.UUID(semantic_type_id) if semantic_type_id else None,
                )
                cloned_wf.graph = resolved_graph
                await db.flush()

            op = await self.create_operation(
                db,
                component_id=component_id,
                name=activity_def["name"],
                display_name=activity_def["display_name"],
                workflow_definition_id=cloned_wf.id,
                description=template.description,
                is_destructive=activity_def["is_destructive"],
                requires_approval=activity_def["requires_approval"],
                estimated_downtime=activity_def["estimated_downtime"],
                sort_order=activity_def["sort_order"],
                operation_category=OperationCategory.DEPLOYMENT,
                operation_kind=activity_def["operation_kind"],
            )
            operations.append(op)

        return operations

    async def reset_deployment_workflow(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
        tenant_id: str,
        user_id: str,
    ) -> ComponentOperation:
        """Re-clone a deployment operation's workflow from the best-matching template."""
        from app.models.workflow_definition import WorkflowDefinition
        from app.services.workflow.definition_service import WorkflowDefinitionService

        op = await self.get_operation(db, operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found")
        if op.operation_category != OperationCategory.DEPLOYMENT:
            raise ValueError("Only deployment operations can be reset to default")

        wf_service = WorkflowDefinitionService(db)

        # Find the current workflow's template source
        current_wf = await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == op.workflow_definition_id,
            )
        )
        current = current_wf.scalar_one_or_none()

        # Determine the template to clone from
        template_id = None
        if current and current.template_source_id:
            template_id = str(current.template_source_id)
        else:
            # Fallback: resolve via the template resolution chain
            template = await wf_service.resolve_template(operation_name=op.name)
            if template:
                template_id = str(template.id)

        if not template_id:
            raise ValueError(
                f"Cannot find template for deployment operation '{op.name}'"
            )

        import time

        cloned_wf = await wf_service.clone_from_template(
            tenant_id=tenant_id,
            template_id=template_id,
            created_by=user_id,
            name=f"{op.name}:{op.component_id}-{int(time.time())}",
            description=op.description,
        )

        # Resolve activity slugs in the cloned graph
        if cloned_wf.graph:
            resolved_graph = await _resolve_template_activity_slugs(
                db, cloned_wf.graph, op.component_id,
            )
            cloned_wf.graph = resolved_graph

        # Soft-delete the old workflow
        if current:
            from datetime import UTC, datetime
            current.deleted_at = datetime.now(UTC)

        op.workflow_definition_id = cloned_wf.id

        await db.flush()
        await db.refresh(op)
        return op

    # Future extension points:
    # - Per-deployment instance workflow overrides: add `workflow_override_graph` column
    #   on the deployments table to allow instance-specific customization without
    #   modifying the component-level operation workflow.
    # - Copy-on-write custom activities: clone a system activity (e.g. deploy-resource)
    #   to tenant scope for per-tenant customization while preserving the system original.
    # - Pulumi executor implementation: Phase 12 will implement the actual
    #   PULUMI_OPERATION executor that runs `pulumi up/destroy/preview` via the
    #   Automation API, replacing the stub source_code in activity versions.
