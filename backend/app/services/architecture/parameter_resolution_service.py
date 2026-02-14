"""
Overview: Parameter resolution service — resolves stack instance parameters against the precedence chain.
Architecture: Service layer for stack parameter resolution within topologies (Section 5)
Dependencies: sqlalchemy, app.services.architecture.topology_service, app.services.tenant.tag_service,
    app.services.cmdb.cluster_service, app.services.cmdb.parameter_service
Concepts: Resolution precedence: Explicit > Tag Reference > Compartment Default > Blueprint Default > Unresolved.
    Deployment order via topological sort of stack dependsOn relationships.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.architecture.topology_service import TopologyService

logger = logging.getLogger(__name__)


@dataclass
class ResolvedParameter:
    name: str
    display_name: str
    value: Any
    source: str  # 'explicit', 'tag_ref', 'compartment_default', 'blueprint_default', 'unresolved'
    is_required: bool = False
    tag_key: str | None = None


@dataclass
class StackResolution:
    stack_id: str
    stack_label: str
    blueprint_id: str
    parameters: list[ResolvedParameter] = field(default_factory=list)
    is_complete: bool = True
    unresolved_count: int = 0


@dataclass
class ResolutionPreview:
    topology_id: str
    stacks: list[StackResolution] = field(default_factory=list)
    deployment_order: list[list[str]] = field(default_factory=list)
    all_complete: bool = True
    total_unresolved: int = 0


class ParameterResolutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_stack_parameters(
        self,
        tenant_id: str,
        topology_id: str,
        stack_node_id: str,
    ) -> list[ResolvedParameter]:
        """Resolve parameters for a single stack instance."""
        topology = await self._get_topology(tenant_id, topology_id)
        if not topology or not topology.graph:
            return []

        graph = topology.graph
        stacks = graph.get("stacks", [])
        stack = next((s for s in stacks if s.get("id") == stack_node_id), None)
        if not stack:
            return []

        return await self._resolve_stack(tenant_id, graph, stack)

    async def resolve_all_stacks(
        self,
        tenant_id: str,
        topology_id: str,
    ) -> dict[str, list[ResolvedParameter]]:
        """Resolve parameters for all stack instances in a topology."""
        topology = await self._get_topology(tenant_id, topology_id)
        if not topology or not topology.graph:
            return {}

        graph = topology.graph
        result: dict[str, list[ResolvedParameter]] = {}
        for stack in graph.get("stacks", []):
            sid = stack.get("id")
            if sid:
                result[sid] = await self._resolve_stack(tenant_id, graph, stack)

        return result

    async def preview_resolution(
        self,
        tenant_id: str,
        topology_id: str,
    ) -> ResolutionPreview:
        """Full preview with deployment order and per-stack resolution."""
        topology = await self._get_topology(tenant_id, topology_id)
        if not topology or not topology.graph:
            return ResolutionPreview(topology_id=topology_id)

        graph = topology.graph
        deployment_order = TopologyService.get_deployment_order(graph)

        preview = ResolutionPreview(
            topology_id=topology_id,
            deployment_order=deployment_order,
        )

        for stack in graph.get("stacks", []):
            sid = stack.get("id")
            if not sid:
                continue

            resolved = await self._resolve_stack(tenant_id, graph, stack)
            unresolved = sum(1 for p in resolved if p.source == "unresolved" and p.is_required)
            is_complete = unresolved == 0

            sr = StackResolution(
                stack_id=sid,
                stack_label=stack.get("label", sid),
                blueprint_id=stack.get("blueprintId", ""),
                parameters=resolved,
                is_complete=is_complete,
                unresolved_count=unresolved,
            )
            preview.stacks.append(sr)
            preview.total_unresolved += unresolved

        preview.all_complete = preview.total_unresolved == 0
        return preview

    async def validate_completeness(
        self,
        tenant_id: str,
        topology_id: str,
    ) -> tuple[bool, list[str]]:
        """Check all required parameters are resolved. Returns (complete, issues)."""
        preview = await self.preview_resolution(tenant_id, topology_id)
        issues: list[str] = []
        for sr in preview.stacks:
            for p in sr.parameters:
                if p.source == "unresolved" and p.is_required:
                    issues.append(
                        f"Stack '{sr.stack_label}' has unresolved required parameter '{p.name}'"
                    )
        return preview.all_complete, issues

    def compute_deployment_order(
        self,
        graph: dict[str, Any],
        subset: set[str] | None = None,
    ) -> list[list[str]]:
        """Topological sort into parallel groups. Optionally filter to a subset."""
        groups = TopologyService.get_deployment_order(graph)
        if subset is None:
            return groups
        return [
            [sid for sid in group if sid in subset]
            for group in groups
            if any(sid in subset for sid in group)
        ]

    # ── Private Helpers ─────────────────────────────────────────

    async def _resolve_stack(
        self,
        tenant_id: str,
        graph: dict[str, Any],
        stack: dict[str, Any],
    ) -> list[ResolvedParameter]:
        """Resolve parameters for one stack against the precedence chain."""
        blueprint_id = stack.get("blueprintId")
        if not blueprint_id:
            return []

        # Load blueprint parameters
        bp_params = await self._get_blueprint_params(blueprint_id, tenant_id)
        if not bp_params:
            return []

        overrides = stack.get("parameterOverrides", {})
        compartment_id = stack.get("compartmentId")
        comp_defaults = (
            TopologyService.resolve_compartment_defaults(graph, compartment_id)
            if compartment_id
            else {}
        )

        resolved: list[ResolvedParameter] = []
        for param in bp_params:
            rp = await self._resolve_single(
                tenant_id, param, overrides, comp_defaults
            )
            resolved.append(rp)

        return resolved

    async def _resolve_single(
        self,
        tenant_id: str,
        param: dict[str, Any],
        overrides: dict[str, Any],
        compartment_defaults: dict[str, Any],
    ) -> ResolvedParameter:
        """
        Resolution precedence:
        1. Explicit value (from stack's parameterOverrides)
        2. Tag reference (resolve tenant tag key -> value)
        3. Compartment default (from merged parent chain)
        4. Blueprint parameter default
        5. Unresolved
        """
        name = param["name"]
        display_name = param.get("display_name", name)
        is_required = param.get("is_required", False)
        default_value = param.get("default_value")

        override = overrides.get(name)

        # 1. Explicit value
        if override and override.get("type") == "explicit":
            return ResolvedParameter(
                name=name,
                display_name=display_name,
                value=override.get("value"),
                source="explicit",
                is_required=is_required,
            )

        # 2. Tag reference
        if override and override.get("type") == "tag_ref":
            tag_key = override.get("tagKey")
            if tag_key:
                tag_value = await self._resolve_tag(tenant_id, tag_key)
                if tag_value is not None:
                    return ResolvedParameter(
                        name=name,
                        display_name=display_name,
                        value=tag_value,
                        source="tag_ref",
                        is_required=is_required,
                        tag_key=tag_key,
                    )

        # 3. Compartment default
        if name in compartment_defaults:
            return ResolvedParameter(
                name=name,
                display_name=display_name,
                value=compartment_defaults[name],
                source="compartment_default",
                is_required=is_required,
            )

        # 4. Blueprint default
        if default_value is not None:
            return ResolvedParameter(
                name=name,
                display_name=display_name,
                value=default_value,
                source="blueprint_default",
                is_required=is_required,
            )

        # 5. Unresolved
        return ResolvedParameter(
            name=name,
            display_name=display_name,
            value=None,
            source="unresolved",
            is_required=is_required,
        )

    async def _get_topology(self, tenant_id: str, topology_id: str) -> Any:
        """Load topology via TopologyService."""
        from app.services.architecture.topology_service import TopologyService as TS
        svc = TS(self.db)
        return await svc.get(tenant_id, topology_id)

    async def _get_blueprint_params(
        self, blueprint_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        """Load parameter definitions from a service cluster blueprint."""
        try:
            from app.services.cmdb.parameter_service import StackParameterService
            param_svc = StackParameterService(self.db)
            params = await param_svc.list_parameters(blueprint_id)
            return [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "is_required": p.is_required,
                    "default_value": p.default_value,
                    "parameter_schema": p.parameter_schema,
                }
                for p in params
            ]
        except Exception:
            logger.debug("Could not load blueprint params for %s", blueprint_id, exc_info=True)
            return []

    async def _resolve_tag(self, tenant_id: str, tag_key: str) -> Any:
        """Resolve a tenant tag value by key."""
        try:
            from app.services.tenant.tag_service import TenantTagService
            tag_svc = TenantTagService(self.db)
            return await tag_svc.resolve_tag_value(tenant_id, tag_key)
        except Exception:
            logger.debug("Could not resolve tag '%s' for tenant %s", tag_key, tenant_id, exc_info=True)
            return None
