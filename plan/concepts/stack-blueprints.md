# Stack Blueprints — PaaS-Grade Infrastructure Compositions

## Problem Statement

Today, Components are individual IaC scripts targeting a single provider + semantic type (e.g., "Proxmox VM", "AWS RDS Instance"). Real infrastructure is never a single resource — it's a **composition**: a WordPress stack is a VM + database + load balancer + DNS + storage + firewall rules, all wired together with specific parameter flows.

We need a layer above Components that defines **reusable, versioned, composable infrastructure offerings** — essentially PaaS products that operators publish and tenants consume.

## Core Concepts

### Stack Blueprint

A **Stack Blueprint** is a versioned composition of Components that together form a deployable platform offering. Think: "Database as a Service", "Kubernetes Cluster", "WordPress Hosting", "Disaster Recovery Site".

```
Stack Blueprint "PostgreSQL HA Cluster"
├── Component: Primary DB (Proxmox VM)
├── Component: Replica DB (Proxmox VM)
├── Component: PgBouncer (Proxmox LXC)
├── Component: Shared Storage (Ceph Volume)
├── Component: Private Network (VLAN)
└── Component: Monitoring Agent

Input Variables:        Output Variables:
  cluster_name            primary_endpoint
  db_version              replica_endpoint
  storage_size_gb         pgbouncer_endpoint
  replica_count           monitoring_dashboard_url
  environment             connection_string
  backup_schedule         admin_credentials_secret
```

Each component in the blueprint has its own parameters, but the blueprint **wires** its top-level input variables into component parameters and **collects** component outputs into blueprint-level outputs.

### Relationship to Existing Entities

```
Stack Blueprint (NEW — composition layer)
  ├── uses → Component (existing — single IaC script per provider+type)
  │           └── has → Activities (existing — CRUD operations)
  ├── defines → Stack Input/Output Variables (NEW)
  ├── binds → Stack Workflows (NEW — DR, HA, scaling)
  ├── reserves → Capacity Reservations (NEW — DR standby)
  └── deploys as → Stack Instance (NEW — runtime)
        ├── tracks → Deployment (existing — topology→env binding)
        └── records → CIs in CMDB (existing)
```

---

## Data Model

### `stack_blueprints`

The top-level blueprint entity. Provider-scoped (system) or tenant-scoped.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK → tenants, nullable | NULL = system/provider-level |
| name | String(255), unique per tenant | Slug identifier |
| display_name | String(255) | Human-readable |
| description | Text | |
| provider_id | FK → semantic_providers | Primary target provider |
| category | Enum | COMPUTE, DATABASE, NETWORKING, PLATFORM, STORAGE, CUSTOM |
| tags | JSONB | Searchable labels: ["ha", "production", "proxmox"] |
| icon | String(100), nullable | Icon identifier for catalog display |
| input_schema | JSONB | JSON Schema defining input variables |
| output_schema | JSONB | JSON Schema defining output variables |
| version | Integer | Current working version |
| is_published | Boolean | |
| is_system | Boolean | Provider-level system blueprint |
| created_by | FK → users | |
| timestamps + soft_delete | | |

### `stack_blueprint_versions`

Immutable version snapshots (same pattern as ComponentVersion).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| version | Integer | |
| input_schema | JSONB | Frozen input schema at this version |
| output_schema | JSONB | Frozen output schema at this version |
| component_graph | JSONB | Frozen component composition (see below) |
| variable_bindings | JSONB | Frozen wiring (see below) |
| changelog | Text | |
| published_at | DateTime | |
| published_by | FK → users | |
| **Unique** | (blueprint_id, version) | |

### `stack_blueprint_components`

Junction table — which components are part of this blueprint, with position/role metadata.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| component_id | FK → components | |
| node_id | String(100) | Unique within blueprint, used in wiring |
| label | String(255) | Role label: "Primary Database", "Load Balancer" |
| description | Text, nullable | What this component does in the stack |
| sort_order | Integer | Provisioning order |
| is_optional | Boolean | Can tenant skip this component? |
| default_parameters | JSONB | Component-specific defaults for this stack |
| depends_on | JSONB | Array of node_ids this component depends on |
| **Unique** | (blueprint_id, node_id) | |

### `stack_variable_bindings`

Wiring: how blueprint input variables flow into component parameters, and how component outputs aggregate into blueprint outputs.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| direction | Enum: INPUT / OUTPUT | |
| variable_name | String(255) | Blueprint-level variable name |
| target_node_id | String(100) | Which component (node_id) |
| target_parameter | String(255) | Which parameter on the component |
| transform_expression | Text, nullable | Optional expression: `"${value}gb"`, `"${value * 1024}"` |
| **Unique** | (blueprint_id, direction, variable_name, target_node_id, target_parameter) | |

**Example bindings for "PostgreSQL HA Cluster":**

| Direction | Variable | Target Node | Target Param | Transform |
|-----------|----------|-------------|--------------|-----------|
| INPUT | storage_size_gb | primary_db | disk_size | `${value}` |
| INPUT | storage_size_gb | replica_db | disk_size | `${value}` |
| INPUT | db_version | primary_db | pg_version | |
| INPUT | db_version | replica_db | pg_version | |
| INPUT | cluster_name | private_net | network_name | `${value}-net` |
| INPUT | replica_count | replica_db | instance_count | |
| OUTPUT | primary_endpoint | primary_db | ip_address | `${value}:5432` |
| OUTPUT | connection_string | pgbouncer | connection_url | |

### `stack_blueprint_governance`

Per-tenant governance (same pattern as ComponentGovernance).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| tenant_id | FK → tenants | |
| is_allowed | Boolean | Can this tenant use this blueprint? |
| parameter_constraints | JSONB | Override min/max/allowed for input variables |
| max_instances | Integer, nullable | Max stack instances per tenant |
| **Unique** | (blueprint_id, tenant_id) | |

---

## Stack Instances (Runtime)

### `stack_instances`

A deployed stack — tracks which blueprint version was used, current state, and parameter values.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| blueprint_version | Integer | Which version was deployed |
| tenant_id | FK → tenants | |
| environment_id | FK → tenant_environments | |
| name | String(255) | Instance name |
| display_name | String(255) | |
| status | Enum | See lifecycle below |
| input_values | JSONB | Actual input variable values |
| output_values | JSONB | Resolved output variable values |
| component_states | JSONB | Per-component deployment state |
| deployed_by | FK → users | |
| deployed_at | DateTime, nullable | |
| last_health_check | DateTime, nullable | |
| health_status | Enum: HEALTHY / DEGRADED / UNHEALTHY / UNKNOWN | |
| error_message | Text, nullable | |
| timestamps + soft_delete | | |
| **Unique** | (tenant_id, environment_id, name) | |

**Stack Instance Lifecycle:**

```
PLANNED → PROVISIONING → ACTIVE → UPDATING → ACTIVE
                                 → DEGRADED → RECOVERING → ACTIVE
                                 → FAILING_OVER → ACTIVE (at DR site)
                                 → DECOMMISSIONING → DECOMMISSIONED
PROVISIONING → FAILED → ROLLING_BACK → ROLLED_BACK
```

### `stack_instance_components`

Per-component state within a stack instance.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| stack_instance_id | FK → stack_instances | |
| blueprint_component_id | FK → stack_blueprint_components | |
| component_id | FK → components | |
| component_version | Integer | Which version was deployed |
| ci_id | FK → configuration_items, nullable | CMDB record once provisioned |
| deployment_id | FK → deployments, nullable | Deployment tracking |
| status | Enum: PENDING / PROVISIONING / ACTIVE / FAILED / SKIPPED | |
| resolved_parameters | JSONB | Actual parameters after variable resolution |
| outputs | JSONB | Component's output values |
| pulumi_state_url | String(500), nullable | MinIO path for Pulumi state |
| **Unique** | (stack_instance_id, blueprint_component_id) | |

---

## Stack Workflows

Stack workflows are **operational workflows bound to a blueprint** that handle lifecycle operations beyond initial provisioning. They differ from component operations (which are per-component CRUD) — stack workflows operate on the **entire composition**.

### `stack_workflows`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| blueprint_id | FK → stack_blueprints | |
| workflow_definition_id | FK → workflow_definitions | Visual workflow |
| workflow_kind | Enum | See kinds below |
| name | String(255) | |
| display_name | String(255) | |
| description | Text, nullable | |
| is_required | Boolean | Must be defined before publishing? |
| trigger_conditions | JSONB, nullable | Auto-trigger rules (event-based) |
| sort_order | Integer | |
| timestamps | | |

**Workflow Kinds:**

| Kind | Purpose | Typical Trigger |
|------|---------|-----------------|
| PROVISION | Initial deployment of all components | User requests stack |
| DECOMMISSION | Tear down entire stack | User/admin action |
| UPGRADE | Roll forward to new blueprint version | New version published |
| SCALE_UP | Add capacity (more replicas, larger VMs) | Manual / auto-scaling rule |
| SCALE_DOWN | Reduce capacity | Manual / auto-scaling rule |
| BACKUP | Snapshot entire stack state | Schedule / manual |
| RESTORE | Restore from backup | Manual (DR scenario) |
| FAILOVER | Switch to DR site | Health check failure / manual |
| FAILBACK | Return from DR site to primary | Manual after primary recovery |
| HEALTH_CHECK | Validate stack is functioning | Schedule (cron) |
| REMEDIATE | Auto-fix detected issues | Drift detection / health check failure |
| CUSTOM | User-defined operational workflow | Manual / event trigger |

**How it works:**

Stack workflows are regular `WorkflowDefinition` entities (reusing the visual editor), but they have additional context:
- The workflow's `input_schema` automatically includes stack instance context (instance_id, component_states, input_values, output_values)
- Workflow nodes can reference stack components by `node_id` (e.g., "restart the primary_db component")
- The PROVISION workflow executes component deploy operations in dependency order
- The FAILOVER workflow can reference reservation targets

**New workflow node types for stack operations:**

| Node Type | Description |
|-----------|-------------|
| `stack_component_action` | Execute a component operation on a specific stack component by node_id |
| `stack_health_check` | Run health check on one or all components, output health status |
| `stack_parameter_resolve` | Re-resolve variable bindings (e.g., after failover, IPs change) |
| `stack_reservation_claim` | Claim reserved capacity at DR site |
| `stack_reservation_release` | Release reserved capacity |
| `stack_snapshot` | Snapshot entire stack state (all component states + Pulumi states) |
| `stack_restore_snapshot` | Restore from snapshot |

---

## Capacity Reservations (Disaster Recoverability)

Reservations pre-allocate infrastructure at a secondary site so that failover can happen within defined RTO targets without competing for capacity.

### `stack_reservations`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| stack_instance_id | FK → stack_instances | Which stack this reserves for |
| tenant_id | FK → tenants | |
| reservation_type | Enum | WARM_STANDBY / COLD_STANDBY / HOT_STANDBY / PILOT_LIGHT |
| target_environment_id | FK → tenant_environments | Where the DR capacity lives |
| target_provider_id | FK → semantic_providers | DR provider (can differ from primary) |
| reserved_resources | JSONB | What's reserved (see schema below) |
| rto_seconds | Integer | Recovery Time Objective |
| rpo_seconds | Integer | Recovery Point Objective |
| status | Enum | PENDING / ACTIVE / CLAIMED / RELEASED / EXPIRED |
| claimed_at | DateTime, nullable | When failover claimed this |
| claimed_by_instance_id | FK → stack_instances, nullable | The DR instance using this |
| expires_at | DateTime, nullable | Auto-release date |
| cost_per_hour | Decimal, nullable | Reservation cost tracking |
| last_tested_at | DateTime, nullable | Last failover test |
| test_result | Enum: PASSED / FAILED / UNTESTED | |
| timestamps + soft_delete | | |

**Reservation Types:**

| Type | What's Reserved | Cost | RTO |
|------|----------------|------|-----|
| HOT_STANDBY | Running replicas, syncing data continuously | High | Seconds |
| WARM_STANDBY | Provisioned but idle VMs, periodic data sync | Medium | Minutes |
| PILOT_LIGHT | Core infra running (DB replicas), compute off | Low-Medium | 10-30 min |
| COLD_STANDBY | Capacity quota reserved, nothing provisioned | Low | Hours |

**`reserved_resources` JSONB schema:**

```json
{
  "compute": {
    "vcpus": 16,
    "memory_gb": 64,
    "instances": [
      { "node_id": "primary_db", "spec": { "cores": 8, "memory": 32 } },
      { "node_id": "replica_db", "spec": { "cores": 4, "memory": 16 }, "count": 2 }
    ]
  },
  "storage": {
    "total_gb": 500,
    "volumes": [
      { "node_id": "shared_storage", "size_gb": 500, "type": "ssd" }
    ]
  },
  "network": {
    "vlans": 2,
    "public_ips": 1
  }
}
```

### `reservation_sync_policies`

Defines how data syncs between primary and DR for each reservation.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| reservation_id | FK → stack_reservations | |
| source_node_id | String(100) | Component in primary stack |
| target_node_id | String(100) | Component in DR reservation |
| sync_method | Enum | STREAMING / PERIODIC_SNAPSHOT / LOG_SHIPPING / NONE |
| sync_interval_seconds | Integer, nullable | For periodic sync |
| sync_workflow_id | FK → workflow_definitions, nullable | Custom sync workflow |
| last_synced_at | DateTime, nullable | |
| sync_lag_seconds | Integer, nullable | Current lag |
| timestamps | | |

### Reservation Lifecycle

```
1. Operator creates Stack Blueprint with DR requirements
2. Tenant deploys stack instance → system checks for required reservations
3. Reservation created at target environment:
   - HOT_STANDBY: provisions + starts replication immediately
   - WARM_STANDBY: provisions VMs but doesn't start workload
   - PILOT_LIGHT: provisions DB replicas only
   - COLD_STANDBY: allocates quota, nothing provisioned
4. Periodic sync runs per policy
5. Health checks verify reservation readiness
6. Failover test can be triggered (uses actual FAILOVER workflow against reservation)
7. Real failover: claim reservation → FAILOVER workflow → DR becomes primary
8. Failback: FAILBACK workflow → return to original site → release reservation → re-establish
```

---

## Workflow Integration (Variable Wiring)

Stack input/output variables can be wired into workflow inputs. This is the key integration point.

### How Wiring Works

```
Stack Blueprint "PostgreSQL HA"
  Input: cluster_name, db_version, storage_size_gb
  Output: primary_endpoint, connection_string

Stack Workflow "Failover" (WorkflowDefinition)
  Input Schema (auto-populated):
    stack_instance_id: UUID            ← injected by system
    stack_input_values: object         ← all stack inputs
    stack_output_values: object        ← all current outputs
    component_states: object           ← per-component status
    reservation_id: UUID               ← if reservation-based failover

  User-defined inputs:
    force: boolean                     ← user can add custom inputs
    notify_channel: string

  The workflow graph can reference:
    {{ stack.inputs.cluster_name }}    ← stack input variables
    {{ stack.outputs.primary_endpoint }} ← stack output variables
    {{ stack.components.primary_db.outputs.ip_address }} ← component outputs
    {{ stack.reservation.target_environment }} ← reservation context
```

### Expression Context for Stack Workflows

When a workflow is bound to a stack (via `stack_workflows`), its execution context is enriched with:

```json
{
  "stack": {
    "instance_id": "...",
    "blueprint_id": "...",
    "blueprint_version": 3,
    "name": "prod-pg-cluster",
    "inputs": { "cluster_name": "prod-pg", "db_version": "16", ... },
    "outputs": { "primary_endpoint": "10.0.1.5:5432", ... },
    "components": {
      "primary_db": {
        "status": "ACTIVE",
        "ci_id": "...",
        "outputs": { "ip_address": "10.0.1.5", "port": 5432 },
        "parameters": { "cores": 8, "memory": 32768 }
      },
      "replica_db": { ... },
      "pgbouncer": { ... }
    },
    "reservation": {
      "id": "...",
      "type": "WARM_STANDBY",
      "target_environment": "dr-site-1",
      "target_provider": "proxmox-secondary",
      "rto_seconds": 300,
      "rpo_seconds": 60
    },
    "health": {
      "status": "DEGRADED",
      "components_healthy": 4,
      "components_total": 5,
      "last_check": "2026-02-27T10:00:00Z"
    }
  }
}
```

---

## Frontend: Provider > Infrastructure

### Navigation Structure

```
Provider
├── Infrastructure          ← NEW section
│   ├── Stack Blueprints    ← Blueprint catalog + editor
│   ├── Components          ← existing (moved here from top-level)
│   ├── Templates           ← existing Pulumi templates
│   └── Reservations        ← Capacity reservation management
├── Activities              ← existing
├── Resolvers               ← existing
└── ...
```

### Stack Blueprint Editor

The editor reuses existing patterns (Monaco for code, visual graph for composition):

```
┌─────────────────────────────────────────────────────────┐
│ Stack Blueprint: PostgreSQL HA Cluster        v3 DRAFT  │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Tabs:    │  [Component Graph Canvas]                    │
│          │                                              │
│ ● Compo- │  ┌──────────┐    ┌──────────┐               │
│   sition │  │Private   │───→│Primary   │               │
│          │  │Network   │    │DB (VM)   │               │
│ ○ Vari-  │  └──────────┘    └────┬─────┘               │
│   ables  │         │             │                      │
│          │         │        ┌────▼─────┐               │
│ ○ Work-  │         └───────→│Replica   │               │
│   flows  │                  │DB (VM)   │               │
│          │                  └────┬─────┘               │
│ ○ DR &   │                      │                      │
│   Reser- │  ┌──────────┐   ┌────▼─────┐               │
│   vations│  │Shared    │   │PgBouncer │               │
│          │  │Storage   │   │(LXC)     │               │
│ ○ Gover- │  └──────────┘   └──────────┘               │
│   nance  │                                              │
│          │                                              │
├──────────┴──────────────────────────────────────────────┤
│ Properties Panel (selected component)                    │
│ Label: Primary Database    Component: proxmox-vm v2      │
│ Parameters: cores=8, memory=32GB, disk=${storage_size}  │
└─────────────────────────────────────────────────────────┘
```

**Variables Tab:**

```
┌─────────────────────────────────────────────────────────┐
│ Input Variables                              [+ Add]     │
├──────────┬──────────┬──────────┬────────────────────────┤
│ Name     │ Type     │ Default  │ Wired To               │
├──────────┼──────────┼──────────┼────────────────────────┤
│ cluster_ │ string   │ —        │ primary_db.name,       │
│ name     │          │          │ replica_db.name,       │
│          │          │          │ private_net.name       │
│ db_ver   │ string   │ "16"    │ primary_db.pg_version, │
│          │          │          │ replica_db.pg_version  │
│ storage_ │ integer  │ 100     │ primary_db.disk_size,  │
│ size_gb  │ (min:10) │         │ replica_db.disk_size,  │
│          │          │          │ shared_storage.size    │
├──────────┴──────────┴──────────┴────────────────────────┤
│ Output Variables                             [+ Add]     │
├──────────┬──────────┬──────────────────────────────────  │
│ Name     │ Type     │ Source                              │
├──────────┼──────────┼──────────────────────────────────  │
│ primary_ │ string   │ primary_db.ip_address + ":5432"    │
│ endpoint │          │                                     │
│ connstr  │ string   │ pgbouncer.connection_url            │
└──────────┴──────────┴───────────────────────────────────┘
```

**Workflows Tab:**

```
┌─────────────────────────────────────────────────────────┐
│ Stack Workflows                              [+ Add]     │
├──────────┬──────────────┬───────────┬───────────────────┤
│ Kind     │ Name         │ Required  │ Trigger            │
├──────────┼──────────────┼───────────┼───────────────────┤
│ PROVISION│ Deploy Stack │ ✓ Yes     │ On Create          │
│ DECOMMIS │ Tear Down    │ ✓ Yes     │ On Delete          │
│ FAILOVER │ DR Failover  │ No        │ Health: UNHEALTHY  │
│ BACKUP   │ Daily Backup │ No        │ Cron: 0 2 * * *   │
│ UPGRADE  │ Version Up   │ No        │ Manual             │
│ HEALTH   │ Health Check │ No        │ Every 5 min        │
├──────────┴──────────────┴───────────┴───────────────────┤
│ [Open in Workflow Editor]  — launches visual editor      │
│ with stack context pre-injected into input schema        │
└─────────────────────────────────────────────────────────┘
```

**DR & Reservations Tab:**

```
┌─────────────────────────────────────────────────────────┐
│ DR Requirements                                          │
├─────────────────────────────────────────────────────────┤
│ Default Reservation Type:  [WARM_STANDBY ▾]              │
│ Target RTO:                [300] seconds (5 min)         │
│ Target RPO:                [60] seconds (1 min)          │
│                                                          │
│ Sync Policies:                                           │
│ ┌──────────┬──────────┬───────────┬──────────────────┐  │
│ │ Source   │ Target   │ Method    │ Interval         │  │
│ ├──────────┼──────────┼───────────┼──────────────────┤  │
│ │ primary_ │ dr_prim  │ STREAMING │ Continuous       │  │
│ │ db       │ ary_db   │           │                  │  │
│ │ shared_  │ dr_stor  │ PERIODIC  │ Every 60s        │  │
│ │ storage  │ age      │ _SNAPSHOT │                  │  │
│ └──────────┴──────────┴───────────┴──────────────────┘  │
│                                                          │
│ Failover Test Schedule:  [Monthly ▾]                     │
│ Last Test: 2026-02-15 — PASSED (RTO: 4m 12s)           │
└─────────────────────────────────────────────────────────┘
```

---

## Versioning Strategy

Stack blueprints follow the same pattern as Components and Workflows:

1. **Draft** (version 0): Editable, not deployable
2. **Publish**: Freezes current state into `stack_blueprint_versions` with incremented version number. Snapshot includes component graph, variable bindings, input/output schemas
3. **Active**: Latest published version is the default for new deployments
4. **Archived**: Previous versions remain accessible for running instances

**Upgrade path for running instances:**
- New blueprint version published → system identifies instances on old version
- Operator can trigger UPGRADE stack workflow per instance
- UPGRADE workflow handles rolling component updates respecting dependency order
- Instance's `blueprint_version` updated after successful upgrade
- Rollback via RESTORE workflow if upgrade fails

---

## Permissions

| Permission | Tier | Description |
|-----------|------|-------------|
| `infrastructure:blueprint:read` | Read-Only | View stack blueprints |
| `infrastructure:blueprint:manage` | Tenant Admin | Create/edit/publish blueprints |
| `infrastructure:blueprint:deploy` | User | Deploy stack instances |
| `infrastructure:blueprint:destroy` | Tenant Admin | Decommission stack instances |
| `infrastructure:reservation:read` | Read-Only | View reservations |
| `infrastructure:reservation:manage` | Tenant Admin | Create/modify reservations |
| `infrastructure:reservation:test` | Tenant Admin | Trigger failover tests |

---

## Impact on Existing Phases

| Phase | Impact |
|-------|--------|
| Phase 12 (Pulumi) | `pulumi_templates` become component-level Pulumi code. Stack blueprints compose them. Pulumi stacks map 1:1 to stack instance components. |
| Phase 6 (Workflows) | New `STACK` workflow type. Stack context injected into execution. New node types for stack operations. |
| Phase 8 (CMDB) | Stack instances create CI groups. Component CIs linked via stack_instance_components. |
| Phase 10 (Approvals) | Stack provisioning/failover can gate through approval chains. |
| Phase 11.6 (Events) | New event types: `stack.provisioned`, `stack.failed`, `stack.failover.started`, `stack.health.degraded` |
| Phase 17 (Drift) | Drift detection runs per-component within stack context. Stack-level drift = any component drifted. |
| Phase 19 (Cost) | Cost aggregated per stack instance (sum of component costs + reservation costs). |

---

## Key Design Decisions

1. **Blueprints compose Components, not raw Pulumi code.** This keeps the abstraction clean — Components handle single-resource IaC, Blueprints handle composition and wiring.

2. **Variable bindings are declarative, not imperative.** The wiring between blueprint inputs and component parameters is a static mapping with optional transform expressions — not workflow logic.

3. **Stack workflows reuse the visual workflow editor.** No new editor needed. The workflow just has richer context (stack inputs/outputs/component states) available in expressions.

4. **Reservations are separate from instances.** A reservation can exist before any failover happens, tracking capacity and sync state independently.

5. **Version snapshots are immutable.** Publishing freezes the entire composition. Running instances reference a specific version. Upgrades are explicit workflow operations.

6. **DR is opt-in per blueprint.** Not every stack needs disaster recovery. The DR tab is optional. Blueprints can declare minimum DR requirements that tenants must satisfy.
