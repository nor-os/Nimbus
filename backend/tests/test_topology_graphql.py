"""
Overview: Tests for architecture topology GraphQL resolvers — queries and mutations.
Architecture: Unit tests for GraphQL layer (Section 7.2)
Dependencies: pytest, unittest.mock
Concepts: GraphQL resolver testing, permission checks, topology CRUD mutations
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.graphql.queries.architecture import _topology_to_type
from app.api.graphql.types.architecture import TopologyStatusGQL
from app.models.architecture_topology import ArchitectureTopology, TopologyStatus


def _make_topology(
    name: str = "Test",
    status: TopologyStatus = TopologyStatus.DRAFT,
) -> ArchitectureTopology:
    t = ArchitectureTopology(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name=name,
        description="desc",
        graph={"nodes": [], "connections": []},
        status=status,
        version=1,
        is_template=False,
        is_system=False,
        tags=["test"],
        created_by=uuid.uuid4(),
    )
    t.created_at = datetime.now(timezone.utc)
    t.updated_at = datetime.now(timezone.utc)
    t.deleted_at = None
    return t


class TestTopologyToType:
    """Test ORM to GraphQL type conversion."""

    def test_converts_draft(self):
        topology = _make_topology(status=TopologyStatus.DRAFT)
        gql_type = _topology_to_type(topology)
        assert gql_type.name == "Test"
        assert gql_type.status == TopologyStatusGQL.DRAFT
        assert gql_type.version == 1
        assert gql_type.is_template is False

    def test_converts_published(self):
        topology = _make_topology(name="Prod", status=TopologyStatus.PUBLISHED)
        gql_type = _topology_to_type(topology)
        assert gql_type.status == TopologyStatusGQL.PUBLISHED

    def test_converts_archived(self):
        topology = _make_topology(status=TopologyStatus.ARCHIVED)
        gql_type = _topology_to_type(topology)
        assert gql_type.status == TopologyStatusGQL.ARCHIVED

    def test_tags_preserved(self):
        topology = _make_topology()
        topology.tags = ["web", "prod"]
        gql_type = _topology_to_type(topology)
        assert gql_type.tags == ["web", "prod"]

    def test_null_tags(self):
        topology = _make_topology()
        topology.tags = None
        gql_type = _topology_to_type(topology)
        assert gql_type.tags is None

    def test_null_tenant_id(self):
        topology = _make_topology()
        topology.tenant_id = None
        gql_type = _topology_to_type(topology)
        assert gql_type.tenant_id is None

    def test_graph_preserved(self):
        topology = _make_topology()
        topology.graph = {"nodes": [{"id": "n1"}], "connections": []}
        gql_type = _topology_to_type(topology)
        assert gql_type.graph == {"nodes": [{"id": "n1"}], "connections": []}


class TestTopologyStatusEnum:
    """Test status enum mapping."""

    def test_all_statuses_mapped(self):
        for status in TopologyStatus:
            topology = _make_topology(status=status)
            gql_type = _topology_to_type(topology)
            assert gql_type.status.value == status.value
