"""
Overview: GraphQL queries for service clusters — listing, detail, blueprint stacks,
    parameters, versions, components, bindings, governance, workflows, instances, reservations.
Architecture: GraphQL query resolvers for cluster read operations (Section 8)
Dependencies: strawberry, app.services.cmdb.cluster_service
Concepts: Read-only queries with permission checks and converter helpers.
"""

from __future__ import annotations

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.cluster import (
    BlueprintReservationTemplateType,
    ComponentReservationTemplateType,
    ReservationSyncPolicyType,
    ServiceClusterListType,
    ServiceClusterSlotType,
    ServiceClusterType,
    StackBlueprintComponentType,
    StackBlueprintGovernanceType,
    StackBlueprintParameterType,
    StackBlueprintVersionType,
    StackInstanceComponentType,
    StackListType,
    StackReservationListType,
    StackReservationType,
    StackRuntimeInstanceListType,
    StackRuntimeInstanceType,
    StackTagGroupType,
    StackVariableBindingType,
    StackWorkflowType,
)


def _slot_to_gql(s) -> ServiceClusterSlotType:
    return ServiceClusterSlotType(
        id=s.id,
        cluster_id=s.cluster_id,
        name=s.name,
        display_name=s.display_name,
        description=s.description,
        allowed_ci_class_ids=s.allowed_ci_class_ids,
        semantic_category_id=s.semantic_category_id,
        semantic_category_name=(
            s.semantic_category.display_name
            if getattr(s, "semantic_category", None) else None
        ),
        semantic_type_id=s.semantic_type_id,
        semantic_type_name=(
            s.semantic_type.display_name
            if getattr(s, "semantic_type", None) else None
        ),
        min_count=s.min_count,
        max_count=s.max_count,
        is_required=s.is_required,
        sort_order=s.sort_order,
        component_id=getattr(s, "component_id", None),
        default_parameters=getattr(s, "default_parameters", None),
        depends_on=getattr(s, "depends_on", None),
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _param_to_gql(p) -> StackBlueprintParameterType:
    return StackBlueprintParameterType(
        id=p.id,
        cluster_id=p.cluster_id,
        name=p.name,
        display_name=p.display_name,
        description=p.description,
        parameter_schema=p.parameter_schema,
        default_value=p.default_value,
        source_type=p.source_type,
        source_slot_id=p.source_slot_id,
        source_slot_name=(
            p.source_slot.name if getattr(p, "source_slot", None) else None
        ),
        source_property_path=p.source_property_path,
        is_required=p.is_required,
        sort_order=p.sort_order,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _component_to_gql(c) -> StackBlueprintComponentType:
    comp = getattr(c, "component", None)
    return StackBlueprintComponentType(
        id=c.id,
        blueprint_id=c.blueprint_id,
        component_id=c.component_id,
        node_id=c.node_id,
        label=c.label,
        description=c.description,
        sort_order=c.sort_order,
        is_optional=c.is_optional,
        default_parameters=c.default_parameters,
        depends_on=c.depends_on,
        component_name=comp.name if comp else None,
        component_version=comp.version if comp else None,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _binding_to_gql(b) -> StackVariableBindingType:
    return StackVariableBindingType(
        id=b.id,
        blueprint_id=b.blueprint_id,
        direction=b.direction,
        variable_name=b.variable_name,
        target_node_id=b.target_node_id,
        target_parameter=b.target_parameter,
        transform_expression=b.transform_expression,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


def _reservation_template_to_gql(t) -> BlueprintReservationTemplateType | None:
    if not t or getattr(t, "deleted_at", None):
        return None
    return BlueprintReservationTemplateType(
        id=t.id,
        blueprint_id=t.blueprint_id,
        reservation_type=t.reservation_type,
        resource_percentage=t.resource_percentage,
        target_environment_label=t.target_environment_label,
        target_provider_id=t.target_provider_id,
        rto_seconds=t.rto_seconds,
        rpo_seconds=t.rpo_seconds,
        auto_create_on_deploy=t.auto_create_on_deploy,
        sync_policies_template=t.sync_policies_template,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _component_reservation_template_to_gql(t) -> ComponentReservationTemplateType | None:
    if not t or getattr(t, "deleted_at", None):
        return None
    return ComponentReservationTemplateType(
        id=t.id,
        blueprint_component_id=t.blueprint_component_id,
        reservation_type=t.reservation_type,
        resource_percentage=t.resource_percentage,
        target_environment_label=t.target_environment_label,
        target_provider_id=t.target_provider_id,
        rto_seconds=t.rto_seconds,
        rpo_seconds=t.rpo_seconds,
        auto_create_on_deploy=t.auto_create_on_deploy,
        sync_policies_template=t.sync_policies_template,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _cluster_to_gql(c) -> ServiceClusterType:
    slots = [
        _slot_to_gql(s) for s in (c.slots or []) if not s.deleted_at
    ]
    parameters = [
        _param_to_gql(p) for p in (getattr(c, "parameters", None) or []) if not p.deleted_at
    ]
    components = [
        _component_to_gql(bc) for bc in (getattr(c, "blueprint_components", None) or [])
        if not bc.deleted_at
    ]
    bindings = [
        _binding_to_gql(b) for b in (getattr(c, "variable_bindings", None) or [])
        if not b.deleted_at
    ]
    return ServiceClusterType(
        id=c.id,
        tenant_id=c.tenant_id,
        name=c.name,
        description=c.description,
        cluster_type=c.cluster_type,
        architecture_topology_id=c.architecture_topology_id,
        topology_node_id=c.topology_node_id,
        tags=c.tags,
        stack_tag_key=c.stack_tag_key,
        metadata_=c.metadata_,
        provider_id=getattr(c, "provider_id", None),
        category=getattr(c, "category", None),
        icon=getattr(c, "icon", None),
        input_schema=getattr(c, "input_schema", None),
        output_schema=getattr(c, "output_schema", None),
        version=getattr(c, "version", 1),
        is_published=getattr(c, "is_published", False),
        is_system=getattr(c, "is_system", False),
        display_name=getattr(c, "display_name", None),
        created_by=getattr(c, "created_by", None),
        ha_config_schema=getattr(c, "ha_config_schema", None),
        ha_config_defaults=getattr(c, "ha_config_defaults", None),
        dr_config_schema=getattr(c, "dr_config_schema", None),
        dr_config_defaults=getattr(c, "dr_config_defaults", None),
        reservation_template=_reservation_template_to_gql(
            getattr(c, "reservation_template", None)
        ),
        slots=slots,
        parameters=parameters,
        blueprint_components=components,
        variable_bindings=bindings,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _instance_to_gql(i) -> StackRuntimeInstanceType:
    components = [
        StackInstanceComponentType(
            id=c.id,
            stack_instance_id=c.stack_instance_id,
            blueprint_component_id=c.blueprint_component_id,
            component_id=c.component_id,
            component_version=c.component_version,
            ci_id=c.ci_id,
            deployment_id=c.deployment_id,
            status=c.status,
            resolved_parameters=c.resolved_parameters,
            outputs=c.outputs,
            pulumi_state_url=c.pulumi_state_url,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in (getattr(i, "instance_components", None) or [])
    ]
    return StackRuntimeInstanceType(
        id=i.id,
        blueprint_id=i.blueprint_id,
        blueprint_version=i.blueprint_version,
        tenant_id=i.tenant_id,
        environment_id=i.environment_id,
        name=i.name,
        status=i.status,
        input_values=i.input_values,
        output_values=i.output_values,
        component_states=i.component_states,
        health_status=i.health_status,
        deployed_by=i.deployed_by,
        deployed_at=i.deployed_at,
        ha_config=getattr(i, "ha_config", None),
        dr_config=getattr(i, "dr_config", None),
        components=components,
        created_at=i.created_at,
        updated_at=i.updated_at,
    )


def _reservation_to_gql(r) -> StackReservationType:
    sync_policies = [
        ReservationSyncPolicyType(
            id=sp.id,
            reservation_id=sp.reservation_id,
            source_node_id=sp.source_node_id,
            target_node_id=sp.target_node_id,
            sync_method=sp.sync_method,
            sync_interval_seconds=sp.sync_interval_seconds,
            sync_workflow_id=sp.sync_workflow_id,
            last_synced_at=sp.last_synced_at,
            sync_lag_seconds=sp.sync_lag_seconds,
            created_at=sp.created_at,
            updated_at=sp.updated_at,
        )
        for sp in (getattr(r, "sync_policies", None) or [])
        if not sp.deleted_at
    ]
    return StackReservationType(
        id=r.id,
        stack_instance_id=r.stack_instance_id,
        tenant_id=r.tenant_id,
        reservation_type=r.reservation_type,
        target_environment_id=r.target_environment_id,
        target_provider_id=r.target_provider_id,
        reserved_resources=r.reserved_resources,
        rto_seconds=r.rto_seconds,
        rpo_seconds=r.rpo_seconds,
        status=r.status,
        cost_per_hour=float(r.cost_per_hour) if r.cost_per_hour is not None else None,
        last_tested_at=r.last_tested_at,
        test_result=r.test_result,
        sync_policies=sync_policies,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ClusterQuery:

    @strawberry.field
    async def service_cluster(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> ServiceClusterType | None:
        """Get a single service cluster by ID."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        cluster = await service.get_cluster(id, str(tenant_id))
        if not cluster:
            return None
        return _cluster_to_gql(cluster)

    @strawberry.field
    async def service_clusters(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        cluster_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
        category: str | None = None,
        is_published: bool | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> ServiceClusterListType:
        """List service clusters with pagination and filtering."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        clusters, total = await service.list_clusters(
            str(tenant_id), cluster_type, search, offset, limit,
            category=category,
            is_published=is_published,
            provider_id=str(provider_id) if provider_id else None,
        )
        return ServiceClusterListType(
            items=[_cluster_to_gql(c) for c in clusters],
            total=total,
        )

    @strawberry.field
    async def blueprint_parameters(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackBlueprintParameterType]:
        """List parameter definitions for a blueprint."""
        await check_graphql_permission(info, "cmdb:blueprint_param:read", str(tenant_id))

        from app.services.cmdb.parameter_service import StackParameterService

        db = await _get_session(info)
        service = StackParameterService(db)
        params = await service.list_parameters(cluster_id)
        return [_param_to_gql(p) for p in params]

    @strawberry.field
    async def blueprint_stacks(
        self, info: Info, tenant_id: uuid.UUID, blueprint_id: uuid.UUID
    ) -> StackListType | None:
        """List deployed stacks for a blueprint based on its stack_tag_key."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        result = await service.list_blueprint_stacks(
            str(blueprint_id), str(tenant_id)
        )
        if result is None:
            return None
        return StackListType(
            blueprint_id=result["blueprint_id"],
            blueprint_name=result["blueprint_name"],
            tag_key=result["tag_key"],
            stacks=[
                StackTagGroupType(
                    tag_value=s["tag_value"],
                    ci_count=s["ci_count"],
                    active_count=s["active_count"],
                    planned_count=s["planned_count"],
                    maintenance_count=s["maintenance_count"],
                )
                for s in result["stacks"]
            ],
            total=len(result["stacks"]),
        )

    # ── Blueprint Versioning ──────────────────────────────────────────

    @strawberry.field
    async def stack_blueprint_versions(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackBlueprintVersionType]:
        """List version snapshots for a blueprint."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        versions = await service.list_blueprint_versions(cluster_id)
        return [
            StackBlueprintVersionType(
                id=v.id, blueprint_id=v.blueprint_id, version=v.version,
                input_schema=v.input_schema, output_schema=v.output_schema,
                component_graph=v.component_graph, variable_bindings=v.variable_bindings,
                changelog=v.changelog, published_by=v.published_by, created_at=v.created_at,
            )
            for v in versions
        ]

    # ── Blueprint Components ──────────────────────────────────────────

    @strawberry.field
    async def stack_blueprint_components(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackBlueprintComponentType]:
        """List component nodes for a blueprint."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        components = await service.list_blueprint_components(cluster_id)
        return [_component_to_gql(c) for c in components]

    # ── Variable Bindings ─────────────────────────────────────────────

    @strawberry.field
    async def stack_variable_bindings(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackVariableBindingType]:
        """List variable bindings for a blueprint."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        bindings = await service.list_variable_bindings(cluster_id)
        return [_binding_to_gql(b) for b in bindings]

    # ── Governance ────────────────────────────────────────────────────

    @strawberry.field
    async def stack_blueprint_governance(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> list[StackBlueprintGovernanceType]:
        """List governance rules for a blueprint."""
        await check_graphql_permission(info, "infrastructure:blueprint:manage", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        rules = await service.list_blueprint_governance(cluster_id)
        return [
            StackBlueprintGovernanceType(
                id=g.id, blueprint_id=g.blueprint_id, tenant_id=g.tenant_id,
                is_allowed=g.is_allowed, parameter_constraints=g.parameter_constraints,
                max_instances=g.max_instances, created_at=g.created_at, updated_at=g.updated_at,
            )
            for g in rules
        ]

    # ── Stack Workflows ───────────────────────────────────────────────

    @strawberry.field
    async def stack_workflows(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
        workflow_kind: str | None = None,
    ) -> list[StackWorkflowType]:
        """List workflows bound to a blueprint."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.stack_workflow_service import StackWorkflowService

        db = await _get_session(info)
        service = StackWorkflowService(db)
        wfs = await service.list_workflows(cluster_id, workflow_kind)
        return [
            StackWorkflowType(
                id=w.id, blueprint_id=w.blueprint_id,
                workflow_definition_id=w.workflow_definition_id,
                workflow_kind=w.workflow_kind, name=w.name,
                display_name=w.display_name, is_required=w.is_required,
                trigger_conditions=w.trigger_conditions, sort_order=w.sort_order,
                created_at=w.created_at, updated_at=w.updated_at,
            )
            for w in wfs
        ]

    # ── Stack Instances ───────────────────────────────────────────────

    @strawberry.field
    async def stack_instances(
        self, info: Info, tenant_id: uuid.UUID,
        blueprint_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0, limit: int = 50,
    ) -> StackRuntimeInstanceListType:
        """List deployed stack instances."""
        await check_graphql_permission(info, "infrastructure:blueprint:read", str(tenant_id))

        from app.services.cmdb.stack_instance_service import StackInstanceService

        db = await _get_session(info)
        service = StackInstanceService(db)
        instances, total = await service.list_instances(
            str(tenant_id),
            blueprint_id=str(blueprint_id) if blueprint_id else None,
            environment_id=str(environment_id) if environment_id else None,
            status=status, offset=offset, limit=limit,
        )
        return StackRuntimeInstanceListType(
            items=[_instance_to_gql(i) for i in instances],
            total=total,
        )

    @strawberry.field
    async def stack_instance(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> StackRuntimeInstanceType | None:
        """Get a single stack instance."""
        await check_graphql_permission(info, "infrastructure:blueprint:read", str(tenant_id))

        from app.services.cmdb.stack_instance_service import StackInstanceService

        db = await _get_session(info)
        service = StackInstanceService(db)
        instance = await service.get_instance(id, str(tenant_id))
        if not instance:
            return None
        return _instance_to_gql(instance)

    # ── Component Reservation Templates ─────────────────────────────

    @strawberry.field
    async def component_reservation_templates(
        self, info: Info, tenant_id: uuid.UUID, cluster_id: uuid.UUID,
    ) -> list[ComponentReservationTemplateType]:
        """List per-component reservation templates for a blueprint."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.services.cmdb.cluster_service import ClusterService

        db = await _get_session(info)
        service = ClusterService(db)
        templates = await service.list_component_reservation_templates(cluster_id)
        return [
            _component_reservation_template_to_gql(t)
            for t in templates
            if _component_reservation_template_to_gql(t) is not None
        ]

    # ── Reservations ──────────────────────────────────────────────────

    @strawberry.field
    async def stack_reservations(
        self, info: Info, tenant_id: uuid.UUID,
        stack_instance_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0, limit: int = 50,
    ) -> StackReservationListType:
        """List DR reservations."""
        await check_graphql_permission(info, "infrastructure:reservation:read", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservations, total = await service.list_reservations(
            str(tenant_id),
            stack_instance_id=str(stack_instance_id) if stack_instance_id else None,
            status=status, offset=offset, limit=limit,
        )
        return StackReservationListType(
            items=[_reservation_to_gql(r) for r in reservations],
            total=total,
        )

    @strawberry.field
    async def stack_reservation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> StackReservationType | None:
        """Get a single DR reservation."""
        await check_graphql_permission(info, "infrastructure:reservation:read", str(tenant_id))

        from app.services.cmdb.stack_reservation_service import StackReservationService

        db = await _get_session(info)
        service = StackReservationService(db)
        reservation = await service.get_reservation(id, str(tenant_id))
        if not reservation:
            return None
        return _reservation_to_gql(reservation)
