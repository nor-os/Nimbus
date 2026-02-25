"""
Overview: Environment configuration option catalog — preset choices that map to ENV_*_SCHEMAS fields.
Architecture: Static data module for guided environment configuration (Section 7.2)
Dependencies: None (pure data module)
Concepts: ConfigOptions are preset config tiles whose config_values map directly to fields
    defined in credential_schemas.py (ENV_NETWORK_SCHEMAS, ENV_IAM_SCHEMAS, etc.).
    Each option represents a quick-start preset — not an architectural decision (those are
    at the landing zone / foundation level). Environments are spokes that inherit foundation
    settings; these presets fill in the spoke-level overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConfigOption:
    """A single selectable configuration option tile."""

    id: str
    domain: str  # network, iam, security, monitoring
    category: str  # e.g. "ip_pool", "subnets"
    provider_name: str
    name: str
    display_name: str
    description: str
    detail: str  # longer explanation for detail panel
    icon: str
    implications: list[str] = field(default_factory=list)
    config_values: dict = field(default_factory=dict)
    conflicts_with: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    related_resolver_types: list[str] = field(default_factory=list)
    related_component_names: list[str] = field(default_factory=list)
    sort_order: int = 0
    is_default: bool = False
    tags: list[str] = field(default_factory=list)
    hierarchy_implications: dict | None = None


@dataclass(frozen=True)
class CategoryInfo:
    """Metadata for a category grouping within a domain."""

    name: str
    display_name: str
    description: str
    icon: str


# ── Category Definitions ───────────────────────────────────────────────
# Categories map to logical groups of fields within each ENV_*_SCHEMA.

NETWORK_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("ip_pool", "IP Pool", "IP addressing for this environment's workloads", "network"),
    CategoryInfo("features", "Features", "Network features and gateways", "toggle"),
]

IAM_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("pool", "Resource Pool", "Compute resource pool assignment", "folder"),
    CategoryInfo("acl", "Access Control", "ACL entries and role assignments", "lock"),
]

SECURITY_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("firewall", "Firewall Rules", "Inbound/outbound traffic rules", "shield"),
    CategoryInfo("encryption", "Encryption", "Encryption keys and settings", "lock"),
    CategoryInfo("backup", "Backup", "Backup schedule and storage", "archive"),
]

MONITORING_CATEGORIES: list[CategoryInfo] = [
    CategoryInfo("budget", "Budget", "Spending limits and alerts", "dollar"),
    CategoryInfo("alerts", "Alerts", "Alert channels and notifications", "bell"),
]

_CATEGORIES_BY_DOMAIN: dict[str, list[CategoryInfo]] = {
    "network": NETWORK_CATEGORIES,
    "iam": IAM_CATEGORIES,
    "security": SECURITY_CATEGORIES,
    "monitoring": MONITORING_CATEGORIES,
}

# ═══════════════════════════════════════════════════════════════════════
# Proxmox environment options
# Schema fields: vlan_id, bridge_override, ip_pool_cidr, subnets[]
# ═══════════════════════════════════════════════════════════════════════

_PROXMOX_OPTIONS: list[ConfigOption] = [
    # Network — IP Pool
    ConfigOption(
        id="pve-net-small-pool",
        domain="network",
        category="ip_pool",
        provider_name="proxmox",
        name="small_pool",
        display_name="Small IP Pool (/26)",
        description="62 usable addresses for small environments",
        detail="Allocates a /26 CIDR block (62 usable IPs) for this environment. "
        "Suitable for dev/test environments with fewer than 50 VMs.",
        icon="network",
        implications=[
            "62 usable IP addresses",
            "Suitable for up to ~50 VMs",
            "Leaves room for other environments in the address space",
        ],
        config_values={"ip_pool_cidr": "10.0.0.0/26"},
        conflicts_with=["pve-net-medium-pool", "pve-net-large-pool"],
        related_resolver_types=["ipam"],
        sort_order=1,
        is_default=True,
        tags=["dev"],
    ),
    ConfigOption(
        id="pve-net-medium-pool",
        domain="network",
        category="ip_pool",
        provider_name="proxmox",
        name="medium_pool",
        display_name="Medium IP Pool (/24)",
        description="254 usable addresses for standard workloads",
        detail="Allocates a /24 CIDR block (254 usable IPs). The standard size "
        "for most production environments running a mix of VMs and containers.",
        icon="network",
        implications=[
            "254 usable IP addresses",
            "Standard production size",
            "Fits most workload patterns",
        ],
        config_values={"ip_pool_cidr": "10.0.0.0/24"},
        conflicts_with=["pve-net-small-pool", "pve-net-large-pool"],
        related_resolver_types=["ipam"],
        sort_order=2,
        tags=["standard"],
    ),
    ConfigOption(
        id="pve-net-large-pool",
        domain="network",
        category="ip_pool",
        provider_name="proxmox",
        name="large_pool",
        display_name="Large IP Pool (/22)",
        description="1022 usable addresses for large deployments",
        detail="Allocates a /22 CIDR block (1022 usable IPs). For environments "
        "with many VMs, containers, or Kubernetes clusters requiring large address spaces.",
        icon="network",
        implications=[
            "1022 usable IP addresses",
            "For large-scale deployments",
            "Consider subnetting within this block",
        ],
        config_values={"ip_pool_cidr": "10.0.0.0/22"},
        conflicts_with=["pve-net-small-pool", "pve-net-medium-pool"],
        related_resolver_types=["ipam"],
        sort_order=3,
        tags=["enterprise"],
    ),
    # Network — Features (VLAN)
    ConfigOption(
        id="pve-net-vlan-tag",
        domain="network",
        category="features",
        provider_name="proxmox",
        name="vlan_tag",
        display_name="VLAN Isolation",
        description="Assign a dedicated VLAN ID to this environment",
        detail="Tags this environment's traffic with a dedicated VLAN ID. "
        "Requires VLAN-aware bridging configured at the landing zone level. "
        "Each environment gets its own broadcast domain.",
        icon="tag",
        implications=[
            "Requires VLAN-aware bridge on the landing zone",
            "Provides L2 isolation from other environments",
            "VLAN ID set here or auto-assigned by IPAM resolver",
        ],
        config_values={"vlan_id": 100},
        related_resolver_types=["ipam"],
        sort_order=20,
        tags=["standard"],
    ),
    ConfigOption(
        id="pve-net-bridge-override",
        domain="network",
        category="features",
        provider_name="proxmox",
        name="bridge_override",
        display_name="Bridge Override",
        description="Use a different bridge than the landing zone default",
        detail="Overrides the default Linux bridge (vmbr0) with a custom bridge "
        "for this environment. Useful when environments need dedicated physical NICs "
        "or separate network paths.",
        icon="toggle",
        implications=[
            "Overrides landing zone default bridge",
            "Bridge must exist on all cluster nodes",
            "Use for dedicated network interfaces",
        ],
        config_values={"bridge_override": "vmbr1"},
        sort_order=21,
        tags=["enterprise"],
    ),

    # IAM — Resource Pool
    ConfigOption(
        id="pve-iam-default-pool",
        domain="iam",
        category="pool",
        provider_name="proxmox",
        name="default_pool",
        display_name="Default Pool",
        description="Use the cluster's default resource pool",
        detail="VMs in this environment are placed in the default resource pool. "
        "No resource limits or quotas — shares capacity with all other environments.",
        icon="folder",
        implications=[
            "No per-environment resource limits",
            "Shared with other environments",
            "Simplest setup",
        ],
        config_values={"pool_name": "default"},
        conflicts_with=["pve-iam-dedicated-pool"],
        sort_order=1,
        is_default=True,
        tags=["dev"],
    ),
    ConfigOption(
        id="pve-iam-dedicated-pool",
        domain="iam",
        category="pool",
        provider_name="proxmox",
        name="dedicated_pool",
        display_name="Dedicated Pool",
        description="Assign a dedicated resource pool with quotas",
        detail="Creates a dedicated Proxmox resource pool for this environment. "
        "Allows setting CPU/memory limits to prevent resource contention.",
        icon="folder",
        implications=[
            "Per-environment resource quotas",
            "Prevents noisy-neighbor issues",
            "Pool name auto-derived from environment name",
        ],
        config_values={"pool_name": ""},
        conflicts_with=["pve-iam-default-pool"],
        sort_order=2,
        tags=["standard"],
    ),
    # IAM — ACL preset
    ConfigOption(
        id="pve-iam-acl-readonly",
        domain="iam",
        category="acl",
        provider_name="proxmox",
        name="acl_readonly",
        display_name="Read-Only ACL",
        description="Viewers can see but not modify VMs",
        detail="Sets ACL entries that grant read-only access to the environment's "
        "resource pool. Operators and admins get full access; everyone else can only view.",
        icon="lock",
        implications=[
            "Viewers: PVEAuditor role",
            "Operators: PVEVMAdmin role",
            "ACL propagates to child resources",
        ],
        config_values={
            "acl_entries": [
                {"path": "/pool/{pool}", "role": "PVEAuditor", "propagate": True},
            ],
        },
        sort_order=10,
        is_default=True,
        tags=["standard"],
    ),

    # Security — Backup
    ConfigOption(
        id="pve-sec-backup-daily",
        domain="security",
        category="backup",
        provider_name="proxmox",
        name="backup_daily",
        display_name="Daily Backups",
        description="Nightly backup at 02:00 UTC",
        detail="Schedules automated backups of all VMs in this environment to run "
        "daily at 02:00 UTC. Backups are stored in the default PBS storage target.",
        icon="archive",
        implications=[
            "Runs daily at 02:00 UTC",
            "Uses default backup storage",
            "Retention managed by PBS",
        ],
        config_values={
            "backup_schedule": "0 2 * * *",
            "backup_storage": "local",
        },
        conflicts_with=["pve-sec-backup-weekly"],
        sort_order=10,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="pve-sec-backup-weekly",
        domain="security",
        category="backup",
        provider_name="proxmox",
        name="backup_weekly",
        display_name="Weekly Backups",
        description="Sunday backup at 03:00 UTC",
        detail="Schedules weekly backups every Sunday at 03:00 UTC. "
        "Suitable for development environments where daily backups aren't needed.",
        icon="archive",
        implications=[
            "Runs every Sunday at 03:00 UTC",
            "Lower storage consumption",
            "Acceptable for non-critical workloads",
        ],
        config_values={
            "backup_schedule": "0 3 * * 0",
            "backup_storage": "local",
        },
        conflicts_with=["pve-sec-backup-daily"],
        sort_order=11,
        tags=["dev"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# AWS environment options
# Schema fields: vpc_cidr, availability_zones[], enable_dns_hostnames,
#   enable_nat_gateway, subnets[{name, cidr, az, type}]
# Security: security_groups[], kms_key_alias, default_encryption,
#   s3_block_public_access
# IAM: iam_roles[], service_accounts[]
# Monitoring: budget_limit, alert_email, enable_cost_anomaly_detection
# ═══════════════════════════════════════════════════════════════════════

_AWS_OPTIONS: list[ConfigOption] = [
    # Network — IP Pool (vpc_cidr)
    ConfigOption(
        id="aws-net-small-vpc",
        domain="network",
        category="ip_pool",
        provider_name="aws",
        name="small_vpc",
        display_name="Small VPC (/24)",
        description="254 addresses for dev/test workloads",
        detail="A /24 VPC CIDR block with 254 usable addresses. "
        "Good for small development environments with a handful of instances.",
        icon="network",
        implications=["254 usable IPs", "Limited subnet splitting", "Dev/test workloads"],
        config_values={"vpc_cidr": "10.0.0.0/24", "enable_dns_hostnames": True},
        conflicts_with=["aws-net-medium-vpc", "aws-net-large-vpc"],
        sort_order=1,
        tags=["dev"],
    ),
    ConfigOption(
        id="aws-net-medium-vpc",
        domain="network",
        category="ip_pool",
        provider_name="aws",
        name="medium_vpc",
        display_name="Standard VPC (/20)",
        description="4094 addresses for standard production",
        detail="A /20 VPC CIDR block with 4094 usable addresses. "
        "Allows splitting into multiple /24 subnets across AZs.",
        icon="network",
        implications=["4094 usable IPs", "Room for 16 subnets (/24 each)", "Standard production size"],
        config_values={"vpc_cidr": "10.0.0.0/20", "enable_dns_hostnames": True},
        conflicts_with=["aws-net-small-vpc", "aws-net-large-vpc"],
        sort_order=2,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="aws-net-large-vpc",
        domain="network",
        category="ip_pool",
        provider_name="aws",
        name="large_vpc",
        display_name="Large VPC (/16)",
        description="65534 addresses for large-scale workloads",
        detail="A /16 VPC CIDR block — the maximum recommended size. "
        "For large environments with many services, microservices, or EKS clusters.",
        icon="network",
        implications=["65534 usable IPs", "Maximum VPC size", "Plan subnetting carefully"],
        config_values={"vpc_cidr": "10.0.0.0/16", "enable_dns_hostnames": True},
        conflicts_with=["aws-net-small-vpc", "aws-net-medium-vpc"],
        sort_order=3,
        tags=["enterprise"],
    ),
    # Network — Features
    ConfigOption(
        id="aws-net-multi-az",
        domain="network",
        category="features",
        provider_name="aws",
        name="multi_az",
        display_name="Multi-AZ",
        description="Spread across multiple Availability Zones",
        detail="Configures subnets across 2-3 AZs for high availability. "
        "If one AZ fails, services failover to surviving AZs.",
        icon="toggle",
        implications=[
            "Higher cross-AZ data transfer costs",
            "Required for production SLAs",
            "AZ names set in availability_zones field",
        ],
        config_values={"availability_zones": ["us-east-1a", "us-east-1b", "us-east-1c"]},
        sort_order=20,
        tags=["standard"],
    ),

    # Security — Encryption
    ConfigOption(
        id="aws-sec-kms-default",
        domain="security",
        category="encryption",
        provider_name="aws",
        name="kms_default",
        display_name="KMS Encryption",
        description="Encrypt EBS/S3 with customer-managed KMS key",
        detail="Sets the default encryption to AWS KMS with a customer-managed key. "
        "All EBS volumes and S3 buckets created in this environment will use this key.",
        icon="lock",
        implications=[
            "~$1/month per CMK",
            "CloudTrail logs key usage",
            "Key alias set to environment name",
        ],
        config_values={"default_encryption": "aws:kms", "kms_key_alias": "env-key", "s3_block_public_access": True},
        conflicts_with=["aws-sec-sse-s3"],
        sort_order=5,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="aws-sec-sse-s3",
        domain="security",
        category="encryption",
        provider_name="aws",
        name="sse_s3",
        display_name="SSE-S3 Encryption",
        description="AWS-managed S3 encryption (no KMS cost)",
        detail="Uses Amazon S3-managed encryption keys (SSE-S3). No additional cost "
        "but less control over key management. Suitable for non-sensitive data.",
        icon="lock",
        implications=[
            "No additional cost",
            "AWS-managed keys (no rotation control)",
            "Cannot audit key usage",
        ],
        config_values={"default_encryption": "AES256", "s3_block_public_access": True},
        conflicts_with=["aws-sec-kms-default"],
        sort_order=6,
        tags=["dev"],
    ),

    # IAM — Roles preset
    ConfigOption(
        id="aws-iam-admin-role",
        domain="iam",
        category="acl",
        provider_name="aws",
        name="admin_role",
        display_name="Admin + ReadOnly Roles",
        description="Standard admin and read-only IAM roles",
        detail="Creates two IAM roles: an admin role with PowerUserAccess "
        "and a read-only role with ReadOnlyAccess. Foundation for role-based access.",
        icon="lock",
        implications=[
            "PowerUserAccess for admin role",
            "ReadOnlyAccess for viewer role",
            "Assume-role based (no static keys)",
        ],
        config_values={
            "iam_roles": [
                {"name": "env-admin", "description": "Environment admin", "managed_policy_names": ["PowerUserAccess"]},
                {"name": "env-readonly", "description": "Read-only", "managed_policy_names": ["ReadOnlyAccess"]},
            ],
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
    ),

    # Monitoring
    ConfigOption(
        id="aws-mon-budget-low",
        domain="monitoring",
        category="budget",
        provider_name="aws",
        name="budget_low",
        display_name="Dev Budget ($100)",
        description="$100/month budget with email alerts",
        detail="Sets a monthly budget of $100 with alerts at 50%, 80%, and 100%. "
        "Suitable for development/test environments.",
        icon="dollar",
        implications=["Alerts at $50, $80, $100", "Email notification required", "No auto-shutdown"],
        config_values={"budget_limit": 100, "alert_email": ""},
        conflicts_with=["aws-mon-budget-high"],
        sort_order=1,
        is_default=True,
        tags=["dev"],
    ),
    ConfigOption(
        id="aws-mon-budget-high",
        domain="monitoring",
        category="budget",
        provider_name="aws",
        name="budget_high",
        display_name="Prod Budget ($5000)",
        description="$5000/month budget with anomaly detection",
        detail="Sets a monthly budget of $5000 with alerts and enables "
        "AWS Cost Anomaly Detection for ML-based spending alerts.",
        icon="dollar",
        implications=["Alerts at $2500, $4000, $5000", "Cost Anomaly Detection enabled", "For production workloads"],
        config_values={"budget_limit": 5000, "alert_email": "", "enable_cost_anomaly_detection": True},
        conflicts_with=["aws-mon-budget-low"],
        sort_order=2,
        tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# Azure environment options
# Schema fields: vnet_cidr, dns_servers[], enable_ddos_protection,
#   subnets[{name, cidr, service_endpoints[]}]
# Security: nsgs[], key_vault_name, enable_key_vault, nsg_default_deny
# IAM: role_assignments[], managed_identities[]
# Monitoring: budget_limit, action_group_email
# ═══════════════════════════════════════════════════════════════════════

_AZURE_OPTIONS: list[ConfigOption] = [
    # Network — IP Pool (vnet_cidr)
    ConfigOption(
        id="az-net-small-vnet",
        domain="network",
        category="ip_pool",
        provider_name="azure",
        name="small_vnet",
        display_name="Small VNet (/24)",
        description="254 addresses for dev/test",
        detail="A /24 spoke VNet address space with 254 usable addresses.",
        icon="network",
        implications=["254 usable IPs", "Limited subnet splitting", "Dev/test workloads"],
        config_values={"vnet_cidr": "10.0.0.0/24"},
        conflicts_with=["az-net-medium-vnet", "az-net-large-vnet"],
        sort_order=1,
        tags=["dev"],
    ),
    ConfigOption(
        id="az-net-medium-vnet",
        domain="network",
        category="ip_pool",
        provider_name="azure",
        name="medium_vnet",
        display_name="Standard VNet (/20)",
        description="4094 addresses for production workloads",
        detail="A /20 spoke VNet for standard production environments. "
        "Room for multiple subnets across web, app, and data tiers.",
        icon="network",
        implications=["4094 usable IPs", "16 subnets at /24 each", "Standard production size"],
        config_values={"vnet_cidr": "10.0.0.0/20"},
        conflicts_with=["az-net-small-vnet", "az-net-large-vnet"],
        sort_order=2,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="az-net-large-vnet",
        domain="network",
        category="ip_pool",
        provider_name="azure",
        name="large_vnet",
        display_name="Large VNet (/16)",
        description="65534 addresses for large-scale workloads",
        detail="A /16 spoke VNet for large environments with many services.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended size", "Plan subnetting carefully"],
        config_values={"vnet_cidr": "10.0.0.0/16"},
        conflicts_with=["az-net-small-vnet", "az-net-medium-vnet"],
        sort_order=3,
        tags=["enterprise"],
    ),
    # Network — Features
    ConfigOption(
        id="az-net-ddos",
        domain="network",
        category="features",
        provider_name="azure",
        name="ddos_protection",
        display_name="DDoS Protection",
        description="Enable Azure DDoS Protection Standard",
        detail="Enables DDoS Protection Standard plan on the VNet. "
        "Protects all public IPs with automatic mitigation. Significant cost.",
        icon="toggle",
        implications=["~$2944/month base cost", "Automatic traffic scrubbing", "Required for some compliance"],
        config_values={"enable_ddos_protection": True},
        sort_order=20,
        tags=["enterprise"],
    ),
    # Security — Encryption
    ConfigOption(
        id="az-sec-keyvault",
        domain="security",
        category="encryption",
        provider_name="azure",
        name="keyvault",
        display_name="Key Vault",
        description="Create Azure Key Vault for secrets and keys",
        detail="Provisions an Azure Key Vault for this environment to manage "
        "encryption keys, certificates, and application secrets.",
        icon="lock",
        implications=["~$0.03/10k operations", "Soft-delete enabled", "HSM-backed keys available"],
        config_values={"enable_key_vault": True, "key_vault_name": ""},
        sort_order=5,
        is_default=True,
        tags=["standard"],
    ),
    # IAM
    ConfigOption(
        id="az-iam-rbac-preset",
        domain="iam",
        category="acl",
        provider_name="azure",
        name="rbac_preset",
        display_name="Contributor + Reader",
        description="Standard RBAC role assignments",
        detail="Creates role assignments for Contributor (operators) "
        "and Reader (viewers) at the resource group scope.",
        icon="lock",
        implications=["Contributor for operators", "Reader for viewers", "Azure AD groups recommended"],
        config_values={
            "role_assignments": [
                {"principal_name": "env-operators", "role_definition": "Contributor", "scope": "resource_group"},
                {"principal_name": "env-viewers", "role_definition": "Reader", "scope": "resource_group"},
            ],
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="az-iam-managed-id",
        domain="iam",
        category="acl",
        provider_name="azure",
        name="managed_identity",
        display_name="Managed Identity",
        description="System-assigned identity for Azure service auth",
        detail="Creates a user-assigned managed identity for this environment. "
        "Services authenticate to Azure resources without credentials in code.",
        icon="lock",
        implications=["No credentials in code", "Automatic token rotation", "RBAC for identity scope"],
        config_values={
            "managed_identities": [
                {"name": "env-identity", "type": "user_assigned"},
            ],
        },
        sort_order=2,
        tags=["standard"],
    ),
    # Monitoring
    ConfigOption(
        id="az-mon-budget-low",
        domain="monitoring",
        category="budget",
        provider_name="azure",
        name="budget_low",
        display_name="Dev Budget ($100)",
        description="$100/month with email alerts",
        detail="Monthly budget of $100 with action group email notification.",
        icon="dollar",
        implications=["Email alert at threshold", "No auto-actions", "Dev environments"],
        config_values={"budget_limit": 100, "action_group_email": ""},
        conflicts_with=["az-mon-budget-high"],
        sort_order=1,
        is_default=True,
        tags=["dev"],
    ),
    ConfigOption(
        id="az-mon-budget-high",
        domain="monitoring",
        category="budget",
        provider_name="azure",
        name="budget_high",
        display_name="Prod Budget ($5000)",
        description="$5000/month with action group alerts",
        detail="Monthly budget of $5000 with action group email notification.",
        icon="dollar",
        implications=["Multi-threshold alerts", "Action group integration", "Production workloads"],
        config_values={"budget_limit": 5000, "action_group_email": ""},
        conflicts_with=["az-mon-budget-low"],
        sort_order=2,
        tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# GCP environment options
# Schema fields: vpc_cidr, subnets[{name, cidr, region, private_google_access}],
#   enable_private_google_access
# Security: firewall_rules[], enable_vpc_flow_logs, enable_binary_authorization
# IAM: iam_bindings[], service_accounts[]
# Monitoring: budget_amount, notification_channels[]
# ═══════════════════════════════════════════════════════════════════════

_GCP_OPTIONS: list[ConfigOption] = [
    # Network — IP Pool
    ConfigOption(
        id="gcp-net-small",
        domain="network",
        category="ip_pool",
        provider_name="gcp",
        name="small_subnet",
        display_name="Small Subnet (/24)",
        description="254 addresses for dev/test",
        detail="A /24 primary IP range for this environment's subnet.",
        icon="network",
        implications=["254 usable IPs", "Single subnet", "Dev/test workloads"],
        config_values={"vpc_cidr": "10.0.0.0/24", "enable_private_google_access": True},
        conflicts_with=["gcp-net-medium", "gcp-net-large"],
        sort_order=1,
        tags=["dev"],
    ),
    ConfigOption(
        id="gcp-net-medium",
        domain="network",
        category="ip_pool",
        provider_name="gcp",
        name="medium_subnet",
        display_name="Standard Subnet (/20)",
        description="4094 addresses for production",
        detail="A /20 primary IP range. Standard production size with Private Google Access enabled.",
        icon="network",
        implications=["4094 usable IPs", "Private Google Access enabled", "Standard production size"],
        config_values={"vpc_cidr": "10.0.0.0/20", "enable_private_google_access": True},
        conflicts_with=["gcp-net-small", "gcp-net-large"],
        sort_order=2,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="gcp-net-large",
        domain="network",
        category="ip_pool",
        provider_name="gcp",
        name="large_subnet",
        display_name="Large Subnet (/16)",
        description="65534 addresses for GKE clusters",
        detail="A /16 primary IP range for environments with large GKE clusters or many services.",
        icon="network",
        implications=["65534 usable IPs", "GKE pod/service ranges need additional space", "Plan secondary ranges"],
        config_values={"vpc_cidr": "10.0.0.0/16", "enable_private_google_access": True},
        conflicts_with=["gcp-net-small", "gcp-net-medium"],
        sort_order=3,
        tags=["enterprise"],
    ),
    # IAM
    ConfigOption(
        id="gcp-iam-basic-bindings",
        domain="iam",
        category="acl",
        provider_name="gcp",
        name="basic_bindings",
        display_name="Editor + Viewer Bindings",
        description="Standard project-level IAM bindings",
        detail="Creates IAM bindings for editor (operators) and viewer (read-only) "
        "at the project level.",
        icon="lock",
        implications=["Editor for operators", "Viewer for read-only users", "Project-level binding"],
        config_values={
            "iam_bindings": [
                {"member": "group:operators", "role": "roles/editor"},
                {"member": "group:viewers", "role": "roles/viewer"},
            ],
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="gcp-iam-service-account",
        domain="iam",
        category="acl",
        provider_name="gcp",
        name="service_account",
        display_name="Service Account",
        description="Dedicated SA for workload identity",
        detail="Creates a Google service account for this environment. "
        "Use with Workload Identity for keyless GKE pod authentication.",
        icon="lock",
        implications=["No JSON keys needed with Workload Identity", "Scoped to environment", "Audit via Admin Activity logs"],
        config_values={
            "service_accounts": [
                {"name": "env-workload", "description": "Environment workload SA", "roles": ["roles/viewer"]},
            ],
        },
        sort_order=2,
        tags=["standard"],
    ),
    # Monitoring
    ConfigOption(
        id="gcp-mon-budget",
        domain="monitoring",
        category="budget",
        provider_name="gcp",
        name="budget",
        display_name="Budget Alert ($500)",
        description="Monthly budget with email + Pub/Sub",
        detail="Cloud Billing budget of $500 with email notifications "
        "at 50%, 80%, 100% thresholds.",
        icon="dollar",
        implications=["Email + Pub/Sub alerts", "Can trigger Cloud Functions", "Free to configure"],
        config_values={
            "budget_amount": 500,
            "notification_channels": [
                {"type": "email", "display_name": "Budget Alert", "address": ""},
            ],
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# OCI environment options
# Schema fields: vcn_cidr, dns_label, subnets[{name, cidr, type, security_list}],
#   enable_internet_gateway, enable_nat_gateway
# Security: security_lists[], enable_vault, vault_name, security_list_default_deny
# IAM: compartment_policies[], instance_principals[]
# Monitoring: budget_amount, alarm_topic{enabled, name, subscription_email}
# ═══════════════════════════════════════════════════════════════════════

_OCI_OPTIONS: list[ConfigOption] = [
    # Network — IP Pool
    ConfigOption(
        id="oci-net-small",
        domain="network",
        category="ip_pool",
        provider_name="oci",
        name="small_vcn",
        display_name="Small VCN (/24)",
        description="254 addresses for dev/test",
        detail="A /24 spoke VCN CIDR block with 254 usable addresses.",
        icon="network",
        implications=["254 usable IPs", "Limited subnet splitting", "Dev/test workloads"],
        config_values={"vcn_cidr": "10.0.0.0/24", "dns_label": "env",
                        "enable_internet_gateway": True, "enable_nat_gateway": True},
        conflicts_with=["oci-net-medium", "oci-net-large"],
        sort_order=1,
        tags=["dev"],
    ),
    ConfigOption(
        id="oci-net-medium",
        domain="network",
        category="ip_pool",
        provider_name="oci",
        name="medium_vcn",
        display_name="Standard VCN (/20)",
        description="4094 addresses for production",
        detail="A /20 spoke VCN for standard production environments.",
        icon="network",
        implications=["4094 usable IPs", "Internet + NAT gateways", "Standard production size"],
        config_values={"vcn_cidr": "10.0.0.0/20", "dns_label": "env",
                        "enable_internet_gateway": True, "enable_nat_gateway": True},
        conflicts_with=["oci-net-small", "oci-net-large"],
        sort_order=2,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="oci-net-large",
        domain="network",
        category="ip_pool",
        provider_name="oci",
        name="large_vcn",
        display_name="Large VCN (/16)",
        description="65534 addresses for large-scale workloads",
        detail="A /16 spoke VCN for large environments.",
        icon="network",
        implications=["65534 usable IPs", "Maximum recommended size", "Plan subnetting carefully"],
        config_values={"vcn_cidr": "10.0.0.0/16", "dns_label": "env",
                        "enable_internet_gateway": True, "enable_nat_gateway": True},
        conflicts_with=["oci-net-small", "oci-net-medium"],
        sort_order=3,
        tags=["enterprise"],
    ),
    # Security
    ConfigOption(
        id="oci-sec-vault",
        domain="security",
        category="encryption",
        provider_name="oci",
        name="vault",
        display_name="OCI Vault",
        description="Customer-managed encryption keys",
        detail="Creates an OCI Vault for managing encryption keys for "
        "block volumes, object storage, and databases.",
        icon="lock",
        implications=["HSM-backed keys available", "Automatic rotation", "Vault per environment"],
        config_values={"enable_vault": True, "vault_name": ""},
        sort_order=5,
        tags=["enterprise"],
    ),
    # IAM
    ConfigOption(
        id="oci-iam-policy-preset",
        domain="iam",
        category="acl",
        provider_name="oci",
        name="policy_preset",
        display_name="Compartment Policies",
        description="Standard manage/inspect policies",
        detail="Creates OCI IAM policies granting manage access to operators "
        "and inspect access to viewers in this compartment.",
        icon="lock",
        implications=["Compartment-scoped", "Inherited by children", "OCI policy syntax"],
        config_values={
            "compartment_policies": [
                {"name": "env-admin-policy",
                 "statements": ["Allow group env-admins to manage all-resources in compartment env"]},
                {"name": "env-viewer-policy",
                 "statements": ["Allow group env-viewers to inspect all-resources in compartment env"]},
            ],
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
    ),
    ConfigOption(
        id="oci-iam-instance-principal",
        domain="iam",
        category="acl",
        provider_name="oci",
        name="instance_principal",
        display_name="Instance Principal",
        description="Keyless auth for compute instances",
        detail="Creates a dynamic group for instance principals, allowing "
        "compute instances to authenticate to OCI services without API keys.",
        icon="lock",
        implications=["No API keys on instances", "Dynamic group matching", "OKE pod identity"],
        config_values={
            "instance_principals": [
                {"name": "env-instances", "matching_rules": ["ANY {instance.compartment.id = 'env'}"]},
            ],
        },
        sort_order=2,
        tags=["standard"],
    ),
    # Monitoring
    ConfigOption(
        id="oci-mon-budget",
        domain="monitoring",
        category="budget",
        provider_name="oci",
        name="budget",
        display_name="Budget Alert ($500)",
        description="Compartment budget with email alarm",
        detail="Sets a monthly budget for this compartment with an "
        "alarm topic sending email notifications at threshold.",
        icon="dollar",
        implications=["Compartment-scoped", "Email notification", "Forecast-based alerting"],
        config_values={
            "budget_amount": 500,
            "alarm_topic": {"enabled": True, "name": "env-alerts", "subscription_email": ""},
        },
        sort_order=1,
        is_default=True,
        tags=["standard"],
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


def get_option_catalog(provider_name: str, domain: str) -> list[ConfigOption]:
    """Return all options for a provider + domain, sorted by sort_order."""
    key = f"{provider_name}:{domain}"
    options = _BY_PROVIDER_DOMAIN.get(key, [])
    return sorted(options, key=lambda o: o.sort_order)


def get_option_categories(provider_name: str, domain: str) -> list[CategoryInfo]:
    """Return categories for a domain, filtered to only those with options for this provider."""
    all_cats = _CATEGORIES_BY_DOMAIN.get(domain, [])
    options = get_option_catalog(provider_name, domain)
    used_cats = {o.category for o in options}
    return [c for c in all_cats if c.name in used_cats]


def get_option_by_id(option_id: str) -> ConfigOption | None:
    """Look up a single option by its ID."""
    return _BY_ID.get(option_id)


def validate_selections(option_ids: list[str]) -> list[str]:
    """Validate a set of selected option IDs, returning conflict warnings."""
    warnings: list[str] = []
    selected = {oid: _BY_ID[oid] for oid in option_ids if oid in _BY_ID}

    for oid, opt in selected.items():
        for conflict_id in opt.conflicts_with:
            if conflict_id in selected:
                conflict = selected[conflict_id]
                warnings.append(
                    f'"{opt.display_name}" conflicts with "{conflict.display_name}"'
                )

        for req_id in opt.requires:
            if req_id not in selected:
                req = _BY_ID.get(req_id)
                req_name = req.display_name if req else req_id
                warnings.append(
                    f'"{opt.display_name}" requires "{req_name}" which is not selected'
                )

    # Deduplicate symmetric conflict warnings
    seen: set[str] = set()
    unique: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique
