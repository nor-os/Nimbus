"""
Overview: Policy resolution service — resolves compartment policies with inheritance and suppression.
Architecture: Service layer for compartment policy resolution (Section 5)
Dependencies: sqlalchemy, app.services.architecture.topology_service, app.services.policy.policy_library_service
Concepts: Policy inheritance walks compartment hierarchy root-first, innermost compartment always included.
    Suppressed policies are removed unless they contain deny statements.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.architecture.topology_service import TopologyService
from app.services.policy.data_classes import PolicySummary, ResolvedPolicy
from app.services.policy.policy_library_service import PolicyLibraryService

logger = logging.getLogger(__name__)


class PolicyResolutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._topology_svc = TopologyService(db)
        self._policy_svc = PolicyLibraryService(db)

    async def resolve_compartment_policies(
        self,
        tenant_id: str,
        topology_id: str,
        compartment_id: str,
    ) -> list[ResolvedPolicy]:
        """Resolve all policies for a compartment including inheritance chain."""
        topology = await self._topology_svc.get(tenant_id, topology_id)
        if not topology or not topology.graph:
            return []

        graph = topology.graph

        # Get compartment chain innermost-first, then reverse to root-first
        chain = TopologyService.resolve_compartment_chain(graph, compartment_id)
        chain_root_first = list(reversed(chain))

        # Build compartment lookup for quick access
        comp_map: dict[str, dict[str, Any]] = {}
        for comp in graph.get("compartments", []):
            comp_map[comp.get("id", "")] = comp

        all_resolved: list[ResolvedPolicy] = []

        for i, comp in enumerate(chain_root_first):
            cid = comp.get("id", "")
            is_target = cid == compartment_id
            policies = comp.get("policies", [])

            for pol_ref in policies:
                # Only inherit if inherit=True or this is the target compartment
                should_include = is_target or pol_ref.get("inherit", True)
                if not should_include:
                    continue

                resolved = await self._resolve_policy_ref(
                    tenant_id, pol_ref, cid, is_target
                )
                if resolved:
                    all_resolved.append(resolved)

        # Apply suppression from target compartment
        target_comp = comp_map.get(compartment_id, {})
        suppressed_names = set(target_comp.get("suppressedPolicies", []))

        if suppressed_names:
            final: list[ResolvedPolicy] = []
            for pol in all_resolved:
                if pol.name in suppressed_names and pol.source_compartment_id != compartment_id:
                    # Only suppress inherited policies, and only if they can be suppressed
                    if pol.can_suppress:
                        continue
                    else:
                        logger.warning(
                            "Cannot suppress deny policy '%s' in compartment '%s'",
                            pol.name,
                            compartment_id,
                        )
                final.append(pol)
            return final

        return all_resolved

    async def resolve_all_compartments(
        self,
        tenant_id: str,
        topology_id: str,
    ) -> dict[str, list[ResolvedPolicy]]:
        """Resolve policies for all compartments in a topology."""
        topology = await self._topology_svc.get(tenant_id, topology_id)
        if not topology or not topology.graph:
            return {}

        result: dict[str, list[ResolvedPolicy]] = {}
        for comp in topology.graph.get("compartments", []):
            cid = comp.get("id", "")
            if cid:
                result[cid] = await self.resolve_compartment_policies(
                    tenant_id, topology_id, cid
                )
        return result

    async def get_policy_summary(
        self,
        tenant_id: str,
        topology_id: str,
        compartment_id: str,
    ) -> PolicySummary:
        """Get aggregated policy statistics for a compartment."""
        resolved = await self.resolve_compartment_policies(
            tenant_id, topology_id, compartment_id
        )

        direct = 0
        inherited = 0
        total_statements = 0
        deny_count = 0
        allow_count = 0

        for pol in resolved:
            if pol.source_compartment_id == compartment_id:
                direct += 1
            else:
                inherited += 1

            for stmt in pol.statements:
                total_statements += 1
                if stmt.get("effect") == "deny":
                    deny_count += 1
                elif stmt.get("effect") == "allow":
                    allow_count += 1

        return PolicySummary(
            compartment_id=compartment_id,
            direct_policies=direct,
            inherited_policies=inherited,
            total_statements=total_statements,
            deny_count=deny_count,
            allow_count=allow_count,
        )

    async def _resolve_policy_ref(
        self,
        tenant_id: str,
        pol_ref: dict[str, Any],
        compartment_id: str,
        is_target: bool,
    ) -> ResolvedPolicy | None:
        """Resolve a single policy reference (library or inline)."""
        policy_id_ref = pol_ref.get("policyId")
        inline_def = pol_ref.get("inline")
        overrides = pol_ref.get("variableOverrides")

        if policy_id_ref:
            # Library policy
            entry = await self._policy_svc.get(tenant_id, policy_id_ref)
            if not entry:
                logger.warning(
                    "Policy library entry '%s' not found for compartment '%s'",
                    policy_id_ref,
                    compartment_id,
                )
                return None

            statements = PolicyLibraryService.substitute_variables(
                entry.statements if isinstance(entry.statements, list) else [],
                entry.variables,
                overrides,
            )

            has_deny = any(s.get("effect") == "deny" for s in statements)
            source = "library" if is_target else "inherited_library"

            return ResolvedPolicy(
                policy_id=str(entry.id),
                name=entry.name,
                source=source,
                source_compartment_id=compartment_id,
                statements=statements,
                severity=entry.severity.value if hasattr(entry.severity, "value") else str(entry.severity),
                category=entry.category.value if hasattr(entry.category, "value") else str(entry.category),
                can_suppress=not has_deny,
            )

        elif inline_def:
            # Inline policy
            name = inline_def.get("name", f"inline-{compartment_id}")
            statements = inline_def.get("statements", [])
            has_deny = any(s.get("effect") == "deny" for s in statements)
            source = "inline" if is_target else "inherited_inline"

            return ResolvedPolicy(
                policy_id=f"inline-{compartment_id}-{name}",
                name=name,
                source=source,
                source_compartment_id=compartment_id,
                statements=statements,
                severity=inline_def.get("severity", "MEDIUM"),
                category=inline_def.get("category", "IAM"),
                can_suppress=not has_deny,
            )

        return None
