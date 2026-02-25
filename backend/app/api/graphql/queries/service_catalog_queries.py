"""
Overview: GraphQL queries for the service catalog redesign — versioned catalogs, provider SKUs,
    service groups, tenant catalog pins, catalog overlays, and offering cost breakdowns.
Architecture: GraphQL query resolvers for service catalog read operations (Section 8)
Dependencies: strawberry, app.services.cmdb.service_catalog_service, app.services.cmdb.sku_service,
    app.services.cmdb.service_group_service, app.services.cmdb.catalog_service
Concepts: Read queries for versioned service catalogs with permission checks.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.service_catalog_types import (
    CatalogDiffItemType,
    CatalogDiffType,
    CatalogOverlayItemType,
    OfferingCostBreakdownItemType,
    ProviderSkuListType,
    ProviderSkuType,
    ServiceCatalogItemType,
    ServiceCatalogListType,
    ServiceCatalogType,
    ServiceGroupItemType,
    ServiceGroupListType,
    ServiceGroupType,
    ServiceOfferingSkuType,
    TenantCatalogAssignmentType,
    TenantCatalogPinType,
)


# ── Helper converters ────────────────────────────────────────────────


def _catalog_to_gql(c) -> ServiceCatalogType:
    region_constraints = getattr(c, "region_constraints", None) or []
    return ServiceCatalogType(
        id=c.id,
        tenant_id=c.tenant_id,
        name=c.name,
        description=c.description,
        group_id=c.group_id,
        version_major=c.version_major,
        version_minor=c.version_minor,
        version_label=getattr(c, "version_label", f"v{c.version_major}.{c.version_minor}"),
        status=c.status,
        parent_version_id=c.parent_version_id,
        cloned_from_catalog_id=getattr(c, "cloned_from_catalog_id", None),
        region_constraint_ids=[rc.delivery_region_id for rc in region_constraints],
        items=[
            ServiceCatalogItemType(
                id=item.id,
                catalog_id=item.catalog_id,
                service_offering_id=item.service_offering_id,
                service_group_id=item.service_group_id,
                sort_order=item.sort_order,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in (c.items or [])
        ],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _sku_to_gql(s) -> ProviderSkuType:
    # Resolve semantic type name via relationship or attribute
    semantic_type_name = None
    sem_rel = getattr(s, "semantic_type_rel", None)
    if sem_rel:
        semantic_type_name = sem_rel.display_name or sem_rel.name
    return ProviderSkuType(
        id=s.id,
        provider_id=s.provider_id,
        external_sku_id=s.external_sku_id,
        name=s.name,
        display_name=s.display_name,
        description=s.description,
        ci_class_id=s.ci_class_id,
        measuring_unit=s.measuring_unit,
        category=s.category,
        unit_cost=s.unit_cost,
        cost_currency=s.cost_currency,
        attributes=s.attributes,
        is_active=s.is_active,
        semantic_type_id=getattr(s, "semantic_type_id", None),
        semantic_type_name=semantic_type_name,
        resource_type=getattr(s, "resource_type", None),
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _group_to_gql(g) -> ServiceGroupType:
    return ServiceGroupType(
        id=g.id,
        tenant_id=g.tenant_id,
        name=g.name,
        display_name=g.display_name,
        description=g.description,
        status=g.status,
        items=[
            ServiceGroupItemType(
                id=item.id,
                group_id=item.group_id,
                service_offering_id=item.service_offering_id,
                offering_name=getattr(item.offering, "name", None) if getattr(item, "offering", None) else None,
                is_required=item.is_required,
                sort_order=item.sort_order,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in (g.items or [])
            if not getattr(item, "deleted_at", None)
        ],
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


def _overlay_item_to_gql(o) -> CatalogOverlayItemType:
    return CatalogOverlayItemType(
        id=o.id,
        tenant_id=o.tenant_id,
        pin_id=o.pin_id,
        overlay_action=o.overlay_action,
        base_item_id=o.base_item_id,
        service_offering_id=o.service_offering_id,
        service_group_id=o.service_group_id,
        sort_order=o.sort_order,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _pin_to_gql(p) -> TenantCatalogPinType:
    cat = getattr(p, "catalog", None)
    overlay_items = getattr(p, "overlay_items", None) or []
    return TenantCatalogPinType(
        id=p.id,
        tenant_id=p.tenant_id,
        catalog_id=p.catalog_id,
        catalog=_catalog_to_gql(cat) if cat else None,
        overlay_items=[
            _overlay_item_to_gql(o) for o in overlay_items
            if not getattr(o, "deleted_at", None)
        ],
        effective_from=p.effective_from,
        effective_to=p.effective_to,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _diff_item_to_gql(item) -> CatalogDiffItemType:
    return CatalogDiffItemType(
        id=item.id,
        catalog_id=item.catalog_id,
        service_offering_id=item.service_offering_id,
        service_group_id=item.service_group_id,
        sort_order=item.sort_order,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# ── Queries ──────────────────────────────────────────────────────────


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ServiceCatalogQuery:
    @strawberry.field
    async def service_catalogs(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ServiceCatalogListType:
        """List service catalogs with optional status filter."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        items, total = await service.list_catalogs(
            str(tenant_id), status=status, offset=offset, limit=limit
        )
        return ServiceCatalogListType(
            items=[_catalog_to_gql(c) for c in items],
            total=total,
        )

    @strawberry.field
    async def service_catalog(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ServiceCatalogType | None:
        """Get a single service catalog by ID."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        c = await service.get_catalog(str(id))
        return _catalog_to_gql(c) if c else None

    @strawberry.field
    async def service_catalog_versions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> list[ServiceCatalogType]:
        """List all versions in a service catalog group."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        versions = await service.list_versions(str(group_id))
        return [_catalog_to_gql(c) for c in versions]

    @strawberry.field
    async def tenant_catalog_pins(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[TenantCatalogPinType]:
        """List active catalog pins for a tenant."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        pins = await service.get_pins(str(tenant_id))
        return [_pin_to_gql(p) for p in pins]

    @strawberry.field
    async def pinned_tenants_for_catalog(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        catalog_id: uuid.UUID,
    ) -> list[TenantCatalogPinType]:
        """List all tenant pins for a specific catalog (reverse lookup)."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        pins = await service.get_pinned_tenants_for_catalog(str(catalog_id))
        return [_pin_to_gql(p) for p in pins]

    @strawberry.field
    async def provider_skus(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_id: uuid.UUID | None = None,
        category: str | None = None,
        semantic_type_id: uuid.UUID | None = None,
        active_only: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ProviderSkuListType:
        """List provider SKUs with optional filters."""
        await check_graphql_permission(
            info, "catalog:sku:read", str(tenant_id)
        )

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        items, total = await service.list_skus(
            provider_id=str(provider_id) if provider_id else None,
            category=category,
            semantic_type_id=str(semantic_type_id) if semantic_type_id else None,
            active_only=active_only,
            offset=offset,
            limit=limit,
        )
        return ProviderSkuListType(
            items=[_sku_to_gql(s) for s in items],
            total=total,
        )

    @strawberry.field
    async def provider_sku(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ProviderSkuType | None:
        """Get a single provider SKU by ID."""
        await check_graphql_permission(
            info, "catalog:sku:read", str(tenant_id)
        )

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        s = await service.get_sku(str(id))
        return _sku_to_gql(s) if s else None

    @strawberry.field
    async def service_groups(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ServiceGroupListType:
        """List service groups for a tenant."""
        await check_graphql_permission(
            info, "catalog:group:read", str(tenant_id)
        )

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        items, total = await service.list_groups(
            str(tenant_id), status=status, offset=offset, limit=limit
        )
        return ServiceGroupListType(
            items=[_group_to_gql(g) for g in items],
            total=total,
        )

    @strawberry.field
    async def service_group(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ServiceGroupType | None:
        """Get a single service group by ID."""
        await check_graphql_permission(
            info, "catalog:group:read", str(tenant_id)
        )

        from app.services.cmdb.service_group_service import ServiceGroupService

        db = await _get_session(info)
        service = ServiceGroupService(db)
        g = await service.get_group(str(id), str(tenant_id))
        return _group_to_gql(g) if g else None

    @strawberry.field
    async def offering_cost_breakdown(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offering_id: uuid.UUID,
        delivery_region_id: uuid.UUID | None = None,
        coverage_model: str | None = None,
        price_list_id: uuid.UUID | None = None,
    ) -> list[OfferingCostBreakdownItemType]:
        """Get a cost breakdown for an offering (SKUs, activity definitions, base fee)."""
        await check_graphql_permission(
            info, "catalog:sku:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        rows = await service.get_offering_cost_breakdown(
            str(tenant_id),
            str(offering_id),
            delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
            coverage_model=coverage_model,
            price_list_id=str(price_list_id) if price_list_id else None,
        )
        return [
            OfferingCostBreakdownItemType(
                source_type=r["source_type"],
                source_id=r["source_id"],
                source_name=r["source_name"],
                quantity=r["quantity"],
                is_required=r["is_required"],
                price_per_unit=r["price_per_unit"],
                currency=r["currency"],
                measuring_unit=r["measuring_unit"],
                markup_percent=r.get("markup_percent"),
            )
            for r in rows
        ]

    @strawberry.field
    async def ci_count_for_offering(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offering_id: uuid.UUID,
    ) -> int:
        """Count CIs in a tenant matching an offering's linked CI classes."""
        await check_graphql_permission(
            info, "catalog:sku:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        return await service.get_ci_count_for_offering(
            str(tenant_id), str(offering_id)
        )

    @strawberry.field
    async def offering_skus(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        service_offering_id: uuid.UUID,
    ) -> list[ServiceOfferingSkuType]:
        """List provider SKU links for a service offering."""
        await check_graphql_permission(
            info, "catalog:sku:read", str(tenant_id)
        )

        from app.services.cmdb.sku_service import SkuService

        db = await _get_session(info)
        service = SkuService(db)
        links = await service.list_offering_skus(str(service_offering_id))
        return [
            ServiceOfferingSkuType(
                id=link.id,
                service_offering_id=link.service_offering_id,
                provider_sku_id=link.provider_sku_id,
                default_quantity=link.default_quantity,
                is_required=link.is_required,
                sort_order=link.sort_order,
                created_at=link.created_at,
                updated_at=link.updated_at,
            )
            for link in links
        ]

    @strawberry.field
    async def tenant_catalog_assignments(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        catalog_id: uuid.UUID,
    ) -> list[TenantCatalogAssignmentType]:
        """List all tenant assignments (pins + clones) for a catalog."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        rows = await service.get_tenant_assignments(str(catalog_id))
        return [
            TenantCatalogAssignmentType(
                tenant_id=uuid.UUID(r["tenant_id"]),
                assignment_type=r["assignment_type"],
                catalog_id=uuid.UUID(r["catalog_id"]),
                clone_catalog_id=uuid.UUID(r["clone_catalog_id"]) if r["clone_catalog_id"] else None,
                additions=r["additions"],
                deletions=r["deletions"],
                is_customized=r["is_customized"],
            )
            for r in rows
        ]

    @strawberry.field
    async def catalog_diff(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        source_catalog_id: uuid.UUID,
        clone_catalog_id: uuid.UUID,
    ) -> CatalogDiffType:
        """Compare items between a source catalog and its clone."""
        await check_graphql_permission(
            info, "catalog:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.service_catalog_service import ServiceCatalogService

        db = await _get_session(info)
        service = ServiceCatalogService(db)
        diff = await service.get_catalog_diff(
            str(source_catalog_id), str(clone_catalog_id)
        )
        return CatalogDiffType(
            source_catalog_id=uuid.UUID(diff["source_catalog_id"]),
            clone_catalog_id=uuid.UUID(diff["clone_catalog_id"]),
            additions=[_diff_item_to_gql(i) for i in diff["additions"]],
            deletions=[_diff_item_to_gql(i) for i in diff["deletions"]],
            common=[_diff_item_to_gql(i) for i in diff["common"]],
        )
