# Phase 12: Pulumi Integration — Templates + Monaco Editor + Governance

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Infrastructure-as-Code integration using Pulumi Automation API, with a Monaco code editor for authoring templates, per-tenant governance constraints, and Temporal workflows for stack operations.

*Was Phase 8. Now Phase 12. Refined 2026-02-09.*

## Dependencies
- Phase 11 complete (Proxmox provider as reference implementation)
- Phase 5 complete (semantic layer provides providers, resource types, type mappings)
- Phase 10 complete (approval workflows for deployment gates)
- Phase 1 Temporal setup (worker, client)

## Key Decisions
- **LocalWorkspace** — Pulumi runs in the backend process, state stored in MinIO
- **Templates ARE Pulumi programs** — TypeScript or Python code stored in DB, edited via Monaco
- **Governance via constraints** — Per-tenant parameter limits, allow/deny lists on templates
- **Approval integration** — Deployments can optionally gate through Phase 10 approval chains
- **Saga pattern** — Failed deployments trigger compensation (destroy) automatically

## Data Model

### `pulumi_templates`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | String(200), unique | |
| display_name | String(200) | |
| description | Text | |
| semantic_type_id | FK → semantic_resource_types | What abstract type this creates |
| provider_id | FK → semantic_providers | Which provider |
| provider_resource_type_id | FK → semantic_provider_resource_types, nullable | Specific resource type |
| language | String(20) | 'typescript' / 'python' |
| code | Text | Pulumi program source |
| exposed_parameters | JSONB | Which params users see |
| default_values | JSONB | |
| version | Integer | |
| is_published | Boolean | |
| is_system | Boolean | |
| created_by | FK → users | |
| timestamps + soft_delete | | |

### `pulumi_template_constraints`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| template_id | FK → pulumi_templates | |
| tenant_id | FK → tenants | |
| parameter_constraints | JSONB | min/max/allowed per param |
| is_allowed | Boolean | |
| max_instances | Integer, nullable | |
| timestamps | | |
| **Unique** | (template_id, tenant_id) | |

### `pulumi_stacks`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| template_id | FK → pulumi_templates | |
| tenant_id | FK → tenants | |
| stack_name | String(200) | |
| parameters | JSONB | Actual values used |
| status | String(20) | pending/deploying/deployed/failed/destroying/destroyed |
| outputs | JSONB | Stack outputs |
| pulumi_state_url | String(500) | MinIO path |
| last_deployed_at | DateTime | |
| deployed_by | FK → users | |
| error_message | Text | |
| timestamps + soft_delete | | |
| **Unique** | (tenant_id, stack_name) | |

## Temporal Workflows

### PulumiDeployWorkflow
```
validate_template(template_id, parameters, tenant_id)
  → check published, check tenant constraints
pulumi_preview(template_id, parameters, stack_name)
  → dry-run, return diff
[optional] wait_for_approval → ApprovalChainWorkflow (Phase 10)
pulumi_up(template_id, parameters, stack_name)
  → execute, store state in MinIO
record_deployment(stack_id, outputs, status)
  → update DB, audit log, notification
compensation: pulumi_destroy on failure
```

### PulumiDestroyWorkflow
```
validate_stack(stack_id)
pulumi_destroy(stack_name)
  → remove resources, update state
record_destruction(stack_id, status)
```

### PulumiPreviewWorkflow
```
validate_template(template_id, parameters, tenant_id)
pulumi_preview(template_id, parameters, stack_name)
  → return diff without executing
```

## Task Breakdown (12 tasks)

### 12.1: Migration — Tables + Permissions
**File**: `backend/alembic/versions/0XX_pulumi_integration.py`
- Create `pulumi_templates`, `pulumi_template_constraints`, `pulumi_stacks` tables
- Seed permissions: `pulumi:template:read`, `pulumi:template:manage`, `pulumi:stack:deploy`, `pulumi:stack:destroy`, `pulumi:constraint:manage`

### 12.2: SQLAlchemy Models
**File**: `backend/app/models/pulumi_template.py`, `backend/app/models/pulumi_stack.py`
- `PulumiTemplate` — with `constraints`, `stacks` relationships
- `PulumiTemplateConstraint` — with `template_rel`, `tenant_rel`
- `PulumiStack` — with `template_rel`, `tenant_rel`, `deployed_by_rel`

### 12.3: Pulumi Automation API Wrapper
**File**: `backend/app/services/pulumi/automation.py`
- `PulumiAutomation` class wrapping Pulumi LocalWorkspace
- Methods: `create_stack`, `preview`, `up`, `destroy`, `export_state`, `import_state`
- State backend: MinIO (S3-compatible) via Pulumi's self-managed backends
- Language support: TypeScript + Python program generation from template code

### 12.4: Template Service
**File**: `backend/app/services/pulumi/template_service.py`
- CRUD for templates (list, get, create, update, delete)
- Versioning: bump version on code changes
- Code validation: syntax check before save
- Publishing workflow: draft → published

### 12.5: Stack Service
**File**: `backend/app/services/pulumi/stack_service.py`
- CRUD for stacks (list, get, create, destroy)
- Parameter validation against template schema + tenant constraints
- Status tracking: pending → deploying → deployed / failed

### 12.6: Governance Service
**File**: `backend/app/services/pulumi/governance_service.py`
- Constraint management per tenant per template
- allow/deny checks before deployment
- Parameter limit enforcement (min/max/allowed values)
- Max instance count enforcement

### 12.7: Temporal Workflows
**Files**: `backend/app/workflows/pulumi_deploy.py`, `backend/app/workflows/activities/pulumi.py`
- `PulumiDeployWorkflow`: validate → preview → (optional approval) → up → record
- `PulumiDestroyWorkflow`: validate → destroy → record
- `PulumiPreviewWorkflow`: validate → preview → return diff
- Saga rollback: auto-destroy on deployment failure
- Activities: `validate_template`, `pulumi_preview`, `pulumi_up`, `pulumi_destroy`, `record_deployment`

### 12.8: GraphQL API
**Files**: `backend/app/api/graphql/types/pulumi.py`, `queries/pulumi.py`, `mutations/pulumi.py`
- Types: `PulumiTemplateType`, `PulumiStackType`, `PulumiConstraintType`
- Queries: `pulumi_templates`, `pulumi_template`, `pulumi_stacks`, `pulumi_stack`
- Mutations: create/update/delete template, deploy_stack, destroy_stack, preview_stack, manage constraints

### 12.9: Monaco Editor Component
**File**: `frontend/src/app/shared/components/monaco-editor/monaco-editor.component.ts`
- Angular wrapper for Monaco Editor
- Language support: TypeScript, Python
- Readonly mode for viewing published templates
- Theme: matches app dark/light mode

### 12.10: Template Editor Page
**Files**: `frontend/src/app/features/infrastructure/template-editor/template-editor.component.ts`
- Monaco editor for writing Pulumi code
- Parameter definition panel (name, type, description, default, constraints)
- Preview button (runs PulumiPreviewWorkflow)
- Publish toggle
- Route: `/infrastructure/templates/:id`

### 12.11: Template Browser + Stack Management
**Files**: `frontend/src/app/features/infrastructure/template-browser/`, `stack-management/`
- Template browser: list/filter templates, deploy dialog
- Stack management: list stacks, status indicators, destroy confirmation
- Deploy dialog: parameter form generated from template's exposed_parameters
- Routes: `/infrastructure/templates`, `/infrastructure/stacks`

### 12.12: Governance Settings
**File**: `frontend/src/app/features/infrastructure/governance/`
- Per-tenant constraint management (in tenant settings)
- Template allow/deny list
- Parameter constraint editor (min, max, allowed values)
- Max instances setting

## Frontend Routes
- `/infrastructure/templates` — Template browser
- `/infrastructure/templates/:id` — Template editor (Monaco)
- `/infrastructure/stacks` — Stack management
- Tenant settings → Governance tab for template constraints

## Permissions
| Permission | Tier | Description |
|-----------|------|-------------|
| `pulumi:template:read` | Read-Only | View templates |
| `pulumi:template:manage` | Tenant Admin | Create/edit/delete templates |
| `pulumi:stack:deploy` | User | Deploy stacks from published templates |
| `pulumi:stack:destroy` | Tenant Admin | Destroy deployed stacks |
| `pulumi:constraint:manage` | Provider Admin | Manage per-tenant governance constraints |

## Impact on Other Phases
| Phase | Impact |
|-------|--------|
| Phase 5 (Semantic Layer) | Templates link to `semantic_providers` and `semantic_resource_types` via FKs |
| Phase 7 (Visual Planner) | Can generate Pulumi template code from visual architecture diagrams |
| Phase 10 (Approvals) | Deployments optionally gate through approval chains |
| Phase 11 (Proxmox) | First provider to have real Pulumi templates |
| Phase 17 (Drift) | Compares Pulumi stack state vs live resources |
| Phase 18 (Cloud Providers) | Each provider gets Pulumi template definitions |
