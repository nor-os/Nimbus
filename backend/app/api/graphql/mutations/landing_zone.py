"""
Overview: GraphQL mutations for landing zones, environments, and IPAM.
Architecture: Mutation resolvers for landing zones & IPAM (Section 7.2)
Dependencies: strawberry, app.services.landing_zone.*, app.services.ipam.*, app.api.graphql.auth
Concepts: Landing zone CRUD, environment lifecycle, IPAM allocation, IP reservation
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.landing_zone import (
    _allocation_to_type,
    _env_to_type,
    _region_to_type,
    _reservation_to_type,
    _space_to_type,
    _tag_policy_to_type,
    _template_to_type,
    _zone_to_type,
)
from app.api.graphql.types.landing_zone import (
    AddressAllocationType,
    AddressSpaceType,
    AllocationCreateInput,
    AddressSpaceCreateInput,
    EnvironmentTemplateCreateInput,
    EnvironmentTemplateType,
    IpReservationCreateInput,
    IpReservationType,
    LandingZoneCreateInput,
    LandingZoneRegionInput,
    LandingZoneRegionType,
    LandingZoneTagPolicyType,
    LandingZoneType,
    LandingZoneUpdateInput,
    TagPolicyInput,
    TenantEnvironmentCreateInput,
    TenantEnvironmentType,
    TenantEnvironmentUpdateInput,
)


@strawberry.type
class LandingZoneMutation:

    # ── Landing Zone CRUD ──────────────────────────────────────────

    @strawberry.mutation
    async def create_landing_zone(
        self, info: Info, tenant_id: uuid.UUID, input: LandingZoneCreateInput,
    ) -> LandingZoneType:
        """Create a new landing zone."""
        user_id = await check_graphql_permission(
            info, "landingzone:zone:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.landing_zone.zone_service import LandingZoneService

        async with async_session_factory() as db:
            svc = LandingZoneService()
            z = await svc.create(
                db, tenant_id=tenant_id, backend_id=input.backend_id,
                name=input.name, created_by=user_id,
                topology_id=input.topology_id,
                description=input.description,
                cloud_tenancy_id=input.cloud_tenancy_id, settings=input.settings,
                hierarchy=input.hierarchy,
            )
            await db.commit()
            return _zone_to_type(z)

    @strawberry.mutation
    async def update_landing_zone(
        self, info: Info, tenant_id: uuid.UUID,
        zone_id: uuid.UUID, input: LandingZoneUpdateInput,
    ) -> LandingZoneType:
        """Update a landing zone."""
        await check_graphql_permission(info, "landingzone:zone:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.zone_service import LandingZoneService

        async with async_session_factory() as db:
            svc = LandingZoneService()
            kwargs = {}
            if input.name is not None:
                kwargs["name"] = input.name
            if input.description is not None:
                kwargs["description"] = input.description
            if input.settings is not None:
                kwargs["settings"] = input.settings
            if input.network_config is not None:
                kwargs["network_config"] = input.network_config
            if input.iam_config is not None:
                kwargs["iam_config"] = input.iam_config
            if input.security_config is not None:
                kwargs["security_config"] = input.security_config
            if input.naming_config is not None:
                kwargs["naming_config"] = input.naming_config
            if input.hierarchy is not None:
                kwargs["hierarchy"] = input.hierarchy
            z = await svc.update(db, zone_id, **kwargs)
            await db.commit()
            return _zone_to_type(z)

    @strawberry.mutation
    async def publish_landing_zone(
        self, info: Info, tenant_id: uuid.UUID, zone_id: uuid.UUID,
    ) -> LandingZoneType:
        """Publish a landing zone (DRAFT → PUBLISHED)."""
        await check_graphql_permission(info, "landingzone:zone:publish", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.zone_service import LandingZoneService

        async with async_session_factory() as db:
            svc = LandingZoneService()
            z = await svc.publish(db, zone_id)
            await db.commit()
            return _zone_to_type(z)

    @strawberry.mutation
    async def archive_landing_zone(
        self, info: Info, tenant_id: uuid.UUID, zone_id: uuid.UUID,
    ) -> LandingZoneType:
        """Archive a landing zone."""
        await check_graphql_permission(info, "landingzone:zone:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.zone_service import LandingZoneService

        async with async_session_factory() as db:
            svc = LandingZoneService()
            z = await svc.archive(db, zone_id)
            await db.commit()
            return _zone_to_type(z)

    @strawberry.mutation
    async def delete_landing_zone(
        self, info: Info, tenant_id: uuid.UUID, zone_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a landing zone."""
        await check_graphql_permission(info, "landingzone:zone:delete", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.zone_service import LandingZoneService

        async with async_session_factory() as db:
            svc = LandingZoneService()
            await svc.delete(db, zone_id)
            await db.commit()
            return True

    # ── Regions ────────────────────────────────────────────────────

    @strawberry.mutation
    async def add_landing_zone_region(
        self, info: Info, tenant_id: uuid.UUID,
        zone_id: uuid.UUID, input: LandingZoneRegionInput,
    ) -> LandingZoneRegionType:
        """Add a region to a landing zone."""
        await check_graphql_permission(info, "landingzone:region:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.region_service import LandingZoneRegionService

        async with async_session_factory() as db:
            svc = LandingZoneRegionService()
            r = await svc.add_region(
                db, landing_zone_id=zone_id,
                region_identifier=input.region_identifier,
                display_name=input.display_name,
                is_primary=input.is_primary, is_dr=input.is_dr,
                settings=input.settings,
            )
            await db.commit()
            return _region_to_type(r)

    @strawberry.mutation
    async def remove_landing_zone_region(
        self, info: Info, tenant_id: uuid.UUID, region_id: uuid.UUID,
    ) -> bool:
        """Remove a region from a landing zone."""
        await check_graphql_permission(info, "landingzone:region:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.region_service import LandingZoneRegionService

        async with async_session_factory() as db:
            svc = LandingZoneRegionService()
            await svc.remove(db, region_id)
            await db.commit()
            return True

    # ── Tag Policies ───────────────────────────────────────────────

    @strawberry.mutation
    async def create_tag_policy(
        self, info: Info, tenant_id: uuid.UUID,
        zone_id: uuid.UUID, input: TagPolicyInput,
    ) -> LandingZoneTagPolicyType:
        """Create a tag policy for a landing zone."""
        await check_graphql_permission(info, "landingzone:tagpolicy:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.tag_policy_service import TagPolicyService

        async with async_session_factory() as db:
            svc = TagPolicyService()
            tp = await svc.create(
                db, landing_zone_id=zone_id, tag_key=input.tag_key,
                display_name=input.display_name, description=input.description,
                is_required=input.is_required, allowed_values=input.allowed_values,
                default_value=input.default_value, inherited=input.inherited,
            )
            await db.commit()
            return _tag_policy_to_type(tp)

    @strawberry.mutation
    async def update_tag_policy(
        self, info: Info, tenant_id: uuid.UUID,
        policy_id: uuid.UUID, input: TagPolicyInput,
    ) -> LandingZoneTagPolicyType:
        """Update a tag policy."""
        await check_graphql_permission(info, "landingzone:tagpolicy:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.tag_policy_service import TagPolicyService

        async with async_session_factory() as db:
            svc = TagPolicyService()
            tp = await svc.update(
                db, policy_id,
                display_name=input.display_name, description=input.description,
                is_required=input.is_required, allowed_values=input.allowed_values,
                default_value=input.default_value, inherited=input.inherited,
            )
            await db.commit()
            return _tag_policy_to_type(tp)

    @strawberry.mutation
    async def delete_tag_policy(
        self, info: Info, tenant_id: uuid.UUID, policy_id: uuid.UUID,
    ) -> bool:
        """Delete a tag policy."""
        await check_graphql_permission(info, "landingzone:tagpolicy:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.tag_policy_service import TagPolicyService

        async with async_session_factory() as db:
            svc = TagPolicyService()
            await svc.delete(db, policy_id)
            await db.commit()
            return True

    # ── Environment Templates ──────────────────────────────────────

    @strawberry.mutation
    async def create_environment_template(
        self, info: Info, tenant_id: uuid.UUID, input: EnvironmentTemplateCreateInput,
    ) -> EnvironmentTemplateType:
        """Create a custom environment template."""
        await check_graphql_permission(info, "landingzone:template:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.environment_service import EnvironmentService

        async with async_session_factory() as db:
            svc = EnvironmentService()
            t = await svc.create_template(
                db, provider_id=input.provider_id, name=input.name,
                display_name=input.display_name, description=input.description,
                icon=input.icon, color=input.color,
                default_tags=input.default_tags, default_policies=input.default_policies,
                sort_order=input.sort_order,
            )
            await db.commit()
            return _template_to_type(t)

    @strawberry.mutation
    async def delete_environment_template(
        self, info: Info, tenant_id: uuid.UUID, template_id: uuid.UUID,
    ) -> bool:
        """Delete a custom environment template."""
        await check_graphql_permission(info, "landingzone:template:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.environment_service import EnvironmentService

        async with async_session_factory() as db:
            svc = EnvironmentService()
            await svc.delete_template(db, template_id)
            await db.commit()
            return True

    # ── Tenant Environments ────────────────────────────────────────

    @strawberry.mutation
    async def create_tenant_environment(
        self, info: Info, tenant_id: uuid.UUID, input: TenantEnvironmentCreateInput,
    ) -> TenantEnvironmentType:
        """Create a tenant environment."""
        user_id = await check_graphql_permission(
            info, "landingzone:environment:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.landing_zone.environment_service import EnvironmentService

        async with async_session_factory() as db:
            svc = EnvironmentService()
            e = await svc.create_environment(
                db, tenant_id=tenant_id, landing_zone_id=input.landing_zone_id,
                name=input.name, display_name=input.display_name,
                created_by=user_id, template_id=input.template_id,
                description=input.description,
                root_compartment_id=input.root_compartment_id,
                tags=input.tags, policies=input.policies, settings=input.settings,
                network_config=input.network_config, iam_config=input.iam_config,
                security_config=input.security_config, monitoring_config=input.monitoring_config,
            )
            await db.commit()
            return _env_to_type(e)

    @strawberry.mutation
    async def update_tenant_environment(
        self, info: Info, tenant_id: uuid.UUID,
        environment_id: uuid.UUID, input: TenantEnvironmentUpdateInput,
    ) -> TenantEnvironmentType:
        """Update a tenant environment."""
        await check_graphql_permission(info, "landingzone:environment:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.landing_zone.environment_service import EnvironmentService

        async with async_session_factory() as db:
            svc = EnvironmentService()
            kwargs = {}
            if input.name is not None:
                kwargs["name"] = input.name
            if input.display_name is not None:
                kwargs["display_name"] = input.display_name
            if input.description is not None:
                kwargs["description"] = input.description
            if input.tags is not None:
                kwargs["tags"] = input.tags
            if input.policies is not None:
                kwargs["policies"] = input.policies
            if input.settings is not None:
                kwargs["settings"] = input.settings
            if input.network_config is not None:
                kwargs["network_config"] = input.network_config
            if input.iam_config is not None:
                kwargs["iam_config"] = input.iam_config
            if input.security_config is not None:
                kwargs["security_config"] = input.security_config
            if input.monitoring_config is not None:
                kwargs["monitoring_config"] = input.monitoring_config
            e = await svc.update_environment(db, environment_id, **kwargs)
            await db.commit()
            return _env_to_type(e)

    @strawberry.mutation
    async def decommission_environment(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> TenantEnvironmentType:
        """Start decommissioning an environment."""
        await check_graphql_permission(
            info, "landingzone:environment:decommission", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.landing_zone.environment_service import EnvironmentService

        async with async_session_factory() as db:
            svc = EnvironmentService()
            e = await svc.decommission(db, environment_id)
            await db.commit()
            return _env_to_type(e)

    # ── IPAM: Address Spaces ───────────────────────────────────────

    @strawberry.mutation
    async def create_address_space(
        self, info: Info, tenant_id: uuid.UUID, input: AddressSpaceCreateInput,
    ) -> AddressSpaceType:
        """Create an address space for a landing zone."""
        await check_graphql_permission(info, "ipam:space:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            s = await svc.create_address_space(
                db, input.landing_zone_id, input.name, input.cidr,
                region_id=input.region_id, description=input.description,
                ip_version=input.ip_version,
            )
            await db.commit()
            return _space_to_type(s)

    @strawberry.mutation
    async def delete_address_space(
        self, info: Info, tenant_id: uuid.UUID, space_id: uuid.UUID,
    ) -> bool:
        """Soft-delete an address space."""
        await check_graphql_permission(info, "ipam:space:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            await svc.delete_address_space(db, space_id)
            await db.commit()
            return True

    # ── IPAM: Allocations ──────────────────────────────────────────

    @strawberry.mutation
    async def allocate_block(
        self, info: Info, tenant_id: uuid.UUID, input: AllocationCreateInput,
    ) -> AddressAllocationType:
        """Allocate a CIDR block within an address space."""
        await check_graphql_permission(info, "ipam:allocation:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            a = await svc.allocate_block(
                db, input.address_space_id, input.name, input.cidr,
                input.allocation_type.value,
                parent_allocation_id=input.parent_allocation_id,
                tenant_environment_id=input.tenant_environment_id,
                purpose=input.purpose, description=input.description,
            )
            await db.commit()
            return _allocation_to_type(a)

    @strawberry.mutation
    async def release_allocation(
        self, info: Info, tenant_id: uuid.UUID, allocation_id: uuid.UUID,
    ) -> bool:
        """Release a CIDR allocation."""
        await check_graphql_permission(info, "ipam:allocation:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            await svc.release_allocation(db, allocation_id)
            await db.commit()
            return True

    # ── IPAM: Reservations ─────────────────────────────────────────

    @strawberry.mutation
    async def reserve_ip(
        self, info: Info, tenant_id: uuid.UUID, input: IpReservationCreateInput,
    ) -> IpReservationType:
        """Reserve an individual IP address."""
        user_id = await check_graphql_permission(
            info, "ipam:reservation:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            r = await svc.reserve_ip(
                db, input.allocation_id, input.ip_address, input.purpose,
                user_id, hostname=input.hostname, ci_id=input.ci_id,
            )
            await db.commit()
            return _reservation_to_type(r)

    @strawberry.mutation
    async def release_ip_reservation(
        self, info: Info, tenant_id: uuid.UUID, reservation_id: uuid.UUID,
    ) -> bool:
        """Release an IP reservation."""
        await check_graphql_permission(info, "ipam:reservation:manage", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.ipam.ipam_service import IpamService

        async with async_session_factory() as db:
            svc = IpamService()
            await svc.release_reservation(db, reservation_id)
            await db.commit()
            return True
