"""
Overview: Tests for CI class service — class CRUD, system protection, attribute definitions.
Architecture: Unit tests for CMDB class management (Section 8)
Dependencies: pytest, app.services.cmdb.class_service
Concepts: CI class lifecycle, system class protection, custom attribute management
"""

from app.services.cmdb.class_service import ClassService, ClassServiceError


class TestClassServiceError:
    def test_is_exception(self):
        assert issubclass(ClassServiceError, Exception)

    def test_error_message(self):
        err = ClassServiceError("System class cannot be deleted")
        assert str(err) == "System class cannot be deleted"

    def test_error_code(self):
        err = ClassServiceError("Test error", code="TEST_ERROR")
        assert err.code == "TEST_ERROR"
        assert err.message == "Test error"

    def test_default_error_code(self):
        err = ClassServiceError("Test error")
        assert err.code == "CLASS_ERROR"


class TestClassServiceInit:
    def test_requires_db_session(self):
        """ClassService requires an AsyncSession parameter."""
        svc = ClassService(db=None)
        assert svc.db is None

    def test_stores_db_session(self):
        """ClassService stores the db session in self.db."""
        mock_db = object()
        svc = ClassService(db=mock_db)
        assert svc.db is mock_db
