"""
Overview: GraphQL mutations for service clusters — CRUD, slot management, and parameters.
Architecture: GraphQL mutation resolvers for cluster write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.cluster_service
Concepts: All mutations enforce permission checks, commit within session context,
    and return the full re-fetched cluster with slots. CI assignment is not part of
    blueprints — it happens at deployment time.
"""

from __future__ import annotations

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.cluster import _cluster_to_gql
from app.api.graphql.types.cluster import (
    BlueprintParameterCreateInput,
    BlueprintParameterUpdateInput,
    ServiceClusterCreateInput,
    ServiceClusterSlotInput,
    ServiceClusterSlotUpdateInput,
    ServiceClusterType,
    ServiceClusterUpdateInput,
    StackBlueprintParameterType,
)


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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
            service = ClusterService(db)
            data = {
                "name": input.name,
                "description": input.description,
                "cluster_type": input.cluster_type,
                "architecture_topology_id": input.architecture_topology_id,
                "topology_node_id": input.topology_node_id,
                "tags": input.tags or {},
                "metadata": input.metadata_,
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
            cluster = await service.create_cluster(str(tenant_id), data)
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.cluster_service import ClusterService
        from app.services.cmdb.parameter_service import StackParameterService

        async with async_session_factory() as db:
            param_svc = StackParameterService(db)
            await param_svc.delete_parameter(param_id, cluster_id)
            await db.commit()
            cluster_svc = ClusterService(db)
            cluster = await cluster_svc.get_cluster(cluster_id, str(tenant_id))
            return _cluster_to_gql(cluster)
