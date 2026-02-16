"""
Overview: Provider hierarchy registry — defines valid organizational hierarchy levels per cloud provider.
Architecture: Landing zone hierarchy definitions (Section 7.2)
Dependencies: dataclasses
Concepts: Each provider has a fixed set of hierarchy levels (org, management group, subscription, etc.)
    with valid parent-child relationships. The registry is used to validate landing zone hierarchy trees
    and to populate the palette in the frontend hierarchy designer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HierarchyLevelDef:
    """Defines a single level in a provider's organizational hierarchy."""
    type_id: str
    label: str
    icon: str
    allowed_children: list[str] = field(default_factory=list)
    supports_ipam: bool = False
    supports_tags: bool = False
    supports_environment: bool = False
    config_schema: dict | None = None


@dataclass
class ProviderHierarchy:
    """Defines the complete hierarchy structure for a provider."""
    provider_name: str
    root_type: str
    levels: list[HierarchyLevelDef] = field(default_factory=list)

    def get_level(self, type_id: str) -> HierarchyLevelDef | None:
        for level in self.levels:
            if level.type_id == type_id:
                return level
        return None

    def get_allowed_children(self, parent_type_id: str) -> list[HierarchyLevelDef]:
        parent = self.get_level(parent_type_id)
        if not parent:
            return []
        return [lv for lv in self.levels if lv.type_id in parent.allowed_children]


# ── Azure Hierarchy ───────────────────────────────────────────────────

AZURE_HIERARCHY = ProviderHierarchy(
    provider_name="azure",
    root_type="organization",
    levels=[
        HierarchyLevelDef(
            type_id="organization",
            label="Organization",
            icon="domain",
            allowed_children=["management_group"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="management_group",
            label="Management Group",
            icon="account_tree",
            allowed_children=["management_group", "subscription"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="subscription",
            label="Subscription",
            icon="folder",
            allowed_children=["resource_group"],
            supports_tags=True,
            supports_environment=True,
        ),
        HierarchyLevelDef(
            type_id="resource_group",
            label="Resource Group",
            icon="folder_open",
            allowed_children=["vnet"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="vnet",
            label="Virtual Network",
            icon="lan",
            allowed_children=["subnet"],
            supports_ipam=True,
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="subnet",
            label="Subnet",
            icon="hub",
            allowed_children=[],
            supports_ipam=True,
            supports_tags=True,
        ),
    ],
)


# ── AWS Hierarchy ─────────────────────────────────────────────────────

AWS_HIERARCHY = ProviderHierarchy(
    provider_name="aws",
    root_type="organization",
    levels=[
        HierarchyLevelDef(
            type_id="organization",
            label="Organization",
            icon="domain",
            allowed_children=["ou"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="ou",
            label="Organizational Unit",
            icon="account_tree",
            allowed_children=["ou", "account"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="account",
            label="Account",
            icon="folder",
            allowed_children=["vpc"],
            supports_tags=True,
            supports_environment=True,
        ),
        HierarchyLevelDef(
            type_id="vpc",
            label="VPC",
            icon="lan",
            allowed_children=["subnet"],
            supports_ipam=True,
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="subnet",
            label="Subnet",
            icon="hub",
            allowed_children=[],
            supports_ipam=True,
            supports_tags=True,
        ),
    ],
)


# ── GCP Hierarchy ─────────────────────────────────────────────────────

GCP_HIERARCHY = ProviderHierarchy(
    provider_name="gcp",
    root_type="organization",
    levels=[
        HierarchyLevelDef(
            type_id="organization",
            label="Organization",
            icon="domain",
            allowed_children=["folder"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="folder",
            label="Folder",
            icon="folder",
            allowed_children=["folder", "project"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="project",
            label="Project",
            icon="folder_open",
            allowed_children=["vpc"],
            supports_tags=True,
            supports_environment=True,
        ),
        HierarchyLevelDef(
            type_id="vpc",
            label="VPC Network",
            icon="lan",
            allowed_children=["subnet"],
            supports_ipam=True,
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="subnet",
            label="Subnet",
            icon="hub",
            allowed_children=[],
            supports_ipam=True,
            supports_tags=True,
        ),
    ],
)


# ── OCI Hierarchy ─────────────────────────────────────────────────────

OCI_HIERARCHY = ProviderHierarchy(
    provider_name="oci",
    root_type="tenancy",
    levels=[
        HierarchyLevelDef(
            type_id="tenancy",
            label="Tenancy",
            icon="domain",
            allowed_children=["compartment"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="compartment",
            label="Compartment",
            icon="folder",
            allowed_children=["compartment", "vcn"],
            supports_tags=True,
            supports_environment=True,
        ),
        HierarchyLevelDef(
            type_id="vcn",
            label="VCN",
            icon="lan",
            allowed_children=["subnet"],
            supports_ipam=True,
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="subnet",
            label="Subnet",
            icon="hub",
            allowed_children=[],
            supports_ipam=True,
            supports_tags=True,
        ),
    ],
)


# ── Proxmox Hierarchy ────────────────────────────────────────────────

PROXMOX_HIERARCHY = ProviderHierarchy(
    provider_name="proxmox",
    root_type="datacenter",
    levels=[
        HierarchyLevelDef(
            type_id="datacenter",
            label="Datacenter",
            icon="domain",
            allowed_children=["cluster"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="cluster",
            label="Cluster",
            icon="dns",
            allowed_children=["pool"],
            supports_tags=True,
        ),
        HierarchyLevelDef(
            type_id="pool",
            label="Resource Pool",
            icon="folder",
            allowed_children=["bridge"],
            supports_tags=True,
            supports_environment=True,
        ),
        HierarchyLevelDef(
            type_id="bridge",
            label="Network Bridge",
            icon="lan",
            allowed_children=[],
            supports_ipam=True,
            supports_tags=True,
        ),
    ],
)


# ── Registry ──────────────────────────────────────────────────────────

_HIERARCHIES: dict[str, ProviderHierarchy] = {
    "azure": AZURE_HIERARCHY,
    "aws": AWS_HIERARCHY,
    "gcp": GCP_HIERARCHY,
    "oci": OCI_HIERARCHY,
    "proxmox": PROXMOX_HIERARCHY,
}


def get_hierarchy(provider_name: str) -> ProviderHierarchy | None:
    """Return the hierarchy definition for a provider."""
    return _HIERARCHIES.get(provider_name.lower())


def get_level_def(provider_name: str, type_id: str) -> HierarchyLevelDef | None:
    """Return a specific level definition."""
    h = get_hierarchy(provider_name)
    return h.get_level(type_id) if h else None


def validate_parent_child(provider_name: str, parent_type_id: str, child_type_id: str) -> bool:
    """Check if a child type is valid under a given parent type."""
    h = get_hierarchy(provider_name)
    if not h:
        return False
    parent = h.get_level(parent_type_id)
    if not parent:
        return False
    return child_type_id in parent.allowed_children


def get_allowed_children(provider_name: str, parent_type_id: str) -> list[HierarchyLevelDef]:
    """Return the allowed child level definitions for a given parent type."""
    h = get_hierarchy(provider_name)
    if not h:
        return []
    return h.get_allowed_children(parent_type_id)
