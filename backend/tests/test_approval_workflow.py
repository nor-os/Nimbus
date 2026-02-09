"""
Overview: Tests for approval workflow dataclasses and activity input/output structures.
Architecture: Unit tests for approval workflow layer (Section 9)
Dependencies: pytest, app.workflows.approval, app.workflows.activities.approval
Concepts: Dataclass validation, workflow input/output, activity structures
"""

from app.workflows.activities.approval import (
    ApprovalAuditInput,
    ApprovalNotifyInput,
    CreateApprovalRequestInput,
    CreateApprovalRequestResult,
    ExpireInput,
    ResolveInput,
)
from app.workflows.approval import ApprovalChainInput, ApprovalChainResult
from app.workflows.impersonation import ImpersonationWorkflowInput


class TestApprovalChainInput:
    """Test ApprovalChainInput dataclass."""

    def test_creation_minimal(self):
        inp = ApprovalChainInput(
            request_id="req-123",
            tenant_id="tenant-abc",
            requester_id="user-456",
            approver_ids=["user-1", "user-2"],
            chain_mode="SEQUENTIAL",
        )
        assert inp.request_id == "req-123"
        assert inp.chain_mode == "SEQUENTIAL"
        assert len(inp.approver_ids) == 2
        assert inp.quorum_required == 1
        assert inp.timeout_minutes == 1440

    def test_creation_quorum(self):
        inp = ApprovalChainInput(
            request_id="req-123",
            tenant_id="tenant-abc",
            requester_id="user-456",
            approver_ids=["u1", "u2", "u3"],
            chain_mode="QUORUM",
            quorum_required=2,
            timeout_minutes=60,
            escalation_user_ids=["admin-1"],
        )
        assert inp.chain_mode == "QUORUM"
        assert inp.quorum_required == 2
        assert inp.timeout_minutes == 60
        assert inp.escalation_user_ids == ["admin-1"]

    def test_defaults(self):
        inp = ApprovalChainInput(
            request_id="r",
            tenant_id="t",
            requester_id="u",
            approver_ids=[],
            chain_mode="PARALLEL",
        )
        assert inp.quorum_required == 1
        assert inp.timeout_minutes == 1440
        assert inp.escalation_user_ids == []
        assert inp.title == ""
        assert inp.description == ""


class TestApprovalChainResult:
    """Test ApprovalChainResult dataclass."""

    def test_approved_result(self):
        result = ApprovalChainResult(
            approved=True,
            status="APPROVED",
            steps=[{"approver_id": "u1", "status": "APPROVED"}],
        )
        assert result.approved is True
        assert result.status == "APPROVED"
        assert len(result.steps) == 1

    def test_rejected_result(self):
        result = ApprovalChainResult(
            approved=False,
            status="REJECTED",
        )
        assert result.approved is False
        assert result.status == "REJECTED"
        assert result.steps == []


class TestActivityDataclasses:
    """Test activity input/output dataclass structures."""

    def test_approval_notify_input(self):
        inp = ApprovalNotifyInput(
            request_id="req-1",
            approver_ids=["u1", "u2"],
            title="Approval needed",
            description="Please review",
            tenant_id="t1",
        )
        assert inp.request_id == "req-1"
        assert len(inp.approver_ids) == 2

    def test_approval_audit_input(self):
        inp = ApprovalAuditInput(
            request_id="req-1",
            tenant_id="t1",
            actor_id="u1",
            action="approved",
            details={"reason": "LGTM"},
        )
        assert inp.action == "approved"
        assert inp.details == {"reason": "LGTM"}

    def test_approval_audit_input_defaults(self):
        inp = ApprovalAuditInput(
            request_id="req-1",
            tenant_id="t1",
            actor_id="u1",
            action="requested",
        )
        assert inp.details is None

    def test_resolve_input(self):
        inp = ResolveInput(
            request_id="req-1",
            tenant_id="t1",
            status="APPROVED",
            requester_id="u1",
            title="Test",
        )
        assert inp.status == "APPROVED"
        assert inp.requester_id == "u1"

    def test_expire_input(self):
        inp = ExpireInput(request_id="req-1", tenant_id="t1")
        assert inp.request_id == "req-1"

    def test_create_approval_request_input(self):
        inp = CreateApprovalRequestInput(
            tenant_id="t1",
            requester_id="u1",
            operation_type="impersonation.standard",
            title="Impersonation request",
            description="Session needs approval",
            context={"session_id": "s1"},
            parent_workflow_id="impersonation-s1",
        )
        assert inp.operation_type == "impersonation.standard"
        assert inp.context == {"session_id": "s1"}

    def test_create_approval_request_result(self):
        result = CreateApprovalRequestResult(
            request_id="req-1",
            approver_ids=["u1", "u2"],
            chain_mode="PARALLEL",
            quorum_required=1,
            timeout_minutes=60,
            escalation_user_ids=["admin-1"],
        )
        assert result.request_id == "req-1"
        assert result.chain_mode == "PARALLEL"
        assert result.timeout_minutes == 60


class TestImpersonationWorkflowInput:
    """Test refactored ImpersonationWorkflowInput with approval fields."""

    def test_new_fields(self):
        inp = ImpersonationWorkflowInput(
            session_id="s1",
            mode="STANDARD",
            requires_approval=True,
            duration_minutes=30,
            tenant_id="t1",
            requester_id="u1",
            chain_mode="QUORUM",
            quorum_required=2,
            timeout_minutes=60,
            escalation_user_ids=["admin-1"],
        )
        assert inp.tenant_id == "t1"
        assert inp.requester_id == "u1"
        assert inp.chain_mode == "QUORUM"
        assert inp.quorum_required == 2
        assert inp.timeout_minutes == 60
        assert inp.escalation_user_ids == ["admin-1"]

    def test_backwards_compatible_defaults(self):
        """Original fields still work with defaults for new fields."""
        inp = ImpersonationWorkflowInput(
            session_id="s1",
            mode="STANDARD",
            requires_approval=False,
            duration_minutes=30,
        )
        assert inp.tenant_id == ""
        assert inp.chain_mode == "SEQUENTIAL"
        assert inp.quorum_required == 1
        assert inp.timeout_minutes == 1440
        assert inp.escalation_user_ids == []
        assert inp.requester_id == ""
