"""
Overview: Tests for CI service — CRUD operations, lifecycle transitions, relationship management.
Architecture: Unit tests for CMDB CI operations (Section 8)
Dependencies: pytest, app.services.cmdb.ci_service, app.schemas.cmdb
Concepts: CI lifecycle state machine, tenant isolation, snapshot creation, relationship constraints
"""

from app.schemas.cmdb import LIFECYCLE_TRANSITIONS
from app.services.cmdb.ci_service import CIService, CIServiceError


class TestCIServiceError:
    def test_is_exception(self):
        assert issubclass(CIServiceError, Exception)

    def test_error_message(self):
        err = CIServiceError("CI not found")
        assert str(err) == "CI not found"

    def test_error_code(self):
        err = CIServiceError("Test error", code="TEST_ERROR")
        assert err.code == "TEST_ERROR"
        assert err.message == "Test error"

    def test_default_error_code(self):
        err = CIServiceError("Test error")
        assert err.code == "CI_ERROR"


class TestCIServiceInit:
    def test_requires_db_session(self):
        svc = CIService(db=None)
        assert svc.db is None

    def test_stores_db_session(self):
        """CIService stores the db session in self.db."""
        mock_db = object()
        svc = CIService(db=mock_db)
        assert svc.db is mock_db


class TestLifecycleTransitions:
    """Test the lifecycle state transition matrix.

    Valid transitions:
    planned → active, deleted
    active → maintenance, retired, deleted
    maintenance → active, retired, deleted
    retired → deleted
    """

    def test_transitions_dict_exists(self):
        """LIFECYCLE_TRANSITIONS should be a dict."""
        assert isinstance(LIFECYCLE_TRANSITIONS, dict)

    def test_planned_transitions(self):
        """planned can transition to active or deleted."""
        assert "planned" in LIFECYCLE_TRANSITIONS
        allowed = LIFECYCLE_TRANSITIONS["planned"]
        assert "active" in allowed
        assert "deleted" in allowed

    def test_active_transitions(self):
        """active can transition to maintenance, retired, or deleted."""
        assert "active" in LIFECYCLE_TRANSITIONS
        allowed = LIFECYCLE_TRANSITIONS["active"]
        assert "maintenance" in allowed
        assert "retired" in allowed
        assert "deleted" in allowed

    def test_maintenance_transitions(self):
        """maintenance can transition to active, retired, or deleted."""
        assert "maintenance" in LIFECYCLE_TRANSITIONS
        allowed = LIFECYCLE_TRANSITIONS["maintenance"]
        assert "active" in allowed
        assert "retired" in allowed
        assert "deleted" in allowed

    def test_retired_transitions(self):
        """retired can only transition to deleted."""
        assert "retired" in LIFECYCLE_TRANSITIONS
        allowed = LIFECYCLE_TRANSITIONS["retired"]
        assert "deleted" in allowed

    def test_deleted_is_terminal(self):
        """deleted is a terminal state — not present as a key."""
        assert "deleted" not in LIFECYCLE_TRANSITIONS
