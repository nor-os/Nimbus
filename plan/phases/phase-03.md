# Phase 3: Permission System

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Implement RBAC + ABAC hybrid permission model with action-level granularity, nested groups, custom roles per tenant, advanced ABAC expressions, and comprehensive permission management UI.

## Deliverables
- Permission model with action-level granularity
- Role system with inheritance and direct permissions
- Custom roles per tenant
- Nested group hierarchy
- Advanced ABAC engine with DSL expressions
- Optional compartment scoping
- Permission evaluation engine (no caching)
- Full policy API (check + list permissions)
- Configurable approval for permission changes
- 8+ comprehensive system roles
- Break-glass emergency access procedure
- Advanced UI: role builder, ABAC editor, permission simulator

## Dependencies
- Phase 2 complete (tenant context, user-tenant associations)

---

## Refinement Questions & Decisions

### Q1: Permission Granularity
**Question**: How granular should permissions be?
**Decision**: Action level
**Rationale**: Provides fine-grained control (e.g., 'cmdb:resource:create') without per-instance complexity.

### Q2: Role Structure
**Question**: How should roles be structured?
**Decision**: Role + permissions
**Rationale**: Roles as permission collections, plus users can have direct permissions for flexibility.

### Q3: Custom Roles
**Question**: Should custom roles be supported?
**Decision**: Custom per tenant
**Rationale**: Each tenant can create roles matching their organizational structure.

### Q4: Group Membership
**Question**: How should group membership work?
**Decision**: Nested groups
**Rationale**: Hierarchical groups mirror organizational structures (teams within departments).

### Q5: ABAC Conditions
**Question**: What ABAC conditions should be supported?
**Decision**: Advanced
**Rationale**: Full flexibility with time, IP, resource attributes, and custom expressions.

### Q6: Conflict Resolution
**Question**: How should permission conflicts be resolved?
**Decision**: Most specific wins
**Rationale**: Intuitive behavior - resource-level overrides type-level overrides global.

### Q7: Compartment Scoping
**Question**: Should permissions support compartment scoping?
**Decision**: Optional scoping
**Rationale**: Flexibility to scope permissions to compartments when needed, tenant-wide by default.

### Q8: Default Permissions
**Question**: How should default permissions work for new users?
**Decision**: Configurable per source
**Rationale**: Different onboarding for local users vs SSO users makes sense organizationally.

### Q9: Permission Caching
**Question**: Should permission checks be cached?
**Decision**: No caching
**Rationale**: Always accurate, simplifies invalidation. Optimize later if needed.

### Q10: Evaluation API
**Question**: How should permission evaluation be exposed?
**Decision**: Full policy API
**Rationale**: UI needs to check permissions and show users what they can do.

### Q11: Change Approval
**Question**: Should permission changes require approval?
**Decision**: Configurable (default no, can be required)
**Rationale**: Flexibility for different security postures. Some tenants need change control.

### Q12: UI Scope
**Question**: What permission management UI features?
**Decision**: Advanced
**Rationale**: Full capability with role builder, ABAC editor, and permission simulator.

### Q13: System Roles
**Question**: What default system roles?
**Decision**: Comprehensive (8+ roles)
**Rationale**: Cover common organizational patterns out of the box.

### Q14: Expression Format
**Question**: How should ABAC expressions be defined?
**Decision**: Simple DSL
**Rationale**: Human-readable expressions like 'resource.cost < 1000 AND resource.env == "prod"'.

### Q15: Emergency Access
**Question**: Should there be an emergency bypass mechanism?
**Decision**: Break-glass procedure (split across phases)
**Rationale**: Basic break-glass in Phase 3 (multi-approval, time-limited). HSM-required break-glass in Phase 12.

### Q16: Permission Format (Cross-Phase Consistency)
**Question**: How to handle CMDB-specific permissions?
**Decision**: Hybrid format
**Rationale**: Generic permissions + class-specific permissions. Example: `cmdb:ci:create` (generic) + `cmdb:ci:create:virtualmachine` (class-specific).

### Q17: Notifications (Cross-Phase Consistency)
**Question**: Break-glass needs notifications but notification system is Phase 15?
**Decision**: Placeholder implementation
**Rationale**: Use logging and simple email (if SMTP configured) in Phase 3. Replace with full notification service in Phase 15.

### Q18: Compartment Source (Cross-Phase Consistency)
**Question**: Where do compartments come from for permission scoping?
**Decision**: Phase 2 Compartment model
**Rationale**: Basic Compartment model created in Phase 2, used for permission scoping in Phase 3, expanded with CMDB features in Phase 5.

---

## System Roles Definition

| Role | Tier | Description |
|------|------|-------------|
| Provider Admin | Provider | Full system access, manages all tenants |
| Provider Auditor | Provider | Read-only access to all tenants for compliance |
| Tenant Admin | Tenant Admin | Full access within tenant |
| Security Admin | Tenant Admin | Manages permissions, users, groups within tenant |
| Network Admin | User | Manages network resources (VPCs, subnets, etc.) |
| Power User | User | Create/modify resources, no admin functions |
| Member | User | Standard access, create within quotas |
| Read-only | Read-only | View-only access to tenant resources |

---

## Permission Format (Hybrid)

```
# Generic format
{domain}:{resource}:{action}

# Class-specific format (for CMDB)
{domain}:{resource}:{action}:{subtype}

Examples - Generic:
- cmdb:ci:create              # Create any CI
- cmdb:ci:read                # Read any CI
- cmdb:ci:update              # Update any CI
- cmdb:ci:delete              # Delete any CI
- cmdb:compartment:*          # Wildcard for all actions
- users:user:create
- users:group:manage
- tenants:settings:update
- workflows:approval:approve
- audit:logs:read
- audit:logs:export

Examples - Class-specific (evaluated after generic):
- cmdb:ci:create:virtualmachine    # Create VMs only
- cmdb:ci:create:database          # Create databases only
- cmdb:ci:delete:*                 # Delete any CI class (same as cmdb:ci:delete)

Resolution order (most specific wins):
1. cmdb:ci:create:virtualmachine   (most specific)
2. cmdb:ci:create                  (generic)
3. cmdb:*:*                        (wildcard)
```

---

## ABAC DSL Syntax

```
# Basic comparisons
resource.cost < 1000
resource.environment == "production"
resource.tags.contains("critical")

# Logical operators
resource.cost < 1000 AND resource.environment == "dev"
user.department == "engineering" OR user.role == "admin"
NOT resource.locked

# Context attributes
context.time.hour >= 9 AND context.time.hour <= 17
context.ip IN ["10.0.0.0/8", "192.168.0.0/16"]
context.mfa_verified == true

# Resource attributes
resource.owner == user.id
resource.compartment IN user.allowed_compartments
resource.type == "compute"

# Complex expressions
(resource.cost < 1000 OR user.approval_limit >= resource.cost) AND resource.environment != "production"
```

---

## Tasks

### Backend Tasks

#### Task 3.1: Permission Data Models
**Complexity**: L
**Description**: Create core permission, role, and group models.
**Files**:
- `backend/app/models/permission.py` - Permission model
- `backend/app/models/role.py` - Role model
- `backend/app/models/group.py` - Group model with nesting
- `backend/app/models/user_permission.py` - Direct user permissions
- `backend/app/models/user_role.py` - User-role assignments
- `backend/app/models/user_group.py` - User-group memberships
- `backend/app/models/role_permission.py` - Role-permission assignments
- `backend/app/models/group_permission.py` - Group-permission assignments
- `backend/app/schemas/permission.py` - Pydantic schemas
- `backend/alembic/versions/003_permissions.py` - Migration
**Acceptance Criteria**:
- [ ] Permission: id, domain, resource, action, description, is_system
- [ ] Role: id, tenant_id (null for system), name, description, is_system, is_custom, parent_role_id
- [ ] Group: id, tenant_id, name, description, parent_group_id (for nesting)
- [ ] UserPermission: user_id, permission_id, compartment_id (optional), abac_conditions (JSON), granted_by, granted_at
- [ ] UserRole: user_id, role_id, compartment_id (optional), granted_by, granted_at
- [ ] UserGroup: user_id, group_id, joined_at
- [ ] RolePermission: role_id, permission_id
- [ ] GroupPermission: group_id, permission_id, compartment_id (optional)
- [ ] GroupRole: group_id, role_id
- [ ] Soft delete on roles and groups
**Tests**:
- [ ] Models create correctly
- [ ] Nested groups work (no circular refs)
- [ ] Role inheritance works

---

#### Task 3.2: ABAC Condition Models
**Complexity**: M
**Description**: Create models for storing ABAC conditions and expressions.
**Files**:
- `backend/app/models/abac_condition.py` - ABAC condition model
- `backend/app/models/abac_policy.py` - Named ABAC policies (reusable)
- `backend/app/schemas/abac.py` - ABAC schemas
**Acceptance Criteria**:
- [ ] ABACCondition: id, name, expression (DSL string), description, tenant_id
- [ ] ABACPolicy: id, name, conditions (list of condition IDs), combine_logic (AND/OR), tenant_id
- [ ] Conditions can be attached to: permissions, roles, user assignments
- [ ] Support for context attributes: time, ip, mfa_verified
- [ ] Support for resource attributes: owner, compartment, tags, custom
- [ ] Support for user attributes: department, role, groups
**Tests**:
- [ ] Conditions store correctly
- [ ] Policies combine conditions

---

#### Task 3.3: ABAC Expression Parser
**Complexity**: L
**Description**: Implement DSL parser for ABAC expressions.
**Files**:
- `backend/app/services/permission/abac_parser.py` - DSL parser
- `backend/app/services/permission/abac_ast.py` - AST node definitions
- `backend/app/services/permission/abac_evaluator.py` - Expression evaluator
**Acceptance Criteria**:
- [ ] Parse comparison operators: ==, !=, <, >, <=, >=
- [ ] Parse logical operators: AND, OR, NOT
- [ ] Parse parentheses for grouping
- [ ] Parse attribute access: resource.cost, user.department, context.time.hour
- [ ] Parse IN operator for lists/ranges
- [ ] Parse .contains() for array membership
- [ ] Return AST for evaluation
- [ ] Syntax error messages with line/column
- [ ] Expression validation without evaluation
**Tests**:
- [ ] All operators parse correctly
- [ ] Complex nested expressions work
- [ ] Invalid syntax returns clear errors

---

#### Task 3.4: Permission Evaluation Engine
**Complexity**: L
**Description**: Core engine to evaluate if a user has permission.
**Files**:
- `backend/app/services/permission/__init__.py`
- `backend/app/services/permission/engine.py` - PermissionEngine class
- `backend/app/services/permission/context.py` - Evaluation context builder
**Acceptance Criteria**:
- [ ] check_permission(user_id, permission, resource=None, context=None) -> bool
- [ ] Collects permissions from: direct user, roles, groups (recursive)
- [ ] Applies compartment scoping if specified
- [ ] Evaluates ABAC conditions against context
- [ ] Implements "most specific wins" conflict resolution
- [ ] Specificity order: resource instance > compartment > type > global
- [ ] Build context from request (time, IP, MFA status)
- [ ] No caching (evaluate fresh each time)
**Tests**:
- [ ] Direct permission grants access
- [ ] Role permission grants access
- [ ] Group permission grants access (including nested)
- [ ] ABAC conditions evaluated
- [ ] Most specific wins works
- [ ] Compartment scoping works

---

#### Task 3.5: Permission Middleware & Decorators
**Complexity**: M
**Description**: FastAPI middleware and decorators for permission checks.
**Files**:
- `backend/app/core/permission_middleware.py` - Request permission middleware
- `backend/app/core/permission_decorators.py` - Route decorators
- `backend/app/api/deps.py` - Update with permission dependencies
**Acceptance Criteria**:
- [ ] @require_permission("domain:resource:action") decorator
- [ ] @require_any_permission([...]) for OR logic
- [ ] @require_all_permissions([...]) for AND logic
- [ ] Decorator extracts resource from path params if needed
- [ ] Middleware builds permission context (IP, time, MFA)
- [ ] Returns 403 with clear error message on denial
- [ ] Audit log on permission denials
**Tests**:
- [ ] Decorator blocks unauthorized access
- [ ] Decorator allows authorized access
- [ ] Context built correctly
- [ ] 403 response format correct

---

#### Task 3.6: Permission Query API
**Complexity**: M
**Description**: API to query permissions and check access.
**Files**:
- `backend/app/api/v1/endpoints/permissions.py` - Permission check endpoints
- `backend/app/services/permission/query_service.py` - Query service
**Acceptance Criteria**:
- [ ] `POST /api/v1/permissions/check` - Check if user can perform action
- [ ] `GET /api/v1/permissions/me` - List all my effective permissions
- [ ] `GET /api/v1/permissions/users/{id}` - List user's effective permissions (admin only)
- [ ] `POST /api/v1/permissions/simulate` - Simulate permission check with custom context
- [ ] Effective permissions include source (direct, role, group)
- [ ] Include ABAC conditions that apply
- [ ] Include compartment scope if applicable
**Tests**:
- [ ] Check endpoint returns correct result
- [ ] List includes all permission sources
- [ ] Simulate works with custom context

---

#### Task 3.7: Role Management Service
**Complexity**: M
**Description**: Service for managing roles (system and custom).
**Files**:
- `backend/app/services/permission/role_service.py` - Role management
- `backend/app/api/v1/endpoints/roles.py` - Role endpoints
**Acceptance Criteria**:
- [ ] create_role(tenant_id, name, permissions, parent_role=None)
- [ ] update_role(role_id, data) - cannot modify system roles
- [ ] delete_role(role_id) - cannot delete system roles, soft delete
- [ ] assign_role_to_user(user_id, role_id, compartment=None)
- [ ] remove_role_from_user(user_id, role_id)
- [ ] list_roles(tenant_id, include_system=True)
- [ ] get_role_permissions(role_id) - includes inherited
- [ ] Seed system roles on tenant creation
- [ ] REST API for all operations
**Tests**:
- [ ] Custom role CRUD works
- [ ] System roles protected
- [ ] Role assignment works
- [ ] Inheritance resolves correctly

---

#### Task 3.8: Group Management Service
**Complexity**: M
**Description**: Service for managing nested groups.
**Files**:
- `backend/app/services/permission/group_service.py` - Group management
- `backend/app/api/v1/endpoints/groups.py` - Group endpoints
**Acceptance Criteria**:
- [ ] create_group(tenant_id, name, parent_group=None)
- [ ] update_group(group_id, data)
- [ ] delete_group(group_id) - soft delete, handles children
- [ ] add_user_to_group(user_id, group_id)
- [ ] remove_user_from_group(user_id, group_id)
- [ ] add_subgroup(parent_id, child_id) - validates no circular refs
- [ ] list_groups(tenant_id) - returns tree structure
- [ ] get_group_members(group_id, recursive=False)
- [ ] get_user_groups(user_id, recursive=True) - all groups including parents
- [ ] Circular reference prevention
- [ ] REST API for all operations
**Tests**:
- [ ] Nested groups work
- [ ] Circular refs prevented
- [ ] Recursive member listing works
- [ ] User group resolution includes ancestors

---

#### Task 3.9: Default Permission Configuration
**Complexity**: M
**Description**: Configure default permissions for new users by source.
**Files**:
- `backend/app/models/default_permission_config.py` - Config model
- `backend/app/services/permission/default_service.py` - Default permission service
- `backend/app/api/v1/endpoints/permission_defaults.py` - Config endpoints
**Acceptance Criteria**:
- [ ] DefaultPermissionConfig: tenant_id, user_source (local/oidc/saml), default_role_id, default_group_ids, auto_assign
- [ ] Apply defaults when user created/provisioned
- [ ] Different defaults for local vs SSO users
- [ ] API to configure defaults per tenant
- [ ] Defaults can specify role and/or groups
- [ ] Option to not auto-assign (require manual assignment)
**Tests**:
- [ ] Local user gets local defaults
- [ ] SSO user gets SSO defaults
- [ ] No defaults when auto_assign=false

---

#### Task 3.10: Permission Change Approval
**Complexity**: M
**Description**: Optional approval workflow for permission changes.
**Files**:
- `backend/app/models/permission_change_request.py` - Change request model
- `backend/app/services/permission/change_request_service.py` - Change request handling
- `backend/app/api/v1/endpoints/permission_changes.py` - Change request API
**Acceptance Criteria**:
- [ ] PermissionChangeRequest: id, tenant_id, requester_id, change_type, target_user_id, details (JSON), status, approver_id, approved_at
- [ ] Tenant setting: require_permission_approval (bool), approval_roles (list)
- [ ] When enabled, permission changes create pending requests
- [ ] Designated roles can approve/reject
- [ ] Approved changes applied automatically
- [ ] Rejected changes logged with reason
- [ ] API for request, approve, reject, list pending
**Tests**:
- [ ] Changes create requests when approval required
- [ ] Direct changes when approval not required
- [ ] Approval applies change
- [ ] Rejection logs reason

---

#### Task 3.11: Break-Glass Emergency Access (Basic)
**Complexity**: M
**Description**: Emergency access bypass with multiple approvals and time limits. HSM-required version in Phase 12.
**Files**:
- `backend/app/models/break_glass_request.py` - Emergency access request
- `backend/app/services/permission/break_glass_service.py` - Break-glass handling
- `backend/app/api/v1/endpoints/break_glass.py` - Break-glass API
**Acceptance Criteria**:
- [ ] BreakGlassRequest: id, requester_id, reason, target_tenant_id, requested_permissions, status, approvals (JSON array), expires_at
- [ ] Requires multiple approvals (configurable count, default 2)
- [ ] Time-limited access (configurable, default 4 hours)
- [ ] Comprehensive audit trail
- [ ] Automatic revocation on expiry
- [ ] Notification to provider admins (PLACEHOLDER: logging + simple email if SMTP configured, full notifications in Phase 15)
- [ ] API for request, approve, revoke
- [ ] Prepare model for HSM fields (hsm_verified, hsm_signature) as nullable for Phase 12
**Tests**:
- [ ] Request requires reason
- [ ] Multiple approvals tracked
- [ ] Access expires automatically
- [ ] Full audit trail created
**Note**: HSM-required break-glass with hardware security module verification implemented in Phase 12 (HSM Integration).

---

#### Task 3.12: Permission GraphQL API
**Complexity**: M
**Description**: GraphQL schema for permission operations.
**Files**:
- `backend/app/api/graphql/types/permission.py` - Permission types
- `backend/app/api/graphql/queries/permissions.py` - Permission queries
- `backend/app/api/graphql/mutations/permissions.py` - Permission mutations
**Acceptance Criteria**:
- [ ] Query: permission(id), permissions(filter), myPermissions, userPermissions(userId)
- [ ] Query: role(id), roles(tenantId), rolePermissions(roleId)
- [ ] Query: group(id), groups(tenantId), groupMembers(groupId)
- [ ] Query: checkPermission(permission, resourceId), simulatePermission(...)
- [ ] Mutation: createRole, updateRole, deleteRole, assignRole, removeRole
- [ ] Mutation: createGroup, updateGroup, deleteGroup, addToGroup, removeFromGroup
- [ ] Mutation: grantPermission, revokePermission
- [ ] Proper authorization on all operations
**Tests**:
- [ ] Queries return correct data
- [ ] Mutations work correctly
- [ ] Authorization enforced

---

### Frontend Tasks

#### Task 3.13: Permission Service (Frontend)
**Complexity**: M
**Description**: Angular service for permission management and checking.
**Files**:
- `frontend/src/app/core/services/permission.service.ts` - Permission API service
- `frontend/src/app/core/services/permission-check.service.ts` - Runtime permission checks
- `frontend/src/app/core/models/permission.model.ts` - Permission types
- `frontend/src/app/core/guards/permission.guard.ts` - Route guard for permissions
- `frontend/src/app/core/directives/has-permission.directive.ts` - *hasPermission directive
**Acceptance Criteria**:
- [ ] API methods for all permission endpoints
- [ ] checkPermission(permission, resource?) - calls API or uses cached effective perms
- [ ] myPermissions signal with current user's permissions
- [ ] hasPermission(permission) - synchronous check against cached permissions
- [ ] Route guard: canActivate based on required permission
- [ ] Structural directive: *hasPermission="'domain:resource:action'"
- [ ] Refresh permissions on tenant switch
**Tests**:
- [ ] Service methods work
- [ ] Directive shows/hides correctly
- [ ] Guard blocks/allows routes

---

#### Task 3.14: Role Management UI
**Complexity**: L
**Description**: UI for viewing and managing roles.
**Files**:
- `frontend/src/app/features/permissions/roles/role-list/role-list.component.ts`
- `frontend/src/app/features/permissions/roles/role-detail/role-detail.component.ts`
- `frontend/src/app/features/permissions/roles/role-builder/role-builder.component.ts`
**Acceptance Criteria**:
- [ ] Role list: system roles, custom roles, filter by tenant
- [ ] Role detail: view permissions, assigned users, inherited permissions
- [ ] Role builder: create/edit custom roles
- [ ] Permission picker: browse and select permissions by domain
- [ ] Parent role selector for inheritance
- [ ] Preview effective permissions (including inherited)
- [ ] Cannot edit system roles (view only)
- [ ] Delete custom role with confirmation
**Tests**:
- [ ] List displays roles
- [ ] Builder creates valid roles
- [ ] System roles protected

---

#### Task 3.15: Group Management UI
**Complexity**: M
**Description**: UI for managing nested groups.
**Files**:
- `frontend/src/app/features/permissions/groups/group-list/group-list.component.ts`
- `frontend/src/app/features/permissions/groups/group-tree/group-tree.component.ts`
- `frontend/src/app/features/permissions/groups/group-detail/group-detail.component.ts`
- `frontend/src/app/features/permissions/groups/group-form/group-form.component.ts`
**Acceptance Criteria**:
- [ ] Group list with tree visualization
- [ ] Expand/collapse nested groups
- [ ] Group detail: members, subgroups, permissions, roles
- [ ] Add/remove members from group
- [ ] Add/remove subgroups (drag-drop or picker)
- [ ] Create/edit group form
- [ ] Circular reference prevention in UI
- [ ] Bulk member management
**Tests**:
- [ ] Tree renders correctly
- [ ] Member management works
- [ ] Subgroup management works

---

#### Task 3.16: User Permission Assignment UI
**Complexity**: M
**Description**: UI for assigning permissions/roles to users.
**Files**:
- `frontend/src/app/features/permissions/user-permissions/user-permission-list.component.ts`
- `frontend/src/app/features/permissions/user-permissions/user-permission-editor.component.ts`
- `frontend/src/app/features/permissions/user-permissions/permission-assignment-dialog.component.ts`
**Acceptance Criteria**:
- [ ] View user's effective permissions (all sources)
- [ ] Show permission source (direct, role name, group name)
- [ ] Assign role to user (with optional compartment scope)
- [ ] Grant direct permission (with optional compartment + ABAC)
- [ ] Add user to group
- [ ] Remove role/permission/group membership
- [ ] Compartment picker for scoped permissions
- [ ] Works with permission change approval if enabled
**Tests**:
- [ ] Effective permissions displayed
- [ ] Assignment works
- [ ] Sources shown correctly

---

#### Task 3.17: ABAC Condition Editor
**Complexity**: L
**Description**: Visual editor for ABAC expressions.
**Files**:
- `frontend/src/app/features/permissions/abac/abac-editor/abac-editor.component.ts`
- `frontend/src/app/features/permissions/abac/abac-builder/abac-builder.component.ts`
- `frontend/src/app/features/permissions/abac/condition-row/condition-row.component.ts`
**Acceptance Criteria**:
- [ ] Visual builder: add condition rows, select field/operator/value
- [ ] Field picker with available attributes (context, resource, user)
- [ ] Operator picker based on field type
- [ ] Value input appropriate to field type
- [ ] AND/OR grouping with visual nesting
- [ ] Raw DSL editor with syntax highlighting
- [ ] Toggle between visual and DSL modes
- [ ] Validation with error display
- [ ] Preview parsed expression
**Tests**:
- [ ] Visual builder creates valid DSL
- [ ] DSL editor validates syntax
- [ ] Mode toggle preserves expression

---

#### Task 3.18: Permission Simulator
**Complexity**: M
**Description**: Tool to test permission scenarios.
**Files**:
- `frontend/src/app/features/permissions/simulator/permission-simulator.component.ts`
- `frontend/src/app/features/permissions/simulator/context-builder/context-builder.component.ts`
- `frontend/src/app/features/permissions/simulator/result-display/result-display.component.ts`
**Acceptance Criteria**:
- [ ] Select user to simulate
- [ ] Select permission to check
- [ ] Optionally select resource
- [ ] Build custom context (time, IP, custom attributes)
- [ ] Run simulation against API
- [ ] Display result: allowed/denied
- [ ] Show which rule matched (permission source)
- [ ] Show ABAC conditions evaluated and results
- [ ] Show specificity resolution if conflicts
- [ ] Save/load simulation scenarios
**Tests**:
- [ ] Simulation calls API correctly
- [ ] Results displayed clearly
- [ ] Context builder works

---

#### Task 3.19: Default Permission Configuration UI
**Complexity**: S
**Description**: UI to configure default permissions for new users.
**Files**:
- `frontend/src/app/features/permissions/defaults/permission-defaults.component.ts`
**Acceptance Criteria**:
- [ ] Configure defaults per user source (local, OIDC, SAML)
- [ ] Select default role
- [ ] Select default groups
- [ ] Toggle auto-assign on/off
- [ ] Preview what new users will receive
- [ ] Save configuration
**Tests**:
- [ ] Configuration saves correctly
- [ ] Preview shows expected permissions

---

#### Task 3.20: Break-Glass Request UI (Basic)
**Complexity**: M
**Description**: UI for emergency access requests and approvals. HSM verification UI in Phase 12.
**Files**:
- `frontend/src/app/features/permissions/break-glass/break-glass-request.component.ts`
- `frontend/src/app/features/permissions/break-glass/break-glass-approval.component.ts`
- `frontend/src/app/features/permissions/break-glass/break-glass-list.component.ts`
**Acceptance Criteria**:
- [ ] Request form: reason, target tenant, requested permissions, duration
- [ ] Approval list for provider admins
- [ ] Approve/reject with comments
- [ ] View approval status (who approved, pending approvals)
- [ ] Active break-glass sessions list
- [ ] Revoke active session
- [ ] Audit history of past break-glass requests
- [ ] Prepare UI structure for HSM verification step (hidden/disabled until Phase 12)
**Tests**:
- [ ] Request submission works
- [ ] Approval workflow works
- [ ] Active sessions displayed
**Note**: HSM verification step UI implemented in Phase 12 (HSM Integration).

---

## Phase Completion Checklist

- [ ] All 20 tasks completed
- [ ] File headers follow documentation standards
- [ ] Function indices updated via script
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] Permission system verified:
  - [ ] Direct permissions work
  - [ ] Role permissions work
  - [ ] Group permissions work (including nested)
  - [ ] ABAC expressions evaluate correctly
  - [ ] Compartment scoping works
  - [ ] Most specific wins conflict resolution works
- [ ] UI tested end-to-end:
  - [ ] Role management works
  - [ ] Group management works
  - [ ] Permission assignment works
  - [ ] ABAC editor creates valid expressions
  - [ ] Permission simulator works
  - [ ] Break-glass workflow works

## Dependencies for Next Phase
Phase 4 (Audit Logging) will build on:
- Permission checks for audit log access
- User/group context for actor tracking
- ABAC conditions for audit retention rules

## Notes & Learnings
[To be filled during implementation]
