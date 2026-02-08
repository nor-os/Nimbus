"""
Overview: Temporal workflow for impersonation lifecycle — approval, activation, expiry.
Architecture: Durable impersonation workflow with signals for approval and session control (Section 9)
Dependencies: temporalio, app.workflows.activities.impersonation
Concepts: Temporal workflow, signals, approval gating, session lifecycle
"""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.impersonation import (
        ActivateInput,
        AuditInput,
        EndInput,
        NotifyInput,
        activate_impersonation_session,
        end_impersonation_session,
        expire_impersonation_session,
        notify_approver,
        record_impersonation_audit,
        reject_impersonation_session,
    )


@dataclass
class ImpersonationWorkflowInput:
    session_id: str
    mode: str
    requires_approval: bool
    duration_minutes: int
    approver_ids: list[str] = field(default_factory=list)
    max_duration_minutes: int = 240


@workflow.defn
class ImpersonationWorkflow:
    def __init__(self) -> None:
        self._approval_decision: str | None = None
        self._approval_reason: str | None = None
        self._session_ended: bool = False
        self._extend_minutes: int = 0
        self._access_token: str | None = None

    @workflow.signal
    async def approval_decision(self, decision: str, reason: str | None = None) -> None:
        self._approval_decision = decision
        self._approval_reason = reason

    @workflow.signal
    async def end_session(self) -> None:
        self._session_ended = True

    @workflow.signal
    async def extend_session(self, minutes: int) -> None:
        self._extend_minutes += minutes

    @workflow.query
    def get_status(self) -> dict:
        return {
            "approval_decision": self._approval_decision,
            "session_ended": self._session_ended,
            "access_token": self._access_token,
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

        # 2. Approval gate
        if input.requires_approval:
            # Notify approvers
            await workflow.execute_activity(
                notify_approver,
                NotifyInput(
                    session_id=input.session_id,
                    approver_ids=input.approver_ids or None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Wait for approval decision (24h timeout)
            try:
                await workflow.wait_condition(
                    lambda: self._approval_decision is not None,
                    timeout=timedelta(hours=24),
                )
            except TimeoutError:
                # Approval timeout — expire the session
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
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return {"status": "expired", "reason": "approval_timeout"}

            # Handle rejection
            if self._approval_decision == "reject":
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
                        details={"reason": self._approval_reason},
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return {"status": "rejected", "reason": self._approval_reason}

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
