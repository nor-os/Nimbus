"""
Overview: Tests for ActivityTypeService — CRUD for semantic activity types.
Architecture: Unit tests for semantic activity type service (Section 5)
Dependencies: pytest, unittest.mock, app.services.semantic.activity_type_service
Concepts: Activity type CRUD, is_system protection, applicable type filtering
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.semantic_activity_type import SemanticActivityType
from app.services.semantic.activity_type_service import (
    ActivityTypeService,
    ActivityTypeServiceError,
)


def _make_activity_type(
    name: str = "provisioning",
    category: str = "lifecycle",
    is_system: bool = False,
    applicable_semantic_categories: list | None = None,
) -> SemanticActivityType:
    at = SemanticActivityType()
    at.id = uuid.uuid4()
    at.name = name
    at.display_name = name.replace("_", " ").title()
    at.category = category
    at.description = f"Test {name}"
    at.icon = "test-icon"
    at.applicable_semantic_categories = applicable_semantic_categories
    at.applicable_semantic_types = None
    at.default_relationship_kind_id = None
    at.properties_schema = None
    at.is_system = is_system
    at.sort_order = 0
    at.created_at = datetime.utcnow()
    at.updated_at = datetime.utcnow()
    at.deleted_at = None
    return at


class TestActivityTypeServiceList:
    """Tests for listing activity types."""

    @pytest.mark.asyncio
    async def test_list_all(self):
        at1 = _make_activity_type("provisioning")
        at2 = _make_activity_type("backup")

        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [at1, at2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        results = await svc.list_activity_types()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_by_category(self):
        at1 = _make_activity_type("provisioning", category="lifecycle")

        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [at1]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        results = await svc.list_activity_types(category="lifecycle")
        assert len(results) == 1


class TestActivityTypeServiceCreate:
    """Tests for creating activity types."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        db = AsyncMock()
        # First execute for duplicate check
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        svc = ActivityTypeService(db)
        at = await svc.create_activity_type({
            "name": "new_type",
            "display_name": "New Type",
            "category": "test",
        })
        assert at.name == "new_type"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_fails(self):
        existing = _make_activity_type("existing")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        with pytest.raises(ActivityTypeServiceError) as exc_info:
            await svc.create_activity_type({
                "name": "existing",
                "display_name": "Existing",
            })
        assert "DUPLICATE" in exc_info.value.code


class TestActivityTypeServiceUpdate:
    """Tests for updating activity types."""

    @pytest.mark.asyncio
    async def test_update_display_name(self):
        at = _make_activity_type("provisioning")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = at
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        svc = ActivityTypeService(db)
        updated = await svc.update_activity_type(str(at.id), {
            "display_name": "Provisioning V2",
        })
        assert updated.display_name == "Provisioning V2"

    @pytest.mark.asyncio
    async def test_cannot_rename_system_type(self):
        at = _make_activity_type("provisioning", is_system=True)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = at
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        with pytest.raises(ActivityTypeServiceError) as exc_info:
            await svc.update_activity_type(str(at.id), {
                "name": "renamed",
            })
        assert "SYSTEM_RECORD" in exc_info.value.code


class TestActivityTypeServiceDelete:
    """Tests for deleting activity types."""

    @pytest.mark.asyncio
    async def test_delete_custom_type(self):
        at = _make_activity_type("custom", is_system=False)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = at
        db.execute.return_value = result_mock
        db.flush = AsyncMock()

        svc = ActivityTypeService(db)
        deleted = await svc.delete_activity_type(str(at.id))
        assert deleted is True
        assert at.deleted_at is not None

    @pytest.mark.asyncio
    async def test_cannot_delete_system_type(self):
        at = _make_activity_type("provisioning", is_system=True)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = at
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        with pytest.raises(ActivityTypeServiceError) as exc_info:
            await svc.delete_activity_type(str(at.id))
        assert "SYSTEM_RECORD" in exc_info.value.code


class TestActivityTypeApplicableFiltering:
    """Tests for get_applicable_types filtering."""

    @pytest.mark.asyncio
    async def test_applicable_by_category(self):
        at1 = _make_activity_type("provisioning", applicable_semantic_categories=["compute", "storage"])
        at2 = _make_activity_type("monitoring_setup", applicable_semantic_categories=["compute"])
        at3 = _make_activity_type("incident_response")  # No constraints = universal

        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [at1, at2, at3]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        results = await svc.get_applicable_types(semantic_category="compute")
        # at1 matches (compute in list), at2 matches (compute in list), at3 matches (universal)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_applicable_by_category_excludes_non_matching(self):
        at1 = _make_activity_type("provisioning", applicable_semantic_categories=["compute"])
        at2 = _make_activity_type("network_config", applicable_semantic_categories=["network"])

        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [at1, at2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        svc = ActivityTypeService(db)
        results = await svc.get_applicable_types(semantic_category="compute")
        # Only at1 matches
        assert len(results) == 1
        assert results[0].name == "provisioning"
