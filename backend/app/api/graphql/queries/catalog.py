"""
Overview: GraphQL queries for the service catalog — offerings, price lists, effective pricing,
    categories, CI class activity associations.
Architecture: GraphQL query resolvers for service catalog (Section 8)
Dependencies: strawberry, app.services.cmdb.catalog_service, app.services.cmdb.ci_class_activity_service
Concepts: Read queries for service catalog with permission checks.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.catalog import (
    CIClassActivityAssociationType,
    EffectivePriceType,
    PinMinimumChargeType,
    PriceListDiffItemType,
    PriceListDiffType,
    PriceListItemType,
    PriceListOverlayItemType,
    PriceListSummaryType,
    PriceListType,
    ServiceOfferingListType,
    ServiceOfferingType,
    TenantPriceListAssignmentType,
    TenantPriceListPinType,
)


def _offering_to_gql(o) -> ServiceOfferingType:
    region_ids = [
        r.delivery_region_id
        for r in getattr(o, "regions", []) or []
    ]
    ci_class_ids = [
        link.ci_class_id
        for link in getattr(o, "ci_classes", []) or []
    ]
    return ServiceOfferingType(
        id=o.id,
        tenant_id=o.tenant_id,
        name=o.name,
        description=o.description,
        category=o.category,
        measuring_unit=o.measuring_unit,
        service_type=o.service_type,
        operating_model=o.operating_model,
        default_coverage_model=o.default_coverage_model,
        ci_class_ids=ci_class_ids,
        is_active=o.is_active,
        status=getattr(o, "status", "draft"),
        cloned_from_id=getattr(o, "cloned_from_id", None),
        base_fee=getattr(o, "base_fee", None),
        fee_period=getattr(o, "fee_period", None),
        minimum_amount=getattr(o, "minimum_amount", None),
        minimum_currency=getattr(o, "minimum_currency", None),
        minimum_period=getattr(o, "minimum_period", None),
        region_ids=region_ids,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _price_list_to_gql(pl) -> PriceListType:
    region_constraint_ids = [
        c.delivery_region_id
        for c in (getattr(pl, "region_constraints", None) or [])
    ]
    return PriceListType(
        id=pl.id,
        tenant_id=pl.tenant_id,
        name=pl.name,
        is_default=pl.is_default,
        group_id=getattr(pl, "group_id", None),
        version_major=getattr(pl, "version_major", 1),
        version_minor=getattr(pl, "version_minor", 0),
        version_label=getattr(pl, "version_label", "v1.0"),
        status=getattr(pl, "status", "published"),
        delivery_region_id=getattr(pl, "delivery_region_id", None),
        parent_version_id=getattr(pl, "parent_version_id", None),
        cloned_from_price_list_id=getattr(pl, "cloned_from_price_list_id", None),
        region_constraint_ids=region_constraint_ids,
        items=[
            PriceListItemType(
                id=item.id,
                price_list_id=item.price_list_id,
                service_offering_id=item.service_offering_id,
                provider_sku_id=getattr(item, "provider_sku_id", None),
                activity_definition_id=getattr(item, "activity_definition_id", None),
                markup_percent=getattr(item, "markup_percent", None),
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in (pl.items or [])
            if not getattr(item, "deleted_at", None)
        ],
        created_at=pl.created_at,
        updated_at=pl.updated_at,
    )


def _pin_to_gql(pin) -> TenantPriceListPinType:
    pl = getattr(pin, "price_list", None)
    overlay_items = [
        PriceListOverlayItemType(
            id=o.id, tenant_id=o.tenant_id, pin_id=o.pin_id,
            overlay_action=o.overlay_action, base_item_id=o.base_item_id,
            service_offering_id=o.service_offering_id,
            provider_sku_id=o.provider_sku_id,
            activity_definition_id=o.activity_definition_id,
            delivery_region_id=o.delivery_region_id,
            coverage_model=o.coverage_model,
            price_per_unit=o.price_per_unit, currency=o.currency,
            markup_percent=o.markup_percent,
            discount_percent=getattr(o, "discount_percent", None),
            min_quantity=o.min_quantity, max_quantity=o.max_quantity,
            created_at=o.created_at, updated_at=o.updated_at,
        )
        for o in (getattr(pin, "overlay_items", None) or [])
        if not getattr(o, "deleted_at", None)
    ]
    minimum_charges = [
        PinMinimumChargeType(
            id=m.id, tenant_id=m.tenant_id, pin_id=m.pin_id,
            category=m.category, minimum_amount=m.minimum_amount,
            currency=m.currency, period=m.period,
            effective_from=m.effective_from, effective_to=m.effective_to,
            created_at=m.created_at, updated_at=m.updated_at,
        )
        for m in (getattr(pin, "minimum_charges", None) or [])
        if not getattr(m, "deleted_at", None)
    ]
    return TenantPriceListPinType(
        id=pin.id,
        tenant_id=pin.tenant_id,
        price_list_id=pin.price_list_id,
        price_list=_price_list_to_gql(pl) if pl else None,
        overlay_items=overlay_items,
        minimum_charges=minimum_charges,
        effective_from=pin.effective_from,
        effective_to=pin.effective_to,
        created_at=pin.created_at,
        updated_at=pin.updated_at,
    )


def _assoc_to_gql(a) -> CIClassActivityAssociationType:
    rt_ref = getattr(a, "relationship_type_ref", None)
    return CIClassActivityAssociationType(
        id=a.id,
        tenant_id=a.tenant_id,
        ci_class_id=a.ci_class_id,
        ci_class_name=a.ci_class.name if a.ci_class else "",
        ci_class_display_name=a.ci_class.display_name if a.ci_class else "",
        activity_template_id=a.activity_template_id,
        activity_template_name=a.activity_template.name if a.activity_template else "",
        relationship_type=a.relationship_type,
        relationship_type_id=a.relationship_type_id,
        relationship_type_name=rt_ref.display_name if rt_ref else None,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class CatalogQuery:
    @strawberry.field
    async def service_offerings(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ServiceOfferingListType:
        """List service offerings."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        items, total = await service.list_offerings(
            str(tenant_id), category, offset=offset, limit=limit
        )
        return ServiceOfferingListType(
            items=[_offering_to_gql(o) for o in items],
            total=total,
        )

    @strawberry.field
    async def service_offering(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ServiceOfferingType | None:
        """Get a service offering."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        o = await service.get_offering(str(id), str(tenant_id))
        return _offering_to_gql(o) if o else None

    @strawberry.field
    async def service_offering_categories(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[str]:
        """List distinct service offering categories for the tenant."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        return await service.list_distinct_categories(str(tenant_id))

    @strawberry.field
    async def price_lists(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        delivery_region_id: uuid.UUID | None = None,
    ) -> PriceListSummaryType:
        """List price lists with optional status and region filters."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        items, total = await service.list_price_lists(
            str(tenant_id), offset, limit,
            status=status,
            delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
        )
        return PriceListSummaryType(
            items=[_price_list_to_gql(pl) for pl in items],
            total=total,
        )

    @strawberry.field
    async def price_list_versions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> list[PriceListType]:
        """List all versions in a price list group."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        versions = await service.list_price_list_versions(str(group_id))
        return [_price_list_to_gql(pl) for pl in versions]

    @strawberry.field
    async def tenant_price_list_pins(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[TenantPriceListPinType]:
        """List active price list pins for a tenant."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pins = await service.get_tenant_pins(str(tenant_id))
        return [_pin_to_gql(p) for p in pins]

    @strawberry.field
    async def effective_price(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        service_offering_id: uuid.UUID,
        delivery_region_id: uuid.UUID | None = None,
        coverage_model: str | None = None,
        price_list_id: uuid.UUID | None = None,
    ) -> EffectivePriceType | None:
        """Get the effective price for a tenant+service+region+coverage."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        price = await service.get_effective_price(
            str(tenant_id),
            str(service_offering_id),
            delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
            coverage_model=coverage_model,
            price_list_id=str(price_list_id) if price_list_id else None,
        )
        if not price:
            return None
        return EffectivePriceType(
            service_offering_id=price["service_offering_id"],
            service_name=price["service_name"],
            price_per_unit=price["price_per_unit"],
            currency=price["currency"],
            measuring_unit=price["measuring_unit"],
            has_override=price["has_override"],
            discount_percent=price["discount_percent"],
            delivery_region_id=price.get("delivery_region_id"),
            coverage_model=price.get("coverage_model"),
            compliance_status=price.get("compliance_status"),
            source_type=price.get("source_type"),
            markup_percent=price.get("markup_percent"),
            price_list_id=price.get("price_list_id"),
        )

    @strawberry.field
    async def pinned_tenants_for_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
    ) -> list[TenantPriceListPinType]:
        """List all tenant pins for a specific price list (reverse lookup)."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pins = await service.get_pinned_tenants(str(price_list_id))
        return [_pin_to_gql(p) for p in pins]

    @strawberry.field
    async def ci_class_activity_associations(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        ci_class_id: uuid.UUID | None = None,
        activity_template_id: uuid.UUID | None = None,
    ) -> list[CIClassActivityAssociationType]:
        """List CI class ↔ activity template associations."""
        await check_graphql_permission(
            info, "cmdb:activity-association:read", str(tenant_id)
        )

        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        db = await _get_session(info)
        service = CIClassActivityService(db)
        if ci_class_id:
            items = await service.list_for_ci_class(str(tenant_id), str(ci_class_id))
        elif activity_template_id:
            items = await service.list_for_activity_template(
                str(tenant_id), str(activity_template_id)
            )
        else:
            items = await service.list_for_ci_class(str(tenant_id), "")
        return [_assoc_to_gql(a) for a in items]

    @strawberry.field
    async def tenant_price_list_assignments(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
    ) -> list[TenantPriceListAssignmentType]:
        """List tenant assignments (pins + clones) for a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        assignments = await service.get_price_list_tenant_assignments(
            str(price_list_id)
        )
        return [
            TenantPriceListAssignmentType(
                tenant_id=uuid.UUID(a["tenant_id"]),
                assignment_type=a["assignment_type"],
                price_list_id=uuid.UUID(a["price_list_id"]),
                clone_price_list_id=uuid.UUID(a["clone_price_list_id"])
                if a["clone_price_list_id"]
                else None,
                additions=a["additions"],
                deletions=a["deletions"],
                is_customized=a["is_customized"],
            )
            for a in assignments
        ]

    @strawberry.field
    async def price_list_diff(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        source_price_list_id: uuid.UUID,
        clone_price_list_id: uuid.UUID,
    ) -> PriceListDiffType:
        """Compare items between a source and clone price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        diff = await service.get_price_list_diff(
            str(source_price_list_id), str(clone_price_list_id)
        )

        def _to_diff_item(item) -> PriceListDiffItemType:
            return PriceListDiffItemType(
                id=item.id,
                price_list_id=item.price_list_id,
                service_offering_id=item.service_offering_id,
                provider_sku_id=getattr(item, "provider_sku_id", None),
                activity_definition_id=getattr(item, "activity_definition_id", None),
                delivery_region_id=item.delivery_region_id,
                coverage_model=item.coverage_model,
                price_per_unit=item.price_per_unit,
                markup_percent=getattr(item, "markup_percent", None),
                currency=item.currency,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )

        return PriceListDiffType(
            source_price_list_id=uuid.UUID(diff["source_price_list_id"]),
            clone_price_list_id=uuid.UUID(diff["clone_price_list_id"]),
            additions=[_to_diff_item(i) for i in diff["additions"]],
            deletions=[_to_diff_item(i) for i in diff["deletions"]],
            common=[_to_diff_item(i) for i in diff["common"]],
        )

    @strawberry.field
    async def relationship_type_suggestions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[str]:
        """List relationship type suggestions for CI class ↔ activity associations."""
        await check_graphql_permission(
            info, "cmdb:activity-association:read", str(tenant_id)
        )

        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        db = await _get_session(info)
        service = CIClassActivityService(db)
        return await service.list_relationship_type_suggestions(str(tenant_id))
