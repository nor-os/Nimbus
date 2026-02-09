"""
Overview: Tests for approval data models — enums, field constraints, model relationships.
Architecture: Unit tests for approval data layer (Section 4)
Dependencies: pytest, app.models.approval_*
Concepts: Model validation, enum values, field constraints, immutable records
"""

import uuid

from app.models.approval_policy import ApprovalChainMode, ApprovalPolicy
from app.models.approval_request import ApprovalRequest, ApprovalRequestStatus
from app.models.approval_step import ApprovalStep, ApprovalStepStatus


class TestApprovalEnums:
    """Test all approval-related enum values."""

    def test_chain_mode_values(self):
        assert set(ApprovalChainMode) == {
            ApprovalChainMode.SEQUENTIAL,
            ApprovalChainMode.PARALLEL,
            ApprovalChainMode.QUORUM,
        }

    def test_request_status_values(self):
        assert set(ApprovalRequestStatus) == {
            ApprovalRequestStatus.PENDING,
            ApprovalRequestStatus.APPROVED,
            ApprovalRequestStatus.REJECTED,
            ApprovalRequestStatus.EXPIRED,
            ApprovalRequestStatus.CANCELLED,
        }

    def test_step_status_values(self):
        assert set(ApprovalStepStatus) == {
            ApprovalStepStatus.PENDING,
            ApprovalStepStatus.APPROVED,
            ApprovalStepStatus.REJECTED,
            ApprovalStepStatus.DELEGATED,
            ApprovalStepStatus.SKIPPED,
            ApprovalStepStatus.EXPIRED,
        }

    def test_enums_are_str_enums(self):
        assert isinstance(ApprovalChainMode.SEQUENTIAL, str)
        assert isinstance(ApprovalRequestStatus.PENDING, str)
        assert isinstance(ApprovalStepStatus.PENDING, str)

    def test_chain_mode_string_values(self):
        assert ApprovalChainMode.SEQUENTIAL.value == "SEQUENTIAL"
        assert ApprovalChainMode.PARALLEL.value == "PARALLEL"
        assert ApprovalChainMode.QUORUM.value == "QUORUM"


class TestApprovalPolicyModel:
    """Test ApprovalPolicy model instantiation."""

    def test_policy_creation(self):
        tenant_id = uuid.uuid4()
        p = ApprovalPolicy(
            tenant_id=tenant_id,
            operation_type="impersonation.standard",
            chain_mode=ApprovalChainMode.SEQUENTIAL,
            quorum_required=1,
            timeout_minutes=1440,
            is_active=True,
        )
        assert p.tenant_id == tenant_id
        assert p.operation_type == "impersonation.standard"
        assert p.chain_mode == ApprovalChainMode.SEQUENTIAL
        assert p.quorum_required == 1
        assert p.timeout_minutes == 1440
        assert p.is_active is True

    def test_policy_with_approver_config(self):
        p = ApprovalPolicy(
            tenant_id=uuid.uuid4(),
            operation_type="deployment",
            chain_mode=ApprovalChainMode.QUORUM,
            quorum_required=2,
            approver_role_names=["tenant_admin", "security_officer"],
            approver_user_ids=[str(uuid.uuid4())],
            escalation_user_ids=[str(uuid.uuid4())],
        )
        assert p.chain_mode == ApprovalChainMode.QUORUM
        assert p.quorum_required == 2
        assert len(p.approver_role_names) == 2
        assert len(p.approver_user_ids) == 1
        assert len(p.escalation_user_ids) == 1

    def test_policy_tablename(self):
        assert ApprovalPolicy.__tablename__ == "approval_policies"

    def test_policy_has_soft_delete(self):
        """ApprovalPolicy uses SoftDeleteMixin."""
        columns = {col.name for col in ApprovalPolicy.__table__.columns}
        assert "deleted_at" in columns


class TestApprovalRequestModel:
    """Test ApprovalRequest model instantiation."""

    def test_request_creation(self):
        tenant_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        r = ApprovalRequest(
            tenant_id=tenant_id,
            operation_type="impersonation.standard",
            requester_id=requester_id,
            chain_mode="SEQUENTIAL",
            quorum_required=1,
            status=ApprovalRequestStatus.PENDING,
            title="Test approval",
            description="Testing approval request",
            context={"session_id": "abc-123"},
        )
        assert r.tenant_id == tenant_id
        assert r.requester_id == requester_id
        assert r.status == ApprovalRequestStatus.PENDING
        assert r.context == {"session_id": "abc-123"}

    def test_request_tablename(self):
        assert ApprovalRequest.__tablename__ == "approval_requests"

    def test_request_no_soft_delete(self):
        """ApprovalRequest is immutable — no SoftDeleteMixin."""
        columns = {col.name for col in ApprovalRequest.__table__.columns}
        assert "deleted_at" not in columns


class TestApprovalStepModel:
    """Test ApprovalStep model instantiation."""

    def test_step_creation(self):
        tenant_id = uuid.uuid4()
        request_id = uuid.uuid4()
        approver_id = uuid.uuid4()
        s = ApprovalStep(
            tenant_id=tenant_id,
            approval_request_id=request_id,
            step_order=0,
            approver_id=approver_id,
            status=ApprovalStepStatus.PENDING,
        )
        assert s.tenant_id == tenant_id
        assert s.approval_request_id == request_id
        assert s.step_order == 0
        assert s.approver_id == approver_id
        assert s.status == ApprovalStepStatus.PENDING

    def test_step_with_delegation(self):
        delegate_id = uuid.uuid4()
        s = ApprovalStep(
            tenant_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
            step_order=0,
            approver_id=uuid.uuid4(),
            status=ApprovalStepStatus.DELEGATED,
            delegate_to_id=delegate_id,
            reason="Delegated to alternate approver",
        )
        assert s.status == ApprovalStepStatus.DELEGATED
        assert s.delegate_to_id == delegate_id
        assert "Delegated" in s.reason

    def test_step_tablename(self):
        assert ApprovalStep.__tablename__ == "approval_steps"

    def test_step_no_soft_delete(self):
        """ApprovalStep is immutable — no SoftDeleteMixin."""
        columns = {col.name for col in ApprovalStep.__table__.columns}
        assert "deleted_at" not in columns
