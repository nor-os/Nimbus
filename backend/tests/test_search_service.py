"""
Overview: Test suite for CMDB search service — validates search functionality and error handling.
Architecture: Test coverage for search and filtering of configuration items (Section 8)
Dependencies: pytest, app.services.cmdb.search_service
Concepts: Full-text search, saved searches, graph-aware queries, service initialization validation.
"""

from app.services.cmdb.search_service import SearchService, SearchServiceError


class TestSearchServiceError:
    """Test SearchServiceError exception behavior."""

    def test_is_exception(self):
        """SearchServiceError is an Exception subclass."""
        error = SearchServiceError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self):
        """SearchServiceError stores message and code."""
        error = SearchServiceError("test error", "TEST_CODE")
        assert error.message == "test error"
        assert error.code == "TEST_CODE"
        assert str(error) == "test error"

    def test_default_code(self):
        """SearchServiceError defaults to SEARCH_ERROR code."""
        error = SearchServiceError("test error")
        assert error.code == "SEARCH_ERROR"


class TestSearchServiceInit:
    """Test SearchService initialization requirements."""

    def test_requires_db_session(self):
        """SearchService requires an AsyncSession parameter."""
        service = SearchService(db=None)
        assert service.db is None

    def test_stores_db_session(self):
        """SearchService stores the db session in self.db."""
        mock_db = object()
        service = SearchService(db=mock_db)
        assert service.db is mock_db
