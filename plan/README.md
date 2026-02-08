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
│   └── phase-20.md
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

*Note: Absorbs old Phase 11 (OIDC/SAML). JIT provisioning deferred to Phase 14.*

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

*Not included (moved to Phase 13): real-time streaming, SIEM, anomaly detection, compliance dashboard, timeline/activity/history views, live feed*

---

### Phase 5: CMDB Core
**Status**: Backlog
**Goal**: Configuration Management Database with CI classes, relationships, service catalog
**Depends on**: Phase 2, Phase 4

Core deliverables:
- CI class definitions (comprehensive hierarchy)
- Compartment hierarchy (unlimited nesting)
- Configuration item CRUD with snapshot versioning
- CI relationships (graph model)
- Full-text search with graph traversal
- Service catalog with pricing
- CI templates with constraints

---

### Phase 6: Semantic Layer
**Status**: Backlog
**Goal**: Cloud provider abstraction — normalize provider-specific concepts
**Depends on**: Phase 5

Core deliverables:
- Semantic model definitions
- Cloud provider interface (abstract)
- Provider-to-semantic mapping engine
- Unified resource view API

---

### Phase 7: Cloud Provider Integration (Proxmox)
**Status**: Backlog
**Goal**: First cloud provider — free, self-hosted, validates full pipeline
**Depends on**: Phase 6

Core deliverables:
- Proxmox provider implementing CloudProviderInterface
- Resource discovery (VMs, containers, storage, networks)
- Credential management (API tokens)
- Resource usage tracking
- Pulumi Proxmox provider (`bpg/proxmox`) integration

---

### Phase 8: Pulumi Integration
**Status**: Backlog
**Goal**: Infrastructure-as-Code via Pulumi Automation API
**Depends on**: Phase 7

Core deliverables:
- Pulumi Automation API integration
- Stack management
- State export/import
- Webhook handlers
- PulumiDeployWorkflow (Temporal) for long-running stack operations

---

### Phase 9: Notifications
**Status**: Backlog
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

*Moved from old Phase 15. Approvals (Phase 10), drift (Phase 11), and audit alerts all need notifications.*

---

### Phase 10: Approval Workflows (Temporal)
**Status**: Backlog
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

### Phase 11: Drift Detection
**Status**: Backlog
**Goal**: Detect and remediate configuration drift
**Depends on**: Phase 8 (Pulumi state), Phase 10 (approvals)

Core deliverables:
- Drift scan trigger (Temporal Schedule)
- Drift detection engine
- Drift delta table model
- DriftRemediationWorkflow (Temporal): detect → notify → approve → remediate pipeline
- Drift severity classification
- Drift report dashboard

*Was old Phase 9. Moved because it needs Pulumi state + approval workflows.*

---

### Phase 12: Real-time & Caching (Valkey)
**Status**: Backlog
**Goal**: Add Valkey to infrastructure, Socket.IO, GraphQL subscriptions, live updates
**Depends on**: Phase 5, Phase 9

Core deliverables:
- Valkey added to Docker Compose (`valkey/valkey:8-alpine`, port 6379)
- Socket.IO server integration with Valkey adapter
- Room-based subscriptions (tenant, user, resource)
- GraphQL subscriptions
- Real-time resource state updates
- Live notification delivery (upgrade in-app notifications to Valkey pub/sub)
- Connection management & reconnection in frontend
- Caching layer (permissions, tenant config)

*Was old Phase 19 (Real-time). Moved earlier to enable real-time features in Phase 13+. Valkey replaces Redis (community fork, same API).*

---

### Phase 13: Advanced Audit
**Status**: Backlog
**Goal**: Audit features that need Valkey + Socket.IO
**Depends on**: Phase 12, Phase 4

Core deliverables:
- Real-time audit event streaming (Socket.IO + Valkey pub/sub)
- SIEM integration (webhook JSON + syslog CEF)
- Anomaly detection service (Temporal scheduled)
- Compliance dashboard (overview, reports, anomaly alerts)
- Audit timeline view
- User activity view
- Resource history view
- Real-time audit feed component

*New phase — split from old Phase 4 (tasks that required streaming/real-time infrastructure).*

---

### Phase 14: MFA & HSM + JIT Provisioning
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

*Was old Phase 12 (MFA/HSM). Gains JIT provisioning from old Phase 11.*

---

### Phase 15: Impersonation
**Status**: Backlog
**Goal**: Secure impersonation workflows
**Depends on**: Phase 10, Phase 4

Core deliverables:
- ImpersonationWorkflow (Temporal): request → approve → session → auto-revoke
- Time-limited sessions with Temporal timer-based auto-expiry
- Separate audit trail
- Re-authentication flow

*Was old Phase 13.*

---

### Phase 16: Visual Architecture Planner
**Status**: Backlog
**Goal**: Drag-and-drop infrastructure designer
**Depends on**: Phase 5, Phase 8

Core deliverables:
- Rete.js integration
- Pre-built components
- Template management
- Pulumi code generation

*Was old Phase 14.*

---

### Phase 17: Additional Cloud Providers
**Status**: Backlog
**Goal**: AWS, Azure, GCP, OCI implementations
**Depends on**: Phase 6, Phase 7

Core deliverables:
- AWS provider implementation
- Azure provider implementation
- GCP provider implementation
- OCI provider implementation
- Cross-cloud unified view

*Was old Phase 16.*

---

### Phase 18: Cost Management
**Status**: Backlog
**Goal**: Cloud cost tracking and billing
**Depends on**: Phase 7+

Core deliverables:
- Cost data aggregation
- Per-tenant cost tracking
- Cost reports/export
- Budget alerts

*Was old Phase 17.*

---

### Phase 19: Monitoring & Observability
**Status**: Backlog
**Goal**: Production-ready observability (Prometheus, Grafana, Loki)
**Depends on**: Core platform

Core deliverables:
- Prometheus metrics endpoint
- Grafana dashboards
- Alert rules
- PagerDuty integration

*Was old Phase 18.*

---

### Phase 20: Production Hardening
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
  │     └─► Phase 5: CMDB
  │           ├─► Phase 6: Semantic Layer
  │           │     ├─► Phase 7: Proxmox
  │           │     │     └─► Phase 8: Pulumi
  │           │     │           └─► Phase 11: Drift
  │           │     └─► Phase 17: Cloud Providers
  │           ├─► Phase 12: Real-time + Valkey
  │           │     └─► Phase 13: Advanced Audit
  │           └─► Phase 16: Visual Planner
  ├─► Phase 9: Notifications
  │     └─► Phase 10: Approvals
  │           ├─► Phase 11: Drift
  │           └─► Phase 15: Impersonation
  └─► Phase 14: MFA + JIT

Phase 18: Cost (after Phase 7+)
Phase 19: Monitoring (after core)
Phase 20: Hardening (after all)
```

No circular dependencies. No phase needs features from a later phase.

---

## Old → New Phase Mapping

| Old Phase | New Phase | Change |
|-----------|-----------|--------|
| 4: Audit (23 tasks) | **4: Audit Core** (~15 tasks) | Split — streaming/SIEM/anomaly removed |
| 5: CMDB | **5: CMDB** | Same |
| 6: Semantic | **6: Semantic** | Same |
| 7: Proxmox | **7: Proxmox** | Same |
| 8: Pulumi | **8: Pulumi** | Same |
| 9: Drift | **11: Drift** | Moved (needs Pulumi + Approvals first) |
| 10: Approvals | **10: Approvals** | Same slot, now has notifications |
| 11: OIDC/SAML | **Absorbed into 3** | JIT provisioning → Phase 14 |
| 12: MFA/HSM | **14: MFA + JIT** | Gains JIT provisioning |
| 13: Impersonation | **15: Impersonation** | Renumbered |
| 14: Visual Planner | **16: Visual Planner** | Renumbered |
| 15: Notifications | **9: Notifications** | **Moved earlier** |
| 16: Cloud Providers | **17: Cloud Providers** | Renumbered |
| 17: Cost | **18: Cost** | Renumbered |
| 18: Monitoring | **19: Monitoring** | Renumbered |
| 19: Real-time | **12: Real-time + Valkey** | **Moved earlier** |
| 20: Hardening | **20: Hardening** | Same |
| — | **13: Advanced Audit** | **New phase** (split from old Phase 4) |

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
