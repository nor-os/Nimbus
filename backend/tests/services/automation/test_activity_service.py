"""
Overview: Unit tests for the activity catalog service.
Architecture: Test layer for activity catalog (Section 11.5)
Dependencies: pytest, app.services.automation.activity_service
Concepts: Activity CRUD, slug generation, versioning
"""

import pytest
from app.services.automation.activity_service import _slugify


class TestSlugify:
    """Test slug generation helper."""

    def test_basic_slugify(self):
        assert _slugify("Disk Resize") == "disk-resize"

    def test_slugify_special_chars(self):
        result = _slugify("Scale Resource (CPU/RAM)")
        assert " " not in result
        assert result.islower() or "-" in result

    def test_slugify_already_slug(self):
        assert _slugify("disk-resize") == "disk-resize"

    def test_slugify_underscores(self):
        result = _slugify("run_backup")
        # Should convert underscores to hyphens
        assert "_" not in result or result == "run-backup"
