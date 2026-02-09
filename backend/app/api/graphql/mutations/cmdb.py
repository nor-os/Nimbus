"""
Overview: GraphQL mutations for the CMDB — CI CRUD, lifecycle management, relationships,
    classes, templates, compartments, and saved searches.
Architecture: GraphQL mutation resolvers for CMDB write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.*
Concepts: All mutations enforce permission checks, validate inputs, and commit within
    a session context. Converter helpers transform ORM models to GQL types.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.cmdb import (
    _ci_to_gql,
    _class_detail_to_gql,
    _class_to_gql,
    _rel_to_gql,
    _template_to_gql,
)
from app.api.graphql.types.cmdb import (
    CIClassCreateInput,
    CIClassDetailType,
    CIClassType,
    CIClassUpdateInput,
    CICreateInput,
    CIFromTemplateInput,
    CIRelationshipInput,
    CIRelationshipType,
    CITemplateCreateInput,
    CITemplateType,
    CITemplateUpdateInput,
    CIType,
    CIUpdateInput,
    CompartmentCreateInput,
    CompartmentNodeType,
    CompartmentUpdateInput,
    SavedSearchInput,
    SavedSearchType,
)


@strawberry.type
class CMDBMutation:
    # ── Configuration Items ───────────────────────────────────────────

    @strawberry.mutation
    async def create_ci(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CICreateInput,
    ) -> CIType:
        """Create a new configuration item."""
        await check_graphql_permission(info, "cmdb:ci:create", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            data = {
                "ci_class_id": input.ci_class_id,
                "name": input.name,
                "description": input.description,
                "compartment_id": input.compartment_id,
                "lifecycle_state": input.lifecycle_state,
                "attributes": input.attributes or {},
                "tags": input.tags or {},
                "cloud_resource_id": input.cloud_resource_id,
                "pulumi_urn": input.pulumi_urn,
            }
            ci = await service.create_ci(str(tenant_id), data)
            await db.commit()
            return _ci_to_gql(ci)

    @strawberry.mutation
    async def update_ci(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: CIUpdateInput,
    ) -> CIType:
        """Update a configuration item."""
        await check_graphql_permission(info, "cmdb:ci:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            data: dict = {}
            if input.name is not None:
                data["name"] = input.name
            if input.description is not strawberry.UNSET:
                data["description"] = input.description
            if input.attributes is not None:
                data["attributes"] = input.attributes
            if input.tags is not None:
                data["tags"] = input.tags
            if input.cloud_resource_id is not strawberry.UNSET:
                data["cloud_resource_id"] = input.cloud_resource_id
            if input.pulumi_urn is not strawberry.UNSET:
                data["pulumi_urn"] = input.pulumi_urn

            ci = await service.update_ci(str(id), str(tenant_id), data)
            await db.commit()
            return _ci_to_gql(ci)

    @strawberry.mutation
    async def delete_ci(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete a configuration item."""
        await check_graphql_permission(info, "cmdb:ci:delete", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            result = await service.delete_ci(str(id), str(tenant_id))
            await db.commit()
            return result

    @strawberry.mutation
    async def move_ci(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        compartment_id: uuid.UUID | None = None,
    ) -> CIType:
        """Move a CI to a different compartment."""
        await check_graphql_permission(info, "cmdb:ci:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            ci = await service.move_ci(
                str(id),
                str(tenant_id),
                str(compartment_id) if compartment_id else None,
            )
            await db.commit()
            return _ci_to_gql(ci)

    @strawberry.mutation
    async def change_ci_state(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        new_state: str,
    ) -> CIType:
        """Change the lifecycle state of a CI."""
        await check_graphql_permission(info, "cmdb:ci:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            ci = await service.change_lifecycle(
                str(id), str(tenant_id), new_state
            )
            await db.commit()
            return _ci_to_gql(ci)

    # ── Relationships ─────────────────────────────────────────────────

    @strawberry.mutation
    async def create_relationship(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CIRelationshipInput,
    ) -> CIRelationshipType:
        """Create a relationship between two CIs."""
        await check_graphql_permission(
            info, "cmdb:relationship:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            rel = await service.add_relationship(
                str(tenant_id),
                str(input.source_ci_id),
                str(input.target_ci_id),
                str(input.relationship_type_id),
                input.attributes,
            )
            await db.commit()
            # Re-fetch with relationships loaded
            rels = await service.get_relationships(
                str(input.source_ci_id), str(tenant_id)
            )
            for r in rels:
                if r.id == rel.id:
                    return _rel_to_gql(r)
            return _rel_to_gql(rel)

    @strawberry.mutation
    async def delete_relationship(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> bool:
        """Delete a CI relationship."""
        await check_graphql_permission(
            info, "cmdb:relationship:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService

        async with async_session_factory() as db:
            service = CIService(db)
            result = await service.remove_relationship(
                str(id), str(tenant_id)
            )
            await db.commit()
            return result

    # ── CI Classes ────────────────────────────────────────────────────

    @strawberry.mutation
    async def create_ci_class(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CIClassCreateInput,
    ) -> CIClassType:
        """Create a custom CI class."""
        await check_graphql_permission(
            info, "cmdb:class:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.class_service import ClassService

        async with async_session_factory() as db:
            service = ClassService(db)
            data = {
                "name": input.name,
                "display_name": input.display_name,
                "parent_class_id": input.parent_class_id,
                "schema": input.schema_def,
                "icon": input.icon,
            }
            c = await service.create_class(str(tenant_id), data)
            await db.commit()
            return _class_to_gql(c)

    @strawberry.mutation
    async def update_ci_class(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: CIClassUpdateInput,
    ) -> CIClassDetailType:
        """Update a CI class."""
        await check_graphql_permission(
            info, "cmdb:class:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.class_service import ClassService

        async with async_session_factory() as db:
            service = ClassService(db)
            data: dict = {}
            if input.display_name is not None:
                data["display_name"] = input.display_name
            if input.icon is not strawberry.UNSET:
                data["icon"] = input.icon
            if input.is_active is not None:
                data["is_active"] = input.is_active
            if input.schema_def is not strawberry.UNSET:
                data["schema"] = input.schema_def

            c = await service.update_class(id, str(tenant_id), data)
            await db.commit()
            return _class_detail_to_gql(c)

    # ── Templates ─────────────────────────────────────────────────────

    @strawberry.mutation
    async def create_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CITemplateCreateInput,
    ) -> CITemplateType:
        """Create a CI template."""
        await check_graphql_permission(
            info, "cmdb:template:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.template_service import TemplateService

        async with async_session_factory() as db:
            service = TemplateService(db)
            data = {
                "name": input.name,
                "ci_class_id": input.ci_class_id,
                "description": input.description,
                "attributes": input.attributes or {},
                "tags": input.tags or {},
                "relationship_templates": input.relationship_templates,
                "constraints": input.constraints,
            }
            t = await service.create_template(str(tenant_id), data)
            await db.commit()
            return _template_to_gql(t)

    @strawberry.mutation
    async def update_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: CITemplateUpdateInput,
    ) -> CITemplateType:
        """Update a CI template."""
        await check_graphql_permission(
            info, "cmdb:template:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.template_service import TemplateService

        async with async_session_factory() as db:
            service = TemplateService(db)
            data: dict = {}
            if input.name is not None:
                data["name"] = input.name
            if input.description is not strawberry.UNSET:
                data["description"] = input.description
            if input.attributes is not None:
                data["attributes"] = input.attributes
            if input.tags is not None:
                data["tags"] = input.tags
            if input.relationship_templates is not strawberry.UNSET:
                data["relationship_templates"] = input.relationship_templates
            if input.constraints is not strawberry.UNSET:
                data["constraints"] = input.constraints
            if input.is_active is not None:
                data["is_active"] = input.is_active

            t = await service.update_template(str(id), str(tenant_id), data)
            await db.commit()
            return _template_to_gql(t)

    @strawberry.mutation
    async def delete_template(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a CI template."""
        await check_graphql_permission(
            info, "cmdb:template:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.template_service import TemplateService

        async with async_session_factory() as db:
            service = TemplateService(db)
            result = await service.delete_template(str(id), str(tenant_id))
            await db.commit()
            return result

    @strawberry.mutation
    async def create_ci_from_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CIFromTemplateInput,
    ) -> CIType:
        """Create a CI from a template with optional overrides."""
        await check_graphql_permission(info, "cmdb:ci:create", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_service import CIService
        from app.services.cmdb.template_service import TemplateService

        async with async_session_factory() as db:
            tmpl_service = TemplateService(db)
            ci_service = CIService(db)

            template = await tmpl_service.get_template(
                str(input.template_id), str(tenant_id)
            )
            if not template:
                raise ValueError("Template not found")

            overrides = {
                "name": input.name,
                "description": input.description,
                "compartment_id": input.compartment_id,
                "attributes": input.attributes,
                "tags": input.tags,
                "lifecycle_state": input.lifecycle_state,
            }
            data = tmpl_service.build_ci_data_from_template(
                template, overrides
            )
            ci = await ci_service.create_ci(str(tenant_id), data)
            await db.commit()
            return _ci_to_gql(ci)

    # ── Compartments ──────────────────────────────────────────────────

    @strawberry.mutation
    async def create_compartment(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CompartmentCreateInput,
    ) -> CompartmentNodeType:
        """Create a compartment."""
        await check_graphql_permission(
            info, "cmdb:compartment:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.models.compartment import Compartment

        async with async_session_factory() as db:
            comp = Compartment(
                tenant_id=tenant_id,
                name=input.name,
                description=input.description,
                parent_id=input.parent_id,
                cloud_id=input.cloud_id,
                provider_type=input.provider_type,
            )
            db.add(comp)
            await db.commit()
            return CompartmentNodeType(
                id=str(comp.id),
                name=comp.name,
                description=comp.description,
                cloud_id=comp.cloud_id,
                provider_type=comp.provider_type,
                children=[],
            )

    @strawberry.mutation
    async def update_compartment(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: CompartmentUpdateInput,
    ) -> CompartmentNodeType:
        """Update a compartment."""
        await check_graphql_permission(
            info, "cmdb:compartment:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.compartment_service import CMDBCompartmentService

        async with async_session_factory() as db:
            service = CMDBCompartmentService(db)
            comp = await service.get_compartment(str(id), str(tenant_id))
            if not comp:
                raise ValueError("Compartment not found")
            if input.name is not None:
                comp.name = input.name
            if input.description is not strawberry.UNSET:
                comp.description = input.description
            if input.cloud_id is not strawberry.UNSET:
                comp.cloud_id = input.cloud_id
            if input.provider_type is not strawberry.UNSET:
                comp.provider_type = input.provider_type
            await db.commit()
            return CompartmentNodeType(
                id=str(comp.id),
                name=comp.name,
                description=comp.description,
                cloud_id=comp.cloud_id,
                provider_type=comp.provider_type,
                children=[],
            )

    @strawberry.mutation
    async def delete_compartment(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete a compartment."""
        await check_graphql_permission(
            info, "cmdb:compartment:manage", str(tenant_id)
        )

        from datetime import UTC, datetime

        from app.db.session import async_session_factory
        from app.services.cmdb.compartment_service import CMDBCompartmentService

        async with async_session_factory() as db:
            service = CMDBCompartmentService(db)
            comp = await service.get_compartment(str(id), str(tenant_id))
            if not comp:
                raise ValueError("Compartment not found")
            comp.deleted_at = datetime.now(UTC)
            await db.commit()
            return True

    # ── Saved Searches ────────────────────────────────────────────────

    @strawberry.mutation
    async def save_search(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        input: SavedSearchInput,
    ) -> SavedSearchType:
        """Save a CMDB search query."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.search_service import SearchService

        async with async_session_factory() as db:
            service = SearchService(db)
            s = await service.save_search(
                str(tenant_id),
                str(user_id),
                input.name,
                input.query_text,
                input.filters,
                input.sort_config,
            )
            await db.commit()
            return SavedSearchType(
                id=s.id,
                tenant_id=s.tenant_id,
                user_id=s.user_id,
                name=s.name,
                query_text=s.query_text,
                filters=s.filters,
                sort_config=s.sort_config,
                is_default=s.is_default,
            )

    @strawberry.mutation
    async def delete_saved_search(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a saved search."""
        await check_graphql_permission(info, "cmdb:ci:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cmdb.search_service import SearchService

        async with async_session_factory() as db:
            service = SearchService(db)
            result = await service.delete_saved_search(
                str(id), str(tenant_id), str(user_id)
            )
            await db.commit()
            return result
