"""
Overview: GraphQL mutations for approval workflow operations.
Architecture: GraphQL mutation resolvers for approval lifecycle (Section 7.2)
Dependencies: strawberry, app.services.approval, temporalio
Concepts: GraphQL mutations, approval policy management, decision submission, delegation
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.approval import _policy_to_type
from app.api.graphql.types.approval import (
    ApprovalDecisionGQLInput,
    ApprovalDelegateGQLInput,
    ApprovalPolicyInput,
    ApprovalPolicyType,
    ApprovalPolicyUpdateInput,
)

logger = logging.getLogger(__name__)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class ApprovalMutation:
    @strawberry.mutation
    async def create_approval_policy(
        self, info: Info, tenant_id: uuid.UUID, input: ApprovalPolicyInput
    ) -> ApprovalPolicyType:
        """Create an approval policy for a tenant."""
        await check_graphql_permission(info, "approval:policy:manage", str(tenant_id))
        from app.services.approval.service import ApprovalService

        db = await _get_session(info)
        service = ApprovalService(db)
        policy = await service.create_policy(
            str(tenant_id),
            {
                "operation_type": input.operation_type,
                "chain_mode": input.chain_mode.value,
                "quorum_required": input.quorum_required,
                "timeout_minutes": input.timeout_minutes,
                "escalation_user_ids": input.escalation_user_ids,
                "approver_role_names": input.approver_role_names,
                "approver_user_ids": input.approver_user_ids,
                "approver_group_ids": input.approver_group_ids,
                "is_active": input.is_active,
            },
        )
        await db.commit()
        return _policy_to_type(policy)

    @strawberry.mutation
    async def update_approval_policy(
        self, info: Info, tenant_id: uuid.UUID, policy_id: uuid.UUID,
        input: ApprovalPolicyUpdateInput
    ) -> ApprovalPolicyType | None:
        """Update an approval policy."""
        await check_graphql_permission(info, "approval:policy:manage", str(tenant_id))
        from app.services.approval.service import ApprovalService

        data = {}
        if input.chain_mode is not None:
            data["chain_mode"] = input.chain_mode.value
        if input.quorum_required is not None:
            data["quorum_required"] = input.quorum_required
        if input.timeout_minutes is not None:
            data["timeout_minutes"] = input.timeout_minutes
        if input.escalation_user_ids is not None:
            data["escalation_user_ids"] = input.escalation_user_ids
        if input.approver_role_names is not None:
            data["approver_role_names"] = input.approver_role_names
        if input.approver_user_ids is not None:
            data["approver_user_ids"] = input.approver_user_ids
        if input.approver_group_ids is not None:
            data["approver_group_ids"] = input.approver_group_ids
        if input.is_active is not None:
            data["is_active"] = input.is_active

        db = await _get_session(info)
        service = ApprovalService(db)
        policy = await service.update_policy(str(tenant_id), str(policy_id), data)
        if not policy:
            return None
        await db.commit()
        return _policy_to_type(policy)

    @strawberry.mutation
    async def delete_approval_policy(
        self, info: Info, tenant_id: uuid.UUID, policy_id: uuid.UUID
    ) -> bool:
        """Soft-delete an approval policy."""
        await check_graphql_permission(info, "approval:policy:manage", str(tenant_id))
        from app.services.approval.service import ApprovalService

        db = await _get_session(info)
        service = ApprovalService(db)
        deleted = await service.delete_policy(str(tenant_id), str(policy_id))
        await db.commit()
        return deleted

    @strawberry.mutation
    async def submit_approval_decision(
        self, info: Info, tenant_id: uuid.UUID, input: ApprovalDecisionGQLInput
    ) -> bool:
        """Submit an approve/reject decision and signal the approval workflow."""
        user_id = await check_graphql_permission(
            info, "approval:decision:submit", str(tenant_id)
        )
        from app.services.approval.service import ApprovalService

        db = await _get_session(info)
        service = ApprovalService(db)

        # Submit decision in DB
        step = await service.submit_decision(
            tenant_id=str(tenant_id),
            step_id=str(input.step_id),
            approver_id=user_id,
            decision=input.decision,
            reason=input.reason,
        )
        await db.commit()

        # Get the request to find the workflow ID
        request = await service.get_request(str(tenant_id), str(step.approval_request_id))

        # Send signal to the ApprovalChainWorkflow
        if request and request.workflow_id:
            try:
                from app.core.temporal import get_temporal_client
                from app.workflows.approval import ApprovalChainWorkflow

                client = await get_temporal_client()
                handle = client.get_workflow_handle(request.workflow_id)
                await handle.signal(
                    ApprovalChainWorkflow.submit_decision,
                    str(input.step_id),
                    input.decision,
                    input.reason,
                )
            except Exception:
                logger.warning(
                    "Failed to send decision signal to workflow %s",
                    request.workflow_id,
                    exc_info=True,
                )

        return True

    @strawberry.mutation
    async def delegate_approval(
        self, info: Info, tenant_id: uuid.UUID, input: ApprovalDelegateGQLInput
    ) -> bool:
        """Delegate an approval step to another user and signal the workflow."""
        user_id = await check_graphql_permission(
            info, "approval:decision:delegate", str(tenant_id)
        )
        from app.services.approval.service import ApprovalService

        db = await _get_session(info)
        service = ApprovalService(db)

        # Get original step to find request_id
        from sqlalchemy import select

        from app.models.approval_step import ApprovalStep

        result = await db.execute(
            select(ApprovalStep).where(ApprovalStep.id == str(input.step_id))
        )
        original_step = result.scalar_one_or_none()
        if not original_step:
            raise ValueError("Step not found")

        await service.delegate_step(
            tenant_id=str(tenant_id),
            step_id=str(input.step_id),
            approver_id=user_id,
            delegate_to_id=str(input.delegate_to_id),
        )
        await db.commit()

        # Get request for workflow ID
        request = await service.get_request(
            str(tenant_id), str(original_step.approval_request_id)
        )

        # Signal the workflow about delegation
        if request and request.workflow_id:
            try:
                from app.core.temporal import get_temporal_client
                from app.workflows.approval import ApprovalChainWorkflow

                client = await get_temporal_client()
                handle = client.get_workflow_handle(request.workflow_id)
                await handle.signal(
                    ApprovalChainWorkflow.delegate,
                    str(input.step_id),
                    str(input.delegate_to_id),
                )
            except Exception:
                logger.warning(
                    "Failed to send delegate signal to workflow %s",
                    request.workflow_id,
                    exc_info=True,
                )

        return True

    @strawberry.mutation
    async def cancel_approval_request(
        self, info: Info, tenant_id: uuid.UUID, request_id: uuid.UUID
    ) -> bool:
        """Cancel a pending approval request (only requester can cancel)."""
        user_id = await check_graphql_permission(
            info, "approval:request:create", str(tenant_id)
        )
        from app.services.approval.service import ApprovalService

        db = await _get_session(info)
        service = ApprovalService(db)
        request = await service.get_request(str(tenant_id), str(request_id))
        if not request:
            raise ValueError("Request not found")
        if str(request.requester_id) != user_id:
            raise PermissionError("Only the requester can cancel")

        cancelled = await service.cancel_request(str(tenant_id), str(request_id))
        await db.commit()

        # Signal the workflow to cancel
        if request.workflow_id and cancelled:
            try:
                from app.core.temporal import get_temporal_client
                from app.workflows.approval import ApprovalChainWorkflow

                client = await get_temporal_client()
                handle = client.get_workflow_handle(request.workflow_id)
                await handle.signal(ApprovalChainWorkflow.cancel)
            except Exception:
                logger.warning(
                    "Failed to send cancel signal to workflow %s",
                    request.workflow_id,
                    exc_info=True,
                )

        return cancelled
