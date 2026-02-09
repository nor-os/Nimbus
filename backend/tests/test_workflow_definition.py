"""
Overview: Tests for the workflow definition service — CRUD, versioning, publish, clone, export/import.
Architecture: Unit tests for definition service (Section 5)
Dependencies: pytest, unittest.mock, app.services.workflow.definition_service
Concepts: Definition lifecycle, draft/active/archived, versioning, tenant isolation
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.workflow_definition import WorkflowDefinition, WorkflowDefinitionStatus
from app.services.workflow.definition_service import (
    WorkflowDefinitionError,
    WorkflowDefinitionService,
)
from app.services.workflow.graph_validator import ValidationResult


# ── Helpers ──────────────────────────────────────────────


def _make_definition(
    *,
    tenant_id="t1",
    name="Test Workflow",
    status=WorkflowDefinitionStatus.DRAFT,
    version=0,
    graph=None,
    timeout_seconds=3600,
    max_concurrent=10,
):
    """Create a mock WorkflowDefinition."""
    defn = MagicMock(spec=WorkflowDefinition)
    defn.id = uuid.uuid4()
    defn.tenant_id = tenant_id
    defn.name = name
    defn.description = "Test description"
    defn.version = version
    defn.graph = graph
    defn.status = status
    defn.created_by = "user1"
    defn.timeout_seconds = timeout_seconds
    defn.max_concurrent = max_concurrent
    defn.deleted_at = None
    defn.created_at = datetime.now(UTC)
    defn.updated_at = datetime.now(UTC)
    return defn


def _make_db_mock(scalar_result=None, scalars_result=None):
    """Create a mock AsyncSession."""
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = scalar_result
    if scalars_result is not None:
        execute_result.scalars.return_value.all.return_value = scalars_result
    else:
        execute_result.scalars.return_value.all.return_value = []
    db.execute.return_value = execute_result
    return db


# ── Create Tests ─────────────────────────────────────────


class TestDefinitionCreate:
    @pytest.mark.asyncio
    async def test_create_draft(self):
        db = AsyncMock()
        service = WorkflowDefinitionService(db)

        result = await service.create(
            tenant_id="t1",
            created_by="user1",
            data={"name": "My Workflow", "description": "A test"},
        )

        assert result.name == "My Workflow"
        assert result.status == WorkflowDefinitionStatus.DRAFT
        assert result.version == 0
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_graph(self):
        db = AsyncMock()
        service = WorkflowDefinitionService(db)
        graph = {"nodes": [], "connections": []}

        result = await service.create(
            tenant_id="t1",
            created_by="user1",
            data={"name": "My Workflow", "graph": graph},
        )

        assert result.graph == graph


# ── Update Tests ─────────────────────────────────────────


class TestDefinitionUpdate:
    @pytest.mark.asyncio
    async def test_update_draft(self):
        defn = _make_definition(status=WorkflowDefinitionStatus.DRAFT)
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        result = await service.update(
            tenant_id="t1",
            definition_id=str(defn.id),
            data={"name": "Updated Name"},
        )

        assert result is defn
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_non_draft_fails(self):
        defn = _make_definition(status=WorkflowDefinitionStatus.ACTIVE)
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        with pytest.raises(WorkflowDefinitionError, match="draft"):
            await service.update(
                tenant_id="t1",
                definition_id=str(defn.id),
                data={"name": "Updated"},
            )

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        db = _make_db_mock(scalar_result=None)
        service = WorkflowDefinitionService(db)

        with pytest.raises(WorkflowDefinitionError, match="not found"):
            await service.update(
                tenant_id="t1",
                definition_id="nonexistent",
                data={"name": "Updated"},
            )


# ── Publish Tests ────────────────────────────────────────


class TestDefinitionPublish:
    @pytest.mark.asyncio
    async def test_publish_valid_graph(self):
        graph = {
            "nodes": [
                {"id": "s", "type": "start", "config": {}},
                {"id": "e", "type": "end", "config": {}},
            ],
            "connections": [{"source": "s", "target": "e", "source_port": "out", "target_port": "in"}],
        }
        defn = _make_definition(
            status=WorkflowDefinitionStatus.DRAFT,
            version=0,
            graph=graph,
        )

        # Mock the db for both get and the archive query
        db = AsyncMock()
        execute_result_get = MagicMock()
        execute_result_get.scalar_one_or_none.return_value = defn
        execute_result_archive = MagicMock()
        execute_result_archive.scalars.return_value.all.return_value = []
        db.execute.side_effect = [execute_result_get, execute_result_archive]

        service = WorkflowDefinitionService(db)

        # Mock validator to return valid
        valid_result = ValidationResult(valid=True)
        service._validator = MagicMock()
        service._validator.validate.return_value = valid_result

        result = await service.publish(tenant_id="t1", definition_id=str(defn.id))

        assert result is defn
        assert defn.version == 1
        assert defn.status == WorkflowDefinitionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_publish_no_graph_fails(self):
        defn = _make_definition(
            status=WorkflowDefinitionStatus.DRAFT,
            graph=None,
        )
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        with pytest.raises(WorkflowDefinitionError, match="without a graph"):
            await service.publish(tenant_id="t1", definition_id=str(defn.id))

    @pytest.mark.asyncio
    async def test_publish_non_draft_fails(self):
        defn = _make_definition(status=WorkflowDefinitionStatus.ACTIVE)
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        with pytest.raises(WorkflowDefinitionError, match="draft"):
            await service.publish(tenant_id="t1", definition_id=str(defn.id))

    @pytest.mark.asyncio
    async def test_publish_invalid_graph_fails(self):
        defn = _make_definition(
            status=WorkflowDefinitionStatus.DRAFT,
            graph={"nodes": [], "connections": []},
        )

        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        # Validator returns invalid
        invalid_result = ValidationResult(valid=False)
        invalid_result.add_error("Graph has no nodes")
        service._validator = MagicMock()
        service._validator.validate.return_value = invalid_result

        with pytest.raises(WorkflowDefinitionError, match="validation failed"):
            await service.publish(tenant_id="t1", definition_id=str(defn.id))

    @pytest.mark.asyncio
    async def test_publish_archives_previous_active(self):
        graph = {
            "nodes": [
                {"id": "s", "type": "start", "config": {}},
                {"id": "e", "type": "end", "config": {}},
            ],
            "connections": [{"source": "s", "target": "e"}],
        }
        defn = _make_definition(
            status=WorkflowDefinitionStatus.DRAFT,
            version=0,
            graph=graph,
        )
        prev_active = _make_definition(
            status=WorkflowDefinitionStatus.ACTIVE,
            version=1,
        )

        db = AsyncMock()
        execute_result_get = MagicMock()
        execute_result_get.scalar_one_or_none.return_value = defn
        execute_result_archive = MagicMock()
        execute_result_archive.scalars.return_value.all.return_value = [prev_active]
        db.execute.side_effect = [execute_result_get, execute_result_archive]

        service = WorkflowDefinitionService(db)
        valid_result = ValidationResult(valid=True)
        service._validator = MagicMock()
        service._validator.validate.return_value = valid_result

        await service.publish(tenant_id="t1", definition_id=str(defn.id))

        assert prev_active.status == WorkflowDefinitionStatus.ARCHIVED


# ── Archive Tests ────────────────────────────────────────


class TestDefinitionArchive:
    @pytest.mark.asyncio
    async def test_archive(self):
        defn = _make_definition(status=WorkflowDefinitionStatus.ACTIVE)
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        result = await service.archive(tenant_id="t1", definition_id=str(defn.id))

        assert result is defn
        assert defn.status == WorkflowDefinitionStatus.ARCHIVED


# ── Clone Tests ──────────────────────────────────────────


class TestDefinitionClone:
    @pytest.mark.asyncio
    async def test_clone(self):
        graph = {"nodes": [], "connections": []}
        defn = _make_definition(
            status=WorkflowDefinitionStatus.ACTIVE,
            graph=graph,
        )
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        result = await service.clone(
            tenant_id="t1",
            definition_id=str(defn.id),
            created_by="user2",
        )

        assert result.name == f"{defn.name} (Copy)"
        assert result.status == WorkflowDefinitionStatus.DRAFT
        assert result.version == 0
        db.add.assert_called_once()


# ── Delete Tests ─────────────────────────────────────────


class TestDefinitionDelete:
    @pytest.mark.asyncio
    async def test_soft_delete(self):
        defn = _make_definition()
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        result = await service.delete(tenant_id="t1", definition_id=str(defn.id))

        assert result is True
        assert defn.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        db = _make_db_mock(scalar_result=None)
        service = WorkflowDefinitionService(db)

        with pytest.raises(WorkflowDefinitionError, match="not found"):
            await service.delete(tenant_id="t1", definition_id="nonexistent")


# ── Export/Import Tests ──────────────────────────────────


class TestDefinitionExportImport:
    @pytest.mark.asyncio
    async def test_export(self):
        graph = {"nodes": [{"id": "s", "type": "start"}], "connections": []}
        defn = _make_definition(graph=graph)
        db = _make_db_mock(scalar_result=defn)
        service = WorkflowDefinitionService(db)

        exported = await service.export_definition(
            tenant_id="t1", definition_id=str(defn.id)
        )

        assert "name" in exported
        assert "graph" in exported
        assert exported["graph"] == graph

    @pytest.mark.asyncio
    async def test_import(self):
        db = AsyncMock()
        service = WorkflowDefinitionService(db)

        result = await service.import_definition(
            tenant_id="t1",
            created_by="user1",
            data={"name": "Imported", "graph": {"nodes": [], "connections": []}},
        )

        assert result.name == "Imported"
        assert result.status == WorkflowDefinitionStatus.DRAFT
