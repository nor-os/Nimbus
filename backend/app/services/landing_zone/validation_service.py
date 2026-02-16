"""
Overview: Landing zone validation service — readiness checks and CIDR overlap detection.
Architecture: Validation layer for landing zone publish readiness (Section 7.2)
Dependencies: ipaddress, sqlalchemy, app.models.landing_zone, app.models.cloud_backend, app.models.ipam
Concepts: Readiness checks determine whether a landing zone is safe to publish. Each check
    returns pass/warning/error status. CIDR overlap detection prevents conflicting address spaces.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_backend import CloudBackend
from app.models.ipam import AddressSpace
from app.models.landing_zone import LandingZone


@dataclass
class ValidationCheck:
    key: str
    label: str
    status: str  # "pass", "warning", "error"
    message: str


@dataclass
class ValidationResult:
    ready: bool
    checks: list[ValidationCheck]


class LandingZoneValidationService:
    """Validates a landing zone for publish readiness."""

    async def validate(self, db: AsyncSession, zone_id) -> ValidationResult:
        """Run all readiness checks against a landing zone."""
        zone = await db.get(LandingZone, zone_id)
        if not zone:
            return ValidationResult(
                ready=False,
                checks=[ValidationCheck("zone_exists", "Landing zone exists", "error", "Landing zone not found")],
            )

        checks: list[ValidationCheck] = []

        # 1. Credentials configured
        backend = await db.get(CloudBackend, zone.backend_id)
        if backend and backend.has_credentials:
            checks.append(ValidationCheck("credentials", "Credentials configured", "pass", "Backend has credentials set"))
        else:
            checks.append(ValidationCheck("credentials", "Credentials configured", "error", "Backend has no credentials. Configure them before publishing."))

        # 2. At least one region
        regions = zone.regions or []
        if len(regions) >= 1:
            checks.append(ValidationCheck("regions", "At least one region", "pass", f"{len(regions)} region(s) configured"))
        else:
            checks.append(ValidationCheck("regions", "At least one region", "error", "Add at least one deployment region"))

        # 3. Primary region set
        has_primary = any(r.is_primary for r in regions)
        if has_primary:
            checks.append(ValidationCheck("primary_region", "Primary region set", "pass", "Primary region is designated"))
        elif len(regions) > 0:
            checks.append(ValidationCheck("primary_region", "Primary region set", "warning", "No primary region designated. Consider marking one."))
        else:
            checks.append(ValidationCheck("primary_region", "Primary region set", "warning", "No regions to set as primary"))

        # 4. Network config present
        if zone.network_config:
            checks.append(ValidationCheck("network_config", "Network configuration", "pass", "Network config is defined"))
        else:
            checks.append(ValidationCheck("network_config", "Network configuration", "error", "Network configuration is required"))

        # 5. IAM config present
        if zone.iam_config:
            checks.append(ValidationCheck("iam_config", "IAM configuration", "pass", "IAM config is defined"))
        else:
            checks.append(ValidationCheck("iam_config", "IAM configuration", "warning", "No IAM configuration defined"))

        # 6. Security config present
        if zone.security_config:
            checks.append(ValidationCheck("security_config", "Security configuration", "pass", "Security config is defined"))
        else:
            checks.append(ValidationCheck("security_config", "Security configuration", "warning", "No security configuration defined"))

        # 7. Tag policies exist
        tag_policies = zone.tag_policies or []
        if len(tag_policies) > 0:
            checks.append(ValidationCheck("tag_policies", "Tag policies defined", "pass", f"{len(tag_policies)} tag policy(ies) configured"))
        else:
            checks.append(ValidationCheck("tag_policies", "Tag policies defined", "warning", "No tag policies defined. Consider adding governance tags."))

        # 8. Address space defined
        stmt = select(AddressSpace).where(AddressSpace.landing_zone_id == zone_id)
        result = await db.execute(stmt)
        spaces = result.scalars().all()
        if len(spaces) > 0:
            checks.append(ValidationCheck("address_space", "Address space defined", "pass", f"{len(spaces)} address space(s)"))
        else:
            checks.append(ValidationCheck("address_space", "Address space defined", "warning", "No address spaces defined"))

        # 9. CIDR overlap check
        overlap = self._check_cidr_overlaps(spaces)
        if overlap:
            checks.append(ValidationCheck("cidr_overlap", "No CIDR overlaps", "error", overlap))
        else:
            checks.append(ValidationCheck("cidr_overlap", "No CIDR overlaps", "pass", "No overlapping address spaces"))

        # 10. Topology or hierarchy defined
        if zone.hierarchy and zone.hierarchy.get("nodes"):
            checks.append(ValidationCheck("hierarchy", "Hierarchy defined", "pass",
                                          f"{len(zone.hierarchy['nodes'])} hierarchy node(s)"))
            # Run hierarchy-specific validations
            checks.extend(self._validate_hierarchy(zone))
        elif zone.topology_id:
            checks.append(ValidationCheck("topology", "Topology attached", "pass", "Architecture topology is linked"))
        else:
            checks.append(ValidationCheck("hierarchy", "Hierarchy defined", "warning",
                                          "No hierarchy or topology defined"))

        # Determine overall readiness: no errors means ready
        ready = all(c.status != "error" for c in checks)

        return ValidationResult(ready=ready, checks=checks)

    @staticmethod
    def _validate_hierarchy(zone: LandingZone) -> list[ValidationCheck]:
        """Validate hierarchy structure and IPAM containment."""
        from app.services.landing_zone.hierarchy_registry import get_hierarchy

        checks: list[ValidationCheck] = []
        hierarchy = zone.hierarchy
        if not hierarchy or not hierarchy.get("nodes"):
            return checks

        nodes = hierarchy["nodes"]
        nodes_by_id = {n["id"]: n for n in nodes}

        # Resolve provider name from backend
        provider_name = ""
        if hasattr(zone, "backend") and zone.backend:
            if hasattr(zone.backend, "provider") and zone.backend.provider:
                provider_name = zone.backend.provider.name.lower()

        provider_def = get_hierarchy(provider_name) if provider_name else None

        # Check 1: Valid parent-child relationships
        if provider_def:
            invalid_pairs: list[str] = []
            for node in nodes:
                parent_id = node.get("parentId")
                if not parent_id:
                    continue
                parent = nodes_by_id.get(parent_id)
                if not parent:
                    invalid_pairs.append(f"'{node['label']}' references missing parent")
                    continue
                parent_def = provider_def.get_level(parent["typeId"])
                if parent_def and node["typeId"] not in parent_def.allowed_children:
                    invalid_pairs.append(
                        f"'{node['label']}' ({node['typeId']}) under '{parent['label']}' ({parent['typeId']})"
                    )

            if invalid_pairs:
                checks.append(ValidationCheck(
                    "hierarchy_structure", "Valid hierarchy structure", "error",
                    f"Invalid parent-child: {'; '.join(invalid_pairs[:3])}"
                ))
            else:
                checks.append(ValidationCheck(
                    "hierarchy_structure", "Valid hierarchy structure", "pass",
                    "All parent-child relationships are valid"
                ))

        # Check 2: IPAM containment — child CIDRs must be within parent CIDRs
        ipam_errors: list[str] = []
        for node in nodes:
            node_props = node.get("properties") or {}
            node_cidr = (node_props.get("ipam") or {}).get("cidr")
            if not node_cidr:
                continue
            parent_id = node.get("parentId")
            if not parent_id:
                continue
            parent = nodes_by_id.get(parent_id)
            if not parent:
                continue
            parent_props = parent.get("properties") or {}
            parent_cidr = (parent_props.get("ipam") or {}).get("cidr")
            if not parent_cidr:
                continue

            try:
                child_net = ipaddress.ip_network(node_cidr, strict=False)
                parent_net = ipaddress.ip_network(parent_cidr, strict=False)
                if not child_net.subnet_of(parent_net):
                    ipam_errors.append(
                        f"'{node['label']}' ({node_cidr}) not within '{parent['label']}' ({parent_cidr})"
                    )
            except ValueError:
                pass  # Invalid CIDRs are caught elsewhere

        if ipam_errors:
            checks.append(ValidationCheck(
                "ipam_containment", "IPAM containment", "error",
                f"CIDR not contained: {'; '.join(ipam_errors[:3])}"
            ))

        # Check 3: Sibling CIDR overlap
        siblings_by_parent: dict[str, list[dict]] = {}
        for node in nodes:
            pid = node.get("parentId") or "__root__"
            siblings_by_parent.setdefault(pid, []).append(node)

        overlap_errors: list[str] = []
        for siblings in siblings_by_parent.values():
            cidrs: list[tuple[str, ipaddress.IPv4Network | ipaddress.IPv6Network]] = []
            for sib in siblings:
                sib_props = sib.get("properties") or {}
                sib_cidr = (sib_props.get("ipam") or {}).get("cidr")
                if not sib_cidr:
                    continue
                try:
                    cidrs.append((sib["label"], ipaddress.ip_network(sib_cidr, strict=False)))
                except ValueError:
                    pass

            for i, (name_a, net_a) in enumerate(cidrs):
                for name_b, net_b in cidrs[i + 1:]:
                    if net_a.overlaps(net_b):
                        overlap_errors.append(f"'{name_a}' ({net_a}) overlaps '{name_b}' ({net_b})")

        if overlap_errors:
            checks.append(ValidationCheck(
                "ipam_sibling_overlap", "No sibling CIDR overlaps", "error",
                f"Overlapping siblings: {'; '.join(overlap_errors[:3])}"
            ))

        return checks

    @staticmethod
    def _check_cidr_overlaps(spaces) -> str | None:
        """Check if any address space CIDRs overlap with each other."""
        networks: list[tuple[str, ipaddress.IPv4Network | ipaddress.IPv6Network]] = []
        for s in spaces:
            try:
                net = ipaddress.ip_network(s.cidr, strict=False)
                networks.append((s.name, net))
            except ValueError:
                return f"Invalid CIDR '{s.cidr}' in address space '{s.name}'"

        for i, (name_a, net_a) in enumerate(networks):
            for name_b, net_b in networks[i + 1:]:
                if net_a.overlaps(net_b):
                    return f"Address spaces '{name_a}' ({net_a}) and '{name_b}' ({net_b}) overlap"

        return None
