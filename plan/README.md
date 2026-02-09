# Nimbus Implementation Plan

## Overview

This document outlines the phased implementation plan for Nimbus. Each phase delivers a working, testable increment of functionality.

## Plan Structure

```
plan/
├── README.md              # This file - master plan overview
├── phases/
│   ├── phase-01.md        # Refined to task-level (complete)
│   ├── phase-02.md        # Refined to task-level (complete)
│   ├── phase-03.md        # Refined to task-level (complete)
│   ├── phase-04.md        # Refined to task-level (complete)
│   ├── ...
│   └── phase-21.md
├── cross-phase-consistency.md
└── templates/
    └── phase-template.md  # Template for new phases
```

## Phase Completion Checklist

At the end of each phase, verify:

- [ ] All planned tasks completed
- [ ] Code follows documentation standards (file headers)
- [ ] Multi-tenancy patterns correctly implemented (where applicable)
- [ ] Security patterns followed (input validation, auth, permissions)
- [ ] All tests pass (unit, integration)
- [ ] No linting errors (Ruff for Python, ESLint for Angular)
- [ ] API endpoints documented (OpenAPI/Swagger auto-generated)
- [ ] Audit logging implemented for new operations
- [ ] Code reviewed against architecture.md
- [ ] Local development environment works end-to-end

---

## Phase Overview

### Phase 1: Project Foundation & Local Auth
**Status**: Complete
**Goal**: Establish project structure, build system, and basic local authentication

Core deliverables:
- Backend project scaffolding (FastAPI)
- Frontend project scaffolding (Angular)
- Docker Compose for local infrastructure (PostgreSQL, MinIO, Temporal Server + UI)
- PowerShell build script
- Local username/password authentication
- JWT token management (access + refresh)
- Basic user session management
- Temporal setup (Server, SDK, worker, example workflow + schedule)

---

### Phase 2: Multi-Tenancy Foundation
**Status**: Complete
**Goal**: Implement tenant hierarchy and data isolation

Core deliverables:
- Provider/Tenant/Sub-tenant data model
- Schema-per-tenant + RLS isolation
- Tenant context middleware
- Tenant-aware queries
- Tenant management API

---

### Phase 3: Users, IdP, SCIM, Permissions, OIDC/SAML
**Status**: Complete
**Goal**: Implement RBAC + ABAC permission model, identity provider integration, SCIM provisioning

Core deliverables:
- Permission tiers (Provider, Tenant Admin, User, Read-only)
- Role management (8 system roles, custom roles)
- Group management (recursive hierarchy)
- Permission evaluation engine (ABAC DSL)
- Permission middleware
- OIDC/SAML identity provider configuration (Authlib)
- SCIM v2 provisioning endpoints
- Identity provider claim mappings

*Note: Absorbs old Phase 11 (OIDC/SAML). JIT provisioning deferred to Phase 15.*

---

### Phase 4: Audit Logging (Core)
**Status**: Complete
**Goal**: Every action gets logged, queryable, exportable. No streaming yet.
**Depends on**: Phase 3

Core deliverables:
- Audit log data models (AuditLog, RetentionPolicy, RedactionRule, SavedQuery)
- Hash chain service (tamper detection)
- Core audit logging service (async, non-blocking)
- Automatic redaction service
- API request/response audit middleware
- Data change auditing (SQLAlchemy hooks)
- Retention & archival service (MinIO cold storage, Temporal schedule)
- Query service (filters, full-text search, saved queries)
- Archive retrieval (list, download from MinIO)
- Export service (JSON, CSV, async via Temporal)
- REST + GraphQL API for audit operations
- Frontend: audit service, audit log explorer, basic config UI

*Not included (moved to Phase 14): real-time streaming, SIEM, anomaly detection, compliance dashboard, timeline/activity/history views, live feed*

---

### Phase 5: Semantic Layer
**Status**: Backlog
**Goal**: Cloud provider abstraction — normalize provider-specific concepts (decoupled from CMDB)
**Depends on**: Phase 4

Core deliverables:
- Semantic model definitions (abstract resource types and their properties)
- Cloud provider interface (abstract `CloudProviderInterface`)
- Provider-to-semantic mapping engine
- Semantic relationship types
- Unified resource view API

*Was old Phase 6. Moved earlier and decoupled from CMDB — no incomplete dependencies. CMDB (Phase 8) now depends on this.*

---

### Phase 6: Visual Workflow Editor
**Status**: Backlog
**Goal**: Node-based visual workflow editor using Rete.js for custom automation workflows
**Depends on**: Phase 10, Phase 9, Phase 4

Core deliverables:
- Rete.js v2 canvas with Angular render plugin
- Extensible node type registry
- Built-in nodes: Start, End, Condition, Switch, Loop, Parallel, Merge, Delay, Sub-Workflow, Approval Gate, Notification, HTTP/Webhook, Script, Variable Set/Get, Transform
- Expression engine (safe, AST-based)
- Graph validator and workflow compiler
- DynamicWorkflowExecutor (Temporal) — interprets compiled graphs at runtime
- Workflow definition management (CRUD, versioning, draft → active → archived)
- Execution monitor with per-node status overlay
- Dry-run testing with breakpoints and mocks
- Permissions: `workflow:definition:*`, `workflow:execution:*`

*Was old Phase 16. Moved earlier. Establishes Rete.js foundation reused by Phase 7 (Visual Architecture Planner). Future phases add node types (Pulumi Deploy, Drift Scan, Cost Check).*

---

### Phase 7: Visual Architecture Planner
**Status**: Backlog
**Goal**: Drag-and-drop infrastructure designer using Rete.js
**Depends on**: Phase 5, Phase 6, Phase 9, Phase 10

Core deliverables:
- Rete.js integration (reuse Phase 6 canvas infrastructure)
- Pre-built components using semantic types from Phase 5
- Template management
- Export design as JSON/YAML

*Was old Phase 17. Now depends on Phase 6 for Rete.js canvas foundation and Phase 5 for semantic types. Pulumi code generation deferred until Phase 12.*

---

### Phase 8: CMDB Core
**Status**: Complete
**Goal**: Configuration Management Database with CI classes, relationships, service catalog
**Depends on**: Phase 5, Phase 2, Phase 4

Core deliverables:
- CI class definitions based on semantic types (comprehensive hierarchy)
- Compartment hierarchy (unlimited nesting)
- Configuration item CRUD with snapshot versioning
- CI relationships (graph model)
- Full-text search with graph traversal
- Service catalog with pricing
- CI templates with constraints

*Was old Phase 5. Moved later — now depends on Semantic Layer (Phase 5) instead of the other way around.*

---

### Phase 9: Notifications
**Status**: Complete
**Goal**: Multi-channel notification system
**Depends on**: Phase 3

Core deliverables:
- Email notifications (SMTP)
- In-app notification center (PostgreSQL-backed initially)
- Webhook integrations (outbound)
- Notification templates
- User notification preferences
- Notification history
- Frontend notification center UI

*Moved from old Phase 15. Approvals (Phase 10), drift (Phase 17), and audit alerts all need notifications.*

---

### Phase 10: Approval Workflows (Temporal)
**Status**: Complete
**Goal**: Configurable approval chains using Temporal workflows
**Depends on**: Phase 9, Phase 1 (Temporal)

Core deliverables:
- ApprovalChainWorkflow (Temporal) with configurable approver chains
- Approval chain configuration (tenant-level, operation-level)
- Temporal Signals for approval decisions, Queries for status
- Timeout + escalation policies
- Notification triggers (activities)
- Approval inbox in frontend
- Workflow status dashboard (leveraging Temporal visibility)

*Now has notification system available.*

---

### Phase 11: Cloud Provider Integration (Proxmox)
**Status**: Backlog
**Goal**: First cloud provider — free, self-hosted, validates full pipeline
**Depends on**: Phase 5, Phase 8

Core deliverables:
- Proxmox provider implementing CloudProviderInterface
- Resource discovery (VMs, containers, storage, networks)
- Credential management (API tokens)
- Resource usage tracking
- Pulumi Proxmox provider (`bpg/proxmox`) integration

*Was old Phase 7. Moved later — now depends on Semantic Layer (Phase 5) and CMDB (Phase 8).*

---

### Phase 12: Pulumi Integration
**Status**: Backlog
**Goal**: Infrastructure-as-Code via Pulumi Automation API
**Depends on**: Phase 11

Core deliverables:
- Pulumi Automation API integration
- Stack management
- State export/import
- Webhook handlers
- PulumiDeployWorkflow (Temporal) for long-running stack operations

*Was old Phase 8. Moved later — now depends on Proxmox (Phase 11).*

---

### Phase 13: Real-time & Caching (Valkey)
**Status**: Backlog
**Goal**: Add Valkey to infrastructure, Socket.IO, GraphQL subscriptions, live updates
**Depends on**: Phase 8, Phase 9

Core deliverables:
- Valkey added to Docker Compose (`valkey/valkey:8-alpine`, port 6379)
- Socket.IO server integration with Valkey adapter
- Room-based subscriptions (tenant, user, resource)
- GraphQL subscriptions
- Real-time resource state updates
- Live notification delivery (upgrade in-app notifications to Valkey pub/sub)
- Connection management & reconnection in frontend
- Caching layer (permissions, tenant config)

*Was old Phase 12. Renumbered. Valkey replaces Redis (community fork, same API).*

---

### Phase 14: Advanced Audit
**Status**: Backlog
**Goal**: Audit features that need Valkey + Socket.IO
**Depends on**: Phase 13, Phase 4

Core deliverables:
- Real-time audit event streaming (Socket.IO + Valkey pub/sub)
- SIEM integration (webhook JSON + syslog CEF)
- Anomaly detection service (Temporal scheduled)
- Compliance dashboard (overview, reports, anomaly alerts)
- Audit timeline view
- User activity view
- Resource history view
- Real-time audit feed component

*Was old Phase 13. Renumbered. Split from old Phase 4 (tasks that required streaming/real-time infrastructure).*

---

### Phase 15: MFA & HSM + JIT Provisioning
**Status**: Backlog
**Goal**: Enhanced auth security + remaining OIDC/SAML work
**Depends on**: Phase 3

Core deliverables:
- TOTP MFA setup/verification
- WebAuthn/Yubikey support
- HSM integration (PKCS#11)
- Tier-based MFA enforcement
- JIT user auto-provisioning from OIDC/SAML claims
- JIT group auto-provisioning from IdP claims
- IdP-initiated SSO flows

*Was old Phase 14. Renumbered. Gains JIT provisioning from old Phase 11.*

---

### Phase 16: Impersonation
**Status**: Backlog
**Goal**: Secure impersonation workflows
**Depends on**: Phase 10, Phase 4

Core deliverables:
- ImpersonationWorkflow (Temporal): request → approve → session → auto-revoke
- Time-limited sessions with Temporal timer-based auto-expiry
- Separate audit trail
- Re-authentication flow

*Was old Phase 15. Renumbered.*

---

### Phase 17: Drift Detection
**Status**: Backlog
**Goal**: Detect and remediate configuration drift
**Depends on**: Phase 12 (Pulumi state), Phase 10 (approvals)

Core deliverables:
- Drift scan trigger (Temporal Schedule)
- Drift detection engine
- Drift delta table model
- DriftRemediationWorkflow (Temporal): detect → notify → approve → remediate pipeline
- Drift severity classification
- Drift report dashboard

*Was old Phase 11. Moved later — needs Pulumi state (Phase 12) + approval workflows (Phase 10).*

---

### Phase 18: Additional Cloud Providers
**Status**: Backlog
**Goal**: AWS, Azure, GCP, OCI implementations
**Depends on**: Phase 5, Phase 11

Core deliverables:
- AWS provider implementation
- Azure provider implementation
- GCP provider implementation
- OCI provider implementation
- Cross-cloud unified view

*Was old Phase 18. Dependencies updated to Phase 5 (Semantic Layer) and Phase 11 (Proxmox).*

---

### Phase 19: Cost Management
**Status**: Backlog
**Goal**: Cloud cost tracking and billing
**Depends on**: Phase 11+

Core deliverables:
- Cost data aggregation
- Per-tenant cost tracking
- Cost reports/export
- Budget alerts

*Was old Phase 19. Dependencies updated to Phase 11+ (Proxmox).*

---

### Phase 20: Monitoring & Observability
**Status**: Backlog
**Goal**: Production-ready observability (Prometheus, Grafana, Loki)
**Depends on**: All prior phases

Core deliverables:
- Prometheus metrics endpoint
- Grafana dashboards
- Alert rules
- PagerDuty integration

*Was old Phase 20.*

---

### Phase 21: Production Hardening
**Status**: Backlog
**Goal**: Security audit, performance, documentation
**Depends on**: All phases

Core deliverables:
- Performance optimization
- Security audit
- Documentation completion
- Deployment guides

---

## Dependency Graph

```
Phase 3 (done)
  ├─► Phase 4: Audit Core (done)
  │     ├─► Phase 5: Semantic Layer
  │     │     ├─► Phase 7: Visual Arch Planner (also needs Phase 6, 9, 10)
  │     │     ├─► Phase 8: CMDB (also needs Phase 2)
  │     │     │     ├─► Phase 11: Proxmox
  │     │     │     │     └─► Phase 12: Pulumi
  │     │     │     │           └─► Phase 17: Drift (also needs Phase 10)
  │     │     │     └─► Phase 13: Real-time + Valkey (also needs Phase 9)
  │     │     │           └─► Phase 14: Advanced Audit
  │     │     └─► Phase 18: Cloud Providers (also needs Phase 11)
  │     └─► Phase 16: Impersonation (also needs Phase 10)
  ├─► Phase 9: Notifications (done)
  │     └─► Phase 10: Approvals (done)
  │           └─► Phase 6: Visual Workflow Editor (also needs Phase 9, 4)
  │                 └─► Phase 7: Visual Arch Planner
  └─► Phase 15: MFA + JIT

Phase 19: Cost (after Phase 11+)
Phase 20: Monitoring (after core)
Phase 21: Hardening (after all)
```

No circular dependencies. No phase needs features from a later phase.

---

## Old → New Phase Mapping

| Previous Phase | New Phase | Change |
|-----------|-----------|--------|
| 4: Audit Core | **4: Audit Core** | Same |
| 5: CMDB | **8: CMDB** | Moved later, now depends on SL |
| 6: Semantic | **5: Semantic Layer** | Moved earlier, decoupled from CMDB |
| 7: Proxmox | **11: Proxmox** | Moved later |
| 8: Pulumi | **12: Pulumi** | Moved later |
| 9: Notifications | **9: Notifications** | Same |
| 10: Approvals | **10: Approvals** | Same |
| 11: Drift | **17: Drift** | Moved later |
| 12: Valkey | **13: Real-time + Valkey** | Renumbered |
| 13: Advanced Audit | **14: Advanced Audit** | Renumbered |
| 14: MFA + JIT | **15: MFA + JIT** | Renumbered |
| 15: Impersonation | **16: Impersonation** | Renumbered |
| 16: VWE | **6: Visual Workflow Editor** | Moved earlier |
| 17: Visual Planner | **7: Visual Arch Planner** | Moved earlier, deps changed |
| 18: Cloud Providers | **18: Cloud Providers** | Same |
| 19: Cost | **19: Cost** | Same |
| 20: Monitoring | **20: Monitoring** | Same |
| 21: Hardening | **21: Hardening** | Same |

---

## Refinement Process

Before starting each phase, conduct a refinement session:

1. Review phase goals and deliverables
2. Identify implementation questions
3. Break down into specific tasks
4. Estimate complexity (S/M/L)
5. Document decisions in phase file

Questions to consider during refinement:
- What are the specific API endpoints needed?
- What data models need to be created/modified?
- What are the edge cases?
- What tests are required?
- Are there dependencies on other phases?
- What configuration options are needed?
