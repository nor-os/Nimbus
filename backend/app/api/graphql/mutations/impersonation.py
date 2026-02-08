"""
Overview: GraphQL mutations for impersonation operations.
Architecture: GraphQL mutation resolvers for impersonation lifecycle (Section 7.2)
Dependencies: strawberry, app.services.impersonation
Concepts: GraphQL mutations, impersonation request/approval/end/extend
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


@strawberry.input
class ImpersonationRequestInput:
    target_user_id: uuid.UUID
    tenant_id: uuid.UUID
    mode: ImpersonationModeGQL = ImpersonationModeGQL.STANDARD
    reason: str
    password: str


@strawberry.input
class ImpersonationApprovalInput:
    session_id: uuid.UUID
    decision: str
    reason: str | None = None


@strawberry.input
class ImpersonationExtendInput:
    session_id: uuid.UUID
    minutes: int


@strawberry.input
class ImpersonationConfigInput:
    tenant_id: uuid.UUID
    standard_duration_minutes: int | None = None
    override_duration_minutes: int | None = None
    standard_requires_approval: bool | None = None
    override_requires_approval: bool | None = None
    max_duration_minutes: int | None = None


async def _get_authenticated_user_id(info: Info) -> str:
    """Extract authenticated user ID from GraphQL context request."""
    request = info.context["request"]
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("Not authenticated")

    token = auth_header[7:]
    from app.services.auth.jwt import decode_token

    payload = decode_token(token)
    return payload["sub"]


@strawberry.type
class ImpersonationMutation:
    @strawberry.mutation
    async def request_impersonation(
        self, info: Info, input: ImpersonationRequestInput
    ) -> ImpersonationSessionType:
        """Request an impersonation session."""
        await check_graphql_permission(info, "impersonation:session:create", str(input.tenant_id))
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        requester_id = await _get_authenticated_user_id(info)

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            session = await service.request_impersonation(
                requester_id=requester_id,
                target_user_id=str(input.target_user_id),
                tenant_id=str(input.tenant_id),
                mode=input.mode.value,
                reason=input.reason,
                password=input.password,
            )
            await db.commit()
            return _to_type(session)

    @strawberry.mutation
    async def approve_impersonation(
        self, info: Info, input: ImpersonationApprovalInput
    ) -> ImpersonationSessionType:
        """Approve or reject an impersonation request."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        approver_id = await _get_authenticated_user_id(info)

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            session = await service.process_approval(
                session_id=str(input.session_id),
                approver_id=approver_id,
                decision=input.decision,
                reason=input.reason,
            )
            await db.commit()
            return _to_type(session)

    @strawberry.mutation
    async def end_impersonation(self, info: Info, session_id: uuid.UUID) -> bool:
        """End an active impersonation session."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            await service.end_session(str(session_id), "manual")
            await db.commit()
            return True

    @strawberry.mutation
    async def extend_impersonation(
        self, info: Info, input: ImpersonationExtendInput
    ) -> ImpersonationSessionType:
        """Extend an active impersonation session."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            await service.extend_session(str(input.session_id), input.minutes)
            await db.commit()
            session = await service.get_session(str(input.session_id))
            return _to_type(session)

    @strawberry.mutation
    async def update_impersonation_config(
        self, info: Info, input: ImpersonationConfigInput
    ) -> ImpersonationConfigType:
        """Update impersonation configuration for a tenant."""
        await check_graphql_permission(info, "impersonation:config:manage", str(input.tenant_id))
        from app.db.session import async_session_factory
        from app.services.impersonation.config import ImpersonationConfigService

        async with async_session_factory() as db:
            service = ImpersonationConfigService(db)
            updates = {}
            if input.standard_duration_minutes is not None:
                updates["standard_duration_minutes"] = input.standard_duration_minutes
            if input.override_duration_minutes is not None:
                updates["override_duration_minutes"] = input.override_duration_minutes
            if input.standard_requires_approval is not None:
                updates["standard_requires_approval"] = input.standard_requires_approval
            if input.override_requires_approval is not None:
                updates["override_requires_approval"] = input.override_requires_approval
            if input.max_duration_minutes is not None:
                updates["max_duration_minutes"] = input.max_duration_minutes

            config = await service.update_config(str(input.tenant_id), updates)
            await db.commit()
            return ImpersonationConfigType(**config)


def _to_type(s) -> ImpersonationSessionType:
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
