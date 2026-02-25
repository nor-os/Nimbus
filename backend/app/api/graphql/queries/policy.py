"""
Overview: GraphQL queries for policy library entries and compartment policy resolution.
Architecture: Query resolvers for governance policies (Section 7.2)
Dependencies: strawberry, app.services.policy.*, app.api.graphql.auth
Concepts: Policy library queries, compartment resolution, permission-gated access
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.policy import (
    PolicyLibraryEntryType,
    PolicySummaryType,
    ResolvedPolicyType,
)


def _entry_to_type(e) -> PolicyLibraryEntryType:
    return PolicyLibraryEntryType(
        id=e.id,
        tenant_id=e.tenant_id,
        name=e.name,
        display_name=e.display_name,
        description=e.description,
        category=e.category.value if hasattr(e.category, "value") else str(e.category),
        statements=e.statements,
        variables=e.variables,
        severity=e.severity.value if hasattr(e.severity, "value") else str(e.severity),
        is_system=e.is_system,
        tags=list(e.tags) if e.tags else None,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class PolicyQuery:

    @strawberry.field
    async def policy_library_entries(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[PolicyLibraryEntryType]:
        """List policy library entries for a tenant (including system policies)."""
        await check_graphql_permission(info, "policy:library:read", str(tenant_id))

        from app.services.policy.policy_library_service import PolicyLibraryService

        db = await _get_session(info)
        svc = PolicyLibraryService(db)
        entries = await svc.list(str(tenant_id), category, search, offset, limit)
        return [_entry_to_type(e) for e in entries]

    @strawberry.field
    async def policy_library_entry(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyLibraryEntryType | None:
        """Get a single policy library entry by ID."""
        await check_graphql_permission(info, "policy:library:read", str(tenant_id))

        from app.services.policy.policy_library_service import PolicyLibraryService

        db = await _get_session(info)
        svc = PolicyLibraryService(db)
        entry = await svc.get(str(tenant_id), str(policy_id))
        return _entry_to_type(entry) if entry else None

    @strawberry.field
    async def resolve_compartment_policies(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
        compartment_id: str,
    ) -> list[ResolvedPolicyType]:
        """Resolve all effective policies for a compartment with inheritance."""
        await check_graphql_permission(info, "policy:resolution:read", str(tenant_id))

        from app.services.policy.policy_resolution_service import PolicyResolutionService

        db = await _get_session(info)
        svc = PolicyResolutionService(db)
        resolved = await svc.resolve_compartment_policies(
            str(tenant_id), str(topology_id), compartment_id
        )
        return [
            ResolvedPolicyType(
                policy_id=r.policy_id,
                name=r.name,
                source=r.source,
                source_compartment_id=r.source_compartment_id,
                statements=r.statements,
                severity=r.severity,
                category=r.category,
                can_suppress=r.can_suppress,
            )
            for r in resolved
        ]

    @strawberry.field
    async def compartment_policy_summary(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        topology_id: uuid.UUID,
        compartment_id: str,
    ) -> PolicySummaryType:
        """Get aggregated policy statistics for a compartment."""
        await check_graphql_permission(info, "policy:resolution:read", str(tenant_id))

        from app.services.policy.policy_resolution_service import PolicyResolutionService

        db = await _get_session(info)
        svc = PolicyResolutionService(db)
        summary = await svc.get_policy_summary(
            str(tenant_id), str(topology_id), compartment_id
        )
        return PolicySummaryType(
            compartment_id=summary.compartment_id,
            direct_policies=summary.direct_policies,
            inherited_policies=summary.inherited_policies,
            total_statements=summary.total_statements,
            deny_count=summary.deny_count,
            allow_count=summary.allow_count,
        )
