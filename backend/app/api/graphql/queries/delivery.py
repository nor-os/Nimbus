"""
Overview: GraphQL queries for the service delivery engine — regions, acceptance, staff,
    rate cards, activities, estimations, price list templates, profitability.
Architecture: GraphQL query resolvers for service delivery operations (Section 8)
Dependencies: strawberry, app.services.cmdb.*
Concepts: Read queries for service delivery with permission checks and session factories.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.delivery import (
    ActivityDefinitionType,
    ActivityTemplateListType,
    ActivityTemplateType,
    DeliveryRegionListType,
    DeliveryRegionType,
    EffectiveRegionAcceptanceType,
    EstimationLineItemType,
    EstimationListType,
    InternalRateCardType,
    OrganizationalUnitType,
    PriceListTemplateItemType,
    PriceListTemplateListType,
    PriceListTemplateType,
    ProcessActivityLinkType,
    ProfitabilityByEntityType,
    ProfitabilityOverviewType,
    RegionAcceptanceTemplateRuleType,
    RegionAcceptanceTemplateType,
    ServiceProcessAssignmentType,
    ServiceProcessListType,
    ServiceProcessType,
    ServiceEstimationType,
    StaffProfileType,
    TenantRegionAcceptanceType,
)


# ── Helper converters ────────────────────────────────────────────────


def _region_to_gql(r) -> DeliveryRegionType:
    return DeliveryRegionType(
        id=r.id,
        tenant_id=r.tenant_id,
        parent_region_id=r.parent_region_id,
        name=r.name,
        display_name=r.display_name,
        code=r.code,
        timezone=r.timezone,
        country_code=r.country_code,
        is_system=r.is_system,
        is_active=r.is_active,
        sort_order=r.sort_order,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _acceptance_template_to_gql(t) -> RegionAcceptanceTemplateType:
    return RegionAcceptanceTemplateType(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        description=t.description,
        is_system=t.is_system,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _template_rule_to_gql(r) -> RegionAcceptanceTemplateRuleType:
    return RegionAcceptanceTemplateRuleType(
        id=r.id,
        template_id=r.template_id,
        delivery_region_id=r.delivery_region_id,
        acceptance_type=r.acceptance_type,
        reason=r.reason,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _tenant_acceptance_to_gql(a) -> TenantRegionAcceptanceType:
    return TenantRegionAcceptanceType(
        id=a.id,
        tenant_id=a.tenant_id,
        delivery_region_id=a.delivery_region_id,
        acceptance_type=a.acceptance_type,
        reason=a.reason,
        is_compliance_enforced=a.is_compliance_enforced,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _org_unit_to_gql(ou) -> OrganizationalUnitType:
    return OrganizationalUnitType(
        id=ou.id,
        tenant_id=ou.tenant_id,
        parent_id=ou.parent_id,
        name=ou.name,
        display_name=ou.display_name,
        cost_center=ou.cost_center,
        is_active=ou.is_active,
        sort_order=ou.sort_order,
        created_at=ou.created_at,
        updated_at=ou.updated_at,
    )


def _staff_profile_to_gql(p) -> StaffProfileType:
    return StaffProfileType(
        id=p.id,
        tenant_id=p.tenant_id,
        org_unit_id=p.org_unit_id,
        name=p.name,
        display_name=p.display_name,
        profile_id=p.profile_id,
        cost_center=p.cost_center,
        default_hourly_cost=p.default_hourly_cost,
        default_currency=p.default_currency,
        is_system=p.is_system,
        sort_order=p.sort_order,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _rate_card_to_gql(c) -> InternalRateCardType:
    return InternalRateCardType(
        id=c.id,
        tenant_id=c.tenant_id,
        staff_profile_id=c.staff_profile_id,
        delivery_region_id=c.delivery_region_id,
        hourly_cost=c.hourly_cost,
        hourly_sell_rate=c.hourly_sell_rate,
        currency=c.currency,
        effective_from=c.effective_from,
        effective_to=c.effective_to,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _activity_definition_to_gql(d) -> ActivityDefinitionType:
    return ActivityDefinitionType(
        id=d.id,
        template_id=d.template_id,
        name=d.name,
        staff_profile_id=d.staff_profile_id,
        estimated_hours=d.estimated_hours,
        sort_order=d.sort_order,
        is_optional=d.is_optional,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _activity_template_to_gql(t) -> ActivityTemplateType:
    return ActivityTemplateType(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        description=t.description,
        version=t.version,
        definitions=[
            _activity_definition_to_gql(d)
            for d in (t.definitions or [])
            if not getattr(d, "deleted_at", None)
        ],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _process_activity_link_to_gql(link) -> ProcessActivityLinkType:
    return ProcessActivityLinkType(
        id=link.id,
        process_id=link.process_id,
        activity_template_id=link.activity_template_id,
        sort_order=link.sort_order,
        is_required=link.is_required,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def _process_to_gql(p) -> ServiceProcessType:
    return ServiceProcessType(
        id=p.id,
        tenant_id=p.tenant_id,
        name=p.name,
        description=p.description,
        version=p.version,
        sort_order=p.sort_order,
        activity_links=[
            _process_activity_link_to_gql(link)
            for link in (p.activity_links or [])
            if not getattr(link, "deleted_at", None)
        ],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _assignment_to_gql(a) -> ServiceProcessAssignmentType:
    return ServiceProcessAssignmentType(
        id=a.id,
        tenant_id=a.tenant_id,
        service_offering_id=a.service_offering_id,
        process_id=a.process_id,
        coverage_model=a.coverage_model,
        is_default=a.is_default,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _line_item_to_gql(li) -> EstimationLineItemType:
    return EstimationLineItemType(
        id=li.id,
        estimation_id=li.estimation_id,
        activity_definition_id=li.activity_definition_id,
        rate_card_id=getattr(li, "rate_card_id", None),
        name=li.name,
        staff_profile_id=li.staff_profile_id,
        delivery_region_id=li.delivery_region_id,
        estimated_hours=li.estimated_hours,
        hourly_rate=li.hourly_rate,
        rate_currency=li.rate_currency,
        line_cost=li.line_cost,
        actual_hours=li.actual_hours,
        actual_cost=li.actual_cost,
        sort_order=li.sort_order,
        created_at=li.created_at,
        updated_at=li.updated_at,
    )


def _estimation_to_gql(e) -> ServiceEstimationType:
    return ServiceEstimationType(
        id=e.id,
        tenant_id=e.tenant_id,
        client_tenant_id=e.client_tenant_id,
        service_offering_id=e.service_offering_id,
        delivery_region_id=e.delivery_region_id,
        coverage_model=e.coverage_model,
        status=e.status,
        quantity=e.quantity,
        sell_price_per_unit=e.sell_price_per_unit,
        sell_currency=e.sell_currency,
        total_estimated_cost=e.total_estimated_cost,
        total_sell_price=e.total_sell_price,
        margin_amount=e.margin_amount,
        margin_percent=e.margin_percent,
        approved_by=e.approved_by,
        approved_at=e.approved_at,
        line_items=[
            _line_item_to_gql(li)
            for li in (e.line_items or [])
            if not getattr(li, "deleted_at", None)
        ],
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def _template_item_to_gql(ti) -> PriceListTemplateItemType:
    return PriceListTemplateItemType(
        id=ti.id,
        template_id=ti.template_id,
        service_offering_id=ti.service_offering_id,
        delivery_region_id=ti.delivery_region_id,
        coverage_model=ti.coverage_model,
        price_per_unit=ti.price_per_unit,
        currency=ti.currency,
        min_quantity=ti.min_quantity,
        max_quantity=ti.max_quantity,
        created_at=ti.created_at,
        updated_at=ti.updated_at,
    )


def _price_list_template_to_gql(t) -> PriceListTemplateType:
    return PriceListTemplateType(
        id=t.id,
        tenant_id=t.tenant_id,
        name=t.name,
        description=t.description,
        region_acceptance_template_id=t.region_acceptance_template_id,
        status=t.status,
        items=[
            _template_item_to_gql(ti)
            for ti in (t.items or [])
            if not getattr(ti, "deleted_at", None)
        ],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ── Query class ──────────────────────────────────────────────────────


@strawberry.type
class DeliveryQuery:
    # ── Delivery Regions ──────────────────────────────────────────────

    @strawberry.field
    async def delivery_regions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        parent_region_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> DeliveryRegionListType:
        """List delivery regions."""
        await check_graphql_permission(
            info, "catalog:region:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_service import DeliveryRegionService

        active_only = is_active if is_active is not None else True

        async with async_session_factory() as db:
            service = DeliveryRegionService(db)
            items, total = await service.list_regions(
                tenant_id=str(tenant_id),
                parent_region_id=str(parent_region_id) if parent_region_id else None,
                active_only=active_only,
                offset=offset,
                limit=limit,
            )
            return DeliveryRegionListType(
                items=[_region_to_gql(r) for r in items],
                total=total,
            )

    @strawberry.field
    async def delivery_region(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> DeliveryRegionType | None:
        """Get a delivery region by ID."""
        await check_graphql_permission(
            info, "catalog:region:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_service import DeliveryRegionService

        async with async_session_factory() as db:
            service = DeliveryRegionService(db)
            r = await service.get_region(str(id))
            return _region_to_gql(r) if r else None

    @strawberry.field
    async def region_children(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> list[DeliveryRegionType]:
        """Get child regions of a region."""
        await check_graphql_permission(
            info, "catalog:region:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_service import DeliveryRegionService

        async with async_session_factory() as db:
            service = DeliveryRegionService(db)
            children = await service.get_children(str(id))
            return [_region_to_gql(r) for r in children]

    # ── Region Acceptance ─────────────────────────────────────────────

    @strawberry.field
    async def region_acceptance_templates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[RegionAcceptanceTemplateType]:
        """List region acceptance templates."""
        await check_graphql_permission(
            info, "catalog:compliance:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        async with async_session_factory() as db:
            service = RegionAcceptanceService(db)
            templates = await service.list_templates(str(tenant_id))
            return [_acceptance_template_to_gql(t) for t in templates]

    @strawberry.field
    async def region_acceptance_template_rules(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> list[RegionAcceptanceTemplateRuleType]:
        """List rules for a region acceptance template."""
        await check_graphql_permission(
            info, "catalog:compliance:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        async with async_session_factory() as db:
            service = RegionAcceptanceService(db)
            rules = await service.list_template_rules(str(template_id))
            return [_template_rule_to_gql(r) for r in rules]

    @strawberry.field
    async def tenant_region_acceptances(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[TenantRegionAcceptanceType]:
        """List tenant region acceptances."""
        await check_graphql_permission(
            info, "catalog:compliance:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        async with async_session_factory() as db:
            service = RegionAcceptanceService(db)
            acceptances = await service.list_tenant_acceptances(str(tenant_id))
            return [_tenant_acceptance_to_gql(a) for a in acceptances]

    @strawberry.field
    async def effective_region_acceptance(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID,
    ) -> EffectiveRegionAcceptanceType:
        """Get the effective region acceptance for a tenant+region."""
        await check_graphql_permission(
            info, "catalog:compliance:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        async with async_session_factory() as db:
            service = RegionAcceptanceService(db)
            result = await service.get_effective_region_acceptance(
                str(tenant_id), str(region_id)
            )
            return EffectiveRegionAcceptanceType(
                acceptance_type=result["acceptance_type"],
                reason=result["reason"],
                is_compliance_enforced=result["is_compliance_enforced"],
                source=result["source"],
            )

    # ── Organizational Units ──────────────────────────────────────────

    @strawberry.field
    async def organizational_units(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[OrganizationalUnitType]:
        """List organizational units."""
        await check_graphql_permission(
            info, "catalog:orgunit:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.rate_card_service import RateCardService

        async with async_session_factory() as db:
            service = RateCardService(db)
            units = await service.list_org_units(str(tenant_id))
            return [_org_unit_to_gql(ou) for ou in units]

    # ── Staff Profiles ────────────────────────────────────────────────

    @strawberry.field
    async def staff_profiles(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[StaffProfileType]:
        """List staff profiles."""
        await check_graphql_permission(
            info, "catalog:staff:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.rate_card_service import RateCardService

        async with async_session_factory() as db:
            service = RateCardService(db)
            profiles = await service.list_profiles(str(tenant_id))
            return [_staff_profile_to_gql(p) for p in profiles]

    @strawberry.field
    async def staff_profile_activities(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        staff_profile_id: uuid.UUID,
    ) -> list[ActivityDefinitionType]:
        """List activity definitions associated with a staff profile."""
        await check_graphql_permission(
            info, "catalog:staff:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            defs = await service.list_definitions_by_staff_profile(
                str(staff_profile_id)
            )
            return [_activity_definition_to_gql(d) for d in defs]

    # ── Rate Cards ────────────────────────────────────────────────────

    @strawberry.field
    async def rate_cards(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        staff_profile_id: uuid.UUID | None = None,
        delivery_region_id: uuid.UUID | None = None,
    ) -> list[InternalRateCardType]:
        """List internal rate cards."""
        await check_graphql_permission(
            info, "catalog:staff:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.rate_card_service import RateCardService

        async with async_session_factory() as db:
            service = RateCardService(db)
            cards = await service.list_rate_cards(
                str(tenant_id),
                staff_profile_id=str(staff_profile_id) if staff_profile_id else None,
                delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
            )
            return [_rate_card_to_gql(c) for c in cards]

    # ── Activity Templates ────────────────────────────────────────────

    @strawberry.field
    async def activity_templates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> ActivityTemplateListType:
        """List activity templates."""
        await check_graphql_permission(
            info, "catalog:activity:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            items, total = await service.list_templates(
                str(tenant_id), offset=offset, limit=limit
            )
            return ActivityTemplateListType(
                items=[_activity_template_to_gql(t) for t in items],
                total=total,
            )

    @strawberry.field
    async def activity_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ActivityTemplateType | None:
        """Get an activity template by ID."""
        await check_graphql_permission(
            info, "catalog:activity:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            t = await service.get_template(str(id))
            return _activity_template_to_gql(t) if t else None

    # ── Service Processes ────────────────────────────────────────────

    @strawberry.field
    async def service_processes(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> ServiceProcessListType:
        """List service processes."""
        await check_graphql_permission(
            info, "catalog:process:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            items, total = await service.list_processes(
                str(tenant_id), offset=offset, limit=limit
            )
            return ServiceProcessListType(
                items=[_process_to_gql(p) for p in items],
                total=total,
            )

    @strawberry.field
    async def service_process(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ServiceProcessType | None:
        """Get a service process by ID."""
        await check_graphql_permission(
            info, "catalog:process:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            p = await service.get_process(str(id))
            return _process_to_gql(p) if p else None

    # ── Service Process Assignments ──────────────────────────────────

    @strawberry.field
    async def service_process_assignments(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        service_offering_id: uuid.UUID | None = None,
    ) -> list[ServiceProcessAssignmentType]:
        """List service-to-process assignments."""
        await check_graphql_permission(
            info, "catalog:process:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.activity_service import ActivityService

        async with async_session_factory() as db:
            service = ActivityService(db)
            assignments = await service.list_assignments(
                str(tenant_id),
                service_offering_id=str(service_offering_id) if service_offering_id else None,
            )
            return [_assignment_to_gql(a) for a in assignments]

    # ── Estimations ───────────────────────────────────────────────────

    @strawberry.field
    async def estimations(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        client_tenant_id: uuid.UUID | None = None,
        service_offering_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> EstimationListType:
        """List service estimations."""
        await check_graphql_permission(
            info, "catalog:estimation:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.estimation_service import EstimationService

        async with async_session_factory() as db:
            service = EstimationService(db)
            items, total = await service.list_estimations(
                str(tenant_id),
                client_tenant_id=str(client_tenant_id) if client_tenant_id else None,
                service_offering_id=str(service_offering_id) if service_offering_id else None,
                status=status,
                offset=offset,
                limit=limit,
            )
            return EstimationListType(
                items=[_estimation_to_gql(e) for e in items],
                total=total,
            )

    @strawberry.field
    async def estimation(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ServiceEstimationType | None:
        """Get an estimation by ID."""
        await check_graphql_permission(
            info, "catalog:estimation:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.estimation_service import EstimationService

        async with async_session_factory() as db:
            service = EstimationService(db)
            e = await service.get_estimation(str(id), str(tenant_id))
            return _estimation_to_gql(e) if e else None

    # ── Price List Templates ──────────────────────────────────────────

    @strawberry.field
    async def price_list_templates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PriceListTemplateListType:
        """List price list templates."""
        await check_graphql_permission(
            info, "catalog:estimation:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        async with async_session_factory() as db:
            service = PriceListTemplateService(db)
            items, total = await service.list_templates(
                str(tenant_id), status=status, offset=offset, limit=limit
            )
            return PriceListTemplateListType(
                items=[_price_list_template_to_gql(t) for t in items],
                total=total,
            )

    @strawberry.field
    async def price_list_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> PriceListTemplateType | None:
        """Get a price list template by ID."""
        await check_graphql_permission(
            info, "catalog:estimation:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        async with async_session_factory() as db:
            service = PriceListTemplateService(db)
            t = await service.get_template(str(id))
            return _price_list_template_to_gql(t) if t else None

    # ── Profitability ─────────────────────────────────────────────────

    @strawberry.field
    async def profitability_overview(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> ProfitabilityOverviewType:
        """Get profitability overview for a tenant."""
        await check_graphql_permission(
            info, "catalog:profitability:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.profitability_service import ProfitabilityService

        async with async_session_factory() as db:
            service = ProfitabilityService(db)
            result = await service.get_overview(str(tenant_id))
            return ProfitabilityOverviewType(
                total_revenue=result["total_revenue"],
                total_cost=result["total_cost"],
                total_margin=result["total_margin"],
                margin_percent=result["margin_percent"],
                estimation_count=result["estimation_count"],
            )

    @strawberry.field
    async def profitability_by_client(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[ProfitabilityByEntityType]:
        """Get profitability breakdown by client."""
        await check_graphql_permission(
            info, "catalog:profitability:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.profitability_service import ProfitabilityService

        async with async_session_factory() as db:
            service = ProfitabilityService(db)
            items = await service.get_by_client(str(tenant_id))
            return [
                ProfitabilityByEntityType(
                    entity_id=item["entity_id"],
                    entity_name=item["entity_name"],
                    total_revenue=item["total_revenue"],
                    total_cost=item["total_cost"],
                    margin_amount=item["margin_amount"],
                    margin_percent=item["margin_percent"],
                    estimation_count=item["estimation_count"],
                )
                for item in items
            ]

    @strawberry.field
    async def profitability_by_region(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[ProfitabilityByEntityType]:
        """Get profitability breakdown by delivery region."""
        await check_graphql_permission(
            info, "catalog:profitability:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.profitability_service import ProfitabilityService

        async with async_session_factory() as db:
            service = ProfitabilityService(db)
            items = await service.get_by_region(str(tenant_id))
            return [
                ProfitabilityByEntityType(
                    entity_id=item["entity_id"],
                    entity_name=item["entity_name"],
                    total_revenue=item["total_revenue"],
                    total_cost=item["total_cost"],
                    margin_amount=item["margin_amount"],
                    margin_percent=item["margin_percent"],
                    estimation_count=item["estimation_count"],
                )
                for item in items
            ]

    @strawberry.field
    async def resolve_effective_rate(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        staff_profile_id: uuid.UUID,
        delivery_region_id: uuid.UUID,
    ) -> InternalRateCardType | None:
        """Get the effective rate card for a staff profile + region."""
        await check_graphql_permission(
            info, "catalog:staff:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.rate_card_service import RateCardService

        async with async_session_factory() as db:
            service = RateCardService(db)
            card = await service.get_effective_rate(
                str(tenant_id), str(staff_profile_id), str(delivery_region_id)
            )
            return _rate_card_to_gql(card) if card else None

    @strawberry.field
    async def profitability_by_service(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[ProfitabilityByEntityType]:
        """Get profitability breakdown by service offering."""
        await check_graphql_permission(
            info, "catalog:profitability:read", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.cmdb.profitability_service import ProfitabilityService

        async with async_session_factory() as db:
            service = ProfitabilityService(db)
            items = await service.get_by_service(str(tenant_id))
            return [
                ProfitabilityByEntityType(
                    entity_id=item["entity_id"],
                    entity_name=item["entity_name"],
                    total_revenue=item["total_revenue"],
                    total_cost=item["total_cost"],
                    margin_amount=item["margin_amount"],
                    margin_percent=item["margin_percent"],
                    estimation_count=item["estimation_count"],
                )
                for item in items
            ]
