"""
Overview: Tests for TopologyValidator — semantic type, relationship, property, and structure validation.
Architecture: Unit tests for topology validation service (Section 5)
Dependencies: pytest, unittest.mock, app.services.architecture.topology_validator
Concepts: Graph validation rules, semantic type verification, relationship kind checks, property schemas
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.architecture.topology_validator import TopologyValidator, ValidationResult


def _mock_type(
    type_id: str,
    display_name: str = "Test Type",
    allowed_rk: list | None = None,
    properties_schema: dict | None = None,
):
    """Create a mock SemanticResourceType."""
    t = MagicMock()
    t.id = uuid.UUID(type_id) if len(type_id) > 8 else type_id
    t.display_name = display_name
    t.allowed_relationship_kinds = allowed_rk
    t.properties_schema = properties_schema
    return t


def _mock_rk(rk_id: str, name: str = "contains", display_name: str = "Contains"):
    """Create a mock SemanticRelationshipKind."""
    rk = MagicMock()
    rk.id = uuid.UUID(rk_id) if len(rk_id) > 8 else rk_id
    rk.name = name
    rk.display_name = display_name
    return rk


TYPE_ID_1 = str(uuid.uuid4())
TYPE_ID_2 = str(uuid.uuid4())
RK_ID_1 = str(uuid.uuid4())


class TestEmptyGraph:
    @pytest.mark.asyncio
    async def test_empty_nodes_warns(self):
        db = AsyncMock()
        validator = TopologyValidator(db)
        result = await validator.validate({"nodes": [], "connections": []})
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "no nodes" in result.warnings[0].message.lower()


class TestNodeValidation:
    @pytest.mark.asyncio
    async def test_missing_node_id(self):
        db = AsyncMock()
        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [{"semantic_type_id": TYPE_ID_1}],
            "connections": [],
        })
        assert result.valid is False
        assert any("missing 'id'" in e.message.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_duplicate_node_id(self):
        db = AsyncMock()
        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1},
                {"id": "n1", "semantic_type_id": TYPE_ID_2},
            ],
            "connections": [],
        })
        assert result.valid is False
        assert any("duplicate" in e.message.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_missing_semantic_type(self):
        db = AsyncMock()
        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [{"id": "n1"}],
            "connections": [],
        })
        assert result.valid is False
        assert any("semantic_type_id" in e.message.lower() for e in result.errors)


class TestConnectionValidation:
    @pytest.mark.asyncio
    async def test_self_connection_fails(self):
        db = AsyncMock()
        # Mock type lookup
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_type(TYPE_ID_1)]
        db.execute = AsyncMock(return_value=mock_result)

        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1},
            ],
            "connections": [
                {"id": "c1", "source": "n1", "target": "n1", "relationship_kind_id": RK_ID_1},
            ],
        })
        assert result.valid is False
        assert any("self-connection" in e.message.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_unknown_source_fails(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_type(TYPE_ID_1)]
        db.execute = AsyncMock(return_value=mock_result)

        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1},
            ],
            "connections": [
                {"id": "c1", "source": "unknown", "target": "n1", "relationship_kind_id": RK_ID_1},
            ],
        })
        assert result.valid is False
        assert any("unknown source" in e.message.lower() for e in result.errors)


class TestOrphanWarning:
    @pytest.mark.asyncio
    async def test_orphan_node_warns(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_type(TYPE_ID_1)]
        db.execute = AsyncMock(return_value=mock_result)

        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1},
            ],
            "connections": [],
        })
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "orphan" in result.warnings[0].message.lower()


class TestPropertyValidation:
    @pytest.mark.asyncio
    async def test_required_property_missing(self):
        schema = {
            "type": "object",
            "required": ["cpu_count"],
            "properties": {
                "cpu_count": {"type": "integer", "title": "CPU Count"},
            },
        }
        mock_type = _mock_type(TYPE_ID_1, properties_schema=schema)

        db = AsyncMock()
        # First call: types, second call: relationship kinds
        type_result = MagicMock()
        type_result.scalars.return_value.all.return_value = [mock_type]
        rk_result = MagicMock()
        rk_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[type_result, rk_result])

        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1, "properties": {}},
            ],
            "connections": [],
        })
        assert result.valid is False
        assert any("required" in e.message.lower() and "cpu_count" in e.message.lower()
                    for e in result.errors)

    @pytest.mark.asyncio
    async def test_type_mismatch_detected(self):
        schema = {
            "type": "object",
            "properties": {
                "memory_gb": {"type": "number", "title": "Memory (GB)"},
            },
        }
        mock_type = _mock_type(TYPE_ID_1, properties_schema=schema)

        db = AsyncMock()
        type_result = MagicMock()
        type_result.scalars.return_value.all.return_value = [mock_type]
        rk_result = MagicMock()
        rk_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[type_result, rk_result])

        validator = TopologyValidator(db)
        result = await validator.validate({
            "nodes": [
                {"id": "n1", "semantic_type_id": TYPE_ID_1, "properties": {"memory_gb": "not_a_number"}},
            ],
            "connections": [],
        })
        assert result.valid is False
        assert any("should be number" in e.message.lower() for e in result.errors)
