"""
Overview: GraphQL queries for approval policies, requests, and pending inbox.
Architecture: GraphQL query resolvers for approval workflows (Section 7.2)
Dependencies: strawberry, app.services.approval
Concepts: GraphQL queries, approval management, inbox
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.approval import (
    ApprovalChainModeGQL,
    ApprovalPolicyType,
    ApprovalRequestListType,
    ApprovalRequestStatusGQL,
    ApprovalRequestType,
    ApprovalStepStatusGQL,
    ApprovalStepType,
)


def _policy_to_type(p) -> ApprovalPolicyType:
    return ApprovalPolicyType(
        id=p.id,
        tenant_id=p.tenant_id,
        operation_type=p.operation_type,
        chain_mode=ApprovalChainModeGQL(p.chain_mode.value),
        quorum_required=p.quorum_required,
        timeout_minutes=p.timeout_minutes,
        escalation_user_ids=(
            [str(u) for u in p.escalation_user_ids] if p.escalation_user_ids else None
        ),
        approver_role_names=p.approver_role_names,
        approver_user_ids=[str(u) for u in p.approver_user_ids] if p.approver_user_ids else None,
        approver_group_ids=[str(g) for g in p.approver_group_ids] if p.approver_group_ids else None,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _step_to_type(s) -> ApprovalStepType:
    return ApprovalStepType(
        id=s.id,
        tenant_id=s.tenant_id,
        approval_request_id=s.approval_request_id,
        step_order=s.step_order,
        approver_id=s.approver_id,
        delegate_to_id=s.delegate_to_id,
        status=ApprovalStepStatusGQL(s.status.value),
        decision_at=s.decision_at,
        reason=s.reason,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _request_to_type(r) -> ApprovalRequestType:
    return ApprovalRequestType(
        id=r.id,
        tenant_id=r.tenant_id,
        operation_type=r.operation_type,
        requester_id=r.requester_id,
        workflow_id=r.workflow_id,
        parent_workflow_id=r.parent_workflow_id,
        chain_mode=r.chain_mode,
        quorum_required=r.quorum_required,
        status=ApprovalRequestStatusGQL(r.status.value),
        title=r.title,
        description=r.description,
        context=r.context,
        resolved_at=r.resolved_at,
        steps=[_step_to_type(s) for s in (r.steps or [])],
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@strawberry.type
class ApprovalQuery:
    @strawberry.field
    async def approval_policies(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[ApprovalPolicyType]:
        """List approval policies for a tenant."""
        await check_graphql_permission(info, "approval:policy:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.approval.service import ApprovalService

        async with async_session_factory() as db:
            service = ApprovalService(db)
            policies = await service.get_policies(str(tenant_id))
            return [_policy_to_type(p) for p in policies]

    @strawberry.field
    async def approval_requests(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        requester_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ApprovalRequestListType:
        """List approval requests for a tenant."""
        await check_graphql_permission(info, "approval:request:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.approval.service import ApprovalService

        async with async_session_factory() as db:
            service = ApprovalService(db)
            items, total = await service.get_requests(
                tenant_id=str(tenant_id),
                status=status,
                requester_id=str(requester_id) if requester_id else None,
                offset=offset,
                limit=limit,
            )
            return ApprovalRequestListType(
                items=[_request_to_type(r) for r in items],
                total=total,
            )

    @strawberry.field
    async def approval_request(
        self, info: Info, tenant_id: uuid.UUID, request_id: uuid.UUID
    ) -> ApprovalRequestType | None:
        """Get a single approval request with steps."""
        await check_graphql_permission(info, "approval:request:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.approval.service import ApprovalService

        async with async_session_factory() as db:
            service = ApprovalService(db)
            r = await service.get_request(str(tenant_id), str(request_id))
            if not r:
                return None
            return _request_to_type(r)

    @strawberry.field
    async def pending_approvals(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> ApprovalRequestListType:
        """Get pending approval requests for the current user (inbox)."""
        user_id = await check_graphql_permission(
            info, "approval:decision:submit", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.approval.service import ApprovalService

        async with async_session_factory() as db:
            service = ApprovalService(db)
            items, total = await service.get_pending_for_user(
                tenant_id=str(tenant_id),
                user_id=user_id,
                offset=offset,
                limit=limit,
            )
            return ApprovalRequestListType(
                items=[_request_to_type(r) for r in items],
                total=total,
            )
