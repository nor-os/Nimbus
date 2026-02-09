"""
Overview: Tests for the workflow graph validator — structure, reachability, cycles, ports.
Architecture: Unit tests for graph validation (Section 5)
Dependencies: pytest, app.services.workflow.graph_validator, app.services.workflow.node_registry
Concepts: DAG validation, reachability, cycle detection, parallel/merge balance, expression validation
"""

import pytest

from app.services.workflow.graph_validator import GraphValidator, ValidationResult
from app.services.workflow.node_registry import get_registry
from app.services.workflow.node_types import register_all


@pytest.fixture(autouse=True)
def _setup_registry():
    """Ensure node types are registered before each test."""
    registry = get_registry()
    registry.clear()
    register_all()
    yield
    registry.clear()


def _make_graph(nodes, connections=None):
    """Helper to build a graph dict."""
    return {
        "nodes": nodes,
        "connections": connections or [],
    }


def _node(node_id, node_type, config=None):
    """Helper to build a node dict."""
    return {"id": node_id, "type": node_type, "config": config or {}}


def _conn(source, target, source_port="out", target_port="in"):
    """Helper to build a connection dict."""
    return {
        "source": source,
        "target": target,
        "source_port": source_port,
        "target_port": target_port,
    }


# ── Valid Graph Tests ────────────────────────────────────


class TestValidGraphs:
    def test_minimal_valid_graph(self):
        """Start → End is the simplest valid graph."""
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "e")],
        )
        result = GraphValidator().validate(graph)
        assert result.valid

    def test_linear_graph(self):
        """Start → Script → End"""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("sc", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "sc"), _conn("sc", "e")],
        )
        result = GraphValidator().validate(graph)
        assert result.valid

    def test_condition_graph(self):
        """Start → Condition → (true: End1, false: End2)"""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("c", "condition", {"expression": "$input.x > 0"}),
                _node("e1", "end"),
                _node("e2", "end"),
            ],
            connections=[
                _conn("s", "c"),
                _conn("c", "e1", source_port="true"),
                _conn("c", "e2", source_port="false"),
            ],
        )
        result = GraphValidator().validate(graph)
        assert result.valid

    def test_parallel_merge_graph(self):
        """Start → Parallel → [A, B] → Merge → End"""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("p", "parallel"),
                _node("a", "script", {"assignments": []}),
                _node("b", "script", {"assignments": []}),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "p"),
                _conn("p", "a", source_port="branch_0"),
                _conn("p", "b", source_port="branch_1"),
                _conn("a", "m"),
                _conn("b", "m"),
                _conn("m", "e"),
            ],
        )
        result = GraphValidator().validate(graph)
        assert result.valid


# ── Start/End Validation ─────────────────────────────────


class TestStartEndValidation:
    def test_no_start_node(self):
        graph = _make_graph(nodes=[_node("e", "end")])
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("Start" in e.message for e in result.errors)

    def test_multiple_start_nodes(self):
        graph = _make_graph(
            nodes=[_node("s1", "start"), _node("s2", "start"), _node("e", "end")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("multiple" in e.message.lower() for e in result.errors)

    def test_no_end_node(self):
        graph = _make_graph(nodes=[_node("s", "start")])
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("End" in e.message for e in result.errors)

    def test_multiple_end_nodes_valid(self):
        """Multiple End nodes are allowed (e.g., from branches)."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("e1", "end"),
                _node("e2", "end"),
            ],
            connections=[_conn("s", "e1"), _conn("s", "e2")],
        )
        result = GraphValidator().validate(graph)
        assert result.valid


# ── Empty Graph ──────────────────────────────────────────


class TestEmptyGraph:
    def test_empty_nodes(self):
        graph = _make_graph(nodes=[])
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("no nodes" in e.message.lower() for e in result.errors)


# ── Node Type Validation ─────────────────────────────────


class TestNodeTypeValidation:
    def test_unknown_node_type(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("x", "nonexistent_type"),
                _node("e", "end"),
            ],
            connections=[_conn("s", "x"), _conn("x", "e")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("Unknown node type" in e.message for e in result.errors)


# ── Connection Validation ────────────────────────────────


class TestConnectionValidation:
    def test_connection_unknown_source(self):
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("nonexistent", "e")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("unknown source" in e.message.lower() for e in result.errors)

    def test_connection_unknown_target(self):
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "nonexistent")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("unknown target" in e.message.lower() for e in result.errors)

    def test_self_connection(self):
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "s"), _conn("s", "e")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("Self-connection" in e.message for e in result.errors)


# ── Reachability Tests ───────────────────────────────────


class TestReachability:
    def test_disconnected_node(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("orphan", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "e")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("not reachable" in e.message for e in result.errors)

    def test_all_reachable(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("a", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "a"), _conn("a", "e")],
        )
        result = GraphValidator().validate(graph)
        assert result.valid


# ── Cycle Detection ──────────────────────────────────────


class TestCycleDetection:
    def test_cycle_detected(self):
        """A → B → A creates a cycle outside of a loop node."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("a", "script", {"assignments": []}),
                _node("b", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "a"),
                _conn("a", "b"),
                _conn("b", "a"),  # cycle
                _conn("b", "e"),
            ],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("cycle" in e.message.lower() for e in result.errors)

    def test_loop_back_allowed(self):
        """Edges back to loop nodes are allowed (they represent loop iteration)."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("loop", "forEach", {"collection": "$input.items"}),
                _node("body", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "loop"),
                _conn("loop", "body", source_port="body"),
                _conn("body", "loop"),  # loop-back, should be allowed
                _conn("loop", "e", source_port="done"),
            ],
        )
        result = GraphValidator().validate(graph)
        assert result.valid


# ── Parallel/Merge Balance ───────────────────────────────


class TestParallelMergeBalance:
    def test_unbalanced_parallel_merge(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("p", "parallel"),
                _node("a", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "p"),
                _conn("p", "a"),
                _conn("a", "e"),
            ],
        )
        result = GraphValidator().validate(graph)
        # This is a warning, not an error
        assert any(
            "Unbalanced" in w.message
            for w in result.warnings
        )

    def test_balanced_parallel_merge(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("p", "parallel"),
                _node("a", "script", {"assignments": []}),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "p"),
                _conn("p", "a"),
                _conn("a", "m"),
                _conn("m", "e"),
            ],
        )
        result = GraphValidator().validate(graph)
        assert not any(
            "Unbalanced" in w.message
            for w in result.warnings
        )


# ── Expression Validation ────────────────────────────────


class TestExpressionValidation:
    def test_valid_condition_expression(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("c", "condition", {"expression": "$vars.x > 0"}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "c"), _conn("c", "e", source_port="true")],
        )
        result = GraphValidator().validate(graph)
        # Should not have expression errors
        assert not any(
            "Expression error" in e.message for e in result.errors
        )

    def test_invalid_condition_expression(self):
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("c", "condition", {"expression": "$vars.x >>"}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "c"), _conn("c", "e", source_port="true")],
        )
        result = GraphValidator().validate(graph)
        assert not result.valid
        assert any("Expression error" in e.message for e in result.errors)


# ── Dead End Warnings ────────────────────────────────────


class TestDeadEndWarnings:
    def test_node_with_no_outgoing(self):
        """Non-End nodes with no outgoing connections get a warning."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("a", "script", {"assignments": []}),
                _node("e", "end"),
            ],
            connections=[_conn("s", "a"), _conn("s", "e")],
            # a has no outgoing
        )
        result = GraphValidator().validate(graph)
        assert any("dead end" in w.message.lower() for w in result.warnings)
