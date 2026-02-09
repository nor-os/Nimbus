"""
Overview: GraphQL mutations for the service catalog — CRUD for offerings, price lists, overrides,
    CI class links, and CI class ↔ activity associations.
Architecture: GraphQL mutation resolvers for catalog write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.catalog_service, app.services.cmdb.ci_class_activity_service
Concepts: Catalog mutations enforce permission checks and commit within session context.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.catalog import _assoc_to_gql, _offering_to_gql, _price_list_to_gql
from app.api.graphql.types.catalog import (
    CIClassActivityAssociationCreateInput,
    CIClassActivityAssociationType,
    PriceListCreateInput,
    PriceListItemCreateInput,
    PriceListItemType,
    PriceListItemUpdateInput,
    PriceListType,
    ServiceOfferingCreateInput,
    ServiceOfferingType,
    ServiceOfferingUpdateInput,
    TenantPriceOverrideCreateInput,
    TenantPriceOverrideType,
)


@strawberry.type
class CatalogMutation:
    # ── Service Offerings ─────────────────────────────────────────────

    @strawberry.mutation
    async def create_service_offering(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ServiceOfferingCreateInput,
    ) -> ServiceOfferingType:
        """Create a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            data = {
                "name": input.name,
                "description": input.description,
                "category": input.category,
                "measuring_unit": input.measuring_unit,
                "service_type": input.service_type,
                "operating_model": input.operating_model,
                "default_coverage_model": input.default_coverage_model,
            }
            o = await service.create_offering(str(tenant_id), data)

            # Set CI classes if provided
            if input.ci_class_ids:
                await service.set_offering_ci_classes(
                    str(o.id), str(tenant_id),
                    [str(cid) for cid in input.ci_class_ids],
                )

            await db.commit()
            # Re-fetch to get loaded relationships
            o = await service.get_offering(str(o.id), str(tenant_id))
            return _offering_to_gql(o)

    @strawberry.mutation
    async def update_service_offering(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ServiceOfferingUpdateInput,
    ) -> ServiceOfferingType:
        """Update a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            data: dict = {}
            if input.name is not None:
                data["name"] = input.name
            if input.description is not strawberry.UNSET:
                data["description"] = input.description
            if input.category is not strawberry.UNSET:
                data["category"] = input.category
            if input.measuring_unit is not None:
                data["measuring_unit"] = input.measuring_unit
            if input.service_type is not None:
                data["service_type"] = input.service_type
            if input.operating_model is not strawberry.UNSET:
                data["operating_model"] = input.operating_model
            if input.default_coverage_model is not strawberry.UNSET:
                data["default_coverage_model"] = input.default_coverage_model
            if input.is_active is not None:
                data["is_active"] = input.is_active

            o = await service.update_offering(str(id), str(tenant_id), data)

            # Set CI classes if provided
            if input.ci_class_ids is not strawberry.UNSET and input.ci_class_ids is not None:
                await service.set_offering_ci_classes(
                    str(id), str(tenant_id),
                    [str(cid) for cid in input.ci_class_ids],
                )

            await db.commit()
            # Re-fetch to get loaded relationships
            o = await service.get_offering(str(id), str(tenant_id))
            return _offering_to_gql(o)

    @strawberry.mutation
    async def delete_service_offering(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            result = await service.delete_offering(str(id), str(tenant_id))
            await db.commit()
            return result

    # ── Offering Regions ────────────────────────────────────────────

    @strawberry.mutation
    async def set_service_offering_regions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offering_id: uuid.UUID,
        region_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Set the delivery regions for a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            result = await service.set_offering_regions(
                str(offering_id),
                str(tenant_id),
                [str(rid) for rid in region_ids],
            )
            await db.commit()
            return [uuid.UUID(r) for r in result]

    # ── Offering CI Classes ────────────────────────────────────────

    @strawberry.mutation
    async def set_service_offering_ci_classes(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offering_id: uuid.UUID,
        ci_class_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Set the CI classes for a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            result = await service.set_offering_ci_classes(
                str(offering_id),
                str(tenant_id),
                [str(cid) for cid in ci_class_ids],
            )
            await db.commit()
            return [uuid.UUID(r) for r in result]

    # ── CI Class ↔ Activity Associations ───────────────────────────

    @strawberry.mutation
    async def create_ci_class_activity_association(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CIClassActivityAssociationCreateInput,
    ) -> CIClassActivityAssociationType:
        """Create a CI class ↔ activity template association."""
        await check_graphql_permission(
            info, "cmdb:activity-association:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        async with async_session_factory() as db:
            service = CIClassActivityService(db)
            assoc = await service.create_association(str(tenant_id), {
                "ci_class_id": str(input.ci_class_id),
                "activity_template_id": str(input.activity_template_id),
                "relationship_type": input.relationship_type,
            })
            await db.commit()
            return _assoc_to_gql(assoc)

    @strawberry.mutation
    async def delete_ci_class_activity_association(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> bool:
        """Delete a CI class ↔ activity template association."""
        await check_graphql_permission(
            info, "cmdb:activity-association:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        async with async_session_factory() as db:
            service = CIClassActivityService(db)
            result = await service.delete_association(str(id), str(tenant_id))
            await db.commit()
            return result

    # ── Price Lists ───────────────────────────────────────────────────

    @strawberry.mutation
    async def create_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: PriceListCreateInput,
    ) -> PriceListType:
        """Create a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            target_tenant = str(input.client_tenant_id) if input.client_tenant_id else str(tenant_id)
            data = {
                "name": input.name,
                "is_default": input.is_default,
                "effective_from": input.effective_from,
                "effective_to": input.effective_to,
            }
            pl = await service.create_price_list(target_tenant, data)
            await db.commit()
            return _price_list_to_gql(pl)

    @strawberry.mutation
    async def delete_price_list(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            result = await service.delete_price_list(
                str(id), str(tenant_id)
            )
            await db.commit()
            return result

    # ── Price List Items ──────────────────────────────────────────────

    @strawberry.mutation
    async def add_price_list_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
        input: PriceListItemCreateInput,
    ) -> PriceListItemType:
        """Add an item to a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            data = {
                "service_offering_id": input.service_offering_id,
                "price_per_unit": input.price_per_unit,
                "currency": input.currency,
                "delivery_region_id": input.delivery_region_id,
                "coverage_model": input.coverage_model,
                "min_quantity": input.min_quantity,
                "max_quantity": input.max_quantity,
            }
            item = await service.add_price_item(str(price_list_id), data)
            await db.commit()
            return PriceListItemType(
                id=item.id,
                price_list_id=item.price_list_id,
                service_offering_id=item.service_offering_id,
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )

    @strawberry.mutation
    async def update_price_list_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: PriceListItemUpdateInput,
    ) -> PriceListItemType:
        """Update a price list item."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            data: dict = {}
            if input.price_per_unit is not None:
                data["price_per_unit"] = input.price_per_unit
            if input.currency is not None:
                data["currency"] = input.currency
            if input.min_quantity is not strawberry.UNSET:
                data["min_quantity"] = input.min_quantity
            if input.max_quantity is not strawberry.UNSET:
                data["max_quantity"] = input.max_quantity

            item = await service.update_price_item(str(id), data)
            await db.commit()
            return PriceListItemType(
                id=item.id,
                price_list_id=item.price_list_id,
                service_offering_id=item.service_offering_id,
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )

    # ── Tenant Price Overrides ────────────────────────────────────────

    @strawberry.mutation
    async def create_tenant_price_override(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: TenantPriceOverrideCreateInput,
    ) -> TenantPriceOverrideType:
        """Create a tenant price override."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            data = {
                "service_offering_id": input.service_offering_id,
                "price_per_unit": input.price_per_unit,
                "discount_percent": input.discount_percent,
                "delivery_region_id": input.delivery_region_id,
                "coverage_model": input.coverage_model,
                "effective_from": input.effective_from,
                "effective_to": input.effective_to,
            }
            o = await service.create_override(str(tenant_id), data)
            await db.commit()
            return TenantPriceOverrideType(
                id=o.id,
                tenant_id=o.tenant_id,
                service_offering_id=o.service_offering_id,
                delivery_region_id=o.delivery_region_id,
                coverage_model=o.coverage_model,
                price_per_unit=o.price_per_unit,
                discount_percent=o.discount_percent,
                effective_from=o.effective_from,
                effective_to=o.effective_to,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )

    @strawberry.mutation
    async def copy_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        source_id: uuid.UUID,
        new_name: str,
        client_tenant_id: uuid.UUID | None = None,
    ) -> PriceListType:
        """Copy a price list with all its items."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            pl = await service.copy_price_list(
                str(source_id),
                str(tenant_id),
                new_name,
                client_tenant_id=str(client_tenant_id) if client_tenant_id else None,
            )
            await db.commit()
            return _price_list_to_gql(pl)

    @strawberry.mutation
    async def delete_tenant_price_override(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a tenant price override."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            result = await service.delete_override(str(id), str(tenant_id))
            await db.commit()
            return result
