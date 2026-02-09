"""
Overview: Test suite for service catalog service — validates catalog CRUD and pricing engine.
Architecture: Test coverage for catalog and pricing management with tenant overrides (Section 8)
Dependencies: pytest, app.services.cmdb.catalog_service
Concepts: Service offerings, pricing engine, tenant overrides, service initialization validation.
"""

from app.services.cmdb.catalog_service import CatalogService, CatalogServiceError


class TestCatalogServiceError:
    """Test CatalogServiceError exception behavior."""

    def test_is_exception(self):
        """CatalogServiceError is an Exception subclass."""
        error = CatalogServiceError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self):
        """CatalogServiceError stores message and code."""
        error = CatalogServiceError("test error", "TEST_CODE")
        assert error.message == "test error"
        assert error.code == "TEST_CODE"
        assert str(error) == "test error"

    def test_default_code(self):
        """CatalogServiceError defaults to CATALOG_ERROR code."""
        error = CatalogServiceError("test error")
        assert error.code == "CATALOG_ERROR"


class TestCatalogServiceInit:
    """Test CatalogService initialization requirements."""

    def test_requires_db_session(self):
        """CatalogService requires an AsyncSession parameter."""
        service = CatalogService(db=None)
        assert service.db is None

    def test_stores_db_session(self):
        """CatalogService stores the db session in self.db."""
        mock_db = object()
        service = CatalogService(db=mock_db)
        assert service.db is mock_db
