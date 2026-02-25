"""
Overview: GraphQL mutations for the service delivery engine — CRUD for regions, acceptance,
    staff profiles, rate cards, activities, estimations, price list templates.
Architecture: GraphQL mutation resolvers for delivery write operations (Section 8)
Dependencies: strawberry, app.services.cmdb.*
Concepts: Delivery mutations enforce permission checks and commit within session context.
"""

import uuid


import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.catalog import _price_list_to_gql
from app.api.graphql.queries.delivery import (
    _acceptance_template_to_gql,
    _activity_definition_to_gql,
    _activity_template_to_gql,
    _assignment_to_gql,
    _estimation_to_gql,
    _line_item_to_gql,
    _org_unit_to_gql,
    _price_list_template_to_gql,
    _process_activity_link_to_gql,
    _process_to_gql,
    _rate_card_to_gql,
    _region_to_gql,
    _staff_profile_to_gql,
    _template_rule_to_gql,
    _tenant_acceptance_to_gql,
)
from app.api.graphql.types.catalog import PriceListType
from app.api.graphql.types.delivery import (
    ActivityDefinitionCreateInput,
    ActivityDefinitionType,
    ActivityDefinitionUpdateInput,
    ActivityTemplateCreateInput,
    ActivityTemplateType,
    DeliveryRegionCreateInput,
    DeliveryRegionType,
    DeliveryRegionUpdateInput,
    EstimationLineItemCreateInput,
    EstimationLineItemType,
    InternalRateCardCreateInput,
    InternalRateCardType,
    InternalRateCardUpdateInput,
    OrganizationalUnitCreateInput,
    OrganizationalUnitType,
    OrganizationalUnitUpdateInput,
    PriceListTemplateCreateInput,
    PriceListTemplateItemCreateInput,
    PriceListTemplateItemType,
    PriceListTemplateType,
    ProcessActivityLinkCreateInput,
    ProcessActivityLinkType,
    RegionAcceptanceTemplateCreateInput,
    RegionAcceptanceTemplateRuleCreateInput,
    RegionAcceptanceTemplateRuleType,
    RegionAcceptanceTemplateType,
    ServiceProcessAssignmentCreateInput,
    ServiceProcessAssignmentType,
    ServiceProcessCreateInput,
    ServiceProcessType,
    ServiceProcessUpdateInput,
    ServiceEstimationCreateInput,
    ServiceEstimationType,
    ServiceEstimationUpdateInput,
    StaffProfileCreateInput,
    StaffProfileType,
    StaffProfileUpdateInput,
    TenantRegionAcceptanceCreateInput,
    TenantRegionAcceptanceType,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class DeliveryMutation:
    # ── Delivery Regions ──────────────────────────────────────────────

    @strawberry.mutation
    async def create_delivery_region(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: DeliveryRegionCreateInput,
    ) -> DeliveryRegionType:
        """Create a delivery region."""
        await check_graphql_permission(
            info, "catalog:region:manage", str(tenant_id)
        )

        from app.services.cmdb.region_service import DeliveryRegionService

        db = await _get_session(info)
        service = DeliveryRegionService(db)
        data = {
            "name": input.name,
            "display_name": input.display_name,
            "code": input.code,
            "parent_region_id": input.parent_region_id,
            "timezone": input.timezone,
            "country_code": input.country_code,
            "is_system": input.is_system,
            "sort_order": input.sort_order,
        }
        r = await service.create_region(str(tenant_id), data)
        await db.commit()
        return _region_to_gql(r)

    @strawberry.mutation
    async def update_delivery_region(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: DeliveryRegionUpdateInput,
    ) -> DeliveryRegionType:
        """Update a delivery region."""
        await check_graphql_permission(
            info, "catalog:region:manage", str(tenant_id)
        )

        from app.services.cmdb.region_service import DeliveryRegionService

        db = await _get_session(info)
        service = DeliveryRegionService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.timezone is not strawberry.UNSET:
            data["timezone"] = input.timezone
        if input.country_code is not strawberry.UNSET:
            data["country_code"] = input.country_code
        if input.is_active is not None:
            data["is_active"] = input.is_active
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        r = await service.update_region(str(id), data)
        await db.commit()
        return _region_to_gql(r)

    @strawberry.mutation
    async def delete_delivery_region(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a delivery region."""
        await check_graphql_permission(
            info, "catalog:region:manage", str(tenant_id)
        )

        from app.services.cmdb.region_service import DeliveryRegionService

        db = await _get_session(info)
        service = DeliveryRegionService(db)
        result = await service.delete_region(str(id))
        await db.commit()
        return result

    # ── Region Acceptance Templates ───────────────────────────────────

    @strawberry.mutation
    async def create_region_acceptance_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: RegionAcceptanceTemplateCreateInput,
    ) -> RegionAcceptanceTemplateType:
        """Create a region acceptance template."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        data = {
            "name": input.name,
            "description": input.description,
            "is_system": input.is_system,
        }
        t = await service.create_template(str(tenant_id), data)
        await db.commit()
        return _acceptance_template_to_gql(t)

    @strawberry.mutation
    async def delete_region_acceptance_template(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a region acceptance template."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        result = await service.delete_template(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def add_template_rule(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        input: RegionAcceptanceTemplateRuleCreateInput,
    ) -> RegionAcceptanceTemplateRuleType:
        """Add a rule to a region acceptance template."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        data = {
            "delivery_region_id": input.delivery_region_id,
            "acceptance_type": input.acceptance_type,
            "reason": input.reason,
        }
        rule = await service.add_template_rule(str(template_id), data)
        await db.commit()
        return _template_rule_to_gql(rule)

    @strawberry.mutation
    async def delete_template_rule(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a template rule."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        result = await service.delete_template_rule(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def set_tenant_region_acceptance(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: TenantRegionAcceptanceCreateInput,
    ) -> TenantRegionAcceptanceType:
        """Set a direct tenant region acceptance."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        data = {
            "delivery_region_id": input.delivery_region_id,
            "acceptance_type": input.acceptance_type,
            "reason": input.reason,
            "is_compliance_enforced": input.is_compliance_enforced,
        }
        a = await service.set_tenant_acceptance(str(tenant_id), data)
        await db.commit()
        return _tenant_acceptance_to_gql(a)

    @strawberry.mutation
    async def delete_tenant_region_acceptance(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a tenant region acceptance."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        result = await service.delete_tenant_acceptance(str(id), str(tenant_id))
        await db.commit()
        return result

    @strawberry.mutation
    async def assign_template_to_tenant(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> bool:
        """Assign a region acceptance template to a tenant."""
        await check_graphql_permission(
            info, "catalog:compliance:manage", str(tenant_id)
        )

        from app.services.cmdb.region_acceptance_service import RegionAcceptanceService

        db = await _get_session(info)
        service = RegionAcceptanceService(db)
        await service.assign_template_to_tenant(str(tenant_id), str(template_id))
        await db.commit()
        return True

    # ── Organizational Units ──────────────────────────────────────────

    @strawberry.mutation
    async def create_organizational_unit(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: OrganizationalUnitCreateInput,
    ) -> OrganizationalUnitType:
        """Create an organizational unit."""
        await check_graphql_permission(
            info, "catalog:orgunit:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data = {
            "parent_id": input.parent_id,
            "name": input.name,
            "display_name": input.display_name,
            "cost_center": input.cost_center,
            "sort_order": input.sort_order,
        }
        ou = await service.create_org_unit(str(tenant_id), data)
        await db.commit()
        return _org_unit_to_gql(ou)

    @strawberry.mutation
    async def update_organizational_unit(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: OrganizationalUnitUpdateInput,
    ) -> OrganizationalUnitType:
        """Update an organizational unit."""
        await check_graphql_permission(
            info, "catalog:orgunit:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.cost_center is not strawberry.UNSET:
            data["cost_center"] = input.cost_center
        if input.is_active is not None:
            data["is_active"] = input.is_active
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        ou = await service.update_org_unit(str(id), data)
        await db.commit()
        return _org_unit_to_gql(ou)

    @strawberry.mutation
    async def delete_organizational_unit(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an organizational unit."""
        await check_graphql_permission(
            info, "catalog:orgunit:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        result = await service.delete_org_unit(str(id))
        await db.commit()
        return result

    # ── Staff Profiles ────────────────────────────────────────────────

    @strawberry.mutation
    async def create_staff_profile(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: StaffProfileCreateInput,
    ) -> StaffProfileType:
        """Create a staff profile."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data = {
            "name": input.name,
            "display_name": input.display_name,
            "org_unit_id": input.org_unit_id,
            "profile_id": input.profile_id,
            "cost_center": input.cost_center,
            "default_hourly_cost": input.default_hourly_cost,
            "default_currency": input.default_currency,
            "is_system": input.is_system,
            "sort_order": input.sort_order,
        }
        p = await service.create_profile(str(tenant_id), data)
        await db.commit()
        return _staff_profile_to_gql(p)

    @strawberry.mutation
    async def update_staff_profile(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: StaffProfileUpdateInput,
    ) -> StaffProfileType:
        """Update a staff profile."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data: dict = {}
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.org_unit_id is not strawberry.UNSET:
            data["org_unit_id"] = input.org_unit_id
        if input.profile_id is not strawberry.UNSET:
            data["profile_id"] = input.profile_id
        if input.cost_center is not strawberry.UNSET:
            data["cost_center"] = input.cost_center
        if input.default_hourly_cost is not strawberry.UNSET:
            data["default_hourly_cost"] = input.default_hourly_cost
        if input.default_currency is not strawberry.UNSET:
            data["default_currency"] = input.default_currency
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        p = await service.update_profile(str(id), data)
        await db.commit()
        return _staff_profile_to_gql(p)

    @strawberry.mutation
    async def delete_staff_profile(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a staff profile."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        result = await service.delete_profile(str(id))
        await db.commit()
        return result

    # ── Rate Cards ────────────────────────────────────────────────────

    @strawberry.mutation
    async def create_rate_card(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: InternalRateCardCreateInput,
    ) -> InternalRateCardType:
        """Create an internal rate card."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data = {
            "staff_profile_id": input.staff_profile_id,
            "delivery_region_id": input.delivery_region_id,
            "hourly_cost": input.hourly_cost,
            "hourly_sell_rate": input.hourly_sell_rate,
            "currency": input.currency,
            "effective_from": input.effective_from,
            "effective_to": input.effective_to,
        }
        c = await service.create_rate_card(str(tenant_id), data)
        await db.commit()
        return _rate_card_to_gql(c)

    @strawberry.mutation
    async def update_rate_card(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: InternalRateCardUpdateInput,
    ) -> InternalRateCardType:
        """Update an internal rate card."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        data: dict = {}
        if input.hourly_cost is not None:
            data["hourly_cost"] = input.hourly_cost
        if input.hourly_sell_rate is not strawberry.UNSET:
            data["hourly_sell_rate"] = input.hourly_sell_rate
        if input.currency is not None:
            data["currency"] = input.currency
        if input.effective_from is not None:
            data["effective_from"] = input.effective_from
        if input.effective_to is not strawberry.UNSET:
            data["effective_to"] = input.effective_to

        c = await service.update_rate_card(str(id), data)
        await db.commit()
        return _rate_card_to_gql(c)

    @strawberry.mutation
    async def delete_rate_card(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an internal rate card."""
        await check_graphql_permission(
            info, "catalog:staff:manage", str(tenant_id)
        )

        from app.services.cmdb.rate_card_service import RateCardService

        db = await _get_session(info)
        service = RateCardService(db)
        result = await service.delete_rate_card(str(id))
        await db.commit()
        return result

    # ── Activity Templates ────────────────────────────────────────────

    @strawberry.mutation
    async def create_activity_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ActivityTemplateCreateInput,
    ) -> ActivityTemplateType:
        """Create an activity template."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data = {
            "name": input.name,
            "description": input.description,
        }
        t = await service.create_template(str(tenant_id), data)
        await db.commit()
        return _activity_template_to_gql(t)

    @strawberry.mutation
    async def update_activity_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ActivityTemplateCreateInput,
    ) -> ActivityTemplateType:
        """Update an activity template."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.description is not None:
            data["description"] = input.description

        t = await service.update_template(str(id), data)
        await db.commit()
        return _activity_template_to_gql(t)

    @strawberry.mutation
    async def delete_activity_template(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an activity template."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        result = await service.delete_template(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def clone_activity_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        new_name: str,
    ) -> ActivityTemplateType:
        """Clone an activity template."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        t = await service.clone_template(str(id), str(tenant_id), new_name)
        await db.commit()
        return _activity_template_to_gql(t)

    # ── Activity Definitions ──────────────────────────────────────────

    @strawberry.mutation
    async def add_activity_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        input: ActivityDefinitionCreateInput,
    ) -> ActivityDefinitionType:
        """Add a definition to an activity template."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data = {
            "name": input.name,
            "staff_profile_id": input.staff_profile_id,
            "estimated_hours": input.estimated_hours,
            "sort_order": input.sort_order,
            "is_optional": input.is_optional,
        }
        d = await service.add_definition(str(template_id), data)
        await db.commit()
        return _activity_definition_to_gql(d)

    @strawberry.mutation
    async def update_activity_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ActivityDefinitionUpdateInput,
    ) -> ActivityDefinitionType:
        """Update an activity definition."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.staff_profile_id is not None:
            data["staff_profile_id"] = input.staff_profile_id
        if input.estimated_hours is not None:
            data["estimated_hours"] = input.estimated_hours
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order
        if input.is_optional is not None:
            data["is_optional"] = input.is_optional

        d = await service.update_definition(str(id), data)
        await db.commit()
        return _activity_definition_to_gql(d)

    @strawberry.mutation
    async def delete_activity_definition(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an activity definition."""
        await check_graphql_permission(
            info, "catalog:activity:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        result = await service.delete_definition(str(id))
        await db.commit()
        return result

    # ── Service Processes ──────────────────────────────────────────────

    @strawberry.mutation
    async def create_service_process(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ServiceProcessCreateInput,
    ) -> ServiceProcessType:
        """Create a service process."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data = {
            "name": input.name,
            "description": input.description,
            "sort_order": input.sort_order,
        }
        p = await service.create_process(str(tenant_id), data)
        await db.commit()
        return _process_to_gql(p)

    @strawberry.mutation
    async def update_service_process(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ServiceProcessUpdateInput,
    ) -> ServiceProcessType:
        """Update a service process."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data: dict = {}
        if input.name is not None:
            data["name"] = input.name
        if input.description is not strawberry.UNSET:
            data["description"] = input.description
        if input.sort_order is not None:
            data["sort_order"] = input.sort_order

        p = await service.update_process(str(id), data)
        await db.commit()
        return _process_to_gql(p)

    @strawberry.mutation
    async def delete_service_process(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a service process."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        result = await service.delete_process(str(id))
        await db.commit()
        return result

    # ── Process Activity Links ─────────────────────────────────────────

    @strawberry.mutation
    async def add_process_activity_link(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        process_id: uuid.UUID,
        input: ProcessActivityLinkCreateInput,
    ) -> ProcessActivityLinkType:
        """Add an activity template to a process."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data = {
            "activity_template_id": input.activity_template_id,
            "sort_order": input.sort_order,
            "is_required": input.is_required,
        }
        link = await service.add_activity_to_process(str(process_id), data)
        await db.commit()
        return _process_activity_link_to_gql(link)

    @strawberry.mutation
    async def remove_process_activity_link(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Remove an activity template from a process."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        result = await service.remove_activity_from_process(str(id))
        await db.commit()
        return result

    # ── Service Process Assignments ────────────────────────────────────

    @strawberry.mutation
    async def create_service_process_assignment(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ServiceProcessAssignmentCreateInput,
    ) -> ServiceProcessAssignmentType:
        """Create a service-to-process assignment."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        data = {
            "service_offering_id": input.service_offering_id,
            "process_id": input.process_id,
            "coverage_model": input.coverage_model,
            "is_default": input.is_default,
        }
        a = await service.create_assignment(str(tenant_id), data)
        await db.commit()
        return _assignment_to_gql(a)

    @strawberry.mutation
    async def delete_service_process_assignment(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a service-to-process assignment."""
        await check_graphql_permission(
            info, "catalog:process:manage", str(tenant_id)
        )

        from app.services.cmdb.activity_service import ActivityService

        db = await _get_session(info)
        service = ActivityService(db)
        result = await service.delete_assignment(str(id))
        await db.commit()
        return result

    # ── Estimations ───────────────────────────────────────────────────

    @strawberry.mutation
    async def create_estimation(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: ServiceEstimationCreateInput,
    ) -> ServiceEstimationType:
        """Create a service estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        data = {
            "client_tenant_id": input.client_tenant_id,
            "service_offering_id": input.service_offering_id,
            "delivery_region_id": input.delivery_region_id,
            "coverage_model": input.coverage_model,
            "price_list_id": input.price_list_id,
            "quantity": input.quantity,
            "sell_price_per_unit": input.sell_price_per_unit,
            "sell_currency": input.sell_currency,
        }
        e = await service.create_estimation(str(tenant_id), data)
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def update_estimation(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: ServiceEstimationUpdateInput,
    ) -> ServiceEstimationType:
        """Update a service estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        data: dict = {}
        if input.quantity is not None:
            data["quantity"] = input.quantity
        if input.sell_price_per_unit is not None:
            data["sell_price_per_unit"] = input.sell_price_per_unit
        if input.sell_currency is not None:
            data["sell_currency"] = input.sell_currency
        if input.delivery_region_id is not strawberry.UNSET:
            data["delivery_region_id"] = input.delivery_region_id
        if input.coverage_model is not strawberry.UNSET:
            data["coverage_model"] = input.coverage_model
        if input.price_list_id is not strawberry.UNSET:
            data["price_list_id"] = input.price_list_id

        e = await service.update_estimation(str(id), str(tenant_id), data)
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def add_estimation_line_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        estimation_id: uuid.UUID,
        input: EstimationLineItemCreateInput,
    ) -> EstimationLineItemType:
        """Add a line item to an estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        data = {
            "name": input.name,
            "staff_profile_id": input.staff_profile_id,
            "delivery_region_id": input.delivery_region_id,
            "estimated_hours": input.estimated_hours,
            "hourly_rate": input.hourly_rate,
            "activity_definition_id": input.activity_definition_id,
            "rate_card_id": input.rate_card_id,
            "rate_currency": input.rate_currency,
            "sort_order": input.sort_order,
        }
        item = await service.add_line_item(
            str(estimation_id), str(tenant_id), data
        )
        await db.commit()
        return _line_item_to_gql(item)

    @strawberry.mutation
    async def update_estimation_line_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        estimated_hours: float | None = None,
        hourly_rate: float | None = None,
        name: str | None = None,
    ) -> EstimationLineItemType:
        """Update an estimation line item."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        data: dict = {}
        if estimated_hours is not None:
            data["estimated_hours"] = estimated_hours
        if hourly_rate is not None:
            data["hourly_rate"] = hourly_rate
        if name is not None:
            data["name"] = name

        item = await service.update_line_item(str(id), data)
        await db.commit()
        return _line_item_to_gql(item)

    @strawberry.mutation
    async def delete_estimation_line_item(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete an estimation line item."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        result = await service.delete_line_item(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def submit_estimation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> ServiceEstimationType:
        """Submit an estimation for approval."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.submit_estimation(str(id), str(tenant_id))
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def approve_estimation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> ServiceEstimationType:
        """Approve a submitted estimation."""
        user_id = await check_graphql_permission(
            info, "catalog:estimation:approve", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.approve_estimation(
            str(id), str(tenant_id), user_id
        )
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def reject_estimation(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> ServiceEstimationType:
        """Reject a submitted estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:approve", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.reject_estimation(str(id), str(tenant_id))
        await db.commit()
        return _estimation_to_gql(e)

    # ── Import Process / Refresh Rates ─────────────────────────────────

    @strawberry.mutation
    async def import_process_to_estimation(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        estimation_id: uuid.UUID,
        process_id: uuid.UUID,
        delivery_region_id: uuid.UUID | None = None,
    ) -> ServiceEstimationType:
        """Import line items from a process into a draft estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.import_process_to_estimation(
            str(estimation_id),
            str(tenant_id),
            str(process_id),
            delivery_region_id=str(delivery_region_id) if delivery_region_id else None,
        )
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def refresh_estimation_rates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        estimation_id: uuid.UUID,
    ) -> ServiceEstimationType:
        """Re-resolve rate cards for all line items in a draft estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.refresh_estimation_rates(
            str(estimation_id), str(tenant_id)
        )
        await db.commit()
        return _estimation_to_gql(e)

    @strawberry.mutation
    async def refresh_estimation_prices(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        estimation_id: uuid.UUID,
    ) -> ServiceEstimationType:
        """Re-resolve sell price from the pricing engine for a draft estimation."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.estimation_service import EstimationService

        db = await _get_session(info)
        service = EstimationService(db)
        e = await service.refresh_estimation_prices(
            str(estimation_id), str(tenant_id)
        )
        await db.commit()
        return _estimation_to_gql(e)

    # ── Price List Templates ──────────────────────────────────────────

    @strawberry.mutation
    async def create_price_list_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: PriceListTemplateCreateInput,
    ) -> PriceListTemplateType:
        """Create a price list template."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        data = {
            "name": input.name,
            "description": input.description,
            "region_acceptance_template_id": input.region_acceptance_template_id,
            "status": input.status,
        }
        t = await service.create_template(str(tenant_id), data)
        await db.commit()
        return _price_list_template_to_gql(t)

    @strawberry.mutation
    async def update_price_list_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> PriceListTemplateType:
        """Update a price list template."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        data: dict = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status

        t = await service.update_template(str(id), data)
        await db.commit()
        return _price_list_template_to_gql(t)

    @strawberry.mutation
    async def delete_price_list_template(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a price list template."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        result = await service.delete_template(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def add_price_list_template_item(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        input: PriceListTemplateItemCreateInput,
    ) -> PriceListTemplateItemType:
        """Add an item to a price list template."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        data = {
            "service_offering_id": input.service_offering_id,
            "price_per_unit": input.price_per_unit,
            "delivery_region_id": input.delivery_region_id,
            "coverage_model": input.coverage_model,
            "currency": input.currency,
            "min_quantity": input.min_quantity,
            "max_quantity": input.max_quantity,
        }
        item = await service.add_template_item(str(template_id), data)
        await db.commit()
        from app.api.graphql.queries.delivery import _template_item_to_gql
        return _template_item_to_gql(item)

    @strawberry.mutation
    async def delete_price_list_template_item(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Delete a price list template item."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        result = await service.delete_template_item(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def clone_template_to_price_list(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> PriceListType:
        """Clone a price list template into a real price list."""
        await check_graphql_permission(
            info, "catalog:estimation:manage", str(tenant_id)
        )

        from app.services.cmdb.price_list_template_service import PriceListTemplateService

        db = await _get_session(info)
        service = PriceListTemplateService(db)
        pl = await service.clone_to_price_list(
            str(template_id), str(tenant_id),
        )
        await db.commit()
        return _price_list_to_gql(pl)
