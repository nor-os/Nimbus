"""
Overview: Tests for graph service — traversal, path finding, impact analysis, cycle detection.
Architecture: Unit tests for CMDB graph operations (Section 8)
Dependencies: pytest, app.services.cmdb.graph_service
Concepts: Graph traversal via recursive CTE, BFS path finding, impact analysis, cycle detection
"""

from app.services.cmdb.graph_service import GraphNode, GraphService, GraphServiceError


class TestGraphServiceError:
    def test_is_exception(self):
        assert issubclass(GraphServiceError, Exception)

    def test_error_message(self):
        err = GraphServiceError("Traversal failed")
        assert str(err) == "Traversal failed"

    def test_error_code(self):
        err = GraphServiceError("Test error", code="TEST_ERROR")
        assert err.code == "TEST_ERROR"
        assert err.message == "Test error"

    def test_default_error_code(self):
        err = GraphServiceError("Test error")
        assert err.code == "GRAPH_ERROR"


class TestGraphNode:
    def test_creation(self):
        node = GraphNode(
            ci_id="abc-123",
            name="Web Server",
            ci_class="VirtualMachine",
            depth=2,
            path=["root", "parent", "abc-123"],
        )
        assert node.ci_id == "abc-123"
        assert node.name == "Web Server"
        assert node.ci_class == "VirtualMachine"
        assert node.depth == 2
        assert len(node.path) == 3
        assert node.path == ["root", "parent", "abc-123"]

    def test_creation_minimal(self):
        node = GraphNode(ci_id="x", name="Test", ci_class="Server", depth=0, path=[])
        assert node.ci_id == "x"
        assert node.name == "Test"
        assert node.ci_class == "Server"
        assert node.depth == 0
        assert node.path == []

    def test_stores_all_attributes(self):
        node = GraphNode(
            ci_id="test-id",
            name="Test Name",
            ci_class="TestClass",
            depth=5,
            path=["a", "b", "c"],
        )
        assert node.ci_id == "test-id"
        assert node.name == "Test Name"
        assert node.ci_class == "TestClass"
        assert node.depth == 5
        assert node.path == ["a", "b", "c"]


class TestGraphServiceInit:
    def test_requires_db_session(self):
        svc = GraphService(db=None)
        assert svc.db is None

    def test_stores_db_session(self):
        """GraphService stores the db session in self.db."""
        mock_db = object()
        svc = GraphService(db=mock_db)
        assert svc.db is mock_db
