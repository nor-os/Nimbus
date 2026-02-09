"""
Overview: Graph service — traversal, path finding, and impact analysis on the CI relationship graph.
Architecture: Recursive CTE-based graph queries for the CMDB (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.*
Concepts: The CI graph is a directed labeled multigraph. Traversal uses recursive CTEs for
    efficient multi-hop queries. Impact analysis follows depends_on/contains/uses edges to
    determine downstream/upstream blast radius.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class GraphServiceError(Exception):
    def __init__(self, message: str, code: str = "GRAPH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class GraphNode:
    """A node in a traversal result."""

    def __init__(self, ci_id: str, name: str, ci_class: str, depth: int, path: list[str]):
        self.ci_id = ci_id
        self.name = name
        self.ci_class = ci_class
        self.depth = depth
        self.path = path


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def traverse(
        self,
        ci_id: str,
        tenant_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",
        max_depth: int = 3,
    ) -> list[GraphNode]:
        """Traverse the CI graph from a starting node using recursive CTE.

        Args:
            ci_id: Starting CI ID
            tenant_id: Tenant isolation
            relationship_types: Filter by relationship type names (None = all)
            direction: 'outgoing', 'incoming', or 'both'
            max_depth: Maximum traversal depth
        """
        type_filter = ""
        params: dict = {
            "ci_id": ci_id,
            "tenant_id": tenant_id,
            "max_depth": max_depth,
        }

        if relationship_types:
            type_filter = "AND rt.name = ANY(:rel_types)"
            params["rel_types"] = relationship_types

        if direction == "outgoing":
            join_clause = "cr.source_ci_id = g.ci_id"
            next_ci = "cr.target_ci_id"
        elif direction == "incoming":
            join_clause = "cr.target_ci_id = g.ci_id"
            next_ci = "cr.source_ci_id"
        else:
            join_clause = "(cr.source_ci_id = g.ci_id OR cr.target_ci_id = g.ci_id)"
            next_ci = (
                "CASE WHEN cr.source_ci_id = g.ci_id "
                "THEN cr.target_ci_id ELSE cr.source_ci_id END"
            )

        query = text(f"""
            WITH RECURSIVE graph AS (
                SELECT
                    ci.id AS ci_id,
                    ci.name AS ci_name,
                    cc.name AS class_name,
                    0 AS depth,
                    ARRAY[ci.id::text] AS path
                FROM configuration_items ci
                JOIN ci_classes cc ON cc.id = ci.ci_class_id
                WHERE ci.id = :ci_id
                  AND ci.tenant_id = :tenant_id
                  AND ci.deleted_at IS NULL

                UNION ALL

                SELECT
                    next_ci.id AS ci_id,
                    next_ci.name AS ci_name,
                    ncc.name AS class_name,
                    g.depth + 1 AS depth,
                    g.path || next_ci.id::text
                FROM graph g
                JOIN ci_relationships cr ON {join_clause}
                    AND cr.tenant_id = :tenant_id
                    AND cr.deleted_at IS NULL
                JOIN relationship_types rt ON rt.id = cr.relationship_type_id
                    {type_filter}
                JOIN configuration_items next_ci ON next_ci.id = {next_ci}
                    AND next_ci.tenant_id = :tenant_id
                    AND next_ci.deleted_at IS NULL
                JOIN ci_classes ncc ON ncc.id = next_ci.ci_class_id
                WHERE g.depth < :max_depth
                  AND NOT (next_ci.id::text = ANY(g.path))
            )
            SELECT ci_id, ci_name, class_name, depth, path
            FROM graph
            WHERE depth > 0
            ORDER BY depth, ci_name
        """)

        result = await self.db.execute(query, params)
        rows = result.fetchall()
        return [
            GraphNode(
                ci_id=str(row[0]),
                name=row[1],
                ci_class=row[2],
                depth=row[3],
                path=row[4],
            )
            for row in rows
        ]

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        tenant_id: str,
        max_depth: int = 10,
    ) -> list[str] | None:
        """Find the shortest path between two CIs using BFS via recursive CTE."""
        query = text("""
            WITH RECURSIVE bfs AS (
                SELECT
                    ci.id AS ci_id,
                    ARRAY[ci.id::text] AS path
                FROM configuration_items ci
                WHERE ci.id = :source_id
                  AND ci.tenant_id = :tenant_id
                  AND ci.deleted_at IS NULL

                UNION ALL

                SELECT
                    next_ci.id,
                    b.path || next_ci.id::text
                FROM bfs b
                JOIN ci_relationships cr ON (
                    cr.source_ci_id = b.ci_id OR cr.target_ci_id = b.ci_id
                )
                    AND cr.tenant_id = :tenant_id
                    AND cr.deleted_at IS NULL
                JOIN configuration_items next_ci ON next_ci.id = (
                    CASE WHEN cr.source_ci_id = b.ci_id
                    THEN cr.target_ci_id ELSE cr.source_ci_id END
                )
                    AND next_ci.tenant_id = :tenant_id
                    AND next_ci.deleted_at IS NULL
                WHERE NOT (next_ci.id::text = ANY(b.path))
                  AND array_length(b.path, 1) < :max_depth
            )
            SELECT path FROM bfs
            WHERE ci_id = :target_id
            ORDER BY array_length(path, 1)
            LIMIT 1
        """)

        result = await self.db.execute(query, {
            "source_id": source_id,
            "target_id": target_id,
            "tenant_id": tenant_id,
            "max_depth": max_depth,
        })
        row = result.fetchone()
        return row[0] if row else None

    async def impact_analysis(
        self,
        ci_id: str,
        tenant_id: str,
        direction: str = "downstream",
        max_depth: int = 5,
    ) -> list[GraphNode]:
        """Analyze the impact of a CI failure on related CIs.

        Downstream: follows depends_on, contains, uses edges outward from target.
        Upstream: follows inverse edges to find what depends on this CI.
        """
        impact_types = ["depends_on", "contains", "uses"]

        if direction == "downstream":
            return await self.traverse(
                ci_id, tenant_id,
                relationship_types=impact_types,
                direction="incoming",
                max_depth=max_depth,
            )
        else:
            return await self.traverse(
                ci_id, tenant_id,
                relationship_types=impact_types,
                direction="outgoing",
                max_depth=max_depth,
            )

    async def detect_cycles(
        self,
        ci_id: str,
        tenant_id: str,
    ) -> list[list[str]] | None:
        """Detect cycles involving a specific CI in the relationship graph."""
        query = text("""
            WITH RECURSIVE cycle_check AS (
                SELECT
                    cr.target_ci_id AS ci_id,
                    ARRAY[cr.source_ci_id::text, cr.target_ci_id::text] AS path,
                    false AS has_cycle
                FROM ci_relationships cr
                WHERE cr.source_ci_id = :ci_id
                  AND cr.tenant_id = :tenant_id
                  AND cr.deleted_at IS NULL

                UNION ALL

                SELECT
                    cr.target_ci_id,
                    cc.path || cr.target_ci_id::text,
                    cr.target_ci_id::text = ANY(cc.path)
                FROM cycle_check cc
                JOIN ci_relationships cr ON cr.source_ci_id = cc.ci_id
                    AND cr.tenant_id = :tenant_id
                    AND cr.deleted_at IS NULL
                WHERE NOT cc.has_cycle
                  AND array_length(cc.path, 1) < 20
            )
            SELECT path FROM cycle_check WHERE has_cycle = true
        """)

        result = await self.db.execute(query, {
            "ci_id": ci_id,
            "tenant_id": tenant_id,
        })
        rows = result.fetchall()
        return [row[0] for row in rows] if rows else None
