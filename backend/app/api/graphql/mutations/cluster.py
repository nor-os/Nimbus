"""
Overview: GraphQL mutations for service clusters — CRUD, slot management, parameters,
    versioning, components, bindings, governance, workflows, instances, reservations.
Architecture: GraphQL mutation resolvers for cluster write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.cluster_service
Concepts: All mutations enforce permission checks, commit within session context,
    and return the full re-fetched entity. CI assignment is not part of
    blueprints — it happens at deployment time.
"""

from __future__ import annotations

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.cluster import (
    _cluster_to_gql,
    _component_reservation_template_to_gql,
    _instance_to_gql,
    _reservation_template_to_gql,
    _reservation_to_gql,
)
from app.api.graphql.types.cluster import (
    BlueprintReservationTemplateType,
    BlueprintComponentInput,
    BlueprintComponentUpdateInput,
    BlueprintParameterCreateInput,
    BlueprintParameterUpdateInput,
    ComponentReservationTemplateInput,
    ComponentReservationTemplateType,
    CreateReservationInput,
    DeployStackInput,
    ClusterGovernanceInput,
    ReservationSyncPolicyType,
    ServiceClusterCreateInput,
    ServiceClusterSlotInput,
    ServiceClusterSlotUpdateInput,
    ServiceClusterType,
    ServiceClusterUpdateInput,
    StackBlueprintComponentType,
    StackBlueprintGovernanceType,
    StackBlueprintVersionType,
    StackReservationType,
    StackRuntimeInstanceType,
    StackVariableBindingType,
    StackWorkflowInput,
    StackWorkflowType,
    ReservationTemplateInput,
    SyncPolicyInput,
    UpdateReservationInput,
    UpdateStackInstanceInput,
    VariableBindingInput,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ClusterMutation:
    # ── Cluster CRUD ──────────────────────────────────────────────────

    @strawberry.mutation
    async def create_service_cluster(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ServiceClusterCreateInput,
    ) -> ServiceClusterType:
        """Create a new service cluster with optional inline slots."""
        await check_graphql_permission(info, "cmdb:cluster:create", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        data = {
            "name": input.name,
            "description": input.description,
            "cluster_type": input.cluster_type,
            "architecture_topology_id": input.architecture_topology_id,
            "topology_node_id": input.topology_node_id,
            "tags": input.tags or {},
            "metadata": input.metadata_,
            "provider_id": input.provider_id,
            "category": input.category,
            "icon": input.icon,
            "input_schema": input.input_schema,
            "output_schema": input.output_schema,
            "display_name": input.display_name,
            "ha_config_schema": input.ha_config_schema,
            "ha_config_defaults": input.ha_config_defaults,
            "dr_config_schema": input.dr_config_schema,
            "dr_config_defaults": input.dr_config_defaults,
            "slots": [
                {
                    "name": s.name,
                    "display_name": s.display_name or s.name,
                    "description": s.description,
                    "allowed_ci_class_ids": s.allowed_ci_class_ids,
                    "semantic_category_id": s.semantic_category_id,
                    "semantic_type_id": s.semantic_type_id,
                    "min_count": s.min_count,
                    "max_count": s.max_count,
                    "is_required": s.is_required,
                    "sort_order": s.sort_order,
                }
                for s in (input.slots or [])
            ],
        }

        ctx = info.context
        user_id = str(ctx.user.id) if hasattr(ctx, "user") and ctx.user else None
        cluster = await service.create_cluster(str(tenant_id), data, user_id=user_id)
        await db.commit()
        cluster = await service.get_cluster(cluster.id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def update_service_cluster(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ServiceClusterUpdateInput,
    ) -> ServiceClusterType:
        """Update a service cluster."""
        await check_graphql_permission(info, "cmdb:cluster:update", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.cluster_type is not None:
            data["cluster_type"] = input.cluster_type
        if input.architecture_topology_id is not strawberry.UNSET:
            data["architecture_topology_id"] = input.architecture_topology_id
        if input.topology_node_id is not strawberry.UNSET:
            data["topology_node_id"] = input.topology_node_id
        if input.tags is not None:
            data["tags"] = input.tags
        if input.metadata_ is not strawberry.UNSET:
            data["metadata"] = input.metadata_
        if input.provider_id is not strawberry.UNSET:
            data["provider_id"] = input.provider_id
        if input.category is not strawberry.UNSET:
            data["category"] = input.category
        if input.icon is not strawberry.UNSET:
            data["icon"] = input.icon
        if input.input_schema is not strawberry.UNSET:
            data["input_schema"] = input.input_schema
        if input.output_schema is not strawberry.UNSET:
            data["output_schema"] = input.output_schema
        if input.display_name is not strawberry.UNSET:
            data["display_name"] = input.display_name
        if input.ha_config_schema is not strawberry.UNSET:
            data["ha_config_schema"] = input.ha_config_schema
        if input.ha_config_defaults is not strawberry.UNSET:
            data["ha_config_defaults"] = input.ha_config_defaults
        if input.dr_config_schema is not strawberry.UNSET:
            data["dr_config_schema"] = input.dr_config_schema
        if input.dr_config_defaults is not strawberry.UNSET:
            data["dr_config_defaults"] = input.dr_config_defaults

        cluster = await service.update_cluster(id, str(tenant_id), data)
        await db.commit()
        cluster = await service.get_cluster(cluster.id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def delete_service_cluster(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete a service cluster and its slots."""
        await check_graphql_permission(info, "cmdb:cluster:delete", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.delete_cluster(id, str(tenant_id))
        await db.commit()
        return result

    # ── Slot Management ───────────────────────────────────────────────

    @strawberry.mutation
    async def add_cluster_slot(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        input: ServiceClusterSlotInput,
    ) -> ServiceClusterType:
        """Add a slot to a service cluster."""
        await check_graphql_permission(info, "cmdb:cluster:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        data = {
            "name": input.name,
            "display_name": input.display_name or input.name,
            "description": input.description,
            "allowed_ci_class_ids": input.allowed_ci_class_ids,
            "semantic_category_id": input.semantic_category_id,
            "semantic_type_id": input.semantic_type_id,
            "min_count": input.min_count,
            "max_count": input.max_count,
            "is_required": input.is_required,
            "sort_order": input.sort_order,
        }
        await service.add_slot(cluster_id, str(tenant_id), data)
        await db.commit()
        cluster = await service.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def update_cluster_slot(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        slot_id: uuid.UUID,
        input: ServiceClusterSlotUpdateInput,
    ) -> ServiceClusterType:
        """Update a slot definition."""
        await check_graphql_permission(info, "cmdb:cluster:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.allowed_ci_class_ids is not strawberry.UNSET:
            data["allowed_ci_class_ids"] = input.allowed_ci_class_ids
        if input.semantic_category_id is not strawberry.UNSET:
            data["semantic_category_id"] = input.semantic_category_id
        if input.semantic_type_id is not strawberry.UNSET:
            data["semantic_type_id"] = input.semantic_type_id
        if input.min_count is not None:
            data["min_count"] = input.min_count
        if input.max_count is not strawberry.UNSET:
            data["max_count"] = input.max_count
        if input.is_required is not None:
            data["is_required"] = input.is_required
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        await service.update_slot(slot_id, cluster_id, str(tenant_id), data)
        await db.commit()
        cluster = await service.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def remove_cluster_slot(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        slot_id: uuid.UUID,
    ) -> ServiceClusterType:
        """Remove a slot from a cluster."""
        await check_graphql_permission(info, "cmdb:cluster:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        await service.remove_slot(slot_id, cluster_id, str(tenant_id))
        await db.commit()
        cluster = await service.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    # ── Blueprint Parameters ──────────────────────────────────────────

    @strawberry.mutation
    async def sync_blueprint_parameters(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> ServiceClusterType:
        """Sync slot-derived parameters from semantic type schemas."""
        await check_graphql_permission(info, "cmdb:blueprint_param:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        db = await _get_session(info)
        param_svc = StackParameterService(db)
        await param_svc.sync_slot_parameters(cluster_id, str(tenant_id))
        await db.commit()
        cluster_svc = ClusterService(db)
        cluster = await cluster_svc.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def add_blueprint_parameter(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        input: BlueprintParameterCreateInput,
    ) -> ServiceClusterType:
        """Add a custom parameter to a blueprint."""
        await check_graphql_permission(info, "cmdb:blueprint_param:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        db = await _get_session(info)
        param_svc = StackParameterService(db)
        await param_svc.add_custom_parameter(cluster_id, str(tenant_id), {
            "name": input.name,
            "display_name": input.display_name or input.name,
            "description": input.description,
            "parameter_schema": input.parameter_schema,
            "default_value": input.default_value,
            "is_required": input.is_required,
            "sort_order": input.sort_order,
        })
        await db.commit()
        cluster_svc = ClusterService(db)
        cluster = await cluster_svc.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def update_blueprint_parameter(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        param_id: uuid.UUID,
        input: BlueprintParameterUpdateInput,
    ) -> ServiceClusterType:
        """Update a blueprint parameter."""
        await check_graphql_permission(info, "cmdb:blueprint_param:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        db = await _get_session(info)
        param_svc = StackParameterService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.parameter_schema is not strawberry.UNSET:
            data["parameter_schema"] = input.parameter_schema
        if input.default_value is not strawberry.UNSET:
            data["default_value"] = input.default_value
        if input.is_required is not None:
            data["is_required"] = input.is_required
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        await param_svc.update_parameter(param_id, cluster_id, data)
        await db.commit()
        cluster_svc = ClusterService(db)
        cluster = await cluster_svc.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    @strawberry.mutation
    async def delete_blueprint_parameter(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_id: uuid.UUID,
        param_id: uuid.UUID,
    ) -> ServiceClusterType:
        """Delete a blueprint parameter."""
        await check_graphql_permission(info, "cmdb:blueprint_param:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        db = await _get_session(info)
        param_svc = StackParameterService(db)
        await param_svc.delete_parameter(param_id, cluster_id)
        await db.commit()
        cluster_svc = ClusterService(db)
        cluster = await cluster_svc.get_cluster(cluster_id, str(tenant_id))
        return _cluster_to_gql(cluster)

    # ── Blueprint Lifecycle ───────────────────────────────────────────

    @strawberry.mutation
    async def publish_blueprint(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        changelog: str | None = None,
    ) -> StackBlueprintVersionType:
        """Publish a blueprint — freeze current state into immutable version."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        ctx = info.context
        user_id = str(ctx.user.id) if hasattr(ctx, "user") and ctx.user else None
        service = ClusterService(db)
        version = await service.publish_blueprint(
            cluster_id, str(tenant_id), user_id=user_id, changelog=changelog,
        )
        await db.commit()
        return StackBlueprintVersionType(
            id=version.id, blueprint_id=version.blueprint_id, version=version.version,
            input_schema=version.input_schema, output_schema=version.output_schema,
            component_graph=version.component_graph, variable_bindings=version.variable_bindings,
            changelog=version.changelog, published_by=version.published_by,
            created_at=version.created_at,
        )

    @strawberry.mutation
    async def archive_blueprint(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> ServiceClusterType:
        """Unpublish a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        cluster = await service.archive_blueprint(cluster_id, str(tenant_id))
        await db.commit()
        cluster = await service.get_cluster(cluster.id, str(tenant_id))
        return _cluster_to_gql(cluster)

    # ── Blueprint Composition ─────────────────────────────────────────

    @strawberry.mutation
    async def add_blueprint_component(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        input: BlueprintComponentInput,
    ) -> StackBlueprintComponentType:
        """Add a component node to a blueprint composition."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        comp = await service.add_blueprint_component(cluster_id, str(tenant_id), {
            "component_id": input.component_id,
            "node_id": input.node_id,
            "label": input.label or input.node_id,
            "description": input.description,
            "sort_order": input.sort_order,
            "is_optional": input.is_optional,
            "default_parameters": input.default_parameters,
            "depends_on": input.depends_on,
        })
        await db.commit()
        return StackBlueprintComponentType(
            id=comp.id, blueprint_id=comp.blueprint_id, component_id=comp.component_id,
            node_id=comp.node_id, label=comp.label, description=comp.description,
            sort_order=comp.sort_order, is_optional=comp.is_optional,
            default_parameters=comp.default_parameters, depends_on=comp.depends_on,
            created_at=comp.created_at, updated_at=comp.updated_at,
        )

    @strawberry.mutation
    async def update_blueprint_component(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        component_id: uuid.UUID, input: BlueprintComponentUpdateInput,
    ) -> StackBlueprintComponentType:
        """Update a blueprint component node."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        data: dict = {}
        if input.label is not None:
            data["label"] = input.label
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order
        if input.is_optional is not None:
            data["is_optional"] = input.is_optional
        if input.default_parameters is not strawberry.UNSET:
            data["default_parameters"] = input.default_parameters
        if input.depends_on is not strawberry.UNSET:
            data["depends_on"] = input.depends_on

        comp = await service.update_blueprint_component(
            component_id, cluster_id, str(tenant_id), data
        )
        await db.commit()
        return StackBlueprintComponentType(
            id=comp.id, blueprint_id=comp.blueprint_id, component_id=comp.component_id,
            node_id=comp.node_id, label=comp.label, description=comp.description,
            sort_order=comp.sort_order, is_optional=comp.is_optional,
            default_parameters=comp.default_parameters, depends_on=comp.depends_on,
            created_at=comp.created_at, updated_at=comp.updated_at,
        )

    @strawberry.mutation
    async def remove_blueprint_component(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        component_id: uuid.UUID,
    ) -> bool:
        """Remove a component node from a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.remove_blueprint_component(
            component_id, cluster_id, str(tenant_id)
        )
        await db.commit()
        return result

    # ── Variable Bindings ─────────────────────────────────────────────

    @strawberry.mutation
    async def set_variable_bindings(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        bindings: list[VariableBindingInput],
    ) -> list[StackVariableBindingType]:
        """Replace all variable bindings for a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        new_bindings = await service.set_variable_bindings(
            cluster_id, str(tenant_id),
            [
                {
                    "direction": b.direction,
                    "variable_name": b.variable_name,
                    "target_node_id": b.target_node_id,
                    "target_parameter": b.target_parameter,
                    "transform_expression": b.transform_expression,
                }
                for b in bindings
            ],
        )
        await db.commit()
        return [
            StackVariableBindingType(
                id=b.id, blueprint_id=b.blueprint_id, direction=b.direction,
                variable_name=b.variable_name, target_node_id=b.target_node_id,
                target_parameter=b.target_parameter,
                transform_expression=b.transform_expression,
                created_at=b.created_at, updated_at=b.updated_at,
            )
            for b in new_bindings
        ]

    # ── Governance ────────────────────────────────────────────────────

    @strawberry.mutation
    async def set_blueprint_governance(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        input: ClusterGovernanceInput,
    ) -> StackBlueprintGovernanceType:
        """Set governance rules for a blueprint in a target tenant."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        gov = await service.set_blueprint_governance(
            cluster_id, str(input.governance_tenant_id),
            {
                "is_allowed": input.is_allowed,
                "parameter_constraints": input.parameter_constraints,
                "max_instances": input.max_instances,
            },
        )
        await db.commit()
        return StackBlueprintGovernanceType(
            id=gov.id, blueprint_id=gov.blueprint_id, tenant_id=gov.tenant_id,
            is_allowed=gov.is_allowed, parameter_constraints=gov.parameter_constraints,
            max_instances=gov.max_instances, created_at=gov.created_at, updated_at=gov.updated_at,
        )

    # ── Stack Workflows ───────────────────────────────────────────────

    @strawberry.mutation
    async def bind_stack_workflow(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        input: StackWorkflowInput,
    ) -> StackWorkflowType:
        """Bind a workflow to a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        wf = await service.bind_stack_workflow(cluster_id, str(tenant_id), {
            "workflow_definition_id": input.workflow_definition_id,
            "workflow_kind": input.workflow_kind,
            "name": input.name,
            "display_name": input.display_name,
            "is_required": input.is_required,
            "trigger_conditions": input.trigger_conditions,
            "sort_order": input.sort_order,
        })
        await db.commit()
        return StackWorkflowType(
            id=wf.id, blueprint_id=wf.blueprint_id,
            workflow_definition_id=wf.workflow_definition_id,
            workflow_kind=wf.workflow_kind, name=wf.name,
            display_name=wf.display_name, is_required=wf.is_required,
            trigger_conditions=wf.trigger_conditions, sort_order=wf.sort_order,
            created_at=wf.created_at, updated_at=wf.updated_at,
        )

    @strawberry.mutation
    async def unbind_stack_workflow(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> bool:
        """Unbind a workflow from a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.unbind_stack_workflow(workflow_id, cluster_id, str(tenant_id))
        await db.commit()
        return result

    @strawberry.mutation
    async def provision_stack_workflows(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackWorkflowType]:
        """Provision default lifecycle workflows for a blueprint from system templates."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        ctx = info.context
        user_id = str(ctx.user.id) if hasattr(ctx, "user") and ctx.user else None
        service = ClusterService(db)
        workflows = await service.provision_stack_workflows(cluster_id, str(tenant_id), user_id)
        await db.commit()
        return [
            StackWorkflowType(
                id=wf.id, blueprint_id=wf.blueprint_id,
                workflow_definition_id=wf.workflow_definition_id,
                workflow_kind=wf.workflow_kind, name=wf.name,
                display_name=wf.display_name, is_required=wf.is_required,
                trigger_conditions=wf.trigger_conditions, sort_order=wf.sort_order,
                created_at=wf.created_at, updated_at=wf.updated_at,
            )
            for wf in workflows
        ]

    @strawberry.mutation
    async def reset_stack_workflow(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> StackWorkflowType:
        """Reset a stack workflow to its template default."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        wf = await service.reset_stack_workflow(workflow_id, cluster_id, str(tenant_id))
        await db.commit()
        return StackWorkflowType(
            id=wf.id, blueprint_id=wf.blueprint_id,
            workflow_definition_id=wf.workflow_definition_id,
            workflow_kind=wf.workflow_kind, name=wf.name,
            display_name=wf.display_name, is_required=wf.is_required,
            trigger_conditions=wf.trigger_conditions, sort_order=wf.sort_order,
            created_at=wf.created_at, updated_at=wf.updated_at,
        )

    # ── Stack Instances ───────────────────────────────────────────────

    @strawberry.mutation
    async def deploy_stack(
        self, info: Info, tenant_id: uuid.UUID,
        input: DeployStackInput,
    ) -> StackRuntimeInstanceType:
        """Create and deploy a stack instance from a published blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:deploy", str(tenant_id))

        from app.services.cmdb.stack_instance_service import StackInstanceService

        db = await _get_session(info)
        ctx = info.context
        user_id = str(ctx.user.id) if hasattr(ctx, "user") and ctx.user else None
        service = StackInstanceService(db)
        instance = await service.create_instance(str(tenant_id), {
            "blueprint_id": input.blueprint_id,
            "name": input.name,
            "environment_id": input.environment_id,
            "input_values": input.input_values,
            "ha_config": input.ha_config,
            "dr_config": input.dr_config,
        }, user_id=user_id)
        await db.commit()
        instance = await service.get_instance(instance.id, str(tenant_id))
        return _instance_to_gql(instance)

    @strawberry.mutation
    async def update_stack_instance(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: UpdateStackInstanceInput,
    ) -> StackRuntimeInstanceType:
        """Update a stack instance status or health."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.stack_instance_service import StackInstanceService

        db = await _get_session(info)
        service = StackInstanceService(db)
        if input.status:
            await service.update_instance_status(id, str(tenant_id), input.status)
        if input.health_status:
            await service.update_health_status(id, str(tenant_id), input.health_status)
        await db.commit()
        instance = await service.get_instance(id, str(tenant_id))
        return _instance_to_gql(instance)

    @strawberry.mutation
    async def decommission_stack(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> StackRuntimeInstanceType:
        """Decommission a stack instance."""
        await check_graphql_permission(info, "infrastructure:blueprint:destroy", str(tenant_id))

        from app.services.cmdb.stack_instance_service import StackInstanceService

        db = await _get_session(info)
        service = StackInstanceService(db)
        instance = await service.decommission_instance(id, str(tenant_id))
        await db.commit()
        instance = await service.get_instance(instance.id, str(tenant_id))
        return _instance_to_gql(instance)

    # ── Reservation Templates ────────────────────────────────────────

    @strawberry.mutation
    async def set_reservation_template(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        input: ReservationTemplateInput,
    ) -> BlueprintReservationTemplateType:
        """Set or update the reservation template for a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        tmpl = await service.set_reservation_template(cluster_id, str(tenant_id), {
            "reservation_type": input.reservation_type,
            "resource_percentage": input.resource_percentage,
            "target_environment_label": input.target_environment_label,
            "target_provider_id": input.target_provider_id,
            "rto_seconds": input.rto_seconds,
            "rpo_seconds": input.rpo_seconds,
            "auto_create_on_deploy": input.auto_create_on_deploy,
            "sync_policies_template": input.sync_policies_template,
        })
        await db.commit()
        return _reservation_template_to_gql(tmpl)

    @strawberry.mutation
    async def remove_reservation_template(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> bool:
        """Remove the reservation template from a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.remove_reservation_template(cluster_id, str(tenant_id))
        await db.commit()
        return result

    # ── Component Reservation Templates ─────────────────────────────

    @strawberry.mutation
    async def set_component_reservation_template(
        self, info: Info, tenant_id: uuid.UUID, blueprint_component_id: uuid.UUID,
        input: ComponentReservationTemplateInput,
    ) -> ComponentReservationTemplateType:
        """Set or update the reservation template for a specific blueprint component."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        tmpl = await service.set_component_reservation_template(blueprint_component_id, str(tenant_id), {
            "reservation_type": input.reservation_type,
            "resource_percentage": input.resource_percentage,
            "target_environment_label": input.target_environment_label,
            "target_provider_id": input.target_provider_id,
            "rto_seconds": input.rto_seconds,
            "rpo_seconds": input.rpo_seconds,
            "auto_create_on_deploy": input.auto_create_on_deploy,
            "sync_policies_template": input.sync_policies_template,
        })
        await db.commit()
        return _component_reservation_template_to_gql(tmpl)

    @strawberry.mutation
    async def remove_component_reservation_template(
        self, info: Info, tenant_id: uuid.UUID, blueprint_component_id: uuid.UUID,
    ) -> bool:
        """Remove the reservation template from a blueprint component."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.remove_component_reservation_template(blueprint_component_id, str(tenant_id))
        await db.commit()
        return result

    # ── Reservations ──────────────────────────────────────────────────

    @strawberry.mutation
    async def create_reservation(
        self, info: Info, tenant_id: uuid.UUID,
        input: CreateReservationInput,
    ) -> StackReservationType:
        """Create a DR capacity reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservation = await service.create_reservation(str(tenant_id), {
            "stack_instance_id": input.stack_instance_id,
            "reservation_type": input.reservation_type,
            "target_environment_id": input.target_environment_id,
            "target_provider_id": input.target_provider_id,
            "reserved_resources": input.reserved_resources,
            "rto_seconds": input.rto_seconds,
            "rpo_seconds": input.rpo_seconds,
            "cost_per_hour": input.cost_per_hour,
        })
        await db.commit()
        reservation = await service.get_reservation(reservation.id, str(tenant_id))
        return _reservation_to_gql(reservation)

    @strawberry.mutation
    async def update_reservation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        input: UpdateReservationInput,
    ) -> StackReservationType:
        """Update a DR reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        data: dict = {}
        if input.reservation_type is not None:
            data["reservation_type"] = input.reservation_type
        if input.target_environment_id is not strawberry.UNSET:
            data["target_environment_id"] = input.target_environment_id
        if input.target_provider_id is not strawberry.UNSET:
            data["target_provider_id"] = input.target_provider_id
        if input.reserved_resources is not strawberry.UNSET:
            data["reserved_resources"] = input.reserved_resources
        if input.rto_seconds is not strawberry.UNSET:
            data["rto_seconds"] = input.rto_seconds
        if input.rpo_seconds is not strawberry.UNSET:
            data["rpo_seconds"] = input.rpo_seconds
        if input.cost_per_hour is not strawberry.UNSET:
            data["cost_per_hour"] = input.cost_per_hour
        if input.status is not None:
            data["status"] = input.status

        reservation = await service.update_reservation(id, str(tenant_id), data)
        await db.commit()
        reservation = await service.get_reservation(reservation.id, str(tenant_id))
        return _reservation_to_gql(reservation)

    @strawberry.mutation
    async def claim_reservation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> StackReservationType:
        """Claim a DR reservation for failover."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservation = await service.claim_reservation(id, str(tenant_id))
        await db.commit()
        reservation = await service.get_reservation(reservation.id, str(tenant_id))
        return _reservation_to_gql(reservation)

    @strawberry.mutation
    async def release_reservation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> StackReservationType:
        """Release a claimed DR reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservation = await service.release_reservation(id, str(tenant_id))
        await db.commit()
        reservation = await service.get_reservation(reservation.id, str(tenant_id))
        return _reservation_to_gql(reservation)

    @strawberry.mutation
    async def test_failover(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        test_result: str,
    ) -> StackReservationType:
        """Record a failover test result."""
        await check_graphql_permission(info, "infrastructure:reservation:test", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservation = await service.record_test_result(id, str(tenant_id), test_result)
        await db.commit()
        reservation = await service.get_reservation(reservation.id, str(tenant_id))
        return _reservation_to_gql(reservation)

    # ── Sync Policies ─────────────────────────────────────────────────

    @strawberry.mutation
    async def add_sync_policy(
        self, info: Info, tenant_id: uuid.UUID, reservation_id: uuid.UUID,
        input: SyncPolicyInput,
    ) -> ReservationSyncPolicyType:
        """Add a sync policy to a reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        policy = await service.add_sync_policy(reservation_id, str(tenant_id), {
            "source_node_id": input.source_node_id,
            "target_node_id": input.target_node_id,
            "sync_method": input.sync_method,
            "sync_interval_seconds": input.sync_interval_seconds,
            "sync_workflow_id": input.sync_workflow_id,
        })
        await db.commit()
        return ReservationSyncPolicyType(
            id=policy.id, reservation_id=policy.reservation_id,
            source_node_id=policy.source_node_id, target_node_id=policy.target_node_id,
            sync_method=policy.sync_method,
            sync_interval_seconds=policy.sync_interval_seconds,
            sync_workflow_id=policy.sync_workflow_id,
            last_synced_at=policy.last_synced_at, sync_lag_seconds=policy.sync_lag_seconds,
            created_at=policy.created_at, updated_at=policy.updated_at,
        )

    @strawberry.mutation
    async def remove_sync_policy(
        self, info: Info, tenant_id: uuid.UUID, reservation_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> bool:
        """Remove a sync policy from a reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:manage", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        result = await service.remove_sync_policy(policy_id, reservation_id, str(tenant_id))
        await db.commit()
        return result

    # ── Stack Workflow Execution ──────────────────────────────────────

    @strawberry.mutation
    async def execute_stack_workflow(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        instance_id: uuid.UUID,
        workflow_kind: str,
        config_overrides: strawberry.scalars.JSON | None = None,
    ) -> strawberry.scalars.JSON:
        """Trigger a bound workflow for an instance with HA/DR config merged with overrides."""
        await check_graphql_permission(info, "infrastructure:instance:manage", str(tenant_id))

        from app.services.cmdb.stack_workflow_service import StackWorkflowService

        db = await _get_session(info)
        service = StackWorkflowService(db)
        result = await service.execute_stack_workflow(
            instance_id, str(tenant_id), workflow_kind, config_overrides,
        )
        return result
