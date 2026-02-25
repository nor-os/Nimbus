"""
Overview: GraphQL queries for landing zones, environments, and IPAM.
Architecture: Query resolvers for landing zones & IPAM (Section 7.2)
Dependencies: strawberry, app.services.landing_zone.*, app.services.ipam.*, app.api.graphql.auth
Concepts: Landing zone queries, environment listing, IPAM queries, CIDR utilities
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.landing_zone import (
    AddressAllocationType,
    AddressSpaceType,
    AllocationStatusGQL,
    AllocationTypeGQL,
    AddressSpaceStatusGQL,
    BackendRegionRefType,
    CidrSuggestionType,
    CidrSummaryType,
    EnvironmentStatusGQL,
    EnvironmentTemplateType,
    HierarchyLevelType,
    IpReservationType,
    LandingZoneBlueprintType,
    LandingZoneCheckType,
    LandingZoneStatusGQL,
    LandingZoneTagPolicyType,
    LandingZoneType,
    LandingZoneValidationType,
    ProviderHierarchyType,
    ReservationStatusGQL,
    TenantEnvironmentType,
)


# ── Converters ─────────────────────────────────────────────────────────

def _reservation_to_type(r) -> IpReservationType:
    return IpReservationType(
        id=r.id, allocation_id=r.allocation_id, ip_address=r.ip_address,
        hostname=r.hostname, purpose=r.purpose, ci_id=r.ci_id,
        status=ReservationStatusGQL(r.status.value),
        reserved_by=r.reserved_by, created_at=r.created_at, updated_at=r.updated_at,
    )


def _allocation_to_type(a) -> AddressAllocationType:
    return AddressAllocationType(
        id=a.id, address_space_id=a.address_space_id,
        parent_allocation_id=a.parent_allocation_id,
        tenant_environment_id=a.tenant_environment_id,
        name=a.name, description=a.description, cidr=a.cidr,
        allocation_type=AllocationTypeGQL(a.allocation_type.value),
        status=AllocationStatusGQL(a.status.value),
        purpose=a.purpose, semantic_type_id=a.semantic_type_id,
        cloud_resource_id=a.cloud_resource_id,
        utilization_percent=a.utilization_percent,
        metadata=a.allocation_metadata, created_at=a.created_at, updated_at=a.updated_at,
        children=[_allocation_to_type(c) for c in (a.children or [])],
        reservations=[_reservation_to_type(r) for r in (a.reservations or [])],
    )


def _space_to_type(s) -> AddressSpaceType:
    return AddressSpaceType(
        id=s.id, landing_zone_id=s.landing_zone_id, region_id=s.region_id,
        name=s.name, description=s.description, cidr=s.cidr,
        ip_version=s.ip_version, status=AddressSpaceStatusGQL(s.status.value),
        created_at=s.created_at, updated_at=s.updated_at,
        allocations=[_allocation_to_type(a) for a in (s.allocations or [])],
    )


def _tag_policy_to_type(tp) -> LandingZoneTagPolicyType:
    return LandingZoneTagPolicyType(
        id=tp.id, landing_zone_id=tp.landing_zone_id,
        tag_key=tp.tag_key, display_name=tp.display_name,
        description=tp.description, is_required=tp.is_required,
        allowed_values=tp.allowed_values, default_value=tp.default_value,
        inherited=tp.inherited, created_at=tp.created_at, updated_at=tp.updated_at,
    )


def _zone_to_type(z) -> LandingZoneType:
    region_ref = None
    if z.region:
        region_ref = BackendRegionRefType(
            id=z.region.id,
            region_identifier=z.region.region_identifier,
            display_name=z.region.display_name,
        )
    return LandingZoneType(
        id=z.id, tenant_id=z.tenant_id, backend_id=z.backend_id,
        region_id=z.region_id, region=region_ref,
        topology_id=z.topology_id, cloud_tenancy_id=z.cloud_tenancy_id,
        name=z.name, description=z.description,
        status=LandingZoneStatusGQL(z.status.value),
        version=z.version, settings=z.settings,
        network_config=z.network_config, iam_config=z.iam_config,
        security_config=z.security_config, naming_config=z.naming_config,
        hierarchy=z.hierarchy,
        created_by=z.created_by,
        created_at=z.created_at, updated_at=z.updated_at,
        tag_policies=[_tag_policy_to_type(tp) for tp in (z.tag_policies or [])],
    )


def _template_to_type(t) -> EnvironmentTemplateType:
    return EnvironmentTemplateType(
        id=t.id, provider_id=t.provider_id, name=t.name,
        display_name=t.display_name, description=t.description,
        icon=t.icon, color=t.color, default_tags=t.default_tags,
        default_policies=t.default_policies, sort_order=t.sort_order,
        is_system=t.is_system, created_at=t.created_at, updated_at=t.updated_at,
    )


def _env_to_type(e) -> TenantEnvironmentType:
    # Resolve provider name via landing_zone -> backend -> provider chain
    provider_name = None
    if hasattr(e, 'landing_zone') and e.landing_zone:
        lz = e.landing_zone
        if hasattr(lz, 'backend') and lz.backend:
            backend = lz.backend
            if hasattr(backend, 'provider') and backend.provider:
                provider_name = backend.provider.name
    region_ref = None
    if hasattr(e, 'region') and e.region:
        region_ref = BackendRegionRefType(
            id=e.region.id,
            region_identifier=e.region.region_identifier,
            display_name=e.region.display_name,
        )
    return TenantEnvironmentType(
        id=e.id, tenant_id=e.tenant_id, landing_zone_id=e.landing_zone_id,
        template_id=e.template_id,
        region_id=getattr(e, 'region_id', None),
        region=region_ref,
        dr_source_env_id=getattr(e, 'dr_source_env_id', None),
        dr_config=getattr(e, 'dr_config', None),
        name=e.name, display_name=e.display_name,
        description=e.description, status=EnvironmentStatusGQL(e.status.value),
        root_compartment_id=e.root_compartment_id, tags=e.tags, policies=e.policies,
        settings=e.settings,
        network_config=e.network_config, iam_config=e.iam_config,
        security_config=e.security_config, monitoring_config=e.monitoring_config,
        provider_name=provider_name,
        created_by=e.created_by,
        created_at=e.created_at, updated_at=e.updated_at,
    )


# ── Queries ────────────────────────────────────────────────────────────


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class LandingZoneQuery:

    @strawberry.field
    async def landing_zones(
        self, info: Info, tenant_id: uuid.UUID,
        status: str | None = None, search: str | None = None,
        offset: int | None = None, limit: int | None = None,
    ) -> list[LandingZoneType]:
        """List all landing zones for a tenant."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.zone_service import LandingZoneService

        db = await _get_session(info)
        svc = LandingZoneService()
        zones = await svc.list_by_tenant(db, tenant_id, status=status, search=search,
                                         offset=offset, limit=limit)
        return [_zone_to_type(z) for z in zones]

    @strawberry.field
    async def landing_zone(
        self, info: Info, tenant_id: uuid.UUID, zone_id: uuid.UUID,
    ) -> LandingZoneType | None:
        """Get a landing zone by ID."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.zone_service import LandingZoneService

        db = await _get_session(info)
        svc = LandingZoneService()
        z = await svc.get(db, zone_id)
        return _zone_to_type(z) if z else None

    @strawberry.field
    async def landing_zones_by_backend(
        self, info: Info, tenant_id: uuid.UUID, backend_id: uuid.UUID,
    ) -> list[LandingZoneType]:
        """List landing zones for a specific cloud backend."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.zone_service import LandingZoneService

        db = await _get_session(info)
        svc = LandingZoneService()
        zones = await svc.list_by_backend(db, backend_id)
        return [_zone_to_type(z) for z in zones]

    @strawberry.field
    async def landing_zone_by_backend(
        self, info: Info, tenant_id: uuid.UUID, backend_id: uuid.UUID,
    ) -> LandingZoneType | None:
        """Get the single landing zone for a cloud backend (1:1 relationship)."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.zone_service import LandingZoneService

        db = await _get_session(info)
        svc = LandingZoneService()
        z = await svc.get_by_backend(db, backend_id)
        return _zone_to_type(z) if z else None

    @strawberry.field
    async def landing_zones_by_region(
        self, info: Info, tenant_id: uuid.UUID, region_id: uuid.UUID,
    ) -> list[LandingZoneType]:
        """List landing zones for a specific backend region."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.zone_service import LandingZoneService

        db = await _get_session(info)
        svc = LandingZoneService()
        zones = await svc.list_by_region(db, region_id)
        return [_zone_to_type(z) for z in zones]

    # ── Environment Templates ──────────────────────────────────────

    @strawberry.field
    async def environment_templates(
        self, info: Info, tenant_id: uuid.UUID,
        provider_id: uuid.UUID | None = None,
        offset: int | None = None, limit: int | None = None,
    ) -> list[EnvironmentTemplateType]:
        """List environment templates, optionally filtered by provider."""
        await check_graphql_permission(info, "landingzone:template:read", str(tenant_id))

        from app.services.landing_zone.environment_service import EnvironmentService

        db = await _get_session(info)
        svc = EnvironmentService()
        templates = await svc.list_templates(db, provider_id, offset=offset, limit=limit)
        return [_template_to_type(t) for t in templates]

    @strawberry.field
    async def environment_template(
        self, info: Info, tenant_id: uuid.UUID, template_id: uuid.UUID,
    ) -> EnvironmentTemplateType | None:
        """Get an environment template by ID."""
        await check_graphql_permission(info, "landingzone:template:read", str(tenant_id))

        from app.services.landing_zone.environment_service import EnvironmentService

        db = await _get_session(info)
        svc = EnvironmentService()
        t = await svc.get_template(db, template_id)
        return _template_to_type(t) if t else None

    # ── Tenant Environments ────────────────────────────────────────

    @strawberry.field
    async def tenant_environments(
        self, info: Info, tenant_id: uuid.UUID,
        landing_zone_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int | None = None, limit: int | None = None,
    ) -> list[TenantEnvironmentType]:
        """List tenant environments."""
        await check_graphql_permission(info, "landingzone:environment:read", str(tenant_id))

        from app.services.landing_zone.environment_service import EnvironmentService

        db = await _get_session(info)
        svc = EnvironmentService()
        envs = await svc.list_environments(db, tenant_id, landing_zone_id,
                                           status=status, offset=offset, limit=limit)
        return [_env_to_type(e) for e in envs]

    @strawberry.field
    async def tenant_environment(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> TenantEnvironmentType | None:
        """Get a tenant environment by ID."""
        await check_graphql_permission(info, "landingzone:environment:read", str(tenant_id))

        from app.services.landing_zone.environment_service import EnvironmentService

        db = await _get_session(info)
        svc = EnvironmentService()
        e = await svc.get_environment(db, environment_id)
        return _env_to_type(e) if e else None

    # ── IPAM ───────────────────────────────────────────────────────

    @strawberry.field
    async def address_spaces(
        self, info: Info, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID,
    ) -> list[AddressSpaceType]:
        """List address spaces for a landing zone."""
        await check_graphql_permission(info, "ipam:space:read", str(tenant_id))

        from app.services.ipam.ipam_service import IpamService

        db = await _get_session(info)
        svc = IpamService()
        spaces = await svc.list_address_spaces(db, landing_zone_id)
        return [_space_to_type(s) for s in spaces]

    @strawberry.field
    async def address_space(
        self, info: Info, tenant_id: uuid.UUID, space_id: uuid.UUID,
    ) -> AddressSpaceType | None:
        """Get an address space by ID."""
        await check_graphql_permission(info, "ipam:space:read", str(tenant_id))

        from app.services.ipam.ipam_service import IpamService

        db = await _get_session(info)
        svc = IpamService()
        s = await svc.get_address_space(db, space_id)
        return _space_to_type(s) if s else None

    @strawberry.field
    async def address_allocations(
        self, info: Info, tenant_id: uuid.UUID,
        address_space_id: uuid.UUID, parent_id: uuid.UUID | None = None,
    ) -> list[AddressAllocationType]:
        """List allocations in an address space, optionally filtered by parent."""
        await check_graphql_permission(info, "ipam:allocation:read", str(tenant_id))

        from app.services.ipam.ipam_service import IpamService

        db = await _get_session(info)
        svc = IpamService()
        allocs = await svc.list_allocations(db, address_space_id, parent_id=parent_id)
        return [_allocation_to_type(a) for a in allocs]

    @strawberry.field
    async def ip_reservations(
        self, info: Info, tenant_id: uuid.UUID, allocation_id: uuid.UUID,
    ) -> list[IpReservationType]:
        """List IP reservations for a subnet allocation."""
        await check_graphql_permission(info, "ipam:reservation:read", str(tenant_id))

        from app.services.ipam.ipam_service import IpamService

        db = await _get_session(info)
        svc = IpamService()
        reservations = await svc.list_reservations(db, allocation_id)
        return [_reservation_to_type(r) for r in reservations]

    @strawberry.field
    async def environment_ipam_allocations(
        self, info: Info, tenant_id: uuid.UUID, environment_id: uuid.UUID,
    ) -> list[AddressAllocationType]:
        """List IPAM allocations associated with a specific environment."""
        await check_graphql_permission(info, "ipam:allocation:read", str(tenant_id))

        from sqlalchemy import select

        from app.models.ipam import AddressAllocation

        db = await _get_session(info)
        stmt = (
            select(AddressAllocation)
            .where(
                AddressAllocation.tenant_environment_id == environment_id,
                AddressAllocation.status != "RELEASED",
            )
            .order_by(AddressAllocation.created_at)
        )
        result = await db.execute(stmt)
        allocs = result.scalars().all()
        return [_allocation_to_type(a) for a in allocs]

    @strawberry.field
    async def suggest_next_block(
        self, info: Info, tenant_id: uuid.UUID,
        address_space_id: uuid.UUID, prefix_length: int,
        parent_allocation_id: uuid.UUID | None = None,
    ) -> CidrSuggestionType:
        """Suggest the next available CIDR block of a given prefix length."""
        await check_graphql_permission(info, "ipam:allocation:read", str(tenant_id))

        from app.services.ipam.ipam_service import IpamService

        db = await _get_session(info)
        svc = IpamService()
        cidr = await svc.suggest_next_block(
            db, address_space_id, prefix_length,
            parent_allocation_id=parent_allocation_id,
        )
        return CidrSuggestionType(cidr=cidr, available=cidr is not None)

    @strawberry.field
    async def cidr_summary(
        self, info: Info, tenant_id: uuid.UUID, cidr: str,
    ) -> CidrSummaryType:
        """Get summary information about a CIDR block."""
        await check_graphql_permission(info, "ipam:space:read", str(tenant_id))

        from app.services.ipam.validation import cidr_summary

        summary = cidr_summary(cidr)
        return CidrSummaryType(**summary)

    # ── Hierarchy Levels ─────────────────────────────────────────

    @strawberry.field
    async def provider_hierarchy_levels(
        self, info: Info, provider_name: str,
    ) -> ProviderHierarchyType | None:
        """Get hierarchy level definitions for a provider."""
        from app.services.landing_zone.hierarchy_registry import get_hierarchy

        h = get_hierarchy(provider_name)
        if not h:
            return None
        return ProviderHierarchyType(
            provider_name=h.provider_name,
            root_type=h.root_type,
            levels=[
                HierarchyLevelType(
                    type_id=lv.type_id,
                    label=lv.label,
                    icon=lv.icon,
                    allowed_children=lv.allowed_children,
                    supports_ipam=lv.supports_ipam,
                    supports_tags=lv.supports_tags,
                    supports_environment=lv.supports_environment,
                )
                for lv in h.levels
            ],
        )

    # ── Blueprints ────────────────────────────────────────────────

    @strawberry.field
    async def landing_zone_blueprints(
        self, info: Info, provider_name: str,
    ) -> list[LandingZoneBlueprintType]:
        """Get landing zone blueprints for a given provider."""
        from app.services.landing_zone.blueprints import get_blueprints

        bps = get_blueprints(provider_name)
        return [
            LandingZoneBlueprintType(
                id=bp["id"],
                name=bp["name"],
                provider_name=bp["providerName"],
                description=bp["description"],
                complexity=bp["complexity"],
                features=bp["features"],
                hierarchy=bp["hierarchy"],
                network_config=bp["networkConfig"],
                iam_config=bp["iamConfig"],
                security_config=bp["securityConfig"],
                naming_config=bp["namingConfig"],
                default_tags=bp["defaultTags"],
                default_address_spaces=bp["defaultAddressSpaces"],
            )
            for bp in bps
        ]

    @strawberry.field
    async def landing_zone_blueprint(
        self, info: Info, blueprint_id: str,
    ) -> LandingZoneBlueprintType | None:
        """Get a single landing zone blueprint by ID."""
        from app.services.landing_zone.blueprints import get_blueprint

        bp = get_blueprint(blueprint_id)
        if not bp:
            return None
        return LandingZoneBlueprintType(
            id=bp["id"],
            name=bp["name"],
            provider_name=bp["providerName"],
            description=bp["description"],
            complexity=bp["complexity"],
            features=bp["features"],
            hierarchy=bp["hierarchy"],
            network_config=bp["networkConfig"],
            iam_config=bp["iamConfig"],
            security_config=bp["securityConfig"],
            naming_config=bp["namingConfig"],
            default_tags=bp["defaultTags"],
            default_address_spaces=bp["defaultAddressSpaces"],
        )

    # ── Validation ────────────────────────────────────────────────

    @strawberry.field
    async def validate_landing_zone(
        self, info: Info, tenant_id: uuid.UUID, zone_id: uuid.UUID,
    ) -> LandingZoneValidationType:
        """Validate a landing zone for publish readiness."""
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))

        from app.services.landing_zone.validation_service import LandingZoneValidationService

        db = await _get_session(info)
        svc = LandingZoneValidationService()
        result = await svc.validate(db, zone_id)
        return LandingZoneValidationType(
            ready=result.ready,
            checks=[
                LandingZoneCheckType(
                    key=c.key, label=c.label, status=c.status, message=c.message,
                )
                for c in result.checks
            ],
        )
