"""
Overview: GraphQL mutations for architecture topologies and templates.
Architecture: Mutation resolvers for architecture planner (Section 7.2)
Dependencies: strawberry, app.services.architecture.*, app.api.graphql.auth
Concepts: Topology CRUD, publish, clone, export, import, template creation
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.architecture import _topology_to_type
from app.api.graphql.types.architecture import (
    ArchitectureTopologyType,
    TopologyCreateInput,
    TopologyExportType,
    TopologyImportInput,
    TopologyUpdateInput,
)

logger = logging.getLogger(__name__)


@strawberry.type
class ArchitectureMutation:

    @strawberry.mutation
    async def create_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: TopologyCreateInput,
    ) -> ArchitectureTopologyType:
        """Create a new draft topology."""
        user_id = await check_graphql_permission(
            info, "architecture:topology:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            data = {
                "name": input.name,
                "description": input.description,
                "graph": input.graph,
                "tags": input.tags,
                "is_template": input.is_template,
            }
            t = await svc.create(str(tenant_id), str(user_id), data)
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def update_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
        input: TopologyUpdateInput,
    ) -> ArchitectureTopologyType | None:
        """Update a draft topology."""
        await check_graphql_permission(
            info, "architecture:topology:update", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            data = {}
            if input.name is not None:
                data["name"] = input.name
            if input.description is not None:
                data["description"] = input.description
            if input.graph is not None:
                data["graph"] = input.graph
            if input.tags is not None:
                data["tags"] = input.tags

            t = await svc.update(str(tenant_id), str(topology_id), data)
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def publish_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> ArchitectureTopologyType:
        """Validate and publish a draft topology."""
        user_id = await check_graphql_permission(
            info, "architecture:topology:publish", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            t = await svc.publish(str(tenant_id), str(topology_id), str(user_id))
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def archive_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> ArchitectureTopologyType:
        """Archive a topology."""
        await check_graphql_permission(
            info, "architecture:topology:update", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            t = await svc.archive(str(tenant_id), str(topology_id))
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def clone_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> ArchitectureTopologyType:
        """Clone a topology as a new draft."""
        user_id = await check_graphql_permission(
            info, "architecture:topology:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            t = await svc.clone(str(tenant_id), str(topology_id), str(user_id))
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def delete_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a topology."""
        await check_graphql_permission(
            info, "architecture:topology:delete", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            result = await svc.delete(str(tenant_id), str(topology_id))
            await db.commit()
            return result

    @strawberry.mutation
    async def export_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
        format: str = "json",
    ) -> TopologyExportType:
        """Export a topology as JSON or YAML."""
        await check_graphql_permission(
            info, "architecture:topology:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            if format == "yaml":
                yaml_str = await svc.export_yaml(str(tenant_id), str(topology_id))
                return TopologyExportType(data=yaml_str, format="yaml")
            else:
                json_data = await svc.export_json(str(tenant_id), str(topology_id))
                return TopologyExportType(data=json_data, format="json")

    @strawberry.mutation
    async def import_topology(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: TopologyImportInput,
    ) -> ArchitectureTopologyType:
        """Import a topology from exported data."""
        user_id = await check_graphql_permission(
            info, "architecture:topology:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            data = {
                "name": input.name,
                "description": input.description,
                "graph": input.graph,
                "tags": input.tags,
                "is_template": input.is_template,
            }
            t = await svc.import_topology(str(tenant_id), str(user_id), data)
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)

    @strawberry.mutation
    async def create_topology_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> ArchitectureTopologyType:
        """Create a template from an existing topology."""
        user_id = await check_graphql_permission(
            info, "architecture:template:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.architecture.topology_service import TopologyService

        async with async_session_factory() as db:
            svc = TopologyService(db)
            t = await svc.create_template(
                str(tenant_id), str(topology_id), str(user_id)
            )
            await db.commit()
            await db.refresh(t)
            return _topology_to_type(t)
