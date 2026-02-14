"""
Overview: Topology graph validator — validates semantic types, relationships, properties, and structure.
Architecture: Validation service for architecture planner (Section 5)
Dependencies: sqlalchemy, app.models.semantic_type
Concepts: Graph validation, semantic type verification, relationship rules, property schema matching
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_library import PolicyLibraryEntry
from app.models.semantic_type import SemanticCategory, SemanticRelationshipKind, SemanticResourceType

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    node_id: str | None
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def add_error(self, message: str, node_id: str | None = None) -> None:
        self.errors.append(ValidationIssue(node_id=node_id, message=message))
        self.valid = False

    def add_warning(self, message: str, node_id: str | None = None) -> None:
        self.warnings.append(ValidationIssue(node_id=node_id, message=message))


class TopologyValidator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate(self, graph: dict[str, Any]) -> ValidationResult:
        """Validate a topology graph against the semantic layer."""
        result = ValidationResult()

        nodes = graph.get("nodes", [])
        connections = graph.get("connections", [])

        if not nodes:
            result.add_warning("Topology has no nodes")
            return result

        # Build lookup maps
        node_ids = set()
        node_type_map: dict[str, str] = {}  # node_id -> semantic_type_id

        # Validate node structure
        for node in nodes:
            nid = node.get("id")
            if not nid:
                result.add_error("Node missing 'id'")
                continue
            if nid in node_ids:
                result.add_error(f"Duplicate node ID '{nid}'", nid)
                continue
            node_ids.add(nid)

            st_id = node.get("semantic_type_id") or node.get("semanticTypeId")
            if not st_id:
                result.add_error("Node missing 'semantic_type_id'", nid)
            else:
                node_type_map[nid] = st_id

        # Load semantic types from DB
        type_ids = set(node_type_map.values())
        type_map: dict[str, SemanticResourceType] = {}
        if type_ids:
            stmt = select(SemanticResourceType).where(
                SemanticResourceType.id.in_(list(type_ids)),
                SemanticResourceType.deleted_at.is_(None),
            )
            db_result = await self.db.execute(stmt)
            for st in db_result.scalars().all():
                type_map[str(st.id)] = st

        # Verify semantic type IDs exist
        for nid, st_id in node_type_map.items():
            if st_id not in type_map:
                result.add_error(f"Unknown semantic type ID '{st_id}'", nid)

        # Load relationship kinds from DB
        rk_ids = set()
        for conn in connections:
            rk_id = conn.get("relationship_kind_id") or conn.get("relationshipKindId")
            if rk_id:
                rk_ids.add(rk_id)

        rk_map: dict[str, SemanticRelationshipKind] = {}
        if rk_ids:
            stmt = select(SemanticRelationshipKind).where(
                SemanticRelationshipKind.id.in_(list(rk_ids)),
                SemanticRelationshipKind.deleted_at.is_(None),
            )
            db_result = await self.db.execute(stmt)
            for rk in db_result.scalars().all():
                rk_map[str(rk.id)] = rk

        # Validate connections
        conn_ids = set()
        conn_pairs = set()
        for conn in connections:
            cid = conn.get("id")
            source = conn.get("source")
            target = conn.get("target")
            rk_id = conn.get("relationship_kind_id") or conn.get("relationshipKindId")

            if not cid:
                result.add_error("Connection missing 'id'")
                continue
            if cid in conn_ids:
                result.add_error(f"Duplicate connection ID '{cid}'")
                continue
            conn_ids.add(cid)

            if not source or not target:
                result.add_error(f"Connection '{cid}' missing source or target")
                continue

            if source not in node_ids:
                result.add_error(f"Connection '{cid}' references unknown source '{source}'")
                continue
            if target not in node_ids:
                result.add_error(f"Connection '{cid}' references unknown target '{target}'")
                continue

            # No self-connections
            if source == target:
                result.add_error(f"Connection '{cid}' is a self-connection on '{source}'")
                continue

            # No duplicate connections (same source, target, relationship kind)
            pair_key = (source, target, rk_id)
            if pair_key in conn_pairs:
                result.add_error(
                    f"Duplicate connection from '{source}' to '{target}' "
                    f"with relationship kind '{rk_id}'"
                )
                continue
            conn_pairs.add(pair_key)

            if not rk_id:
                result.add_error(f"Connection '{cid}' missing 'relationship_kind_id'")
                continue

            if rk_id not in rk_map:
                result.add_error(f"Unknown relationship kind ID '{rk_id}' on connection '{cid}'")
                continue

            # Validate relationship kind is allowed on both source and target types
            source_type = type_map.get(node_type_map.get(source, ""))
            target_type = type_map.get(node_type_map.get(target, ""))
            rk = rk_map[rk_id]

            if source_type and source_type.allowed_relationship_kinds:
                allowed = [str(x) for x in source_type.allowed_relationship_kinds]
                if rk_id not in allowed and rk.name not in allowed:
                    result.add_error(
                        f"Relationship kind '{rk.display_name}' not allowed on "
                        f"source type '{source_type.display_name}'",
                        source,
                    )

            if target_type and target_type.allowed_relationship_kinds:
                allowed = [str(x) for x in target_type.allowed_relationship_kinds]
                if rk_id not in allowed and rk.name not in allowed:
                    result.add_error(
                        f"Relationship kind '{rk.display_name}' not allowed on "
                        f"target type '{target_type.display_name}'",
                        target,
                    )

        # Validate node properties against properties_schema
        for node in nodes:
            nid = node.get("id")
            st_id = node_type_map.get(nid, "")
            st = type_map.get(st_id)
            if not st or not st.properties_schema:
                continue

            props = node.get("properties", {})
            schema = st.properties_schema
            required_fields = schema.get("required", [])
            schema_props = schema.get("properties", {})

            for req in required_fields:
                if req not in props or props[req] is None:
                    result.add_error(
                        f"Missing required property '{req}' for type "
                        f"'{st.display_name}'",
                        nid,
                    )

            for prop_name, prop_value in props.items():
                if prop_name not in schema_props:
                    continue
                prop_def = schema_props[prop_name]
                prop_type = prop_def.get("type")
                if prop_type and not self._check_type(prop_value, prop_type):
                    result.add_error(
                        f"Property '{prop_name}' should be {prop_type} "
                        f"on type '{st.display_name}'",
                        nid,
                    )

                # Enum validation
                if "enum" in prop_def and prop_value not in prop_def["enum"]:
                    result.add_error(
                        f"Property '{prop_name}' value '{prop_value}' not in "
                        f"allowed values {prop_def['enum']}",
                        nid,
                    )

        # Warn about orphan nodes (no connections)
        connected_nodes = set()
        for conn in connections:
            connected_nodes.add(conn.get("source"))
            connected_nodes.add(conn.get("target"))

        for nid in node_ids:
            if nid not in connected_nodes:
                result.add_warning(f"Node '{nid}' has no connections (orphan)", nid)

        # Validate compartments (optional array, backward compatible)
        compartments = graph.get("compartments", [])
        compartment_ids = set()
        compartment_parent_map: dict[str, str | None] = {}

        for comp in compartments:
            cid = comp.get("id")
            if not cid:
                result.add_error("Compartment missing 'id'")
                continue
            if cid in compartment_ids:
                result.add_error(f"Duplicate compartment ID '{cid}'")
                continue
            compartment_ids.add(cid)
            compartment_parent_map[cid] = comp.get("parentCompartmentId")

        # Validate compartment parent references and detect cycles
        for cid, parent_id in compartment_parent_map.items():
            if parent_id and parent_id not in compartment_ids:
                result.add_error(
                    f"Compartment '{cid}' references unknown parent '{parent_id}'"
                )

        # Cycle detection for compartment nesting
        if compartment_ids:
            self._validate_compartment_cycles(
                compartment_parent_map, compartment_ids, result
            )

        # Validate compartment policies
        await self._validate_compartment_policies(compartments, compartment_ids, result)

        # Validate node compartmentId references
        for node in nodes:
            comp_id = node.get("compartmentId")
            if comp_id and comp_id not in compartment_ids:
                result.add_error(
                    f"Node '{node.get('id')}' references unknown compartment '{comp_id}'",
                    node.get("id"),
                )

        # Validate stacks (optional array, backward compatible)
        stacks = graph.get("stacks", [])
        stack_ids = set()

        for stack in stacks:
            sid = stack.get("id")
            if not sid:
                result.add_error("Stack missing 'id'")
                continue
            if sid in stack_ids:
                result.add_error(f"Duplicate stack ID '{sid}'")
                continue
            stack_ids.add(sid)

            # Validate compartmentId reference
            stack_comp = stack.get("compartmentId")
            if stack_comp and stack_comp not in compartment_ids:
                result.add_error(
                    f"Stack '{sid}' references unknown compartment '{stack_comp}'"
                )

            # Validate blueprintId is present
            if not stack.get("blueprintId"):
                result.add_error(f"Stack '{sid}' missing 'blueprintId'")

            # Validate dependsOn references
            depends_on = stack.get("dependsOn", [])
            for dep in depends_on:
                if dep not in stack_ids and dep not in {
                    s.get("id") for s in stacks
                }:
                    result.add_warning(
                        f"Stack '{sid}' depends on unknown stack '{dep}'"
                    )

        # Cycle detection for stack dependencies
        if stack_ids:
            self._validate_stack_dep_cycles(stacks, stack_ids, result)

        return result

    @staticmethod
    def _validate_compartment_cycles(
        parent_map: dict[str, str | None],
        compartment_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """Detect cycles in compartment nesting hierarchy."""
        visited: set[str] = set()
        for cid in compartment_ids:
            if cid in visited:
                continue
            path: set[str] = set()
            current: str | None = cid
            while current and current not in visited:
                if current in path:
                    result.add_error(
                        f"Compartment nesting cycle detected involving '{current}'"
                    )
                    break
                path.add(current)
                current = parent_map.get(current)
            visited.update(path)

    @staticmethod
    def _validate_stack_dep_cycles(
        stacks: list[dict[str, Any]],
        stack_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """Detect cycles in stack dependsOn relationships via DFS."""
        adj: dict[str, list[str]] = {sid: [] for sid in stack_ids}
        for stack in stacks:
            sid = stack.get("id")
            if not sid or sid not in adj:
                continue
            for dep in stack.get("dependsOn", []):
                if dep in adj:
                    adj[sid].append(dep)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {sid: WHITE for sid in stack_ids}

        for start in stack_ids:
            if color[start] != WHITE:
                continue
            stack_dfs: list[str] = [start]
            while stack_dfs:
                node = stack_dfs[-1]
                if color[node] == WHITE:
                    color[node] = GRAY
                    for neighbor in adj.get(node, []):
                        if color.get(neighbor) == GRAY:
                            result.add_error(
                                f"Stack dependency cycle detected involving '{neighbor}'"
                            )
                        elif color.get(neighbor) == WHITE:
                            stack_dfs.append(neighbor)
                else:
                    stack_dfs.pop()
                    color[node] = BLACK

    async def _validate_compartment_policies(
        self,
        compartments: list[dict[str, Any]],
        compartment_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """Validate policy attachments on compartments."""
        for comp in compartments:
            cid = comp.get("id", "")
            policies = comp.get("policies", [])
            if not isinstance(policies, list):
                result.add_error(f"Compartment '{cid}': 'policies' must be an array")
                continue

            for i, pol_ref in enumerate(policies):
                prefix = f"Compartment '{cid}' policy {i}"
                policy_id = pol_ref.get("policyId")
                inline = pol_ref.get("inline")

                # Must have policyId XOR inline, not both
                if policy_id and inline:
                    result.add_error(
                        f"{prefix}: cannot specify both 'policyId' and 'inline'"
                    )
                    continue
                if not policy_id and not inline:
                    result.add_error(
                        f"{prefix}: must specify either 'policyId' or 'inline'"
                    )
                    continue

                # Validate inherit field
                inherit = pol_ref.get("inherit")
                if inherit is not None and not isinstance(inherit, bool):
                    result.add_error(f"{prefix}: 'inherit' must be a boolean")

                if policy_id:
                    # Validate library reference exists and is accessible
                    try:
                        stmt = select(PolicyLibraryEntry).where(
                            PolicyLibraryEntry.id == policy_id,
                            PolicyLibraryEntry.deleted_at.is_(None),
                        )
                        db_result = await self.db.execute(stmt)
                        entry = db_result.scalar_one_or_none()
                        if not entry:
                            result.add_error(
                                f"{prefix}: policy library entry '{policy_id}' not found"
                            )
                        else:
                            # Validate variable overrides match schema
                            overrides = pol_ref.get("variableOverrides", {})
                            if overrides and entry.variables:
                                for key in overrides:
                                    if key not in entry.variables:
                                        result.add_warning(
                                            f"{prefix}: variable override '{key}' "
                                            f"not defined in policy '{entry.name}'"
                                        )
                    except Exception:
                        result.add_error(
                            f"{prefix}: invalid policyId format '{policy_id}'"
                        )

                elif inline:
                    # Validate inline policy structure
                    if not isinstance(inline, dict):
                        result.add_error(f"{prefix}: 'inline' must be an object")
                        continue

                    if not inline.get("name"):
                        result.add_error(f"{prefix}: inline policy must have a 'name'")

                    stmts = inline.get("statements", [])
                    if not stmts:
                        result.add_error(
                            f"{prefix}: inline policy must have at least one statement"
                        )
                    else:
                        for j, stmt in enumerate(stmts):
                            stmt_prefix = f"{prefix} statement {j}"
                            if not stmt.get("sid"):
                                result.add_error(f"{stmt_prefix}: missing 'sid'")
                            if stmt.get("effect") not in ("allow", "deny"):
                                result.add_error(
                                    f"{stmt_prefix}: effect must be 'allow' or 'deny'"
                                )
                            if not stmt.get("actions"):
                                result.add_error(f"{stmt_prefix}: missing 'actions'")
                            if not stmt.get("resources"):
                                result.add_error(f"{stmt_prefix}: missing 'resources'")

                            # Validate ABAC condition expression
                            condition = stmt.get("condition")
                            if condition:
                                try:
                                    import re

                                    from app.services.permission.abac.parser import ABACParser
                                    from app.services.permission.abac.tokenizer import tokenize

                                    clean = re.sub(r"\{\{\w+\}\}", "null", condition)
                                    tokens = tokenize(clean)
                                    ABACParser(tokens).parse()
                                except Exception as e:
                                    result.add_error(
                                        f"{stmt_prefix}: invalid condition: {e}"
                                    )

            # Validate suppressedPolicies
            suppressed = comp.get("suppressedPolicies", [])
            if suppressed and not isinstance(suppressed, list):
                result.add_error(
                    f"Compartment '{cid}': 'suppressedPolicies' must be an array"
                )
            elif isinstance(suppressed, list):
                for name in suppressed:
                    if not isinstance(name, str):
                        result.add_error(
                            f"Compartment '{cid}': suppressedPolicies entries must be strings"
                        )

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected JSON Schema type."""
        if value is None:
            return True
        type_checks = {
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)),
            "integer": lambda v: isinstance(v, int),
            "boolean": lambda v: isinstance(v, bool),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
        }
        checker = type_checks.get(expected_type)
        return checker(value) if checker else True
