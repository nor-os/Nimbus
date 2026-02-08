# Phase 2: Multi-Tenancy Foundation

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Implement tenant hierarchy (Provider → Tenant → Sub-tenant) with Schema per Tenant + RLS isolation, comprehensive quotas, multi-tenant user support, basic compartments, and role placeholders.

## Deliverables
- Tenant and Sub-tenant data models with full attributes
- Virtual root tenant for provider-level user management
- Schema per Tenant + RLS isolation (hardcoded strategy)
- Dynamic RLS policy generation
- Tenant context middleware (request.state + contextvars)
- Tenant-aware query filters
- Comprehensive quota system with configurable enforcement
- Tenant settings table (normalized)
- Soft delete with configurable global retention + scheduled purge
- Tenant data export (GDPR compliance)
- Multi-tenant user support with tenant switching
- Basic Compartment model (foundation for Phase 3 permission scoping, expanded in Phase 5)
- Role placeholder tables (populated by Phase 3)
- Tenant management REST & GraphQL APIs
- Tenant management UI with dashboard

## Dependencies
- Phase 1 complete (auth, database, basic models, Temporal)

---

## Refinement Questions & Decisions

### Q1: Schema Creation Timing
**Question**: How should tenant schema creation be handled?
**Decision**: Synchronous
**Rationale**: Simpler implementation, immediate feedback. Acceptable for expected tenant creation volume.

### Q2: Hierarchy Depth
**Question**: What tenant hierarchy depth to support?
**Decision**: Provider → Tenant → Sub-tenant (3 levels)
**Rationale**: Matches documented architecture. Provides flexibility without unlimited complexity.

### Q3: Tenant Deletion
**Question**: How should tenant deletion work?
**Decision**: Soft delete + scheduled purge
**Rationale**: Safety of soft delete with eventual cleanup. Configurable retention prevents indefinite storage.

### Q4: Isolation Customization
**Question**: Should tenants customize their isolation strategy?
**Decision**: No — hardcoded to Schema per Tenant + RLS
**Rationale**: Reduces complexity. One strategy done well beats four done partially. Revisit if operational experience reveals a need.

### Q5: Required Attributes
**Question**: What attributes required when creating a tenant?
**Decision**: Full - name, parent, contact email, billing info, resource quotas
**Rationale**: Capture all necessary info upfront for proper tenant setup and billing. Isolation strategy is hardcoded (not a tenant choice).

### Q6: Sub-tenant Creation
**Question**: Who can create sub-tenants?
**Decision**: Provider only
**Rationale**: Maintains control over tenant hierarchy. Prevents uncontrolled sprawl.

### Q7: Tenant Config Storage
**Question**: How to store tenant settings?
**Decision**: Separate normalized table (key-value)
**Rationale**: Queryable, auditable, supports typed values and validation.

### Q8: Quotas
**Question**: Include resource quotas in Phase 2?
**Decision**: Yes - comprehensive (users, storage, API calls, resources per type)
**Rationale**: Essential for multi-tenancy. Better to build foundation now.

### Q9: Context Passing
**Question**: How to pass tenant context through application?
**Decision**: Both - request.state for API layer, contextvars for services/background tasks
**Rationale**: Covers all execution contexts. Clean separation of concerns.

### Q10: RLS Management
**Question**: How to manage Row-Level Security policies?
**Decision**: Dynamic policies - generate per tenant
**Rationale**: Per-tenant isolation choices require dynamic policy creation.

### Q11: Quota Enforcement
**Question**: What happens when quota exceeded?
**Decision**: Configurable per-quota (some hard block, some soft warning)
**Rationale**: Different quotas have different business implications.

### Q12: Tenant Switching
**Question**: Should UI support tenant switching?
**Decision**: Multi-tenant users - users can belong to multiple tenants and switch
**Rationale**: Supports consultants, MSPs, users with access to multiple orgs.

### Q13: Purge Schedule
**Question**: How should scheduled purge work?
**Decision**: Configurable global - provider sets retention period for all tenants
**Rationale**: Consistent policy, simpler than per-tenant. Provider controls data lifecycle.

### Q14: Data Export
**Question**: Include tenant data export?
**Decision**: Yes
**Rationale**: GDPR compliance requirement. Essential for enterprise customers.

### Q15: UI Scope
**Question**: What tenant UI features in Phase 2?
**Decision**: Full CRUD + dashboard with stats/quotas
**Rationale**: Complete management capability. Dashboard provides operational visibility.

### Q16: Virtual Root Tenant (Cross-Phase Consistency)
**Question**: How to handle provider-level users vs tenant-level users?
**Decision**: Virtual root tenant
**Rationale**: Users can be created at provider-level or tenant-level. Provider-level users are modeled via a virtual root tenant (is_root=true) that has no cloud representation but enables consistent user management.

### Q17: Basic Compartments (Cross-Phase Consistency)
**Question**: When to introduce Compartments for permission scoping?
**Decision**: Basic model in Phase 2, expanded in Phase 5
**Rationale**: Phase 3 needs compartment scoping for permissions. Introduce basic Compartment model here, expand with full CMDB features in Phase 5.

### Q18: Role Placeholders (Cross-Phase Consistency)
**Question**: How to handle role seeding for existing tenants when Phase 3 deploys?
**Decision**: Placeholder tables in Phase 2
**Rationale**: Create Role and related tables in Phase 2 with basic structure. Phase 3 populates them and adds full functionality. Avoids migration complexity.

### Q19: Isolation Strategy (Cross-Phase Consistency)
**Question**: What isolation strategy to use?
**Decision**: Hardcoded Schema per Tenant + RLS for all tenants
**Rationale**: Simplifies implementation. Setup wizard no longer asks for isolation choice. All tenants use the same strategy.

---

## Virtual Root Tenant

The system uses a **virtual root tenant** to manage provider-level users:

```
Tenant {
  id: UUID
  is_root: boolean (true for virtual root)
  name: "Provider Root" (for root tenant)
  ...
}
```

- **is_root=true**: Virtual tenant for provider-level user management
- No cloud provider representation (cloud_id is null)
- No schema created (uses core schema)
- Provider-level users belong to this tenant via UserTenant
- Regular tenants have is_root=false

This enables consistent user management:
- All users are associated with tenants via UserTenant
- Provider-level users → UserTenant with root tenant
- Tenant-level users → UserTenant with their tenant(s)

---

## Basic Compartment Model

Basic compartment structure for Phase 3 permission scoping:

```
Compartment {
  id: UUID
  tenant_id: UUID
  parent_id: UUID (nullable, self-ref for nesting)
  name: string
  description: string
  created_at: timestamp
  updated_at: timestamp
}
```

**Phase 2 scope**:
- Basic CRUD operations
- Unlimited nesting
- Used for permission scoping in Phase 3

**Phase 5 expansion**:
- Cloud provider mapping (cloud_id, provider_type)
- CI associations
- Full CMDB integration

---

## Role Placeholder Tables

Tables created in Phase 2, populated by Phase 3:

```
Role {
  id: UUID
  tenant_id: UUID (nullable for system roles)
  name: string
  description: string
  is_system: boolean
  created_at: timestamp
}

UserRole {
  user_id: UUID
  role_id: UUID
  tenant_id: UUID
  granted_at: timestamp
}
```

**Phase 2**: Creates tables, no business logic
**Phase 3**: Adds permissions, role management, RBAC/ABAC engine

---

## Tasks

### Backend Tasks

#### Task 2.1: Tenant Data Models
**Complexity**: L
**Description**: Create tenant, sub-tenant, and related models with full attributes including virtual root tenant support.
**Files**:
- `backend/app/models/tenant.py` - Tenant model
- `backend/app/models/tenant_settings.py` - TenantSettings model (key-value)
- `backend/app/models/tenant_quota.py` - TenantQuota model
- `backend/app/models/user_tenant.py` - UserTenant association (multi-tenant users)
- `backend/app/schemas/tenant.py` - Pydantic schemas
- `backend/alembic/versions/002_tenants.py` - Migration
**Acceptance Criteria**:
- [ ] Tenant model with: id, name, parent_id (self-ref), provider_id, isolation_strategy, contact_email, billing_info (JSON), is_root, default_isolation_strategy, created_at, updated_at, deleted_at
- [ ] is_root=true for virtual root tenant (provider-level user management)
- [ ] Virtual root tenant created during first-run wizard
- [ ] Tenant hierarchy: Provider → Tenant → Sub-tenant (max 3 levels enforced, root tenant is level 0)
- [ ] TenantSettings: id, tenant_id, key, value, value_type, created_at, updated_at
- [ ] TenantQuota: id, tenant_id, quota_type, limit, current_usage, enforcement (hard/soft), created_at, updated_at
- [ ] Quota types enum: users, storage_bytes, api_calls_daily, resources_compute, resources_network, resources_storage, resources_database
- [ ] UserTenant: user_id, tenant_id, is_default, joined_at (for multi-tenant users)
- [ ] Isolation strategy: always schema_with_rls (hardcoded, no enum needed)
- [ ] Soft delete support on Tenant (except root tenant)
**Tests**:
- [ ] Tenant hierarchy enforced (no 4th level)
- [ ] Virtual root tenant cannot be deleted
- [ ] Settings CRUD works
- [ ] Quota tracking works
- [ ] User can belong to multiple tenants

---

#### Task 2.2: Tenant Context System
**Complexity**: M
**Description**: Implement tenant context passing via request.state and contextvars.
**Files**:
- `backend/app/core/tenant_context.py` - TenantContext class with contextvars
- `backend/app/core/middleware.py` - Update to extract tenant from JWT and set context
- `backend/app/api/deps.py` - Add get_current_tenant dependency
**Acceptance Criteria**:
- [ ] TenantContext class with get/set methods
- [ ] Contextvar for async-safe tenant access in services
- [ ] Middleware extracts tenant_id from JWT, sets in request.state and contextvar
- [ ] get_current_tenant dependency for route handlers
- [ ] Context available in Temporal activities via workflow context
- [ ] Tenant context cleared after request
**Tests**:
- [ ] Context set correctly from JWT
- [ ] Context accessible in nested async calls
- [ ] Context isolated between concurrent requests

---

#### Task 2.3: Dynamic Schema Management
**Complexity**: L
**Description**: Create and manage tenant schemas (Schema per Tenant + RLS).
**Files**:
- `backend/app/services/tenant/schema_manager.py` - Schema creation/deletion
- `backend/app/db/tenant_schema.py` - Tenant-specific table definitions
**Acceptance Criteria**:
- [ ] create_tenant_schema(tenant_id, isolation_strategy) - creates appropriate schema
- [ ] Schema naming: `nimbus_tenant_{tenant_id}`
- [ ] For schema_with_rls and schema_only: create schema with tenant tables
- [ ] For rls_only: use shared schema with tenant_id column
- [ ] For database_per_tenant: create separate database (connection pooling)
- [ ] drop_tenant_schema(tenant_id) - for purge process
- [ ] Schema creation is synchronous (blocks until complete)
**Tests**:
- [ ] Schema created for each isolation type
- [ ] Tables created in correct schema
- [ ] Schema dropped cleanly

---

#### Task 2.4: Dynamic RLS Policies
**Complexity**: L
**Description**: Generate and apply Row-Level Security policies per tenant.
**Files**:
- `backend/app/services/tenant/rls_manager.py` - RLS policy generation
- `backend/app/db/rls_policies.sql` - Policy templates
**Acceptance Criteria**:
- [ ] create_rls_policies(tenant_id, schema_name) - generates policies for tenant
- [ ] Policies use session variable `app.current_tenant_id`
- [ ] Set session variable on each connection from pool
- [ ] Policies for: SELECT, INSERT, UPDATE, DELETE
- [ ] Policy prevents cross-tenant data access
- [ ] drop_rls_policies(tenant_id) - removes policies
- [ ] Bypass for provider-level operations (with explicit flag)
**Tests**:
- [ ] RLS blocks cross-tenant SELECT
- [ ] RLS blocks cross-tenant INSERT
- [ ] Provider bypass works when enabled
- [ ] Session variable set correctly

---

#### Task 2.5: Tenant-Aware Database Sessions
**Complexity**: M
**Description**: Update database session management for tenant context.
**Files**:
- `backend/app/db/session.py` - Update async session factory
- `backend/app/db/tenant_session.py` - Tenant-aware session wrapper
**Acceptance Criteria**:
- [ ] Session automatically sets `app.current_tenant_id` variable
- [ ] Session routes to correct schema based on tenant_id
- [ ] Connection pool per tenant for database_per_tenant isolation
- [ ] Automatic schema prefix for queries when using schema isolation
- [ ] Session context manager handles tenant setup/teardown
**Tests**:
- [ ] Queries go to correct schema
- [ ] RLS variable set on session
- [ ] Cross-tenant query blocked by RLS

---

#### Task 2.6: Quota Service
**Complexity**: M
**Description**: Implement quota tracking and enforcement.
**Files**:
- `backend/app/services/tenant/quota_service.py` - Quota management
- `backend/app/core/quota_middleware.py` - Request-level quota checks
**Acceptance Criteria**:
- [ ] check_quota(tenant_id, quota_type, increment=1) - checks and optionally increments
- [ ] Returns: allowed (bool), current_usage, limit, enforcement_type
- [ ] Hard enforcement: raises QuotaExceededError
- [ ] Soft enforcement: logs warning, returns allowed=True with exceeded flag
- [ ] increment_usage(tenant_id, quota_type, amount) - updates current usage
- [ ] decrement_usage(tenant_id, quota_type, amount) - for deletions
- [ ] reset_daily_quotas() - Temporal scheduled workflow for daily quotas (API calls)
- [ ] Quota check middleware for API endpoints (configurable)
**Tests**:
- [ ] Hard quota blocks operation
- [ ] Soft quota allows with warning
- [ ] Usage tracking accurate
- [ ] Daily reset works

---

#### Task 2.7: Tenant Service
**Complexity**: L
**Description**: Core tenant management service.
**Files**:
- `backend/app/services/tenant/__init__.py`
- `backend/app/services/tenant/service.py` - TenantService
**Acceptance Criteria**:
- [ ] create_tenant() - validates, creates model, creates schema, sets up quotas
- [ ] get_tenant(tenant_id) - retrieves tenant with settings and quotas
- [ ] update_tenant(tenant_id, data) - updates allowed fields
- [ ] delete_tenant(tenant_id) - soft delete, schedules purge
- [ ] list_tenants(provider_id, include_deleted=False) - with pagination
- [ ] get_tenant_hierarchy(tenant_id) - returns parent chain
- [ ] Validates hierarchy depth (max 3 levels)
- [ ] Provider-only check for sub-tenant creation
**Tests**:
- [ ] Tenant creation flow complete
- [ ] Hierarchy validation works
- [ ] Soft delete marks correctly
- [ ] List pagination works

---

#### Task 2.8: Tenant Purge Scheduler
**Complexity**: M
**Description**: Temporal scheduled workflow to purge soft-deleted tenants after retention period.
**Files**:
- `backend/app/workflows/tenant_purge.py` - Purge workflow
- `backend/app/workflows/activities/tenant_purge.py` - Purge activity
- `backend/app/services/tenant/purge_service.py` - Purge logic
**Acceptance Criteria**:
- [ ] Temporal Schedule: daily check for tenants past retention
- [ ] Retention period from provider settings (default 30 days)
- [ ] Purge process: drop schema, drop RLS policies, hard delete records
- [ ] Purge creates audit log entry before deletion
- [ ] Optional: export tenant data before purge (configurable)
- [ ] Purge is idempotent (can retry safely)
**Tests**:
- [ ] Tenants within retention not purged
- [ ] Tenants past retention are purged
- [ ] Audit log created
- [ ] Schema and data removed

---

#### Task 2.9: Tenant Data Export
**Complexity**: M
**Description**: GDPR-compliant tenant data export functionality.
**Files**:
- `backend/app/services/tenant/export_service.py` - Export service
- `backend/app/tasks/tenant_export.py` - Async export task
- `backend/app/api/v1/endpoints/tenant_export.py` - Export endpoints
**Acceptance Criteria**:
- [ ] `POST /api/v1/tenants/{id}/export` - initiates export job
- [ ] `GET /api/v1/tenants/{id}/export/{job_id}` - check status
- [ ] `GET /api/v1/tenants/{id}/export/{job_id}/download` - download file
- [ ] Export includes: tenant settings, users, quotas, all tenant-schema data
- [ ] Export format: ZIP containing JSON files
- [ ] Export stored in MinIO with expiration (configurable, default 7 days)
- [ ] Audit log for export requests
**Tests**:
- [ ] Export job created and tracked
- [ ] Export file contains all data
- [ ] Download works with signed URL
- [ ] File expires correctly

---

#### Task 2.10: Tenant REST API
**Complexity**: M
**Description**: REST endpoints for tenant management.
**Files**:
- `backend/app/api/v1/endpoints/tenants.py` - Tenant endpoints
**Acceptance Criteria**:
- [ ] `GET /api/v1/tenants` - list tenants (provider sees all, tenant sees own + children)
- [ ] `POST /api/v1/tenants` - create tenant (provider only)
- [ ] `GET /api/v1/tenants/{id}` - get tenant details with settings/quotas
- [ ] `PATCH /api/v1/tenants/{id}` - update tenant
- [ ] `DELETE /api/v1/tenants/{id}` - soft delete tenant
- [ ] `GET /api/v1/tenants/{id}/hierarchy` - get parent/child tree
- [ ] `GET /api/v1/tenants/{id}/stats` - usage statistics
- [ ] `POST /api/v1/tenants/{id}/settings` - update settings
- [ ] `PATCH /api/v1/tenants/{id}/quotas` - update quotas (provider only)
- [ ] Provider-level permission checks
**Tests**:
- [ ] CRUD operations work
- [ ] Permission checks enforced
- [ ] Hierarchy endpoint returns correct tree

---

#### Task 2.11: Tenant GraphQL API
**Complexity**: M
**Description**: GraphQL schema for tenant operations.
**Files**:
- `backend/app/api/graphql/types/tenant.py` - Tenant types
- `backend/app/api/graphql/queries/tenants.py` - Tenant queries
- `backend/app/api/graphql/mutations/tenants.py` - Tenant mutations
**Acceptance Criteria**:
- [ ] Query: tenant(id), tenants(filter, pagination), tenantHierarchy(id)
- [ ] Query: tenantStats(id) - usage and quota statistics
- [ ] Mutation: createTenant, updateTenant, deleteTenant
- [ ] Mutation: updateTenantSettings, updateTenantQuotas
- [ ] Tenant type includes: settings, quotas, parent, children relationships
- [ ] Proper authorization checks
**Tests**:
- [ ] Queries return correct data
- [ ] Mutations update correctly
- [ ] Nested relationships resolve

---

#### Task 2.12: User Multi-Tenant Support
**Complexity**: M
**Description**: Enable users to belong to multiple tenants with switching.
**Files**:
- `backend/app/services/auth/service.py` - Update for multi-tenant
- `backend/app/api/v1/endpoints/auth.py` - Add tenant switching
- `backend/app/schemas/auth.py` - Update token schema
**Acceptance Criteria**:
- [ ] User can be associated with multiple tenants via UserTenant
- [ ] JWT includes list of tenant_ids user has access to
- [ ] JWT has current_tenant_id for active context
- [ ] `POST /api/v1/auth/switch-tenant` - switch active tenant
- [ ] `GET /api/v1/auth/tenants` - list user's accessible tenants
- [ ] Token refresh maintains tenant context
- [ ] Default tenant used on login (from UserTenant.is_default)
**Tests**:
- [ ] User with multiple tenants can switch
- [ ] Switch issues new token with updated tenant
- [ ] Permissions scoped to current tenant

---

#### Task 2.13: Basic Compartment Model
**Complexity**: M
**Description**: Create basic compartment model for permission scoping (expanded in Phase 5).
**Files**:
- `backend/app/models/compartment.py` - Compartment model
- `backend/app/services/tenant/compartment_service.py` - Basic compartment service
- `backend/app/api/v1/endpoints/compartments.py` - Compartment endpoints
- `backend/app/schemas/compartment.py` - Pydantic schemas
**Acceptance Criteria**:
- [ ] Compartment: id, tenant_id, parent_id (self-ref), name, description, created_at, updated_at
- [ ] Unlimited nesting (recursive parent-child)
- [ ] Circular reference prevention
- [ ] Basic CRUD operations
- [ ] `GET /api/v1/compartments` - list compartments (flat or tree)
- [ ] `POST /api/v1/compartments` - create compartment
- [ ] `PATCH /api/v1/compartments/{id}` - update compartment
- [ ] `DELETE /api/v1/compartments/{id}` - delete (fails if has children)
- [ ] GraphQL: compartment(id), compartments(tenantId), compartmentTree
- [ ] Note: cloud_id and provider_type added in Phase 5
**Tests**:
- [ ] Compartment CRUD works
- [ ] Nesting works correctly
- [ ] Circular refs prevented
- [ ] Cannot delete with children

---

#### Task 2.14: Role Placeholder Tables
**Complexity**: S
**Description**: Create role placeholder tables for Phase 3 to populate.
**Files**:
- `backend/app/models/role.py` - Role model (placeholder)
- `backend/app/models/user_role.py` - UserRole association (placeholder)
- `backend/alembic/versions/002b_role_placeholders.py` - Migration
**Acceptance Criteria**:
- [ ] Role: id, tenant_id (nullable for system), name, description, is_system, created_at
- [ ] UserRole: user_id, role_id, tenant_id, granted_at
- [ ] No business logic (placeholder for Phase 3)
- [ ] Tables created in migration
- [ ] Foreign keys to User and Tenant
- [ ] Note: permissions, inheritance, ABAC added in Phase 3
**Tests**:
- [ ] Tables exist after migration
- [ ] Foreign keys work

---

### Frontend Tasks

#### Task 2.15: Tenant Service (Frontend)
**Complexity**: M
**Description**: Angular service for tenant management.
**Files**:
- `frontend/src/app/core/services/tenant.service.ts` - Tenant API service
- `frontend/src/app/core/services/tenant-context.service.ts` - Active tenant state
- `frontend/src/app/core/models/tenant.model.ts` - Tenant types
**Acceptance Criteria**:
- [ ] CRUD methods calling REST/GraphQL API
- [ ] Tenant context as signal (currentTenant)
- [ ] List of accessible tenants as signal
- [ ] switchTenant() method updates context and refreshes token
- [ ] Tenant context persisted in localStorage
**Tests**:
- [ ] Service methods call correct endpoints
- [ ] Tenant switch updates signals

---

#### Task 2.16: Tenant Switcher Component
**Complexity**: S
**Description**: UI component for switching between tenants.
**Files**:
- `frontend/src/app/shared/components/tenant-switcher/tenant-switcher.component.ts`
- `frontend/src/app/shared/components/tenant-switcher/tenant-switcher.component.html`
**Acceptance Criteria**:
- [ ] Dropdown showing accessible tenants
- [ ] Current tenant highlighted
- [ ] Click switches tenant
- [ ] Shows tenant hierarchy (indent sub-tenants)
- [ ] Integrated into header component
- [ ] Hidden if user has only one tenant
**Tests**:
- [ ] Dropdown lists all tenants
- [ ] Switch calls service

---

#### Task 2.17: Tenant List Page
**Complexity**: M
**Description**: Page listing all tenants with filtering and actions.
**Files**:
- `frontend/src/app/features/tenants/tenant-list/tenant-list.component.ts`
- `frontend/src/app/features/tenants/tenant-list/tenant-list.component.html`
**Acceptance Criteria**:
- [ ] Table with: name, type (tenant/sub-tenant), isolation, status, created
- [ ] Filter by: status (active/deleted), type
- [ ] Search by name
- [ ] Actions: view, edit, delete
- [ ] Create tenant button (provider only)
- [ ] Pagination
- [ ] Show hierarchy with indentation
**Tests**:
- [ ] List loads and displays
- [ ] Filters work
- [ ] Pagination works

---

#### Task 2.18: Tenant Create/Edit Form
**Complexity**: M
**Description**: Form for creating and editing tenants.
**Files**:
- `frontend/src/app/features/tenants/tenant-form/tenant-form.component.ts`
- `frontend/src/app/features/tenants/tenant-form/tenant-form.component.html`
**Acceptance Criteria**:
- [ ] Fields: name, parent (dropdown), contact email, billing info
- [ ] Quota configuration section (all quota types with limits)
- [ ] Quota enforcement toggle (hard/soft) per quota
- [ ] Validation for all required fields
- [ ] Create vs Edit mode
- [ ] Parent dropdown only shows valid parents (respects 3-level limit)
**Tests**:
- [ ] Form validation works
- [ ] Create submits correctly
- [ ] Edit loads and saves

---

#### Task 2.19: Tenant Dashboard
**Complexity**: L
**Description**: Dashboard view showing tenant statistics and quota usage.
**Files**:
- `frontend/src/app/features/tenants/tenant-dashboard/tenant-dashboard.component.ts`
- `frontend/src/app/features/tenants/tenant-dashboard/tenant-dashboard.component.html`
- `frontend/src/app/features/tenants/tenant-dashboard/components/quota-card/quota-card.component.ts`
- `frontend/src/app/features/tenants/tenant-dashboard/components/tenant-tree/tenant-tree.component.ts`
**Acceptance Criteria**:
- [ ] Overview cards: total tenants, active, pending deletion
- [ ] Quota usage cards with progress bars for each quota type
- [ ] Quota status indicators (ok, warning, exceeded)
- [ ] Tenant hierarchy tree visualization
- [ ] Recent tenant activity (audit log preview)
- [ ] Quick actions: create tenant, view all
- [ ] Responsive layout
**Tests**:
- [ ] Dashboard loads with data
- [ ] Quota cards show correct usage
- [ ] Tree renders hierarchy

---

#### Task 2.20: Tenant Settings Page
**Complexity**: M
**Description**: Page for managing tenant settings and viewing details.
**Files**:
- `frontend/src/app/features/tenants/tenant-settings/tenant-settings.component.ts`
- `frontend/src/app/features/tenants/tenant-settings/tenant-settings.component.html`
**Acceptance Criteria**:
- [ ] Tabs: General, Quotas, Settings, Data Export
- [ ] General: view/edit basic info, see hierarchy position
- [ ] Quotas: view/edit all quotas with current usage
- [ ] Settings: key-value editor for tenant settings
- [ ] Data Export: request export, view pending/completed exports, download
- [ ] Danger zone: delete tenant with confirmation
**Tests**:
- [ ] Tabs switch correctly
- [ ] Settings save correctly
- [ ] Export request works

---

## Phase Completion Checklist

- [ ] All 20 tasks completed
- [ ] File headers follow documentation standards
- [ ] Function indices updated via script
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] Migration runs cleanly on fresh database
- [ ] Multi-tenant isolation verified:
  - [ ] Schema creation works for all isolation types
  - [ ] RLS policies block cross-tenant access
  - [ ] Tenant context propagates correctly
- [ ] Quota enforcement verified:
  - [ ] Hard quotas block operations
  - [ ] Soft quotas log warnings
- [ ] UI tested end-to-end:
  - [ ] Tenant CRUD works
  - [ ] Tenant switching works
  - [ ] Dashboard displays correctly
  - [ ] Data export works

## Dependencies for Next Phase
Phase 3 (Permission System) will build on:
- Tenant context system (permissions scoped to tenant)
- User-Tenant associations (for permission assignment)
- Quota service patterns (similar enforcement approach)
- Compartment model (for permission scoping)
- Role placeholder tables (to populate with permissions)
- Virtual root tenant (for provider-level permissions)

## Notes & Learnings
[To be filled during implementation]
