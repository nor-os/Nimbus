"""
Overview: GraphQL queries for the CMDB — configuration items, classes, relationships,
    graph traversal, impact analysis, compartments, templates, and search.
Architecture: GraphQL query resolvers for CMDB operations (Section 8)
Dependencies: strawberry, app.services.cmdb.*
Concepts: Read-only queries with permission checks, converter helpers, and pagination.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.cmdb import (
    CIAttributeDefinitionType,
    CIClassDetailType,
    CIClassType,
    CIListType,
    CIRelationshipType,
    CISnapshotType,
    CITemplateListType,
    CITemplateType,
    CIType,
    CIVersionListType,
    CompartmentNodeType,
    ExplorerSummaryType,
    GraphNodeType,
    LifecycleStateGQL,
    RelationshipTypeType,
    SavedSearchType,
    VersionDiffType,
)


def _ci_to_gql(ci) -> CIType:
    backend = getattr(ci, "backend", None)
    return CIType(
        id=ci.id,
        tenant_id=ci.tenant_id,
        ci_class_id=ci.ci_class_id,
        ci_class_name=ci.ci_class.name if ci.ci_class else "",
        compartment_id=ci.compartment_id,
        name=ci.name,
        description=ci.description,
        lifecycle_state=LifecycleStateGQL(ci.lifecycle_state),
        attributes=ci.attributes,
        tags=ci.tags,
        cloud_resource_id=ci.cloud_resource_id,
        pulumi_urn=ci.pulumi_urn,
        backend_id=str(ci.backend_id) if ci.backend_id else None,
        backend_name=backend.name if backend else None,
        created_at=ci.created_at,
        updated_at=ci.updated_at,
    )


def _class_to_gql(c) -> CIClassType:
    return CIClassType(
        id=c.id,
        tenant_id=c.tenant_id,
        name=c.name,
        display_name=c.display_name,
        parent_class_id=c.parent_class_id,
        semantic_type_id=c.semantic_type_id,
        schema_def=c.schema,
        icon=c.icon,
        is_system=c.is_system,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _class_detail_to_gql(c) -> CIClassDetailType:
    attr_defs = [
        CIAttributeDefinitionType(
            id=a.id,
            ci_class_id=a.ci_class_id,
            name=a.name,
            display_name=a.display_name,
            data_type=a.data_type,
            is_required=a.is_required,
            default_value=a.default_value,
            validation_rules=a.validation_rules,
            sort_order=a.sort_order,
        )
        for a in (c.attribute_definitions or [])
        if not getattr(a, "deleted_at", None)
    ]
    return CIClassDetailType(
        id=c.id,
        tenant_id=c.tenant_id,
        name=c.name,
        display_name=c.display_name,
        parent_class_id=c.parent_class_id,
        semantic_type_id=c.semantic_type_id,
        schema_def=c.schema,
        icon=c.icon,
        is_system=c.is_system,
        is_active=c.is_active,
        attribute_definitions=attr_defs,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _rel_to_gql(r) -> CIRelationshipType:
    return CIRelationshipType(
        id=r.id,
        tenant_id=r.tenant_id,
        source_ci_id=r.source_ci_id,
        source_ci_name=r.source_ci.name if r.source_ci else "",
        target_ci_id=r.target_ci_id,
        target_ci_name=r.target_ci.name if r.target_ci else "",
        relationship_type_id=r.relationship_type_id,
        relationship_type_name=(
            r.relationship_type.name if r.relationship_type else ""
        ),
        attributes=r.attributes,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _snapshot_to_gql(s) -> CISnapshotType:
    return CISnapshotType(
        id=s.id,
        ci_id=s.ci_id,
        tenant_id=s.tenant_id,
        version_number=s.version_number,
        snapshot_data=s.snapshot_data,
        changed_by=s.changed_by,
        changed_at=s.changed_at,
        change_reason=s.change_reason,
        change_type=s.change_type,
    )


def _template_to_gql(t) -> CITemplateType:
    return CITemplateType(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        description=t.description,
        ci_class_id=t.ci_class_id,
        ci_class_name=t.ci_class.name if t.ci_class else "",
        attributes=t.attributes,
        tags=t.tags,
        relationship_templates=t.relationship_templates,
        constraints=t.constraints,
        is_active=t.is_active,
        version=t.version,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _compartment_dict_to_gql(d: dict) -> CompartmentNodeType:
    return CompartmentNodeType(
        id=d["id"],
        name=d["name"],
        description=d.get("description"),
        cloud_id=d.get("cloud_id"),
        provider_type=d.get("provider_type"),
        children=[_compartment_dict_to_gql(c) for c in d.get("children", [])],
    )


@strawberry.type
class CMDBQuery:
    # ── Configuration Items ───────────────────────────────────────────

    @strawberry.field
    async def ci(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        version: int | None = None,
    ) -> CIType | None:
        """Get a single CI, optionally at a specific version."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            ci = await service.get_ci(str(id), str(tenant_id), version)
            return _ci_to_gql(ci) if ci else None

    @strawberry.field
    async def cis(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_class_id: uuid.UUID | None = None,
        compartment_id: uuid.UUID | None = None,
        backend_id: uuid.UUID | None = None,
        lifecycle_state: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CIListType:
        """List CIs with filtering and pagination."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            items, total = await service.list_cis(
                tenant_id=str(tenant_id),
                ci_class_id=str(ci_class_id) if ci_class_id else None,
                compartment_id=(
                    str(compartment_id) if compartment_id else None
                ),
                backend_id=str(backend_id) if backend_id else None,
                lifecycle_state=lifecycle_state,
                search=search,
                offset=offset,
                limit=limit,
            )
            return CIListType(
                items=[_ci_to_gql(ci) for ci in items],
                total=total,
            )

    # ── CI Versions ───────────────────────────────────────────────────

    @strawberry.field
    async def ci_versions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> CIVersionListType:
        """List version history for a CI."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.versioning_service import VersioningService

        async with async_session_factory() as db:
            service = VersioningService(db)
            items, total = await service.get_versions(
                str(ci_id), str(tenant_id), offset, limit
            )
            return CIVersionListType(
                items=[_snapshot_to_gql(s) for s in items],
                total=total,
            )

    @strawberry.field
    async def ci_version_diff(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_id: uuid.UUID,
        version_a: int,
        version_b: int,
    ) -> VersionDiffType:
        """Compare two versions of a CI."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.versioning_service import VersioningService

        async with async_session_factory() as db:
            service = VersioningService(db)
            diff = await service.diff_versions(
                str(ci_id), str(tenant_id), version_a, version_b
            )
            return VersionDiffType(
                version_a=diff.get("version_a", version_a),
                version_b=diff.get("version_b", version_b),
                changes=diff.get("changes", {}),
            )

    # ── CI Classes ────────────────────────────────────────────────────

    @strawberry.field
    async def ci_classes(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        include_system: bool = True,
    ) -> list[CIClassType]:
        """List CI classes."""
        await check_graphql_permission(
            info, "cmdb:class:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.class_service import ClassService

        async with async_session_factory() as db:
            service = ClassService(db)
            classes = await service.list_classes(
                str(tenant_id), include_system
            )
            return [_class_to_gql(c) for c in classes]

    @strawberry.field
    async def ci_class(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> CIClassDetailType | None:
        """Get a CI class with attribute definitions."""
        await check_graphql_permission(
            info, "cmdb:class:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.class_service import ClassService

        async with async_session_factory() as db:
            service = ClassService(db)
            c = await service.get_class(id)
            return _class_detail_to_gql(c) if c else None

    # ── Relationship Types ────────────────────────────────────────────

    @strawberry.field
    async def relationship_types(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        domain: str | None = None,
    ) -> list[RelationshipTypeType]:
        """List relationship types, optionally filtered by domain."""
        await check_graphql_permission(
            info, "cmdb:relationship:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            types = await service.list_relationship_types()
            if domain:
                types = [t for t in types if t.domain == domain]
            return [
                RelationshipTypeType(
                    id=t.id,
                    name=t.name,
                    display_name=t.display_name,
                    inverse_name=t.inverse_name,
                    description=t.description,
                    source_class_ids=t.source_class_ids,
                    target_class_ids=t.target_class_ids,
                    is_system=t.is_system,
                    domain=t.domain,
                    source_entity_type=t.source_entity_type,
                    target_entity_type=t.target_entity_type,
                    source_semantic_types=t.source_semantic_types,
                    target_semantic_types=t.target_semantic_types,
                    source_semantic_categories=t.source_semantic_categories,
                    target_semantic_categories=t.target_semantic_categories,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in types
            ]

    # ── CI Relationships ──────────────────────────────────────────────

    @strawberry.field
    async def ci_relationships(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_id: uuid.UUID,
        relationship_type_id: uuid.UUID | None = None,
        direction: str = "both",
    ) -> list[CIRelationshipType]:
        """Get relationships for a CI."""
        await check_graphql_permission(
            info, "cmdb:relationship:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            rels = await service.get_relationships(
                str(ci_id),
                str(tenant_id),
                str(relationship_type_id) if relationship_type_id else None,
                direction,
            )
            return [_rel_to_gql(r) for r in rels]

    # ── Graph & Impact ────────────────────────────────────────────────

    @strawberry.field
    async def ci_graph(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_id: uuid.UUID,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",
        max_depth: int = 3,
    ) -> list[GraphNodeType]:
        """Traverse the CI relationship graph."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.graph_service import GraphService

        async with async_session_factory() as db:
            service = GraphService(db)
            nodes = await service.traverse(
                str(ci_id),
                str(tenant_id),
                relationship_types,
                direction,
                max_depth,
            )
            return [
                GraphNodeType(
                    ci_id=n.ci_id,
                    name=n.name,
                    ci_class=n.ci_class,
                    depth=n.depth,
                    path=n.path,
                )
                for n in nodes
            ]

    @strawberry.field
    async def ci_impact(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_id: uuid.UUID,
        direction: str = "downstream",
        max_depth: int = 5,
    ) -> list[GraphNodeType]:
        """Analyze impact of a CI failure."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.graph_service import GraphService

        async with async_session_factory() as db:
            service = GraphService(db)
            nodes = await service.impact_analysis(
                str(ci_id), str(tenant_id), direction, max_depth
            )
            return [
                GraphNodeType(
                    ci_id=n.ci_id,
                    name=n.name,
                    ci_class=n.ci_class,
                    depth=n.depth,
                    path=n.path,
                )
                for n in nodes
            ]

    # ── Compartments ──────────────────────────────────────────────────

    @strawberry.field
    async def compartment_tree(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[CompartmentNodeType]:
        """Get the compartment tree for a tenant."""
        await check_graphql_permission(
            info, "cmdb:compartment:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.compartment_service import CMDBCompartmentService

        async with async_session_factory() as db:
            service = CMDBCompartmentService(db)
            tree = await service.get_compartment_tree(str(tenant_id))
            return [_compartment_dict_to_gql(n) for n in tree]

    # ── Templates ─────────────────────────────────────────────────────

    @strawberry.field
    async def ci_templates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_class_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CITemplateListType:
        """List CI templates."""
        await check_graphql_permission(
            info, "cmdb:template:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.template_service import TemplateService

        async with async_session_factory() as db:
            service = TemplateService(db)
            items, total = await service.list_templates(
                str(tenant_id),
                str(ci_class_id) if ci_class_id else None,
                offset=offset,
                limit=limit,
            )
            return CITemplateListType(
                items=[_template_to_gql(t) for t in items],
                total=total,
            )

    # ── Search ────────────────────────────────────────────────────────

    @strawberry.field
    async def search_cis(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        query: str | None = None,
        ci_class_id: uuid.UUID | None = None,
        compartment_id: uuid.UUID | None = None,
        lifecycle_state: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CIListType:
        """Search CIs with full-text query and filters."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.search_service import SearchService

        async with async_session_factory() as db:
            service = SearchService(db)
            items, total = await service.search_cis(
                tenant_id=str(tenant_id),
                query=query,
                ci_class_id=str(ci_class_id) if ci_class_id else None,
                compartment_id=(
                    str(compartment_id) if compartment_id else None
                ),
                lifecycle_state=lifecycle_state,
                offset=offset,
                limit=limit,
            )
            return CIListType(
                items=[_ci_to_gql(ci) for ci in items],
                total=total,
            )

    @strawberry.field
    async def saved_searches(
        self, info: Info, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[SavedSearchType]:
        """List saved searches for a user."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.search_service import SearchService

        async with async_session_factory() as db:
            service = SearchService(db)
            items = await service.list_saved_searches(
                str(tenant_id), str(user_id)
            )
            return [
                SavedSearchType(
                    id=s.id,
                    tenant_id=s.tenant_id,
                    user_id=s.user_id,
                    name=s.name,
                    query_text=s.query_text,
                    filters=s.filters,
                    sort_config=s.sort_config,
                    is_default=s.is_default,
                )
                for s in items
            ]

    # ── Explorer ──────────────────────────────────────────────────────

    @strawberry.field
    async def explorer_summary(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        compartment_id: uuid.UUID | None = None,
        backend_id: uuid.UUID | None = None,
    ) -> ExplorerSummaryType:
        """Get aggregated CI counts grouped by semantic category, type, and backend."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            return await service.get_explorer_summary(
                tenant_id=str(tenant_id),
                compartment_id=(
                    str(compartment_id) if compartment_id else None
                ),
                backend_id=str(backend_id) if backend_id else None,
            )
