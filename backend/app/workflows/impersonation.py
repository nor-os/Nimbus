"""
Overview: Temporal workflow for impersonation lifecycle — uses ApprovalChainWorkflow for approval.
Architecture: Durable impersonation workflow with child approval workflow (Section 9)
Dependencies: temporalio, app.workflows.approval, app.workflows.activities.impersonation
Concepts: Temporal workflow, child workflow, approval gating, session lifecycle
"""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.approval import (
        CreateApprovalRequestInput,
        CreateApprovalRequestResult,
        create_approval_request_activity,
    )
    from app.workflows.activities.impersonation import (
        ActivateInput,
        AuditInput,
        EndInput,
        activate_impersonation_session,
        end_impersonation_session,
        expire_impersonation_session,
        record_impersonation_audit,
        reject_impersonation_session,
    )
    from app.workflows.approval import (
        ApprovalChainInput,
        ApprovalChainResult,
        ApprovalChainWorkflow,
    )


@dataclass
class ImpersonationWorkflowInput:
    session_id: str
    mode: str
    requires_approval: bool
    duration_minutes: int
    tenant_id: str = ""
    approver_ids: list[str] = field(default_factory=list)
    max_duration_minutes: int = 240
    chain_mode: str = "SEQUENTIAL"
    quorum_required: int = 1
    timeout_minutes: int = 1440
    escalation_user_ids: list[str] = field(default_factory=list)
    requester_id: str = ""


@workflow.defn
class ImpersonationWorkflow:
    def __init__(self) -> None:
        self._session_ended: bool = False
        self._extend_minutes: int = 0
        self._access_token: str | None = None
        self._approval_request_id: str | None = None

    @workflow.signal
    async def end_session(self) -> None:
        self._session_ended = True

    @workflow.signal
    async def extend_session(self, minutes: int) -> None:
        self._extend_minutes += minutes

    @workflow.query
    def get_status(self) -> dict:
        return {
            "session_ended": self._session_ended,
            "access_token": self._access_token,
            "approval_request_id": self._approval_request_id,
        }

    @workflow.run
    async def run(self, input: ImpersonationWorkflowInput) -> dict:
        # 1. Audit: request created
        await workflow.execute_activity(
            record_impersonation_audit,
            AuditInput(
                session_id=input.session_id,
                action="request_created",
                details={"mode": input.mode, "requires_approval": input.requires_approval},
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 2. Approval gate — use ApprovalChainWorkflow as child workflow
        if input.requires_approval:
            # Create approval request via activity
            approval_result: CreateApprovalRequestResult = await workflow.execute_activity(
                create_approval_request_activity,
                CreateApprovalRequestInput(
                    tenant_id=input.tenant_id,
                    requester_id=input.requester_id,
                    operation_type=f"impersonation.{input.mode.lower()}",
                    title=f"Impersonation request ({input.mode})",
                    description=f"Session {input.session_id} requires approval",
                    context={"session_id": input.session_id, "mode": input.mode},
                    parent_workflow_id=f"impersonation-{input.session_id}",
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            self._approval_request_id = approval_result.request_id

            # Determine approver_ids and chain params from the approval request
            approver_ids = approval_result.approver_ids or input.approver_ids
            chain_mode = approval_result.chain_mode or input.chain_mode
            quorum_required = approval_result.quorum_required or input.quorum_required
            timeout_minutes = approval_result.timeout_minutes or input.timeout_minutes
            escalation_user_ids = approval_result.escalation_user_ids or input.escalation_user_ids

            # Start ApprovalChainWorkflow as CHILD WORKFLOW
            chain_result: ApprovalChainResult = await workflow.execute_child_workflow(
                ApprovalChainWorkflow.run,
                ApprovalChainInput(
                    request_id=approval_result.request_id,
                    tenant_id=input.tenant_id,
                    requester_id=input.requester_id,
                    approver_ids=approver_ids,
                    chain_mode=chain_mode,
                    quorum_required=quorum_required,
                    timeout_minutes=timeout_minutes,
                    escalation_user_ids=escalation_user_ids,
                    title=f"Impersonation request ({input.mode})",
                    description=f"Session {input.session_id} requires approval",
                ),
                id=f"approval-{approval_result.request_id}",
            )

            if not chain_result.approved:
                # Handle rejection/expiry
                if chain_result.status == "REJECTED":
                    await workflow.execute_activity(
                        reject_impersonation_session,
                        input.session_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    await workflow.execute_activity(
                        record_impersonation_audit,
                        AuditInput(
                            session_id=input.session_id,
                            action="rejected",
                            details={"approval_status": chain_result.status},
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                else:
                    await workflow.execute_activity(
                        expire_impersonation_session,
                        input.session_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    await workflow.execute_activity(
                        record_impersonation_audit,
                        AuditInput(
                            session_id=input.session_id,
                            action="approval_timeout",
                            details={"approval_status": chain_result.status},
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                    )

                return {
                    "status": chain_result.status.lower(),
                    "reason": chain_result.status,
                }

        # 3. Activate the session
        result = await workflow.execute_activity(
            activate_impersonation_session,
            ActivateInput(
                session_id=input.session_id,
                mode=input.mode,
                duration_minutes=input.duration_minutes,
            ),
            start_to_close_timeout=timedelta(seconds=60),
        )

        if not result.success:
            return {"status": "failed", "error": result.error}

        if result.access_token:
            self._access_token = result.access_token

        # 4. Audit: session activated
        await workflow.execute_activity(
            record_impersonation_audit,
            AuditInput(
                session_id=input.session_id,
                action="session_activated",
                details={"mode": input.mode, "duration_minutes": input.duration_minutes},
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 5. Wait for session end or expiry
        total_elapsed = 0
        remaining_minutes = input.duration_minutes
        while remaining_minutes > 0 and not self._session_ended:
            try:
                await workflow.wait_condition(
                    lambda: self._session_ended or self._extend_minutes > 0,
                    timeout=timedelta(minutes=remaining_minutes),
                )
                # Handle extension
                if self._extend_minutes > 0 and not self._session_ended:
                    total_elapsed += remaining_minutes
                    budget_left = input.max_duration_minutes - total_elapsed
                    remaining_minutes = min(self._extend_minutes, budget_left)
                    self._extend_minutes = 0
                    if remaining_minutes <= 0:
                        break
            except TimeoutError:
                # Session expired naturally
                break

        # 6. End session
        await workflow.execute_activity(
            end_impersonation_session,
            EndInput(
                session_id=input.session_id,
                reason="manual" if self._session_ended else "expired",
            ),
            start_to_close_timeout=timedelta(seconds=60),
        )

        # 7. Audit: session ended
        await workflow.execute_activity(
            record_impersonation_audit,
            AuditInput(
                session_id=input.session_id,
                action="session_ended",
                details={
                    "reason": "manual" if self._session_ended else "expired",
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return {
            "status": "ended",
            "reason": "manual" if self._session_ended else "expired",
        }
