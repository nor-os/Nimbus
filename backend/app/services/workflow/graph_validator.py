"""
Overview: Graph validator — validates workflow graph structure before compilation.
Architecture: Graph validation layer for workflow editor (Section 5)
Dependencies: app.services.workflow.node_registry, app.services.workflow.expression_engine
Concepts: DAG validation, reachability, cycle detection, port compatibility, expression validation
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.services.workflow.expression_engine import validate_expression
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS
from app.services.workflow.node_registry import NodeTypeRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    node_id: str | None
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def add_error(self, message: str, node_id: str | None = None) -> None:
        self.errors.append(ValidationError(node_id, message, "error"))
        self.valid = False

    def add_warning(self, message: str, node_id: str | None = None) -> None:
        self.warnings.append(ValidationError(node_id, message, "warning"))


class GraphValidator:
    """Validates a workflow graph for structural and semantic correctness."""

    def __init__(self, registry: NodeTypeRegistry | None = None):
        self._registry = registry or get_registry()

    def validate(self, graph: dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        nodes: list[dict] = graph.get("nodes", [])
        connections: list[dict] = graph.get("connections", [])

        if not nodes:
            result.add_error("Graph has no nodes")
            return result

        node_map = {n["id"]: n for n in nodes}

        self._validate_start_end(nodes, result)
        if not result.valid:
            return result

        self._validate_node_types(nodes, result)
        self._validate_connections(connections, node_map, result)
        self._validate_reachability(nodes, connections, node_map, result)
        self._validate_all_paths_reach_end(nodes, connections, node_map, result)
        self._validate_cycles(nodes, connections, node_map, result)
        self._validate_parallel_merge_balance(nodes, connections, result)
        self._validate_expressions(nodes, result)
        self._validate_required_ports(nodes, connections, node_map, result)

        return result

    def _validate_start_end(
        self, nodes: list[dict], result: ValidationResult
    ) -> None:
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        end_nodes = [n for n in nodes if n.get("type") == "end"]

        if len(start_nodes) == 0:
            result.add_error("Graph must have exactly one Start node")
        elif len(start_nodes) > 1:
            result.add_error("Graph must have exactly one Start node, found multiple")

        if len(end_nodes) == 0:
            result.add_error("Graph must have at least one End node")

    def _validate_node_types(
        self, nodes: list[dict], result: ValidationResult
    ) -> None:
        for node in nodes:
            type_id = node.get("type", "")
            if not self._registry.has(type_id):
                result.add_error(
                    f"Unknown node type '{type_id}'",
                    node.get("id"),
                )

    def _validate_connections(
        self,
        connections: list[dict],
        node_map: dict[str, dict],
        result: ValidationResult,
    ) -> None:
        for conn in connections:
            source_id = conn.get("source")
            target_id = conn.get("target")

            if source_id not in node_map:
                result.add_error(
                    f"Connection references unknown source node '{source_id}'"
                )
            if target_id not in node_map:
                result.add_error(
                    f"Connection references unknown target node '{target_id}'"
                )
            if source_id == target_id:
                result.add_error(
                    "Self-connections are not allowed",
                    source_id,
                )

    def _validate_reachability(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
        result: ValidationResult,
    ) -> None:
        """Check that all nodes are reachable from Start."""
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        if not start_nodes:
            return

        adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        for conn in connections:
            src = conn.get("source")
            tgt = conn.get("target")
            if src in adj:
                adj[src].append(tgt)

        visited: set[str] = set()
        queue = deque([start_nodes[0]["id"]])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        for node in nodes:
            node_id = node["id"]
            node_type = node.get("type", "")
            if node_id not in visited and node_type != "start":
                result.add_error(
                    "Node is not reachable from Start",
                    node_id,
                )

    def _validate_all_paths_reach_end(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
        result: ValidationResult,
    ) -> None:
        """Check that all non-End nodes have at least one outgoing connection."""
        end_types = {"end"}
        loop_types = {"forEach", "while"}

        outgoing: dict[str, int] = {n["id"]: 0 for n in nodes}
        for conn in connections:
            src = conn.get("source")
            if src in outgoing:
                outgoing[src] += 1

        for node in nodes:
            node_id = node["id"]
            node_type = node.get("type", "")
            if node_type not in end_types and outgoing[node_id] == 0:
                # Loop body end nodes connect back, but the executor handles this
                if node_type not in loop_types:
                    result.add_warning(
                        "Node has no outgoing connections (dead end)",
                        node_id,
                    )

    def _validate_cycles(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
        result: ValidationResult,
    ) -> None:
        """Detect cycles that are NOT inside Loop nodes."""
        loop_node_ids = {
            n["id"] for n in nodes if n.get("type") in ("forEach", "while")
        }

        # Build adjacency excluding loop-back edges (edges targeting loop nodes)
        adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        for conn in connections:
            src = conn.get("source")
            tgt = conn.get("target")
            # Allow edges back to loop nodes (they represent loop-back)
            if tgt in loop_node_ids:
                continue
            if src in adj and tgt in adj:
                adj[src].append(tgt)

        # Kahn's algorithm to detect cycles
        in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
        for node_id, neighbors in adj.items():
            for n in neighbors:
                if n in in_degree:
                    in_degree[n] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        processed = 0

        while queue:
            current = queue.popleft()
            processed += 1
            for neighbor in adj.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if processed < len(nodes):
            result.add_error(
                "Graph contains a cycle outside of Loop nodes"
            )

    def _validate_parallel_merge_balance(
        self,
        nodes: list[dict],
        connections: list[dict],
        result: ValidationResult,
    ) -> None:
        """Check that Parallel and Merge nodes are balanced."""
        parallel_count = sum(1 for n in nodes if n.get("type") == "parallel")
        merge_count = sum(1 for n in nodes if n.get("type") == "merge")

        if parallel_count != merge_count:
            result.add_warning(
                f"Unbalanced Parallel/Merge: {parallel_count} Parallel, {merge_count} Merge"
            )

    def _validate_expressions(
        self, nodes: list[dict], result: ValidationResult
    ) -> None:
        """Validate expression syntax in node configurations."""
        expression_fields = {
            "condition": ["expression"],
            "switch": ["expression"],
            "forEach": ["collection"],
            "while": ["condition"],
            "script": [],  # validated via assignments
        }

        for node in nodes:
            node_type = node.get("type", "")
            config = node.get("config", {})

            if node_type in expression_fields:
                for field_name in expression_fields[node_type]:
                    expr = config.get(field_name, "")
                    if expr:
                        errors = validate_expression(expr, BUILTIN_FUNCTIONS)
                        for error in errors:
                            result.add_error(
                                f"Expression error in '{field_name}': {error}",
                                node.get("id"),
                            )

            # Validate script assignments
            if node_type == "script":
                for assignment in config.get("assignments", []):
                    expr = assignment.get("expression", "")
                    if expr:
                        errors = validate_expression(expr, BUILTIN_FUNCTIONS)
                        for error in errors:
                            result.add_error(
                                f"Script expression error: {error}",
                                node.get("id"),
                            )

    def _validate_required_ports(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
        result: ValidationResult,
    ) -> None:
        """Check that required input ports are connected."""
        incoming_ports: dict[str, set[str]] = {n["id"]: set() for n in nodes}
        for conn in connections:
            target_id = conn.get("target")
            target_port = conn.get("target_port", "in")
            if target_id in incoming_ports:
                incoming_ports[target_id].add(target_port)

        for node in nodes:
            node_id = node["id"]
            type_id = node.get("type", "")
            defn = self._registry.get(type_id)
            if not defn:
                continue

            for port in defn.ports:
                if (
                    port.direction.value == "INPUT"
                    and port.required
                    and port.name not in incoming_ports.get(node_id, set())
                ):
                    # Start node doesn't need incoming connections
                    if type_id != "start":
                        result.add_warning(
                            f"Required input port '{port.name}' is not connected",
                            node_id,
                        )
