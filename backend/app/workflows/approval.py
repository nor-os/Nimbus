"""
Overview: Temporal workflow for reusable approval chains — sequential, parallel, and quorum modes.
Architecture: Durable approval chain workflow, child of parent operations (Section 9)
Dependencies: temporalio, app.workflows.activities.approval
Concepts: Temporal workflow, child workflow, approval chains, signals, quorum
"""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.approval import (
        ApprovalAuditInput,
        ApprovalNotifyInput,
        ExpireInput,
        ResolveInput,
        expire_approval_steps,
        record_approval_audit,
        resolve_approval_request,
        send_approval_notification,
    )


@dataclass
class ApprovalChainInput:
    request_id: str
    tenant_id: str
    requester_id: str
    approver_ids: list[str]
    chain_mode: str  # "SEQUENTIAL" | "PARALLEL" | "QUORUM"
    quorum_required: int = 1
    timeout_minutes: int = 1440
    escalation_user_ids: list[str] = field(default_factory=list)
    title: str = ""
    description: str = ""


@dataclass
class ApprovalChainResult:
    approved: bool
    status: str  # "APPROVED" | "REJECTED" | "EXPIRED" | "CANCELLED"
    steps: list[dict] = field(default_factory=list)


@dataclass
class _StepDecision:
    step_id: str
    decision: str  # "approve" | "reject"
    reason: str | None = None


@dataclass
class _DelegateAction:
    step_id: str
    delegate_to_id: str


@workflow.defn
class ApprovalChainWorkflow:
    def __init__(self) -> None:
        self._decisions: list[_StepDecision] = []
        self._delegates: list[_DelegateAction] = []
        self._cancelled: bool = False
        self._step_statuses: dict[str, str] = {}  # step_id -> status

    @workflow.signal
    async def submit_decision(
        self, step_id: str, decision: str, reason: str | None = None
    ) -> None:
        self._decisions.append(_StepDecision(step_id, decision, reason))

    @workflow.signal
    async def delegate(self, step_id: str, delegate_to_id: str) -> None:
        self._delegates.append(_DelegateAction(step_id, delegate_to_id))

    @workflow.signal
    async def cancel(self) -> None:
        self._cancelled = True

    @workflow.query
    def get_status(self) -> dict:
        return {
            "cancelled": self._cancelled,
            "step_statuses": self._step_statuses,
            "pending_decisions": len(self._decisions),
        }

    @workflow.run
    async def run(self, input: ApprovalChainInput) -> ApprovalChainResult:
        # Audit: approval requested
        await workflow.execute_activity(
            record_approval_audit,
            ApprovalAuditInput(
                request_id=input.request_id,
                tenant_id=input.tenant_id,
                actor_id=input.requester_id,
                action="requested",
                details={
                    "chain_mode": input.chain_mode,
                    "approver_count": len(input.approver_ids),
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        if input.chain_mode == "SEQUENTIAL":
            result = await self._run_sequential(input)
        elif input.chain_mode == "PARALLEL":
            result = await self._run_parallel(input)
        elif input.chain_mode == "QUORUM":
            result = await self._run_quorum(input)
        else:
            result = await self._run_sequential(input)

        # Resolve the approval request
        await workflow.execute_activity(
            resolve_approval_request,
            ResolveInput(
                request_id=input.request_id,
                tenant_id=input.tenant_id,
                status=result.status,
                requester_id=input.requester_id,
                title=input.title,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return result

    async def _run_sequential(self, input: ApprovalChainInput) -> ApprovalChainResult:
        """Process approvers one at a time, in order."""
        step_results: list[dict] = []

        for i, approver_id in enumerate(input.approver_ids):
            if self._cancelled:
                return ApprovalChainResult(
                    approved=False, status="CANCELLED", steps=step_results
                )

            # Notify this approver
            await workflow.execute_activity(
                send_approval_notification,
                ApprovalNotifyInput(
                    request_id=input.request_id,
                    approver_ids=[approver_id],
                    title=input.title,
                    description=input.description,
                    tenant_id=input.tenant_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Wait for decision from this approver
            decision = await self._wait_for_decision(
                input, approver_id, input.timeout_minutes
            )

            if decision is None:
                # Timed out
                await self._handle_timeout(input)
                step_results.append(
                    {"approver_id": approver_id, "status": "EXPIRED"}
                )
                return ApprovalChainResult(
                    approved=False, status="EXPIRED", steps=step_results
                )

            step_results.append({
                "approver_id": approver_id,
                "status": decision.decision.upper() + "D",
                "reason": decision.reason,
            })

            # Audit the decision
            await workflow.execute_activity(
                record_approval_audit,
                ApprovalAuditInput(
                    request_id=input.request_id,
                    tenant_id=input.tenant_id,
                    actor_id=approver_id,
                    action=decision.decision + "d",
                    details={"reason": decision.reason, "step": i},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            if decision.decision == "reject":
                return ApprovalChainResult(
                    approved=False, status="REJECTED", steps=step_results
                )

        return ApprovalChainResult(
            approved=True, status="APPROVED", steps=step_results
        )

    async def _run_parallel(self, input: ApprovalChainInput) -> ApprovalChainResult:
        """Notify all approvers simultaneously, wait for all to decide."""
        # Notify all approvers
        await workflow.execute_activity(
            send_approval_notification,
            ApprovalNotifyInput(
                request_id=input.request_id,
                approver_ids=input.approver_ids,
                title=input.title,
                description=input.description,
                tenant_id=input.tenant_id,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return await self._collect_decisions(
            input,
            required_approvals=len(input.approver_ids),
            mode="PARALLEL",
        )

    async def _run_quorum(self, input: ApprovalChainInput) -> ApprovalChainResult:
        """Notify all approvers, wait for quorum count to approve."""
        # Notify all approvers
        await workflow.execute_activity(
            send_approval_notification,
            ApprovalNotifyInput(
                request_id=input.request_id,
                approver_ids=input.approver_ids,
                title=input.title,
                description=input.description,
                tenant_id=input.tenant_id,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return await self._collect_decisions(
            input,
            required_approvals=input.quorum_required,
            mode="QUORUM",
        )

    async def _collect_decisions(
        self,
        input: ApprovalChainInput,
        required_approvals: int,
        mode: str,
    ) -> ApprovalChainResult:
        """Collect decisions until chain resolves or times out."""
        step_results: list[dict] = []
        approve_count = 0
        reject_count = 0
        total = len(input.approver_ids)
        processed_count = 0

        try:
            await workflow.wait_condition(
                lambda: (
                    self._cancelled
                    or len(self._decisions) > processed_count
                ),
                timeout=timedelta(minutes=input.timeout_minutes),
            )
        except TimeoutError:
            await self._handle_timeout(input)
            return ApprovalChainResult(
                approved=False, status="EXPIRED", steps=step_results
            )

        # Process decisions as they come in
        while True:
            if self._cancelled:
                return ApprovalChainResult(
                    approved=False, status="CANCELLED", steps=step_results
                )

            # Process any new decisions
            while processed_count < len(self._decisions):
                d = self._decisions[processed_count]
                processed_count += 1

                if d.decision == "approve":
                    approve_count += 1
                    status_str = "APPROVED"
                else:
                    reject_count += 1
                    status_str = "REJECTED"

                self._step_statuses[d.step_id] = status_str
                step_results.append({
                    "step_id": d.step_id,
                    "status": status_str,
                    "reason": d.reason,
                })

                # Audit
                await workflow.execute_activity(
                    record_approval_audit,
                    ApprovalAuditInput(
                        request_id=input.request_id,
                        tenant_id=input.tenant_id,
                        actor_id="system",
                        action=d.decision + "d",
                        details={
                            "step_id": d.step_id,
                            "reason": d.reason,
                            "approve_count": approve_count,
                            "reject_count": reject_count,
                        },
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                )

                # Check resolution
                if approve_count >= required_approvals:
                    return ApprovalChainResult(
                        approved=True, status="APPROVED", steps=step_results
                    )

                if mode == "PARALLEL" and reject_count > 0:
                    return ApprovalChainResult(
                        approved=False, status="REJECTED", steps=step_results
                    )

                if mode == "QUORUM":
                    remaining = total - approve_count - reject_count
                    if approve_count + remaining < required_approvals:
                        return ApprovalChainResult(
                            approved=False, status="REJECTED", steps=step_results
                        )

            # Wait for more decisions or cancellation
            try:
                await workflow.wait_condition(
                    lambda _pc=processed_count: (
                        self._cancelled
                        or len(self._decisions) > _pc
                    ),
                    timeout=timedelta(minutes=input.timeout_minutes),
                )
            except TimeoutError:
                await self._handle_timeout(input)
                return ApprovalChainResult(
                    approved=False, status="EXPIRED", steps=step_results
                )

    async def _wait_for_decision(
        self,
        input: ApprovalChainInput,
        approver_id: str,
        timeout_minutes: int,
    ) -> _StepDecision | None:
        """Wait for a single decision, handling delegation and cancellation."""
        initial_count = len(self._decisions)

        try:
            await workflow.wait_condition(
                lambda: (
                    self._cancelled
                    or len(self._decisions) > initial_count
                ),
                timeout=timedelta(minutes=timeout_minutes),
            )
        except TimeoutError:
            return None

        if self._cancelled:
            return None

        # Return the latest decision
        if len(self._decisions) > initial_count:
            return self._decisions[-1]

        return None

    async def _handle_timeout(self, input: ApprovalChainInput) -> None:
        """Handle timeout: expire steps, notify escalation users."""
        await workflow.execute_activity(
            expire_approval_steps,
            ExpireInput(
                request_id=input.request_id,
                tenant_id=input.tenant_id,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Audit the timeout
        await workflow.execute_activity(
            record_approval_audit,
            ApprovalAuditInput(
                request_id=input.request_id,
                tenant_id=input.tenant_id,
                actor_id="system",
                action="expired",
                details={"timeout_minutes": input.timeout_minutes},
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Notify escalation users if configured
        if input.escalation_user_ids:
            await workflow.execute_activity(
                send_approval_notification,
                ApprovalNotifyInput(
                    request_id=input.request_id,
                    approver_ids=input.escalation_user_ids,
                    title=f"[ESCALATION] {input.title}",
                    description=f"Approval timed out after {input.timeout_minutes} minutes.",
                    tenant_id=input.tenant_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
