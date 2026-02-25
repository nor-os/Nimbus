"""
Overview: GraphQL mutations for the service catalog redesign — catalog lifecycle, catalog items,
    tenant pins, provider SKUs, offering SKUs, offering lifecycle, service groups,
    catalog overlay items, region constraints.
Architecture: GraphQL mutation resolvers for service catalog write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.service_catalog_service, app.services.cmdb.sku_service,
    app.services.cmdb.service_group_service, app.services.cmdb.overlay_service,
    app.services.cmdb.region_constraint_service, app.services.cmdb.catalog_service
Concepts: Catalog mutations enforce permission checks and commit within session context.
"""

import uuid
from datetime import date

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.catalog import _offering_to_gql
from app.api.graphql.queries.service_catalog_queries import (
    _catalog_to_gql,
    _group_to_gql,
    _pin_to_gql,
    _sku_to_gql,
)
from app.api.graphql.types.catalog import ServiceOfferingType
from app.api.graphql.types.service_catalog_types import (
    CatalogOverlayItemCreateInput,
    CatalogOverlayItemType,
    ProviderSkuCreateInput,
    ProviderSkuType,
    ProviderSkuUpdateInput,
    ServiceCatalogCreateInput,
    ServiceCatalogItemType,
    ServiceCatalogType,
    ServiceCatalogVersionInput,
    ServiceGroupCreateInput,
    ServiceGroupItemType,
    ServiceGroupType,
    ServiceGroupUpdateInput,
    ServiceOfferingSkuType,
    TenantCatalogPinType,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ServiceCatalogMutation:
    # ── Catalog Lifecycle ─────────────────────────────────────────────

    @strawberry.mutation
    async def create_service_catalog(
        self, info: Info, tenant_id: uuid.UUID, input: ServiceCatalogCreateInput,
    ) -> ServiceCatalogType:
        """Create a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        catalog = await service.create_catalog(str(tenant_id), {
            "name": input.name,
            "description": input.description,
        })
        await db.commit()
        await db.refresh(catalog, ["items"])
        return _catalog_to_gql(catalog)

    @strawberry.mutation
    async def delete_service_catalog(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        """Delete a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        result = await service.delete_catalog(str(id), str(tenant_id))
        await db.commit()
        return result

    @strawberry.mutation
    async def create_service_catalog_version(
        self, info: Info, tenant_id: uuid.UUID, input: ServiceCatalogVersionInput,
    ) -> ServiceCatalogType:
        """Create a new version of a service catalog by cloning items and bumping version."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        catalog = await service.create_version(str(input.catalog_id), input.bump)
        await db.commit()
        await db.refresh(catalog, ["items"])
        return _catalog_to_gql(catalog)

    @strawberry.mutation
    async def publish_service_catalog(
        self, info: Info, tenant_id: uuid.UUID, catalog_id: uuid.UUID,
    ) -> ServiceCatalogType:
        """Publish a draft service catalog; archives the previous published version."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        catalog = await service.publish_catalog(str(catalog_id))
        await db.commit()
        await db.refresh(catalog, ["items"])
        return _catalog_to_gql(catalog)

    @strawberry.mutation
    async def archive_service_catalog(
        self, info: Info, tenant_id: uuid.UUID, catalog_id: uuid.UUID,
    ) -> ServiceCatalogType:
        """Archive a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        catalog = await service.archive_catalog(str(catalog_id))
        await db.commit()
        await db.refresh(catalog, ["items"])
        return _catalog_to_gql(catalog)

    @strawberry.mutation
    async def clone_catalog_for_tenant(
        self, info: Info, tenant_id: uuid.UUID,
        catalog_id: uuid.UUID, target_tenant_id: uuid.UUID,
    ) -> ServiceCatalogType:
        """Clone a service catalog to a different tenant."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        catalog = await service.clone_for_tenant(
            str(catalog_id), str(target_tenant_id)
        )
        await db.commit()
        await db.refresh(catalog, ["items"])
        return _catalog_to_gql(catalog)

    # ── Catalog Items ─────────────────────────────────────────────────

    @strawberry.mutation
    async def add_catalog_item(
        self, info: Info, tenant_id: uuid.UUID,
        catalog_id: uuid.UUID,
        service_offering_id: uuid.UUID | None = None,
        service_group_id: uuid.UUID | None = None,
        sort_order: int | None = None,
    ) -> ServiceCatalogItemType:
        """Add an item (offering or group) to a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        item = await service.add_catalog_item(str(catalog_id), {
            "service_offering_id": str(service_offering_id) if service_offering_id else None,
            "service_group_id": str(service_group_id) if service_group_id else None,
            "sort_order": sort_order or 0,
        })
        await db.commit()
        return ServiceCatalogItemType(
            id=item.id,
            catalog_id=item.catalog_id,
            service_offering_id=item.service_offering_id,
            service_group_id=item.service_group_id,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @strawberry.mutation
    async def remove_catalog_item(
        self, info: Info, tenant_id: uuid.UUID, item_id: uuid.UUID,
    ) -> bool:
        """Remove an item from a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        result = await service.remove_catalog_item(str(item_id))
        await db.commit()
        return result

    # ── Tenant Pins ───────────────────────────────────────────────────

    @strawberry.mutation
    async def pin_tenant_to_catalog(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        catalog_id: uuid.UUID,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> TenantCatalogPinType:
        """Pin a tenant to a specific service catalog version for a date range."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        pin = await service.pin_tenant(
            str(tenant_id), str(catalog_id),
            effective_from=effective_from,
            effective_to=effective_to,
        )
        await db.commit()
        # Re-query with eager loading for all nested relationships
        pins = await service.get_pins(str(tenant_id))
        pin = next((p for p in pins if p.id == pin.id), pin)
        return _pin_to_gql(pin)

    @strawberry.mutation
    async def unpin_tenant_from_catalog(
        self, info: Info, tenant_id: uuid.UUID, catalog_id: uuid.UUID,
    ) -> bool:
        """Remove a tenant's pin from a service catalog version."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        result = await service.unpin_tenant(
            str(tenant_id), str(catalog_id)
        )
        await db.commit()
        return result

    # ── Provider SKUs ─────────────────────────────────────────────────

    @strawberry.mutation
    async def create_provider_sku(
        self, info: Info, tenant_id: uuid.UUID, input: ProviderSkuCreateInput,
    ) -> ProviderSkuType:
        """Create a provider SKU."""
        await check_graphql_permission(info, "catalog:sku:manage", str(tenant_id))

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        sku = await service.create_sku({
            "provider_id": str(input.provider_id),
            "external_sku_id": input.external_sku_id,
            "name": input.name,
            "display_name": input.display_name,
            "description": input.description,
            "ci_class_id": str(input.ci_class_id) if input.ci_class_id else None,
            "measuring_unit": input.measuring_unit,
            "category": input.category,
            "unit_cost": input.unit_cost,
            "cost_currency": input.cost_currency,
            "attributes": input.attributes,
        })
        await db.commit()
        return _sku_to_gql(sku)

    @strawberry.mutation
    async def update_provider_sku(
        self, info: Info, tenant_id: uuid.UUID,
        id: uuid.UUID, input: ProviderSkuUpdateInput,
    ) -> ProviderSkuType:
        """Update a provider SKU."""
        await check_graphql_permission(info, "catalog:sku:manage", str(tenant_id))

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.description is not None:
            data["description"] = input.description
        if input.ci_class_id is not strawberry.UNSET:
            data["ci_class_id"] = str(input.ci_class_id) if input.ci_class_id else None
        if input.measuring_unit is not None:
            data["measuring_unit"] = input.measuring_unit
        if input.category is not strawberry.UNSET:
            data["category"] = input.category
        if input.unit_cost is not strawberry.UNSET:
            data["unit_cost"] = input.unit_cost
        if input.cost_currency is not None:
            data["cost_currency"] = input.cost_currency
        if input.attributes is not strawberry.UNSET:
            data["attributes"] = input.attributes

        sku = await service.update_sku(str(id), data)
        await db.commit()
        return _sku_to_gql(sku)

    @strawberry.mutation
    async def deactivate_provider_sku(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> ProviderSkuType:
        """Deactivate a provider SKU."""
        await check_graphql_permission(info, "catalog:sku:manage", str(tenant_id))

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        sku = await service.deactivate_sku(str(id))
        await db.commit()
        return _sku_to_gql(sku)

    # ── Offering SKUs ─────────────────────────────────────────────────

    @strawberry.mutation
    async def add_sku_to_offering(
        self, info: Info, tenant_id: uuid.UUID,
        service_offering_id: uuid.UUID, provider_sku_id: uuid.UUID,
        default_quantity: int | None = None,
        is_required: bool | None = None,
        sort_order: int | None = None,
    ) -> ServiceOfferingSkuType:
        """Link a provider SKU to a service offering."""
        await check_graphql_permission(info, "catalog:sku:manage", str(tenant_id))

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        link = await service.add_sku_to_offering(
            str(service_offering_id),
            str(provider_sku_id),
            {
                "default_quantity": default_quantity or 1,
                "is_required": is_required if is_required is not None else True,
                "sort_order": sort_order or 0,
            },
        )
        await db.commit()
        return ServiceOfferingSkuType(
            id=link.id,
            service_offering_id=link.service_offering_id,
            provider_sku_id=link.provider_sku_id,
            default_quantity=link.default_quantity,
            is_required=link.is_required,
            sort_order=link.sort_order,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )

    @strawberry.mutation
    async def remove_sku_from_offering(
        self, info: Info, tenant_id: uuid.UUID, link_id: uuid.UUID,
    ) -> bool:
        """Remove a provider SKU link from a service offering."""
        await check_graphql_permission(info, "catalog:sku:manage", str(tenant_id))

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        result = await service.remove_sku_from_offering(str(link_id))
        await db.commit()
        return result

    # ── Offering Lifecycle ────────────────────────────────────────────

    @strawberry.mutation
    async def clone_offering(
        self, info: Info, tenant_id: uuid.UUID, offering_id: uuid.UUID,
    ) -> ServiceOfferingType:
        """Clone a service offering."""
        await check_graphql_permission(info, "cmdb:catalog:manage", str(tenant_id))

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        o = await service.clone_offering(str(offering_id), str(tenant_id))
        await db.commit()
        o = await service.get_offering(str(o.id), str(tenant_id))
        return _offering_to_gql(o)

    @strawberry.mutation
    async def publish_offering(
        self, info: Info, tenant_id: uuid.UUID, offering_id: uuid.UUID,
    ) -> ServiceOfferingType:
        """Publish a draft service offering."""
        await check_graphql_permission(info, "cmdb:catalog:manage", str(tenant_id))

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        o = await service.publish_offering(str(offering_id), str(tenant_id))
        await db.commit()
        o = await service.get_offering(str(o.id), str(tenant_id))
        return _offering_to_gql(o)

    @strawberry.mutation
    async def archive_offering(
        self, info: Info, tenant_id: uuid.UUID, offering_id: uuid.UUID,
    ) -> ServiceOfferingType:
        """Archive a service offering."""
        await check_graphql_permission(info, "cmdb:catalog:manage", str(tenant_id))

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        o = await service.archive_offering(str(offering_id), str(tenant_id))
        await db.commit()
        o = await service.get_offering(str(o.id), str(tenant_id))
        return _offering_to_gql(o)

    # ── Service Groups ────────────────────────────────────────────────

    @strawberry.mutation
    async def create_service_group(
        self, info: Info, tenant_id: uuid.UUID, input: ServiceGroupCreateInput,
    ) -> ServiceGroupType:
        """Create a service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        group = await service.create_group(str(tenant_id), {
            "name": input.name,
            "display_name": input.display_name,
            "description": input.description,
        })
        await db.commit()
        await db.refresh(group, ["items"])
        return _group_to_gql(group)

    @strawberry.mutation
    async def update_service_group(
        self, info: Info, tenant_id: uuid.UUID,
        id: uuid.UUID, input: ServiceGroupUpdateInput,
    ) -> ServiceGroupType:
        """Update a service group (draft only)."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.display_name is not strawberry.UNSET:
            data["display_name"] = input.display_name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description

        group = await service.update_group(str(id), data)
        await db.commit()
        await db.refresh(group, ["items"])
        return _group_to_gql(group)

    @strawberry.mutation
    async def delete_service_group(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> bool:
        """Delete a service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        result = await service.delete_group(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def publish_service_group(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> ServiceGroupType:
        """Publish a draft service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        group = await service.publish_group(str(id))
        await db.commit()
        await db.refresh(group, ["items"])
        return _group_to_gql(group)

    @strawberry.mutation
    async def archive_service_group(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
    ) -> ServiceGroupType:
        """Archive a published service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        group = await service.archive_group(str(id))
        await db.commit()
        await db.refresh(group, ["items"])
        return _group_to_gql(group)

    @strawberry.mutation
    async def clone_service_group(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID,
        target_tenant_id: uuid.UUID | None = None,
    ) -> ServiceGroupType:
        """Clone a service group as a new draft."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        group = await service.clone_group(
            str(id),
            str(target_tenant_id) if target_tenant_id else None,
        )
        await db.commit()
        await db.refresh(group, ["items"])
        return _group_to_gql(group)

    @strawberry.mutation
    async def add_group_item(
        self, info: Info, tenant_id: uuid.UUID,
        group_id: uuid.UUID, service_offering_id: uuid.UUID,
        is_required: bool | None = None,
        sort_order: int | None = None,
    ) -> ServiceGroupItemType:
        """Add an offering to a service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        item = await service.add_item(
            str(group_id),
            str(service_offering_id),
            is_required if is_required is not None else True,
            sort_order or 0,
        )
        await db.commit()
        await db.refresh(item, ["offering"])
        return ServiceGroupItemType(
            id=item.id,
            group_id=item.group_id,
            service_offering_id=item.service_offering_id,
            offering_name=getattr(item.offering, "name", None) if getattr(item, "offering", None) else None,
            is_required=item.is_required,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @strawberry.mutation
    async def remove_group_item(
        self, info: Info, tenant_id: uuid.UUID, item_id: uuid.UUID,
    ) -> bool:
        """Remove an offering from a service group."""
        await check_graphql_permission(info, "catalog:group:manage", str(tenant_id))

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        result = await service.remove_item(str(item_id))
        await db.commit()
        return result

    # ── Catalog Overlay Items ─────────────────────────────────────────

    @strawberry.mutation
    async def create_catalog_overlay_item(
        self, info: Info, tenant_id: uuid.UUID,
        pin_id: uuid.UUID, input: CatalogOverlayItemCreateInput,
    ) -> CatalogOverlayItemType:
        """Create a catalog overlay item on a tenant catalog pin."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.api.graphql.queries.service_catalog_queries import _overlay_item_to_gql
        from app.services.cmdb.overlay_service import OverlayService

        db = await _get_session(info)
        service = OverlayService(db)
        item = await service.create_catalog_overlay(str(tenant_id), str(pin_id), {
            "overlay_action": input.overlay_action,
            "base_item_id": str(input.base_item_id) if input.base_item_id else None,
            "service_offering_id": str(input.service_offering_id) if input.service_offering_id else None,
            "service_group_id": str(input.service_group_id) if input.service_group_id else None,
            "sort_order": input.sort_order,
        })
        await db.commit()
        return _overlay_item_to_gql(item)

    @strawberry.mutation
    async def delete_catalog_overlay_item(
        self, info: Info, tenant_id: uuid.UUID, item_id: uuid.UUID,
    ) -> bool:
        """Delete a catalog overlay item."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.overlay_service import OverlayService

        db = await _get_session(info)
        service = OverlayService(db)
        result = await service.delete_catalog_overlay(str(item_id), str(tenant_id))
        await db.commit()
        return result

    # ── Region Constraints ─────────────────────────────────────────────

    @strawberry.mutation
    async def set_catalog_region_constraints(
        self, info: Info, tenant_id: uuid.UUID,
        catalog_id: uuid.UUID, region_ids: list[uuid.UUID],
    ) -> list[str]:
        """Set region constraints for a service catalog."""
        await check_graphql_permission(info, "catalog:catalog:manage", str(tenant_id))

        from app.services.cmdb.region_constraint_service import RegionConstraintService

        db = await _get_session(info)
        service = RegionConstraintService(db)
        names = await service.set_catalog_regions(
            str(catalog_id), [str(r) for r in region_ids],
        )
        await db.commit()
        return names
