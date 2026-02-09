# Cross-Phase Consistency Document

This document tracks design decisions that span multiple phases, ensuring consistency across the implementation plan.

---

## 1. Compartment Model

**Issue**: Compartments are used for permission scoping in Phase 3 but defined in CMDB (Phase 8).

**Resolution**: Split implementation across phases.

| Phase | Implementation |
|-------|----------------|
| Phase 2 | Basic Compartment model: id, tenant_id, parent_id, name, description, timestamps |
| Phase 3 | Uses Phase 2 Compartment for permission scoping |
| Phase 8 | Extends Compartment with CMDB fields: cloud_id, provider_type. Adds full hierarchy service. |

**Files Affected**:
- Phase 2: Task 2.13 creates basic model
- Phase 3: Q18 references Phase 2 Compartment
- Phase 8: Task 8.1 extends model, Task 8.7 extends service

---

## 2. Break-Glass Emergency Access (HSM Split)

**Issue**: Phase 3 break-glass references HSM verification, but HSM is implemented in Phase 15.

**Resolution**: Split break-glass into basic and HSM-required versions.

| Phase | Implementation |
|-------|----------------|
| Phase 3 | Basic break-glass: multi-approval, time-limited access, audit trail |
| Phase 15 | HSM-required break-glass: adds hardware security module verification |

**Files Affected**:
- Phase 3: Task 3.11 (Basic), Task 3.20 (Basic UI) - model prepared for HSM fields
- Phase 15: Adds HSM verification requirement, UI integration

---

## 3. Notification System Placeholders

**Issue**: Several features (break-glass, approvals) need notifications before full notification system.

**Resolution**: Phase 9 (Notifications) is now early enough in the plan to be available for Phase 10 (Approvals) and Phase 17 (Drift). Only Phase 3 break-glass still uses placeholder notifications.

| Phase | Implementation |
|-------|----------------|
| Phase 3 | Break-glass notifications: logging + simple email (if SMTP configured) — PLACEHOLDER |
| Phase 9 | Full notification service (email, in-app, webhooks) |
| Phase 10+ | All subsequent phases use Phase 9 notification service |

**Files Affected**:
- Phase 3: Task 3.11 notification marked as PLACEHOLDER
- Phase 9: Full notification system replaces placeholder pattern

---

## 4. Tenant Isolation Configuration

**Issue**: Originally planned configurable isolation strategies, but premature choice adds complexity without benefit.

**Resolution**: Hardcode Schema per Tenant + RLS. It's the most secure default and the industry standard. Alternative strategies can be added later if operational experience reveals a need.

| Phase | Implementation |
|-------|----------------|
| Phase 1 | Hardcoded: Schema per Tenant + RLS (no wizard choice) |
| Phase 2 | Implements Schema per Tenant + RLS isolation |

**Files Affected**:
- Phase 1: Setup wizard (no isolation step)
- Phase 2: Tenant creation always uses schema + RLS

---

## 5. Virtual Root Tenant

**Issue**: Provider-level users need a tenant context for user management.

**Resolution**: Create virtual root tenant for provider-level users.

| Aspect | Implementation |
|--------|----------------|
| Model | Tenant with is_root=true, name="Provider Root" |
| Purpose | User management, metadata storage, no cloud representation |
| Created | During Phase 1 first-run wizard |
| Used | Provider-level user assignment, provider admin context |

**Files Affected**:
- Phase 2: Task 2.1 includes virtual root tenant creation
- Phase 2: Q13 documents concept

---

## 6. Permission Format (Hybrid)

**Issue**: Generic permissions don't support CMDB class-specific access.

**Resolution**: Hybrid format with generic and class-specific permissions.

```
# Generic format
{domain}:{resource}:{action}

# Class-specific format (for CMDB)
{domain}:{resource}:{action}:{subtype}

Examples:
- cmdb:ci:create              # Create any CI
- cmdb:ci:create:virtualmachine    # Create VMs only
```

**Resolution Order** (most specific wins):
1. `cmdb:ci:create:virtualmachine` (most specific)
2. `cmdb:ci:create` (generic)
3. `cmdb:*:*` (wildcard)

**Files Affected**:
- Phase 3: Q16 documents format, Task 3.1 implements
- Phase 8: CMDB uses class-specific permissions

---

## 7. Role Placeholder Tables

**Issue**: Phase 3 needs to populate roles, but Phase 2 creates users.

**Resolution**: Phase 2 creates placeholder tables that Phase 3 populates.

| Phase | Implementation |
|-------|----------------|
| Phase 2 | Role, Permission tables with basic structure (empty) |
| Phase 3 | Full role system, system roles seeding, permission engine |

**Files Affected**:
- Phase 2: Task 2.14 creates placeholder tables
- Phase 3: Task 3.1 extends models, Task 3.7 seeds system roles

---

## 8. CMDB Audit vs Tenant Audit

**Issue**: Should CMDB have separate audit storage from tenant audit?

**Resolution**: Use tenant schema for CMDB audit (consistent with Phase 4).

| Aspect | Implementation |
|--------|----------------|
| Storage | Same audit infrastructure as Phase 4 |
| Scope | Tenant-scoped audit logs |
| Integration | CMDB operations emit standard audit events |

**Files Affected**:
- Phase 4: Audit infrastructure
- Phase 8: CMDB operations use Phase 4 audit service

---

## 9. Real-time Communication (Socket.IO) + Valkey Introduction

**Issue**: Multiple phases need real-time updates. Socket.IO requires a pub/sub backend for multi-process support.

**Resolution**: Valkey (community Redis fork, drop-in replacement, same API, `valkey/valkey:8-alpine`) is introduced in Phase 13 alongside Socket.IO infrastructure. This is earlier than originally planned (old Phase 19) to enable real-time features for Phase 14 (Advanced Audit).

| Phase | Usage |
|-------|-------|
| Phase 9 | In-app notifications (PostgreSQL-backed initially) |
| Phase 13 | **Valkey added to Docker Compose.** Socket.IO + Valkey adapter. Live notification upgrade. Caching layer. |
| Phase 14 | Live audit event streaming, SIEM integration |
| Phase 7 | Visual planner real-time collaboration (future) |

**Why Valkey instead of Redis**: Valkey is the community fork of Redis after the license change. Same API, same client libraries (`redis-py`, `ioredis`), different license (BSD). Drop-in replacement.

**Files Affected**:
- Phase 13: Docker Compose updated, Socket.IO infrastructure, Valkey caching
- Phase 14: Audit streaming via Socket.IO + Valkey pub/sub
- Later phases: Extend with domain-specific events

---

## 10. Workflow Engine (Temporal — Sole Background Processing)

**Issue**: Multiple phases need long-running, stateful workflows (approvals, deployments, impersonation, drift remediation) as well as simple scheduled tasks (token cleanup, archival).

**Resolution**: Use Temporal for everything. Temporal handles both durable multi-step workflows and simple recurring tasks via Temporal Schedules. No Celery needed — this eliminates an entire infrastructure dependency and gives unified visibility.

| Temporal Feature | Purpose | Examples |
|------------------|---------|----------|
| Workflows | Long-running, stateful, multi-step processes | Approval chains, Pulumi deployments, impersonation, break-glass, drift remediation |
| Schedules | Recurring tasks on cron intervals | Token cleanup, audit archival, cost sync, state export, drift scan triggers, notification digests |

| Phase | Temporal Usage |
|-------|----------------|
| Phase 1 | Temporal Server setup (Docker Compose), SDK scaffold, worker entrypoint, example workflow + schedule |
| Phase 2 | TenantPurgeWorkflow (scheduled daily) |
| Phase 3 | BreakGlassWorkflow (basic, HSM deferred to Phase 15) |
| Phase 4 | AuditArchiveWorkflow (scheduled daily), AuditExportWorkflow |
| Phase 6 | DynamicWorkflowExecutor (interprets visual workflow graphs at runtime) |
| Phase 10 | ApprovalChainWorkflow (reusable core workflow consumed by other phases) |
| Phase 12 | PulumiDeployWorkflow (preview → approve → execute → verify, saga rollback) |
| Phase 14 | AnomalyDetectionWorkflow (scheduled hourly) |
| Phase 16 | ImpersonationWorkflow (request → approve → session → auto-revoke via timer) |
| Phase 17 | DriftRemediationWorkflow (detect → notify → approve → remediate), drift scan Schedule |

**Key Conventions**:
- Workflow definitions: `backend/app/workflows/` (not in `services/`)
- Activities: `backend/app/workflows/activities/`
- Worker entrypoint: `backend/app/workflows/worker.py`
- Task queue: `nimbus-workflows`
- Namespace: `nimbus`
- Temporal Server database: `nimbus_temporal` (separate from app database)
- Valkey introduced in Phase 13 for caching and Socket.IO pub/sub (not a task broker)

**Files Affected**:
- Phase 1: Docker Compose, `backend/app/workflows/`, `backend/app/core/temporal.py`
- Phase 2: `backend/app/workflows/tenant_purge.py`
- Phase 3: `backend/app/workflows/break_glass.py`
- Phase 4: `backend/app/workflows/audit_archive.py`, `backend/app/workflows/audit_export.py`
- Phase 6: `backend/app/workflows/dynamic_workflow.py`
- Phase 10: `backend/app/workflows/approval.py`
- Phase 12: `backend/app/workflows/pulumi_deploy.py`
- Phase 14: `backend/app/workflows/anomaly_detection.py`
- Phase 16: `backend/app/workflows/impersonation.py`
- Phase 17: `backend/app/workflows/drift_remediation.py`

---

## 11. Cloud Provider Order (Proxmox First)

**Issue**: Original plan had OCI as first cloud provider (Phase 7), requiring a cloud account and billing for development.

**Resolution**: Use Proxmox VE as the first provider (Phase 11). Proxmox is free, self-hosted, has a full REST API, and a Pulumi provider (`bpg/proxmox`). It validates the entire CloudProviderInterface → semantic layer → CMDB → Pulumi deploy pipeline without cloud costs. Real cloud providers (AWS, Azure, GCP, OCI) move to Phase 18.

| Phase | Implementation |
|-------|----------------|
| Phase 5 | CloudProviderInterface (abstract), semantic model definitions |
| Phase 11 | ProxmoxProvider — first concrete implementation, validates patterns |
| Phase 18 | AWSProvider, AzureProvider, GCPProvider, OCIProvider |

**Files Affected**:
- Phase 5: CloudProviderInterface definition
- Phase 11: `backend/app/services/providers/proxmox.py`, Pulumi `bpg/proxmox` integration
- Phase 18: `backend/app/services/providers/{aws,azure,gcp,oci}.py`

---

## 12. Password Policy (Deferred)

**Issue**: When to implement password complexity rules?

**Resolution**: Defer to local auth implementation in Phase 1.

| Phase | Implementation |
|-------|----------------|
| Phase 1 | Basic password requirements in local auth |
| Future | Enhanced password policy if needed |

**Files Affected**:
- Phase 1: Task 1.6 includes password validation

---

## 13. Tenant Creation Wizard (Post-Create Onboarding)

**Issue**: Tenant creation currently only captures basic info (name, parent, email, description). But a new tenant isn't usable until it also has: domain mappings (for login discovery), at least one identity provider (local or SSO), and optionally SCIM tokens for provisioning.

**Resolution**: Expand tenant creation into a multi-step wizard or post-create onboarding flow. The current simple form remains step 1; subsequent steps configure auth and domains. Alternatively, after creating, redirect to tenant settings with the relevant tabs highlighted.

| Aspect | Implementation |
|--------|----------------|
| Step 1 | Basic info (name, parent, contact email, description) — existing form |
| Step 2 | Domain mappings — add email domains that route to this tenant |
| Step 3 | Authentication — configure at least one IdP (local created by default, optional OIDC/SAML) |
| Step 4 | SCIM tokens — optional, for directory sync |
| Post-create | Redirect to tenant settings (Domains tab) or show inline completion checklist |

**Current State**: Steps 2-4 are available in tenant settings (`/tenants/:id/settings` — Domains tab, plus `/settings/auth` for IdP, `/settings/auth/scim-tokens`). A unified wizard is deferred but the building blocks exist.

**Files Affected**:
- `frontend/src/app/features/tenants/tenant-form/tenant-form.component.ts` — expand or replace with wizard
- `frontend/src/app/features/tenants/tenant-settings/tenant-settings.component.ts` — already has Domains tab
- Backend: tenant creation endpoint could optionally accept initial domain + IdP config in one call

---

## 14. Audit System Split (Core + Advanced)

**Issue**: Original Phase 4 had 23 tasks including real-time streaming, SIEM integration, anomaly detection, and compliance dashboards — all of which require Valkey + Socket.IO infrastructure that wasn't available until Phase 19.

**Resolution**: Split audit into two phases:
- **Phase 4 (Audit Core)**: ~15 tasks covering data models, logging service, redaction, middleware, retention/archival, query/search, export, REST/GraphQL API, and basic frontend (explorer + config UI)
- **Phase 14 (Advanced Audit)**: ~10 tasks covering real-time streaming, SIEM integration, anomaly detection, compliance dashboard, timeline/activity/history views, and live feed — all requiring Phase 13 (Valkey + Socket.IO)

| Phase | Scope |
|-------|-------|
| Phase 4 | Core logging, hash chain, redaction, retention, query, export, basic UI |
| Phase 14 | Real-time streaming, SIEM, anomaly detection, compliance dashboard, timeline views |

**Files Affected**:
- Phase 4: All `backend/app/services/audit/` core files, basic frontend components
- Phase 14: `streaming_service.py`, `siem_*.py`, `anomaly_service.py`, compliance/timeline/activity/feed frontend components

---

## 15. OIDC/SAML Absorption into Phase 3

**Issue**: Old Phase 11 (OIDC/SAML Authentication) was a standalone phase, but Phase 3 already needed IdP integration for enterprise permission management. Building IdP configuration separately from the permission system that consumes it creates unnecessary coupling complexity.

**Resolution**: Phase 3 absorbs the core OIDC/SAML work (IdP configuration, claim mappings, SP-initiated flows). JIT provisioning and IdP-initiated SSO flows move to Phase 15 (MFA & HSM + JIT) since they are optional enhancements that don't block the core permission system.

| Phase | Implementation |
|-------|----------------|
| Phase 3 | IdP configuration (OIDC + SAML via Authlib), claim-to-role mapping, SP-initiated flows, SCIM |
| Phase 15 | JIT user/group auto-provisioning, IdP-initiated SSO, MFA, HSM |

**Files Affected**:
- Phase 3: `IdentityProviderService`, IdP configuration endpoints, SCIM v2
- Phase 15: JIT provisioning logic, IdP-initiated flow handlers

---

## 16. Visual Workflow Editor (Rete.js Foundation)

**Issue**: Both the Visual Workflow Editor (Phase 6) and Visual Architecture Planner (Phase 7) need Rete.js integration. Building them independently would duplicate the canvas infrastructure.

**Resolution**: Phase 6 (Visual Workflow Editor) establishes the Rete.js v2 canvas foundation — custom Angular node rendering, zoom/pan, connection system, properties panel, serialization. Phase 7 (Visual Architecture Planner) reuses this infrastructure for infrastructure topology editing. The workflow editor also provides an extensible node type registry that future phases can extend with domain-specific node types.

| Phase | Implementation |
|-------|----------------|
| Phase 6 | Rete.js v2 + Angular render plugin, canvas infrastructure, node type registry, expression engine, graph validator, workflow compiler, DynamicWorkflowExecutor (Temporal) |
| Phase 7 | Reuses Phase 6 Rete.js canvas, adds infrastructure-specific components and Pulumi code generation |
| Phase 12 (future) | Registers Pulumi Deploy/Destroy node types in workflow editor |
| Phase 17 (future) | Registers Drift Scan/Remediate node types in workflow editor |
| Phase 19 (future) | Registers Cost Check/Budget Alert node types in workflow editor |

**Key Decisions**:
- Interpreter pattern: DynamicWorkflowExecutor reads graph at runtime (no code generation)
- Safe expression engine: AST-based, no eval/exec/imports
- Full DAG + loops: Parallel, Condition, Switch, For-Each, While with max_iterations safety
- Permissions: `workflow:definition:*`, `workflow:execution:*` — any permitted user can design workflows
- Graph stored as JSONB with versioned schema

**Files Affected**:
- Phase 6: `backend/app/services/workflow/`, `backend/app/workflows/dynamic_workflow.py`, `frontend/src/app/features/workflows/`
- Phase 7: Extends Rete.js canvas from Phase 6

---

## Cross-Reference Matrix

| Feature | Ph1 | Ph2 | Ph3 | Ph4 | Ph5 | Ph6 | Ph7 | Ph8 | Ph9 | Ph10 | Ph11 | Ph12 | Ph13 | Ph14 | Ph15 | Ph16 | Ph17 |
|---------|-----|-----|-----|-----|-----|-----|-----|-----|-----|------|------|------|------|------|------|------|------|
| Compartment | - | Create | Use | - | - | - | - | Extend | - | - | - | - | - | - | - | - | - |
| Break-glass | - | - | Basic | Audit | - | - | - | - | - | - | - | - | - | - | HSM | - | - |
| Notifications | - | - | Placeholder | - | - | Use | - | - | Full | Use | - | - | Upgrade | Use | - | Use | Use |
| Roles | - | Placeholder | Full | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Audit | - | - | - | Core | - | Use | - | Use | - | - | - | - | - | Advanced | - | Use | - |
| Socket.IO | - | - | - | - | - | - | - | - | - | - | - | - | Create | Use | - | - | - |
| Valkey | - | - | - | - | - | - | - | - | - | - | - | - | Create | Use | - | - | - |
| Permissions | - | - | Create | Use | - | Use | Use | Use | - | - | - | - | - | - | - | - | - |
| Temporal | Setup | Purge | BreakGlass | Archive | - | DynWorkflow | - | - | - | Approval | - | Deploy | - | Anomaly | - | Impersonate | Drift |
| Rete.js | - | - | - | - | - | Create | Reuse | - | - | - | - | - | - | - | - | - | - |

---

## Validation Checklist

Before implementing any phase, verify:

- [ ] All dependencies from earlier phases are complete
- [ ] Cross-phase features use shared models (not duplicates)
- [ ] Placeholder implementations are clearly marked
- [ ] Extension points are prepared for later phases
- [ ] Audit logging uses Phase 4 infrastructure (after Phase 4)
- [ ] Permissions use Phase 3 decorators (after Phase 3)
- [ ] Notifications use Phase 9 service (after Phase 9)

---

## Notes

- When implementing, always check this document for cross-phase dependencies
- Update this document if new cross-phase issues are discovered
- Keep placeholder implementations minimal but functional
