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
    PriceListItemType,
    PriceListSummaryType,
    PriceListType,
    ServiceOfferingListType,
    ServiceOfferingType,
    TenantPriceOverrideType,
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
        region_ids=region_ids,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _price_list_to_gql(pl) -> PriceListType:
    return PriceListType(
        id=pl.id,
        tenant_id=pl.tenant_id,
        name=pl.name,
        is_default=pl.is_default,
        effective_from=pl.effective_from,
        effective_to=pl.effective_to,
        items=[
            PriceListItemType(
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
            for item in (pl.items or [])
            if not getattr(item, "deleted_at", None)
        ],
        created_at=pl.created_at,
        updated_at=pl.updated_at,
    )


def _assoc_to_gql(a) -> CIClassActivityAssociationType:
    return CIClassActivityAssociationType(
        id=a.id,
        tenant_id=a.tenant_id,
        ci_class_id=a.ci_class_id,
        ci_class_name=a.ci_class.name if a.ci_class else "",
        ci_class_display_name=a.ci_class.display_name if a.ci_class else "",
        activity_template_id=a.activity_template_id,
        activity_template_name=a.activity_template.name if a.activity_template else "",
        relationship_type=a.relationship_type,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


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

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
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

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            return await service.list_distinct_categories(str(tenant_id))

    @strawberry.field
    async def price_lists(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> PriceListSummaryType:
        """List price lists."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            items, total = await service.list_price_lists(
                str(tenant_id), offset, limit
            )
            return PriceListSummaryType(
                items=[_price_list_to_gql(pl) for pl in items],
                total=total,
            )

    @strawberry.field
    async def effective_price(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        service_offering_id: uuid.UUID,
        delivery_region_id: uuid.UUID | None = None,
        coverage_model: str | None = None,
    ) -> EffectivePriceType | None:
        """Get the effective price for a tenant+service+region+coverage."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            price = await service.get_effective_price(
                str(tenant_id),
                str(service_offering_id),
                delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
                coverage_model=coverage_model,
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
            )

    @strawberry.field
    async def tenant_price_overrides(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[TenantPriceOverrideType]:
        """List tenant price overrides."""
        await check_graphql_permission(
            info, "cmdb:catalog:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.catalog_service import CatalogService

        async with async_session_factory() as db:
            service = CatalogService(db)
            overrides = await service.list_overrides(str(tenant_id))
            return [
                TenantPriceOverrideType(
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
                for o in overrides
            ]

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

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        async with async_session_factory() as db:
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
    async def relationship_type_suggestions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[str]:
        """List relationship type suggestions for CI class ↔ activity associations."""
        await check_graphql_permission(
            info, "cmdb:activity-association:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        async with async_session_factory() as db:
            service = CIClassActivityService(db)
            return await service.list_relationship_type_suggestions(str(tenant_id))
