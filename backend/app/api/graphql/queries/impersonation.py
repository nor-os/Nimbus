"""
Overview: GraphQL queries for impersonation sessions and configuration.
Architecture: GraphQL query resolvers for impersonation (Section 7.2)
Dependencies: strawberry, app.services.impersonation
Concepts: GraphQL queries, impersonation management
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.impersonation import (
    ImpersonationConfigType,
    ImpersonationModeGQL,
    ImpersonationSessionType,
    ImpersonationStatusGQL,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ImpersonationQuery:
    @strawberry.field
    async def impersonation_sessions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ImpersonationSessionType]:
        """List impersonation sessions for a tenant."""
        await check_graphql_permission(info, "impersonation:session:read", str(tenant_id))
        from app.services.impersonation.service import ImpersonationService

        db = await _get_session(info)
        service = ImpersonationService(db)
        sessions, _total = await service.get_sessions(str(tenant_id), offset, limit)
        return [
            ImpersonationSessionType(
                id=s.id,
                tenant_id=s.tenant_id,
                requester_id=s.requester_id,
                target_user_id=s.target_user_id,
                mode=ImpersonationModeGQL(s.mode.value),
                status=ImpersonationStatusGQL(s.status.value),
                reason=s.reason,
                rejection_reason=s.rejection_reason,
                approver_id=s.approver_id,
                approval_decision_at=s.approval_decision_at,
                started_at=s.started_at,
                expires_at=s.expires_at,
                ended_at=s.ended_at,
                end_reason=s.end_reason,
                workflow_id=s.workflow_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]

    @strawberry.field
    async def impersonation_session(
        self, info: Info, session_id: uuid.UUID
    ) -> ImpersonationSessionType | None:
        """Get a single impersonation session."""
        from app.services.impersonation.service import ImpersonationService

        db = await _get_session(info)
        service = ImpersonationService(db)
        s = await service.get_session(str(session_id))
        if not s:
            return None
        return ImpersonationSessionType(
            id=s.id,
            tenant_id=s.tenant_id,
            requester_id=s.requester_id,
            target_user_id=s.target_user_id,
            mode=ImpersonationModeGQL(s.mode.value),
            status=ImpersonationStatusGQL(s.status.value),
            reason=s.reason,
            rejection_reason=s.rejection_reason,
            approver_id=s.approver_id,
            approval_decision_at=s.approval_decision_at,
            started_at=s.started_at,
            expires_at=s.expires_at,
            ended_at=s.ended_at,
            end_reason=s.end_reason,
            workflow_id=s.workflow_id,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )

    @strawberry.field
    async def impersonation_config(
        self, info: Info, tenant_id: uuid.UUID
    ) -> ImpersonationConfigType:
        """Get impersonation configuration for a tenant."""
        await check_graphql_permission(info, "impersonation:session:read", str(tenant_id))
        from app.services.impersonation.config import ImpersonationConfigService

        db = await _get_session(info)
        service = ImpersonationConfigService(db)
        config = await service.get_config(str(tenant_id))
        return ImpersonationConfigType(**config)
