# Revised Phase Plan: Infrastructure Automation Pipeline

## Status
- [x] Concept drafted (2026-02-14)
- [ ] Approved
- [ ] Supersedes current phases 11-22

## Context

This document revises phases 11+ based on a refined conceptual model for infrastructure automation.
Phases 1-10 remain unchanged (all complete). The landing zone backend (migrations 058-063,
services, GraphQL) is ~80% implemented and carries forward.

## Conceptual Model

```
Landing Zone (per backend/provider)
├── Provider-level topology (shared services, network backbone)
├── Resolver configurations (IPAM pools, naming conventions, image catalogs)
├── Environment templates (with mandatory component lists)
└── System services (observability, bastion — provider-managed, auto-deployed)

Component (per provider, versioned)
├── Pulumi script + typed parameter contract (inputs/outputs)
├── Semantic type binding (1 component = 1 semantic type)
├── Resolver bindings (which inputs are resolved by platform services)
└── Upgrade workflow slot (migration logic for version N → N+1)

Resolver (platform service, provider-admin managed)
├── Same typed interface as components (inputs → outputs)
├── NOT deployed to cloud — runs inside Nimbus at resolution time
├── Configured at landing zone or environment level
├── Examples: IPAM allocator, image catalog, naming service, secret provisioner

Stack (per provider, versioned, forkable)
├── Component DAG (ordered, with inter-component parameter wiring)
├── Stack-level parameters → transformed → component parameters
├── State machine definition (states, transitions, trigger conditions)
├── Lifecycle workflows (deploy, destroy, upgrade, custom day-2)
└── Tenant-forkable (copy + modify)

Topology (per tenant, environment-scoped)
├── Stack instances + standalone component instances
├── Inter-stack dependencies
├── Environment binding (which landing zone / environment)
└── Deployment plan (parallel groups from dependency sort)

Environment (deployment target within landing zone)
├── Resolver instances (IPAM allocation scope, naming scope)
├── Deployed artifact instances (stacks + components with runtime state)
├── Mandatory components (from environment template)
└── Day-2 operation surface
```

### Key Principles

1. **Components map 1:1 to semantic types.** A "VirtualMachine" component for OCI internally
   handles instance + boot volume + VNIC + attachments. Sub-resources are properties, not
   separate components.

2. **Resolvers are NOT components.** They share the same typed I/O interface pattern but are
   platform-internal services, invisible to tenant users, configured by provider admins at the
   landing zone or environment level.

3. **Pre-resolution.** Before a component's Pulumi program runs, all resolver-bound parameters
   are resolved and injected as concrete values into the Pulumi stack config. Pulumi programs
   never call back to Nimbus mid-execution.

4. **State machines are Temporal workflows.** A stack's state machine compiles to a long-running
   `StackLifecycleWorkflow` that holds state, accepts signal-based transitions, and executes
   associated workflows on each transition.

5. **Version pinning with explicit upgrades.** Deployed instances are pinned to the component/stack
   version they were deployed with. Upgrading requires an upgrade workflow defined in the higher
   version (like a database migration).

6. **Composition AND forking for stacks.** Tenants can compose provider stacks with their own
   components at the topology level, OR fork a provider stack to create a modified copy.

7. **Landing zone system services** replace hidden environments. Observability, bastion, and
   shared security infrastructure are provider-level concerns deployed as part of the landing
   zone itself, not per-tenant environments.

8. **Cross-provider topologies are out of scope** for now.

---

## Revised Phase Plan (Phases 11–26)

### Phase 11: Component Model & Resolver Framework
**Status**: Backlog
**Goal**: Define the core Component abstraction — typed, versioned Pulumi scripts bound to semantic
types — and the Resolver framework for deploy-time parameter resolution.
**Depends on**: Phase 5 (semantic types), Phase 6 (workflow editor, for upgrade workflows)

This is the **new foundation** for all infrastructure automation. Everything else builds on this.

#### Data Model

**`components`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK → tenants, nullable | NULL = provider-level (shared), non-null = tenant-scoped |
| provider_id | FK → semantic_providers | Which cloud provider |
| semantic_type_id | FK → semantic_resource_types | What abstract type this represents |
| name | String(200) | Unique per provider+tenant |
| display_name | String(200) | |
| description | Text | |
| language | String(20) | 'typescript' / 'python' |
| code | Text | Pulumi program source |
| input_schema | JSONB | Typed input parameters (JSON Schema) |
| output_schema | JSONB | Typed outputs (JSON Schema) |
| resolver_bindings | JSONB | Map of input params → resolver type (e.g. `{"ip_address": "ipam", "hostname": "naming"}`) |
| version | Integer | Incremented on publish |
| is_published | Boolean | Only published versions are deployable |
| is_system | Boolean | System-provided vs user-created |
| upgrade_workflow_id | FK → workflow_definitions, nullable | Workflow for upgrading from previous version |
| created_by | FK → users | |
| timestamps + soft_delete | | |
| **Unique** | (provider_id, tenant_id, name, version) | |

**`component_versions`** (version history)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| component_id | FK → components | |
| version | Integer | |
| code | Text | Snapshot of code at this version |
| input_schema | JSONB | Snapshot |
| output_schema | JSONB | Snapshot |
| resolver_bindings | JSONB | Snapshot |
| changelog | Text | What changed |
| published_at | DateTime | |
| published_by | FK → users | |

**`resolvers`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resolver_type | String(50), unique | 'ipam', 'naming', 'image_catalog', 'secret' |
| display_name | String(200) | |
| description | Text | |
| input_schema | JSONB | What the resolver needs (e.g. `{"network_tier": "string", "ip_version": "integer"}`) |
| output_schema | JSONB | What it returns (e.g. `{"ip_address": "string", "subnet_id": "string"}`) |
| handler_class | String(200) | Python class path (e.g. `app.services.resolvers.ipam.IPAMResolver`) |
| is_system | Boolean | Always true for built-in resolvers |

**`resolver_configurations`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resolver_id | FK → resolvers | |
| landing_zone_id | FK → landing_zones, nullable | Zone-wide config |
| environment_id | FK → tenant_environments, nullable | Environment-specific override |
| config | JSONB | Resolver-specific settings (e.g. IPAM pool ID, naming pattern) |
| **Unique** | (resolver_id, landing_zone_id, environment_id) | |

**`component_governance`** (per-tenant constraints, replaces pulumi_template_constraints)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| component_id | FK → components | |
| tenant_id | FK → tenants | |
| is_allowed | Boolean | Allow/deny this component for this tenant |
| parameter_constraints | JSONB | Per-parameter min/max/allowed |
| max_instances | Integer, nullable | |
| **Unique** | (component_id, tenant_id) | |

#### Built-in Resolvers (implemented in Phase 11)

1. **IPAM Resolver** — Allocates IPs/subnets from the landing zone's address pools.
   Wraps the existing `ipam_service`. Input: `{allocation_type, prefix_length, parent_scope}`.
   Output: `{cidr, gateway, subnet_id}`.

2. **Naming Resolver** — Generates resource names per naming convention.
   Input: `{resource_type, environment, sequence}`.
   Output: `{name, fqdn}`.
   Naming patterns configured per landing zone (e.g. `{env}-{type}-{seq:03d}`).

3. **Image Catalog Resolver** — Maps semantic OS names to provider-specific image IDs.
   Input: `{os_family, os_version, architecture}`.
   Output: `{image_id, image_name}`.
   Catalog populated per provider (Proxmox templates, OCI images, AWS AMIs, etc.).

#### Task Breakdown (~15 tasks)

1. **Migration** — `components`, `component_versions`, `resolvers`, `resolver_configurations`, `component_governance` tables + permissions + seed built-in resolver types
2. **SQLAlchemy Models** — Component, ComponentVersion, Resolver, ResolverConfiguration, ComponentGovernance
3. **Component Service** — CRUD, versioning (publish creates snapshot in component_versions), code validation
4. **Resolver Framework** — Abstract `BaseResolver` class, resolver registry, pre-resolution pipeline (`resolve_all(component, environment) → resolved_params`)
5. **IPAM Resolver** — Wraps existing IPAM service, implements BaseResolver interface
6. **Naming Resolver** — Pattern-based name generation, implements BaseResolver
7. **Image Catalog Resolver** — Provider-specific image lookup, seed data for Proxmox
8. **Governance Service** — Per-tenant allow/deny, parameter constraint enforcement, max instances
9. **GraphQL Types** — ComponentType, ComponentVersionType, ResolverType, ResolverConfigType, GovernanceType
10. **GraphQL Queries + Mutations** — Full CRUD for components, resolver configs, governance
11. **Monaco Editor Component** — Angular wrapper for Monaco, TypeScript + Python language support, light theme
12. **Component Editor Page** — Monaco code editor + input/output schema builder + resolver binding UI + version history
13. **Component Catalog Page** — Browse/filter/search components, deploy action, provider filter
14. **Resolver Configuration UI** — Part of landing zone detail page, configure resolvers per zone/environment
15. **Governance Settings UI** — Per-tenant component allow/deny, parameter constraints

#### Permissions (8)
| Permission | Tier |
|-----------|------|
| `component:definition:read` | Read-Only |
| `component:definition:create` | Tenant Admin |
| `component:definition:update` | Tenant Admin |
| `component:definition:delete` | Tenant Admin |
| `component:definition:publish` | Provider Admin |
| `component:governance:manage` | Provider Admin |
| `resolver:config:read` | Read-Only |
| `resolver:config:manage` | Provider Admin |

---

### Phase 12: Pulumi Execution Engine
**Status**: Backlog
**Goal**: Make components executable — Pulumi Automation API wrapper, pre-resolution pipeline,
deploy/destroy/preview workflows, CMDB sync, and landing zone bootstrap.
**Depends on**: Phase 11 (component model), Phase 10 (approvals), Phase 8 (CMDB)

#### Data Model

**`deployed_components`** (runtime instances of components)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| component_id | FK → components | |
| component_version | Integer | Pinned version at deploy time |
| tenant_id | FK → tenants | |
| environment_id | FK → tenant_environments | |
| stack_instance_id | FK → stack_instances, nullable | If part of a stack |
| pulumi_stack_name | String(200) | Unique Pulumi stack identifier |
| resolved_parameters | JSONB | All parameters after resolution (snapshot) |
| outputs | JSONB | Pulumi stack outputs |
| status | Enum | pending / deploying / deployed / failed / destroying / destroyed / upgrading |
| pulumi_state_url | String(500) | MinIO path |
| deployed_at | DateTime | |
| deployed_by | FK → users | |
| error_message | Text, nullable | |
| timestamps + soft_delete | | |

**Updates to `landing_zones`:**
- Add `system_services_topology_id` FK → architecture_topologies (nullable)
- Add `resolver_configs` relationship (via resolver_configurations table)

**Updates to `environment_templates`:**
- Add `mandatory_components` JSONB — list of component IDs + default parameters that must be deployed in every environment using this template

#### Pulumi Automation Wrapper

`backend/app/services/pulumi/automation.py`:
- `PulumiEngine` class wrapping Pulumi Automation API `LocalWorkspace`
- State backend: MinIO (S3-compatible)
- Methods:
  - `preview(code, language, config) → ResourceDiff`
  - `up(code, language, config) → UpResult` (outputs, resource URNs)
  - `destroy(stack_name) → DestroyResult`
  - `refresh(stack_name) → RefreshResult`
  - `export_state(stack_name) → StateSnapshot`
- Handles TypeScript and Python programs
- Injects resolved parameters as Pulumi config values

#### Pre-Resolution Pipeline

`backend/app/services/pulumi/resolution.py`:
- `ParameterResolver.resolve(component, environment, user_params) → resolved_params`
  1. Start with component's `input_schema` defaults
  2. Override with user-provided params
  3. For each param with a resolver binding: call resolver, inject result
  4. Validate final params against input_schema + governance constraints
  5. Return fully resolved parameter set (no unknowns)

#### Temporal Workflows

**ComponentDeployWorkflow:**
```
resolve_parameters(component_id, environment_id, user_params)
  → pre-resolve all abstract params via resolvers
validate_governance(component_id, tenant_id, resolved_params)
  → check allow/deny, parameter constraints, max instances
pulumi_preview(code, language, resolved_params)
  → dry-run, return diff
[optional] wait_for_approval → ApprovalChainWorkflow
pulumi_up(code, language, resolved_params, stack_name)
  → execute, store state in MinIO
sync_cmdb(outputs, environment_id, semantic_type_id)
  → create/update CIs in CMDB from Pulumi outputs
record_deployment(deployed_component_id, outputs, status)
compensation: pulumi_destroy on failure → release resolver allocations (e.g. IPAM)
```

**ComponentDestroyWorkflow:**
```
validate(deployed_component_id)
pulumi_destroy(stack_name)
release_resolver_allocations(deployed_component_id)
  → e.g. release IPAM allocations back to pool
sync_cmdb(environment_id, status=decommissioned)
record(status=destroyed)
```

**ComponentUpgradeWorkflow:**
```
validate_upgrade_path(deployed_component_id, target_version)
  → check upgrade_workflow_id exists on target version
resolve_parameters(target_version, environment_id, params)
  → re-resolve with new version's schema
execute_upgrade_workflow(upgrade_workflow_id, old_params, new_params)
  → runs the component author's custom upgrade logic
pulumi_up(new_code, language, new_params, stack_name)
  → in-place update
sync_cmdb(...)
update_deployed_component(version=target_version)
```

**LandingZoneBootstrapWorkflow:**
```
on landing_zone.publish:
  for each system_service in landing_zone.system_services_topology:
    deploy_component(service_component, landing_zone_environment)
  configure_resolvers(landing_zone.resolver_configs)

on environment.create (status → PROVISIONING):
  for each mandatory_component in environment_template.mandatory_components:
    resolve_parameters(component, environment, template_defaults)
    deploy_component(component, environment)
  transition environment status → ACTIVE
```

#### Task Breakdown (~14 tasks)

1. **Migration** — `deployed_components` table, updates to `landing_zones` (system_services_topology_id), updates to `environment_templates` (mandatory_components)
2. **SQLAlchemy Models** — DeployedComponent + relationships
3. **Pulumi Engine** — `PulumiEngine` wrapper class (LocalWorkspace, MinIO state, TS+Python)
4. **Pre-Resolution Pipeline** — `ParameterResolver` service, resolver chain execution
5. **Deploy Service** — Orchestrates deploy/destroy/upgrade lifecycle, status tracking
6. **ComponentDeployWorkflow** — Temporal workflow + activities (resolve, validate, preview, up, sync, record)
7. **ComponentDestroyWorkflow** — Temporal workflow + activities (destroy, release, sync, record)
8. **ComponentUpgradeWorkflow** — Temporal workflow + activities (validate path, re-resolve, upgrade, up, sync)
9. **LandingZoneBootstrapWorkflow** — Temporal workflow for auto-provisioning on LZ publish + env create
10. **CMDB Sync Service** — Map Pulumi outputs to CMDB CIs, create/update/decommission
11. **GraphQL API** — DeployedComponentType, queries (list/get by env), mutations (deploy, destroy, upgrade, preview)
12. **Landing Zone System Services UI** — Topology sub-editor for system services on LZ detail page
13. **Environment Mandatory Components UI** — Template editor section for required components
14. **Deploy/Destroy/Upgrade UI** — Deploy dialog (parameter form from input_schema), status tracking, upgrade wizard

#### Permissions (5)
| Permission | Tier |
|-----------|------|
| `component:deploy` | User |
| `component:destroy` | Tenant Admin |
| `component:upgrade` | Tenant Admin |
| `component:preview` | User |
| `landingzone:bootstrap:manage` | Provider Admin |

---

### Phase 13: Proxmox Provider (First Provider)
**Status**: Backlog
**Goal**: First concrete provider implementation — validates the entire pipeline end-to-end
(Component → Resolver → Pulumi → CMDB) with a free, self-hosted platform.
**Depends on**: Phase 12 (execution engine), Phase 5 (semantic types), Phase 8 (CMDB)

This phase creates real, deployable Proxmox components and validates the full automation pipeline.

#### Deliverables

1. **CloudProviderInterface implementation** (`ProxmoxProvider`)
   - `validate_credentials` — test API token against Proxmox REST API
   - `list_resources` — discover VMs, containers, storage, networks
   - `get_resource` — fetch single resource details
   - `map_to_semantic` — map Proxmox resources to semantic types
   - `get_cost_data` — N/A for Proxmox (return empty; cost is infrastructure-level)

2. **Proxmox Components** (provider-level, system, published)
   - `proxmox-vm` — QEMU/KVM virtual machine (semantic: VirtualMachine)
     - Inputs: `name, cores, memory_mb, disk_gb, os_template, network_bridge, ip_address, gateway, dns, storage_pool, tags`
     - Resolver bindings: `ip_address → ipam`, `name → naming`
     - Outputs: `vmid, ip_address, mac_address, status`
   - `proxmox-lxc` — LXC container (semantic: Container)
     - Inputs: `name, cores, memory_mb, rootfs_gb, os_template, network_bridge, ip_address, gateway, storage_pool`
     - Resolver bindings: `ip_address → ipam`, `name → naming`
     - Outputs: `vmid, ip_address, status`
   - `proxmox-storage` — Storage volume (semantic: BlockStorage)
     - Inputs: `name, size_gb, storage_pool, format`
     - Outputs: `volume_id, path`
   - `proxmox-network` — Linux Bridge or SDN VNet (semantic: VirtualNetwork)
     - Inputs: `name, type (bridge/sdn), cidr, vlan_tag, sdn_zone`
     - Resolver bindings: `cidr → ipam`
     - Outputs: `bridge_name, network_id`
   - `proxmox-firewall-rule` — Firewall rules (semantic: FirewallRule)
     - Inputs: `direction, action, source, dest, port, protocol, comment`

3. **Proxmox Image Catalog** — Seed resolver data
   - Map OS families (debian, ubuntu, centos, rocky, windows) to Proxmox template names
   - Resolver config per landing zone (which storage pool holds templates)

4. **Proxmox Landing Zone Blueprint** — Update existing blueprints
   - Wire blueprint topology nodes to actual Proxmox components
   - Bootstrap workflow deploys: management bridge, storage pool config, firewall baseline

5. **End-to-End Validation**
   - Create Proxmox backend → Create landing zone → Publish (triggers bootstrap) →
     Create environment → Deploy VM component → Verify CMDB CI created →
     Destroy VM → Verify CMDB updated → Verify IPAM released

#### Task Breakdown (~12 tasks)

1. **ProxmoxProvider class** — CloudProviderInterface implementation using `proxmoxer` library
2. **Provider registration** — Register ProxmoxProvider in provider_registry on startup
3. **Proxmox VM component** — Pulumi TypeScript using `@bpg/pulumi-proxmox`, input/output schema, resolver bindings
4. **Proxmox LXC component** — Same pattern for containers
5. **Proxmox Storage component** — Block storage provisioning
6. **Proxmox Network component** — Bridge/SDN creation
7. **Proxmox Firewall component** — Rule management
8. **Image catalog seed data** — Proxmox OS templates in image_catalog resolver
9. **Landing zone blueprint wiring** — Connect blueprint nodes to components
10. **Resource discovery service** — Sync existing Proxmox resources to CMDB
11. **Integration tests** — End-to-end deploy/destroy cycle (requires Proxmox test instance)
12. **Documentation** — Proxmox setup guide, component reference

---

### Phase 14: Stack Model, State Machines & Lifecycle
**Status**: Backlog
**Goal**: Multi-component groupings (stacks) with visual composition, state machines for
runtime behavior, and programmable lifecycle workflows (deploy, destroy, upgrade, day-2).
**Depends on**: Phase 12 (component execution), Phase 6 (workflow editor for lifecycle workflows
and state machine visual editor)

#### Core Concepts

**Stack = provider-level blueprint for deploying multiple components together.**
- A stack contains an ordered DAG of components with parameter wiring between them.
- A stack declares its own parameters, which are transformed before being passed to components.
- A stack defines a state machine for runtime behavior (e.g. HA failover).
- A stack defines lifecycle workflows (deploy, destroy, upgrade, and custom day-2 operations).
- Stacks are versioned. Deployed stacks are pinned. Upgrades require explicit workflows.

**Stack Instance = a deployed stack in a specific environment.**
- References the stack definition + version
- Holds runtime state (current state machine state)
- Contains deployed_components for each component in the stack

**Forking = tenant copies a provider stack and modifies it.**
- Creates a new tenant-scoped stack with the provider stack as `forked_from`
- Tenant can add/remove components, modify wiring, change state machine
- Fork does NOT auto-update when parent changes (explicit merge required)

#### Data Model

**`stacks`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | FK → tenants, nullable | NULL = provider-level |
| provider_id | FK → semantic_providers | |
| name | String(200) | |
| display_name | String(200) | |
| description | Text | |
| input_schema | JSONB | Stack-level parameters (exposed to deployer) |
| component_graph | JSONB | DAG: `{nodes: [{component_id, param_wiring, position}], edges: [{from, to, output_key, input_key}]}` |
| state_machine | JSONB | `{states: [{name, is_initial, is_terminal}], transitions: [{from, to, trigger, workflow_id}]}` |
| deploy_workflow_id | FK → workflow_definitions, nullable | Custom deploy sequence |
| destroy_workflow_id | FK → workflow_definitions, nullable | Custom destroy sequence |
| upgrade_workflow_id | FK → workflow_definitions, nullable | Version migration logic |
| version | Integer | |
| is_published | Boolean | |
| is_system | Boolean | |
| forked_from_id | FK → stacks, nullable | Parent stack if forked |
| created_by | FK → users | |
| timestamps + soft_delete | | |

**`stack_day2_operations`** (named operations beyond deploy/destroy/upgrade)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| stack_id | FK → stacks | |
| name | String(100) | e.g. 'failover', 'scale_out', 'backup', 'restart' |
| display_name | String(200) | |
| description | Text | |
| input_schema | JSONB | Operation-specific parameters |
| workflow_id | FK → workflow_definitions | Workflow to execute |
| required_states | JSONB | Which state machine states allow this operation (e.g. failover only when 'active') |
| triggers_transition | String(100), nullable | State machine transition name triggered on completion |

**`stack_instances`** (deployed stacks in environments)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| stack_id | FK → stacks | |
| stack_version | Integer | Pinned version |
| tenant_id | FK → tenants | |
| environment_id | FK → tenant_environments | |
| deployment_id | FK → deployments, nullable | Parent deployment if from topology |
| name | String(200) | Instance name |
| parameters | JSONB | Resolved stack-level params |
| current_state | String(100) | Current state machine state |
| status | Enum | pending / deploying / active / degraded / failed / destroying / destroyed / upgrading |
| deployed_at | DateTime | |
| deployed_by | FK → users | |
| timestamps + soft_delete | | |

Note: `deployed_components` (from Phase 12) gains `stack_instance_id` FK to link components to their parent stack.

#### State Machine Runtime

The state machine is implemented as a **long-running Temporal workflow**: `StackLifecycleWorkflow`.

```
StackLifecycleWorkflow(stack_instance_id):
  state = load_initial_state()

  while not state.is_terminal:
    # Wait for a transition signal
    signal = await wait_for_signal([
      "transition",        # Manual trigger from UI/API
      "event",             # Cloud event / Nimbus event / monitoring webhook
      "scheduled_check",   # Periodic health check
    ])

    transition = match_transition(state, signal)
    if transition:
      # Execute the transition's workflow
      await execute_child_workflow(transition.workflow_id, context)
      state = transition.target_state
      update_stack_instance(current_state=state.name)
      emit_event("stack.state_changed", {instance_id, from, to})
    else:
      log_invalid_transition(state, signal)
```

This gives us:
- **Durability** — Temporal persists state across restarts
- **Signal-based triggers** — Cloud events, webhooks, manual actions all become signals
- **Workflow composition** — Each transition executes a child workflow (reuses Phase 6 engine)
- **Queryable state** — Temporal queries expose current state without DB lookup
- **Timeout handling** — Transitions can have deadlines (e.g. "if failover takes >5min, escalate")

#### Stack Deploy Sequence

When a stack is deployed:
1. Resolve stack-level parameters
2. Topologically sort the component graph
3. For each component (respecting dependencies):
   a. Map stack params → component params (via `param_wiring`)
   b. Feed outputs of upstream components as inputs to downstream
   c. Run `ComponentDeployWorkflow` (from Phase 12)
4. Once all components deployed, start `StackLifecycleWorkflow` in initial state
5. Record stack_instance as `active`

This can be customized via `deploy_workflow_id` — the stack author can override the default
deployment sequence with a custom workflow (e.g. adding health checks between components,
parallel groups, approval gates, notifications).

#### Stack Editor (Specialized UI)

A **concise, focused editor** — NOT the free-form Rete.js topology canvas. The stack editor
is a structured form-based UI with these sections:

1. **Component Slots** — Ordered list of components in the stack. Each slot shows: component
   name/type, parameter wiring (which stack params or upstream outputs feed into each input),
   position in dependency order. Add/remove/reorder slots.

2. **Parameter Definition Panel** — Define stack-level input parameters (name, type, description,
   default, required). Map each to component slot inputs via transformation expressions.

3. **Monaco Code Editor** — For viewing/editing the Pulumi scripts of individual components
   inline. Monaco is the open-source editor that VS Code uses. Supports TypeScript + Python
   with syntax highlighting, IntelliSense, and error markers.

4. **State Machine Editor** — Visual state/transition diagram. Drag states, draw transition
   arrows, assign trigger conditions (event patterns) and workflows to each transition.
   Uses a simple graph visualization (not the full Rete.js node engine — states and transitions
   are simpler than workflow nodes).

5. **Lifecycle Workflows** — Assign workflows for deploy, destroy, upgrade, and custom day-2
   operations. Links to workflow definitions from Phase 6. Each operation shows its parameter
   schema and required state machine states.

6. **Day-2 Operations** — Define named operations (failover, scale, backup, etc.) with input
   schemas, required states, and workflow bindings.

#### Task Breakdown (~18 tasks)

1. **Migration** — `stacks`, `stack_day2_operations`, `stack_instances` tables + permissions
2. **SQLAlchemy Models** — Stack, StackDay2Operation, StackInstance
3. **Stack Service** — CRUD, versioning, publish, fork
4. **Stack Deploy Service** — Topological sort, parameter wiring, orchestrate ComponentDeployWorkflows
5. **Stack Destroy Service** — Reverse-order component destruction
6. **Stack Upgrade Service** — Version diff, parameter migration, rolling component upgrades
7. **State Machine Engine** — Parse state_machine JSONB, validate transitions, compile to workflow
8. **StackLifecycleWorkflow** — Long-running Temporal workflow with signal handlers
9. **Day-2 Operation Service** — Execute named operations, validate required_states
10. **Forking Service** — Deep copy stack + rewire, track lineage
11. **GraphQL Types** — StackType, StackInstanceType, Day2OperationType, StateMachineType
12. **GraphQL Queries + Mutations** — Full CRUD + deploy/destroy/upgrade/fork/day2-execute
13. **Stack Editor** — Specialized UI: component slots, parameter wiring, Monaco code view, lifecycle workflow assignment
14. **State Machine Editor** — Visual state/transition diagram within stack editor
15. **Stack Catalog Page** — Browse/search/filter stacks, fork action
16. **Stack Instance Detail Page** — Current state, component status, day-2 operations panel, state history
17. **Day-2 Operations Panel** — Buttons for available operations (filtered by current state), parameter dialogs
18. **Stack Deploy Wizard** — Select stack → configure params → preview → approve → deploy

#### Permissions (8)
| Permission | Tier |
|-----------|------|
| `stack:definition:read` | Read-Only |
| `stack:definition:create` | Tenant Admin |
| `stack:definition:update` | Tenant Admin |
| `stack:definition:publish` | Provider Admin |
| `stack:instance:deploy` | User |
| `stack:instance:destroy` | Tenant Admin |
| `stack:instance:upgrade` | Tenant Admin |
| `stack:instance:day2` | User |

---

### Phase 15: Event Bus & Cloud Events
**Status**: Backlog
**Goal**: Unified event ingestion for cloud provider events, Nimbus internal events, monitoring
webhooks, and (later) OS/app-level agent events. Routes events to stack state machine transitions.
**Depends on**: Phase 14 (state machines), Phase 13 (Valkey for pub/sub)

#### Core Concepts

Events come from multiple sources and must be routed to the correct stack instance's state
machine for potential transitions.

**Event Sources:**
1. **Cloud Events** — Provider-specific: Proxmox task completion, OCI event service, AWS EventBridge, Azure Event Grid
2. **Nimbus Events** — Internal: deployment completed, approval granted, drift detected, CMDB changed
3. **Monitoring Webhooks** — External: Prometheus Alertmanager, Grafana alerts, PagerDuty, custom
4. **Agent Events** (Phase 24) — OS/app-level: process crashed, disk full, service unhealthy

**Event Routing:**
- Events carry a `resource_id` or `stack_instance_id` to identify the target
- Routing rules map event types to state machine transition signals
- Rules are defined per stack definition (e.g. "when event type = `vm.stopped`, signal = `failure`")

#### Data Model

**`event_sources`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | String(200) | |
| source_type | Enum | cloud_provider / nimbus / webhook / agent |
| provider_id | FK → semantic_providers, nullable | For cloud_provider type |
| endpoint_config | JSONB | Polling URL, webhook secret, etc. |
| is_active | Boolean | |

**`event_routing_rules`**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| stack_id | FK → stacks | Which stack definition |
| event_source_type | String(50) | Source filter |
| event_type_pattern | String(200) | Glob/regex pattern (e.g. `vm.*`, `alert.critical`) |
| transition_signal | String(100) | Signal name to send to StackLifecycleWorkflow |
| filter_expression | Text, nullable | Optional condition (e.g. `event.severity >= 'critical'`) |
| is_active | Boolean | |

**`event_log`** (append-only, for audit and debugging)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| source_id | FK → event_sources | |
| event_type | String(200) | |
| payload | JSONB | |
| target_instance_id | FK → stack_instances, nullable | Resolved target |
| transition_triggered | String(100), nullable | Which transition, if any |
| received_at | DateTime | |

#### Event Processing Pipeline

```
Event received (webhook / poll / internal emit)
  → Parse & normalize to NimbusEvent schema
  → Identify target stack instance (via resource_id lookup in deployed_components)
  → Match against event_routing_rules for that stack definition
  → If match: send Temporal signal to StackLifecycleWorkflow
  → Log to event_log
```

For **cloud provider polling** (e.g. Proxmox has no push events):
- Temporal Schedule polls provider API every N seconds
- Compares current state to last known state
- Emits synthetic events for changes (vm.started, vm.stopped, task.completed)

#### Task Breakdown (~12 tasks)

1. **Migration** — `event_sources`, `event_routing_rules`, `event_log` tables + permissions
2. **SQLAlchemy Models** — EventSource, EventRoutingRule, EventLog
3. **Event Bus Service** — Receive, normalize, route, log events
4. **Webhook Receiver** — REST endpoint for external webhooks (signed, validated)
5. **Cloud Event Poller** — Temporal Schedule per cloud backend, polls for changes
6. **Proxmox Event Poller** — Concrete poller: task log, VM status changes
7. **Nimbus Internal Event Emitter** — Emit events from existing services (deploy, approve, drift, etc.)
8. **Event Router** — Match events against rules, send signals to Temporal workflows
9. **GraphQL API** — Event source CRUD, routing rule CRUD, event log queries
10. **Event Source Configuration UI** — Manage sources per landing zone
11. **Event Routing Rule Editor** — Per-stack rule definition (part of stack editor)
12. **Event Log Viewer** — Filterable event stream (per stack instance, per environment)

#### Permissions (4)
| Permission | Tier |
|-----------|------|
| `events:source:manage` | Provider Admin |
| `events:rules:manage` | Tenant Admin |
| `events:log:read` | Read-Only |
| `events:webhook:receive` | System (API key auth) |

---

### Phase 16: Real-time & Caching (Valkey)
**Status**: Backlog (renumbered from old Phase 13)
**Goal**: Valkey for caching and Socket.IO pub/sub, GraphQL subscriptions, live deployment status.
**Depends on**: Phase 8 (CMDB), Phase 9 (Notifications)

*(Content unchanged from old Phase 13 — Valkey Docker Compose, Socket.IO, GraphQL subscriptions,
caching layer. Now also supports real-time event streaming for Phase 15.)*

Core deliverables:
- Valkey added to Docker Compose (`valkey/valkey:8-alpine`, port 6379)
- Socket.IO server integration with Valkey adapter
- Room-based subscriptions (tenant, user, resource, stack_instance)
- GraphQL subscriptions for deployment status, state machine changes, events
- Real-time resource state updates
- Live notification delivery
- Caching layer (permissions, tenant config)

---

### Phases 17–26: Remaining Phases (Renumbered)

| New # | Old # | Name | Changes |
|-------|-------|------|---------|
| 17 | 14 | Advanced Audit | Depends on Phase 16 (Valkey). Unchanged otherwise. |
| 18 | 15 | MFA & HSM + JIT | Unchanged. |
| 19 | 16 | Impersonation | Unchanged. |
| 20 | 17 | Drift Detection | Now operates on `deployed_components` + `stack_instances` instead of raw Pulumi stacks. Drift triggers events for stack state machines. |
| 21 | 18 | Additional Cloud Providers | Each provider adds: CloudProviderInterface impl + components + image catalog + event poller. Follows Phase 13 (Proxmox) pattern. |
| 22 | 19 | Cost Management | Cost linked to deployed_components and stack_instances. Per-environment + per-stack cost rollup. |
| 23 | — | **VM Agent** (NEW) | Lightweight agent deployed with every VM. Reports OS/app metrics. Emits events to event bus. Enables in-guest operations (script execution, config management). Depends on Phase 15 (event bus). |
| 24 | 20 | Monitoring & Observability | Prometheus, Grafana, Loki. Stack health dashboards. |
| 25 | 21 | Production Hardening | Security audit, performance, documentation. |
| 26 | 22 | Enterprise Architecture Management | Application portfolio, business capabilities, tech radar. Now includes topology → stack → component drill-down from app layer. |

---

## Revised Dependency Graph

```
Phases 1-10 (COMPLETE)
  │
  ├─► Phase 11: Component Model & Resolver Framework
  │     └─► Phase 12: Pulumi Execution Engine
  │           └─► Phase 13: Proxmox Provider (end-to-end validation)
  │                 └─► Phase 14: Stacks, State Machines & Lifecycle
  │                       └─► Phase 15: Event Bus & Cloud Events
  │                             ├─► Phase 20: Drift Detection
  │                             ├─► Phase 23: VM Agent
  │                             └─► Phase 21: Additional Cloud Providers
  │
  ├─► Phase 16: Real-time & Caching (Valkey)
  │     └─► Phase 17: Advanced Audit
  │     └─► (supports Phase 15 event streaming)
  │
  ├─► Phase 18: MFA & HSM + JIT
  ├─► Phase 19: Impersonation
  ├─► Phase 22: Cost Management (after Phase 13+)
  ├─► Phase 24: Monitoring & Observability
  ├─► Phase 25: Production Hardening
  └─► Phase 26: Enterprise Architecture (after Phase 14, 8, 5)
```

Critical path: **11 → 12 → 13 → 14 → 15**

This is the infrastructure automation spine. Everything else can proceed in parallel
where dependencies allow.

---

## Migration from Current State

### What carries forward unchanged:
- All Phase 1-10 work
- Landing zone backend (migrations 058-063, services, GraphQL) — continues to work
- Landing zone frontend (list/detail pages) — continues to work
- IPAM system — becomes the backend for the IPAM Resolver
- Topology system — topologies now contain stack instances and component instances
- Workflow editor — reused for lifecycle workflows and state machine editor
- Approval system — reused for deployment approval gates

### What changes:
- **Phase 12 (old Pulumi Integration) is superseded** by new Phases 11-12
- `pulumi_templates` → replaced by `components` (richer model with typed I/O, resolvers, versioning)
- `pulumi_stacks` → replaced by `deployed_components` (execution instances)
- `pulumi_template_constraints` → replaced by `component_governance`
- Deployment model gains `stack_instance_id` linkage
- Landing zones gain `system_services_topology_id` and resolver configurations
- Environment templates gain `mandatory_components`

### What's new:
- Component model with typed contracts
- Resolver framework (platform services for deploy-time resolution)
- Stack model with state machines
- Event bus for cloud/monitoring/agent event ingestion
- VM Agent (Phase 23)
- 4 additional phases (26 total, up from 22)

---

## Resolved Design Decisions (2026-02-14)

1. **Stack editor**: Use a **specialized, concise editor** (not the Rete.js topology canvas).
   The stack editor includes: component slot list with parameter wiring, stack-level parameter
   definition panel, Monaco code editor (the open-source editor VS Code uses) for Pulumi scripts,
   and the state machine editor. This is more focused than the free-form topology canvas.

2. **Resolver caching**: **No caching — always fresh.** Every resolution call hits the live
   service. This avoids stale data issues (e.g. IPAM returning an already-allocated IP).
   No Valkey dependency for Phase 12.

3. **Component marketplace**: **Provider-level components/stacks ARE the shared catalog.**
   Components and stacks defined at provider level (tenant_id = NULL) are visible to all tenants
   under that provider. This is the built-in sharing mechanism. No cross-installation sharing
   is planned.

4. **State machine complexity**: **No limits.** State machines can be as complex as needed.
   The system does not impose caps on states or transitions. Complexity is the stack author's
   responsibility.

5. **Fork strategy**: **Forks are fully independent — no merge back.** Once a tenant forks a
   provider stack, it becomes the tenant's own artifact. If the provider updates the original,
   the fork is unaffected. The tenant can choose to create a new fork from the updated original,
   but there is no automated merge, diff, or reconciliation mechanism. The forked_from_id is
   kept for lineage tracking only (informational, not functional).
