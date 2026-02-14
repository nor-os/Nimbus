# Phase 11: Landing Zones & IPAM

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Establish the foundational concept of **Landing Zones** — the structured, pre-configured cloud environments into which tenants deploy infrastructure. This phase defines two complementary layers:

1. **Provider Landing Zones** — Per-cloud-backend network topology (compartments, networking, regions) managed by the provider. Defines the "playing field" that tenants deploy into.
2. **Tenant Landing Zones** — Per-tenant environment definitions (dev/staging/prod/custom) with environment-level configuration, tagging rules, and resource policies.
3. **Cloud Tenancy Abstraction** — Semantic types for cloud tenancy concepts (OCI Tenancy, Azure Subscription, AWS Account, GCP Project, Proxmox Datacenter) resolved through the semantic model.
4. **Full IPAM** — Hierarchical IP address management with supernet allocation, VCN/VPC carving, subnet planning, individual IP reservation, conflict detection, and utilization tracking.

No actual cloud provisioning in this phase — landing zones are planning/modeling artifacts. Provisioning occurs when Pulumi integration (Phase 13, formerly 12) connects.

*New phase, inserted before old Phase 11 (Proxmox Provider). All subsequent phases renumber +1.*

## Dependencies
- Phase 5 complete (semantic layer — providers, resource types, type mappings)
- Phase 7 complete (topology engine — Rete.js canvas, graph model, compartment hierarchy)
- Phase 8 complete (CMDB — compartments, CI classes, relationships)
- Phase 10 complete (approval workflows — landing zone publish gates)

## Key Decisions
- **Topology reuse** — Provider landing zones ARE topologies (`architecture_topologies` with `is_landing_zone: true`). Reuses the full Rete.js canvas with a restricted node palette (compartment + networking nodes only).
- **Cloud tenancy via semantic types** — New `Tenancy` semantic category with abstract `CloudTenancy` type. Provider-specific mappings: OCI Tenancy, Azure Subscription, AWS Account, GCP Project, Proxmox Datacenter/Cluster.
- **Multi-region from the start** — Provider landing zones define per-region network topologies with cross-region peering connections.
- **Environment templates + custom** — Provider defines standard templates (Development, Staging, Production, DR). Tenants can use templates or create fully custom environments.
- **Full IPAM** — Hierarchical address spaces, subnet planning, IP reservation, conflict detection, utilization tracking.
- **Planning only** — No Pulumi execution. Landing zones generate deployment-ready specifications that Phase 13 (Pulumi) consumes.

---

## Concept Overview

### Provider Landing Zone

A provider landing zone is the **top-level cloud infrastructure skeleton** that the provider (MSP/platform operator) prepares for tenant consumption. It is scoped to a single **cloud backend** (e.g., one Proxmox cluster, one OCI tenancy, one Azure subscription).

```
Cloud Backend (e.g., OCI Frankfurt)
└── Provider Landing Zone
    ├── Cloud Tenancy (root OCI tenancy / Azure subscription / AWS account)
    ├── Region: eu-frankfurt-1
    │   ├── Shared Services Compartment
    │   │   ├── Hub VCN (10.0.0.0/16)
    │   │   │   ├── Management Subnet (10.0.1.0/24)
    │   │   │   ├── Monitoring Subnet (10.0.2.0/24)
    │   │   │   └── Bastion Subnet (10.0.3.0/24)
    │   │   ├── Internet Gateway
    │   │   ├── NAT Gateway
    │   │   └── DRG (Dynamic Routing Gateway)
    │   └── Tenant Zone
    │       ├── Address Pool: 10.100.0.0/12 (carved per tenant)
    │       └── [Tenant environments deploy here]
    ├── Region: eu-amsterdam-1
    │   ├── DR Compartment
    │   │   └── DR VCN (10.200.0.0/16)
    │   └── Cross-Region Peering ↔ eu-frankfurt-1
    └── Tagging Namespace
        ├── environment (required)
        ├── cost-center (required)
        ├── owner (required)
        └── project (optional)
```

The topology editor palette is restricted to:
- **Compartment** nodes (nested hierarchy)
- **Region** nodes (top-level containers)
- **Network** nodes: VCN/VPC/VNet, Subnet, Route Table, Security List/NSG, Internet Gateway, NAT Gateway, VPN Gateway, Peering Connection, DRG/Transit Gateway
- **Tenancy** node (root cloud tenancy reference)
- **Address Pool** nodes (IPAM allocation blocks)

Compute, storage, database, and application nodes are NOT available in landing zone mode.

### Tenant Landing Zone

A tenant landing zone defines the **environments** that a specific tenant operates within a provider landing zone. Each environment is a logical deployment target with its own compartment tree, network allocations, tagging rules, and policies.

```
Tenant: Acme Corp
├── Environment: Production
│   ├── Root Compartment (auto-created in provider's Tenant Zone)
│   ├── VCN: 10.100.0.0/20 (allocated from provider's address pool)
│   │   ├── App Subnet: 10.100.0.0/24
│   │   ├── DB Subnet: 10.100.1.0/24
│   │   └── LB Subnet: 10.100.2.0/24
│   ├── Tags (inherited + custom):
│   │   ├── environment = "production"
│   │   ├── cost-center = "CC-1234"
│   │   ├── tenant = "acme-corp"
│   │   └── compliance = "pci-dss"
│   └── Policies:
│       ├── Min subnet size: /28
│       ├── Max VCNs: 3
│       └── Required tags on all resources: [environment, cost-center]
├── Environment: Staging
│   ├── VCN: 10.100.16.0/20
│   └── Tags: environment = "staging", ...
└── Environment: Development
    ├── VCN: 10.100.32.0/20
    └── Tags: environment = "development", ...
```

### Cloud Tenancy Resolution (Semantic Layer)

Cloud tenancy concepts are provider-specific but share a common abstraction:

| Semantic Type | OCI | Azure | AWS | GCP | Proxmox |
|---|---|---|---|---|---|
| CloudTenancy | Tenancy | Subscription | Account | Project | Datacenter |
| CloudCompartment | Compartment | Resource Group | OU | Folder | Pool |
| CloudRegion | Region | Region | Region | Region | Node/Cluster |

These become **semantic types** in the existing semantic layer framework. Provider landing zones reference them to define the cloud-side hierarchy that Nimbus manages.

### IPAM (IP Address Management)

Full hierarchical IPAM with four levels:

```
Address Space (per provider landing zone)
├── Supernet: 10.0.0.0/8
│   ├── Region Allocation: 10.0.0.0/12 (eu-frankfurt-1)
│   │   ├── Provider Reserved: 10.0.0.0/16 (shared services)
│   │   │   ├── Subnet: 10.0.1.0/24 (management) — 80% utilized
│   │   │   └── Subnet: 10.0.2.0/24 (monitoring) — 30% utilized
│   │   └── Tenant Pool: 10.100.0.0/12
│   │       ├── Acme Corp Prod: 10.100.0.0/20
│   │       │   ├── Subnet: 10.100.0.0/24 — 45% utilized
│   │       │   │   ├── 10.100.0.10 — Reserved (load balancer VIP)
│   │       │   │   ├── 10.100.0.11 — Reserved (bastion host)
│   │       │   │   └── 10.100.0.12-254 — DHCP pool
│   │       │   └── Subnet: 10.100.1.0/24 — 20% utilized
│   │       ├── Acme Corp Staging: 10.100.16.0/20
│   │       └── [Available: 10.100.48.0/20 - 10.100.240.0/20]
│   └── Region Allocation: 10.200.0.0/12 (eu-amsterdam-1)
└── Supernet: 172.16.0.0/12 (secondary, if needed)
```

Features:
- **Conflict detection** — Overlapping CIDR validation across all allocations
- **Auto-suggestion** — Next available block of requested size
- **Utilization tracking** — Per-subnet, per-VCN, per-region utilization percentages
- **Reservation** — Individual IP addresses reserved with purpose/owner metadata
- **Capacity planning** — Alerting when pools approach exhaustion thresholds
- **Visual map** — Treemap or bar visualization of address space utilization

---

## Data Model

### `landing_zones`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | `server_default=gen_random_uuid()` |
| tenant_id | UUID FK → tenants | Provider's root tenant (NOT NULL) |
| backend_id | UUID FK → cloud_backends | Which cloud backend this LZ covers (NOT NULL) |
| topology_id | UUID FK → architecture_topologies | The LZ topology (restricted palette) (NOT NULL) |
| cloud_tenancy_id | UUID FK → configuration_items, nullable | CI representing the root cloud tenancy |
| name | String(255) | NOT NULL |
| description | Text, nullable | |
| status | Enum `landing_zone_status` | DRAFT, PUBLISHED, ARCHIVED. Default DRAFT |
| version | Integer, default 0 | |
| settings | JSONB, nullable | LZ-wide config (default tags, naming conventions) |
| created_by | UUID FK → users | NOT NULL |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | Soft delete |

**Indexes:**
- `ix_landing_zones_tenant` on `tenant_id`
- `ix_landing_zones_backend` on `backend_id`
- `ix_landing_zones_status` on `(tenant_id, status)`

**Unique:** `uq_landing_zone_backend_name_version` on `(backend_id, name, version) WHERE deleted_at IS NULL` (partial)

### `landing_zone_regions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| landing_zone_id | UUID FK → landing_zones | NOT NULL |
| region_identifier | String(100) | Provider-specific (e.g., `eu-frankfurt-1`) NOT NULL |
| display_name | String(255) | NOT NULL |
| is_primary | Boolean, default false | |
| is_dr | Boolean, default false | Disaster recovery region |
| settings | JSONB, nullable | Region-specific overrides |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |

**Unique:** `uq_lz_region` on `(landing_zone_id, region_identifier)`

### `landing_zone_tag_policies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| landing_zone_id | UUID FK → landing_zones | NOT NULL |
| tag_key | String(255) | e.g., `environment`, `cost-center` NOT NULL |
| display_name | String(255) | NOT NULL |
| description | Text, nullable | |
| is_required | Boolean, default false | Must be set on all resources |
| allowed_values | JSONB, nullable | Array of allowed values, null = freeform |
| default_value | String(500), nullable | |
| inherited | Boolean, default true | Auto-inherit to child compartments/resources |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |

**Unique:** `uq_lz_tag_key` on `(landing_zone_id, tag_key)`

### `environment_templates`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| provider_id | UUID FK → providers | Which Nimbus provider defines this template NOT NULL |
| name | String(100) | e.g., `production`, `staging`, `development` NOT NULL |
| display_name | String(255) | NOT NULL |
| description | Text, nullable | |
| icon | String(50), nullable | |
| color | String(7), nullable | Hex color for UI visualization |
| default_tags | JSONB, nullable | Tags auto-applied to this environment type |
| default_policies | JSONB, nullable | Default resource policies (max VCNs, min subnet size, etc.) |
| sort_order | Integer, default 0 | |
| is_system | Boolean, default false | |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | |

**Unique:** `uq_env_template_provider_name` on `(provider_id, name) WHERE deleted_at IS NULL` (partial)

**Seed data (is_system=true):**
| name | display_name | icon | color | default_tags | sort_order |
|------|-------------|------|-------|-------------|------------|
| development | Development | code | #22c55e | `{"environment": "development"}` | 1 |
| staging | Staging | flask | #f59e0b | `{"environment": "staging"}` | 2 |
| production | Production | shield-check | #3b82f6 | `{"environment": "production"}` | 3 |
| disaster-recovery | Disaster Recovery | alert-triangle | #ef4444 | `{"environment": "disaster-recovery"}` | 4 |

### `tenant_environments`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK → tenants | NOT NULL |
| landing_zone_id | UUID FK → landing_zones | Which provider LZ this deploys into NOT NULL |
| template_id | UUID FK → environment_templates, nullable | Null = custom environment |
| name | String(100) | NOT NULL |
| display_name | String(255) | NOT NULL |
| description | Text, nullable | |
| status | Enum `environment_status` | PLANNED, PROVISIONING, ACTIVE, SUSPENDED, DECOMMISSIONING, DECOMMISSIONED. Default PLANNED |
| root_compartment_id | UUID FK → compartments, nullable | Root compartment in cloud provider |
| tags | JSONB, default '{}' | Merged: template defaults + tenant overrides |
| policies | JSONB, default '{}' | Merged: template defaults + tenant overrides |
| settings | JSONB, nullable | Environment-specific config |
| created_by | UUID FK → users | NOT NULL |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | |

**Indexes:**
- `ix_tenant_envs_tenant` on `tenant_id`
- `ix_tenant_envs_lz` on `landing_zone_id`
- `ix_tenant_envs_status` on `(tenant_id, status)`

**Unique:** `uq_tenant_env_name` on `(tenant_id, landing_zone_id, name) WHERE deleted_at IS NULL` (partial)

### `address_spaces`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| landing_zone_id | UUID FK → landing_zones | NOT NULL |
| region_id | UUID FK → landing_zone_regions, nullable | Null = spans all regions |
| name | String(255) | NOT NULL |
| description | Text, nullable | |
| cidr | String(43) | CIDR notation. Max length for IPv6: `xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx/128` = 43 chars |
| ip_version | SmallInteger, default 4 | 4 or 6 |
| status | Enum `address_space_status` | ACTIVE, EXHAUSTED, RESERVED. Default ACTIVE |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | |

**Unique:** `uq_addr_space_lz_cidr` on `(landing_zone_id, cidr) WHERE deleted_at IS NULL` (partial)

### `address_allocations`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| address_space_id | UUID FK → address_spaces | NOT NULL |
| parent_allocation_id | UUID FK → address_allocations, nullable | Hierarchical carving |
| tenant_environment_id | UUID FK → tenant_environments, nullable | Which tenant env owns this block |
| name | String(255) | NOT NULL |
| description | Text, nullable | |
| cidr | String(43) | Allocated CIDR block NOT NULL |
| allocation_type | Enum `allocation_type` | REGION, PROVIDER_RESERVED, TENANT_POOL, VCN, SUBNET. NOT NULL |
| status | Enum `allocation_status` | PLANNED, ALLOCATED, IN_USE, RELEASED. Default PLANNED |
| purpose | String(255), nullable | e.g., "management", "application", "database" |
| semantic_type_id | UUID FK → semantic_resource_types, nullable | Links to VirtualNetwork, Subnet semantic types |
| cloud_resource_id | String(500), nullable | Actual cloud resource ID once provisioned |
| utilization_percent | Float, nullable | 0-100. Updated by utilization tracking |
| metadata | JSONB, nullable | Provider-specific allocation data |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | |

**Indexes:**
- `ix_addr_alloc_space` on `address_space_id`
- `ix_addr_alloc_parent` on `parent_allocation_id`
- `ix_addr_alloc_tenant_env` on `tenant_environment_id`

**Unique:** `uq_addr_alloc_space_cidr` on `(address_space_id, cidr) WHERE deleted_at IS NULL` (partial)

### `ip_reservations`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| allocation_id | UUID FK → address_allocations | Must be SUBNET-type allocation. NOT NULL |
| ip_address | String(45) | IPv4 or IPv6 address NOT NULL |
| hostname | String(255), nullable | Associated hostname |
| purpose | String(255) | e.g., "load-balancer-vip" NOT NULL |
| ci_id | UUID FK → configuration_items, nullable | Linked CI once provisioned |
| status | Enum `reservation_status` | RESERVED, IN_USE, RELEASED. Default RESERVED |
| reserved_by | UUID FK → users | NOT NULL |
| created_at | DateTime(tz), server_default=now() | |
| updated_at | DateTime(tz), server_default=now() | |
| deleted_at | DateTime(tz), nullable | |

**Indexes:**
- `ix_ip_res_allocation` on `allocation_id`
- `ix_ip_res_ci` on `ci_id`

**Unique:** `uq_ip_res_alloc_ip` on `(allocation_id, ip_address) WHERE deleted_at IS NULL` (partial)

### Column added to existing table

**`architecture_topologies`** — Add column:
- `is_landing_zone` Boolean, default false, NOT NULL

---

## New Semantic Types

### New Category: `Tenancy` (sort_order=9)

Added to `CATEGORIES` list in `registry.py`:
```python
SemanticCategoryDef(
    name="tenancy",
    display_name="Tenancy",
    description="Cloud tenancy constructs — accounts, subscriptions, compartments, regions",
    icon="building",
    sort_order=9,
)
```

### New Semantic Types (added to `SEMANTIC_TYPES` list)

#### CloudTenancy (abstract)
```python
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
        PropertyDef("status", "Status", PropertyDataType.STRING, default_value="active",
                     allowed_values=["active", "suspended", "closed"]),
        PropertyDef("home_region", "Home Region", PropertyDataType.STRING),
    ],
    allowed_relationship_kinds=["contains", "hosts_in"],
    sort_order=1,
)
```

#### CloudCompartment (abstract)
```python
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
)
```

#### CloudRegion
```python
SemanticTypeDef(
    name="CloudRegion",
    display_name="Cloud Region",
    category="tenancy",
    description="Cloud provider region — maps to OCI Region, Azure Region, AWS Region, GCP Region",
    icon="map-pin",
    properties=[
        PropertyDef("region_name", "Region Name", PropertyDataType.STRING, required=True),
        PropertyDef("region_code", "Region Code", PropertyDataType.STRING, required=True,
                     description="Provider-specific code (e.g., eu-frankfurt-1, westeurope, us-east-1)"),
        PropertyDef("availability_domains", "Availability Domains", PropertyDataType.INTEGER, default_value="3"),
        PropertyDef("geographic_area", "Geographic Area", PropertyDataType.STRING),
    ],
    allowed_relationship_kinds=["contains", "peers_with", "hosted_by"],
    sort_order=3,
)
```

#### AddressPool (non-abstract, for use in landing zone palette)
```python
SemanticTypeDef(
    name="AddressPool",
    display_name="Address Pool",
    category="tenancy",
    description="IPAM address pool — a CIDR block reserved for tenant allocation",
    icon="grid",
    properties=[
        PropertyDef("cidr", "CIDR Block", PropertyDataType.STRING, required=True,
                     description="CIDR notation (e.g., 10.100.0.0/12)"),
        PropertyDef("ip_version", "IP Version", PropertyDataType.INTEGER, default_value="4",
                     allowed_values=["4", "6"]),
        PropertyDef("pool_type", "Pool Type", PropertyDataType.STRING, default_value="tenant",
                     allowed_values=["provider_reserved", "tenant", "shared"]),
    ],
    allowed_relationship_kinds=["contained_by", "allocates_from"],
    sort_order=4,
)
```

### New Provider Resource Type Mappings (added to `PROVIDER_RESOURCE_MAPPINGS`)

| provider_name | api_type | semantic_type_name | display_name |
|---|---|---|---|
| oci | `iam:tenancy` | CloudTenancy | OCI Tenancy |
| oci | `iam:compartment` | CloudCompartment | OCI Compartment |
| oci | `iam:region-subscription` | CloudRegion | OCI Region Subscription |
| azure | `management:subscription` | CloudTenancy | Azure Subscription |
| azure | `resources:resource-group` | CloudCompartment | Azure Resource Group |
| azure | `management:management-group` | CloudCompartment | Azure Management Group |
| aws | `organizations:account` | CloudTenancy | AWS Account |
| aws | `organizations:organizational-unit` | CloudCompartment | AWS Organizational Unit |
| gcp | `cloudresourcemanager:project` | CloudTenancy | GCP Project |
| gcp | `cloudresourcemanager:folder` | CloudCompartment | GCP Folder |
| proxmox | `cluster:datacenter` | CloudTenancy | Proxmox Datacenter |
| proxmox | `cluster:pool` | CloudCompartment | Proxmox Pool |
| proxmox | `cluster:node` | CloudRegion | Proxmox Node |

### New Relationship Kinds (added to `RELATIONSHIP_KINDS`)

```python
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
```

---

## Enums

### Python Enums (backend)
```python
class LandingZoneStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class EnvironmentStatus(str, Enum):
    PLANNED = "PLANNED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DECOMMISSIONING = "DECOMMISSIONING"
    DECOMMISSIONED = "DECOMMISSIONED"

class AddressSpaceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    RESERVED = "RESERVED"

class AllocationType(str, Enum):
    REGION = "REGION"
    PROVIDER_RESERVED = "PROVIDER_RESERVED"
    TENANT_POOL = "TENANT_POOL"
    VCN = "VCN"
    SUBNET = "SUBNET"

class AllocationStatus(str, Enum):
    PLANNED = "PLANNED"
    ALLOCATED = "ALLOCATED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"

class ReservationStatus(str, Enum):
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    RELEASED = "RELEASED"
```

### SQL Enum Creation (migration)
```sql
DO $$ BEGIN CREATE TYPE landing_zone_status AS ENUM ('DRAFT','PUBLISHED','ARCHIVED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
DO $$ BEGIN CREATE TYPE environment_status AS ENUM ('PLANNED','PROVISIONING','ACTIVE','SUSPENDED','DECOMMISSIONING','DECOMMISSIONED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
DO $$ BEGIN CREATE TYPE address_space_status AS ENUM ('ACTIVE','EXHAUSTED','RESERVED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
DO $$ BEGIN CREATE TYPE allocation_type AS ENUM ('REGION','PROVIDER_RESERVED','TENANT_POOL','VCN','SUBNET'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
DO $$ BEGIN CREATE TYPE allocation_status AS ENUM ('PLANNED','ALLOCATED','IN_USE','RELEASED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
DO $$ BEGIN CREATE TYPE reservation_status AS ENUM ('RESERVED','IN_USE','RELEASED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$
```

---

## Permissions

| Permission Key | Tier | Description |
|-----------|------|-------------|
| `landingzone:zone:read` | Read-Only | View landing zones |
| `landingzone:zone:create` | Tenant Admin | Create landing zones |
| `landingzone:zone:update` | Tenant Admin | Edit landing zones |
| `landingzone:zone:delete` | Tenant Admin | Delete landing zones |
| `landingzone:zone:publish` | Provider Admin | Publish landing zones |
| `landingzone:region:manage` | Tenant Admin | Add/remove regions |
| `landingzone:tagpolicy:manage` | Provider Admin | Manage tag policies |
| `landingzone:template:read` | Read-Only | View environment templates |
| `landingzone:template:manage` | Provider Admin | Create/edit environment templates |
| `landingzone:environment:read` | Read-Only | View tenant environments |
| `landingzone:environment:create` | Tenant Admin | Create environments |
| `landingzone:environment:update` | Tenant Admin | Update environments |
| `landingzone:environment:decommission` | Tenant Admin | Decommission environments |
| `ipam:space:read` | Read-Only | View address spaces |
| `ipam:space:manage` | Tenant Admin | Create/edit address spaces |
| `ipam:allocation:read` | Read-Only | View allocations |
| `ipam:allocation:manage` | Tenant Admin | Allocate/release blocks |
| `ipam:reservation:read` | User | View IP reservations |
| `ipam:reservation:manage` | User | Reserve/release individual IPs |

**Role assignment SQL pattern:**
```sql
-- Provider Admin & Tenant Admin: all landingzone:* and ipam:* permissions
WHERE r.name IN ('Provider Admin', 'Tenant Admin')
  AND p.domain IN ('landingzone', 'ipam')

-- Provider Admin only: publish, tagpolicy:manage, template:manage
WHERE r.name = 'Provider Admin'
  AND ((p.domain = 'landingzone' AND p.action IN ('publish', 'manage') AND p.resource IN ('zone', 'tagpolicy', 'template'))

-- User: read permissions + ipam:reservation:*
WHERE r.name = 'User'
  AND ((p.domain IN ('landingzone', 'ipam') AND p.action = 'read')
       OR (p.domain = 'ipam' AND p.resource = 'reservation'))

-- Read-Only: all :read permissions
WHERE r.name = 'Read-Only'
  AND p.action = 'read'
  AND p.domain IN ('landingzone', 'ipam')
```

---

## Task Breakdown (20 tasks)

### 11.1: Migration — Landing Zone Tables + Permissions
**File**: `backend/alembic/versions/058_landing_zones.py`
**Revision**: `058` (next after 057)
**Down revision**: latest head

**Creates:**
1. Six enum types (see Enums section above)
2. Seven tables: `landing_zones`, `landing_zone_regions`, `landing_zone_tag_policies`, `environment_templates`, `tenant_environments`, `address_spaces`, `address_allocations`, `ip_reservations`
3. All indexes listed in the Data Model section
4. All partial unique constraints (WHERE deleted_at IS NULL)
5. Adds `is_landing_zone` Boolean column to `architecture_topologies` with default false
6. Inserts 19 permissions (see Permissions section)
7. Assigns permissions to roles using PascalCase role names: `'Provider Admin'`, `'Tenant Admin'`, `'User'`, `'Read-Only'`
8. Seeds 4 system environment templates (Development, Staging, Production, Disaster Recovery) — linked to all providers via a loop

**Downgrade:**
- Delete role_permissions WHERE permission domain IN ('landingzone', 'ipam')
- Delete permissions WHERE domain IN ('landingzone', 'ipam')
- Delete from environment_templates WHERE is_system = true
- Drop column `is_landing_zone` from `architecture_topologies`
- Drop all 8 tables in reverse order
- Drop all 6 enum types

### 11.2: Migration — Semantic Tenancy Types
**File**: `backend/alembic/versions/059_semantic_tenancy_types.py`
**Down revision**: `058`

**Creates:**
1. Insert `tenancy` category into `semantic_categories`
2. Insert `CloudTenancy`, `CloudCompartment`, `CloudRegion`, `AddressPool` into `semantic_resource_types`
3. Insert 13 provider resource type mappings into `semantic_provider_resource_types` + `semantic_type_mappings`
4. Insert 3 new relationship kinds: `hosts_in`/`hosted_by`, `peers_with`/`peers_with`, `allocates_from`/`allocated_to`

**Also updates `registry.py`:**
- Add `tenancy` to `CATEGORIES`
- Add 4 new types to `SEMANTIC_TYPES`
- Add 13 entries to `PROVIDER_RESOURCE_MAPPINGS`
- Add 3 entries to `RELATIONSHIP_KINDS`

**Downgrade:**
- Delete type_mappings, provider_resource_types, resource_types, relationship_kinds, category (in FK order)

### 11.3: SQLAlchemy Models — Landing Zones
**File**: `backend/app/models/landing_zone.py`

**Header:**
```
Overview: Landing zone models — provider landing zones with regions and tag policies.
Architecture: Landing zone data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Provider landing zones, multi-region, tag governance, topology reuse
```

**Models:**

```python
class LandingZone(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "landing_zones"

    tenant_id → tenants.id (NOT NULL, indexed)
    backend_id → cloud_backends.id (NOT NULL, indexed)
    topology_id → architecture_topologies.id (NOT NULL)
    cloud_tenancy_id → configuration_items.id (nullable)
    name: String(255)
    description: Text (nullable)
    status: Enum(LandingZoneStatus) default DRAFT
    version: Integer default 0
    settings: JSONB (nullable)
    created_by → users.id (NOT NULL)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(lazy="joined")
    backend: Mapped["CloudBackend"] = relationship(lazy="joined")
    topology: Mapped["ArchitectureTopology"] = relationship(lazy="joined")
    regions: Mapped[list["LandingZoneRegion"]] = relationship(back_populates="landing_zone", lazy="selectin")
    tag_policies: Mapped[list["LandingZoneTagPolicy"]] = relationship(back_populates="landing_zone", lazy="selectin")
    environments: Mapped[list["TenantEnvironment"]] = relationship(back_populates="landing_zone", lazy="selectin")
    address_spaces: Mapped[list["AddressSpace"]] = relationship(back_populates="landing_zone", lazy="selectin")

class LandingZoneRegion(Base, IDMixin, TimestampMixin):
    __tablename__ = "landing_zone_regions"
    landing_zone_id, region_identifier, display_name, is_primary, is_dr, settings
    landing_zone: Mapped["LandingZone"] = relationship(back_populates="regions")

class LandingZoneTagPolicy(Base, IDMixin, TimestampMixin):
    __tablename__ = "landing_zone_tag_policies"
    landing_zone_id, tag_key, display_name, description, is_required, allowed_values, default_value, inherited
    landing_zone: Mapped["LandingZone"] = relationship(back_populates="tag_policies")
```

**Register in `backend/app/models/__init__.py`:**
```python
from app.models.landing_zone import LandingZone, LandingZoneRegion, LandingZoneTagPolicy
# + add to __all__
```

### 11.4: SQLAlchemy Models — Environments
**File**: `backend/app/models/environment.py`

**Header:**
```
Overview: Environment models — templates and tenant environment instances.
Architecture: Tenant environment data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Environment templates, tenant environments, lifecycle management, tag inheritance
```

**Models:**
```python
class EnvironmentTemplate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "environment_templates"
    provider_id → providers.id, name, display_name, description, icon, color,
    default_tags (JSONB), default_policies (JSONB), sort_order, is_system
    provider: Mapped["Provider"] = relationship(lazy="joined")

class TenantEnvironment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenant_environments"
    tenant_id → tenants.id, landing_zone_id → landing_zones.id,
    template_id → environment_templates.id (nullable),
    name, display_name, description,
    status: Enum(EnvironmentStatus) default PLANNED,
    root_compartment_id → compartments.id (nullable),
    tags (JSONB), policies (JSONB), settings (JSONB),
    created_by → users.id
    tenant: Mapped["Tenant"] = relationship(lazy="joined")
    landing_zone: Mapped["LandingZone"] = relationship(back_populates="environments")
    template: Mapped["EnvironmentTemplate | None"] = relationship(lazy="joined")
    root_compartment: Mapped["Compartment | None"] = relationship(lazy="joined")
    allocations: Mapped[list["AddressAllocation"]] = relationship(back_populates="tenant_environment", lazy="selectin")
```

**Register in `__init__.py`.**

### 11.5: SQLAlchemy Models — IPAM
**File**: `backend/app/models/ipam.py`

**Header:**
```
Overview: IPAM models — address spaces, hierarchical allocations, IP reservations.
Architecture: IP address management data layer (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: CIDR hierarchy, address allocation, IP reservation, utilization tracking
```

**Models:**
```python
class AddressSpace(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "address_spaces"
    landing_zone_id → landing_zones.id, region_id → landing_zone_regions.id (nullable),
    name, description, cidr: String(43), ip_version: SmallInteger default 4,
    status: Enum(AddressSpaceStatus) default ACTIVE
    landing_zone: Mapped["LandingZone"] = relationship(back_populates="address_spaces")
    region: Mapped["LandingZoneRegion | None"] = relationship(lazy="joined")
    allocations: Mapped[list["AddressAllocation"]] = relationship(back_populates="address_space", lazy="selectin")

class AddressAllocation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "address_allocations"
    address_space_id → address_spaces.id,
    parent_allocation_id → address_allocations.id (nullable, self-referencing),
    tenant_environment_id → tenant_environments.id (nullable),
    name, description, cidr: String(43),
    allocation_type: Enum(AllocationType),
    status: Enum(AllocationStatus) default PLANNED,
    purpose: String(255) nullable, semantic_type_id → semantic_resource_types.id nullable,
    cloud_resource_id: String(500) nullable, utilization_percent: Float nullable,
    metadata: JSONB nullable
    address_space: Mapped["AddressSpace"] = relationship(back_populates="allocations")
    parent: Mapped["AddressAllocation | None"] = relationship(remote_side="AddressAllocation.id", back_populates="children")
    children: Mapped[list["AddressAllocation"]] = relationship(back_populates="parent")
    tenant_environment: Mapped["TenantEnvironment | None"] = relationship(back_populates="allocations")
    reservations: Mapped[list["IpReservation"]] = relationship(back_populates="allocation", lazy="selectin")

class IpReservation(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ip_reservations"
    allocation_id → address_allocations.id, ip_address: String(45),
    hostname: String(255) nullable, purpose: String(255),
    ci_id → configuration_items.id nullable,
    status: Enum(ReservationStatus) default RESERVED,
    reserved_by → users.id
    allocation: Mapped["AddressAllocation"] = relationship(back_populates="reservations")
```

**Register in `__init__.py`.**

### 11.6: IPAM Core Service
**File**: `backend/app/services/ipam/ipam_service.py`

**Header:**
```
Overview: IPAM service — address space management, CIDR allocation, IP reservation, utilization tracking.
Architecture: Core IPAM business logic (Section 5)
Dependencies: sqlalchemy, ipaddress, app.models.ipam, app.services.ipam.validation
Concepts: Hierarchical CIDR allocation, conflict detection, auto-suggestion, capacity planning
```

**Class: `IpamService(db: AsyncSession)`**

**Custom exception: `IpamError(message, code)`**

**Methods:**

```python
# Address Space CRUD
async def create_space(self, landing_zone_id: str, region_id: str | None, data: dict) -> AddressSpace
async def get_space(self, space_id: str) -> AddressSpace
async def list_spaces(self, landing_zone_id: str) -> list[AddressSpace]
async def delete_space(self, space_id: str) -> bool

# Allocation CRUD + smart allocation
async def allocate_block(
    self, space_id: str, parent_id: str | None,
    cidr: str, allocation_type: str, name: str,
    tenant_environment_id: str | None = None, **kwargs
) -> AddressAllocation
"""Validates CIDR containment within parent, checks for overlaps, creates allocation."""

async def release_block(self, allocation_id: str) -> bool
"""Sets status to RELEASED. Fails if has children that are not RELEASED."""

async def suggest_next_available(
    self, space_id: str, parent_id: str | None, prefix_length: int
) -> str | None
"""Finds the next available CIDR block of the requested size within the parent.
Uses Python ipaddress module to iterate subnets and find gaps."""

async def get_allocation_tree(self, space_id: str) -> list[AddressAllocation]
"""Returns flat list of allocations; parent_allocation_id builds the tree client-side."""

async def update_allocation(self, allocation_id: str, **kwargs) -> AddressAllocation

# Utilization
async def calculate_utilization(self, allocation_id: str) -> float
"""For SUBNET: count reserved IPs / total usable IPs.
For VCN/POOL: sum of child allocated space / total space."""

async def get_utilization_summary(self, landing_zone_id: str) -> dict
"""Aggregate utilization by region, by allocation_type."""

async def check_capacity(self, space_id: str, threshold: float = 80.0) -> list[dict]
"""Returns allocations above the threshold."""

# IP Reservation
async def reserve_ip(
    self, allocation_id: str, ip_address: str, purpose: str,
    reserved_by: str, hostname: str | None = None, ci_id: str | None = None
) -> IpReservation
"""Validates IP is within the SUBNET allocation's CIDR. Checks no duplicate."""

async def release_ip(self, reservation_id: str) -> bool
async def list_reservations(self, allocation_id: str) -> list[IpReservation]
async def search_ip(self, landing_zone_id: str, ip_address: str) -> dict | None
"""Search across all spaces/allocations to find which allocation/reservation contains this IP."""

async def update_reservation(self, reservation_id: str, **kwargs) -> IpReservation
```

### 11.7: IPAM Validation Service
**File**: `backend/app/services/ipam/validation.py`

**Header:**
```
Overview: IPAM validation — CIDR overlap detection, containment checking, boundary validation.
Architecture: IPAM validation layer (Section 5)
Dependencies: ipaddress (stdlib)
Concepts: CIDR arithmetic, overlap detection, RFC 1918 validation, subnet boundaries
```

**Pure functions (no DB dependency):**

```python
import ipaddress

def validate_cidr(cidr: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    """Parse and validate CIDR notation. Raises ValueError on invalid input."""

def is_contained_in(child_cidr: str, parent_cidr: str) -> bool:
    """Check if child is entirely within parent."""

def overlaps_with(cidr_a: str, cidr_b: str) -> bool:
    """Check if two CIDRs overlap."""

def find_overlaps(new_cidr: str, existing_cidrs: list[str]) -> list[str]:
    """Return all existing CIDRs that overlap with new_cidr."""

def validate_subnet_boundary(cidr: str) -> bool:
    """Check CIDR is on a proper network boundary (e.g., 10.0.0.0/24 not 10.0.0.1/24)."""

def is_private_range(cidr: str) -> bool:
    """Check if CIDR falls within RFC 1918 (IPv4) or RFC 4193 (IPv6) private ranges."""

def calculate_usable_ips(cidr: str) -> int:
    """Total usable IPs in a CIDR (excludes network and broadcast for IPv4)."""

def next_available_block(
    parent_cidr: str,
    existing_children: list[str],
    prefix_length: int,
) -> str | None:
    """Find next available CIDR of given prefix_length within parent that doesn't overlap existing."""

def ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP address falls within a CIDR block."""
```

### 11.8: Landing Zone Service
**File**: `backend/app/services/landing_zone/landing_zone_service.py`

**Header:**
```
Overview: Landing zone service — CRUD, publish lifecycle, clone, validation, capacity summary.
Architecture: Landing zone business logic (Section 5)
Dependencies: sqlalchemy, app.models.landing_zone, app.services.architecture.topology_service
Concepts: Landing zone lifecycle, approval integration, topology reuse, audit trail
```

**Class: `LandingZoneService(db: AsyncSession)`**

**Custom exception: `LandingZoneError(message, code)`**

**Methods:**

```python
async def create(self, tenant_id: str, created_by: str, data: dict) -> LandingZone:
    """Create a draft LZ. Also creates a new topology with is_landing_zone=True.
    data: {name, description, backend_id, settings}"""

async def get(self, lz_id: str, tenant_id: str) -> LandingZone
async def list(self, tenant_id: str, status: str | None = None,
               backend_id: str | None = None, offset: int = 0, limit: int = 50) -> list[LandingZone]
async def update(self, lz_id: str, tenant_id: str, data: dict) -> LandingZone
    """Only DRAFT status. Updates name, description, settings. Topology updated separately."""
async def delete(self, lz_id: str, tenant_id: str) -> bool

async def publish(self, lz_id: str, tenant_id: str, user_id: str) -> LandingZone:
    """Validate topology (via TopologyService.validate_graph), validate IPAM consistency,
    check approval policy, transition to PUBLISHED or create approval request."""

async def archive(self, lz_id: str, tenant_id: str) -> LandingZone
async def clone(self, lz_id: str, tenant_id: str, created_by: str, new_name: str) -> LandingZone:
    """Deep clone: creates new topology clone, copies regions, tag_policies, address_spaces."""

async def validate(self, lz_id: str) -> dict:
    """Full validation: {topology_valid: bool, ipam_valid: bool, errors: [...]}"""

async def get_available_capacity(self, lz_id: str) -> dict:
    """Per-region summary: {region_id: {total_ips, allocated_ips, available_ips, utilization_pct}}"""

# Private
async def _audit(self, tenant_id, user_id, action, resource)
```

### 11.9: Landing Zone Region & Tag Policy Services
**File**: `backend/app/services/landing_zone/region_service.py`

**Class: `RegionService(db: AsyncSession)`**

```python
async def add_region(self, lz_id: str, data: dict) -> LandingZoneRegion
async def update_region(self, region_id: str, data: dict) -> LandingZoneRegion
async def remove_region(self, region_id: str) -> bool
async def list_regions(self, lz_id: str) -> list[LandingZoneRegion]
async def set_primary(self, lz_id: str, region_id: str) -> LandingZoneRegion
    """Sets is_primary=True for this region, false for all others in the LZ."""
```

**File**: `backend/app/services/landing_zone/tag_policy_service.py`

**Class: `TagPolicyService(db: AsyncSession)`**

```python
async def add_policy(self, lz_id: str, data: dict) -> LandingZoneTagPolicy
async def update_policy(self, policy_id: str, data: dict) -> LandingZoneTagPolicy
async def remove_policy(self, policy_id: str) -> bool
async def list_policies(self, lz_id: str) -> list[LandingZoneTagPolicy]
async def compute_effective_tags(self, lz_id: str, template_id: str | None, overrides: dict) -> dict:
    """Merge: LZ tag defaults → template defaults → tenant overrides. Validates required tags."""
async def validate_tags(self, lz_id: str, tags: dict) -> list[str]:
    """Returns list of validation errors (missing required, invalid values)."""
```

### 11.10: Environment Template Service
**File**: `backend/app/services/landing_zone/environment_template_service.py`

**Class: `EnvironmentTemplateService(db: AsyncSession)`**

```python
async def create(self, provider_id: str, data: dict) -> EnvironmentTemplate
async def update(self, template_id: str, data: dict) -> EnvironmentTemplate
async def delete(self, template_id: str) -> bool
async def get(self, template_id: str) -> EnvironmentTemplate
async def list(self, provider_id: str) -> list[EnvironmentTemplate]
```

### 11.11: Tenant Environment Service
**File**: `backend/app/services/landing_zone/tenant_environment_service.py`

**Class: `TenantEnvironmentService(db: AsyncSession)`**

**Custom exception: `EnvironmentError(message, code)`**

```python
async def create_from_template(
    self, tenant_id: str, lz_id: str, template_id: str,
    created_by: str, overrides: dict | None = None,
) -> TenantEnvironment:
    """1. Load template defaults
    2. Merge overrides (tags, policies, settings)
    3. Compute effective tags via TagPolicyService
    4. Auto-allocate VCN CIDR from tenant pool via IpamService.suggest_next_available
    5. Create root compartment in provider's tenant zone
    6. Create TenantEnvironment record
    7. Audit log + notification"""

async def create_custom(
    self, tenant_id: str, lz_id: str, created_by: str, data: dict,
) -> TenantEnvironment:
    """Same flow but no template — all config provided directly."""

async def get(self, env_id: str, tenant_id: str) -> TenantEnvironment
async def list(self, tenant_id: str, lz_id: str | None = None,
               status: str | None = None) -> list[TenantEnvironment]
async def update(self, env_id: str, tenant_id: str, data: dict) -> TenantEnvironment

async def transition_status(
    self, env_id: str, tenant_id: str, new_status: str, user_id: str,
) -> TenantEnvironment:
    """Validate status transition. Allowed transitions:
    PLANNED → PROVISIONING → ACTIVE
    ACTIVE → SUSPENDED → ACTIVE (resume)
    ACTIVE → DECOMMISSIONING → DECOMMISSIONED
    Audit logs every transition."""

async def decommission(self, env_id: str, tenant_id: str, user_id: str) -> TenantEnvironment:
    """Release all IPAM allocations, transition to DECOMMISSIONING."""
```

### 11.12: GraphQL Types — Landing Zones & IPAM
**File**: `backend/app/api/graphql/types/landing_zone.py`

```python
@strawberry.enum
class LandingZoneStatusGQL(Enum): DRAFT, PUBLISHED, ARCHIVED

@strawberry.enum
class EnvironmentStatusGQL(Enum): PLANNED, PROVISIONING, ACTIVE, SUSPENDED, DECOMMISSIONING, DECOMMISSIONED

@strawberry.enum
class AddressSpaceStatusGQL(Enum): ACTIVE, EXHAUSTED, RESERVED

@strawberry.enum
class AllocationTypeGQL(Enum): REGION, PROVIDER_RESERVED, TENANT_POOL, VCN, SUBNET

@strawberry.enum
class AllocationStatusGQL(Enum): PLANNED, ALLOCATED, IN_USE, RELEASED

@strawberry.enum
class ReservationStatusGQL(Enum): RESERVED, IN_USE, RELEASED

@strawberry.type
class LandingZoneType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    backend_id: uuid.UUID
    topology_id: uuid.UUID
    cloud_tenancy_id: uuid.UUID | None
    name: str
    description: str | None
    status: LandingZoneStatusGQL
    version: int
    settings: strawberry.scalars.JSON | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    regions: list[LandingZoneRegionType]
    tag_policies: list[TagPolicyType]

@strawberry.type
class LandingZoneRegionType:
    id: uuid.UUID
    landing_zone_id: uuid.UUID
    region_identifier: str
    display_name: str
    is_primary: bool
    is_dr: bool
    settings: strawberry.scalars.JSON | None

@strawberry.type
class TagPolicyType:
    id: uuid.UUID
    tag_key: str
    display_name: str
    description: str | None
    is_required: bool
    allowed_values: strawberry.scalars.JSON | None
    default_value: str | None
    inherited: bool

@strawberry.type
class EnvironmentTemplateType:
    id: uuid.UUID
    provider_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    icon: str | None
    color: str | None
    default_tags: strawberry.scalars.JSON | None
    default_policies: strawberry.scalars.JSON | None
    sort_order: int
    is_system: bool

@strawberry.type
class TenantEnvironmentType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    landing_zone_id: uuid.UUID
    template_id: uuid.UUID | None
    name: str
    display_name: str
    description: str | None
    status: EnvironmentStatusGQL
    root_compartment_id: uuid.UUID | None
    tags: strawberry.scalars.JSON
    policies: strawberry.scalars.JSON
    settings: strawberry.scalars.JSON | None
    created_by: uuid.UUID
    created_at: datetime

@strawberry.type
class AddressSpaceType:
    id: uuid.UUID
    landing_zone_id: uuid.UUID
    region_id: uuid.UUID | None
    name: str
    description: str | None
    cidr: str
    ip_version: int
    status: AddressSpaceStatusGQL

@strawberry.type
class AddressAllocationType:
    id: uuid.UUID
    address_space_id: uuid.UUID
    parent_allocation_id: uuid.UUID | None
    tenant_environment_id: uuid.UUID | None
    name: str
    description: str | None
    cidr: str
    allocation_type: AllocationTypeGQL
    status: AllocationStatusGQL
    purpose: str | None
    semantic_type_id: uuid.UUID | None
    cloud_resource_id: str | None
    utilization_percent: float | None
    metadata: strawberry.scalars.JSON | None

@strawberry.type
class IpReservationType:
    id: uuid.UUID
    allocation_id: uuid.UUID
    ip_address: str
    hostname: str | None
    purpose: str
    ci_id: uuid.UUID | None
    status: ReservationStatusGQL
    reserved_by: uuid.UUID

@strawberry.type
class IpamUtilizationType:
    """Summary stats for a landing zone or address space."""
    total_ips: int
    allocated_ips: int
    available_ips: int
    utilization_percent: float
    exhaustion_warnings: list[str]

# Input types
@strawberry.input class LandingZoneCreateInput: name, description, backend_id, settings
@strawberry.input class LandingZoneUpdateInput: name, description, settings (all optional)
@strawberry.input class RegionInput: region_identifier, display_name, is_primary, is_dr, settings
@strawberry.input class TagPolicyInput: tag_key, display_name, description, is_required, allowed_values, default_value, inherited
@strawberry.input class EnvironmentTemplateInput: name, display_name, description, icon, color, default_tags, default_policies, sort_order
@strawberry.input class EnvironmentCreateInput: landing_zone_id, template_id (opt), name, display_name, description, tag_overrides, policy_overrides, settings
@strawberry.input class AddressSpaceInput: name, description, cidr, ip_version, region_id
@strawberry.input class AllocationInput: space_id, parent_id (opt), cidr, allocation_type, name, purpose, tenant_environment_id
@strawberry.input class IpReservationInput: allocation_id, ip_address, purpose, hostname
```

**File**: `backend/app/api/graphql/types/ipam.py` — Not separate. All types above go in `types/landing_zone.py` to keep the module cohesive.

### 11.13: GraphQL Queries
**File**: `backend/app/api/graphql/queries/landing_zone.py`

```python
@strawberry.type
class LandingZoneQuery:

    @strawberry.field
    async def landing_zones(info, tenant_id: UUID, status: str | None = None,
                            backend_id: UUID | None = None, offset: int = 0,
                            limit: int = 50) -> list[LandingZoneType]:
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))
        # → LandingZoneService.list()

    @strawberry.field
    async def landing_zone(info, tenant_id: UUID, lz_id: UUID) -> LandingZoneType | None:
        await check_graphql_permission(info, "landingzone:zone:read", str(tenant_id))
        # → LandingZoneService.get()

    @strawberry.field
    async def environment_templates(info, provider_id: UUID) -> list[EnvironmentTemplateType]:
        # Provider-scoped, no tenant permission needed (read-only seed data)
        # → EnvironmentTemplateService.list()

    @strawberry.field
    async def tenant_environments(info, tenant_id: UUID, lz_id: UUID | None = None,
                                   status: str | None = None) -> list[TenantEnvironmentType]:
        await check_graphql_permission(info, "landingzone:environment:read", str(tenant_id))
        # → TenantEnvironmentService.list()

    @strawberry.field
    async def tenant_environment(info, tenant_id: UUID, env_id: UUID) -> TenantEnvironmentType | None:
        await check_graphql_permission(info, "landingzone:environment:read", str(tenant_id))
        # → TenantEnvironmentService.get()

    @strawberry.field
    async def address_spaces(info, tenant_id: UUID, lz_id: UUID) -> list[AddressSpaceType]:
        await check_graphql_permission(info, "ipam:space:read", str(tenant_id))
        # → IpamService.list_spaces()

    @strawberry.field
    async def address_allocation_tree(info, tenant_id: UUID, space_id: UUID) -> list[AddressAllocationType]:
        await check_graphql_permission(info, "ipam:allocation:read", str(tenant_id))
        # → IpamService.get_allocation_tree()

    @strawberry.field
    async def ip_reservations(info, tenant_id: UUID, allocation_id: UUID) -> list[IpReservationType]:
        await check_graphql_permission(info, "ipam:reservation:read", str(tenant_id))
        # → IpamService.list_reservations()

    @strawberry.field
    async def ipam_utilization(info, tenant_id: UUID, lz_id: UUID) -> IpamUtilizationType:
        await check_graphql_permission(info, "ipam:space:read", str(tenant_id))
        # → IpamService.get_utilization_summary()

    @strawberry.field
    async def search_ip(info, tenant_id: UUID, lz_id: UUID, ip_address: str) -> strawberry.scalars.JSON | None:
        await check_graphql_permission(info, "ipam:reservation:read", str(tenant_id))
        # → IpamService.search_ip()

    @strawberry.field
    async def suggest_next_cidr(info, tenant_id: UUID, space_id: UUID,
                                 parent_id: UUID | None, prefix_length: int) -> str | None:
        await check_graphql_permission(info, "ipam:allocation:manage", str(tenant_id))
        # → IpamService.suggest_next_available()
```

### 11.14: GraphQL Mutations
**File**: `backend/app/api/graphql/mutations/landing_zone.py`

```python
@strawberry.type
class LandingZoneMutation:

    # Landing Zone CRUD
    @strawberry.mutation
    async def create_landing_zone(info, tenant_id: UUID, input: LandingZoneCreateInput) -> LandingZoneType
    @strawberry.mutation
    async def update_landing_zone(info, tenant_id: UUID, lz_id: UUID, input: LandingZoneUpdateInput) -> LandingZoneType
    @strawberry.mutation
    async def delete_landing_zone(info, tenant_id: UUID, lz_id: UUID) -> bool
    @strawberry.mutation
    async def publish_landing_zone(info, tenant_id: UUID, lz_id: UUID) -> LandingZoneType
    @strawberry.mutation
    async def archive_landing_zone(info, tenant_id: UUID, lz_id: UUID) -> LandingZoneType
    @strawberry.mutation
    async def clone_landing_zone(info, tenant_id: UUID, lz_id: UUID, new_name: str) -> LandingZoneType

    # Regions
    @strawberry.mutation
    async def add_landing_zone_region(info, tenant_id: UUID, lz_id: UUID, input: RegionInput) -> LandingZoneRegionType
    @strawberry.mutation
    async def update_landing_zone_region(info, tenant_id: UUID, region_id: UUID, input: RegionInput) -> LandingZoneRegionType
    @strawberry.mutation
    async def remove_landing_zone_region(info, tenant_id: UUID, region_id: UUID) -> bool

    # Tag Policies
    @strawberry.mutation
    async def add_tag_policy(info, tenant_id: UUID, lz_id: UUID, input: TagPolicyInput) -> TagPolicyType
    @strawberry.mutation
    async def update_tag_policy(info, tenant_id: UUID, policy_id: UUID, input: TagPolicyInput) -> TagPolicyType
    @strawberry.mutation
    async def remove_tag_policy(info, tenant_id: UUID, policy_id: UUID) -> bool

    # Environment Templates (provider-scoped)
    @strawberry.mutation
    async def create_environment_template(info, provider_id: UUID, input: EnvironmentTemplateInput) -> EnvironmentTemplateType
    @strawberry.mutation
    async def update_environment_template(info, template_id: UUID, input: EnvironmentTemplateInput) -> EnvironmentTemplateType
    @strawberry.mutation
    async def delete_environment_template(info, template_id: UUID) -> bool

    # Tenant Environments
    @strawberry.mutation
    async def create_tenant_environment(info, tenant_id: UUID, input: EnvironmentCreateInput) -> TenantEnvironmentType
    @strawberry.mutation
    async def update_tenant_environment(info, tenant_id: UUID, env_id: UUID, tags: JSON, policies: JSON, settings: JSON) -> TenantEnvironmentType
    @strawberry.mutation
    async def transition_environment_status(info, tenant_id: UUID, env_id: UUID, new_status: str) -> TenantEnvironmentType
    @strawberry.mutation
    async def decommission_environment(info, tenant_id: UUID, env_id: UUID) -> TenantEnvironmentType

    # IPAM - Address Spaces
    @strawberry.mutation
    async def create_address_space(info, tenant_id: UUID, lz_id: UUID, input: AddressSpaceInput) -> AddressSpaceType
    @strawberry.mutation
    async def delete_address_space(info, tenant_id: UUID, space_id: UUID) -> bool

    # IPAM - Allocations
    @strawberry.mutation
    async def allocate_block(info, tenant_id: UUID, input: AllocationInput) -> AddressAllocationType
    @strawberry.mutation
    async def release_block(info, tenant_id: UUID, allocation_id: UUID) -> bool
    @strawberry.mutation
    async def update_allocation(info, tenant_id: UUID, allocation_id: UUID, name: str | None, purpose: str | None, metadata: JSON | None) -> AddressAllocationType

    # IPAM - IP Reservations
    @strawberry.mutation
    async def reserve_ip(info, tenant_id: UUID, input: IpReservationInput) -> IpReservationType
    @strawberry.mutation
    async def release_ip(info, tenant_id: UUID, reservation_id: UUID) -> bool
    @strawberry.mutation
    async def update_ip_reservation(info, tenant_id: UUID, reservation_id: UUID, hostname: str | None, purpose: str | None) -> IpReservationType
```

### 11.15: GraphQL Schema Registration
**File**: `backend/app/api/graphql/schema.py`

Add to imports:
```python
from app.api.graphql.queries.landing_zone import LandingZoneQuery
from app.api.graphql.mutations.landing_zone import LandingZoneMutation
```

Add `LandingZoneQuery` to the `Query` class bases.
Add `LandingZoneMutation` to the `Mutation` class bases.

### 11.16: Frontend — Angular Service + Models
**File**: `frontend/src/app/shared/models/landing-zone.model.ts`

TypeScript interfaces:
```typescript
export interface LandingZone { id, tenantId, backendId, topologyId, cloudTenancyId?, name, description?, status, version, settings?, createdBy, createdAt, updatedAt, regions, tagPolicies }
export interface LandingZoneRegion { id, landingZoneId, regionIdentifier, displayName, isPrimary, isDr, settings? }
export interface TagPolicy { id, tagKey, displayName, description?, isRequired, allowedValues?, defaultValue?, inherited }
export interface EnvironmentTemplate { id, providerId, name, displayName, description?, icon?, color?, defaultTags?, defaultPolicies?, sortOrder, isSystem }
export interface TenantEnvironment { id, tenantId, landingZoneId, templateId?, name, displayName, description?, status, rootCompartmentId?, tags, policies, settings?, createdBy, createdAt }
export interface AddressSpace { id, landingZoneId, regionId?, name, description?, cidr, ipVersion, status }
export interface AddressAllocation { id, addressSpaceId, parentAllocationId?, tenantEnvironmentId?, name, description?, cidr, allocationType, status, purpose?, semanticTypeId?, cloudResourceId?, utilizationPercent?, metadata? }
export interface IpReservation { id, allocationId, ipAddress, hostname?, purpose, ciId?, status, reservedBy }
export interface IpamUtilization { totalIps, allocatedIps, availableIps, utilizationPercent, exhaustionWarnings }
```

**File**: `frontend/src/app/core/services/landing-zone.service.ts`

Angular service with `private gql<T>()` helper pattern (like ArchitectureService):
- `listLandingZones(filters?)`, `getLandingZone(id)`, `createLandingZone(input)`, `updateLandingZone(id, input)`, `deleteLandingZone(id)`, `publishLandingZone(id)`, `archiveLandingZone(id)`, `cloneLandingZone(id, name)`
- `addRegion(lzId, input)`, `updateRegion(regionId, input)`, `removeRegion(regionId)`
- `addTagPolicy(lzId, input)`, `updateTagPolicy(policyId, input)`, `removeTagPolicy(policyId)`
- `listEnvironmentTemplates(providerId)`, `createEnvironmentTemplate(input)`, `updateEnvironmentTemplate(id, input)`, `deleteEnvironmentTemplate(id)`
- `listTenantEnvironments(filters?)`, `getTenantEnvironment(id)`, `createTenantEnvironment(input)`, `updateTenantEnvironment(id, data)`, `transitionEnvironmentStatus(id, status)`, `decommissionEnvironment(id)`
- `listAddressSpaces(lzId)`, `createAddressSpace(lzId, input)`, `deleteAddressSpace(id)`
- `getAllocationTree(spaceId)`, `allocateBlock(input)`, `releaseBlock(id)`, `suggestNextCidr(spaceId, parentId, prefixLength)`
- `listReservations(allocationId)`, `reserveIp(input)`, `releaseIp(id)`
- `getIpamUtilization(lzId)`, `searchIp(lzId, ipAddress)`

### 11.17: Frontend — Landing Zone List & Detail
**Files**: `frontend/src/app/features/landing-zones/`

**`landing-zone-list.component.ts`**
- Page wrapped in `<nimbus-layout>`
- Page header: "Landing Zones" + "New Landing Zone" primary button
- Status filter tabs: All | Draft | Published | Archived
- Cloud backend dropdown filter
- Table: Name (link to detail), Backend, Status badge, Regions count, Version, Created date, Actions (Edit, Clone, Delete)
- Light theme: #fff table container, #fafbfc header row, #e2e8f0 borders

**`landing-zone-detail.component.ts`**
- Header: LZ name + status badge + actions (Edit, Publish, Archive, Clone)
- Tabs: Overview | Regions | Tag Policies | IPAM | Environments
- **Overview tab**: Backend info, topology preview (mini Rete canvas readonly), settings JSON viewer
- **Regions tab**: Table of regions with primary/DR badges, add/edit/remove buttons
- **Tag Policies tab**: Table with tag_key, required badge, allowed values chips, add/edit/remove
- **IPAM tab**: Embedded IpamDashboard component (task 11.19)
- **Environments tab**: List of tenant environments using this LZ, with status and allocation info

### 11.18: Frontend — Landing Zone Editor (Topology Integration)
**Files**: `frontend/src/app/features/landing-zones/editor/landing-zone-editor.component.ts`

This component wraps the existing architecture editor with landing zone constraints:

1. **Reuses `ArchitectureEditorService`** — calls `setSemanticTypes()` with filtered types
2. **Palette restriction**: Passes only tenancy + network + security category types to `ComponentPaletteComponent`
   - Allowed categories: `tenancy`, `network`, `security`
   - Blocks: `compute`, `storage`, `database`, `monitoring`, `application`, `services`
3. **Hides Stacks section** in palette (no blueprints in LZ mode)
4. **Adds CIDR input fields** to the properties panel for VirtualNetwork and Subnet nodes
   - Inline CIDR validation using the same logic from `validation.py` (ported to TS or via API call)
5. **Region containers**: Uses compartment nodes with `CloudRegion` semantic type
6. **Cross-region peering**: Uses `peers_with` relationship kind for connections between region nodes
7. **Sidebar panels**: Region manager, Tag policy manager, Address space manager
8. Route: `/landing-zones/new` (create), `/landing-zones/:id/editor` (edit)

**Palette filtering approach** — add `@Input() mode: 'full' | 'landing_zone'` to `ComponentPaletteComponent`:
```typescript
// In component-palette.component.ts, modify filteredTypes computed:
const LANDING_ZONE_CATEGORIES = new Set(['Tenancy', 'Network', 'Security']);

filteredTypes = computed(() => {
  let types = this._types().filter(t => !t.isAbstract);
  if (this.mode === 'landing_zone') {
    types = types.filter(t => LANDING_ZONE_CATEGORIES.has((t as any).category?.displayName));
  }
  // ... existing search filter
});
```

### 11.19: Frontend — IPAM Dashboard
**Files**: `frontend/src/app/features/landing-zones/ipam/`

**`ipam-dashboard.component.ts`**
- **Summary cards**: Total IPs, Allocated, Available, Utilization % (with color: green <60%, yellow 60-80%, red >80%)
- **Address Space list**: Cards per space with CIDR, region, status, utilization bar
- Click on space → drill into allocation tree

**`allocation-tree.component.ts`**
- **Hierarchical tree view** of allocations within a space
- Indented rows: REGION → PROVIDER_RESERVED / TENANT_POOL → VCN → SUBNET
- Each row: name, CIDR, type badge, status badge, utilization bar, purpose
- Color-coded: provider_reserved=blue, tenant_pool=green, vcn=purple, subnet=gray
- Actions: Allocate sub-block, Release, View reservations

**`subnet-detail.component.ts`**
- Shows individual subnet: CIDR, usable IPs, reserved count, DHCP pool
- Table of IP reservations: IP, hostname, purpose, CI link, status, actions
- "Reserve IP" button with form: IP address (with auto-suggest), purpose, hostname

**`ip-search.component.ts`**
- Search bar: type IP address → shows which space/allocation/reservation contains it
- Results: breadcrumb trail (Space → Region Alloc → Tenant Pool → VCN → Subnet → Reserved IP)

Route: `/landing-zones/:id/ipam`

### 11.20: Frontend — Environment Manager & Template Admin
**Files**: `frontend/src/app/features/landing-zones/environments/`

**`environment-list.component.ts`**
- Table: Environment name, Landing Zone, Template (or "Custom"), Status badge, Tags count, Actions
- Filter by: LZ, status, template
- Route: `/environments`

**`environment-create.component.ts`**
- **Step wizard** (4 steps):
  1. **Select Landing Zone**: Dropdown of published LZs, shows backend + regions info
  2. **Choose Template**: Cards for each template (icon, color, name, description) + "Custom" option
  3. **Configure**: Name, display name, description, tag overrides (pre-filled from template), policy overrides
  4. **Review & Create**: Summary with auto-allocated CIDR preview (calls `suggestNextCidr`)
- Route: `/environments/new`

**`environment-detail.component.ts`**
- Header: Env name + status badge + lifecycle actions (Provision, Suspend, Resume, Decommission)
- Tabs: Overview | Tags | Network | Resources
- **Overview**: Template info, LZ info, root compartment, settings
- **Tags**: Effective tags table (source: template/override/inherited)
- **Network**: IPAM allocations for this environment (VCNs + subnets)
- **Resources**: CIs deployed in this environment (links to CMDB)
- Route: `/environments/:id`

**Files**: `frontend/src/app/features/settings/environment-templates/`

**`template-list.component.ts`**
- Provider-admin only
- Table: Name, Icon+Color swatch, Tags count, Sort order, System badge, Actions
- "New Template" button

**`template-editor.component.ts`**
- Form: name, display_name, description, icon picker, color picker (7-char hex), sort_order
- Tag defaults editor: key-value pairs
- Policy defaults editor: JSON editor or structured form (max_vcns, min_subnet_size, required_tags)
- Route: `/settings/environment-templates`, `/settings/environment-templates/:id`

---

## Frontend Routes (added to `app.routes.ts`)

```typescript
{
  path: 'landing-zones',
  canActivate: [authGuard],
  children: [
    { path: '', loadComponent: () => import('./features/landing-zones/landing-zone-list.component').then(m => m.LandingZoneListComponent),
      canActivate: [permissionGuard('landingzone:zone:read')], data: { breadcrumb: 'Landing Zones' } },
    { path: 'new', loadComponent: () => import('./features/landing-zones/editor/landing-zone-editor.component').then(m => m.LandingZoneEditorComponent),
      canActivate: [permissionGuard('landingzone:zone:create')], data: { breadcrumb: [{ label: 'Landing Zones', path: '/landing-zones' }, 'New'] } },
    { path: ':id', loadComponent: () => import('./features/landing-zones/landing-zone-detail.component').then(m => m.LandingZoneDetailComponent),
      canActivate: [permissionGuard('landingzone:zone:read')], data: { breadcrumb: [{ label: 'Landing Zones', path: '/landing-zones' }, 'Details'] } },
    { path: ':id/editor', loadComponent: () => import('./features/landing-zones/editor/landing-zone-editor.component').then(m => m.LandingZoneEditorComponent),
      canActivate: [permissionGuard('landingzone:zone:update')], data: { breadcrumb: [{ label: 'Landing Zones', path: '/landing-zones' }, 'Editor'] } },
    { path: ':id/ipam', loadComponent: () => import('./features/landing-zones/ipam/ipam-dashboard.component').then(m => m.IpamDashboardComponent),
      canActivate: [permissionGuard('ipam:space:read')], data: { breadcrumb: [{ label: 'Landing Zones', path: '/landing-zones' }, 'IPAM'] } },
  ],
},
{
  path: 'environments',
  canActivate: [authGuard],
  children: [
    { path: '', loadComponent: () => import('./features/landing-zones/environments/environment-list.component').then(m => m.EnvironmentListComponent),
      canActivate: [permissionGuard('landingzone:environment:read')], data: { breadcrumb: 'Environments' } },
    { path: 'new', loadComponent: () => import('./features/landing-zones/environments/environment-create.component').then(m => m.EnvironmentCreateComponent),
      canActivate: [permissionGuard('landingzone:environment:create')], data: { breadcrumb: [{ label: 'Environments', path: '/environments' }, 'New'] } },
    { path: ':id', loadComponent: () => import('./features/landing-zones/environments/environment-detail.component').then(m => m.EnvironmentDetailComponent),
      canActivate: [permissionGuard('landingzone:environment:read')], data: { breadcrumb: [{ label: 'Environments', path: '/environments' }, 'Details'] } },
  ],
},
```

Settings routes (nested under existing settings path):
```typescript
{ path: 'environment-templates', loadComponent: () => import('./features/settings/environment-templates/template-list.component').then(m => m.TemplateListComponent),
  canActivate: [permissionGuard('landingzone:template:read')], data: { breadcrumb: 'Environment Templates' } },
{ path: 'environment-templates/:id', loadComponent: () => import('./features/settings/environment-templates/template-editor.component').then(m => m.TemplateEditorComponent),
  canActivate: [permissionGuard('landingzone:template:manage')], data: { breadcrumb: [{ label: 'Environment Templates', path: '/settings/environment-templates' }, 'Edit'] } },
```

---

## Sidebar Integration

Add to `allNavGroups` in `sidebar.component.ts`:

```typescript
{
  label: 'Landing Zones', icon: '&#9730;', permission: 'landingzone:zone:read',
  children: [
    { label: 'Landing Zones', route: '/landing-zones', exact: true, permission: 'landingzone:zone:read' },
    { label: 'Environments', route: '/environments', exact: true, permission: 'landingzone:environment:read' },
  ],
},
```

Insert after the "Architecture" nav group.

Add to Settings children:
```typescript
{ label: 'Env Templates', route: '/settings/environment-templates', permission: 'landingzone:template:read', rootOnly: true },
```

---

## Impact on Other Phases

| Phase | Impact |
|-------|--------|
| Phase 5 (Semantic Layer) | New `Tenancy` category + 4 semantic types + 13 provider mappings + 3 relationship kinds |
| Phase 7 (Visual Planner) | Topology engine reused; `is_landing_zone` flag restricts palette |
| Phase 8 (CMDB) | Compartments linked to tenant environments; CIs scoped to environments |
| Phase 12 (Proxmox, renumbered) | Proxmox pools mapped to CloudCompartment, datacenter to CloudTenancy |
| Phase 13 (Pulumi, renumbered) | Stacks deploy INTO tenant environments; IPAM provides network config |
| Phase 17 (Drift, renumbered) | Drift detection scoped per landing zone / environment |
| Phase 19 (Cost, renumbered) | Cost allocation per environment using LZ tags |

---

## Phase Renumbering Impact

| Old Phase | New Phase | Name |
|-----------|-----------|------|
| 11 | **11 (NEW)** | **Landing Zones & IPAM** |
| 11 | 12 | Cloud Provider Integration (Proxmox) |
| 12 | 13 | Pulumi Integration |
| 13 | 14 | Real-time & Caching (Valkey) |
| 14 | 15 | Advanced Audit |
| 15 | 16 | MFA & HSM + JIT |
| 16 | 17 | Impersonation |
| 17 | 18 | Drift Detection |
| 18 | 19 | Additional Cloud Providers |
| 19 | 20 | Cost Management |
| 20 | 21 | Monitoring & Observability |
| 21 | 22 | Production Hardening |
| 22 | 23 | Enterprise Architecture Management |
