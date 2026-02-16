"""
Overview: GraphQL queries for components, resolvers, and governance.
Architecture: Query resolvers for component framework (Section 11)
Dependencies: strawberry, app.services.component.*, app.api.graphql.auth
Concepts: Component listing with filters, version history, resolver discovery, governance queries
"""

import uuid

import strawberry
import strawberry.scalars
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.component import (
    ComponentGovernanceType,
    ComponentLanguageGQL,
    ComponentOperationType,
    ComponentType,
    ComponentVersionType,
    EstimatedDowntimeGQL,
    ResolverConfigurationType,
    ResolverType,
)


# ── Converters ─────────────────────────────────────────────────────────

def _version_to_type(v) -> ComponentVersionType:
    return ComponentVersionType(
        id=v.id, component_id=v.component_id, version=v.version,
        code=v.code, input_schema=v.input_schema, output_schema=v.output_schema,
        resolver_bindings=v.resolver_bindings, changelog=v.changelog,
        published_at=v.published_at, published_by=v.published_by,
    )


def _governance_to_type(g) -> ComponentGovernanceType:
    return ComponentGovernanceType(
        id=g.id, component_id=g.component_id, tenant_id=g.tenant_id,
        is_allowed=g.is_allowed, parameter_constraints=g.parameter_constraints,
        max_instances=g.max_instances,
        created_at=g.created_at, updated_at=g.updated_at,
    )


def _operation_to_type(op) -> ComponentOperationType:
    wf_name = None
    if hasattr(op, "workflow_definition") and op.workflow_definition:
        wf_name = op.workflow_definition.name
    return ComponentOperationType(
        id=op.id, component_id=op.component_id, name=op.name,
        display_name=op.display_name, description=op.description,
        input_schema=op.input_schema, output_schema=op.output_schema,
        workflow_definition_id=op.workflow_definition_id,
        workflow_definition_name=wf_name,
        is_destructive=op.is_destructive, requires_approval=op.requires_approval,
        estimated_downtime=EstimatedDowntimeGQL(op.estimated_downtime.value),
        sort_order=op.sort_order,
        created_at=op.created_at, updated_at=op.updated_at,
    )


def _component_to_type(c) -> ComponentType:
    provider_name = None
    if hasattr(c, "provider") and c.provider:
        provider_name = c.provider.display_name or c.provider.name
    semantic_type_name = None
    if hasattr(c, "semantic_type") and c.semantic_type:
        semantic_type_name = c.semantic_type.display_name or c.semantic_type.name

    return ComponentType(
        id=c.id, tenant_id=c.tenant_id, provider_id=c.provider_id,
        semantic_type_id=c.semantic_type_id, name=c.name, display_name=c.display_name,
        description=c.description, language=ComponentLanguageGQL(c.language.value),
        code=c.code, input_schema=c.input_schema, output_schema=c.output_schema,
        resolver_bindings=c.resolver_bindings, version=c.version,
        is_published=c.is_published, is_system=c.is_system,
        upgrade_workflow_id=c.upgrade_workflow_id, created_by=c.created_by,
        created_at=c.created_at, updated_at=c.updated_at,
        versions=[_version_to_type(v) for v in (c.versions or [])],
        governance_rules=[_governance_to_type(g) for g in (c.governance_rules or [])],
        operations=[_operation_to_type(op) for op in (c.operations or [])],
        provider_name=provider_name,
        semantic_type_name=semantic_type_name,
    )


def _resolver_to_type(r) -> ResolverType:
    compatible_ids = []
    if hasattr(r, "compatible_providers") and r.compatible_providers:
        compatible_ids = [cp.provider_id for cp in r.compatible_providers]
    return ResolverType(
        id=r.id, resolver_type=r.resolver_type, display_name=r.display_name,
        description=r.description, input_schema=r.input_schema,
        output_schema=r.output_schema, handler_class=r.handler_class,
        is_system=r.is_system,
        instance_config_schema=r.instance_config_schema if hasattr(r, "instance_config_schema") else None,
        code=r.code if hasattr(r, "code") else None,
        category=r.category if hasattr(r, "category") else None,
        supports_release=r.supports_release if hasattr(r, "supports_release") else False,
        supports_update=r.supports_update if hasattr(r, "supports_update") else False,
        compatible_provider_ids=compatible_ids,
    )


def _resolver_config_to_type(rc) -> ResolverConfigurationType:
    resolver_type = ""
    if hasattr(rc, "resolver") and rc.resolver:
        resolver_type = rc.resolver.resolver_type
    return ResolverConfigurationType(
        id=rc.id, resolver_id=rc.resolver_id, resolver_type=resolver_type,
        landing_zone_id=rc.landing_zone_id, environment_id=rc.environment_id,
        config=rc.config, created_at=rc.created_at, updated_at=rc.updated_at,
    )


# ── Queries ────────────────────────────────────────────────────────────

@strawberry.type
class ComponentQuery:

    @strawberry.field
    async def components(
        self, info: Info, tenant_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
        semantic_type_id: uuid.UUID | None = None,
        published_only: bool = False,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[ComponentType]:
        """List components visible to a tenant, or provider-level if tenant_id is null."""
        await check_graphql_permission(info, "component:definition:read", str(tenant_id or ""))

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            items = await svc.list_components(
                db, tenant_id, provider_id=provider_id,
                semantic_type_id=semantic_type_id, published_only=published_only,
                search=search, offset=offset, limit=limit,
            )
            return [_component_to_type(c) for c in items]

    @strawberry.field
    async def component(
        self, info: Info, component_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentType | None:
        """Get a component by ID."""
        await check_graphql_permission(info, "component:definition:read", str(tenant_id or ""))

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            c = await svc.get_component(db, component_id)
            return _component_to_type(c) if c else None

    @strawberry.field
    async def component_versions(
        self, info: Info, tenant_id: uuid.UUID, component_id: uuid.UUID,
    ) -> list[ComponentVersionType]:
        """Get version history for a component."""
        await check_graphql_permission(info, "component:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            versions = await svc.get_version_history(db, component_id)
            return [_version_to_type(v) for v in versions]

    @strawberry.field
    async def component_version(
        self, info: Info, tenant_id: uuid.UUID,
        component_id: uuid.UUID, version: int,
    ) -> ComponentVersionType | None:
        """Get a specific version snapshot."""
        await check_graphql_permission(info, "component:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            v = await svc.get_version(db, component_id, version)
            return _version_to_type(v) if v else None

    @strawberry.field
    async def resolvers(self, info: Info) -> list[ResolverType]:
        """List all resolver type definitions."""
        from app.db.session import async_session_factory
        from app.models.resolver import Resolver
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(Resolver).where(Resolver.deleted_at.is_(None))
                .order_by(Resolver.resolver_type)
            )
            items = list(result.scalars().all())
            return [_resolver_to_type(r) for r in items]

    @strawberry.field
    async def resolver_configurations(
        self, info: Info, tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
    ) -> list[ResolverConfigurationType]:
        """List resolver configurations for a scope."""
        await check_graphql_permission(info, "resolver:config:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.models.resolver import ResolverConfiguration
        from sqlalchemy import select

        async with async_session_factory() as db:
            stmt = select(ResolverConfiguration)
            if landing_zone_id:
                stmt = stmt.where(ResolverConfiguration.landing_zone_id == landing_zone_id)
            if environment_id:
                stmt = stmt.where(ResolverConfiguration.environment_id == environment_id)
            stmt = stmt.order_by(ResolverConfiguration.created_at)

            result = await db.execute(stmt)
            items = list(result.scalars().all())
            return [_resolver_config_to_type(rc) for rc in items]

    @strawberry.field
    async def component_operations(
        self, info: Info, component_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> list[ComponentOperationType]:
        """List day-2 operations for a component."""
        await check_graphql_permission(info, "component:operation:read", str(tenant_id or ""))

        from app.db.session import async_session_factory
        from app.services.component.operation_service import ComponentOperationService

        async with async_session_factory() as db:
            svc = ComponentOperationService()
            ops = await svc.list_operations(db, component_id)
            return [_operation_to_type(op) for op in ops]

    @strawberry.field
    async def suggest_resolvers_for_field(
        self, info: Info, field_type: str, provider_id: uuid.UUID | None = None,
    ) -> strawberry.scalars.JSON:
        """Suggest compatible resolvers for a field type."""
        await check_graphql_permission(info, "resolver:config:read", "")

        from app.db.session import async_session_factory
        from app.services.resolver.binding_validator import ResolverBindingValidator

        async with async_session_factory() as db:
            validator = ResolverBindingValidator()
            return await validator.suggest_resolvers_for_field(db, field_type, provider_id)

    @strawberry.field
    async def validate_resolver_bindings(
        self, info: Info, component_id: uuid.UUID,
    ) -> list[str]:
        """Validate resolver bindings on a component. Returns warnings."""
        await check_graphql_permission(info, "component:definition:read", "")

        from app.db.session import async_session_factory
        from app.services.resolver.binding_validator import ResolverBindingValidator

        async with async_session_factory() as db:
            validator = ResolverBindingValidator()
            return await validator.validate_bindings(db, component_id)

    @strawberry.field
    async def resolver_definitions(
        self, info: Info, provider_id: uuid.UUID | None = None,
    ) -> list[ResolverType]:
        """List resolver definitions, optionally filtered by compatible provider."""
        await check_graphql_permission(info, "resolver:config:read", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            items = await svc.list_all(db, provider_id=provider_id)
            return [_resolver_to_type(r) for r in items]

    @strawberry.field
    async def resolver_definition(
        self, info: Info, resolver_id: uuid.UUID,
    ) -> ResolverType | None:
        """Get a single resolver definition by ID."""
        await check_graphql_permission(info, "resolver:config:read", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            r = await svc.get(db, resolver_id)
            return _resolver_to_type(r) if r else None

    @strawberry.field
    async def component_governance(
        self, info: Info, tenant_id: uuid.UUID,
    ) -> list[ComponentGovernanceType]:
        """List governance rules for a tenant."""
        await check_graphql_permission(info, "component:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.component.governance_service import ComponentGovernanceService

        async with async_session_factory() as db:
            svc = ComponentGovernanceService()
            rules = await svc.list_governance_for_tenant(db, tenant_id)
            return [_governance_to_type(g) for g in rules]
