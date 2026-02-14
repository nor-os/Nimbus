"""
Overview: GraphQL queries for service clusters — listing, detail, blueprint stacks, and parameters.
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
    ServiceClusterListType,
    ServiceClusterSlotType,
    ServiceClusterType,
    StackBlueprintParameterType,
    StackInstanceType,
    StackListType,
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


def _cluster_to_gql(c) -> ServiceClusterType:
    slots = [
        _slot_to_gql(s) for s in (c.slots or []) if not s.deleted_at
    ]
    parameters = [
        _param_to_gql(p) for p in (getattr(c, "parameters", None) or []) if not p.deleted_at
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
        slots=slots,
        parameters=parameters,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@strawberry.type
class ClusterQuery:

    @strawberry.field
    async def service_cluster(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> ServiceClusterType | None:
        """Get a single service cluster by ID."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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
    ) -> ServiceClusterListType:
        """List service clusters with pagination and filtering."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
            service = ClusterService(db)
            clusters, total = await service.list_clusters(
                str(tenant_id), cluster_type, search, offset, limit
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

        from app.db.session import async_session_factory
        from app.services.cmdb.parameter_service import StackParameterService

        async with async_session_factory() as db:
            service = StackParameterService(db)
            params = await service.list_parameters(cluster_id)
            return [_param_to_gql(p) for p in params]

    @strawberry.field
    async def blueprint_stacks(
        self, info: Info, tenant_id: uuid.UUID, blueprint_id: uuid.UUID
    ) -> StackListType | None:
        """List deployed stacks for a blueprint based on its stack_tag_key."""
        await check_graphql_permission(info, "cmdb:cluster:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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
                    StackInstanceType(
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
