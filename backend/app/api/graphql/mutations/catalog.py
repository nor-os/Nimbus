"""
Overview: GraphQL mutations for the service catalog — CRUD for offerings, price lists, overrides,
    CI class links, and CI class ↔ activity associations.
Architecture: GraphQL mutation resolvers for catalog write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.catalog_service, app.services.cmdb.ci_class_activity_service
Concepts: Catalog mutations enforce permission checks and commit within session context.
"""

import uuid
from datetime import date

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.catalog import (
    _assoc_to_gql,
    _offering_to_gql,
    _pin_to_gql,
    _price_list_to_gql,
)
from app.api.graphql.types.catalog import (
    CIClassActivityAssociationCreateInput,
    CIClassActivityAssociationType,
    PinMinimumChargeCreateInput,
    PinMinimumChargeType,
    PinMinimumChargeUpdateInput,
    PriceListCreateInput,
    PriceListItemCreateInput,
    PriceListItemType,
    PriceListItemUpdateInput,
    PriceListOverlayItemCreateInput,
    PriceListOverlayItemType,
    PriceListOverlayItemUpdateInput,
    PriceListType,
    PriceListVersionInput,
    ServiceOfferingCreateInput,
    ServiceOfferingType,
    ServiceOfferingUpdateInput,
    TenantPriceListPinType,
)


def _overlay_item_to_gql(item) -> PriceListOverlayItemType:
    return PriceListOverlayItemType(
        id=item.id,
        tenant_id=item.tenant_id,
        pin_id=item.pin_id,
        overlay_action=item.overlay_action,
        base_item_id=item.base_item_id,
        service_offering_id=item.service_offering_id,
        provider_sku_id=item.provider_sku_id,
        activity_definition_id=item.activity_definition_id,
        delivery_region_id=item.delivery_region_id,
        coverage_model=item.coverage_model,
        price_per_unit=item.price_per_unit,
        currency=item.currency,
        markup_percent=item.markup_percent,
        discount_percent=getattr(item, "discount_percent", None),
        min_quantity=item.min_quantity,
        max_quantity=item.max_quantity,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _pin_minimum_to_gql(charge) -> PinMinimumChargeType:
    return PinMinimumChargeType(
        id=charge.id,
        tenant_id=charge.tenant_id,
        pin_id=charge.pin_id,
        category=charge.category,
        minimum_amount=charge.minimum_amount,
        currency=charge.currency,
        period=charge.period,
        effective_from=charge.effective_from,
        effective_to=charge.effective_to,
        created_at=charge.created_at,
        updated_at=charge.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        data = {
            "name": input.name,
            "description": input.description,
            "category": input.category,
            "measuring_unit": input.measuring_unit,
            "service_type": input.service_type,
            "operating_model": input.operating_model,
            "default_coverage_model": input.default_coverage_model,
            "minimum_amount": input.minimum_amount,
            "minimum_currency": input.minimum_currency,
            "minimum_period": input.minimum_period,
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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
        if input.minimum_amount is not strawberry.UNSET:
            data["minimum_amount"] = input.minimum_amount
        if input.minimum_currency is not strawberry.UNSET:
            data["minimum_currency"] = input.minimum_currency
        if input.minimum_period is not strawberry.UNSET:
            data["minimum_period"] = input.minimum_period

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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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

        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        db = await _get_session(info)
        service = CIClassActivityService(db)
        assoc = await service.create_association(str(tenant_id), {
            "ci_class_id": str(input.ci_class_id),
            "activity_template_id": str(input.activity_template_id),
            "relationship_type": input.relationship_type,
            "relationship_type_id": str(input.relationship_type_id) if input.relationship_type_id else None,
        })
        await db.commit()
        await db.refresh(assoc, ["ci_class", "activity_template"])
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

        from app.services.cmdb.ci_class_activity_service import CIClassActivityService

        db = await _get_session(info)
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        target_tenant = str(input.client_tenant_id) if input.client_tenant_id else str(tenant_id)
        data = {
            "name": input.name,
            "is_default": input.is_default,
            "delivery_region_id": str(input.delivery_region_id) if input.delivery_region_id else None,
        }
        pl = await service.create_price_list(target_tenant, data)
        await db.commit()
        await db.refresh(pl, ["items"])
        return _price_list_to_gql(pl)

    @strawberry.mutation
    async def delete_price_list(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        data = {
            "service_offering_id": input.service_offering_id,
            "price_per_unit": input.price_per_unit,
            "currency": input.currency,
            "delivery_region_id": input.delivery_region_id,
            "coverage_model": input.coverage_model,
            "min_quantity": input.min_quantity,
            "max_quantity": input.max_quantity,
            "provider_sku_id": getattr(input, "provider_sku_id", None),
            "activity_definition_id": getattr(input, "activity_definition_id", None),
            "markup_percent": getattr(input, "markup_percent", None),
        }
        item = await service.add_price_item(str(price_list_id), data)
        await db.commit()
        return PriceListItemType(
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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
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

    # ── Price List Overlay Items ──────────────────────────────────────

    @strawberry.mutation
    async def create_price_list_overlay_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        pin_id: uuid.UUID,
        input: PriceListOverlayItemCreateInput,
    ) -> PriceListOverlayItemType:
        """Create a price list overlay item on a pin."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.overlay_service import OverlayService

        db = await _get_session(info)
        service = OverlayService(db)
        item = await service.create_price_list_overlay(
            str(tenant_id), str(pin_id), {
                "overlay_action": input.overlay_action,
                "base_item_id": str(input.base_item_id) if input.base_item_id else None,
                "service_offering_id": str(input.service_offering_id) if input.service_offering_id else None,
                "provider_sku_id": str(input.provider_sku_id) if input.provider_sku_id else None,
                "activity_definition_id": str(input.activity_definition_id) if input.activity_definition_id else None,
                "delivery_region_id": str(input.delivery_region_id) if input.delivery_region_id else None,
                "coverage_model": input.coverage_model,
                "price_per_unit": input.price_per_unit,
                "currency": input.currency,
                "markup_percent": input.markup_percent,
                "discount_percent": input.discount_percent,
                "min_quantity": input.min_quantity,
                "max_quantity": input.max_quantity,
            },
        )
        await db.commit()
        return _overlay_item_to_gql(item)

    @strawberry.mutation
    async def update_price_list_overlay_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        item_id: uuid.UUID,
        input: PriceListOverlayItemUpdateInput,
    ) -> PriceListOverlayItemType:
        """Update a price list overlay item."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.overlay_service import OverlayService

        db = await _get_session(info)
        service = OverlayService(db)
        data: dict = {}
        if input.price_per_unit is not None:
            data["price_per_unit"] = input.price_per_unit
        if input.currency is not None:
            data["currency"] = input.currency
        if input.markup_percent is not strawberry.UNSET:
            data["markup_percent"] = input.markup_percent
        if input.discount_percent is not strawberry.UNSET:
            data["discount_percent"] = input.discount_percent
        if input.min_quantity is not strawberry.UNSET:
            data["min_quantity"] = input.min_quantity
        if input.max_quantity is not strawberry.UNSET:
            data["max_quantity"] = input.max_quantity
        if input.coverage_model is not strawberry.UNSET:
            data["coverage_model"] = input.coverage_model
        if input.delivery_region_id is not strawberry.UNSET:
            data["delivery_region_id"] = str(input.delivery_region_id) if input.delivery_region_id else None

        item = await service.update_price_list_overlay(str(item_id), str(tenant_id), data)
        await db.commit()
        return _overlay_item_to_gql(item)

    @strawberry.mutation
    async def delete_price_list_overlay_item(
        self, info: Info, tenant_id: uuid.UUID, item_id: uuid.UUID
    ) -> bool:
        """Delete a price list overlay item."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.overlay_service import OverlayService

        db = await _get_session(info)
        service = OverlayService(db)
        result = await service.delete_price_list_overlay(str(item_id), str(tenant_id))
        await db.commit()
        return result

    # ── Pin Minimum Charges ────────────────────────────────────────────

    @strawberry.mutation
    async def create_pin_minimum_charge(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        pin_id: uuid.UUID,
        input: PinMinimumChargeCreateInput,
    ) -> PinMinimumChargeType:
        """Create a minimum charge on a price list pin."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.pin_minimum_service import PinMinimumChargeService

        db = await _get_session(info)
        service = PinMinimumChargeService(db)
        charge = await service.create_minimum(str(tenant_id), str(pin_id), {
            "category": input.category,
            "minimum_amount": input.minimum_amount,
            "currency": input.currency,
            "period": input.period,
            "effective_from": input.effective_from,
            "effective_to": input.effective_to,
        })
        await db.commit()
        return _pin_minimum_to_gql(charge)

    @strawberry.mutation
    async def update_pin_minimum_charge(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        charge_id: uuid.UUID,
        input: PinMinimumChargeUpdateInput,
    ) -> PinMinimumChargeType:
        """Update a pin minimum charge."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.pin_minimum_service import PinMinimumChargeService

        db = await _get_session(info)
        service = PinMinimumChargeService(db)
        data: dict = {}
        if input.minimum_amount is not None:
            data["minimum_amount"] = input.minimum_amount
        if input.currency is not None:
            data["currency"] = input.currency
        if input.period is not None:
            data["period"] = input.period
        if input.effective_from is not None:
            data["effective_from"] = input.effective_from
        if input.effective_to is not strawberry.UNSET:
            data["effective_to"] = input.effective_to

        charge = await service.update_minimum(str(charge_id), str(tenant_id), data)
        await db.commit()
        return _pin_minimum_to_gql(charge)

    @strawberry.mutation
    async def delete_pin_minimum_charge(
        self, info: Info, tenant_id: uuid.UUID, charge_id: uuid.UUID
    ) -> bool:
        """Delete a pin minimum charge."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.pin_minimum_service import PinMinimumChargeService

        db = await _get_session(info)
        service = PinMinimumChargeService(db)
        result = await service.delete_minimum(str(charge_id), str(tenant_id))
        await db.commit()
        return result

    # ── Price List Region Constraints ─────────────────────────────────

    @strawberry.mutation
    async def set_price_list_region_constraints(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
        region_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Set region constraints for a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.region_constraint_service import RegionConstraintService

        db = await _get_session(info)
        service = RegionConstraintService(db)
        result = await service.set_price_list_regions(
            str(price_list_id), [str(r) for r in region_ids]
        )
        await db.commit()
        return [uuid.UUID(r) for r in result]

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

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pl = await service.copy_price_list(
            str(source_id),
            str(tenant_id),
            new_name,
            client_tenant_id=str(client_tenant_id) if client_tenant_id else None,
        )
        await db.commit()
        await db.refresh(pl, ["items"])
        return _price_list_to_gql(pl)

    # ── Price List Versioning ──────────────────────────────────────────

    @strawberry.mutation
    async def create_price_list_version(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: PriceListVersionInput,
    ) -> PriceListType:
        """Create a new version of a price list by cloning items and bumping version."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pl = await service.create_price_list_version(
            str(input.price_list_id), input.bump
        )
        await db.commit()
        await db.refresh(pl, ["items"])
        return _price_list_to_gql(pl)

    @strawberry.mutation
    async def publish_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
    ) -> PriceListType:
        """Publish a draft price list; archives the previous published version."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pl = await service.publish_price_list(str(price_list_id))
        await db.commit()
        await db.refresh(pl, ["items"])
        return _price_list_to_gql(pl)

    @strawberry.mutation
    async def archive_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
    ) -> PriceListType:
        """Archive a price list."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pl = await service.archive_price_list(str(price_list_id))
        await db.commit()
        await db.refresh(pl, ["items"])
        return _price_list_to_gql(pl)

    # ── Tenant Price List Pins ─────────────────────────────────────────

    @strawberry.mutation
    async def pin_tenant_to_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> TenantPriceListPinType:
        """Pin a tenant to a specific price list version for a date range."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        pin = await service.pin_tenant_to_price_list(
            str(tenant_id), str(price_list_id),
            effective_from=effective_from,
            effective_to=effective_to,
        )
        await db.commit()

        # Re-query with eager loading to avoid lazy-load greenlet errors
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.cmdb.price_list import (
            PriceList,
            TenantPriceListPin,
        )

        result = await db.execute(
            select(TenantPriceListPin)
            .where(TenantPriceListPin.id == pin.id)
            .options(
                selectinload(TenantPriceListPin.price_list).selectinload(PriceList.items),
                selectinload(TenantPriceListPin.price_list).selectinload(PriceList.region_constraints),
                selectinload(TenantPriceListPin.overlay_items),
                selectinload(TenantPriceListPin.minimum_charges),
            )
        )
        pin = result.scalar_one()
        return _pin_to_gql(pin)

    @strawberry.mutation
    async def unpin_tenant_from_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        price_list_id: uuid.UUID,
    ) -> bool:
        """Remove a tenant's pin from a price list version."""
        await check_graphql_permission(
            info, "cmdb:catalog:manage", str(tenant_id)
        )

        from app.services.cmdb.catalog_service import CatalogService

        db = await _get_session(info)
        service = CatalogService(db)
        result = await service.unpin_tenant_from_price_list(
            str(tenant_id), str(price_list_id)
        )
        await db.commit()
        return result
