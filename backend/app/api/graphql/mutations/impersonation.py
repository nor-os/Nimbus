"""
Overview: GraphQL mutations for impersonation operations with Temporal workflow signals.
Architecture: GraphQL mutation resolvers for impersonation lifecycle (Section 7.2)
Dependencies: strawberry, app.services.impersonation, temporalio
Concepts: GraphQL mutations, impersonation request/approval/end/extend, Temporal signals
"""

import logging
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

logger = logging.getLogger(__name__)


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
        """Request an impersonation session and start Temporal workflow."""
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

            # Get config for this tenant
            from app.services.impersonation.config import ImpersonationConfigService

            config_service = ImpersonationConfigService(db)
            config = await config_service.get_config(str(input.tenant_id))

            mode_key = "standard" if input.mode == ImpersonationModeGQL.STANDARD else "override"
            requires_approval = config[f"{mode_key}_requires_approval"]
            duration_minutes = config[f"{mode_key}_duration_minutes"]

            # Resolve approval policy parameters
            from app.services.approval.service import ApprovalService

            approval_service = ApprovalService(db)
            op_type = f"impersonation.{mode_key}"
            policy = await approval_service.get_policy(str(input.tenant_id), op_type)

            chain_mode = "SEQUENTIAL"
            quorum_required = 1
            timeout_minutes = 1440
            escalation_user_ids: list[str] = []
            if policy and policy.is_active:
                chain_mode = policy.chain_mode.value
                quorum_required = policy.quorum_required
                timeout_minutes = policy.timeout_minutes
                escalation_user_ids = [str(u) for u in (policy.escalation_user_ids or [])]

            # Start Temporal workflow
            try:
                from app.core.config import get_settings
                from app.core.temporal import get_temporal_client
                from app.workflows.impersonation import (
                    ImpersonationWorkflow,
                    ImpersonationWorkflowInput,
                )

                settings = get_settings()
                client = await get_temporal_client()
                workflow_id = f"impersonation-{session.id}"
                await client.start_workflow(
                    ImpersonationWorkflow.run,
                    ImpersonationWorkflowInput(
                        session_id=str(session.id),
                        mode=input.mode.value,
                        requires_approval=requires_approval,
                        duration_minutes=duration_minutes,
                        max_duration_minutes=config["max_duration_minutes"],
                        tenant_id=str(input.tenant_id),
                        requester_id=requester_id,
                        chain_mode=chain_mode,
                        quorum_required=quorum_required,
                        timeout_minutes=timeout_minutes,
                        escalation_user_ids=escalation_user_ids,
                    ),
                    id=workflow_id,
                    task_queue=settings.temporal_task_queue,
                )

                session.workflow_id = workflow_id
                await db.commit()
            except Exception:
                logger.warning(
                    "Failed to start impersonation workflow for session %s",
                    session.id,
                    exc_info=True,
                )

            await db.refresh(session)
            return _to_type(session)

    @strawberry.mutation
    async def approve_impersonation(
        self, info: Info, input: ImpersonationApprovalInput
    ) -> ImpersonationSessionType:
        """Approve or reject an impersonation request (signals child ApprovalChainWorkflow)."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        approver_id = await _get_authenticated_user_id(info)

        async with async_session_factory() as db:
            # Check permission in session's tenant context
            service = ImpersonationService(db)
            session = await service.get_session(str(input.session_id))
            if session:
                await check_graphql_permission(
                    info, "impersonation:approval:decide", str(session.tenant_id)
                )

            session = await service.process_approval(
                session_id=str(input.session_id),
                approver_id=approver_id,
                decision=input.decision,
                reason=input.reason,
            )
            await db.commit()

            # Signal the child ApprovalChainWorkflow
            from sqlalchemy import select

            from app.models.approval_request import ApprovalRequest
            from app.models.approval_step import ApprovalStep, ApprovalStepStatus

            approval_req_result = await db.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.context["session_id"].astext == str(input.session_id),
                    ApprovalRequest.tenant_id == session.tenant_id,
                )
            )
            approval_request = approval_req_result.scalar_one_or_none()

            if approval_request and approval_request.workflow_id:
                try:
                    from app.core.temporal import get_temporal_client
                    from app.workflows.approval import ApprovalChainWorkflow

                    step_result = await db.execute(
                        select(ApprovalStep).where(
                            ApprovalStep.approval_request_id == approval_request.id,
                            ApprovalStep.approver_id == uuid.UUID(approver_id),
                            ApprovalStep.status == ApprovalStepStatus.PENDING,
                        )
                    )
                    step = step_result.scalar_one_or_none()
                    step_id = str(step.id) if step else ""

                    client = await get_temporal_client()
                    handle = client.get_workflow_handle(approval_request.workflow_id)
                    await handle.signal(
                        ApprovalChainWorkflow.submit_decision,
                        step_id,
                        input.decision,
                        input.reason,
                    )
                except Exception:
                    logger.warning(
                        "Failed to send approval signal to child workflow",
                        exc_info=True,
                    )

            return _to_type(session)

    @strawberry.mutation
    async def end_impersonation(self, info: Info, session_id: uuid.UUID) -> bool:
        """End an active impersonation session (signals Temporal workflow)."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            session = await service.get_session(str(session_id))
            if not session:
                raise ValueError("Session not found")

            await check_graphql_permission(
                info, "impersonation:session:read", str(session.tenant_id)
            )

            # Send Temporal signal to end
            if session.workflow_id:
                try:
                    from app.core.temporal import get_temporal_client
                    from app.workflows.impersonation import ImpersonationWorkflow

                    client = await get_temporal_client()
                    handle = client.get_workflow_handle(session.workflow_id)
                    await handle.signal(ImpersonationWorkflow.end_session)
                except Exception:
                    logger.warning(
                        "Failed to send end signal to workflow %s, falling back",
                        session.workflow_id,
                        exc_info=True,
                    )
                    await service.end_session(str(session_id), "manual")
                    await db.commit()
            else:
                await service.end_session(str(session_id), "manual")
                await db.commit()

            return True

    @strawberry.mutation
    async def extend_impersonation(
        self, info: Info, input: ImpersonationExtendInput
    ) -> ImpersonationSessionType:
        """Extend an active impersonation session (signals Temporal workflow)."""
        from app.db.session import async_session_factory
        from app.services.impersonation.service import ImpersonationService

        async with async_session_factory() as db:
            service = ImpersonationService(db)
            session = await service.get_session(str(input.session_id))
            if not session:
                raise ValueError("Session not found")

            await check_graphql_permission(
                info, "impersonation:session:create", str(session.tenant_id)
            )

            # Send Temporal signal
            if session.workflow_id:
                try:
                    from app.core.temporal import get_temporal_client
                    from app.workflows.impersonation import ImpersonationWorkflow

                    client = await get_temporal_client()
                    handle = client.get_workflow_handle(session.workflow_id)
                    await handle.signal(ImpersonationWorkflow.extend_session, input.minutes)
                except Exception:
                    logger.warning(
                        "Failed to send extend signal to workflow %s",
                        session.workflow_id,
                        exc_info=True,
                    )

            # Also extend in DB directly
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
