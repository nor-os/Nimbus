"""
Overview: GraphQL queries for architecture topologies, templates, validation, and version history.
Architecture: Query resolvers for architecture planner (Section 7.2)
Dependencies: strawberry, app.services.architecture.*, app.api.graphql.auth
Concepts: Topology queries, template listing, validation, version history
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.architecture import (
    ArchitectureTopologyType,
    DeploymentOrderType,
    ResolvedParameterType,
    ResolutionPreviewType,
    StackResolutionType,
    TopologyStatusGQL,
    TopologyValidationErrorType,
    TopologyValidationResultType,
)


def _topology_to_type(t) -> ArchitectureTopologyType:
    return ArchitectureTopologyType(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        description=t.description,
        graph=t.graph,
        status=TopologyStatusGQL(t.status.value),
        version=t.version,
        is_template=t.is_template,
        is_system=t.is_system,
        tags=list(t.tags) if t.tags else None,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ArchitectureQuery:

    @strawberry.field
    async def topologies(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        is_template: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ArchitectureTopologyType]:
        """List architecture topologies for a tenant."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        topologies = await svc.list(
            str(tenant_id), status, is_template, search, offset, limit
        )
        return [_topology_to_type(t) for t in topologies]

    @strawberry.field
    async def topology(
        self, info: Info, tenant_id: uuid.UUID, topology_id: uuid.UUID
    ) -> ArchitectureTopologyType | None:
        """Get a topology by ID."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        t = await svc.get(str(tenant_id), str(topology_id))
        return _topology_to_type(t) if t else None

    @strawberry.field
    async def topology_versions(
        self, info: Info, tenant_id: uuid.UUID, name: str
    ) -> list[ArchitectureTopologyType]:
        """Get all versions of a topology by name."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        versions = await svc.get_versions(str(tenant_id), name)
        return [_topology_to_type(t) for t in versions]

    @strawberry.field
    async def validate_topology_graph(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        graph: strawberry.scalars.JSON,
    ) -> TopologyValidationResultType:
        """Validate a topology graph without saving it."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        result = await svc.validate_graph(graph)
        return TopologyValidationResultType(
            valid=result.valid,
            errors=[
                TopologyValidationErrorType(
                    node_id=e.node_id, message=e.message, severity=e.severity
                )
                for e in result.errors
            ],
            warnings=[
                TopologyValidationErrorType(
                    node_id=w.node_id, message=w.message, severity=w.severity
                )
                for w in result.warnings
            ],
        )

    @strawberry.field
    async def topology_templates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ArchitectureTopologyType]:
        """List topology templates (tenant + system)."""
        await check_graphql_permission(info, "architecture:template:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        templates = await svc.list(
            str(tenant_id),
            is_template=True,
            search=search,
            offset=offset,
            limit=limit,
        )
        return [_topology_to_type(t) for t in templates]

    # ── Parameter Resolution ────────────────────────────────────────

    @strawberry.field
    async def resolve_stack_parameters(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
        stack_id: str,
    ) -> list[ResolvedParameterType]:
        """Resolve parameters for a single stack instance."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.parameter_resolution_service import (
            ParameterResolutionService,
        )

        db = await _get_session(info)
        svc = ParameterResolutionService(db)
        resolved = await svc.resolve_stack_parameters(
            str(tenant_id), str(topology_id), stack_id
        )
        return [
            ResolvedParameterType(
                name=r.name,
                display_name=r.display_name,
                value=r.value,
                source=r.source,
                is_required=r.is_required,
                tag_key=r.tag_key,
            )
            for r in resolved
        ]

    @strawberry.field
    async def preview_topology_resolution(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> ResolutionPreviewType:
        """Full resolution preview with deployment order."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.parameter_resolution_service import (
            ParameterResolutionService,
        )

        db = await _get_session(info)
        svc = ParameterResolutionService(db)
        preview = await svc.preview_resolution(str(tenant_id), str(topology_id))
        return ResolutionPreviewType(
            topology_id=preview.topology_id,
            stacks=[
                StackResolutionType(
                    stack_id=sr.stack_id,
                    stack_label=sr.stack_label,
                    blueprint_id=sr.blueprint_id,
                    parameters=[
                        ResolvedParameterType(
                            name=p.name,
                            display_name=p.display_name,
                            value=p.value,
                            source=p.source,
                            is_required=p.is_required,
                            tag_key=p.tag_key,
                        )
                        for p in sr.parameters
                    ],
                    is_complete=sr.is_complete,
                    unresolved_count=sr.unresolved_count,
                )
                for sr in preview.stacks
            ],
            deployment_order=preview.deployment_order,
            all_complete=preview.all_complete,
            total_unresolved=preview.total_unresolved,
        )

    @strawberry.field
    async def topology_deployment_order(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
    ) -> DeploymentOrderType:
        """Get deployment order for stacks in a topology."""
        await check_graphql_permission(info, "architecture:topology:read", str(tenant_id))

        from app.services.architecture.topology_service import TopologyService

        db = await _get_session(info)
        svc = TopologyService(db)
        t = await svc.get(str(tenant_id), str(topology_id))
        if not t or not t.graph:
            return DeploymentOrderType(groups=[])
        groups = TopologyService.get_deployment_order(t.graph)
        return DeploymentOrderType(groups=groups)
