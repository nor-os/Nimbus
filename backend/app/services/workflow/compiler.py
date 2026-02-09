"""
Overview: Workflow compiler — transforms a validated graph into an ExecutionPlan.
Architecture: Graph-to-execution-plan compiler using topological sort (Section 5)
Dependencies: app.services.workflow.execution_plan
Concepts: Topological sort, Kahn's algorithm, parallel groups, loop body extraction, branch grouping
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from app.services.workflow.execution_plan import ExecutionPlan, ExecutionStep

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    pass


class WorkflowCompiler:
    """Compiles a validated workflow graph into a deterministic ExecutionPlan."""

    def compile(
        self,
        definition_id: str,
        version: int,
        graph: dict[str, Any],
        timeout_seconds: int = 3600,
    ) -> ExecutionPlan:
        nodes: list[dict] = graph.get("nodes", [])
        connections: list[dict] = graph.get("connections", [])

        if not nodes:
            raise CompilationError("Graph has no nodes")

        node_map = {n["id"]: n for n in nodes}

        # Build adjacency and reverse adjacency
        adj: dict[str, list[tuple[str, str]]] = {n["id"]: [] for n in nodes}
        reverse_adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        connection_ports: dict[tuple[str, str], str] = {}  # (source, target) -> source_port

        for conn in connections:
            src = conn.get("source")
            tgt = conn.get("target")
            src_port = conn.get("source_port", "out")
            if src in adj:
                adj[src].append((tgt, src_port))
            if tgt in reverse_adj:
                reverse_adj[tgt].append(src)
            connection_ports[(src, tgt)] = src_port

        # Topological sort using Kahn's algorithm
        sorted_ids = self._topological_sort(nodes, adj, reverse_adj)

        # Detect parallel groups, loop bodies, and branches
        parallel_groups = self._detect_parallel_groups(nodes, connections, node_map)
        loop_bodies = self._detect_loop_bodies(nodes, connections, node_map)
        branch_map = self._detect_branches(connections, node_map, connection_ports)

        # Build execution steps
        steps: list[ExecutionStep] = []
        for node_id in sorted_ids:
            node = node_map[node_id]
            step = ExecutionStep(
                node_id=node_id,
                node_type=node.get("type", ""),
                config=node.get("config", {}),
                dependencies=list(reverse_adj.get(node_id, [])),
                parallel_group=parallel_groups.get(node_id),
                loop_parent=loop_bodies.get(node_id),
                branch_key=branch_map.get(node_id),
            )
            steps.append(step)

        return ExecutionPlan(
            definition_id=definition_id,
            definition_version=version,
            steps=steps,
            timeout_seconds=timeout_seconds,
        )

    def _topological_sort(
        self,
        nodes: list[dict],
        adj: dict[str, list[tuple[str, str]]],
        reverse_adj: dict[str, list[str]],
    ) -> list[str]:
        """Kahn's algorithm for deterministic topological ordering."""
        in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
        for node_id, deps in reverse_adj.items():
            in_degree[node_id] = len(deps)

        # Sort by node_id for deterministic output when multiple nodes have in_degree 0
        queue = deque(
            sorted([nid for nid, deg in in_degree.items() if deg == 0])
        )
        sorted_ids: list[str] = []

        while queue:
            current = queue.popleft()
            sorted_ids.append(current)

            neighbors = sorted([tgt for tgt, _ in adj.get(current, [])])
            for neighbor in neighbors:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(nodes):
            raise CompilationError(
                f"Cycle detected: processed {len(sorted_ids)} of {len(nodes)} nodes"
            )

        return sorted_ids

    def _detect_parallel_groups(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
    ) -> dict[str, str]:
        """Assign parallel group IDs to nodes between Parallel and Merge."""
        groups: dict[str, str] = {}

        parallel_nodes = [n for n in nodes if n.get("type") == "parallel"]

        for pnode in parallel_nodes:
            group_id = f"pg_{pnode['id']}"
            groups[pnode["id"]] = group_id

            # BFS from parallel node to find all nodes until merge
            visited: set[str] = set()
            queue = deque([pnode["id"]])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                groups[current] = group_id

                for conn in connections:
                    if conn.get("source") == current:
                        target = conn.get("target")
                        target_type = node_map.get(target, {}).get("type")
                        if target_type == "merge":
                            groups[target] = group_id
                        elif target and target not in visited:
                            queue.append(target)

        return groups

    def _detect_loop_bodies(
        self,
        nodes: list[dict],
        connections: list[dict],
        node_map: dict[str, dict],
    ) -> dict[str, str]:
        """Identify which nodes belong to which loop body."""
        loop_bodies: dict[str, str] = {}

        loop_nodes = [
            n for n in nodes if n.get("type") in ("forEach", "while")
        ]

        for lnode in loop_nodes:
            loop_id = lnode["id"]

            # Find nodes connected via the "body" port
            body_starts: list[str] = []
            for conn in connections:
                if (
                    conn.get("source") == loop_id
                    and conn.get("source_port", "") == "body"
                ):
                    body_starts.append(conn.get("target"))

            # BFS through body nodes
            visited: set[str] = set()
            queue = deque(body_starts)
            while queue:
                current = queue.popleft()
                if current in visited or current == loop_id:
                    continue
                visited.add(current)
                loop_bodies[current] = loop_id

                for conn in connections:
                    if conn.get("source") == current:
                        target = conn.get("target")
                        # Stop at loop node (loop-back) or done port targets
                        if target != loop_id and target not in visited:
                            queue.append(target)

        return loop_bodies

    def _detect_branches(
        self,
        connections: list[dict],
        node_map: dict[str, dict],
        connection_ports: dict[tuple[str, str], str],
    ) -> dict[str, str]:
        """Assign branch keys to nodes following conditional/switch outputs."""
        branch_map: dict[str, str] = {}
        branching_types = {"condition", "switch"}

        for conn in connections:
            src = conn.get("source")
            tgt = conn.get("target")
            src_port = conn.get("source_port", "")
            src_type = node_map.get(src, {}).get("type")

            if src_type in branching_types and src_port:
                branch_key = f"{src}:{src_port}"
                branch_map[tgt] = branch_key

        return branch_map
