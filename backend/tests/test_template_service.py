"""
Overview: Test suite for CI template service — validates template CRUD and instantiation logic.
Architecture: Test coverage for template management and CI creation from templates (Section 8)
Dependencies: pytest, app.services.cmdb.template_service
Concepts: Template CRUD, instantiation, override merging, pure data transformation validation.
"""

import uuid
from unittest.mock import MagicMock

from app.services.cmdb.template_service import TemplateService, TemplateServiceError


class TestTemplateServiceError:
    """Test TemplateServiceError exception behavior."""

    def test_is_exception(self):
        """TemplateServiceError is an Exception subclass."""
        error = TemplateServiceError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self):
        """TemplateServiceError stores message and code."""
        error = TemplateServiceError("test error", "TEST_CODE")
        assert error.message == "test error"
        assert error.code == "TEST_CODE"
        assert str(error) == "test error"

    def test_default_code(self):
        """TemplateServiceError defaults to TEMPLATE_ERROR code."""
        error = TemplateServiceError("test error")
        assert error.code == "TEMPLATE_ERROR"


class TestTemplateServiceInit:
    """Test TemplateService initialization requirements."""

    def test_requires_db_session(self):
        """TemplateService requires an AsyncSession parameter."""
        service = TemplateService(db=None)
        assert service.db is None

    def test_stores_db_session(self):
        """TemplateService stores the db session in self.db."""
        mock_db = object()
        service = TemplateService(db=mock_db)
        assert service.db is mock_db


class TestBuildCIData:
    """Test build_ci_data_from_template pure data transformation."""

    def test_builds_data_from_template_without_overrides(self):
        """build_ci_data_from_template returns correct structure without overrides."""
        service = TemplateService(db=None)

        # Create mock template with required attributes
        mock_template = MagicMock()
        mock_template.ci_class_id = uuid.uuid4()
        mock_template.name = "Web Server Template"
        mock_template.description = "Standard web server configuration"
        mock_template.attributes = {"cpu": 4, "memory": 8192}
        mock_template.tags = {"env": "production", "owner": "platform"}

        result = service.build_ci_data_from_template(mock_template)

        assert result["ci_class_id"] == mock_template.ci_class_id
        assert result["name"] == "Web Server Template"
        assert result["description"] == "Standard web server configuration"
        assert result["attributes"] == {"cpu": 4, "memory": 8192}
        assert result["tags"] == {"env": "production", "owner": "platform"}

    def test_builds_data_with_overrides(self):
        """build_ci_data_from_template merges overrides correctly."""
        service = TemplateService(db=None)

        mock_template = MagicMock()
        mock_template.ci_class_id = uuid.uuid4()
        mock_template.name = "Web Server Template"
        mock_template.description = "Standard web server configuration"
        mock_template.attributes = {"cpu": 4, "memory": 8192}
        mock_template.tags = {"env": "production", "owner": "platform"}

        overrides = {
            "name": "Custom Web Server",
            "description": "Custom configuration",
            "attributes": {"cpu": 8},
            "tags": {"tier": "premium"},
            "compartment_id": uuid.uuid4(),
            "lifecycle_state": "active",
        }

        result = service.build_ci_data_from_template(mock_template, overrides)

        assert result["name"] == "Custom Web Server"
        assert result["description"] == "Custom configuration"
        assert result["attributes"] == {"cpu": 8, "memory": 8192}  # Merged
        assert result["tags"] == {
            "env": "production",
            "owner": "platform",
            "tier": "premium",
        }  # Merged
        assert result["compartment_id"] == overrides["compartment_id"]
        assert result["lifecycle_state"] == "active"

    def test_partial_overrides(self):
        """build_ci_data_from_template handles partial overrides."""
        service = TemplateService(db=None)

        mock_template = MagicMock()
        mock_template.ci_class_id = uuid.uuid4()
        mock_template.name = "DB Template"
        mock_template.description = "Database server"
        mock_template.attributes = {"storage": 100}
        mock_template.tags = {"type": "mysql"}

        overrides = {"name": "Production DB"}

        result = service.build_ci_data_from_template(mock_template, overrides)

        assert result["name"] == "Production DB"
        assert result["description"] == "Database server"  # Not overridden
        assert result["attributes"] == {"storage": 100}  # Not overridden
        assert result["tags"] == {"type": "mysql"}  # Not overridden
