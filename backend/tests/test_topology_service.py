"""
Overview: Tests for TopologyService — lifecycle, versioning, export/import, clone, templates.
Architecture: Unit tests for architecture topology service (Section 5)
Dependencies: pytest, unittest.mock, app.services.architecture.topology_service
Concepts: Topology lifecycle tests, draft/publish/archive, versioning, clone, export/import
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.architecture_topology import ArchitectureTopology, TopologyStatus
from app.services.architecture.topology_service import TopologyError, TopologyService


def _make_topology(
    name: str = "Test Topology",
    status: TopologyStatus = TopologyStatus.DRAFT,
    version: int = 0,
    graph: dict | None = None,
    tenant_id: str | None = None,
) -> ArchitectureTopology:
    """Create a minimal ArchitectureTopology for testing."""
    t = ArchitectureTopology(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(tenant_id) if tenant_id else uuid.uuid4(),
        name=name,
        description="Test description",
        graph=graph or {"nodes": [], "connections": []},
        status=status,
        version=version,
        is_template=False,
        is_system=False,
        tags=["test"],
        created_by=uuid.uuid4(),
    )
    t.created_at = datetime.utcnow()
    t.updated_at = datetime.utcnow()
    t.deleted_at = None
    return t


class TestTopologyCreate:
    """Test topology creation."""

    @pytest.mark.asyncio
    async def test_create_sets_draft_status(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, '_audit', new_callable=AsyncMock):
            result = await svc.create(
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                {"name": "My Topology", "description": "A test"},
            )

        assert result.name == "My Topology"
        assert result.status == TopologyStatus.DRAFT
        assert result.version == 0
        assert result.is_template is False
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_template(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, '_audit', new_callable=AsyncMock):
            result = await svc.create(
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                {"name": "Template", "is_template": True},
            )

        assert result.is_template is True


class TestTopologyUpdate:
    """Test topology update logic."""

    @pytest.mark.asyncio
    async def test_update_draft_succeeds(self):
        topology = _make_topology()
        db = AsyncMock()
        db.flush = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology), \
             patch.object(svc, '_audit', new_callable=AsyncMock):
            result = await svc.update(
                str(topology.tenant_id),
                str(topology.id),
                {"name": "Updated Name"},
            )

        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_published_fails(self):
        topology = _make_topology(status=TopologyStatus.PUBLISHED)
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology):
            with pytest.raises(TopologyError) as exc_info:
                await svc.update(
                    str(topology.tenant_id),
                    str(topology.id),
                    {"name": "Updated"},
                )
            assert exc_info.value.code == "NOT_DRAFT"


class TestTopologyPublish:
    """Test publish lifecycle."""

    @pytest.mark.asyncio
    async def test_publish_no_graph_fails(self):
        topology = _make_topology(graph=None)
        topology.graph = None
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology):
            with pytest.raises(TopologyError) as exc_info:
                await svc.publish(
                    str(topology.tenant_id),
                    str(topology.id),
                    str(uuid.uuid4()),
                )
            assert exc_info.value.code == "NO_GRAPH"

    @pytest.mark.asyncio
    async def test_publish_not_draft_fails(self):
        topology = _make_topology(status=TopologyStatus.PUBLISHED)
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology):
            with pytest.raises(TopologyError) as exc_info:
                await svc.publish(
                    str(topology.tenant_id),
                    str(topology.id),
                    str(uuid.uuid4()),
                )
            assert exc_info.value.code == "NOT_DRAFT"


class TestTopologyClone:
    """Test clone behavior."""

    @pytest.mark.asyncio
    async def test_clone_creates_draft_copy(self):
        topology = _make_topology(
            name="Original",
            status=TopologyStatus.PUBLISHED,
            version=3,
            graph={"nodes": [{"id": "n1"}], "connections": []},
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology), \
             patch.object(svc, '_audit', new_callable=AsyncMock):
            result = await svc.clone(
                str(topology.tenant_id),
                str(topology.id),
                str(uuid.uuid4()),
            )

        assert result.name == "Original (Copy)"
        assert result.status == TopologyStatus.DRAFT
        assert result.version == 0
        assert result.graph is not None
        db.add.assert_called_once()


class TestTopologyExport:
    """Test export/import."""

    @pytest.mark.asyncio
    async def test_export_json(self):
        topology = _make_topology(
            name="Export Test",
            graph={"nodes": [{"id": "n1"}], "connections": []},
        )
        topology.tags = ["web", "prod"]
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology):
            result = await svc.export_json(
                str(topology.tenant_id),
                str(topology.id),
            )

        assert result["name"] == "Export Test"
        assert result["graph"] == {"nodes": [{"id": "n1"}], "connections": []}
        assert result["tags"] == ["web", "prod"]

    @pytest.mark.asyncio
    async def test_export_yaml(self):
        topology = _make_topology(name="YAML Test")
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology):
            result = await svc.export_yaml(
                str(topology.tenant_id),
                str(topology.id),
            )

        assert "name: YAML Test" in result


class TestTopologyDelete:
    """Test soft delete."""

    @pytest.mark.asyncio
    async def test_delete_sets_deleted_at(self):
        topology = _make_topology()
        db = AsyncMock()
        db.flush = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=topology), \
             patch.object(svc, '_audit', new_callable=AsyncMock):
            result = await svc.delete(
                str(topology.tenant_id),
                str(topology.id),
            )

        assert result is True
        assert topology.deleted_at is not None


class TestTopologyNotFound:
    """Test not-found handling."""

    @pytest.mark.asyncio
    async def test_get_or_raise_not_found(self):
        db = AsyncMock()
        svc = TopologyService(db)

        with patch.object(svc, 'get', new_callable=AsyncMock, return_value=None):
            with pytest.raises(TopologyError) as exc_info:
                await svc._get_or_raise(str(uuid.uuid4()), str(uuid.uuid4()))
            assert exc_info.value.code == "NOT_FOUND"
