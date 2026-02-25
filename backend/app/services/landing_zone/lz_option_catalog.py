"""
Overview: Landing zone strategy and foundation option catalog — preset choices for organizational
    structure, network topology, IAM policies, and security baselines at the landing zone level.
Architecture: Static data module for guided LZ configuration (Section 7.2)
Dependencies: app.services.landing_zone.env_option_catalog (ConfigOption, CategoryInfo)
Concepts: LZ options cover four domains: organization (isolation/topology/shared services),
    network (hub network, connectivity, DNS, gateways), iam (policies, identity, access control),
    and security (logging, protection, encryption, backup). Organization options include
    hierarchy_implications that generate the initial LZ hierarchy tree.
"""

from __future__ import annotations

from app.services.landing_zone.env_option_catalog import CategoryInfo, ConfigOption


# ── Category Definitions ───────────────────────────────────────────────

ORGANIZATION_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("isolation", "Isolation Strategy", "How tenants and environments are isolated", "layers"),
    CategoryInfo("topology", "Network Topology", "Hub-spoke vs flat network architecture", "network"),
    CategoryInfo("shared_services", "Shared Services", "Centralized vs distributed services", "grid"),
]

NETWORK_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("hub_network", "Hub Network", "Hub VPC/VNet/VCN sizing and bridge config", "network"),
    CategoryInfo("connectivity", "Connectivity", "Transit gateways and interconnects", "link"),
    CategoryInfo("dns", "DNS", "DNS resolvers and private zones", "globe"),
    CategoryInfo("gateway", "Gateways", "NAT, internet, and service gateways", "zap"),
]

IAM_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("policies", "Org Policies", "Service control policies and org-level policies", "shield"),
    CategoryInfo("identity", "Identity", "MFA, password policy, workload identity", "user"),
    CategoryInfo("access_control", "Access Control", "PIM, conditional access, custom roles", "lock"),
]

SECURITY_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("logging", "Logging", "Centralized logging and audit trails", "activity"),
    CategoryInfo("protection", "Threat Protection", "Cloud-native threat detection services", "shield"),
    CategoryInfo("encryption", "Encryption", "KMS keys, vaults, and key management", "lock"),
    CategoryInfo("backup", "Backup", "Backup policies and storage config", "archive"),
]

_CATEGORIES_BY_DOMAIN: dict[str, list[CategoryInfo]] = {
    "organization": ORGANIZATION_CATEGORIES,
    "network": NETWORK_CATEGORIES,
    "iam": IAM_CATEGORIES,
    "security": SECURITY_CATEGORIES,
}

# ═══════════════════════════════════════════════════════════════════════
# Proxmox LZ options
# ═══════════════════════════════════════════════════════════════════════

_PROXMOX_OPTIONS: list[ConfigOption] = [
    # ── Organization ────────────────────────────────────────────────
    ConfigOption(
        id="pve-org-pool-isolation",
        domain="organization", category="isolation", provider_name="proxmox",
        name="pool_isolation", display_name="Pool per Environment",
        description="Separate resource pool for each environment",
        detail="Each environment gets its own Proxmox resource pool with quotas. "
        "Provides logical isolation within a single cluster.",
        icon="folder",
        implications=["Single cluster, logical isolation", "Per-pool CPU/memory quotas", "Simplest Proxmox setup"],
        config_values={"isolation_strategy": "pool-per-env"},
        conflicts_with=["pve-org-cluster-isolation"],
        sort_order=1, is_default=True, tags=["standard"],
        hierarchy_implications={
            "description": "Cluster > Resource Pool per environment",
            "nodes": [
                {"typeId": "cluster", "label": "Proxmox Cluster", "parentId": None},
                {"typeId": "pool", "label": "Shared Services Pool", "parentId": "__idx_0"},
                {"typeId": "pool", "label": "Production Pool", "parentId": "__idx_0"},
                {"typeId": "pool", "label": "Development Pool", "parentId": "__idx_0"},
            ],
        },
    ),
    ConfigOption(
        id="pve-org-cluster-isolation",
        domain="organization", category="isolation", provider_name="proxmox",
        name="cluster_isolation", display_name="Cluster per Environment",
        description="Dedicated cluster for each environment",
        detail="Each environment runs on a separate Proxmox cluster. "
        "Provides physical isolation but requires more hardware.",
        icon="server",
        implications=["Physical isolation per environment", "More hardware required", "Strongest isolation"],
        config_values={"isolation_strategy": "cluster-per-env"},
        conflicts_with=["pve-org-pool-isolation"],
        sort_order=2, tags=["enterprise"],
        hierarchy_implications={
            "description": "Separate cluster per environment",
            "nodes": [
                {"typeId": "cluster", "label": "Shared Services Cluster", "parentId": None},
                {"typeId": "cluster", "label": "Production Cluster", "parentId": None},
                {"typeId": "cluster", "label": "Development Cluster", "parentId": None},
            ],
        },
    ),
    ConfigOption(
        id="pve-org-hub-spoke",
        domain="organization", category="topology", provider_name="proxmox",
        name="hub_spoke", display_name="Hub-Spoke",
        description="Central bridge with spoke VLANs per environment",
        detail="A hub bridge (vmbr0) connects to spoke VLANs for each environment. "
        "Centralized routing through the hub bridge.",
        icon="network",
        implications=["Centralized routing", "VLAN-aware bridging required", "Standard topology"],
        config_values={"topology": "hub-spoke"},
        conflicts_with=["pve-org-flat"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="pve-org-flat",
        domain="organization", category="topology", provider_name="proxmox",
        name="flat", display_name="Flat Network",
        description="Single flat network for all environments",
        detail="All environments share a single network bridge. "
        "Simplest setup but no network-level isolation.",
        icon="network",
        implications=["No network isolation", "Simplest configuration", "Dev/lab environments only"],
        config_values={"topology": "flat"},
        conflicts_with=["pve-org-hub-spoke"],
        sort_order=2, tags=["dev"],
    ),
    ConfigOption(
        id="pve-org-central-dns",
        domain="organization", category="shared_services", provider_name="proxmox",
        name="central_dns", display_name="Central DNS",
        description="Shared DNS server for all environments",
        detail="A central DNS resolver VM in the shared services pool resolves "
        "names for all environments.",
        icon="globe",
        implications=["Single DNS management point", "Shared services pool required", "BIND or similar"],
        config_values={"shared_dns": "central"},
        conflicts_with=["pve-org-distributed-dns"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="pve-org-distributed-dns",
        domain="organization", category="shared_services", provider_name="proxmox",
        name="distributed_dns", display_name="Distributed DNS",
        description="Per-environment DNS resolvers",
        detail="Each environment runs its own DNS resolver. "
        "More complex but fully isolated name resolution.",
        icon="globe",
        implications=["Per-environment isolation", "Higher resource usage", "Independent failure domains"],
        config_values={"shared_dns": "distributed"},
        conflicts_with=["pve-org-central-dns"],
        sort_order=2, tags=["enterprise"],
    ),

    # ── Network ─────────────────────────────────────────────────────
    ConfigOption(
        id="pve-net-hub-small",
        domain="network", category="hub_network", provider_name="proxmox",
        name="hub_small", display_name="Small Hub (/24)",
        description="254 addresses for hub bridge network",
        detail="A /24 CIDR block for the hub bridge (vmbr0). "
        "Suitable for small deployments with a few environments.",
        icon="network",
        implications=["254 usable IPs", "Hub bridge vmbr0", "Small deployment"],
        config_values={"hub_cidr": "10.0.0.0/24", "bridge": "vmbr0"},
        conflicts_with=["pve-net-hub-medium", "pve-net-hub-large"],
        sort_order=1, tags=["dev"],
    ),
    ConfigOption(
        id="pve-net-hub-medium",
        domain="network", category="hub_network", provider_name="proxmox",
        name="hub_medium", display_name="Standard Hub (/20)",
        description="4094 addresses for hub network",
        detail="A /20 CIDR block for the hub bridge. "
        "Room for multiple VLANs and shared services.",
        icon="network",
        implications=["4094 usable IPs", "Room for 16 /24 subnets", "Standard size"],
        config_values={"hub_cidr": "10.0.0.0/20", "bridge": "vmbr0"},
        conflicts_with=["pve-net-hub-small", "pve-net-hub-large"],
        sort_order=2, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="pve-net-hub-large",
        domain="network", category="hub_network", provider_name="proxmox",
        name="hub_large", display_name="Large Hub (/16)",
        description="65534 addresses for large hub network",
        detail="A /16 CIDR block for large multi-cluster deployments.",
        icon="network",
        implications=["65534 usable IPs", "Large-scale deployment", "Plan subnetting carefully"],
        config_values={"hub_cidr": "10.0.0.0/16", "bridge": "vmbr0"},
        conflicts_with=["pve-net-hub-small", "pve-net-hub-medium"],
        sort_order=3, tags=["enterprise"],
    ),
    ConfigOption(
        id="pve-net-nat-gw",
        domain="network", category="gateway", provider_name="proxmox",
        name="nat_gateway", display_name="NAT Gateway",
        description="Enable NAT for outbound internet access",
        detail="Configure a NAT gateway on the hub bridge for environments "
        "that need outbound internet without public IPs.",
        icon="zap",
        implications=["Outbound internet access", "No inbound by default", "Masquerade on hub bridge"],
        config_values={"enable_nat": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),

    # ── IAM ─────────────────────────────────────────────────────────
    ConfigOption(
        id="pve-iam-realm-policy",
        domain="iam", category="policies", provider_name="proxmox",
        name="realm_policy", display_name="Realm-Based Access",
        description="Proxmox realm + role assignments",
        detail="Use Proxmox authentication realms (PAM, LDAP, AD) with "
        "role-based ACLs at the pool/path level.",
        icon="shield",
        implications=["Realm-scoped users", "ACL propagation", "PVE built-in roles"],
        config_values={"auth_realm": "pam", "acl_propagate": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="pve-iam-2fa",
        domain="iam", category="identity", provider_name="proxmox",
        name="enforce_2fa", display_name="Enforce TOTP 2FA",
        description="Require two-factor authentication for all users",
        detail="Enable TOTP-based two-factor authentication for all Proxmox users. "
        "Provides additional security for cluster access.",
        icon="lock",
        implications=["TOTP for all users", "Yubikey also supported", "Required at realm level"],
        config_values={"enforce_2fa": True, "tfa_type": "totp"},
        sort_order=1, tags=["enterprise"],
    ),

    # ── Security ────────────────────────────────────────────────────
    ConfigOption(
        id="pve-sec-pbs-backup",
        domain="security", category="backup", provider_name="proxmox",
        name="pbs_backup", display_name="PBS Backup",
        description="Proxmox Backup Server integration",
        detail="Configure automated backups to a Proxmox Backup Server instance. "
        "Deduplication and encryption at rest.",
        icon="archive",
        implications=["Deduplication storage", "Encryption at rest", "Incremental backups"],
        config_values={"backup_target": "pbs", "backup_encryption": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="pve-sec-firewall",
        domain="security", category="protection", provider_name="proxmox",
        name="pve_firewall", display_name="PVE Firewall",
        description="Enable Proxmox built-in firewall at datacenter level",
        detail="Enable the Proxmox firewall at the datacenter level with "
        "default-deny inbound rules. Cluster-wide policy.",
        icon="shield",
        implications=["Default deny inbound", "Datacenter-level rules", "Per-VM exceptions"],
        config_values={"enable_firewall": True, "default_policy_in": "DROP"},
        sort_order=1, is_default=True, tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# AWS LZ options
# ═══════════════════════════════════════════════════════════════════════

_AWS_OPTIONS: list[ConfigOption] = [
    # ── Organization ────────────────────────────────────────────────
    ConfigOption(
        id="aws-org-account-isolation",
        domain="organization", category="isolation", provider_name="aws",
        name="account_isolation", display_name="Account per Environment",
        description="Separate AWS account for each environment",
        detail="AWS Organizations with separate accounts per environment. "
        "Strongest isolation with independent IAM boundaries.",
        icon="layers",
        implications=["IAM boundary per environment", "Consolidated billing", "AWS Organizations required"],
        config_values={"isolation_strategy": "account-per-env"},
        conflicts_with=["aws-org-vpc-isolation"],
        sort_order=1, is_default=True, tags=["standard"],
        hierarchy_implications={
            "description": "Organization > OU > Account per environment",
            "nodes": [
                {"typeId": "organization", "label": "AWS Organization", "parentId": None},
                {"typeId": "ou", "label": "Shared Services OU", "parentId": "__idx_0"},
                {"typeId": "ou", "label": "Workloads OU", "parentId": "__idx_0"},
                {"typeId": "account", "label": "Shared Services Account", "parentId": "__idx_1"},
                {"typeId": "account", "label": "Production Account", "parentId": "__idx_2"},
                {"typeId": "account", "label": "Development Account", "parentId": "__idx_2"},
                {"typeId": "vpc", "label": "Hub VPC", "parentId": "__idx_3"},
            ],
        },
    ),
    ConfigOption(
        id="aws-org-vpc-isolation",
        domain="organization", category="isolation", provider_name="aws",
        name="vpc_isolation", display_name="VPC per Environment",
        description="Separate VPCs in a shared account",
        detail="All environments in one account, isolated by VPC. "
        "Simpler than multi-account but weaker IAM boundaries.",
        icon="layers",
        implications=["Shared IAM boundary", "VPC-level isolation only", "Simpler management"],
        config_values={"isolation_strategy": "vpc-per-env"},
        conflicts_with=["aws-org-account-isolation"],
        sort_order=2, tags=["dev"],
        hierarchy_implications={
            "description": "Single account with VPCs per environment",
            "nodes": [
                {"typeId": "account", "label": "AWS Account", "parentId": None},
                {"typeId": "vpc", "label": "Hub VPC", "parentId": "__idx_0"},
                {"typeId": "vpc", "label": "Production VPC", "parentId": "__idx_0"},
                {"typeId": "vpc", "label": "Development VPC", "parentId": "__idx_0"},
            ],
        },
    ),
    ConfigOption(
        id="aws-org-hub-spoke",
        domain="organization", category="topology", provider_name="aws",
        name="hub_spoke", display_name="Hub-Spoke",
        description="Transit Gateway connecting hub and spoke VPCs",
        detail="A central hub VPC connected to spoke VPCs via Transit Gateway. "
        "Centralized routing, inspection, and shared services.",
        icon="network",
        implications=["Transit Gateway required", "Centralized inspection", "Standard enterprise pattern"],
        config_values={"topology": "hub-spoke"},
        conflicts_with=["aws-org-flat"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-org-flat",
        domain="organization", category="topology", provider_name="aws",
        name="flat", display_name="Flat (VPC Peering)",
        description="Direct VPC peering between environments",
        detail="VPCs connected via peering connections. "
        "No centralized routing — suitable for simple setups.",
        icon="network",
        implications=["No Transit Gateway cost", "Point-to-point peering", "Does not scale well"],
        config_values={"topology": "flat"},
        conflicts_with=["aws-org-hub-spoke"],
        sort_order=2, tags=["dev"],
    ),
    ConfigOption(
        id="aws-org-central-dns",
        domain="organization", category="shared_services", provider_name="aws",
        name="central_dns", display_name="Route 53 Central DNS",
        description="Centralized Route 53 private hosted zones",
        detail="Shared Route 53 private hosted zones in the hub account, "
        "associated with all spoke VPCs.",
        icon="globe",
        implications=["Route 53 Resolver rules", "Cross-account zone association", "Centralized DNS management"],
        config_values={"shared_dns": "central"},
        conflicts_with=["aws-org-distributed-dns"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-org-distributed-dns",
        domain="organization", category="shared_services", provider_name="aws",
        name="distributed_dns", display_name="Per-Account DNS",
        description="Independent Route 53 zones per account",
        detail="Each account manages its own Route 53 hosted zones. "
        "Full autonomy but no centralized resolution.",
        icon="globe",
        implications=["Independent per account", "No cross-account resolution", "Simpler but fragmented"],
        config_values={"shared_dns": "distributed"},
        conflicts_with=["aws-org-central-dns"],
        sort_order=2, tags=["dev"],
    ),

    # ── Network ─────────────────────────────────────────────────────
    ConfigOption(
        id="aws-net-hub-small",
        domain="network", category="hub_network", provider_name="aws",
        name="hub_small", display_name="Small Hub VPC (/24)",
        description="254 addresses for hub VPC",
        detail="A /24 hub VPC for the shared services account.",
        icon="network",
        implications=["254 usable IPs", "Limited spoke connectivity", "Dev/test hub"],
        config_values={"hub_vpc_cidr": "10.0.0.0/24"},
        conflicts_with=["aws-net-hub-medium", "aws-net-hub-large"],
        sort_order=1, tags=["dev"],
    ),
    ConfigOption(
        id="aws-net-hub-medium",
        domain="network", category="hub_network", provider_name="aws",
        name="hub_medium", display_name="Standard Hub VPC (/20)",
        description="4094 addresses for hub VPC",
        detail="A /20 hub VPC. Standard size for enterprise hub-spoke topologies.",
        icon="network",
        implications=["4094 usable IPs", "Room for multiple AZ subnets", "Standard enterprise size"],
        config_values={"hub_vpc_cidr": "10.0.0.0/20"},
        conflicts_with=["aws-net-hub-small", "aws-net-hub-large"],
        sort_order=2, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-net-hub-large",
        domain="network", category="hub_network", provider_name="aws",
        name="hub_large", display_name="Large Hub VPC (/16)",
        description="65534 addresses for hub VPC",
        detail="A /16 hub VPC for large-scale enterprise deployments.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended size", "Plan subnetting carefully"],
        config_values={"hub_vpc_cidr": "10.0.0.0/16"},
        conflicts_with=["aws-net-hub-small", "aws-net-hub-medium"],
        sort_order=3, tags=["enterprise"],
    ),
    ConfigOption(
        id="aws-net-tgw",
        domain="network", category="connectivity", provider_name="aws",
        name="transit_gateway", display_name="Transit Gateway",
        description="AWS Transit Gateway for hub-spoke connectivity",
        detail="Provision a Transit Gateway to connect hub and spoke VPCs. "
        "Centralized routing with route tables.",
        icon="link",
        implications=["~$0.05/GB data processing", "$36/month per attachment", "Centralized routing"],
        config_values={"enable_transit_gateway": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-net-r53-resolver",
        domain="network", category="dns", provider_name="aws",
        name="r53_resolver", display_name="Route 53 Resolver",
        description="DNS resolution between VPCs and on-premises",
        detail="Route 53 Resolver endpoints for hybrid DNS resolution.",
        icon="globe",
        implications=["Inbound + outbound endpoints", "~$0.125/hr per endpoint", "On-premises DNS forwarding"],
        config_values={"enable_r53_resolver": True},
        sort_order=1, tags=["enterprise"],
    ),
    ConfigOption(
        id="aws-net-nat-gw",
        domain="network", category="gateway", provider_name="aws",
        name="nat_gateway", display_name="NAT Gateway",
        description="Managed NAT for private subnet outbound access",
        detail="AWS Managed NAT Gateway in the hub VPC. "
        "Shared by spoke VPCs via Transit Gateway routing.",
        icon="zap",
        implications=["~$32/month + data charges", "Managed HA in each AZ", "Outbound internet access"],
        config_values={"enable_nat_gateway": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),

    # ── IAM ─────────────────────────────────────────────────────────
    ConfigOption(
        id="aws-iam-scp",
        domain="iam", category="policies", provider_name="aws",
        name="scp_baseline", display_name="SCP Baseline",
        description="Service Control Policies for guardrails",
        detail="Apply baseline SCPs to deny dangerous actions: "
        "root user activity, region restrictions, GuardDuty disabling.",
        icon="shield",
        implications=["Deny root user API calls", "Region restrictions", "Prevent guardrail removal"],
        config_values={"enable_scps": True, "deny_root_actions": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-iam-sso",
        domain="iam", category="identity", provider_name="aws",
        name="sso", display_name="AWS IAM Identity Center",
        description="Centralized SSO with permission sets",
        detail="Use AWS IAM Identity Center (SSO) for centralized access management. "
        "Permission sets define cross-account role mappings.",
        icon="user",
        implications=["Centralized user management", "Permission sets per account", "SAML/OIDC federation"],
        config_values={"enable_sso": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),

    # ── Security ────────────────────────────────────────────────────
    ConfigOption(
        id="aws-sec-cloudtrail",
        domain="security", category="logging", provider_name="aws",
        name="cloudtrail", display_name="CloudTrail Org Trail",
        description="Organization-wide CloudTrail logging",
        detail="Enable an organization trail that logs all management events "
        "across all accounts to a central S3 bucket.",
        icon="activity",
        implications=["All accounts, all regions", "S3 + optional CloudWatch Logs", "~$2/100k events"],
        config_values={"enable_org_trail": True, "trail_s3_bucket": ""},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-sec-guardduty",
        domain="security", category="protection", provider_name="aws",
        name="guardduty", display_name="GuardDuty",
        description="Threat detection across all accounts",
        detail="Enable Amazon GuardDuty with delegated admin in the security account. "
        "Automatic member account enrollment.",
        icon="shield",
        implications=["ML-based threat detection", "~$4/GB analyzed", "Delegated admin model"],
        config_values={"enable_guardduty": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="aws-sec-kms-org",
        domain="security", category="encryption", provider_name="aws",
        name="kms_org", display_name="Organization KMS",
        description="Shared KMS key for org-wide encryption",
        detail="A KMS key in the security account shared via key policy "
        "with all member accounts for default encryption.",
        icon="lock",
        implications=["~$1/month per key", "Cross-account key sharing", "CloudTrail key usage logging"],
        config_values={"enable_org_kms": True, "kms_key_alias": "org-key"},
        sort_order=1, is_default=True, tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# Azure LZ options
# ═══════════════════════════════════════════════════════════════════════

_AZURE_OPTIONS: list[ConfigOption] = [
    # ── Organization ────────────────────────────────────────────────
    ConfigOption(
        id="az-org-sub-isolation",
        domain="organization", category="isolation", provider_name="azure",
        name="subscription_isolation", display_name="Subscription per Env",
        description="Separate Azure subscription per environment",
        detail="Each environment gets its own Azure subscription under a management group. "
        "Provides billing isolation and independent RBAC boundaries.",
        icon="layers",
        implications=["Billing boundary per environment", "Subscription-level RBAC", "Management group hierarchy"],
        config_values={"isolation_strategy": "subscription-per-env"},
        conflicts_with=["az-org-rg-isolation"],
        sort_order=1, is_default=True, tags=["standard"],
        hierarchy_implications={
            "description": "Tenant > Management Group > Subscription per environment",
            "nodes": [
                {"typeId": "tenant", "label": "Azure AD Tenant", "parentId": None},
                {"typeId": "management_group", "label": "Platform MG", "parentId": "__idx_0"},
                {"typeId": "management_group", "label": "Workloads MG", "parentId": "__idx_0"},
                {"typeId": "subscription", "label": "Connectivity Sub", "parentId": "__idx_1"},
                {"typeId": "subscription", "label": "Identity Sub", "parentId": "__idx_1"},
                {"typeId": "subscription", "label": "Production Sub", "parentId": "__idx_2"},
                {"typeId": "subscription", "label": "Development Sub", "parentId": "__idx_2"},
                {"typeId": "vnet", "label": "Hub VNet", "parentId": "__idx_3"},
            ],
        },
    ),
    ConfigOption(
        id="az-org-rg-isolation",
        domain="organization", category="isolation", provider_name="azure",
        name="rg_isolation", display_name="Resource Group per Env",
        description="Separate resource groups in a shared subscription",
        detail="All environments in one subscription, isolated by resource group. "
        "Simpler but less isolation.",
        icon="layers",
        implications=["Shared subscription", "RG-level RBAC", "Simpler management"],
        config_values={"isolation_strategy": "rg-per-env"},
        conflicts_with=["az-org-sub-isolation"],
        sort_order=2, tags=["dev"],
        hierarchy_implications={
            "description": "Single subscription with resource groups",
            "nodes": [
                {"typeId": "subscription", "label": "Azure Subscription", "parentId": None},
                {"typeId": "resource_group", "label": "Shared Services RG", "parentId": "__idx_0"},
                {"typeId": "resource_group", "label": "Production RG", "parentId": "__idx_0"},
                {"typeId": "resource_group", "label": "Development RG", "parentId": "__idx_0"},
                {"typeId": "vnet", "label": "Hub VNet", "parentId": "__idx_1"},
            ],
        },
    ),
    ConfigOption(
        id="az-org-hub-spoke",
        domain="organization", category="topology", provider_name="azure",
        name="hub_spoke", display_name="Hub-Spoke",
        description="Hub VNet with spoke VNet peering",
        detail="Central hub VNet with VNet peering to spoke VNets. "
        "Firewall/NVA in hub for centralized inspection.",
        icon="network",
        implications=["VNet peering", "Centralized firewall", "Standard Azure pattern"],
        config_values={"topology": "hub-spoke"},
        conflicts_with=["az-org-flat"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-org-flat",
        domain="organization", category="topology", provider_name="azure",
        name="flat", display_name="Flat (Direct Peering)",
        description="Direct VNet peering without hub",
        detail="VNets peer directly without a centralized hub. "
        "No centralized inspection or routing.",
        icon="network",
        implications=["No hub VNet", "Point-to-point peering", "Simple but limited"],
        config_values={"topology": "flat"},
        conflicts_with=["az-org-hub-spoke"],
        sort_order=2, tags=["dev"],
    ),
    ConfigOption(
        id="az-org-central-dns",
        domain="organization", category="shared_services", provider_name="azure",
        name="central_dns", display_name="Azure Private DNS",
        description="Centralized private DNS zones in hub",
        detail="Private DNS zones in the connectivity subscription, "
        "linked to all spoke VNets.",
        icon="globe",
        implications=["Private DNS zones in hub", "VNet links to spokes", "Centralized management"],
        config_values={"shared_dns": "central"},
        conflicts_with=["az-org-distributed-dns"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-org-distributed-dns",
        domain="organization", category="shared_services", provider_name="azure",
        name="distributed_dns", display_name="Per-Sub DNS",
        description="DNS zones per subscription",
        detail="Each subscription manages its own private DNS zones.",
        icon="globe",
        implications=["Independent zones", "No cross-subscription resolution", "Simpler but fragmented"],
        config_values={"shared_dns": "distributed"},
        conflicts_with=["az-org-central-dns"],
        sort_order=2, tags=["dev"],
    ),

    # ── Network ─────────────────────────────────────────────────────
    ConfigOption(
        id="az-net-hub-medium",
        domain="network", category="hub_network", provider_name="azure",
        name="hub_medium", display_name="Standard Hub VNet (/20)",
        description="4094 addresses for hub VNet",
        detail="A /20 hub VNet in the connectivity subscription.",
        icon="network",
        implications=["4094 usable IPs", "AzureFirewall + Gateway subnets", "Standard enterprise size"],
        config_values={"hub_vnet_cidr": "10.0.0.0/20"},
        conflicts_with=["az-net-hub-large"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-net-hub-large",
        domain="network", category="hub_network", provider_name="azure",
        name="hub_large", display_name="Large Hub VNet (/16)",
        description="65534 addresses for hub VNet",
        detail="A /16 hub VNet for large enterprise deployments.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended size", "Plan subnetting carefully"],
        config_values={"hub_vnet_cidr": "10.0.0.0/16"},
        conflicts_with=["az-net-hub-medium"],
        sort_order=2, tags=["enterprise"],
    ),
    ConfigOption(
        id="az-net-expressroute",
        domain="network", category="connectivity", provider_name="azure",
        name="expressroute", display_name="ExpressRoute",
        description="Private connectivity to on-premises",
        detail="ExpressRoute circuit for private, low-latency on-premises connectivity.",
        icon="link",
        implications=["Private peering", "~$55/month + circuit cost", "ExpressRoute Gateway required"],
        config_values={"enable_expressroute": True},
        sort_order=1, tags=["enterprise"],
    ),

    # ── IAM ─────────────────────────────────────────────────────────
    ConfigOption(
        id="az-iam-policy-baseline",
        domain="iam", category="policies", provider_name="azure",
        name="policy_baseline", display_name="Azure Policy Baseline",
        description="Built-in policy initiative for security baseline",
        detail="Assign the Azure Security Benchmark initiative at the management group level.",
        icon="shield",
        implications=["Security benchmark compliance", "Policy inheritance", "Audit + deny modes"],
        config_values={"enable_policy_baseline": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-iam-pim",
        domain="iam", category="access_control", provider_name="azure",
        name="pim", display_name="Privileged Identity Mgmt",
        description="Just-in-time elevated access with PIM",
        detail="Enable Azure AD PIM for just-in-time privileged access. "
        "Users request elevation with approval workflows.",
        icon="lock",
        implications=["JIT access", "Approval required", "Azure AD P2 license required"],
        config_values={"enable_pim": True},
        sort_order=1, tags=["enterprise"],
    ),

    # ── Security ────────────────────────────────────────────────────
    ConfigOption(
        id="az-sec-log-analytics",
        domain="security", category="logging", provider_name="azure",
        name="log_analytics", display_name="Central Log Analytics",
        description="Centralized Log Analytics workspace",
        detail="A central Log Analytics workspace for diagnostic logs, "
        "Activity Logs, and Azure Monitor data.",
        icon="activity",
        implications=["Centralized log sink", "~$2.76/GB ingested", "30-day default retention"],
        config_values={"enable_central_logs": True, "log_retention_days": 90},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-sec-defender",
        domain="security", category="protection", provider_name="azure",
        name="defender", display_name="Defender for Cloud",
        description="Microsoft Defender for Cloud across subscriptions",
        detail="Enable Defender for Cloud at the management group level "
        "with auto-provisioning of agents.",
        icon="shield",
        implications=["CSPM + CWP", "Auto-provisioning", "Per-resource pricing"],
        config_values={"enable_defender": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="az-sec-keyvault-org",
        domain="security", category="encryption", provider_name="azure",
        name="keyvault_org", display_name="Central Key Vault",
        description="Shared Key Vault for org-wide encryption keys",
        detail="A Key Vault in the management subscription for encryption keys "
        "shared across subscriptions.",
        icon="lock",
        implications=["HSM-backed keys available", "RBAC access model", "Soft-delete mandatory"],
        config_values={"enable_central_keyvault": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# GCP LZ options
# ═══════════════════════════════════════════════════════════════════════

_GCP_OPTIONS: list[ConfigOption] = [
    # ── Organization ────────────────────────────────────────────────
    ConfigOption(
        id="gcp-org-project-isolation",
        domain="organization", category="isolation", provider_name="gcp",
        name="project_isolation", display_name="Project per Environment",
        description="Separate GCP project per environment",
        detail="Each environment gets its own GCP project under a folder structure. "
        "Standard GCP isolation pattern.",
        icon="layers",
        implications=["IAM boundary per project", "Billing labels", "Folder hierarchy"],
        config_values={"isolation_strategy": "project-per-env"},
        conflicts_with=["gcp-org-vpc-isolation"],
        sort_order=1, is_default=True, tags=["standard"],
        hierarchy_implications={
            "description": "Organization > Folder > Project per environment",
            "nodes": [
                {"typeId": "organization", "label": "GCP Organization", "parentId": None},
                {"typeId": "folder", "label": "Shared Services", "parentId": "__idx_0"},
                {"typeId": "folder", "label": "Workloads", "parentId": "__idx_0"},
                {"typeId": "project", "label": "Shared VPC Host Project", "parentId": "__idx_1"},
                {"typeId": "project", "label": "Production Project", "parentId": "__idx_2"},
                {"typeId": "project", "label": "Development Project", "parentId": "__idx_2"},
                {"typeId": "vpc", "label": "Shared VPC", "parentId": "__idx_3"},
            ],
        },
    ),
    ConfigOption(
        id="gcp-org-vpc-isolation",
        domain="organization", category="isolation", provider_name="gcp",
        name="vpc_isolation", display_name="Shared VPC",
        description="Single project with Shared VPC subnets",
        detail="One host project with Shared VPC, service projects get subnets. "
        "Centralized network with project-level isolation.",
        icon="layers",
        implications=["Single Shared VPC", "Centralized networking", "Service project model"],
        config_values={"isolation_strategy": "shared-vpc"},
        conflicts_with=["gcp-org-project-isolation"],
        sort_order=2, tags=["enterprise"],
        hierarchy_implications={
            "description": "Shared VPC host project with service projects",
            "nodes": [
                {"typeId": "organization", "label": "GCP Organization", "parentId": None},
                {"typeId": "project", "label": "Shared VPC Host", "parentId": "__idx_0"},
                {"typeId": "project", "label": "Production Service Project", "parentId": "__idx_0"},
                {"typeId": "project", "label": "Development Service Project", "parentId": "__idx_0"},
                {"typeId": "vpc", "label": "Shared VPC", "parentId": "__idx_1"},
            ],
        },
    ),
    ConfigOption(
        id="gcp-org-hub-spoke",
        domain="organization", category="topology", provider_name="gcp",
        name="hub_spoke", display_name="Hub-Spoke",
        description="Hub VPC with VPC peering to spokes",
        detail="Central hub VPC with peering to spoke VPCs or Shared VPC subnets.",
        icon="network",
        implications=["VPC peering or Shared VPC", "Cloud Router for centralized routing", "Standard GCP pattern"],
        config_values={"topology": "hub-spoke"},
        conflicts_with=["gcp-org-flat"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-org-flat",
        domain="organization", category="topology", provider_name="gcp",
        name="flat", display_name="Flat (Single VPC)",
        description="Single VPC for all environments",
        detail="All environments share a single VPC with subnet isolation.",
        icon="network",
        implications=["No VPC peering needed", "Subnet-level isolation", "Simple but limited"],
        config_values={"topology": "flat"},
        conflicts_with=["gcp-org-hub-spoke"],
        sort_order=2, tags=["dev"],
    ),
    ConfigOption(
        id="gcp-org-central-dns",
        domain="organization", category="shared_services", provider_name="gcp",
        name="central_dns", display_name="Cloud DNS Central",
        description="Centralized Cloud DNS private zones",
        detail="Cloud DNS private zones in the host project, visible to all VPCs.",
        icon="globe",
        implications=["DNS peering zones", "Centralized management", "Cloud DNS forwarding"],
        config_values={"shared_dns": "central"},
        conflicts_with=["gcp-org-distributed-dns"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-org-distributed-dns",
        domain="organization", category="shared_services", provider_name="gcp",
        name="distributed_dns", display_name="Per-Project DNS",
        description="DNS zones per project",
        detail="Each project manages its own Cloud DNS zones.",
        icon="globe",
        implications=["Independent zones", "No cross-project resolution", "Simpler but fragmented"],
        config_values={"shared_dns": "distributed"},
        conflicts_with=["gcp-org-central-dns"],
        sort_order=2, tags=["dev"],
    ),

    # ── Network ─────────────────────────────────────────────────────
    ConfigOption(
        id="gcp-net-hub-medium",
        domain="network", category="hub_network", provider_name="gcp",
        name="hub_medium", display_name="Standard Hub VPC (/20)",
        description="4094 addresses for hub VPC",
        detail="A /20 primary range for the hub VPC.",
        icon="network",
        implications=["4094 usable IPs", "Room for multiple subnets", "Standard size"],
        config_values={"hub_vpc_cidr": "10.0.0.0/20"},
        conflicts_with=["gcp-net-hub-large"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-net-hub-large",
        domain="network", category="hub_network", provider_name="gcp",
        name="hub_large", display_name="Large Hub VPC (/16)",
        description="65534 addresses for hub VPC",
        detail="A /16 primary range for large deployments.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended", "Plan secondary ranges for GKE"],
        config_values={"hub_vpc_cidr": "10.0.0.0/16"},
        conflicts_with=["gcp-net-hub-medium"],
        sort_order=2, tags=["enterprise"],
    ),
    ConfigOption(
        id="gcp-net-cloud-interconnect",
        domain="network", category="connectivity", provider_name="gcp",
        name="cloud_interconnect", display_name="Cloud Interconnect",
        description="Dedicated or partner interconnect to on-premises",
        detail="Cloud Interconnect for private, low-latency on-premises connectivity.",
        icon="link",
        implications=["Private connectivity", "Dedicated or partner", "Cloud Router required"],
        config_values={"enable_cloud_interconnect": True},
        sort_order=1, tags=["enterprise"],
    ),

    # ── IAM ─────────────────────────────────────────────────────────
    ConfigOption(
        id="gcp-iam-org-policy",
        domain="iam", category="policies", provider_name="gcp",
        name="org_policies", display_name="Org Policy Constraints",
        description="Organization policy constraints for guardrails",
        detail="Apply org policy constraints: restrict resource locations, "
        "disable service account key creation, enforce uniform bucket access.",
        icon="shield",
        implications=["Location restrictions", "No SA key creation", "Uniform bucket access"],
        config_values={"enable_org_policies": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-iam-workload-id",
        domain="iam", category="identity", provider_name="gcp",
        name="workload_identity", display_name="Workload Identity",
        description="Keyless workload authentication",
        detail="Enable Workload Identity Federation and GKE Workload Identity. "
        "No service account keys needed.",
        icon="user",
        implications=["Keyless authentication", "GKE pod identity", "Federation with external IdPs"],
        config_values={"enable_workload_identity": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),

    # ── Security ────────────────────────────────────────────────────
    ConfigOption(
        id="gcp-sec-org-log-sink",
        domain="security", category="logging", provider_name="gcp",
        name="org_log_sink", display_name="Org Log Sink",
        description="Organization-level log sink to BigQuery",
        detail="An organization-level log sink routing audit logs to a central BigQuery dataset.",
        icon="activity",
        implications=["All projects, all log types", "BigQuery for analytics", "Log Router pricing"],
        config_values={"enable_org_log_sink": True, "log_sink_destination": "bigquery"},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-sec-scc",
        domain="security", category="protection", provider_name="gcp",
        name="scc", display_name="Security Command Center",
        description="Cloud-native security and risk management",
        detail="Enable Security Command Center Premium for vulnerability scanning, "
        "threat detection, and compliance monitoring.",
        icon="shield",
        implications=["Vulnerability scanning", "Threat detection", "SCC Premium pricing"],
        config_values={"enable_scc": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="gcp-sec-kms-org",
        domain="security", category="encryption", provider_name="gcp",
        name="kms_org", display_name="Organization CMEK",
        description="Customer-managed encryption keys",
        detail="Cloud KMS keyring in the security project for "
        "customer-managed encryption keys (CMEK) across projects.",
        icon="lock",
        implications=["$0.06/key version/month", "Automatic rotation", "Cross-project key sharing"],
        config_values={"enable_org_kms": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# OCI LZ options
# ═══════════════════════════════════════════════════════════════════════

_OCI_OPTIONS: list[ConfigOption] = [
    # ── Organization ────────────────────────────────────────────────
    ConfigOption(
        id="oci-org-compartment",
        domain="organization", category="isolation", provider_name="oci",
        name="compartment_isolation", display_name="Compartment Isolation",
        description="One compartment per environment within a single tenancy",
        detail="Environments are isolated using OCI compartments. "
        "Simpler than sub-tenancies, suitable for most workloads.",
        icon="folder",
        implications=["Single tenancy, lower overhead", "Compartment-level IAM policies", "Shared tenancy-level resources"],
        config_values={"isolation_strategy": "compartment-per-env"},
        conflicts_with=["oci-org-subtenancy"],
        sort_order=1, is_default=True, tags=["standard"],
        hierarchy_implications={
            "description": "Tenancy > Compartment per environment",
            "nodes": [
                {"typeId": "tenancy", "label": "OCI Tenancy", "parentId": None},
                {"typeId": "compartment", "label": "Shared Services", "parentId": "__idx_0"},
                {"typeId": "compartment", "label": "Production", "parentId": "__idx_0"},
                {"typeId": "compartment", "label": "Development", "parentId": "__idx_0"},
                {"typeId": "vcn", "label": "Hub VCN", "parentId": "__idx_1"},
            ],
        },
    ),
    ConfigOption(
        id="oci-org-subtenancy",
        domain="organization", category="isolation", provider_name="oci",
        name="subtenancy_isolation", display_name="Sub-Tenancy Isolation",
        description="Separate OCI sub-tenancy per environment",
        detail="Each environment gets its own sub-tenancy. "
        "Strongest isolation but requires OCI Organizations.",
        icon="layers",
        implications=["Full IAM isolation", "OCI Organizations required", "Higher administrative overhead"],
        config_values={"isolation_strategy": "subtenancy-per-env"},
        conflicts_with=["oci-org-compartment"],
        sort_order=2, tags=["enterprise"],
        hierarchy_implications={
            "description": "Parent Tenancy > Sub-Tenancy per environment",
            "nodes": [
                {"typeId": "tenancy", "label": "Parent Tenancy", "parentId": None},
                {"typeId": "tenancy", "label": "Shared Services Tenancy", "parentId": "__idx_0"},
                {"typeId": "tenancy", "label": "Production Tenancy", "parentId": "__idx_0"},
                {"typeId": "tenancy", "label": "Development Tenancy", "parentId": "__idx_0"},
                {"typeId": "vcn", "label": "Hub VCN", "parentId": "__idx_1"},
            ],
        },
    ),
    ConfigOption(
        id="oci-org-hub-spoke",
        domain="organization", category="topology", provider_name="oci",
        name="hub_spoke", display_name="Hub-Spoke",
        description="Hub VCN with DRG for spoke connectivity",
        detail="Central hub VCN connected to spoke VCNs via DRG. "
        "Centralized routing and network inspection.",
        icon="network",
        implications=["DRG for routing", "Centralized inspection", "Standard OCI pattern"],
        config_values={"topology": "hub-spoke"},
        conflicts_with=["oci-org-flat"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-org-flat",
        domain="organization", category="topology", provider_name="oci",
        name="flat", display_name="Flat (Local Peering)",
        description="Direct VCN local peering",
        detail="VCNs connected via Local Peering Gateways. No centralized routing.",
        icon="network",
        implications=["No DRG needed", "Point-to-point peering", "Simple but limited"],
        config_values={"topology": "flat"},
        conflicts_with=["oci-org-hub-spoke"],
        sort_order=2, tags=["dev"],
    ),
    ConfigOption(
        id="oci-org-central-dns",
        domain="organization", category="shared_services", provider_name="oci",
        name="central_dns", display_name="Central DNS Resolver",
        description="Shared DNS resolver in hub VCN",
        detail="OCI DNS resolver in the hub VCN with forwarding rules for spoke VCNs.",
        icon="globe",
        implications=["Hub-based DNS resolver", "Forwarding rules per VCN", "Centralized management"],
        config_values={"shared_dns": "central"},
        conflicts_with=["oci-org-distributed-dns"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-org-distributed-dns",
        domain="organization", category="shared_services", provider_name="oci",
        name="distributed_dns", display_name="Per-Compartment DNS",
        description="DNS resolvers per compartment",
        detail="Each compartment manages its own DNS resolver.",
        icon="globe",
        implications=["Independent resolvers", "No cross-compartment resolution", "Simpler but fragmented"],
        config_values={"shared_dns": "distributed"},
        conflicts_with=["oci-org-central-dns"],
        sort_order=2, tags=["dev"],
    ),

    # ── Network ─────────────────────────────────────────────────────
    ConfigOption(
        id="oci-net-hub-medium",
        domain="network", category="hub_network", provider_name="oci",
        name="hub_medium", display_name="Standard Hub VCN (/20)",
        description="4094 addresses for hub VCN",
        detail="A /20 hub VCN for centralized services and DRG connectivity.",
        icon="network",
        implications=["4094 usable IPs", "Room for service subnets", "Standard size"],
        config_values={"hub_vcn_cidr": "10.0.0.0/20"},
        conflicts_with=["oci-net-hub-large"],
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-net-hub-large",
        domain="network", category="hub_network", provider_name="oci",
        name="hub_large", display_name="Large Hub VCN (/16)",
        description="65534 addresses for hub VCN",
        detail="A /16 hub VCN for large-scale enterprise deployments.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended", "Plan subnetting carefully"],
        config_values={"hub_vcn_cidr": "10.0.0.0/16"},
        conflicts_with=["oci-net-hub-medium"],
        sort_order=2, tags=["enterprise"],
    ),
    ConfigOption(
        id="oci-net-drg",
        domain="network", category="connectivity", provider_name="oci",
        name="drg", display_name="Dynamic Routing Gateway",
        description="DRG for hub-spoke and on-premises connectivity",
        detail="OCI Dynamic Routing Gateway for centralized routing between VCNs "
        "and on-premises via FastConnect or IPSec.",
        icon="link",
        implications=["Centralized routing", "FastConnect + IPSec support", "DRG v2 with route tables"],
        config_values={"enable_drg": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-net-service-gw",
        domain="network", category="gateway", provider_name="oci",
        name="service_gateway", display_name="Service Gateway",
        description="Private access to OCI services without internet",
        detail="Service Gateway for private connectivity to OCI Object Storage, "
        "Streaming, and other Oracle services.",
        icon="zap",
        implications=["No internet transit needed", "Free data transfer", "Per-VCN service gateway"],
        config_values={"enable_service_gateway": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),

    # ── IAM ─────────────────────────────────────────────────────────
    ConfigOption(
        id="oci-iam-compartment-policies",
        domain="iam", category="policies", provider_name="oci",
        name="compartment_policies", display_name="Compartment Policies",
        description="Org-level IAM policies for compartment isolation",
        detail="IAM policies at the tenancy level that scope access to specific compartments. "
        "Enforces least-privilege across environments.",
        icon="shield",
        implications=["Tenancy-level policies", "Compartment scoping", "Group-based access"],
        config_values={"enable_org_policies": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-iam-mfa",
        domain="iam", category="identity", provider_name="oci",
        name="enforce_mfa", display_name="Enforce MFA",
        description="Require MFA for all IAM users",
        detail="Enforce multi-factor authentication for all OCI IAM users. "
        "TOTP or FIDO2 security keys.",
        icon="lock",
        implications=["TOTP or FIDO2", "Identity domain policy", "Required for compliance"],
        config_values={"enforce_mfa": True},
        sort_order=1, tags=["enterprise"],
    ),

    # ── Security ────────────────────────────────────────────────────
    ConfigOption(
        id="oci-sec-audit-logs",
        domain="security", category="logging", provider_name="oci",
        name="audit_logs", display_name="OCI Audit Logs",
        description="Tenancy-wide audit log retention",
        detail="Enable audit log retention with Service Connector Hub "
        "routing logs to Object Storage or Logging Analytics.",
        icon="activity",
        implications=["90-day default retention", "Service Connector Hub routing", "Logging Analytics optional"],
        config_values={"enable_audit_logs": True, "audit_retention_days": 365},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-sec-cloud-guard",
        domain="security", category="protection", provider_name="oci",
        name="cloud_guard", display_name="Cloud Guard",
        description="OCI Cloud Guard for threat detection",
        detail="Enable Cloud Guard at the tenancy level for automated "
        "threat detection and response.",
        icon="shield",
        implications=["Automated detection", "Responder recipes", "Free with OCI"],
        config_values={"enable_cloud_guard": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
    ConfigOption(
        id="oci-sec-vault-org",
        domain="security", category="encryption", provider_name="oci",
        name="vault_org", display_name="OCI Vault (Org)",
        description="Shared vault for org-wide encryption keys",
        detail="An OCI Vault in the shared services compartment for "
        "customer-managed master encryption keys.",
        icon="lock",
        implications=["HSM-backed keys", "Cross-compartment key sharing", "Key version rotation"],
        config_values={"enable_org_vault": True},
        sort_order=1, is_default=True, tags=["standard"],
    ),
]


# ── Registry & Lookup Functions ────────────────────────────────────────

_ALL_OPTIONS: list[ConfigOption] = (
    _PROXMOX_OPTIONS + _AWS_OPTIONS + _AZURE_OPTIONS + _GCP_OPTIONS + _OCI_OPTIONS
)

_BY_ID: dict[str, ConfigOption] = {o.id: o for o in _ALL_OPTIONS}

_BY_PROVIDER_DOMAIN: dict[str, list[ConfigOption]] = {}
for _opt in _ALL_OPTIONS:
    _key = f"{_opt.provider_name}:{_opt.domain}"
    _BY_PROVIDER_DOMAIN.setdefault(_key, []).append(_opt)


def get_lz_option_catalog(provider_name: str, domain: str) -> list[ConfigOption]:
    """Return all LZ options for a provider + domain, sorted by sort_order."""
    key = f"{provider_name}:{domain}"
    options = _BY_PROVIDER_DOMAIN.get(key, [])
    return sorted(options, key=lambda o: o.sort_order)


def get_lz_option_categories(provider_name: str, domain: str) -> list[CategoryInfo]:
    """Return categories for a domain, filtered to only those with options for this provider."""
    all_cats = _CATEGORIES_BY_DOMAIN.get(domain, [])
    options = get_lz_option_catalog(provider_name, domain)
    used_cats = {o.category for o in options}
    return [c for c in all_cats if c.name in used_cats]


def get_lz_option_by_id(option_id: str) -> ConfigOption | None:
    """Look up a single LZ option by its ID."""
    return _BY_ID.get(option_id)
