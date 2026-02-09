"""
Overview: Semantic type registry — single source of truth for all abstract resource types,
    categories, relationships, property schemas, providers, and type mappings.
Architecture: Core definitions that seed the database (Section 5)
Dependencies: dataclasses
Concepts: Semantic types normalize provider-specific resources into a unified model.
    Categories group types. Relationships define how types connect. Providers represent
    infrastructure platforms. ProviderResourceTypes define provider-specific resource APIs.
    TypeMappings link provider resource types to semantic types.
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


@dataclass(frozen=True)
class SemanticCategoryDef:
    """A top-level grouping of semantic types (Compute, Network, etc.)."""

    name: str
    display_name: str
    description: str
    icon: str
    sort_order: int = 0


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
class ProviderResourceTypeDef:
    """Defines a provider-specific resource type API (e.g., aws:ec2:instance, proxmox:qemu)."""

    provider_name: str
    api_type: str
    display_name: str
    description: str = ""
    parameter_schema: dict | None = None  # JSON schema, populated in Phase 11/18
    status: str = "available"  # "available", "deprecated", "preview"


@dataclass(frozen=True)
class TypeMappingDef:
    """Maps a provider resource type to a semantic type."""

    provider_name: str
    api_type: str
    semantic_type_name: str  # References SemanticTypeDef.name
    parameter_mapping: dict | None = None  # Mapping config, populated in Phase 11/18
    notes: str = ""


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
    ),
    SemanticCategoryDef(
        name="application",
        display_name="Application",
        description="Applications, services, endpoints, and message queues",
        icon="layers",
        sort_order=7,
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
                "os_type", "OS Type", PropertyDataType.STRING, description="linux, windows, other"
            ),
            PropertyDef("os_version", "OS Version", PropertyDataType.STRING),
            PropertyDef(
                "state",
                "State",
                PropertyDataType.STRING,
                required=True,
                description="running, stopped, suspended",
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
# Provider resource types
# ---------------------------------------------------------------------------

PROVIDER_RESOURCE_TYPES: list[ProviderResourceTypeDef] = [
    # ── Proxmox ───────────────────────────────────────────────────────────
    ProviderResourceTypeDef("proxmox", "qemu", "Proxmox QEMU/KVM virtual machine"),
    ProviderResourceTypeDef("proxmox", "lxc", "Proxmox LXC container"),
    ProviderResourceTypeDef("proxmox", "node", "Proxmox cluster node"),
    ProviderResourceTypeDef("proxmox", "linux-bridge", "Proxmox Linux bridge"),
    ProviderResourceTypeDef("proxmox", "ovs-bridge", "Proxmox OVS bridge"),
    ProviderResourceTypeDef("proxmox", "sdn-vnet", "Proxmox SDN VNet"),
    ProviderResourceTypeDef("proxmox", "sdn-subnet", "Proxmox SDN subnet"),
    ProviderResourceTypeDef("proxmox", "storage-lvm", "Proxmox LVM storage"),
    ProviderResourceTypeDef("proxmox", "storage-lvmthin", "Proxmox LVM-Thin storage"),
    ProviderResourceTypeDef("proxmox", "storage-zfs", "Proxmox ZFS storage"),
    ProviderResourceTypeDef("proxmox", "storage-ceph", "Proxmox Ceph RBD storage"),
    ProviderResourceTypeDef("proxmox", "storage-nfs", "Proxmox NFS storage"),
    ProviderResourceTypeDef("proxmox", "storage-cephfs", "Proxmox CephFS storage"),
    ProviderResourceTypeDef("proxmox", "storage-pbs", "Proxmox Backup Server"),
    ProviderResourceTypeDef("proxmox", "firewall-group", "Proxmox firewall security group"),
    ProviderResourceTypeDef("proxmox", "ha-group", "Proxmox HA group"),
    # ── AWS ───────────────────────────────────────────────────────────────
    ProviderResourceTypeDef("aws", "ec2:instance", "AWS EC2 Instance"),
    ProviderResourceTypeDef("aws", "ecs:task", "AWS ECS Task"),
    ProviderResourceTypeDef("aws", "ecs:service", "AWS ECS Service"),
    ProviderResourceTypeDef("aws", "lambda:function", "AWS Lambda Function"),
    ProviderResourceTypeDef("aws", "ec2:vpc", "AWS VPC"),
    ProviderResourceTypeDef("aws", "ec2:subnet", "AWS VPC Subnet"),
    ProviderResourceTypeDef("aws", "ec2:network-interface", "AWS ENI"),
    ProviderResourceTypeDef("aws", "elasticloadbalancing:loadbalancer", "AWS ELB/ALB/NLB"),
    ProviderResourceTypeDef("aws", "route53:hostedzone", "AWS Route 53 Hosted Zone"),
    ProviderResourceTypeDef("aws", "cloudfront:distribution", "AWS CloudFront Distribution"),
    ProviderResourceTypeDef("aws", "ec2:vpn-gateway", "AWS VPN Gateway"),
    ProviderResourceTypeDef("aws", "ebs:volume", "AWS EBS Volume"),
    ProviderResourceTypeDef("aws", "s3:bucket", "AWS S3 Bucket"),
    ProviderResourceTypeDef("aws", "efs:filesystem", "AWS EFS File System"),
    ProviderResourceTypeDef("aws", "backup:recovery-point", "AWS Backup Recovery Point"),
    ProviderResourceTypeDef("aws", "rds:db", "AWS RDS Instance"),
    ProviderResourceTypeDef("aws", "dynamodb:table", "AWS DynamoDB Table"),
    ProviderResourceTypeDef("aws", "elasticache:cluster", "AWS ElastiCache Cluster"),
    ProviderResourceTypeDef("aws", "redshift:cluster", "AWS Redshift Cluster"),
    ProviderResourceTypeDef("aws", "ec2:security-group", "AWS Security Group"),
    ProviderResourceTypeDef("aws", "ec2:network-acl", "AWS Network ACL"),
    ProviderResourceTypeDef("aws", "iam:role", "AWS IAM Role"),
    ProviderResourceTypeDef("aws", "iam:policy", "AWS IAM Policy"),
    ProviderResourceTypeDef("aws", "acm:certificate", "AWS ACM Certificate"),
    ProviderResourceTypeDef("aws", "secretsmanager:secret", "AWS Secrets Manager"),
    ProviderResourceTypeDef("aws", "kms:key", "AWS KMS Key (vault-like)"),
    ProviderResourceTypeDef("aws", "cloudwatch:alarm", "AWS CloudWatch Alarm"),
    ProviderResourceTypeDef("aws", "cloudwatch:dashboard", "AWS CloudWatch Dashboard"),
    ProviderResourceTypeDef("aws", "logs:log-group", "AWS CloudWatch Log Group"),
    ProviderResourceTypeDef("aws", "cloudwatch:metric", "AWS CloudWatch Metric"),
    ProviderResourceTypeDef("aws", "elasticbeanstalk:application", "AWS Elastic Beanstalk App"),
    ProviderResourceTypeDef("aws", "apigateway:restapi", "AWS API Gateway"),
    ProviderResourceTypeDef("aws", "sqs:queue", "AWS SQS Queue"),
    # ── Azure ─────────────────────────────────────────────────────────────
    ProviderResourceTypeDef("azure", "Microsoft.Compute/virtualMachines", "Azure VM"),
    ProviderResourceTypeDef("azure", "Microsoft.ContainerInstance/containerGroups", "Azure Container Instance"),
    ProviderResourceTypeDef("azure", "Microsoft.Web/sites", "Azure Functions (via App Service)"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/virtualNetworks", "Azure VNet"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/virtualNetworks/subnets", "Azure Subnet"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/networkInterfaces", "Azure NIC"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/loadBalancers", "Azure Load Balancer"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/dnszones", "Azure DNS Zone"),
    ProviderResourceTypeDef("azure", "Microsoft.Cdn/profiles", "Azure CDN Profile"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/vpnGateways", "Azure VPN Gateway"),
    ProviderResourceTypeDef("azure", "Microsoft.Compute/disks", "Azure Managed Disk"),
    ProviderResourceTypeDef("azure", "Microsoft.Storage/storageAccounts", "Azure Storage Account (Blob)"),
    ProviderResourceTypeDef("azure", "Microsoft.Storage/storageAccounts/fileServices", "Azure Files"),
    ProviderResourceTypeDef("azure", "Microsoft.RecoveryServices/vaults", "Azure Recovery Services Vault"),
    ProviderResourceTypeDef("azure", "Microsoft.Sql/servers/databases", "Azure SQL Database"),
    ProviderResourceTypeDef("azure", "Microsoft.DocumentDB/databaseAccounts", "Azure Cosmos DB"),
    ProviderResourceTypeDef("azure", "Microsoft.Cache/redis", "Azure Cache for Redis"),
    ProviderResourceTypeDef("azure", "Microsoft.Synapse/workspaces", "Azure Synapse Analytics"),
    ProviderResourceTypeDef("azure", "Microsoft.Network/networkSecurityGroups", "Azure NSG"),
    ProviderResourceTypeDef("azure", "Microsoft.Authorization/roleDefinitions", "Azure Role Definition"),
    ProviderResourceTypeDef("azure", "Microsoft.Authorization/policyDefinitions", "Azure Policy Definition"),
    ProviderResourceTypeDef("azure", "Microsoft.KeyVault/vaults", "Azure Key Vault"),
    ProviderResourceTypeDef("azure", "Microsoft.Insights/metricAlerts", "Azure Monitor Alert"),
    ProviderResourceTypeDef("azure", "Microsoft.Portal/dashboards", "Azure Dashboard"),
    ProviderResourceTypeDef("azure", "Microsoft.Insights/components", "Azure App Insights"),
    ProviderResourceTypeDef("azure", "Microsoft.ApiManagement/service", "Azure API Management"),
    ProviderResourceTypeDef("azure", "Microsoft.ServiceBus/namespaces/queues", "Azure Service Bus Queue"),
    # ── GCP ───────────────────────────────────────────────────────────────
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/Instance", "GCP Compute Engine Instance"),
    ProviderResourceTypeDef("gcp", "run.googleapis.com/Service", "GCP Cloud Run Service"),
    ProviderResourceTypeDef("gcp", "cloudfunctions.googleapis.com/Function", "GCP Cloud Function"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/Network", "GCP VPC Network"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/Subnetwork", "GCP Subnetwork"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/ForwardingRule", "GCP Load Balancer"),
    ProviderResourceTypeDef("gcp", "dns.googleapis.com/ManagedZone", "GCP Cloud DNS"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/VpnGateway", "GCP VPN Gateway"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/Disk", "GCP Persistent Disk"),
    ProviderResourceTypeDef("gcp", "storage.googleapis.com/Bucket", "GCP Cloud Storage Bucket"),
    ProviderResourceTypeDef("gcp", "file.googleapis.com/Instance", "GCP Filestore Instance"),
    ProviderResourceTypeDef("gcp", "sqladmin.googleapis.com/Instance", "GCP Cloud SQL Instance"),
    ProviderResourceTypeDef("gcp", "firestore.googleapis.com/Database", "GCP Firestore Database"),
    ProviderResourceTypeDef("gcp", "redis.googleapis.com/Instance", "GCP Memorystore Redis"),
    ProviderResourceTypeDef("gcp", "bigquery.googleapis.com/Dataset", "GCP BigQuery Dataset"),
    ProviderResourceTypeDef("gcp", "compute.googleapis.com/Firewall", "GCP Firewall Rule"),
    ProviderResourceTypeDef("gcp", "iam.googleapis.com/Role", "GCP IAM Role"),
    ProviderResourceTypeDef("gcp", "cloudkms.googleapis.com/KeyRing", "GCP Cloud KMS Key Ring"),
    ProviderResourceTypeDef("gcp", "monitoring.googleapis.com/AlertPolicy", "GCP Cloud Monitoring Alert"),
    ProviderResourceTypeDef("gcp", "monitoring.googleapis.com/Dashboard", "GCP Cloud Monitoring Dashboard"),
    ProviderResourceTypeDef("gcp", "logging.googleapis.com/LogBucket", "GCP Cloud Logging Bucket"),
    ProviderResourceTypeDef("gcp", "appengine.googleapis.com/Application", "GCP App Engine Application"),
    ProviderResourceTypeDef("gcp", "pubsub.googleapis.com/Topic", "GCP Pub/Sub Topic"),
    # ── OCI (Oracle Cloud Infrastructure) ─────────────────────────────────
    ProviderResourceTypeDef("oci", "core/instance", "OCI Compute Instance"),
    ProviderResourceTypeDef("oci", "containerinstances/containerInstance", "OCI Container Instance"),
    ProviderResourceTypeDef("oci", "functions/function", "OCI Functions"),
    ProviderResourceTypeDef("oci", "computebaremetal/instance", "OCI Bare Metal Instance"),
    ProviderResourceTypeDef("oci", "core/vcn", "OCI VCN"),
    ProviderResourceTypeDef("oci", "core/subnet", "OCI Subnet"),
    ProviderResourceTypeDef("oci", "core/vnic", "OCI VNIC"),
    ProviderResourceTypeDef("oci", "loadbalancer/loadbalancer", "OCI Load Balancer"),
    ProviderResourceTypeDef("oci", "dns/zone", "OCI DNS Zone"),
    ProviderResourceTypeDef("oci", "core/ipsecconnection", "OCI IPSec Connection"),
    ProviderResourceTypeDef("oci", "core/volume", "OCI Block Volume"),
    ProviderResourceTypeDef("oci", "objectstorage/bucket", "OCI Object Storage Bucket"),
    ProviderResourceTypeDef("oci", "filestorage/filesystem", "OCI File Storage"),
    ProviderResourceTypeDef("oci", "database/dbsystem", "OCI DB System"),
    ProviderResourceTypeDef("oci", "nosql/table", "OCI NoSQL Table"),
    ProviderResourceTypeDef("oci", "redis/redisCluster", "OCI Cache with Redis"),
    ProviderResourceTypeDef("oci", "core/securitylist", "OCI Security List"),
    ProviderResourceTypeDef("oci", "core/networksecuritygroup", "OCI Network Security Group"),
    ProviderResourceTypeDef("oci", "identity/policy", "OCI IAM Policy"),
    ProviderResourceTypeDef("oci", "vault/vault", "OCI Vault"),
    ProviderResourceTypeDef("oci", "monitoring/alarm", "OCI Monitoring Alarm"),
    ProviderResourceTypeDef("oci", "logging/loggroup", "OCI Logging Log Group"),
    ProviderResourceTypeDef("oci", "streaming/stream", "OCI Streaming"),
]


# ---------------------------------------------------------------------------
# Type mappings
# ---------------------------------------------------------------------------

TYPE_MAPPINGS: list[TypeMappingDef] = [
    # ── Proxmox ───────────────────────────────────────────────────────────
    TypeMappingDef("proxmox", "qemu", "VirtualMachine"),
    TypeMappingDef("proxmox", "lxc", "Container"),
    TypeMappingDef("proxmox", "node", "BareMetalServer"),
    TypeMappingDef("proxmox", "linux-bridge", "VirtualNetwork"),
    TypeMappingDef("proxmox", "ovs-bridge", "VirtualNetwork"),
    TypeMappingDef("proxmox", "sdn-vnet", "VirtualNetwork"),
    TypeMappingDef("proxmox", "sdn-subnet", "Subnet"),
    TypeMappingDef("proxmox", "storage-lvm", "BlockStorage"),
    TypeMappingDef("proxmox", "storage-lvmthin", "BlockStorage"),
    TypeMappingDef("proxmox", "storage-zfs", "BlockStorage"),
    TypeMappingDef("proxmox", "storage-ceph", "BlockStorage"),
    TypeMappingDef("proxmox", "storage-nfs", "FileStorage"),
    TypeMappingDef("proxmox", "storage-cephfs", "FileStorage"),
    TypeMappingDef("proxmox", "storage-pbs", "Backup"),
    TypeMappingDef("proxmox", "firewall-group", "SecurityGroup"),
    TypeMappingDef("proxmox", "ha-group", "Application"),
    # ── AWS ───────────────────────────────────────────────────────────────
    TypeMappingDef("aws", "ec2:instance", "VirtualMachine"),
    TypeMappingDef("aws", "ecs:task", "Container"),
    TypeMappingDef("aws", "ecs:service", "Service"),
    TypeMappingDef("aws", "lambda:function", "ServerlessFunction"),
    TypeMappingDef("aws", "ec2:vpc", "VirtualNetwork"),
    TypeMappingDef("aws", "ec2:subnet", "Subnet"),
    TypeMappingDef("aws", "ec2:network-interface", "NetworkInterface"),
    TypeMappingDef("aws", "elasticloadbalancing:loadbalancer", "LoadBalancer"),
    TypeMappingDef("aws", "route53:hostedzone", "DNS"),
    TypeMappingDef("aws", "cloudfront:distribution", "CDN"),
    TypeMappingDef("aws", "ec2:vpn-gateway", "VPNGateway"),
    TypeMappingDef("aws", "ebs:volume", "BlockStorage"),
    TypeMappingDef("aws", "s3:bucket", "ObjectStorage"),
    TypeMappingDef("aws", "efs:filesystem", "FileStorage"),
    TypeMappingDef("aws", "backup:recovery-point", "Backup"),
    TypeMappingDef("aws", "rds:db", "RelationalDatabase"),
    TypeMappingDef("aws", "dynamodb:table", "NoSQLDatabase"),
    TypeMappingDef("aws", "elasticache:cluster", "CacheService"),
    TypeMappingDef("aws", "redshift:cluster", "DataWarehouse"),
    TypeMappingDef("aws", "ec2:security-group", "SecurityGroup"),
    TypeMappingDef("aws", "ec2:network-acl", "NetworkACL"),
    TypeMappingDef("aws", "iam:role", "IAMRole"),
    TypeMappingDef("aws", "iam:policy", "IAMPolicy"),
    TypeMappingDef("aws", "acm:certificate", "Certificate"),
    TypeMappingDef("aws", "secretsmanager:secret", "Secret"),
    TypeMappingDef("aws", "kms:key", "KeyVault"),
    TypeMappingDef("aws", "cloudwatch:alarm", "AlertRule"),
    TypeMappingDef("aws", "cloudwatch:dashboard", "Dashboard"),
    TypeMappingDef("aws", "logs:log-group", "LogGroup"),
    TypeMappingDef("aws", "cloudwatch:metric", "Metric"),
    TypeMappingDef("aws", "elasticbeanstalk:application", "Application"),
    TypeMappingDef("aws", "apigateway:restapi", "Endpoint"),
    TypeMappingDef("aws", "sqs:queue", "Queue"),
    # ── Azure ─────────────────────────────────────────────────────────────
    TypeMappingDef("azure", "Microsoft.Compute/virtualMachines", "VirtualMachine"),
    TypeMappingDef("azure", "Microsoft.ContainerInstance/containerGroups", "Container"),
    TypeMappingDef("azure", "Microsoft.Web/sites", "ServerlessFunction"),
    TypeMappingDef("azure", "Microsoft.Network/virtualNetworks", "VirtualNetwork"),
    TypeMappingDef("azure", "Microsoft.Network/virtualNetworks/subnets", "Subnet"),
    TypeMappingDef("azure", "Microsoft.Network/networkInterfaces", "NetworkInterface"),
    TypeMappingDef("azure", "Microsoft.Network/loadBalancers", "LoadBalancer"),
    TypeMappingDef("azure", "Microsoft.Network/dnszones", "DNS"),
    TypeMappingDef("azure", "Microsoft.Cdn/profiles", "CDN"),
    TypeMappingDef("azure", "Microsoft.Network/vpnGateways", "VPNGateway"),
    TypeMappingDef("azure", "Microsoft.Compute/disks", "BlockStorage"),
    TypeMappingDef("azure", "Microsoft.Storage/storageAccounts", "ObjectStorage"),
    TypeMappingDef("azure", "Microsoft.Storage/storageAccounts/fileServices", "FileStorage"),
    TypeMappingDef("azure", "Microsoft.RecoveryServices/vaults", "Backup"),
    TypeMappingDef("azure", "Microsoft.Sql/servers/databases", "RelationalDatabase"),
    TypeMappingDef("azure", "Microsoft.DocumentDB/databaseAccounts", "NoSQLDatabase"),
    TypeMappingDef("azure", "Microsoft.Cache/redis", "CacheService"),
    TypeMappingDef("azure", "Microsoft.Synapse/workspaces", "DataWarehouse"),
    TypeMappingDef("azure", "Microsoft.Network/networkSecurityGroups", "SecurityGroup"),
    TypeMappingDef("azure", "Microsoft.Authorization/roleDefinitions", "IAMRole"),
    TypeMappingDef("azure", "Microsoft.Authorization/policyDefinitions", "IAMPolicy"),
    TypeMappingDef("azure", "Microsoft.KeyVault/vaults", "KeyVault"),
    TypeMappingDef("azure", "Microsoft.Insights/metricAlerts", "AlertRule"),
    TypeMappingDef("azure", "Microsoft.Portal/dashboards", "Dashboard"),
    TypeMappingDef("azure", "Microsoft.Insights/components", "LogGroup"),
    TypeMappingDef("azure", "Microsoft.ApiManagement/service", "Endpoint"),
    TypeMappingDef("azure", "Microsoft.ServiceBus/namespaces/queues", "Queue"),
    # ── GCP ───────────────────────────────────────────────────────────────
    TypeMappingDef("gcp", "compute.googleapis.com/Instance", "VirtualMachine"),
    TypeMappingDef("gcp", "run.googleapis.com/Service", "Container"),
    TypeMappingDef("gcp", "cloudfunctions.googleapis.com/Function", "ServerlessFunction"),
    TypeMappingDef("gcp", "compute.googleapis.com/Network", "VirtualNetwork"),
    TypeMappingDef("gcp", "compute.googleapis.com/Subnetwork", "Subnet"),
    TypeMappingDef("gcp", "compute.googleapis.com/ForwardingRule", "LoadBalancer"),
    TypeMappingDef("gcp", "dns.googleapis.com/ManagedZone", "DNS"),
    TypeMappingDef("gcp", "compute.googleapis.com/VpnGateway", "VPNGateway"),
    TypeMappingDef("gcp", "compute.googleapis.com/Disk", "BlockStorage"),
    TypeMappingDef("gcp", "storage.googleapis.com/Bucket", "ObjectStorage"),
    TypeMappingDef("gcp", "file.googleapis.com/Instance", "FileStorage"),
    TypeMappingDef("gcp", "sqladmin.googleapis.com/Instance", "RelationalDatabase"),
    TypeMappingDef("gcp", "firestore.googleapis.com/Database", "NoSQLDatabase"),
    TypeMappingDef("gcp", "redis.googleapis.com/Instance", "CacheService"),
    TypeMappingDef("gcp", "bigquery.googleapis.com/Dataset", "DataWarehouse"),
    TypeMappingDef("gcp", "compute.googleapis.com/Firewall", "SecurityGroup"),
    TypeMappingDef("gcp", "iam.googleapis.com/Role", "IAMRole"),
    TypeMappingDef("gcp", "cloudkms.googleapis.com/KeyRing", "KeyVault"),
    TypeMappingDef("gcp", "monitoring.googleapis.com/AlertPolicy", "AlertRule"),
    TypeMappingDef("gcp", "monitoring.googleapis.com/Dashboard", "Dashboard"),
    TypeMappingDef("gcp", "logging.googleapis.com/LogBucket", "LogGroup"),
    TypeMappingDef("gcp", "appengine.googleapis.com/Application", "Application"),
    TypeMappingDef("gcp", "pubsub.googleapis.com/Topic", "Queue"),
    # ── OCI (Oracle Cloud Infrastructure) ─────────────────────────────────
    TypeMappingDef("oci", "core/instance", "VirtualMachine"),
    TypeMappingDef("oci", "containerinstances/containerInstance", "Container"),
    TypeMappingDef("oci", "functions/function", "ServerlessFunction"),
    TypeMappingDef("oci", "computebaremetal/instance", "BareMetalServer"),
    TypeMappingDef("oci", "core/vcn", "VirtualNetwork"),
    TypeMappingDef("oci", "core/subnet", "Subnet"),
    TypeMappingDef("oci", "core/vnic", "NetworkInterface"),
    TypeMappingDef("oci", "loadbalancer/loadbalancer", "LoadBalancer"),
    TypeMappingDef("oci", "dns/zone", "DNS"),
    TypeMappingDef("oci", "core/ipsecconnection", "VPNGateway"),
    TypeMappingDef("oci", "core/volume", "BlockStorage"),
    TypeMappingDef("oci", "objectstorage/bucket", "ObjectStorage"),
    TypeMappingDef("oci", "filestorage/filesystem", "FileStorage"),
    TypeMappingDef("oci", "database/dbsystem", "RelationalDatabase"),
    TypeMappingDef("oci", "nosql/table", "NoSQLDatabase"),
    TypeMappingDef("oci", "redis/redisCluster", "CacheService"),
    TypeMappingDef("oci", "core/securitylist", "SecurityGroup"),
    TypeMappingDef("oci", "core/networksecuritygroup", "SecurityGroup"),
    TypeMappingDef("oci", "identity/policy", "IAMPolicy"),
    TypeMappingDef("oci", "vault/vault", "KeyVault"),
    TypeMappingDef("oci", "monitoring/alarm", "AlertRule"),
    TypeMappingDef("oci", "logging/loggroup", "LogGroup"),
    TypeMappingDef("oci", "streaming/stream", "Queue"),
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


def get_provider_resource_types(provider_name: str) -> list[ProviderResourceTypeDef]:
    """Get all resource types for a given provider."""
    return [prt for prt in PROVIDER_RESOURCE_TYPES if prt.provider_name == provider_name]


def get_type_mappings_for_provider(provider_name: str) -> list[TypeMappingDef]:
    """Get all type mappings for a given provider."""
    return [tm for tm in TYPE_MAPPINGS if tm.provider_name == provider_name]
