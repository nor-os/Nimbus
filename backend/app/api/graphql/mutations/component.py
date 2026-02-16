"""
Overview: GraphQL mutations for components, resolvers, and governance.
Architecture: Mutation resolvers for component framework (Section 11)
Dependencies: strawberry, app.services.component.*, app.api.graphql.auth
Concepts: Component CRUD + publish, resolver configuration management, governance rules
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.component import (
    _component_to_type,
    _governance_to_type,
    _operation_to_type,
    _resolver_config_to_type,
)
from app.api.graphql.types.component import (
    ComponentGovernanceType,
    ComponentOperationCreateInput,
    ComponentOperationType,
    ComponentOperationUpdateInput,
    ComponentPublishInput,
    ComponentType,
    ComponentCreateInput,
    ComponentUpdateInput,
    GovernanceInput,
    ResolverConfigurationInput,
    ResolverConfigurationType,
    ResolverDefinitionCreateInput,
    ResolverDefinitionUpdateInput,
    ResolverType,
)
from app.models.component import ComponentLanguage, EstimatedDowntime


@strawberry.type
class ComponentMutation:

    # ── Component CRUD ─────────────────────────────────────────────────

    @strawberry.mutation
    async def create_component(
        self, info: Info, input: ComponentCreateInput,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentType:
        """Create a new draft component. Null tenant_id = provider-level shared."""
        user_id = await check_graphql_permission(
            info, "component:definition:create", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            c = await svc.create_component(
                db,
                tenant_id=tenant_id,
                provider_id=input.provider_id,
                semantic_type_id=input.semantic_type_id,
                name=input.name,
                display_name=input.display_name,
                language=ComponentLanguage(input.language.value),
                created_by=user_id,
                description=input.description,
                code=input.code,
                input_schema=input.input_schema,
                output_schema=input.output_schema,
                resolver_bindings=input.resolver_bindings,
            )
            await db.commit()
            return _component_to_type(c)

    @strawberry.mutation
    async def update_component(
        self, info: Info,
        component_id: uuid.UUID, input: ComponentUpdateInput,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentType:
        """Update a draft component."""
        await check_graphql_permission(
            info, "component:definition:update", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            kwargs = {}
            if input.name is not None:
                kwargs["name"] = input.name
            if input.display_name is not None:
                kwargs["display_name"] = input.display_name
            if input.description is not None:
                kwargs["description"] = input.description
            if input.code is not None:
                kwargs["code"] = input.code
            if input.input_schema is not None:
                kwargs["input_schema"] = input.input_schema
            if input.output_schema is not None:
                kwargs["output_schema"] = input.output_schema
            if input.resolver_bindings is not None:
                kwargs["resolver_bindings"] = input.resolver_bindings
            if input.language is not None:
                kwargs["language"] = ComponentLanguage(input.language.value)

            c = await svc.update_component(db, component_id, **kwargs)
            await db.commit()
            return _component_to_type(c)

    @strawberry.mutation
    async def publish_component(
        self, info: Info,
        component_id: uuid.UUID, input: ComponentPublishInput,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentType:
        """Publish a component — creates an immutable version snapshot."""
        user_id = await check_graphql_permission(
            info, "component:definition:publish", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            c = await svc.publish_component(
                db, component_id,
                changelog=input.changelog,
                published_by=user_id,
            )
            await db.commit()
            return _component_to_type(c)

    @strawberry.mutation
    async def delete_component(
        self, info: Info, component_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> bool:
        """Soft-delete a component."""
        await check_graphql_permission(
            info, "component:definition:delete", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.component_service import ComponentService

        async with async_session_factory() as db:
            svc = ComponentService()
            await svc.delete_component(db, component_id)
            await db.commit()
            return True

    # ── Resolver Configuration ─────────────────────────────────────────

    @strawberry.mutation
    async def set_resolver_configuration(
        self, info: Info, tenant_id: uuid.UUID, input: ResolverConfigurationInput,
    ) -> ResolverConfigurationType:
        """Create or update a resolver configuration for a scope."""
        await check_graphql_permission(
            info, "resolver:config:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.models.resolver import ResolverConfiguration
        from sqlalchemy import select

        async with async_session_factory() as db:
            # Check for existing config at this scope
            stmt = select(ResolverConfiguration).where(
                ResolverConfiguration.resolver_id == input.resolver_id,
            )
            if input.landing_zone_id:
                stmt = stmt.where(ResolverConfiguration.landing_zone_id == input.landing_zone_id)
            else:
                stmt = stmt.where(ResolverConfiguration.landing_zone_id.is_(None))
            if input.environment_id:
                stmt = stmt.where(ResolverConfiguration.environment_id == input.environment_id)
            else:
                stmt = stmt.where(ResolverConfiguration.environment_id.is_(None))

            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.config = input.config
                await db.flush()
                await db.refresh(existing)
                rc = existing
            else:
                rc = ResolverConfiguration(
                    resolver_id=input.resolver_id,
                    landing_zone_id=input.landing_zone_id,
                    environment_id=input.environment_id,
                    config=input.config,
                )
                db.add(rc)
                await db.flush()
                await db.refresh(rc)

            await db.commit()
            return _resolver_config_to_type(rc)

    @strawberry.mutation
    async def delete_resolver_configuration(
        self, info: Info, tenant_id: uuid.UUID, configuration_id: uuid.UUID,
    ) -> bool:
        """Delete a resolver configuration."""
        await check_graphql_permission(
            info, "resolver:config:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.models.resolver import ResolverConfiguration
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(ResolverConfiguration).where(ResolverConfiguration.id == configuration_id)
            )
            rc = result.scalar_one_or_none()
            if not rc:
                raise ValueError(f"Resolver configuration '{configuration_id}' not found")
            await db.delete(rc)
            await db.commit()
            return True

    # ── Operations ───────────────────────────────────────────────────

    @strawberry.mutation
    async def create_component_operation(
        self, info: Info,
        component_id: uuid.UUID, input: ComponentOperationCreateInput,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentOperationType:
        """Create a day-2 operation on a component."""
        await check_graphql_permission(
            info, "component:operation:create", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.operation_service import ComponentOperationService

        async with async_session_factory() as db:
            svc = ComponentOperationService()
            op = await svc.create_operation(
                db,
                component_id=component_id,
                name=input.name,
                display_name=input.display_name,
                workflow_definition_id=input.workflow_definition_id,
                description=input.description,
                input_schema=input.input_schema,
                output_schema=input.output_schema,
                is_destructive=input.is_destructive,
                requires_approval=input.requires_approval,
                estimated_downtime=EstimatedDowntime(input.estimated_downtime.value),
                sort_order=input.sort_order,
            )
            await db.commit()
            return _operation_to_type(op)

    @strawberry.mutation
    async def update_component_operation(
        self, info: Info,
        operation_id: uuid.UUID, input: ComponentOperationUpdateInput,
        tenant_id: uuid.UUID | None = None,
    ) -> ComponentOperationType:
        """Update a component operation."""
        await check_graphql_permission(
            info, "component:operation:update", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.operation_service import ComponentOperationService

        async with async_session_factory() as db:
            svc = ComponentOperationService()
            kwargs = {}
            if input.name is not None:
                kwargs["name"] = input.name
            if input.display_name is not None:
                kwargs["display_name"] = input.display_name
            if input.description is not None:
                kwargs["description"] = input.description
            if input.input_schema is not None:
                kwargs["input_schema"] = input.input_schema
            if input.output_schema is not None:
                kwargs["output_schema"] = input.output_schema
            if input.workflow_definition_id is not None:
                kwargs["workflow_definition_id"] = input.workflow_definition_id
            if input.is_destructive is not None:
                kwargs["is_destructive"] = input.is_destructive
            if input.requires_approval is not None:
                kwargs["requires_approval"] = input.requires_approval
            if input.estimated_downtime is not None:
                kwargs["estimated_downtime"] = EstimatedDowntime(input.estimated_downtime.value)
            if input.sort_order is not None:
                kwargs["sort_order"] = input.sort_order

            op = await svc.update_operation(db, operation_id, **kwargs)
            await db.commit()
            return _operation_to_type(op)

    @strawberry.mutation
    async def delete_component_operation(
        self, info: Info,
        operation_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> bool:
        """Soft-delete a component operation."""
        await check_graphql_permission(
            info, "component:operation:delete", str(tenant_id or "")
        )

        from app.db.session import async_session_factory
        from app.services.component.operation_service import ComponentOperationService

        async with async_session_factory() as db:
            svc = ComponentOperationService()
            await svc.delete_operation(db, operation_id)
            await db.commit()
            return True

    # ── Governance ─────────────────────────────────────────────────────

    @strawberry.mutation
    async def set_component_governance(
        self, info: Info, input: GovernanceInput,
    ) -> ComponentGovernanceType:
        """Create or update a component governance rule."""
        await check_graphql_permission(
            info, "component:governance:manage", str(input.tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.component.governance_service import ComponentGovernanceService

        async with async_session_factory() as db:
            svc = ComponentGovernanceService()
            g = await svc.set_governance(
                db, input.component_id, input.tenant_id,
                is_allowed=input.is_allowed,
                parameter_constraints=input.parameter_constraints,
                max_instances=input.max_instances,
            )
            await db.commit()
            return _governance_to_type(g)

    @strawberry.mutation
    async def delete_component_governance(
        self, info: Info, component_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> bool:
        """Delete a component governance rule."""
        await check_graphql_permission(
            info, "component:governance:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.component.governance_service import ComponentGovernanceService

        async with async_session_factory() as db:
            svc = ComponentGovernanceService()
            await svc.delete_governance(db, component_id, tenant_id)
            await db.commit()
            return True

    # ── Resolver Definitions ──────────────────────────────────────────

    @strawberry.mutation
    async def create_resolver_definition(
        self, info: Info, input: ResolverDefinitionCreateInput,
    ) -> ResolverType:
        """Create a new resolver definition (Provider Admin only)."""
        await check_graphql_permission(info, "resolver:config:manage", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService
        from app.api.graphql.queries.component import _resolver_to_type

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            r = await svc.create(
                db,
                resolver_type=input.resolver_type,
                display_name=input.display_name,
                handler_class=input.handler_class,
                description=input.description,
                input_schema=input.input_schema,
                output_schema=input.output_schema,
                instance_config_schema=input.instance_config_schema,
                code=input.code,
                category=input.category,
                supports_release=input.supports_release,
                supports_update=input.supports_update,
                compatible_provider_ids=input.compatible_provider_ids,
            )
            await db.commit()
            return _resolver_to_type(r)

    @strawberry.mutation
    async def update_resolver_definition(
        self, info: Info, resolver_id: uuid.UUID, input: ResolverDefinitionUpdateInput,
    ) -> ResolverType:
        """Update a resolver definition (Provider Admin only)."""
        await check_graphql_permission(info, "resolver:config:manage", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService
        from app.api.graphql.queries.component import _resolver_to_type

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            kwargs = {}
            if input.display_name is not None:
                kwargs["display_name"] = input.display_name
            if input.description is not None:
                kwargs["description"] = input.description
            if input.input_schema is not None:
                kwargs["input_schema"] = input.input_schema
            if input.output_schema is not None:
                kwargs["output_schema"] = input.output_schema
            if input.instance_config_schema is not None:
                kwargs["instance_config_schema"] = input.instance_config_schema
            if input.code is not None:
                kwargs["code"] = input.code
            if input.category is not None:
                kwargs["category"] = input.category
            if input.supports_release is not None:
                kwargs["supports_release"] = input.supports_release
            if input.supports_update is not None:
                kwargs["supports_update"] = input.supports_update
            if input.compatible_provider_ids is not None:
                kwargs["compatible_provider_ids"] = input.compatible_provider_ids

            r = await svc.update(db, resolver_id, **kwargs)
            await db.commit()
            return _resolver_to_type(r)

    @strawberry.mutation
    async def delete_resolver_definition(
        self, info: Info, resolver_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a resolver definition (Provider Admin only)."""
        await check_graphql_permission(info, "resolver:config:manage", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            await svc.delete(db, resolver_id)
            await db.commit()
            return True

    @strawberry.mutation
    async def set_resolver_provider_compatibility(
        self, info: Info, resolver_id: uuid.UUID, provider_ids: list[uuid.UUID],
    ) -> bool:
        """Set provider compatibility for a resolver definition."""
        await check_graphql_permission(info, "resolver:config:manage", "")

        from app.db.session import async_session_factory
        from app.services.resolver.definition_service import ResolverDefinitionService

        async with async_session_factory() as db:
            svc = ResolverDefinitionService()
            await svc.set_provider_compatibility(db, resolver_id, provider_ids)
            await db.commit()
            return True
