"""
Overview: Semantic type registry — single source of truth for all abstract resource types,
    categories, relationships, property schemas, providers, and provider resource mappings.
Architecture: Core definitions that seed the database (Section 5)
Dependencies: dataclasses
Concepts: Semantic types normalize provider-specific resources into a unified model.
    Categories group types. Relationships define how types connect. Providers represent
    infrastructure platforms. ProviderResourceMappings link provider API types to semantic types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PropertyDataType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    OS_IMAGE = "os_image"


# ---------------------------------------------------------------------------
# Dataclass definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyDef:
    """A single property within a semantic type's schema."""

    name: str
    display_name: str
    data_type: PropertyDataType
    required: bool = False
    default_value: str | None = None
    unit: str | None = None
    description: str = ""
    allowed_values: list[str] | None = None


@dataclass(frozen=True)
class SemanticCategoryDef:
    """A top-level grouping of semantic types (Compute, Network, etc.)."""

    name: str
    display_name: str
    description: str
    icon: str
    sort_order: int = 0
    is_infrastructure: bool = True


@dataclass(frozen=True)
class SemanticTypeDef:
    """An abstract resource type (VirtualMachine, Subnet, etc.)."""

    name: str
    display_name: str
    category: str  # References SemanticCategoryDef.name
    description: str
    icon: str
    is_abstract: bool = False
    parent_type: str | None = None  # References another SemanticTypeDef.name
    properties: list[PropertyDef] = field(default_factory=list)
    allowed_relationship_kinds: list[str] = field(default_factory=list)
    sort_order: int = 0


@dataclass(frozen=True)
class RelationshipKindDef:
    """A kind of relationship between semantic types (contains, connects_to, etc.)."""

    name: str
    display_name: str
    description: str
    inverse_name: str


@dataclass(frozen=True)
class ProviderDef:
    """Defines an infrastructure provider (Proxmox, AWS, Azure, etc.)."""

    name: str
    display_name: str
    description: str
    icon: str
    provider_type: str  # "on_prem" or "cloud"
    website_url: str
    documentation_url: str


@dataclass(frozen=True)
class ProviderResourceMappingDef:
    """Maps a provider resource type to a semantic type (used by MappingEngine)."""

    provider_name: str
    api_type: str
    semantic_type_name: str  # References SemanticTypeDef.name
    display_name: str = ""


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

CATEGORIES: list[SemanticCategoryDef] = [
    SemanticCategoryDef(
        name="compute",
        display_name="Compute",
        description="Virtual machines, containers, serverless functions, and bare-metal servers",
        icon="server",
        sort_order=1,
    ),
    SemanticCategoryDef(
        name="network",
        display_name="Network",
        description="Virtual networks, subnets, load balancers, DNS, and connectivity",
        icon="globe",
        sort_order=2,
    ),
    SemanticCategoryDef(
        name="storage",
        display_name="Storage",
        description="Block, object, and file storage, plus backups",
        icon="hard-drive",
        sort_order=3,
    ),
    SemanticCategoryDef(
        name="database",
        display_name="Database",
        description="Relational, NoSQL, cache, and data warehouse services",
        icon="database",
        sort_order=4,
    ),
    SemanticCategoryDef(
        name="security",
        display_name="Security",
        description="Security groups, ACLs, IAM roles/policies, certificates, and secrets",
        icon="shield",
        sort_order=5,
    ),
    SemanticCategoryDef(
        name="monitoring",
        display_name="Monitoring",
        description="Alert rules, dashboards, log groups, and metrics",
        icon="activity",
        sort_order=6,
        is_infrastructure=False,
    ),
    SemanticCategoryDef(
        name="application",
        display_name="Application",
        description="Applications, services, endpoints, and message queues",
        icon="layers",
        sort_order=7,
        is_infrastructure=False,
    ),
    SemanticCategoryDef(
        name="services",
        display_name="Services",
        description="Business and managed services — the bridge between infrastructure assets and service delivery",
        icon="briefcase",
        sort_order=8,
        is_infrastructure=False,
    ),
    SemanticCategoryDef(
        name="tenancy",
        display_name="Tenancy",
        description="Cloud tenancy constructs — accounts, subscriptions, compartments, regions",
        icon="building",
        sort_order=9,
    ),
]


# ---------------------------------------------------------------------------
# Relationship kinds
# ---------------------------------------------------------------------------

RELATIONSHIP_KINDS: list[RelationshipKindDef] = [
    RelationshipKindDef(
        name="contains",
        display_name="Contains",
        description="Parent resource contains a child resource (e.g., VNet contains Subnet)",
        inverse_name="contained_by",
    ),
    RelationshipKindDef(
        name="connects_to",
        display_name="Connects To",
        description="Resource has a network or logical connection to another",
        inverse_name="connected_from",
    ),
    RelationshipKindDef(
        name="depends_on",
        display_name="Depends On",
        description="Resource depends on another to function",
        inverse_name="depended_on_by",
    ),
    RelationshipKindDef(
        name="attached_to",
        display_name="Attached To",
        description="Resource is attached to another (e.g., volume to VM)",
        inverse_name="has_attachment",
    ),
    RelationshipKindDef(
        name="routes_to",
        display_name="Routes To",
        description="Network routing relationship between resources",
        inverse_name="routed_from",
    ),
    RelationshipKindDef(
        name="secures",
        display_name="Secures",
        description="Security resource protects or controls access to another",
        inverse_name="secured_by",
    ),
    RelationshipKindDef(
        name="monitors",
        display_name="Monitors",
        description="Monitoring resource observes another resource",
        inverse_name="monitored_by",
    ),
    RelationshipKindDef(
        name="backs_up",
        display_name="Backs Up",
        description="Backup resource protects data of another resource",
        inverse_name="backed_up_by",
    ),
    RelationshipKindDef(
        name="hosts_in",
        display_name="Hosts In",
        description="Tenancy or region hosts compartments and resources",
        inverse_name="hosted_by",
    ),
    RelationshipKindDef(
        name="peers_with",
        display_name="Peers With",
        description="Cross-region or cross-VCN peering (symmetric)",
        inverse_name="peers_with",
    ),
    RelationshipKindDef(
        name="allocates_from",
        display_name="Allocates From",
        description="Subnet or VCN allocates address space from a pool",
        inverse_name="allocated_to",
    ),
]


# ---------------------------------------------------------------------------
# Semantic types — organized by category
# ---------------------------------------------------------------------------

SEMANTIC_TYPES: list[SemanticTypeDef] = [
    # ── Compute ───────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="VirtualMachine",
        display_name="Virtual Machine",
        category="compute",
        description="A virtual compute instance running an operating system",
        icon="monitor",
        properties=[
            PropertyDef(
                "cpu_count", "CPU Count", PropertyDataType.INTEGER, required=True, unit="vCPU"
            ),
            PropertyDef("memory_gb", "Memory", PropertyDataType.FLOAT, required=True, unit="GB"),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef(
                "os_image",
                "OS Image",
                PropertyDataType.OS_IMAGE,
                required=True,
                description="Operating system image from the catalog",
            ),
            PropertyDef("availability_zone", "Availability Zone", PropertyDataType.STRING),
            PropertyDef("public_ip", "Public IP", PropertyDataType.STRING),
            PropertyDef("private_ip", "Private IP", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=[
            "contains",
            "connects_to",
            "depends_on",
            "attached_to",
            "secured_by",
            "monitored_by",
        ],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="Container",
        display_name="Container",
        category="compute",
        description="A containerized workload (Docker, LXC, or managed container service)",
        icon="box",
        properties=[
            PropertyDef("image", "Image", PropertyDataType.STRING, required=True),
            PropertyDef("cpu_limit", "CPU Limit", PropertyDataType.FLOAT, unit="cores"),
            PropertyDef("memory_limit_mb", "Memory Limit", PropertyDataType.INTEGER, unit="MB"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
            PropertyDef("replicas", "Replicas", PropertyDataType.INTEGER, default_value="1"),
            PropertyDef("port_mappings", "Port Mappings", PropertyDataType.JSON),
        ],
        allowed_relationship_kinds=[
            "contains",
            "connects_to",
            "depends_on",
            "secured_by",
            "monitored_by",
        ],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="ServerlessFunction",
        display_name="Serverless Function",
        category="compute",
        description="An event-driven serverless compute function",
        icon="zap",
        properties=[
            PropertyDef(
                "runtime",
                "Runtime",
                PropertyDataType.STRING,
                required=True,
                description="python3.12, nodejs20, etc.",
            ),
            PropertyDef("memory_mb", "Memory", PropertyDataType.INTEGER, required=True, unit="MB"),
            PropertyDef(
                "timeout_seconds", "Timeout", PropertyDataType.INTEGER, unit="s", default_value="30"
            ),
            PropertyDef("handler", "Handler", PropertyDataType.STRING),
            PropertyDef("environment_variables", "Environment Variables", PropertyDataType.JSON),
        ],
        allowed_relationship_kinds=["connects_to", "depends_on", "secured_by", "monitored_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="BareMetalServer",
        display_name="Bare Metal Server",
        category="compute",
        description="A dedicated physical server without virtualization",
        icon="cpu",
        properties=[
            PropertyDef(
                "cpu_count", "CPU Count", PropertyDataType.INTEGER, required=True, unit="cores"
            ),
            PropertyDef("memory_gb", "Memory", PropertyDataType.FLOAT, required=True, unit="GB"),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("os_type", "OS Type", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
            PropertyDef("rack_location", "Rack Location", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=[
            "contains",
            "connects_to",
            "attached_to",
            "secured_by",
            "monitored_by",
        ],
        sort_order=4,
    ),
    # ── Network ───────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="VirtualNetwork",
        display_name="Virtual Network",
        category="network",
        description="A virtual network (VPC, VNet, VCN, Bridge) that isolates resources",
        icon="cloud",
        properties=[
            PropertyDef("cidr_block", "CIDR Block", PropertyDataType.STRING, required=True),
            PropertyDef("region", "Region", PropertyDataType.STRING),
            PropertyDef(
                "is_default", "Is Default", PropertyDataType.BOOLEAN, default_value="false"
            ),
            PropertyDef(
                "dns_enabled", "DNS Enabled", PropertyDataType.BOOLEAN, default_value="true"
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "routes_to", "secured_by"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="Subnet",
        display_name="Subnet",
        category="network",
        description="A subdivision of a virtual network with its own CIDR range",
        icon="git-branch",
        properties=[
            PropertyDef("cidr_block", "CIDR Block", PropertyDataType.STRING, required=True),
            PropertyDef("availability_zone", "Availability Zone", PropertyDataType.STRING),
            PropertyDef("is_public", "Is Public", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("gateway_ip", "Gateway IP", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contained_by", "connects_to", "routes_to", "secured_by"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="NetworkInterface",
        display_name="Network Interface",
        category="network",
        description="A network interface card (NIC) attached to a compute resource",
        icon="link",
        properties=[
            PropertyDef("private_ip", "Private IP", PropertyDataType.STRING, required=True),
            PropertyDef("public_ip", "Public IP", PropertyDataType.STRING),
            PropertyDef("mac_address", "MAC Address", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["attached_to", "contained_by", "secured_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="LoadBalancer",
        display_name="Load Balancer",
        category="network",
        description="Distributes traffic across multiple compute resources",
        icon="share-2",
        properties=[
            PropertyDef(
                "scheme",
                "Scheme",
                PropertyDataType.STRING,
                description="internet-facing or internal",
            ),
            PropertyDef(
                "protocol", "Protocol", PropertyDataType.STRING, description="HTTP, HTTPS, TCP"
            ),
            PropertyDef("port", "Port", PropertyDataType.INTEGER),
            PropertyDef("health_check_path", "Health Check Path", PropertyDataType.STRING),
            PropertyDef(
                "algorithm",
                "Algorithm",
                PropertyDataType.STRING,
                description="round-robin, least-connections",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["connects_to", "routes_to", "secured_by", "monitored_by"],
        sort_order=4,
    ),
    SemanticTypeDef(
        name="DNS",
        display_name="DNS Zone",
        category="network",
        description="A DNS zone managing domain name records",
        icon="at-sign",
        properties=[
            PropertyDef("domain_name", "Domain Name", PropertyDataType.STRING, required=True),
            PropertyDef(
                "zone_type", "Zone Type", PropertyDataType.STRING, description="public or private"
            ),
            PropertyDef("record_count", "Record Count", PropertyDataType.INTEGER),
        ],
        allowed_relationship_kinds=["connects_to", "routes_to"],
        sort_order=5,
    ),
    SemanticTypeDef(
        name="CDN",
        display_name="CDN Distribution",
        category="network",
        description="Content delivery network distribution for caching and acceleration",
        icon="globe",
        properties=[
            PropertyDef("domain_name", "Domain Name", PropertyDataType.STRING, required=True),
            PropertyDef("origin", "Origin", PropertyDataType.STRING, required=True),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
            PropertyDef("protocol_policy", "Protocol Policy", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["connects_to", "routes_to", "secured_by"],
        sort_order=6,
    ),
    SemanticTypeDef(
        name="VPNGateway",
        display_name="VPN Gateway",
        category="network",
        description="A VPN gateway for secure site-to-site or client connectivity",
        icon="lock",
        properties=[
            PropertyDef(
                "gateway_type",
                "Gateway Type",
                PropertyDataType.STRING,
                description="site-to-site, client",
            ),
            PropertyDef(
                "vpn_protocol",
                "VPN Protocol",
                PropertyDataType.STRING,
                description="IPSec, OpenVPN, WireGuard",
            ),
            PropertyDef("public_ip", "Public IP", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["connects_to", "attached_to", "secured_by"],
        sort_order=7,
    ),
    # ── Storage ───────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="BlockStorage",
        display_name="Block Storage",
        category="storage",
        description="A block storage volume (disk) attachable to compute resources",
        icon="hard-drive",
        properties=[
            PropertyDef("size_gb", "Size", PropertyDataType.FLOAT, required=True, unit="GB"),
            PropertyDef("iops", "IOPS", PropertyDataType.INTEGER),
            PropertyDef("throughput_mbps", "Throughput", PropertyDataType.INTEGER, unit="MB/s"),
            PropertyDef(
                "volume_type", "Volume Type", PropertyDataType.STRING, description="ssd, hdd, nvme"
            ),
            PropertyDef("encrypted", "Encrypted", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["attached_to", "backed_up_by", "secured_by", "monitored_by"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="ObjectStorage",
        display_name="Object Storage",
        category="storage",
        description="An object storage bucket (S3, Blob, GCS, etc.)",
        icon="archive",
        properties=[
            PropertyDef("bucket_name", "Bucket Name", PropertyDataType.STRING, required=True),
            PropertyDef("region", "Region", PropertyDataType.STRING),
            PropertyDef(
                "versioning_enabled",
                "Versioning Enabled",
                PropertyDataType.BOOLEAN,
                default_value="false",
            ),
            PropertyDef("encryption_type", "Encryption Type", PropertyDataType.STRING),
            PropertyDef(
                "public_access", "Public Access", PropertyDataType.BOOLEAN, default_value="false"
            ),
            PropertyDef("storage_class", "Storage Class", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["secured_by", "backed_up_by", "monitored_by"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="FileStorage",
        display_name="File Storage",
        category="storage",
        description="A managed file storage share (NFS, SMB, etc.)",
        icon="folder",
        properties=[
            PropertyDef("size_gb", "Size", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef(
                "protocol", "Protocol", PropertyDataType.STRING, description="NFS, SMB, CIFS"
            ),
            PropertyDef("mount_target", "Mount Target", PropertyDataType.STRING),
            PropertyDef("encrypted", "Encrypted", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["attached_to", "secured_by", "backed_up_by", "monitored_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="Backup",
        display_name="Backup",
        category="storage",
        description="A backup or snapshot of a resource",
        icon="save",
        properties=[
            PropertyDef(
                "source_resource_type", "Source Type", PropertyDataType.STRING, required=True
            ),
            PropertyDef("source_resource_id", "Source ID", PropertyDataType.STRING),
            PropertyDef("size_gb", "Size", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef(
                "backup_type",
                "Backup Type",
                PropertyDataType.STRING,
                description="full, incremental, snapshot",
            ),
            PropertyDef("retention_days", "Retention Days", PropertyDataType.INTEGER, unit="days"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["backs_up", "secured_by"],
        sort_order=4,
    ),
    # ── Database ──────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="RelationalDatabase",
        display_name="Relational Database",
        category="database",
        description="A managed relational database (PostgreSQL, MySQL, SQL Server, Oracle)",
        icon="database",
        properties=[
            PropertyDef(
                "engine",
                "Engine",
                PropertyDataType.STRING,
                required=True,
                description="postgresql, mysql, mssql, oracle",
            ),
            PropertyDef("engine_version", "Engine Version", PropertyDataType.STRING),
            PropertyDef("instance_class", "Instance Class", PropertyDataType.STRING),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("multi_az", "Multi-AZ", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("encrypted", "Encrypted", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("port", "Port", PropertyDataType.INTEGER),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=[
            "contained_by",
            "connects_to",
            "depends_on",
            "secured_by",
            "backed_up_by",
            "monitored_by",
        ],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="NoSQLDatabase",
        display_name="NoSQL Database",
        category="database",
        description="A managed NoSQL database (MongoDB, DynamoDB, Cosmos DB, etc.)",
        icon="database",
        properties=[
            PropertyDef(
                "engine",
                "Engine",
                PropertyDataType.STRING,
                required=True,
                description="mongodb, dynamodb, cosmosdb",
            ),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("read_capacity", "Read Capacity", PropertyDataType.INTEGER),
            PropertyDef("write_capacity", "Write Capacity", PropertyDataType.INTEGER),
            PropertyDef("replication", "Replication", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=[
            "contained_by",
            "connects_to",
            "depends_on",
            "secured_by",
            "backed_up_by",
            "monitored_by",
        ],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="CacheService",
        display_name="Cache Service",
        category="database",
        description="A managed caching service (Redis, Memcached, Valkey, etc.)",
        icon="zap",
        properties=[
            PropertyDef(
                "engine",
                "Engine",
                PropertyDataType.STRING,
                required=True,
                description="redis, memcached, valkey",
            ),
            PropertyDef("engine_version", "Engine Version", PropertyDataType.STRING),
            PropertyDef("node_type", "Node Type", PropertyDataType.STRING),
            PropertyDef(
                "num_nodes", "Number of Nodes", PropertyDataType.INTEGER, default_value="1"
            ),
            PropertyDef("memory_gb", "Memory", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("port", "Port", PropertyDataType.INTEGER),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=[
            "contained_by",
            "connects_to",
            "depends_on",
            "secured_by",
            "monitored_by",
        ],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="DataWarehouse",
        display_name="Data Warehouse",
        category="database",
        description="A managed data warehouse for analytics (BigQuery, Redshift, Synapse, etc.)",
        icon="bar-chart-2",
        properties=[
            PropertyDef("engine", "Engine", PropertyDataType.STRING, required=True),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("compute_units", "Compute Units", PropertyDataType.INTEGER),
            PropertyDef("encrypted", "Encrypted", PropertyDataType.BOOLEAN, default_value="false"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=[
            "contained_by",
            "connects_to",
            "depends_on",
            "secured_by",
            "monitored_by",
        ],
        sort_order=4,
    ),
    # ── Security ──────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="SecurityGroup",
        display_name="Security Group",
        category="security",
        description="A virtual firewall controlling inbound/outbound traffic rules",
        icon="shield",
        properties=[
            PropertyDef(
                "rules",
                "Rules",
                PropertyDataType.JSON,
                required=True,
                description="Inbound/outbound rule list",
            ),
            PropertyDef("description", "Description", PropertyDataType.STRING),
            PropertyDef(
                "is_default", "Is Default", PropertyDataType.BOOLEAN, default_value="false"
            ),
        ],
        allowed_relationship_kinds=["secures", "contained_by"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="NetworkACL",
        display_name="Network ACL",
        category="security",
        description="A network access control list with numbered allow/deny rules",
        icon="list",
        properties=[
            PropertyDef("rules", "Rules", PropertyDataType.JSON, required=True),
            PropertyDef(
                "is_default", "Is Default", PropertyDataType.BOOLEAN, default_value="false"
            ),
        ],
        allowed_relationship_kinds=["secures", "contained_by"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="IAMRole",
        display_name="IAM Role",
        category="security",
        description="An identity and access management role with trust and permission policies",
        icon="user-check",
        properties=[
            PropertyDef("trust_policy", "Trust Policy", PropertyDataType.JSON),
            PropertyDef(
                "max_session_duration", "Max Session Duration", PropertyDataType.INTEGER, unit="s"
            ),
            PropertyDef("path", "Path", PropertyDataType.STRING, default_value="/"),
            PropertyDef("description", "Description", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["secures", "depends_on"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="IAMPolicy",
        display_name="IAM Policy",
        category="security",
        description="An identity and access management policy document",
        icon="file-text",
        properties=[
            PropertyDef("policy_document", "Policy Document", PropertyDataType.JSON, required=True),
            PropertyDef(
                "policy_type",
                "Policy Type",
                PropertyDataType.STRING,
                description="managed, inline, customer",
            ),
            PropertyDef("description", "Description", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["secures", "attached_to"],
        sort_order=4,
    ),
    SemanticTypeDef(
        name="Certificate",
        display_name="Certificate",
        category="security",
        description="A TLS/SSL certificate for securing communications",
        icon="award",
        properties=[
            PropertyDef("domain_name", "Domain Name", PropertyDataType.STRING, required=True),
            PropertyDef("subject_alternative_names", "SANs", PropertyDataType.JSON),
            PropertyDef("issuer", "Issuer", PropertyDataType.STRING),
            PropertyDef("valid_from", "Valid From", PropertyDataType.STRING),
            PropertyDef("valid_to", "Valid To", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["secures", "attached_to"],
        sort_order=5,
    ),
    SemanticTypeDef(
        name="Secret",
        display_name="Secret",
        category="security",
        description="A managed secret (API key, password, token) stored securely",
        icon="key",
        properties=[
            PropertyDef(
                "secret_type",
                "Secret Type",
                PropertyDataType.STRING,
                description="api-key, password, token, other",
            ),
            PropertyDef(
                "rotation_enabled",
                "Rotation Enabled",
                PropertyDataType.BOOLEAN,
                default_value="false",
            ),
            PropertyDef("rotation_days", "Rotation Days", PropertyDataType.INTEGER, unit="days"),
            PropertyDef("last_rotated", "Last Rotated", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["secures", "depends_on"],
        sort_order=6,
    ),
    SemanticTypeDef(
        name="KeyVault",
        display_name="Key Vault",
        category="security",
        description="A managed key management service for encryption keys and secrets",
        icon="lock",
        properties=[
            PropertyDef(
                "sku", "SKU", PropertyDataType.STRING, description="standard, premium, hsm"
            ),
            PropertyDef(
                "soft_delete_enabled", "Soft Delete", PropertyDataType.BOOLEAN, default_value="true"
            ),
            PropertyDef(
                "purge_protection",
                "Purge Protection",
                PropertyDataType.BOOLEAN,
                default_value="false",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "secures"],
        sort_order=7,
    ),
    # ── Monitoring ────────────────────────────────────────────────────────
    SemanticTypeDef(
        name="AlertRule",
        display_name="Alert Rule",
        category="monitoring",
        description="An alert rule that triggers notifications based on conditions",
        icon="bell",
        properties=[
            PropertyDef("condition", "Condition", PropertyDataType.JSON, required=True),
            PropertyDef(
                "severity",
                "Severity",
                PropertyDataType.STRING,
                required=True,
                description="critical, warning, info",
            ),
            PropertyDef("threshold", "Threshold", PropertyDataType.FLOAT),
            PropertyDef(
                "evaluation_period", "Evaluation Period", PropertyDataType.INTEGER, unit="s"
            ),
            PropertyDef(
                "state",
                "State",
                PropertyDataType.STRING,
                required=True,
                description="enabled, disabled",
            ),
        ],
        allowed_relationship_kinds=["monitors"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="Dashboard",
        display_name="Dashboard",
        category="monitoring",
        description="A monitoring dashboard with widgets and visualizations",
        icon="layout",
        properties=[
            PropertyDef("widgets", "Widgets", PropertyDataType.JSON),
            PropertyDef("refresh_interval", "Refresh Interval", PropertyDataType.INTEGER, unit="s"),
            PropertyDef("description", "Description", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["monitors"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="LogGroup",
        display_name="Log Group",
        category="monitoring",
        description="A log group or log stream collecting application/infrastructure logs",
        icon="file-text",
        properties=[
            PropertyDef("retention_days", "Retention Days", PropertyDataType.INTEGER, unit="days"),
            PropertyDef("storage_gb", "Storage", PropertyDataType.FLOAT, unit="GB"),
            PropertyDef("encrypted", "Encrypted", PropertyDataType.BOOLEAN, default_value="false"),
        ],
        allowed_relationship_kinds=["monitors", "contained_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="Metric",
        display_name="Metric",
        category="monitoring",
        description="A custom or system metric for resource monitoring",
        icon="trending-up",
        properties=[
            PropertyDef("namespace", "Namespace", PropertyDataType.STRING, required=True),
            PropertyDef("metric_name", "Metric Name", PropertyDataType.STRING, required=True),
            PropertyDef("unit", "Unit", PropertyDataType.STRING),
            PropertyDef(
                "statistic",
                "Statistic",
                PropertyDataType.STRING,
                description="avg, sum, min, max, count",
            ),
            PropertyDef("period", "Period", PropertyDataType.INTEGER, unit="s"),
        ],
        allowed_relationship_kinds=["monitors"],
        sort_order=4,
    ),
    # ── Application ───────────────────────────────────────────────────────
    SemanticTypeDef(
        name="Application",
        display_name="Application",
        category="application",
        description="A deployed application or app service",
        icon="package",
        properties=[
            PropertyDef("runtime", "Runtime", PropertyDataType.STRING),
            PropertyDef("framework", "Framework", PropertyDataType.STRING),
            PropertyDef("version", "Version", PropertyDataType.STRING),
            PropertyDef("replicas", "Replicas", PropertyDataType.INTEGER, default_value="1"),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
            PropertyDef("url", "URL", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=[
            "contains",
            "connects_to",
            "depends_on",
            "secured_by",
            "monitored_by",
        ],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="Service",
        display_name="Service",
        category="application",
        description="A microservice or service component within an application",
        icon="server",
        properties=[
            PropertyDef(
                "service_type",
                "Service Type",
                PropertyDataType.STRING,
                description="web, api, worker, cron",
            ),
            PropertyDef("port", "Port", PropertyDataType.INTEGER),
            PropertyDef(
                "protocol", "Protocol", PropertyDataType.STRING, description="HTTP, gRPC, TCP"
            ),
            PropertyDef("health_endpoint", "Health Endpoint", PropertyDataType.STRING),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=[
            "contained_by",
            "connects_to",
            "depends_on",
            "secured_by",
            "monitored_by",
        ],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="Endpoint",
        display_name="Endpoint",
        category="application",
        description="An API endpoint or service entry point",
        icon="terminal",
        properties=[
            PropertyDef("url", "URL", PropertyDataType.STRING, required=True),
            PropertyDef(
                "method", "Method", PropertyDataType.STRING, description="GET, POST, PUT, DELETE"
            ),
            PropertyDef(
                "protocol", "Protocol", PropertyDataType.STRING, description="REST, GraphQL, gRPC"
            ),
            PropertyDef("authentication", "Authentication", PropertyDataType.STRING),
            PropertyDef("rate_limit", "Rate Limit", PropertyDataType.INTEGER, unit="req/s"),
        ],
        allowed_relationship_kinds=["contained_by", "connects_to", "secured_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="Queue",
        display_name="Message Queue",
        category="application",
        description="A message queue or event stream (SQS, RabbitMQ, Kafka, etc.)",
        icon="inbox",
        properties=[
            PropertyDef(
                "engine",
                "Engine",
                PropertyDataType.STRING,
                required=True,
                description="sqs, rabbitmq, kafka, servicebus",
            ),
            PropertyDef(
                "queue_type",
                "Queue Type",
                PropertyDataType.STRING,
                description="standard, fifo, topic",
            ),
            PropertyDef(
                "max_message_size_kb", "Max Message Size", PropertyDataType.INTEGER, unit="KB"
            ),
            PropertyDef("retention_seconds", "Retention", PropertyDataType.INTEGER, unit="s"),
            PropertyDef(
                "dead_letter_queue",
                "Dead Letter Queue",
                PropertyDataType.BOOLEAN,
                default_value="false",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["connects_to", "depends_on", "secured_by", "monitored_by"],
        sort_order=4,
    ),
]


# ---------------------------------------------------------------------------
# Services category — bridges infrastructure assets and service delivery
# ---------------------------------------------------------------------------

SERVICES_TYPES: list[SemanticTypeDef] = [
    SemanticTypeDef(
        name="ServiceCluster",
        display_name="Service Cluster",
        category="services",
        description="A logical group of resources forming a service unit with defined role slots",
        icon="layers",
        properties=[
            PropertyDef(
                "cluster_type",
                "Cluster Type",
                PropertyDataType.STRING,
                required=True,
                description="service_cluster or service_group",
            ),
            PropertyDef(
                "target_size",
                "Target Size",
                PropertyDataType.INTEGER,
                description="Expected number of member CIs",
            ),
            PropertyDef(
                "sla_target",
                "SLA Target",
                PropertyDataType.STRING,
                description="SLA tier or percentage target",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="ServiceGroup",
        display_name="Service Group",
        category="services",
        description="A logical grouping of related services for organizational purposes",
        icon="folder",
        properties=[
            PropertyDef(
                "group_purpose",
                "Group Purpose",
                PropertyDataType.STRING,
                description="The purpose or function of this service group",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="ManagedService",
        display_name="Managed Service",
        category="services",
        description="A fully managed service delivered to tenants (e.g., Managed Firewall, Managed Backup)",
        icon="briefcase",
        properties=[
            PropertyDef(
                "service_category",
                "Service Category",
                PropertyDataType.STRING,
                required=True,
                description="security, infrastructure, application, data, platform",
            ),
            PropertyDef(
                "operating_model",
                "Operating Model",
                PropertyDataType.STRING,
                description="regional, global, follow_the_sun",
            ),
            PropertyDef(
                "coverage_model",
                "Coverage Model",
                PropertyDataType.STRING,
                description="business_hours, extended, 24x7",
            ),
            PropertyDef(
                "sla_tier",
                "SLA Tier",
                PropertyDataType.STRING,
                description="bronze, silver, gold, platinum",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="SecurityService",
        display_name="Security Service",
        category="services",
        description="Security-focused service (SIEM, vulnerability management, WAF, SOC)",
        icon="shield",
        properties=[
            PropertyDef(
                "security_domain",
                "Security Domain",
                PropertyDataType.STRING,
                required=True,
                description="perimeter, endpoint, identity, data, monitoring, compliance",
            ),
            PropertyDef(
                "compliance_frameworks",
                "Compliance Frameworks",
                PropertyDataType.STRING,
                description="Comma-separated: ISO27001, SOC2, GDPR, PCI-DSS",
            ),
            PropertyDef(
                "coverage_model",
                "Coverage Model",
                PropertyDataType.STRING,
                description="business_hours, extended, 24x7",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "secures", "monitored_by"],
        sort_order=4,
    ),
    SemanticTypeDef(
        name="ConsultingService",
        display_name="Consulting Service",
        category="services",
        description="Advisory and consulting service (architecture review, migration planning, optimization)",
        icon="users",
        properties=[
            PropertyDef(
                "consulting_type",
                "Consulting Type",
                PropertyDataType.STRING,
                required=True,
                description="architecture, migration, optimization, training, assessment",
            ),
            PropertyDef(
                "delivery_model",
                "Delivery Model",
                PropertyDataType.STRING,
                description="project, retainer, on_demand",
            ),
            PropertyDef(
                "measuring_unit",
                "Measuring Unit",
                PropertyDataType.STRING,
                description="hour, day, project, engagement",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on"],
        sort_order=5,
    ),
    SemanticTypeDef(
        name="SupportService",
        display_name="Support Service",
        category="services",
        description="Operational support service (helpdesk, L1/L2/L3, incident response, on-call)",
        icon="headphones",
        properties=[
            PropertyDef(
                "support_tier",
                "Support Tier",
                PropertyDataType.STRING,
                required=True,
                description="l1, l2, l3, specialist",
            ),
            PropertyDef(
                "coverage_model",
                "Coverage Model",
                PropertyDataType.STRING,
                description="business_hours, extended, 24x7",
            ),
            PropertyDef(
                "response_time_minutes",
                "Response Time",
                PropertyDataType.INTEGER,
                unit="min",
                description="Target initial response time",
            ),
            PropertyDef(
                "resolution_time_hours",
                "Resolution Time",
                PropertyDataType.INTEGER,
                unit="h",
                description="Target resolution time",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=6,
    ),
    SemanticTypeDef(
        name="IncidentManagement",
        display_name="Incident Management",
        category="services",
        description="Incident management process service (detection, triage, resolution, post-mortem)",
        icon="alert-triangle",
        properties=[
            PropertyDef(
                "process_scope",
                "Process Scope",
                PropertyDataType.STRING,
                required=True,
                description="detection, triage, resolution, post_mortem, full_lifecycle",
            ),
            PropertyDef(
                "severity_levels",
                "Severity Levels",
                PropertyDataType.STRING,
                description="Comma-separated: P1, P2, P3, P4",
            ),
            PropertyDef(
                "escalation_policy",
                "Escalation Policy",
                PropertyDataType.STRING,
                description="automatic, manual, hybrid",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=7,
    ),
    SemanticTypeDef(
        name="PlatformService",
        display_name="Platform Service",
        category="services",
        description="Platform-level service (CI/CD, container orchestration, API gateway, service mesh)",
        icon="grid",
        properties=[
            PropertyDef(
                "platform_type",
                "Platform Type",
                PropertyDataType.STRING,
                required=True,
                description="cicd, container_platform, api_gateway, service_mesh, observability",
            ),
            PropertyDef(
                "target_environment",
                "Target Environment",
                PropertyDataType.STRING,
                description="development, staging, production, all",
            ),
            PropertyDef("state", "State", PropertyDataType.STRING, required=True),
        ],
        allowed_relationship_kinds=["contains", "connects_to", "depends_on", "monitored_by"],
        sort_order=8,
    ),
]

# Merge services types into the main list
SEMANTIC_TYPES = SEMANTIC_TYPES + SERVICES_TYPES

# ── Tenancy ──────────────────────────────────────────────────────────────

TENANCY_TYPES: list[SemanticTypeDef] = [
    SemanticTypeDef(
        name="CloudTenancy",
        display_name="Cloud Tenancy",
        category="tenancy",
        description="Abstract root tenancy — maps to OCI Tenancy, Azure Subscription, AWS Account, GCP Project",
        icon="building",
        is_abstract=True,
        properties=[
            PropertyDef("tenancy_name", "Tenancy Name", PropertyDataType.STRING, required=True),
            PropertyDef("tenancy_id", "External Tenancy ID", PropertyDataType.STRING),
            PropertyDef(
                "status",
                "Status",
                PropertyDataType.STRING,
                default_value="active",
                allowed_values=["active", "suspended", "closed"],
            ),
            PropertyDef("home_region", "Home Region", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["contains", "hosts_in"],
        sort_order=1,
    ),
    SemanticTypeDef(
        name="CloudCompartment",
        display_name="Cloud Compartment",
        category="tenancy",
        description="Abstract compartment — maps to OCI Compartment, Azure Resource Group, AWS OU, GCP Folder",
        icon="folder",
        is_abstract=True,
        properties=[
            PropertyDef("compartment_name", "Compartment Name", PropertyDataType.STRING, required=True),
            PropertyDef("compartment_id", "External Compartment ID", PropertyDataType.STRING),
            PropertyDef("parent_compartment_id", "Parent Compartment ID", PropertyDataType.STRING),
            PropertyDef("description", "Description", PropertyDataType.STRING),
            PropertyDef("tags", "Tags", PropertyDataType.JSON),
        ],
        allowed_relationship_kinds=["contains", "contained_by", "hosts_in", "hosted_by"],
        sort_order=2,
    ),
    SemanticTypeDef(
        name="CloudRegion",
        display_name="Cloud Region",
        category="tenancy",
        description="Cloud provider region — maps to OCI Region, Azure Region, AWS Region, GCP Region",
        icon="map-pin",
        properties=[
            PropertyDef("region_name", "Region Name", PropertyDataType.STRING, required=True),
            PropertyDef(
                "region_code",
                "Region Code",
                PropertyDataType.STRING,
                required=True,
                description="Provider-specific code (e.g., eu-frankfurt-1, westeurope, us-east-1)",
            ),
            PropertyDef(
                "availability_domains",
                "Availability Domains",
                PropertyDataType.INTEGER,
                default_value="3",
            ),
            PropertyDef("geographic_area", "Geographic Area", PropertyDataType.STRING),
        ],
        allowed_relationship_kinds=["contains", "peers_with", "hosted_by"],
        sort_order=3,
    ),
    SemanticTypeDef(
        name="AddressPool",
        display_name="Address Pool",
        category="tenancy",
        description="IPAM address pool — a CIDR block reserved for tenant allocation",
        icon="grid",
        properties=[
            PropertyDef(
                "cidr",
                "CIDR Block",
                PropertyDataType.STRING,
                required=True,
                description="CIDR notation (e.g., 10.100.0.0/12)",
            ),
            PropertyDef(
                "ip_version",
                "IP Version",
                PropertyDataType.INTEGER,
                default_value="4",
                allowed_values=["4", "6"],
            ),
            PropertyDef(
                "pool_type",
                "Pool Type",
                PropertyDataType.STRING,
                default_value="tenant",
                allowed_values=["provider_reserved", "tenant", "shared"],
            ),
        ],
        allowed_relationship_kinds=["contained_by", "allocates_from"],
        sort_order=4,
    ),
]

SEMANTIC_TYPES = SEMANTIC_TYPES + TENANCY_TYPES


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

PROVIDERS: list[ProviderDef] = [
    ProviderDef(
        name="proxmox",
        display_name="Proxmox VE",
        description="Open-source virtualization platform with KVM and LXC support",
        icon="server",
        provider_type="on_prem",
        website_url="https://www.proxmox.com/",
        documentation_url="https://pve.proxmox.com/pve-docs/",
    ),
    ProviderDef(
        name="aws",
        display_name="Amazon Web Services",
        description="Comprehensive cloud computing platform by Amazon",
        icon="cloud",
        provider_type="cloud",
        website_url="https://aws.amazon.com/",
        documentation_url="https://docs.aws.amazon.com/",
    ),
    ProviderDef(
        name="azure",
        display_name="Microsoft Azure",
        description="Cloud computing service by Microsoft",
        icon="cloud",
        provider_type="cloud",
        website_url="https://azure.microsoft.com/",
        documentation_url="https://docs.microsoft.com/azure/",
    ),
    ProviderDef(
        name="gcp",
        display_name="Google Cloud Platform",
        description="Cloud computing services by Google",
        icon="cloud",
        provider_type="cloud",
        website_url="https://cloud.google.com/",
        documentation_url="https://cloud.google.com/docs/",
    ),
    ProviderDef(
        name="oci",
        display_name="Oracle Cloud Infrastructure",
        description="Cloud computing service by Oracle Corporation",
        icon="cloud",
        provider_type="cloud",
        website_url="https://www.oracle.com/cloud/",
        documentation_url="https://docs.oracle.com/en-us/iaas/",
    ),
]


# ---------------------------------------------------------------------------
# Provider resource mappings (merged from PRT + TypeMapping)
# ---------------------------------------------------------------------------

PROVIDER_RESOURCE_MAPPINGS: list[ProviderResourceMappingDef] = [
    # ── Proxmox ───────────────────────────────────────────────────────────
    ProviderResourceMappingDef("proxmox", "qemu", "VirtualMachine", "Proxmox QEMU/KVM VM"),
    ProviderResourceMappingDef("proxmox", "lxc", "Container", "Proxmox LXC container"),
    ProviderResourceMappingDef("proxmox", "node", "BareMetalServer", "Proxmox cluster node"),
    ProviderResourceMappingDef("proxmox", "linux-bridge", "VirtualNetwork", "Proxmox Linux bridge"),
    ProviderResourceMappingDef("proxmox", "ovs-bridge", "VirtualNetwork", "Proxmox OVS bridge"),
    ProviderResourceMappingDef("proxmox", "sdn-vnet", "VirtualNetwork", "Proxmox SDN VNet"),
    ProviderResourceMappingDef("proxmox", "sdn-subnet", "Subnet", "Proxmox SDN subnet"),
    ProviderResourceMappingDef("proxmox", "storage-lvm", "BlockStorage", "Proxmox LVM storage"),
    ProviderResourceMappingDef("proxmox", "storage-lvmthin", "BlockStorage", "Proxmox LVM-Thin storage"),
    ProviderResourceMappingDef("proxmox", "storage-zfs", "BlockStorage", "Proxmox ZFS storage"),
    ProviderResourceMappingDef("proxmox", "storage-ceph", "BlockStorage", "Proxmox Ceph RBD storage"),
    ProviderResourceMappingDef("proxmox", "storage-nfs", "FileStorage", "Proxmox NFS storage"),
    ProviderResourceMappingDef("proxmox", "storage-cephfs", "FileStorage", "Proxmox CephFS storage"),
    ProviderResourceMappingDef("proxmox", "storage-pbs", "Backup", "Proxmox Backup Server"),
    ProviderResourceMappingDef("proxmox", "firewall-group", "SecurityGroup", "Proxmox firewall security group"),
    ProviderResourceMappingDef("proxmox", "ha-group", "Application", "Proxmox HA group"),
    # ── AWS ───────────────────────────────────────────────────────────────
    ProviderResourceMappingDef("aws", "ec2:instance", "VirtualMachine", "AWS EC2 Instance"),
    ProviderResourceMappingDef("aws", "ecs:task", "Container", "AWS ECS Task"),
    ProviderResourceMappingDef("aws", "ecs:service", "Service", "AWS ECS Service"),
    ProviderResourceMappingDef("aws", "lambda:function", "ServerlessFunction", "AWS Lambda Function"),
    ProviderResourceMappingDef("aws", "ec2:vpc", "VirtualNetwork", "AWS VPC"),
    ProviderResourceMappingDef("aws", "ec2:subnet", "Subnet", "AWS VPC Subnet"),
    ProviderResourceMappingDef("aws", "ec2:network-interface", "NetworkInterface", "AWS ENI"),
    ProviderResourceMappingDef("aws", "elasticloadbalancing:loadbalancer", "LoadBalancer", "AWS ELB/ALB/NLB"),
    ProviderResourceMappingDef("aws", "route53:hostedzone", "DNS", "AWS Route 53 Hosted Zone"),
    ProviderResourceMappingDef("aws", "cloudfront:distribution", "CDN", "AWS CloudFront Distribution"),
    ProviderResourceMappingDef("aws", "ec2:vpn-gateway", "VPNGateway", "AWS VPN Gateway"),
    ProviderResourceMappingDef("aws", "ebs:volume", "BlockStorage", "AWS EBS Volume"),
    ProviderResourceMappingDef("aws", "s3:bucket", "ObjectStorage", "AWS S3 Bucket"),
    ProviderResourceMappingDef("aws", "efs:filesystem", "FileStorage", "AWS EFS File System"),
    ProviderResourceMappingDef("aws", "backup:recovery-point", "Backup", "AWS Backup Recovery Point"),
    ProviderResourceMappingDef("aws", "rds:db", "RelationalDatabase", "AWS RDS Instance"),
    ProviderResourceMappingDef("aws", "dynamodb:table", "NoSQLDatabase", "AWS DynamoDB Table"),
    ProviderResourceMappingDef("aws", "elasticache:cluster", "CacheService", "AWS ElastiCache Cluster"),
    ProviderResourceMappingDef("aws", "redshift:cluster", "DataWarehouse", "AWS Redshift Cluster"),
    ProviderResourceMappingDef("aws", "ec2:security-group", "SecurityGroup", "AWS Security Group"),
    ProviderResourceMappingDef("aws", "ec2:network-acl", "NetworkACL", "AWS Network ACL"),
    ProviderResourceMappingDef("aws", "iam:role", "IAMRole", "AWS IAM Role"),
    ProviderResourceMappingDef("aws", "iam:policy", "IAMPolicy", "AWS IAM Policy"),
    ProviderResourceMappingDef("aws", "acm:certificate", "Certificate", "AWS ACM Certificate"),
    ProviderResourceMappingDef("aws", "secretsmanager:secret", "Secret", "AWS Secrets Manager"),
    ProviderResourceMappingDef("aws", "kms:key", "KeyVault", "AWS KMS Key"),
    ProviderResourceMappingDef("aws", "cloudwatch:alarm", "AlertRule", "AWS CloudWatch Alarm"),
    ProviderResourceMappingDef("aws", "cloudwatch:dashboard", "Dashboard", "AWS CloudWatch Dashboard"),
    ProviderResourceMappingDef("aws", "logs:log-group", "LogGroup", "AWS CloudWatch Log Group"),
    ProviderResourceMappingDef("aws", "cloudwatch:metric", "Metric", "AWS CloudWatch Metric"),
    ProviderResourceMappingDef("aws", "elasticbeanstalk:application", "Application", "AWS Elastic Beanstalk App"),
    ProviderResourceMappingDef("aws", "apigateway:restapi", "Endpoint", "AWS API Gateway"),
    ProviderResourceMappingDef("aws", "sqs:queue", "Queue", "AWS SQS Queue"),
    # ── Azure ─────────────────────────────────────────────────────────────
    ProviderResourceMappingDef("azure", "Microsoft.Compute/virtualMachines", "VirtualMachine", "Azure VM"),
    ProviderResourceMappingDef("azure", "Microsoft.ContainerInstance/containerGroups", "Container", "Azure Container Instance"),
    ProviderResourceMappingDef("azure", "Microsoft.Web/sites", "ServerlessFunction", "Azure Functions"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/virtualNetworks", "VirtualNetwork", "Azure VNet"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/virtualNetworks/subnets", "Subnet", "Azure Subnet"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/networkInterfaces", "NetworkInterface", "Azure NIC"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/loadBalancers", "LoadBalancer", "Azure Load Balancer"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/dnszones", "DNS", "Azure DNS Zone"),
    ProviderResourceMappingDef("azure", "Microsoft.Cdn/profiles", "CDN", "Azure CDN Profile"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/vpnGateways", "VPNGateway", "Azure VPN Gateway"),
    ProviderResourceMappingDef("azure", "Microsoft.Compute/disks", "BlockStorage", "Azure Managed Disk"),
    ProviderResourceMappingDef("azure", "Microsoft.Storage/storageAccounts", "ObjectStorage", "Azure Blob Storage"),
    ProviderResourceMappingDef("azure", "Microsoft.Storage/storageAccounts/fileServices", "FileStorage", "Azure Files"),
    ProviderResourceMappingDef("azure", "Microsoft.RecoveryServices/vaults", "Backup", "Azure Recovery Services"),
    ProviderResourceMappingDef("azure", "Microsoft.Sql/servers/databases", "RelationalDatabase", "Azure SQL Database"),
    ProviderResourceMappingDef("azure", "Microsoft.DocumentDB/databaseAccounts", "NoSQLDatabase", "Azure Cosmos DB"),
    ProviderResourceMappingDef("azure", "Microsoft.Cache/redis", "CacheService", "Azure Cache for Redis"),
    ProviderResourceMappingDef("azure", "Microsoft.Synapse/workspaces", "DataWarehouse", "Azure Synapse Analytics"),
    ProviderResourceMappingDef("azure", "Microsoft.Network/networkSecurityGroups", "SecurityGroup", "Azure NSG"),
    ProviderResourceMappingDef("azure", "Microsoft.Authorization/roleDefinitions", "IAMRole", "Azure Role Definition"),
    ProviderResourceMappingDef("azure", "Microsoft.Authorization/policyDefinitions", "IAMPolicy", "Azure Policy"),
    ProviderResourceMappingDef("azure", "Microsoft.KeyVault/vaults", "KeyVault", "Azure Key Vault"),
    ProviderResourceMappingDef("azure", "Microsoft.Insights/metricAlerts", "AlertRule", "Azure Monitor Alert"),
    ProviderResourceMappingDef("azure", "Microsoft.Portal/dashboards", "Dashboard", "Azure Dashboard"),
    ProviderResourceMappingDef("azure", "Microsoft.Insights/components", "LogGroup", "Azure App Insights"),
    ProviderResourceMappingDef("azure", "Microsoft.ApiManagement/service", "Endpoint", "Azure API Management"),
    ProviderResourceMappingDef("azure", "Microsoft.ServiceBus/namespaces/queues", "Queue", "Azure Service Bus Queue"),
    # ── GCP ───────────────────────────────────────────────────────────────
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/Instance", "VirtualMachine", "GCP Compute Engine"),
    ProviderResourceMappingDef("gcp", "run.googleapis.com/Service", "Container", "GCP Cloud Run Service"),
    ProviderResourceMappingDef("gcp", "cloudfunctions.googleapis.com/Function", "ServerlessFunction", "GCP Cloud Function"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/Network", "VirtualNetwork", "GCP VPC Network"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/Subnetwork", "Subnet", "GCP Subnetwork"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/ForwardingRule", "LoadBalancer", "GCP Load Balancer"),
    ProviderResourceMappingDef("gcp", "dns.googleapis.com/ManagedZone", "DNS", "GCP Cloud DNS"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/VpnGateway", "VPNGateway", "GCP VPN Gateway"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/Disk", "BlockStorage", "GCP Persistent Disk"),
    ProviderResourceMappingDef("gcp", "storage.googleapis.com/Bucket", "ObjectStorage", "GCP Cloud Storage"),
    ProviderResourceMappingDef("gcp", "file.googleapis.com/Instance", "FileStorage", "GCP Filestore"),
    ProviderResourceMappingDef("gcp", "sqladmin.googleapis.com/Instance", "RelationalDatabase", "GCP Cloud SQL"),
    ProviderResourceMappingDef("gcp", "firestore.googleapis.com/Database", "NoSQLDatabase", "GCP Firestore"),
    ProviderResourceMappingDef("gcp", "redis.googleapis.com/Instance", "CacheService", "GCP Memorystore Redis"),
    ProviderResourceMappingDef("gcp", "bigquery.googleapis.com/Dataset", "DataWarehouse", "GCP BigQuery"),
    ProviderResourceMappingDef("gcp", "compute.googleapis.com/Firewall", "SecurityGroup", "GCP Firewall Rule"),
    ProviderResourceMappingDef("gcp", "iam.googleapis.com/Role", "IAMRole", "GCP IAM Role"),
    ProviderResourceMappingDef("gcp", "cloudkms.googleapis.com/KeyRing", "KeyVault", "GCP Cloud KMS"),
    ProviderResourceMappingDef("gcp", "monitoring.googleapis.com/AlertPolicy", "AlertRule", "GCP Monitoring Alert"),
    ProviderResourceMappingDef("gcp", "monitoring.googleapis.com/Dashboard", "Dashboard", "GCP Monitoring Dashboard"),
    ProviderResourceMappingDef("gcp", "logging.googleapis.com/LogBucket", "LogGroup", "GCP Cloud Logging"),
    ProviderResourceMappingDef("gcp", "appengine.googleapis.com/Application", "Application", "GCP App Engine"),
    ProviderResourceMappingDef("gcp", "pubsub.googleapis.com/Topic", "Queue", "GCP Pub/Sub Topic"),
    # ── OCI ───────────────────────────────────────────────────────────────
    ProviderResourceMappingDef("oci", "core/instance", "VirtualMachine", "OCI Compute Instance"),
    ProviderResourceMappingDef("oci", "containerinstances/containerInstance", "Container", "OCI Container Instance"),
    ProviderResourceMappingDef("oci", "functions/function", "ServerlessFunction", "OCI Functions"),
    ProviderResourceMappingDef("oci", "computebaremetal/instance", "BareMetalServer", "OCI Bare Metal"),
    ProviderResourceMappingDef("oci", "core/vcn", "VirtualNetwork", "OCI VCN"),
    ProviderResourceMappingDef("oci", "core/subnet", "Subnet", "OCI Subnet"),
    ProviderResourceMappingDef("oci", "core/vnic", "NetworkInterface", "OCI VNIC"),
    ProviderResourceMappingDef("oci", "loadbalancer/loadbalancer", "LoadBalancer", "OCI Load Balancer"),
    ProviderResourceMappingDef("oci", "dns/zone", "DNS", "OCI DNS Zone"),
    ProviderResourceMappingDef("oci", "core/ipsecconnection", "VPNGateway", "OCI IPSec Connection"),
    ProviderResourceMappingDef("oci", "core/volume", "BlockStorage", "OCI Block Volume"),
    ProviderResourceMappingDef("oci", "objectstorage/bucket", "ObjectStorage", "OCI Object Storage"),
    ProviderResourceMappingDef("oci", "filestorage/filesystem", "FileStorage", "OCI File Storage"),
    ProviderResourceMappingDef("oci", "database/dbsystem", "RelationalDatabase", "OCI DB System"),
    ProviderResourceMappingDef("oci", "nosql/table", "NoSQLDatabase", "OCI NoSQL Table"),
    ProviderResourceMappingDef("oci", "redis/redisCluster", "CacheService", "OCI Cache with Redis"),
    ProviderResourceMappingDef("oci", "core/securitylist", "SecurityGroup", "OCI Security List"),
    ProviderResourceMappingDef("oci", "core/networksecuritygroup", "SecurityGroup", "OCI Network Security Group"),
    ProviderResourceMappingDef("oci", "identity/policy", "IAMPolicy", "OCI IAM Policy"),
    ProviderResourceMappingDef("oci", "vault/vault", "KeyVault", "OCI Vault"),
    ProviderResourceMappingDef("oci", "monitoring/alarm", "AlertRule", "OCI Monitoring Alarm"),
    ProviderResourceMappingDef("oci", "logging/loggroup", "LogGroup", "OCI Logging Log Group"),
    ProviderResourceMappingDef("oci", "streaming/stream", "Queue", "OCI Streaming"),
    # ── Tenancy mappings ──────────────────────────────────────────────────
    ProviderResourceMappingDef("proxmox", "cluster:datacenter", "CloudTenancy", "Proxmox Datacenter"),
    ProviderResourceMappingDef("proxmox", "cluster:pool", "CloudCompartment", "Proxmox Pool"),
    ProviderResourceMappingDef("proxmox", "cluster:node", "CloudRegion", "Proxmox Node"),
    ProviderResourceMappingDef("aws", "organizations:account", "CloudTenancy", "AWS Account"),
    ProviderResourceMappingDef("aws", "organizations:organizational-unit", "CloudCompartment", "AWS Organizational Unit"),
    ProviderResourceMappingDef("azure", "management:subscription", "CloudTenancy", "Azure Subscription"),
    ProviderResourceMappingDef("azure", "resources:resource-group", "CloudCompartment", "Azure Resource Group"),
    ProviderResourceMappingDef("azure", "management:management-group", "CloudCompartment", "Azure Management Group"),
    ProviderResourceMappingDef("gcp", "cloudresourcemanager:project", "CloudTenancy", "GCP Project"),
    ProviderResourceMappingDef("gcp", "cloudresourcemanager:folder", "CloudCompartment", "GCP Folder"),
    ProviderResourceMappingDef("oci", "iam:tenancy", "CloudTenancy", "OCI Tenancy"),
    ProviderResourceMappingDef("oci", "iam:compartment", "CloudCompartment", "OCI Compartment"),
    ProviderResourceMappingDef("oci", "iam:region-subscription", "CloudRegion", "OCI Region Subscription"),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, SemanticCategoryDef] = {c.name: c for c in CATEGORIES}
_TYPE_MAP: dict[str, SemanticTypeDef] = {t.name: t for t in SEMANTIC_TYPES}
_RELATIONSHIP_MAP: dict[str, RelationshipKindDef] = {r.name: r for r in RELATIONSHIP_KINDS}
_PROVIDER_MAP: dict[str, ProviderDef] = {p.name: p for p in PROVIDERS}


def get_category(name: str) -> SemanticCategoryDef | None:
    """Look up a category by name."""
    return _CATEGORY_MAP.get(name)


def get_type(name: str) -> SemanticTypeDef | None:
    """Look up a semantic type by name."""
    return _TYPE_MAP.get(name)


def get_relationship_kind(name: str) -> RelationshipKindDef | None:
    """Look up a relationship kind by name."""
    return _RELATIONSHIP_MAP.get(name)


def get_types_by_category(category_name: str) -> list[SemanticTypeDef]:
    """Get all types belonging to a category."""
    return [t for t in SEMANTIC_TYPES if t.category == category_name]


def get_provider(name: str) -> ProviderDef | None:
    """Look up a provider by name."""
    return _PROVIDER_MAP.get(name)


def get_provider_resource_mappings(provider_name: str) -> list[ProviderResourceMappingDef]:
    """Get all resource mappings for a given provider."""
    return [m for m in PROVIDER_RESOURCE_MAPPINGS if m.provider_name == provider_name]
