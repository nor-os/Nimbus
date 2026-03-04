"""
Overview: Component operation service — CRUD for day-2 and deployment operations declared on components.
Architecture: Component service layer (Section 11)
Dependencies: sqlalchemy, app.models.component, app.services.workflow.definition_service
Concepts: Activity-centric model — 3 deployment workflows (deploy, decommission, upgrade) with
    embedded activity nodes (dry-run, validate, rollback). Per-component activities cloned from
    system defaults. Activities resolved by slug at clone time via _resolve_template_activity_slugs().
"""

from __future__ import annotations

import copy
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automated_activity import (
    AutomatedActivity,
    AutomatedActivityVersion,
    OperationKind as ActivityOperationKind,
)
from app.models.component import (
    ComponentOperation,
    EstimatedDowntime,
    OperationCategory,
    OperationKind,
)

logger = logging.getLogger(__name__)

# The 3 deployment operations (workflows) — down from 6
DEPLOYMENT_OPERATIONS = [
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
        "name": "upgrade",
        "display_name": "Upgrade",
        "operation_kind": OperationKind.UPDATE,
        "is_destructive": False,
        "requires_approval": True,
        "estimated_downtime": EstimatedDowntime.BRIEF,
        "sort_order": 2,
    },
]

# The 6 deployment activities to create per component
DEPLOYMENT_ACTIVITY_DEFINITIONS = [
    {
        "name": "Deploy Resource",
        "slug": "deploy-resource",
        "operation_kind": ActivityOperationKind.CREATE,
        "description": "Provision a new infrastructure resource via Pulumi.",
        "timeout_seconds": 3600,
    },
    {
        "name": "Decommission Resource",
        "slug": "decommission-resource",
        "operation_kind": ActivityOperationKind.DELETE,
        "description": "Tear down and decommission an infrastructure resource via Pulumi.",
        "timeout_seconds": 3600,
    },
    {
        "name": "Upgrade Resource",
        "slug": "upgrade-resource",
        "operation_kind": ActivityOperationKind.UPDATE,
        "description": "Update an existing resource in place via Pulumi.",
        "timeout_seconds": 3600,
    },
    {
        "name": "Rollback Resource",
        "slug": "rollback-resource",
        "operation_kind": ActivityOperationKind.RESTORE,
        "description": "Rollback a resource to a previous version via Pulumi.",
        "timeout_seconds": 3600,
    },
    {
        "name": "Dry Run Resource",
        "slug": "dry-run-resource",
        "operation_kind": ActivityOperationKind.READ,
        "description": "Preview deployment changes without applying them.",
        "timeout_seconds": 600,
    },
    {
        "name": "Validate Resource",
        "slug": "validate-resource",
        "operation_kind": ActivityOperationKind.VALIDATE,
        "description": "Validate health and configuration of a deployed resource.",
        "timeout_seconds": 600,
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

    Looks up per-component activities first (by slug + component_id), then falls
    back to system defaults. Also injects component context into parameter_bindings.
    """
    graph = copy.deepcopy(graph)
    nodes = graph.get("nodes", [])

    for node in nodes:
        if node.get("type") != "activity":
            continue

        config = node.get("config", {})
        slug = config.get("activity_slug")
        if not slug or config.get("activity_id"):
            continue

        # Try per-component activity first
        result = await db.execute(
            select(AutomatedActivity).where(
                AutomatedActivity.slug == slug,
                AutomatedActivity.component_id == component_id,
                AutomatedActivity.deleted_at.is_(None),
            )
        )
        activity = result.scalar_one_or_none()

        # Fall back to template (non-component) activity
        if not activity:
            result = await db.execute(
                select(AutomatedActivity).where(
                    AutomatedActivity.slug == slug,
                    AutomatedActivity.is_component_activity.is_(False),
                    AutomatedActivity.component_id.is_(None),
                    AutomatedActivity.deleted_at.is_(None),
                )
            )
            activity = result.scalar_one_or_none()

        if activity:
            config["activity_id"] = str(activity.id)
            logger.debug("Resolved activity slug '%s' → %s", slug, activity.id)
        else:
            logger.warning("Activity with slug '%s' not found", slug)

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
            "name", "display_name", "description",
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

    async def _provision_component_activities(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        provider_id: str | None = None,
        semantic_type_id: str | None = None,
    ) -> dict[str, uuid.UUID]:
        """Create 6 per-component deployment activities cloned from system defaults.

        Returns a mapping of slug → per-component activity ID.
        """
        from app.models.automated_activity import ImplementationType
        from sqlalchemy.orm import selectinload

        MANDATORY_SLUGS = {"deploy-resource", "decommission-resource", "upgrade-resource"}

        activity_map: dict[str, uuid.UUID] = {}

        for activity_def in DEPLOYMENT_ACTIVITY_DEFINITIONS:
            slug = activity_def["slug"]

            # Check if already exists for this component
            result = await db.execute(
                select(AutomatedActivity).where(
                    AutomatedActivity.slug == slug,
                    AutomatedActivity.component_id == component_id,
                    AutomatedActivity.deleted_at.is_(None),
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                activity_map[slug] = existing.id
                continue

            # Find template (non-component) activity to clone from
            result = await db.execute(
                select(AutomatedActivity)
                .options(selectinload(AutomatedActivity.versions))
                .where(
                    AutomatedActivity.slug == slug,
                    AutomatedActivity.is_component_activity.is_(False),
                    AutomatedActivity.component_id.is_(None),
                    AutomatedActivity.deleted_at.is_(None),
                )
            )
            system_activity = result.scalar_one_or_none()

            # Determine forked_at_version from latest published version
            forked_version = None
            if system_activity and system_activity.versions:
                published = [v for v in system_activity.versions if v.published_at]
                if published:
                    forked_version = max(published, key=lambda v: v.version).version
                else:
                    forked_version = max(system_activity.versions, key=lambda v: v.version).version

            # Create per-component activity
            new_activity = AutomatedActivity(
                tenant_id=None,
                name=activity_def["name"],
                slug=slug,
                description=activity_def["description"],
                operation_kind=activity_def["operation_kind"],
                implementation_type=ImplementationType.PULUMI_OPERATION,
                idempotent=slug in ("dry-run-resource", "validate-resource"),
                timeout_seconds=activity_def["timeout_seconds"],
                is_component_activity=True,
                component_id=component_id,
                template_activity_id=system_activity.id if system_activity else None,
                forked_at_version=forked_version,
                is_mandatory=slug in MANDATORY_SLUGS,
                provider_id=uuid.UUID(provider_id) if provider_id else None,
                semantic_type_id=uuid.UUID(semantic_type_id) if semantic_type_id else None,
            )
            db.add(new_activity)
            await db.flush()

            # Clone the latest version from the system activity
            if system_activity and system_activity.versions:
                latest_version = max(system_activity.versions, key=lambda v: v.version)
                new_version = AutomatedActivityVersion(
                    activity_id=new_activity.id,
                    version=1,
                    source_code=latest_version.source_code,
                    input_schema=latest_version.input_schema,
                    output_schema=latest_version.output_schema,
                    config_mutations=latest_version.config_mutations,
                    rollback_mutations=latest_version.rollback_mutations,
                    changelog="Cloned from system default",
                    runtime_config=latest_version.runtime_config,
                )
                db.add(new_version)
                await db.flush()

            activity_map[slug] = new_activity.id
            logger.debug(
                "Created per-component activity '%s' for component %s (forked_at_version=%s, mandatory=%s)",
                slug, component_id, forked_version, slug in MANDATORY_SLUGS,
            )

        return activity_map

    async def provision_deployment_operations(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        tenant_id: str,
        created_by: str,
        provider_id: str | None = None,
        semantic_type_id: str | None = None,
    ) -> list[ComponentOperation]:
        """Auto-provision deployment operations: 6 per-component activities + 3 workflow-backed operations.

        Step A: Create 6 per-component activities (clone from system defaults)
        Step B: Clone 3 workflow templates (deploy, decommission, upgrade)
        Step C: Resolve activity slugs in cloned workflows to per-component activity IDs
        Step D: Create 3 ComponentOperation records
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

        # Step A: Create 6 per-component activities
        await self._provision_component_activities(
            db, component_id,
            provider_id=provider_id,
            semantic_type_id=semantic_type_id,
        )

        wf_service = WorkflowDefinitionService(db)

        # Step B + C + D: Clone 3 workflows and create operations
        operations: list[ComponentOperation] = []
        for op_def in DEPLOYMENT_OPERATIONS:
            # Resolve best-matching template (provider+type → provider → global)
            template = await wf_service.resolve_template(
                operation_name=op_def["name"],
                provider_id=provider_id,
                semantic_type_id=semantic_type_id,
            )
            if not template:
                logger.warning(
                    "Deployment template for '%s' not found, skipping",
                    op_def["name"],
                )
                continue

            # Clone the template workflow for this component
            cloned_wf = await wf_service.clone_from_template(
                tenant_id=tenant_id,
                template_id=str(template.id),
                created_by=created_by,
                name=f"{op_def['name']}:{component_id}{reinit_suffix}",
                description=template.description,
                component_id=str(component_id),
            )

            # Step C: Resolve activity slugs → per-component activity IDs
            if cloned_wf.graph:
                resolved_graph = await _resolve_template_activity_slugs(
                    db, cloned_wf.graph, component_id,
                    provider_id=uuid.UUID(provider_id) if provider_id else None,
                    semantic_type_id=uuid.UUID(semantic_type_id) if semantic_type_id else None,
                )
                cloned_wf.graph = resolved_graph
                await db.flush()

            # Auto-publish cloned workflow so it's ACTIVE v1 (not stuck as DRAFT v0)
            await wf_service.publish(tenant_id, str(cloned_wf.id))

            # Step D: Create operation record
            op = await self.create_operation(
                db,
                component_id=component_id,
                name=op_def["name"],
                display_name=op_def["display_name"],
                workflow_definition_id=cloned_wf.id,
                description=template.description,
                is_destructive=op_def["is_destructive"],
                requires_approval=op_def["requires_approval"],
                estimated_downtime=op_def["estimated_downtime"],
                sort_order=op_def["sort_order"],
                operation_category=OperationCategory.DEPLOYMENT,
                operation_kind=op_def["operation_kind"],
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
            component_id=str(op.component_id),
        )

        # Resolve activity slugs in the cloned graph
        if cloned_wf.graph:
            resolved_graph = await _resolve_template_activity_slugs(
                db, cloned_wf.graph, op.component_id,
            )
            cloned_wf.graph = resolved_graph

        # Auto-publish cloned workflow so it's ACTIVE v1 (not stuck as DRAFT v0)
        await wf_service.publish(tenant_id, str(cloned_wf.id))

        # Soft-delete the old workflow
        if current:
            from datetime import UTC, datetime
            current.deleted_at = datetime.now(UTC)

        op.workflow_definition_id = cloned_wf.id

        # Bump component version after workflow reset
        from app.models.component import Component as ComponentModel

        comp_result = await db.execute(
            select(ComponentModel).where(ComponentModel.id == op.component_id)
        )
        comp = comp_result.scalar_one_or_none()
        if comp:
            comp.version = comp.version + 1

        await db.flush()
        await db.refresh(op)
        return op
