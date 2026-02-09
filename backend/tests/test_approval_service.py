"""
Overview: Tests for ApprovalService — resolution logic for sequential, parallel, quorum modes.
Architecture: Unit tests for approval service layer (Section 5)
Dependencies: pytest, app.services.approval, app.models.approval_*
Concepts: Chain resolution, quorum logic, delegation, cancellation
"""

import uuid
from unittest.mock import MagicMock

from app.models.approval_request import ApprovalRequest, ApprovalRequestStatus
from app.models.approval_step import ApprovalStep, ApprovalStepStatus
from app.services.approval.service import ApprovalService


def _make_step(status: ApprovalStepStatus, step_order: int = 0) -> ApprovalStep:
    """Create a minimal ApprovalStep for testing resolution logic."""
    step = ApprovalStep(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        approval_request_id=uuid.uuid4(),
        step_order=step_order,
        approver_id=uuid.uuid4(),
        status=status,
    )
    return step


def _make_request(
    chain_mode: str,
    quorum_required: int,
    steps: list[ApprovalStep],
) -> ApprovalRequest:
    """Create a minimal ApprovalRequest for testing resolution logic."""
    request = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        operation_type="test",
        requester_id=uuid.uuid4(),
        chain_mode=chain_mode,
        quorum_required=quorum_required,
        status=ApprovalRequestStatus.PENDING,
        title="Test",
    )
    request.steps = steps
    return request


class TestSequentialResolution:
    """Test check_resolution for SEQUENTIAL mode."""

    def setup_method(self):
        self.service = ApprovalService(MagicMock())

    def test_all_approved(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.APPROVED, 1),
        ]
        request = _make_request("SEQUENTIAL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.APPROVED

    def test_any_rejected(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.REJECTED, 1),
        ]
        request = _make_request("SEQUENTIAL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.REJECTED

    def test_still_pending(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.PENDING, 1),
        ]
        request = _make_request("SEQUENTIAL", 1, steps)
        result = self.service.check_resolution(request)
        assert result is None

    def test_expired_no_pending(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.EXPIRED, 1),
        ]
        request = _make_request("SEQUENTIAL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.EXPIRED

    def test_delegated_steps_ignored(self):
        """Delegated steps should be excluded from resolution counting."""
        steps = [
            _make_step(ApprovalStepStatus.DELEGATED, 0),
            _make_step(ApprovalStepStatus.APPROVED, 0),
        ]
        request = _make_request("SEQUENTIAL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.APPROVED


class TestParallelResolution:
    """Test check_resolution for PARALLEL mode."""

    def setup_method(self):
        self.service = ApprovalService(MagicMock())

    def test_all_approved(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.APPROVED, 0),
        ]
        request = _make_request("PARALLEL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.APPROVED

    def test_any_rejected(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.REJECTED, 0),
            _make_step(ApprovalStepStatus.PENDING, 0),
        ]
        request = _make_request("PARALLEL", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.REJECTED

    def test_still_pending(self):
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.PENDING, 0),
        ]
        request = _make_request("PARALLEL", 1, steps)
        result = self.service.check_resolution(request)
        assert result is None


class TestQuorumResolution:
    """Test check_resolution for QUORUM mode."""

    def setup_method(self):
        self.service = ApprovalService(MagicMock())

    def test_quorum_met(self):
        """2-of-3 quorum met when 2 approved."""
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.PENDING, 0),
        ]
        request = _make_request("QUORUM", 2, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.APPROVED

    def test_quorum_impossible(self):
        """2-of-3 impossible when 2 rejected."""
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.REJECTED, 0),
            _make_step(ApprovalStepStatus.REJECTED, 0),
        ]
        request = _make_request("QUORUM", 2, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.REJECTED

    def test_quorum_still_possible(self):
        """2-of-3 with 1 approved, 1 rejected, 1 pending — still possible."""
        steps = [
            _make_step(ApprovalStepStatus.APPROVED, 0),
            _make_step(ApprovalStepStatus.REJECTED, 0),
            _make_step(ApprovalStepStatus.PENDING, 0),
        ]
        request = _make_request("QUORUM", 2, steps)
        result = self.service.check_resolution(request)
        assert result is None

    def test_quorum_all_expired(self):
        steps = [
            _make_step(ApprovalStepStatus.EXPIRED, 0),
            _make_step(ApprovalStepStatus.EXPIRED, 0),
            _make_step(ApprovalStepStatus.EXPIRED, 0),
        ]
        request = _make_request("QUORUM", 2, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.EXPIRED

    def test_quorum_1_of_1(self):
        """Simple 1-of-1 quorum."""
        steps = [_make_step(ApprovalStepStatus.APPROVED, 0)]
        request = _make_request("QUORUM", 1, steps)
        result = self.service.check_resolution(request)
        assert result == ApprovalRequestStatus.APPROVED


class TestEmptySteps:
    """Test edge cases with empty steps."""

    def setup_method(self):
        self.service = ApprovalService(MagicMock())

    def test_no_steps(self):
        request = _make_request("SEQUENTIAL", 1, [])
        result = self.service.check_resolution(request)
        assert result is None

    def test_none_steps(self):
        """check_resolution handles steps=None gracefully (e.g. from raw dict)."""
        request = _make_request("SEQUENTIAL", 1, [])
        # Bypass SQLAlchemy by setting on __dict__ directly
        request.__dict__["steps"] = None
        result = self.service.check_resolution(request)
        assert result is None
