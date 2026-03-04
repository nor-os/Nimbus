"""
Overview: Service cluster service — CRUD for blueprint clusters, versioning, components,
    variable bindings, governance, and operational workflows.
Architecture: Service layer for cluster management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_cluster, app.models.cmdb.stack_blueprint
Concepts: Clusters are pure blueprint templates defining slot shapes. CI assignment
    happens at deployment time, not on the blueprint itself.
    Evolved to full stack blueprints with versioning, composition, and governance.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.service_cluster import (
    ServiceCluster,
    ServiceClusterSlot,
)
from app.models.cmdb.stack_blueprint import (
    StackBlueprintComponent,
    StackBlueprintGovernance,
    StackBlueprintVersion,
    StackVariableBinding,
    StackWorkflow,
)

logger = logging.getLogger(__name__)


class ClusterServiceError(Exception):
    def __init__(self, message: str, code: str = "CLUSTER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ClusterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Cluster CRUD ──────────────────────────────────────────────────

    async def create_cluster(
        self, tenant_id: str, data: dict, user_id: str | None = None
    ) -> ServiceCluster:
        """Create a service cluster with optional inline slots."""
        existing = await self.db.execute(
            select(ServiceCluster).where(
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.name == data["name"],
                ServiceCluster.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ClusterServiceError(
                f"Cluster '{data['name']}' already exists", "CLUSTER_EXISTS"
            )

        cluster = ServiceCluster(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            cluster_type=data.get("cluster_type", "service_cluster"),
            architecture_topology_id=data.get("architecture_topology_id"),
            topology_node_id=data.get("topology_node_id"),
            tags=data.get("tags", {}),
            stack_tag_key=data.get("stack_tag_key"),
            metadata_=data.get("metadata"),
            provider_id=data.get("provider_id"),
            category=data.get("category"),
            icon=data.get("icon"),
            input_schema=data.get("input_schema"),
            output_schema=data.get("output_schema"),
            display_name=data.get("display_name"),
            ha_config_schema=data.get("ha_config_schema"),
            ha_config_defaults=data.get("ha_config_defaults"),
            dr_config_schema=data.get("dr_config_schema"),
            dr_config_defaults=data.get("dr_config_defaults"),
            created_by=user_id,
        )
        self.db.add(cluster)
        await self.db.flush()

        # Create inline slots if provided
        for i, slot_data in enumerate(data.get("slots", [])):
            slot = ServiceClusterSlot(
                cluster_id=cluster.id,
                name=slot_data["name"],
                display_name=slot_data.get("display_name", slot_data["name"]),
                description=slot_data.get("description"),
                allowed_ci_class_ids=slot_data.get("allowed_ci_class_ids"),
                semantic_category_id=slot_data.get("semantic_category_id"),
                semantic_type_id=slot_data.get("semantic_type_id"),
                min_count=slot_data.get("min_count", 1),
                max_count=slot_data.get("max_count"),
                is_required=slot_data.get("is_required", True),
                sort_order=slot_data.get("sort_order", i),
            )
            self.db.add(slot)

        await self.db.flush()

        # Auto-create mandatory lifecycle workflows (PROVISION, DEPROVISION, UPDATE)
        try:
            await self.provision_stack_workflows(cluster.id, tenant_id, user_id)
        except Exception:
            logger.warning("Failed to auto-provision workflows for cluster %s", cluster.id)

        return await self.get_cluster(cluster.id, tenant_id)

    async def update_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceCluster:
        """Partial update of a service cluster."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        for key in ("name", "description", "cluster_type",
                     "tags", "stack_tag_key", "architecture_topology_id", "topology_node_id",
                     "provider_id", "category", "icon", "input_schema", "output_schema",
                     "display_name", "ha_config_schema", "ha_config_defaults",
                     "dr_config_schema", "dr_config_defaults"):
            if key in data:
                setattr(cluster, key, data[key])
        if "metadata" in data:
            cluster.metadata_ = data["metadata"]

        await self.db.flush()
        return cluster

    async def delete_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a cluster and cascade to slots."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        now = datetime.now(UTC)
        cluster.deleted_at = now
        for slot in cluster.slots:
            slot.deleted_at = now

        await self.db.flush()
        return True

    async def get_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> ServiceCluster | None:
        """Get a cluster with slots eagerly loaded."""
        result = await self.db.execute(
            select(ServiceCluster)
            .where(
                ServiceCluster.id == cluster_id,
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.deleted_at.is_(None),
            )
            .options(
                selectinload(ServiceCluster.slots),
            )
        )
        return result.scalar_one_or_none()

    async def list_clusters(
        self,
        tenant_id: str,
        cluster_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
        category: str | None = None,
        is_published: bool | None = None,
        provider_id: str | None = None,
    ) -> tuple[list[ServiceCluster], int]:
        """List clusters with pagination and filtering."""
        base = select(ServiceCluster).where(
            ServiceCluster.deleted_at.is_(None),
        )
        # Include both tenant-owned and system blueprints
        if tenant_id:
            base = base.where(
                (ServiceCluster.tenant_id == tenant_id) | (ServiceCluster.is_system.is_(True))
            )

        if cluster_type:
            base = base.where(ServiceCluster.cluster_type == cluster_type)
        if search:
            base = base.where(ServiceCluster.name.ilike(f"%{search}%"))
        if category:
            base = base.where(ServiceCluster.category == category)
        if is_published is not None:
            base = base.where(ServiceCluster.is_published == is_published)
        if provider_id:
            base = base.where(ServiceCluster.provider_id == provider_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        query = (
            base
            .options(
                selectinload(ServiceCluster.slots),
            )
            .order_by(ServiceCluster.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all()), total

    # ── Slot Management ───────────────────────────────────────────────

    async def add_slot(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceClusterSlot:
        """Add a slot to a cluster."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        # Check unique name within cluster
        for existing_slot in cluster.slots:
            if existing_slot.name == data["name"] and not existing_slot.deleted_at:
                raise ClusterServiceError(
                    f"Slot '{data['name']}' already exists", "SLOT_EXISTS"
                )

        slot = ServiceClusterSlot(
            cluster_id=cluster_id,
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description"),
            allowed_ci_class_ids=data.get("allowed_ci_class_ids"),
            semantic_category_id=data.get("semantic_category_id"),
            semantic_type_id=data.get("semantic_type_id"),
            min_count=data.get("min_count", 1),
            max_count=data.get("max_count"),
            is_required=data.get("is_required", True),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(slot)
        await self.db.flush()
        return slot

    async def update_slot(
        self, slot_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceClusterSlot:
        """Update a slot definition."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        slot = None
        for s in cluster.slots:
            if s.id == slot_id and not s.deleted_at:
                slot = s
                break
        if not slot:
            raise ClusterServiceError("Slot not found", "SLOT_NOT_FOUND")

        for key in ("display_name", "description", "allowed_ci_class_ids",
                     "semantic_category_id", "semantic_type_id",
                     "min_count", "max_count", "is_required", "sort_order"):
            if key in data:
                setattr(slot, key, data[key])

        await self.db.flush()
        return slot

    async def remove_slot(
        self, slot_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a slot."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        now = datetime.now(UTC)
        for slot in cluster.slots:
            if slot.id == slot_id and not slot.deleted_at:
                slot.deleted_at = now
                await self.db.flush()
                return True

        raise ClusterServiceError("Slot not found", "SLOT_NOT_FOUND")

    # ── Versioning & Publishing ───────────────────────────────────────

    async def publish_blueprint(
        self, cluster_id: uuid.UUID, tenant_id: str, user_id: str | None = None,
        changelog: str | None = None,
    ) -> StackBlueprintVersion:
        """Freeze current blueprint state into an immutable version snapshot."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        new_version = cluster.version
        component_graph = [
            {
                "node_id": c.node_id,
                "component_id": str(c.component_id),
                "label": c.label,
                "sort_order": c.sort_order,
                "is_optional": c.is_optional,
                "default_parameters": c.default_parameters,
                "depends_on": c.depends_on,
            }
            for c in (cluster.blueprint_components or [])
            if not c.deleted_at
        ]
        bindings_snapshot = [
            {
                "direction": b.direction,
                "variable_name": b.variable_name,
                "target_node_id": b.target_node_id,
                "target_parameter": b.target_parameter,
                "transform_expression": b.transform_expression,
            }
            for b in (cluster.variable_bindings or [])
            if not b.deleted_at
        ]

        version = StackBlueprintVersion(
            blueprint_id=cluster.id,
            version=new_version,
            input_schema=cluster.input_schema,
            output_schema=cluster.output_schema,
            component_graph=component_graph,
            variable_bindings=bindings_snapshot,
            changelog=changelog,
            published_by=user_id,
        )
        self.db.add(version)

        cluster.is_published = True
        cluster.version = new_version + 1

        await self.db.flush()
        return version

    async def archive_blueprint(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> ServiceCluster:
        """Unpublish a blueprint."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")
        cluster.is_published = False
        await self.db.flush()
        return cluster

    async def get_blueprint_version(
        self, cluster_id: uuid.UUID, version: int
    ) -> StackBlueprintVersion | None:
        """Get a specific version snapshot."""
        result = await self.db.execute(
            select(StackBlueprintVersion).where(
                StackBlueprintVersion.blueprint_id == cluster_id,
                StackBlueprintVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def list_blueprint_versions(
        self, cluster_id: uuid.UUID
    ) -> list[StackBlueprintVersion]:
        """List all version snapshots for a blueprint."""
        result = await self.db.execute(
            select(StackBlueprintVersion)
            .where(StackBlueprintVersion.blueprint_id == cluster_id)
            .order_by(StackBlueprintVersion.version.desc())
        )
        return list(result.scalars().all())

    # ── Blueprint Components ──────────────────────────────────────────

    async def add_blueprint_component(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> StackBlueprintComponent:
        """Add a component node to a blueprint's composition graph."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        component = StackBlueprintComponent(
            blueprint_id=cluster.id,
            component_id=data["component_id"],
            node_id=data["node_id"],
            label=data.get("label", data["node_id"]),
            description=data.get("description"),
            sort_order=data.get("sort_order", 0),
            is_optional=data.get("is_optional", False),
            default_parameters=data.get("default_parameters"),
            depends_on=data.get("depends_on"),
        )
        self.db.add(component)
        await self.db.flush()
        return component

    async def update_blueprint_component(
        self, component_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> StackBlueprintComponent:
        """Update a blueprint component."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        result = await self.db.execute(
            select(StackBlueprintComponent).where(
                StackBlueprintComponent.id == component_id,
                StackBlueprintComponent.blueprint_id == cluster_id,
                StackBlueprintComponent.deleted_at.is_(None),
            )
        )
        comp = result.scalar_one_or_none()
        if not comp:
            raise ClusterServiceError("Component not found", "COMPONENT_NOT_FOUND")

        for key in ("label", "description", "sort_order", "is_optional",
                     "default_parameters", "depends_on"):
            if key in data:
                setattr(comp, key, data[key])

        await self.db.flush()
        return comp

    async def remove_blueprint_component(
        self, component_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a blueprint component."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        result = await self.db.execute(
            select(StackBlueprintComponent).where(
                StackBlueprintComponent.id == component_id,
                StackBlueprintComponent.blueprint_id == cluster_id,
                StackBlueprintComponent.deleted_at.is_(None),
            )
        )
        comp = result.scalar_one_or_none()
        if not comp:
            raise ClusterServiceError("Component not found", "COMPONENT_NOT_FOUND")

        comp.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_blueprint_components(
        self, cluster_id: uuid.UUID
    ) -> list[StackBlueprintComponent]:
        """List active components for a blueprint."""
        result = await self.db.execute(
            select(StackBlueprintComponent)
            .where(
                StackBlueprintComponent.blueprint_id == cluster_id,
                StackBlueprintComponent.deleted_at.is_(None),
            )
            .order_by(StackBlueprintComponent.sort_order)
        )
        return list(result.scalars().all())

    # ── Variable Bindings ─────────────────────────────────────────────

    async def set_variable_bindings(
        self, cluster_id: uuid.UUID, tenant_id: str, bindings: list[dict]
    ) -> list[StackVariableBinding]:
        """Replace all variable bindings for a blueprint."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        # Soft-delete existing bindings
        now = datetime.now(UTC)
        for existing in (cluster.variable_bindings or []):
            if not existing.deleted_at:
                existing.deleted_at = now

        # Create new bindings
        new_bindings = []
        for b in bindings:
            binding = StackVariableBinding(
                blueprint_id=cluster.id,
                direction=b["direction"],
                variable_name=b["variable_name"],
                target_node_id=b["target_node_id"],
                target_parameter=b["target_parameter"],
                transform_expression=b.get("transform_expression"),
            )
            self.db.add(binding)
            new_bindings.append(binding)

        await self.db.flush()
        return new_bindings

    async def list_variable_bindings(
        self, cluster_id: uuid.UUID
    ) -> list[StackVariableBinding]:
        """List active variable bindings for a blueprint."""
        result = await self.db.execute(
            select(StackVariableBinding)
            .where(
                StackVariableBinding.blueprint_id == cluster_id,
                StackVariableBinding.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # ── Governance ────────────────────────────────────────────────────

    async def set_blueprint_governance(
        self, cluster_id: uuid.UUID, governance_tenant_id: str, data: dict
    ) -> StackBlueprintGovernance:
        """Set governance rules for a blueprint in a specific tenant."""
        result = await self.db.execute(
            select(StackBlueprintGovernance).where(
                StackBlueprintGovernance.blueprint_id == cluster_id,
                StackBlueprintGovernance.tenant_id == governance_tenant_id,
                StackBlueprintGovernance.deleted_at.is_(None),
            )
        )
        gov = result.scalar_one_or_none()

        if gov:
            for key in ("is_allowed", "parameter_constraints", "max_instances"):
                if key in data:
                    setattr(gov, key, data[key])
        else:
            gov = StackBlueprintGovernance(
                blueprint_id=cluster_id,
                tenant_id=governance_tenant_id,
                is_allowed=data.get("is_allowed", True),
                parameter_constraints=data.get("parameter_constraints"),
                max_instances=data.get("max_instances"),
            )
            self.db.add(gov)

        await self.db.flush()
        return gov

    async def list_blueprint_governance(
        self, cluster_id: uuid.UUID
    ) -> list[StackBlueprintGovernance]:
        """List governance rules for a blueprint."""
        result = await self.db.execute(
            select(StackBlueprintGovernance)
            .where(
                StackBlueprintGovernance.blueprint_id == cluster_id,
                StackBlueprintGovernance.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # ── Stack Workflows ───────────────────────────────────────────────

    async def bind_stack_workflow(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> StackWorkflow:
        """Bind a workflow definition to a blueprint."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        wf = StackWorkflow(
            blueprint_id=cluster.id,
            workflow_definition_id=data["workflow_definition_id"],
            workflow_kind=data["workflow_kind"],
            name=data["name"],
            display_name=data.get("display_name"),
            is_required=data.get("is_required", False),
            trigger_conditions=data.get("trigger_conditions"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def unbind_stack_workflow(
        self, workflow_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Unbind a workflow from a blueprint."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        result = await self.db.execute(
            select(StackWorkflow).where(
                StackWorkflow.id == workflow_id,
                StackWorkflow.blueprint_id == cluster_id,
                StackWorkflow.deleted_at.is_(None),
            )
        )
        wf = result.scalar_one_or_none()
        if not wf:
            raise ClusterServiceError("Workflow not found", "WORKFLOW_NOT_FOUND")

        wf.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_stack_workflows(
        self, cluster_id: uuid.UUID
    ) -> list[StackWorkflow]:
        """List active workflows bound to a blueprint."""
        result = await self.db.execute(
            select(StackWorkflow)
            .where(
                StackWorkflow.blueprint_id == cluster_id,
                StackWorkflow.deleted_at.is_(None),
            )
            .order_by(StackWorkflow.sort_order)
        )
        return list(result.scalars().all())

    # ── Reservation Templates ────────────────────────────────────────

    async def set_reservation_template(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> "BlueprintReservationTemplate":
        """Set or update the reservation template for a blueprint."""
        from app.models.cmdb.reservation_template import BlueprintReservationTemplate

        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        tmpl = cluster.reservation_template
        if tmpl and not tmpl.deleted_at:
            for key in ("reservation_type", "resource_percentage",
                        "target_environment_label", "target_provider_id",
                        "rto_seconds", "rpo_seconds", "auto_create_on_deploy",
                        "sync_policies_template"):
                if key in data:
                    setattr(tmpl, key, data[key])
        else:
            tmpl = BlueprintReservationTemplate(
                blueprint_id=cluster.id,
                reservation_type=data["reservation_type"],
                resource_percentage=data.get("resource_percentage", 80),
                target_environment_label=data.get("target_environment_label"),
                target_provider_id=data.get("target_provider_id"),
                rto_seconds=data.get("rto_seconds"),
                rpo_seconds=data.get("rpo_seconds"),
                auto_create_on_deploy=data.get("auto_create_on_deploy", True),
                sync_policies_template=data.get("sync_policies_template"),
            )
            self.db.add(tmpl)

        await self.db.flush()
        return tmpl

    async def remove_reservation_template(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Remove the reservation template from a blueprint."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        tmpl = cluster.reservation_template
        if not tmpl or tmpl.deleted_at:
            raise ClusterServiceError("No reservation template found", "TEMPLATE_NOT_FOUND")

        tmpl.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Stack Workflow Provisioning ──────────────────────────────────

    async def provision_stack_workflows(
        self, cluster_id: uuid.UUID, tenant_id: str, user_id: str | None = None
    ) -> list[StackWorkflow]:
        """Provision default lifecycle workflows for a blueprint from system templates."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        from app.models.workflow_definition import WorkflowDefinition

        # Find the 3 mandatory stack templates
        template_names = ["stack:provision", "stack:deprovision", "stack:upgrade"]
        kind_mapping = {
            "stack:provision": "PROVISION",
            "stack:deprovision": "DEPROVISION",
            "stack:upgrade": "UPDATE",
        }

        result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.name.in_(template_names),
                WorkflowDefinition.is_system.is_(True),
                WorkflowDefinition.is_template.is_(True),
                WorkflowDefinition.deleted_at.is_(None),
            )
        )
        templates = {t.name: t for t in result.scalars().all()}

        # Check which kinds already exist
        existing_kinds = {
            wf.workflow_kind
            for wf in (cluster.stack_workflows or [])
            if not wf.deleted_at
        }

        created = []
        for tmpl_name, kind in kind_mapping.items():
            if kind in existing_kinds:
                continue
            tmpl = templates.get(tmpl_name)
            if not tmpl:
                continue

            # Clone the template
            import copy
            clone = WorkflowDefinition(
                tenant_id=tenant_id,
                name=f"{tmpl.name}:{cluster.name}",
                description=f"{tmpl.description} (for {cluster.display_name or cluster.name})",
                version=1,
                graph=copy.deepcopy(tmpl.graph) if tmpl.graph else None,
                input_schema=copy.deepcopy(tmpl.input_schema) if tmpl.input_schema else None,
                output_schema=copy.deepcopy(tmpl.output_schema) if tmpl.output_schema else None,
                status="ACTIVE",
                created_by=user_id or tmpl.created_by,
                workflow_type="STACK",
                is_system=False,
                is_template=False,
                template_source_id=tmpl.id,
                timeout_seconds=tmpl.timeout_seconds,
                max_concurrent=tmpl.max_concurrent,
            )
            self.db.add(clone)
            await self.db.flush()

            # Bind to blueprint
            wf = StackWorkflow(
                blueprint_id=cluster.id,
                workflow_definition_id=clone.id,
                workflow_kind=kind,
                name=tmpl.name,
                display_name=tmpl.name.replace("stack:", "Stack ").replace(":", " ").title(),
                is_required=kind in ("PROVISION", "DEPROVISION"),
                sort_order=list(kind_mapping.values()).index(kind),
            )
            self.db.add(wf)
            created.append(wf)

        await self.db.flush()
        return created

    async def reset_stack_workflow(
        self, workflow_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str
    ) -> StackWorkflow:
        """Reset a stack workflow to its template default."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        result = await self.db.execute(
            select(StackWorkflow).where(
                StackWorkflow.id == workflow_id,
                StackWorkflow.blueprint_id == cluster_id,
                StackWorkflow.deleted_at.is_(None),
            )
        )
        wf = result.scalar_one_or_none()
        if not wf:
            raise ClusterServiceError("Workflow not found", "WORKFLOW_NOT_FOUND")

        from app.models.workflow_definition import WorkflowDefinition

        # Get the cloned workflow definition
        wf_def_result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == wf.workflow_definition_id,
            )
        )
        wf_def = wf_def_result.scalar_one_or_none()
        if not wf_def or not wf_def.template_source_id:
            raise ClusterServiceError("No template source found", "NO_TEMPLATE_SOURCE")

        # Get the template
        tmpl_result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == wf_def.template_source_id,
            )
        )
        tmpl = tmpl_result.scalar_one_or_none()
        if not tmpl:
            raise ClusterServiceError("Template not found", "TEMPLATE_NOT_FOUND")

        # Reset the cloned workflow to template state
        import copy
        wf_def.graph = copy.deepcopy(tmpl.graph) if tmpl.graph else None
        wf_def.input_schema = copy.deepcopy(tmpl.input_schema) if tmpl.input_schema else None
        wf_def.output_schema = copy.deepcopy(tmpl.output_schema) if tmpl.output_schema else None

        await self.db.flush()
        return wf

    # ── Blueprint Stacks ───────────────────────────────────────────────

    async def list_blueprint_stacks(
        self, blueprint_id: str, tenant_id: str
    ) -> dict | None:
        """List deployed stacks by querying CIs with the blueprint's stack_tag_key."""
        cluster = await self.get_cluster(blueprint_id, tenant_id)
        if not cluster or not cluster.stack_tag_key:
            return None

        tag_key = cluster.stack_tag_key

        # Query CIs that have this tag key, grouped by tag value
        from sqlalchemy import case, literal_column

        stmt = (
            select(
                ConfigurationItem.tags[tag_key].astext.label("tag_value"),
                func.count(ConfigurationItem.id).label("ci_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "active", literal_column("1")),
                )).label("active_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "planned", literal_column("1")),
                )).label("planned_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "maintenance", literal_column("1")),
                )).label("maintenance_count"),
            )
            .where(
                ConfigurationItem.tenant_id == tenant_id,
                ConfigurationItem.deleted_at.is_(None),
                ConfigurationItem.tags[tag_key].astext.isnot(None),
            )
            .group_by(ConfigurationItem.tags[tag_key].astext)
            .order_by(ConfigurationItem.tags[tag_key].astext)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        stacks = [
            {
                "tag_value": row.tag_value,
                "ci_count": row.ci_count,
                "active_count": row.active_count,
                "planned_count": row.planned_count,
                "maintenance_count": row.maintenance_count,
            }
            for row in rows
            if row.tag_value  # Skip null values
        ]

        return {
            "blueprint_id": str(cluster.id),
            "blueprint_name": cluster.name,
            "tag_key": tag_key,
            "stacks": stacks,
        }

    # ── Component Reservation Templates ──────────────────────────────

    async def set_component_reservation_template(
        self, blueprint_component_id: uuid.UUID, tenant_id: str, data: dict
    ) -> "ComponentReservationTemplate":
        """Set or update the reservation template for a specific blueprint component."""
        from app.models.cmdb.reservation_template import ComponentReservationTemplate

        result = await self.db.execute(
            select(ComponentReservationTemplate).where(
                ComponentReservationTemplate.blueprint_component_id == blueprint_component_id,
                ComponentReservationTemplate.deleted_at.is_(None),
            )
        )
        tmpl = result.scalar_one_or_none()

        if tmpl:
            for key in ("reservation_type", "resource_percentage",
                        "target_environment_label", "target_provider_id",
                        "rto_seconds", "rpo_seconds", "auto_create_on_deploy",
                        "sync_policies_template"):
                if key in data:
                    setattr(tmpl, key, data[key])
        else:
            tmpl = ComponentReservationTemplate(
                blueprint_component_id=blueprint_component_id,
                reservation_type=data["reservation_type"],
                resource_percentage=data.get("resource_percentage", 80),
                target_environment_label=data.get("target_environment_label"),
                target_provider_id=data.get("target_provider_id"),
                rto_seconds=data.get("rto_seconds"),
                rpo_seconds=data.get("rpo_seconds"),
                auto_create_on_deploy=data.get("auto_create_on_deploy", True),
                sync_policies_template=data.get("sync_policies_template"),
            )
            self.db.add(tmpl)

        await self.db.flush()
        return tmpl

    async def remove_component_reservation_template(
        self, blueprint_component_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Remove the reservation template from a blueprint component."""
        from app.models.cmdb.reservation_template import ComponentReservationTemplate

        result = await self.db.execute(
            select(ComponentReservationTemplate).where(
                ComponentReservationTemplate.blueprint_component_id == blueprint_component_id,
                ComponentReservationTemplate.deleted_at.is_(None),
            )
        )
        tmpl = result.scalar_one_or_none()
        if not tmpl:
            raise ClusterServiceError("No component reservation template found", "TEMPLATE_NOT_FOUND")

        tmpl.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_component_reservation_templates(
        self, cluster_id: uuid.UUID
    ) -> list["ComponentReservationTemplate"]:
        """List active component reservation templates for all components in a blueprint."""
        from app.models.cmdb.reservation_template import ComponentReservationTemplate

        result = await self.db.execute(
            select(ComponentReservationTemplate)
            .join(
                StackBlueprintComponent,
                StackBlueprintComponent.id == ComponentReservationTemplate.blueprint_component_id,
            )
            .where(
                StackBlueprintComponent.blueprint_id == cluster_id,
                StackBlueprintComponent.deleted_at.is_(None),
                ComponentReservationTemplate.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
