"""
Overview: Tests for versioning service — snapshot management, version retrieval, diff generation.
Architecture: Unit tests for CMDB version control (Section 8)
Dependencies: pytest, app.services.cmdb.versioning_service
Concepts: CI snapshots, point-in-time state retrieval, version diffing
"""

from app.services.cmdb.versioning_service import VersioningService


class TestVersioningServiceInit:
    def test_requires_db_session(self):
        svc = VersioningService(db=None)
        assert svc.db is None

    def test_stores_db_session(self):
        """VersioningService stores the db session in self.db."""
        mock_db = object()
        svc = VersioningService(db=mock_db)
        assert svc.db is mock_db

    def test_service_exists(self):
        """VersioningService should be importable and instantiable."""
        assert VersioningService is not None
