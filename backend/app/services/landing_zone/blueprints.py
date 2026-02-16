"""
Overview: Landing zone blueprint definitions — pre-built hierarchy templates per provider and complexity tier.
Architecture: Blueprint data layer for landing zone guided setup (Section 7.2)
Dependencies: None (pure data module)
Concepts: Blueprints are pre-built organizational hierarchies + landing zone config defaults.
    Each provider has 3 tiers (simple, standard, enterprise). Blueprints include a hierarchy
    (flat list of nodes with parentId references) and default LZ config values.
"""

from __future__ import annotations

_next_id = 0


def _h(id: str, label: str, type_id: str, parent_id: str | None = None,
       properties: dict | None = None) -> dict:
    """Helper to build a hierarchy node."""
    return {
        "id": id,
        "label": label,
        "typeId": type_id,
        "parentId": parent_id,
        "properties": properties or {},
    }


# ── Proxmox Blueprints ──────────────────────────────────────────────────

PROXMOX_SIMPLE: dict = {
    "id": "proxmox-simple",
    "name": "Simple",
    "providerName": "proxmox",
    "complexity": "basic",
    "description": "Single-node Proxmox setup with a Linux bridge and basic firewall. Suitable for home labs and small deployments.",
    "features": [
        "Single Linux bridge (vmbr0)",
        "Basic firewall rules",
        "Local storage pool",
        "Standard backup schedule",
    ],
    "hierarchy": {
        "nodes": [
            _h("dc1", "Lab Datacenter", "datacenter"),
            _h("cl1", "Single Node", "cluster", "dc1"),
            _h("pool1", "Default Pool", "pool", "cl1"),
            _h("br1", "vmbr0", "bridge", "pool1", {"ipam": {"cidr": "10.0.0.0/24"}}),
        ],
    },
    "networkConfig": {"bridge_name": "vmbr0", "vlan_aware": False, "mtu": 1500},
    "iamConfig": {"api_token_isolation": True},
    "securityConfig": {"firewall_enabled": True, "default_policy": "drop"},
    "namingConfig": {"template": "{env}-{resource}-{index}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "production"]},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Management", "cidr": "10.0.0.0/24", "description": "Management network"},
    ],
}

PROXMOX_STANDARD: dict = {
    "id": "proxmox-standard",
    "name": "Standard",
    "providerName": "proxmox",
    "complexity": "standard",
    "description": "Clustered Proxmox with VLAN-aware bridging, HA, Ceph storage, and automated backups.",
    "features": [
        "VLAN-aware Linux bridge",
        "Proxmox HA cluster",
        "Ceph distributed storage",
        "Automated PBS backups",
        "Resource pools per environment",
    ],
    "hierarchy": {
        "nodes": [
            _h("dc1", "Production Datacenter", "datacenter"),
            _h("cl1", "HA Cluster", "cluster", "dc1"),
            _h("pool_mgmt", "Management", "pool", "cl1"),
            _h("pool_prod", "Production", "pool", "cl1"),
            _h("pool_dev", "Development", "pool", "cl1"),
            _h("br_mgmt", "vmbr0 (Mgmt)", "bridge", "pool_mgmt", {"ipam": {"cidr": "10.0.0.0/24"}}),
            _h("br_prod", "vmbr1 (Prod)", "bridge", "pool_prod", {"ipam": {"cidr": "10.100.0.0/16"}}),
            _h("br_dev", "vmbr2 (Dev)", "bridge", "pool_dev", {"ipam": {"cidr": "10.200.0.0/16"}}),
        ],
    },
    "networkConfig": {"bridge_name": "vmbr0", "vlan_aware": True, "mtu": 1500, "vlans": {"management": 10, "production": 100, "development": 200}},
    "iamConfig": {"api_token_isolation": True, "pve_realm": "pam", "two_factor": False},
    "securityConfig": {"firewall_enabled": True, "default_policy": "drop", "cluster_wide": True, "backup_schedule": "daily"},
    "namingConfig": {"template": "{env}-{region}-{resource}-{index}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "production"]},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "cost-center", "displayName": "Cost Center", "isRequired": False},
        {"tagKey": "project", "displayName": "Project", "isRequired": False},
    ],
    "defaultAddressSpaces": [
        {"name": "Management", "cidr": "10.0.0.0/24", "description": "Management VLAN 10"},
        {"name": "Production", "cidr": "10.100.0.0/16", "description": "Production VLAN 100"},
        {"name": "Development", "cidr": "10.200.0.0/16", "description": "Development VLAN 200"},
    ],
}

PROXMOX_ENTERPRISE: dict = {
    "id": "proxmox-enterprise",
    "name": "Enterprise",
    "providerName": "proxmox",
    "complexity": "advanced",
    "description": "SDN-enabled Proxmox with VXLAN/EVPN overlay, multi-tenant resource pools, Ceph with tiered storage.",
    "features": [
        "SDN with VXLAN/EVPN overlay",
        "Multi-tenant resource pools",
        "Ceph with SSD + HDD tiers",
        "Automated snapshots + offsite PBS",
        "Per-pool firewall policies",
        "LDAP/AD integration ready",
    ],
    "hierarchy": {
        "nodes": [
            _h("dc1", "Enterprise Datacenter", "datacenter"),
            _h("cl1", "Primary Cluster", "cluster", "dc1"),
            _h("cl2", "DR Cluster", "cluster", "dc1"),
            _h("pool_mgmt", "Management", "pool", "cl1"),
            _h("pool_prod", "Production", "pool", "cl1"),
            _h("pool_dev", "Development", "pool", "cl1"),
            _h("pool_dr", "DR Pool", "pool", "cl2"),
            _h("br_mgmt", "SDN Mgmt", "bridge", "pool_mgmt", {"ipam": {"cidr": "10.0.0.0/24"}}),
            _h("br_prod", "SDN Production", "bridge", "pool_prod", {"ipam": {"cidr": "10.100.0.0/16"}}),
            _h("br_dev", "SDN Development", "bridge", "pool_dev", {"ipam": {"cidr": "10.200.0.0/16"}}),
            _h("br_dr", "SDN DR", "bridge", "pool_dr", {"ipam": {"cidr": "10.250.0.0/16"}}),
        ],
    },
    "networkConfig": {"sdn_type": "vxlan", "evpn": True, "bridge_type": "ovs", "mtu": 9000},
    "iamConfig": {"api_token_isolation": True, "ldap_realm": True, "two_factor": True, "pve_realm": "ldap"},
    "securityConfig": {"firewall_enabled": True, "per_pool_policies": True, "audit_logging": True, "backup_schedule": "hourly_snapshots", "offsite_backup": True},
    "namingConfig": {"template": "{tenant}-{env}-{region}-{resource}-{index}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "production", "dr"]},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "cost-center", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "project", "displayName": "Project", "isRequired": True},
        {"tagKey": "data-classification", "displayName": "Data Classification", "isRequired": False, "allowedValues": ["public", "internal", "confidential", "restricted"]},
    ],
    "defaultAddressSpaces": [
        {"name": "Management", "cidr": "10.0.0.0/24", "description": "Management overlay"},
        {"name": "Production", "cidr": "10.100.0.0/16", "description": "Production overlay"},
        {"name": "Development", "cidr": "10.200.0.0/16", "description": "Development overlay"},
        {"name": "DR", "cidr": "10.250.0.0/16", "description": "Disaster recovery"},
    ],
}


# ── AWS Blueprints ──────────────────────────────────────────────────────

AWS_SIMPLE: dict = {
    "id": "aws-simple",
    "name": "Simple",
    "providerName": "aws",
    "complexity": "basic",
    "description": "Single account with one VPC, public/private subnets, and CloudTrail logging.",
    "features": [
        "Single VPC with 2 AZs",
        "Public + private subnets",
        "NAT Gateway",
        "CloudTrail enabled",
        "S3 flow logs",
    ],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("ou_workload", "Workloads", "ou", "org"),
            _h("acct1", "Workload Account", "account", "ou_workload"),
            _h("vpc1", "Workload VPC", "vpc", "acct1", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("sub_pub", "Public Subnet", "subnet", "vpc1", {"ipam": {"cidr": "10.0.0.0/24"}}),
            _h("sub_priv", "Private Subnet", "subnet", "vpc1", {"ipam": {"cidr": "10.0.1.0/24"}}),
        ],
    },
    "networkConfig": {"vpc_cidr": "10.0.0.0/16", "azs": 2, "nat_gateway": True, "flow_logs": True},
    "iamConfig": {"cloudtrail": True, "password_policy": True},
    "securityConfig": {"guardduty": False, "security_hub": False},
    "namingConfig": {"template": "{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod"]},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Workload VPC", "cidr": "10.0.0.0/16", "description": "Primary VPC"},
    ],
}

AWS_STANDARD: dict = {
    "id": "aws-standard",
    "name": "Standard",
    "providerName": "aws",
    "complexity": "standard",
    "description": "Multi-account with hub-spoke networking, Transit Gateway, GuardDuty, and SCPs.",
    "features": [
        "Hub VPC + Transit Gateway",
        "Centralized NAT + egress filtering",
        "GuardDuty threat detection",
        "Service Control Policies",
        "AWS Config + compliance rules",
        "Multi-AZ (3 AZs)",
    ],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("ou_security", "Security", "ou", "org"),
            _h("ou_shared", "Shared Services", "ou", "org"),
            _h("ou_workloads", "Workloads", "ou", "org"),
            _h("acct_security", "Security Account", "account", "ou_security"),
            _h("acct_network", "Network Hub Account", "account", "ou_shared"),
            _h("acct_prod", "Production Account", "account", "ou_workloads"),
            _h("acct_dev", "Development Account", "account", "ou_workloads"),
            _h("vpc_hub", "Hub VPC", "vpc", "acct_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vpc_prod", "Production VPC", "vpc", "acct_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vpc_dev", "Development VPC", "vpc", "acct_dev", {"ipam": {"cidr": "10.2.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vpc_cidr": "10.0.0.0/16", "transit_gateway": True, "azs": 3, "nat_gateway_ha": True, "flow_logs": True},
    "iamConfig": {"cloudtrail": True, "org_trail": True, "scps": True, "password_policy": True},
    "securityConfig": {"guardduty": True, "security_hub": False, "config_rules": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod"]},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "Project", "displayName": "Project", "isRequired": False},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VPC", "cidr": "10.0.0.0/16", "description": "Shared services hub"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/16", "description": "Spoke VPC allocation pool"},
    ],
}

AWS_ENTERPRISE: dict = {
    "id": "aws-enterprise",
    "name": "Enterprise",
    "providerName": "aws",
    "complexity": "advanced",
    "description": "Full AWS landing zone with Network Firewall, DNS Resolver, VPN/Direct Connect, KMS, and Security Hub.",
    "features": [
        "Network Firewall + inspection VPC",
        "Route 53 Resolver + DNS firewall",
        "Site-to-site VPN / Direct Connect",
        "KMS with custom key policies",
        "Security Hub + compliance standards",
        "Centralized logging to S3 + CloudWatch",
    ],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("ou_security", "Security", "ou", "org"),
            _h("ou_infra", "Infrastructure", "ou", "org"),
            _h("ou_sandbox", "Sandbox", "ou", "org"),
            _h("ou_workloads", "Workloads", "ou", "org"),
            _h("ou_prod", "Production", "ou", "ou_workloads"),
            _h("ou_nonprod", "Non-Production", "ou", "ou_workloads"),
            _h("acct_security", "Security Account", "account", "ou_security"),
            _h("acct_log", "Log Archive Account", "account", "ou_security"),
            _h("acct_network", "Network Hub Account", "account", "ou_infra"),
            _h("acct_shared", "Shared Services Account", "account", "ou_infra"),
            _h("acct_prod", "Production Account", "account", "ou_prod"),
            _h("acct_staging", "Staging Account", "account", "ou_nonprod"),
            _h("acct_dev", "Development Account", "account", "ou_nonprod"),
            _h("acct_sandbox", "Sandbox Account", "account", "ou_sandbox"),
            _h("vpc_hub", "Hub VPC", "vpc", "acct_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vpc_inspect", "Inspection VPC", "vpc", "acct_network", {"ipam": {"cidr": "100.64.0.0/16"}}),
            _h("vpc_prod", "Production VPC", "vpc", "acct_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vpc_staging", "Staging VPC", "vpc", "acct_staging", {"ipam": {"cidr": "10.2.0.0/16"}}),
            _h("vpc_dev", "Development VPC", "vpc", "acct_dev", {"ipam": {"cidr": "10.3.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vpc_cidr": "10.0.0.0/16", "inspection_vpc_cidr": "100.64.0.0/16", "transit_gateway": True, "network_firewall": True, "dns_resolver": True, "vpn": True, "azs": 3},
    "iamConfig": {"cloudtrail": True, "org_trail": True, "scps": True, "kms_custom_keys": True, "password_policy": True, "access_analyzer": True},
    "securityConfig": {"guardduty": True, "security_hub": True, "network_firewall": True, "config_rules": True, "dns_firewall": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod", "dr"]},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "Project", "displayName": "Project", "isRequired": True},
        {"tagKey": "DataClassification", "displayName": "Data Classification", "isRequired": True, "allowedValues": ["public", "internal", "confidential", "restricted"]},
        {"tagKey": "Compliance", "displayName": "Compliance", "isRequired": False, "allowedValues": ["sox", "hipaa", "pci", "gdpr"]},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VPC", "cidr": "10.0.0.0/16", "description": "Shared services hub"},
        {"name": "Inspection VPC", "cidr": "100.64.0.0/16", "description": "Network firewall inspection"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/12", "description": "Spoke VPC allocation pool"},
    ],
}


# ── Azure Blueprints ────────────────────────────────────────────────────

AZURE_SIMPLE: dict = {
    "id": "azure-simple",
    "name": "Simple",
    "providerName": "azure",
    "complexity": "basic",
    "description": "Single subscription with a VNet, NSGs, and basic Activity Log monitoring.",
    "features": ["Single VNet", "Network Security Groups", "Activity Log", "Azure Monitor basics"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("mg_root", "Root Management Group", "management_group", "org"),
            _h("sub1", "Workload Subscription", "subscription", "mg_root"),
            _h("rg1", "Main Resource Group", "resource_group", "sub1"),
            _h("vnet1", "Hub VNet", "vnet", "rg1", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("sn_default", "Default Subnet", "subnet", "vnet1", {"ipam": {"cidr": "10.0.0.0/24"}}),
        ],
    },
    "networkConfig": {"vnet_cidr": "10.0.0.0/16", "subnets": 2},
    "iamConfig": {"activity_log": True},
    "securityConfig": {"nsg_enabled": True, "defender": False},
    "namingConfig": {"template": "{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
    ],
    "defaultAddressSpaces": [{"name": "Hub VNet", "cidr": "10.0.0.0/16", "description": "Primary VNet"}],
}

AZURE_STANDARD: dict = {
    "id": "azure-standard",
    "name": "Standard",
    "providerName": "azure",
    "complexity": "standard",
    "description": "Hub-spoke with management groups, Azure Firewall, Bastion, Defender, and PIM.",
    "features": ["Hub-spoke VNet peering", "Azure Firewall", "Bastion host", "Defender for Cloud", "PIM for JIT access", "Log Analytics workspace"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("mg_platform", "Platform", "management_group", "org"),
            _h("mg_landing", "Landing Zones", "management_group", "org"),
            _h("sub_conn", "Connectivity", "subscription", "mg_platform"),
            _h("sub_identity", "Identity", "subscription", "mg_platform"),
            _h("sub_prod", "Production", "subscription", "mg_landing"),
            _h("sub_dev", "Development", "subscription", "mg_landing"),
            _h("rg_hub", "Hub Network RG", "resource_group", "sub_conn"),
            _h("rg_prod", "Production RG", "resource_group", "sub_prod"),
            _h("rg_dev", "Development RG", "resource_group", "sub_dev"),
            _h("vnet_hub", "Hub VNet", "vnet", "rg_hub", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vnet_prod", "Production VNet", "vnet", "rg_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vnet_dev", "Development VNet", "vnet", "rg_dev", {"ipam": {"cidr": "10.2.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vnet_cidr": "10.0.0.0/16", "azure_firewall": True, "bastion": True, "peering": True},
    "iamConfig": {"defender": True, "pim": True, "activity_log": True},
    "securityConfig": {"azure_firewall": True, "defender": True, "bastion": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VNet", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/16", "description": "Spoke VNet pool"},
    ],
}

AZURE_ENTERPRISE: dict = {
    "id": "azure-enterprise",
    "name": "Enterprise",
    "providerName": "azure",
    "complexity": "advanced",
    "description": "Full Azure landing zone with Sentinel, Premium Firewall, ExpressRoute, and comprehensive compliance.",
    "features": ["Sentinel SIEM", "Premium Firewall with TLS inspection", "ExpressRoute gateway", "Key Vault with HSM", "Azure Policy + Blueprints", "Comprehensive RBAC"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("mg_platform", "Platform", "management_group", "org"),
            _h("mg_connectivity", "Connectivity", "management_group", "mg_platform"),
            _h("mg_identity", "Identity", "management_group", "mg_platform"),
            _h("mg_management", "Management", "management_group", "mg_platform"),
            _h("mg_landing", "Landing Zones", "management_group", "org"),
            _h("mg_prod", "Production", "management_group", "mg_landing"),
            _h("mg_nonprod", "Non-Production", "management_group", "mg_landing"),
            _h("mg_sandbox", "Sandbox", "management_group", "org"),
            _h("sub_conn", "Connectivity Sub", "subscription", "mg_connectivity"),
            _h("sub_identity", "Identity Sub", "subscription", "mg_identity"),
            _h("sub_mgmt", "Management Sub", "subscription", "mg_management"),
            _h("sub_prod", "Production Sub", "subscription", "mg_prod"),
            _h("sub_staging", "Staging Sub", "subscription", "mg_nonprod"),
            _h("sub_dev", "Development Sub", "subscription", "mg_nonprod"),
            _h("sub_sandbox", "Sandbox Sub", "subscription", "mg_sandbox"),
            _h("rg_hub", "Hub Network RG", "resource_group", "sub_conn"),
            _h("vnet_hub", "Hub VNet", "vnet", "rg_hub", {"ipam": {"cidr": "10.0.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vnet_cidr": "10.0.0.0/16", "firewall_premium": True, "expressroute": True, "bastion": True, "ddos_protection": True},
    "iamConfig": {"sentinel": True, "pim": True, "azure_policy": True, "conditional_access": True},
    "securityConfig": {"firewall_premium": True, "sentinel": True, "keyvault_hsm": True, "defender_plans": "all"},
    "namingConfig": {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod", "dr"]},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "Project", "displayName": "Project", "isRequired": True},
        {"tagKey": "DataClassification", "displayName": "Data Classification", "isRequired": True, "allowedValues": ["public", "internal", "confidential", "restricted"]},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VNet", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/12", "description": "Spoke VNet pool"},
    ],
}


# ── GCP Blueprints ──────────────────────────────────────────────────────

GCP_SIMPLE: dict = {
    "id": "gcp-simple",
    "name": "Simple",
    "providerName": "gcp",
    "complexity": "basic",
    "description": "Single project with a Shared VPC, Cloud NAT, and basic logging.",
    "features": ["Shared VPC", "Cloud NAT", "Cloud Logging", "Default firewall rules"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("folder1", "Workloads", "folder", "org"),
            _h("proj1", "Workload Project", "project", "folder1"),
            _h("vpc1", "Shared VPC", "vpc", "proj1", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("sn1", "Default Subnet", "subnet", "vpc1", {"ipam": {"cidr": "10.0.0.0/24"}}),
        ],
    },
    "networkConfig": {"shared_vpc": True, "cloud_nat": True},
    "iamConfig": {"org_policies": False},
    "securityConfig": {"scc": False},
    "namingConfig": {"template": "{env}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
    ],
    "defaultAddressSpaces": [{"name": "Shared VPC", "cidr": "10.0.0.0/16", "description": "Primary VPC"}],
}

GCP_STANDARD: dict = {
    "id": "gcp-standard",
    "name": "Standard",
    "providerName": "gcp",
    "complexity": "standard",
    "description": "Multi-folder with Shared VPC, Cloud DNS, Org policies, SCC Premium, and centralized logging.",
    "features": ["Cloud DNS zones", "Organization policies", "SCC Premium", "VPC Flow Logs", "IAM Recommender"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("folder_shared", "Shared Services", "folder", "org"),
            _h("folder_prod", "Production", "folder", "org"),
            _h("folder_dev", "Development", "folder", "org"),
            _h("proj_network", "Network Hub Project", "project", "folder_shared"),
            _h("proj_prod", "Production Project", "project", "folder_prod"),
            _h("proj_dev", "Development Project", "project", "folder_dev"),
            _h("vpc_hub", "Shared VPC", "vpc", "proj_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vpc_prod", "Production VPC", "vpc", "proj_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vpc_dev", "Development VPC", "vpc", "proj_dev", {"ipam": {"cidr": "10.2.0.0/16"}}),
        ],
    },
    "networkConfig": {"shared_vpc": True, "cloud_nat": True, "cloud_dns": True, "flow_logs": True},
    "iamConfig": {"org_policies": True, "iam_recommender": True},
    "securityConfig": {"scc_premium": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "cost-center", "displayName": "Cost Center", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Shared VPC", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Service Projects", "cidr": "10.1.0.0/16", "description": "Service project pool"},
    ],
}

GCP_ENTERPRISE: dict = {
    "id": "gcp-enterprise",
    "name": "Enterprise",
    "providerName": "gcp",
    "complexity": "advanced",
    "description": "Full GCP with VPC Service Controls, Interconnect, Cloud KMS, and Access Context Manager.",
    "features": ["VPC Service Controls", "Cloud Interconnect", "Cloud KMS with HSM", "Access Context Manager", "Binary Authorization", "Assured Workloads"],
    "hierarchy": {
        "nodes": [
            _h("org", "Organization", "organization"),
            _h("folder_bootstrap", "Bootstrap", "folder", "org"),
            _h("folder_common", "Common", "folder", "org"),
            _h("folder_prod", "Production", "folder", "org"),
            _h("folder_nonprod", "Non-Production", "folder", "org"),
            _h("folder_sandbox", "Sandbox", "folder", "org"),
            _h("proj_seed", "Seed Project", "project", "folder_bootstrap"),
            _h("proj_network", "Network Hub", "project", "folder_common"),
            _h("proj_security", "Security", "project", "folder_common"),
            _h("proj_logging", "Logging", "project", "folder_common"),
            _h("proj_prod", "Production", "project", "folder_prod"),
            _h("proj_staging", "Staging", "project", "folder_nonprod"),
            _h("proj_dev", "Development", "project", "folder_nonprod"),
            _h("vpc_hub", "Shared VPC", "vpc", "proj_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vpc_prod", "Production VPC", "vpc", "proj_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
        ],
    },
    "networkConfig": {"shared_vpc": True, "interconnect": True, "cloud_dns": True, "vpc_service_controls": True},
    "iamConfig": {"org_policies": True, "access_context_manager": True, "binary_authorization": True},
    "securityConfig": {"scc_premium": True, "vpc_sc": True, "kms_hsm": True, "assured_workloads": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod", "dr"]},
        {"tagKey": "owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "cost-center", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "project", "displayName": "Project", "isRequired": True},
        {"tagKey": "data-classification", "displayName": "Data Classification", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Shared VPC", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Service Projects", "cidr": "10.1.0.0/12", "description": "Service project pool"},
    ],
}


# ── OCI Blueprints ──────────────────────────────────────────────────────

OCI_SIMPLE: dict = {
    "id": "oci-simple",
    "name": "Simple",
    "providerName": "oci",
    "complexity": "basic",
    "description": "Single compartment with a Hub VCN, DRG, and default security lists.",
    "features": ["Hub VCN", "DRG attachment", "Internet & NAT gateways", "Default security lists"],
    "hierarchy": {
        "nodes": [
            _h("tenancy", "Tenancy", "tenancy"),
            _h("comp_network", "Network", "compartment", "tenancy"),
            _h("vcn1", "Hub VCN", "vcn", "comp_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("sn_pub", "Public Subnet", "subnet", "vcn1", {"ipam": {"cidr": "10.0.0.0/24"}}),
            _h("sn_priv", "Private Subnet", "subnet", "vcn1", {"ipam": {"cidr": "10.0.1.0/24"}}),
        ],
    },
    "networkConfig": {"hub_vcn_cidr": "10.0.0.0/16", "drg": True},
    "iamConfig": {},
    "securityConfig": {},
    "namingConfig": {"template": "{env}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
    ],
    "defaultAddressSpaces": [{"name": "Hub VCN", "cidr": "10.0.0.0/16", "description": "Primary VCN"}],
}

OCI_STANDARD: dict = {
    "id": "oci-standard",
    "name": "Standard",
    "providerName": "oci",
    "complexity": "standard",
    "description": "Multi-compartment with Cloud Guard, Vault, and centralized logging.",
    "features": ["Compartment hierarchy", "Cloud Guard", "OCI Vault", "Logging Analytics", "Cost tracking tags"],
    "hierarchy": {
        "nodes": [
            _h("tenancy", "Tenancy", "tenancy"),
            _h("comp_security", "Security", "compartment", "tenancy"),
            _h("comp_network", "Network", "compartment", "tenancy"),
            _h("comp_prod", "Production", "compartment", "tenancy"),
            _h("comp_dev", "Development", "compartment", "tenancy"),
            _h("vcn_hub", "Hub VCN", "vcn", "comp_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vcn_prod", "Production VCN", "vcn", "comp_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vcn_dev", "Development VCN", "vcn", "comp_dev", {"ipam": {"cidr": "10.2.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vcn_cidr": "10.0.0.0/16", "drg": True, "service_gateway": True},
    "iamConfig": {"compartments": True, "cloud_guard": True},
    "securityConfig": {"cloud_guard": True, "vault": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VCN", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/16", "description": "Spoke VCN pool"},
    ],
}

OCI_ENTERPRISE: dict = {
    "id": "oci-enterprise",
    "name": "Enterprise",
    "providerName": "oci",
    "complexity": "advanced",
    "description": "Full OCI landing zone with Events, Notifications, VPrivate Vault, and FastConnect.",
    "features": ["Events + Notifications", "VPrivate (dedicated) Vault", "FastConnect", "Network Firewall", "Bastion service", "Full audit + compliance"],
    "hierarchy": {
        "nodes": [
            _h("tenancy", "Tenancy", "tenancy"),
            _h("comp_security", "Security", "compartment", "tenancy"),
            _h("comp_network", "Network", "compartment", "tenancy"),
            _h("comp_logging", "Logging", "compartment", "tenancy"),
            _h("comp_prod", "Production", "compartment", "tenancy"),
            _h("comp_nonprod", "Non-Production", "compartment", "tenancy"),
            _h("comp_sandbox", "Sandbox", "compartment", "tenancy"),
            _h("comp_staging", "Staging", "compartment", "comp_nonprod"),
            _h("comp_dev", "Development", "compartment", "comp_nonprod"),
            _h("vcn_hub", "Hub VCN", "vcn", "comp_network", {"ipam": {"cidr": "10.0.0.0/16"}}),
            _h("vcn_prod", "Production VCN", "vcn", "comp_prod", {"ipam": {"cidr": "10.1.0.0/16"}}),
            _h("vcn_staging", "Staging VCN", "vcn", "comp_staging", {"ipam": {"cidr": "10.2.0.0/16"}}),
            _h("vcn_dev", "Development VCN", "vcn", "comp_dev", {"ipam": {"cidr": "10.3.0.0/16"}}),
        ],
    },
    "networkConfig": {"hub_vcn_cidr": "10.0.0.0/16", "drg": True, "fastconnect": True, "network_firewall": True, "bastion": True},
    "iamConfig": {"compartments": True, "cloud_guard": True, "events": True, "notifications": True},
    "securityConfig": {"cloud_guard": True, "vprivate_vault": True, "network_firewall": True, "bastion": True},
    "namingConfig": {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    "defaultTags": [
        {"tagKey": "Environment", "displayName": "Environment", "isRequired": True, "allowedValues": ["dev", "staging", "prod", "dr"]},
        {"tagKey": "Owner", "displayName": "Owner", "isRequired": True},
        {"tagKey": "CostCenter", "displayName": "Cost Center", "isRequired": True},
        {"tagKey": "Project", "displayName": "Project", "isRequired": True},
        {"tagKey": "DataClassification", "displayName": "Data Classification", "isRequired": True},
    ],
    "defaultAddressSpaces": [
        {"name": "Hub VCN", "cidr": "10.0.0.0/16", "description": "Hub network"},
        {"name": "Spoke Pool", "cidr": "10.1.0.0/12", "description": "Spoke VCN pool"},
    ],
}


# ── Registry ────────────────────────────────────────────────────────────

_ALL_BLUEPRINTS: list[dict] = [
    # Proxmox
    PROXMOX_SIMPLE, PROXMOX_STANDARD, PROXMOX_ENTERPRISE,
    # AWS
    AWS_SIMPLE, AWS_STANDARD, AWS_ENTERPRISE,
    # Azure
    AZURE_SIMPLE, AZURE_STANDARD, AZURE_ENTERPRISE,
    # GCP
    GCP_SIMPLE, GCP_STANDARD, GCP_ENTERPRISE,
    # OCI
    OCI_SIMPLE, OCI_STANDARD, OCI_ENTERPRISE,
]

_BY_PROVIDER: dict[str, list[dict]] = {}
for _bp in _ALL_BLUEPRINTS:
    _BY_PROVIDER.setdefault(_bp["providerName"], []).append(_bp)


def get_blueprints(provider_name: str) -> list[dict]:
    """Return all blueprints for a given provider name (case-insensitive)."""
    return _BY_PROVIDER.get(provider_name.lower(), [])


def get_blueprint(blueprint_id: str) -> dict | None:
    """Return a single blueprint by ID."""
    for bp in _ALL_BLUEPRINTS:
        if bp["id"] == blueprint_id:
            return bp
    return None
