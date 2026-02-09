# Nimbus Developer Guide for Claude

## Project Overview

Nimbus is a Pulumi-based SaaS Control Panel for multi-user and multi-tenancy cloud backend management. It provides a unified interface for managing cloud infrastructure across Proxmox, AWS, Azure, GCP, and OCI with enterprise-grade features including CMDB, semantic layer abstraction, visual architecture planning, and comprehensive audit trails.

**Project Status**: Planning/specification phase - implementation code to be written.

---

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy (async mode)
- **GraphQL**: Strawberry
- **Migrations**: Alembic
- **Auth**: Authlib + python-jose (JWT)
- **Workflow Engine & Scheduler**: Temporal (workflows + Temporal Schedules for recurring tasks)
- **Infrastructure**: Pulumi Automation API

### Frontend
- **Framework**: Angular 17+ with TypeScript
- **Components**: Standalone components only
- **State**: Signals (not NgRx/RxJS stores)
- **UI Library**: Taiga UI
- **Visual Editor**: Rete.js (architecture planner)
- **GraphQL Client**: Apollo Angular
- **Routing**: Hash-based (`/#/route`)

### Infrastructure
- **Database**: PostgreSQL (`nimbus` for app, `nimbus_temporal` for Temporal)
- **Object Storage**: MinIO (S3-compatible)
- **Cache / Pub-Sub**: Valkey (Phase 12+ — caching, Socket.IO pub/sub)
- **Logging**: Loki + Grafana (Phase 18+)
- **Metrics**: Prometheus + Grafana (Phase 18+)

### Code Quality
- **Python**: Ruff (linting + formatting)
- **Angular**: ESLint + Prettier
- **Pre-commit hooks**: Enabled

---

## Architecture Adherence

### Multi-Tenancy
Always implement tenant isolation. The strategy is **schema per tenant + row-level security (RLS)** (hardcoded, not configurable):
- Core schema: `nimbus_core` (system tables)
- Tenant schemas: `nimbus_tenant_{tenant_id}`
- Every data model MUST include `tenant_id`
- All queries MUST be tenant-aware

### Service Layer Pattern
Follow the defined service architecture:
```
API Request → Auth Middleware → Rate Limiter → Trace ID → Permission Check → Service Layer → Audit Log → Response
```

### Permission Model (RBAC + ABAC)
Four permission tiers (highest to lowest):
1. **Provider**: Requires HSM/Yubikey cryptographic proof
2. **Tenant Admin**: Full tenant control
3. **User**: Configurable permissions
4. **Read-Only**: View access only

### API Design
- **REST** (`/api/v1/*`): Authentication only (login, refresh, logout, OIDC/SAML callbacks, MFA). REST is the natural fit for auth flows and OIDC/SAML protocol requirements.
- **GraphQL** (`/graphql`): All data operations (tenants, users, CMDB, workflows, audit, cost). GraphQL excels at complex relational queries, pagination, and selective field fetching.
- All errors include `trace_id` for log correlation
- Health endpoints: `/health`, `/ready`, `/live`

---

## Code Organization

### Backend Structure
```
backend/
├── app/
│   ├── api/v1/endpoints/     # REST endpoints
│   ├── api/graphql/          # Strawberry schema, queries, mutations, subscriptions
│   ├── core/                 # config, security, permissions, middleware
│   ├── services/             # Business logic (cmdb, pulumi, semantic, audit, etc.)
│   ├── workflows/            # Temporal workflows, activities, and worker
│   ├── models/               # SQLAlchemy models (all include tenant_id)
│   ├── schemas/              # Pydantic schemas
│   └── db/                   # Session management, tenant context, migrations
├── tests/
├── alembic/
└── main.py
```

### Frontend Structure
```
frontend/src/app/
├── core/                     # auth, guards, interceptors, core services
├── shared/                   # reusable components, directives, pipes, models
├── features/                 # dashboard, cmdb, architecture-planner, tenants, etc.
└── graphql/                  # queries, mutations, subscriptions
```

### Frontend Component Rules

**Layout Requirement**: Every routed page component MUST:
1. Import `LayoutComponent` from `@shared/components/layout/layout.component`
2. Add `LayoutComponent` to the `imports` array
3. Wrap its entire template content with `<nimbus-layout>...</nimbus-layout>`

This provides the shared header, sidebar, and breadcrumb navigation.

**Light Theme Color Palette — MANDATORY for ALL components**:

The application uses a **light theme**. Never use dark backgrounds (#0f172a, #1e293b) as page/card/panel backgrounds, or light colors (#e2e8f0, #c8ccd0) as text. The only exception is tooltips (dark bg + white text is OK).

| Element | Color | Example |
|---------|-------|---------|
| Page headings (h1) | `#1e293b` | `font-size: 1.5rem; font-weight: 700; color: #1e293b` |
| Body text | `#374151` | Table cells, descriptions |
| Secondary text | `#64748b` | Labels, table headers, muted text |
| Tertiary/muted | `#94a3b8` | Hints, empty states |
| Card/panel background | `#fff` | Tables, detail cards, panels |
| Page background | transparent | Inherited from layout (`#f5f6f8`) |
| Code block background | `#f8fafc` | JSON viewers, expression editors |
| Primary border | `#e2e8f0` | Cards, tables, inputs |
| Row separator border | `#f1f5f9` | Table rows, list items |
| Hover background | `#f8fafc` | Table rows, list items |
| Input background | `#fff` | Text inputs, selects, textareas |
| Input border | `#e2e8f0` | Focus: `#3b82f6` |
| Primary action | `background: #3b82f6; color: #fff` | Buttons, active tabs |
| Primary link | `#3b82f6` | Clickable text links |
| Outline button | `border: 1px solid #e2e8f0; background: #fff` | Secondary actions |
| Active tab | `background: #eff6ff; color: #3b82f6` | Tab/filter selection |
| Badge - success | `background: #dcfce7; color: #16a34a` | Active, Completed |
| Badge - error | `background: #fef2f2; color: #dc2626` | Failed, Error |
| Badge - warning | `background: #fefce8; color: #ca8a04` | Archived, Cancelled |
| Badge - neutral | `background: #f1f5f9; color: #64748b` | Draft, Pending |
| Badge - info | `background: #dbeafe; color: #2563eb` | Running, Info |

**Reference component**: `frontend/src/app/features/users/user-list/user-list.component.ts` — canonical example of correct light theme styling.

**Boolean `@Input()` Binding**: When using a component with a boolean `@Input()` (e.g. `@Input() allowClear = false`), you MUST use property binding syntax: `[allowClear]="true"`. A bare attribute `allowClear` without brackets passes the empty string `""`, not `true`, causing Angular type errors (`Type 'string' is not assignable to type 'boolean'`).

**Searchable Select Component**: Entity dropdowns with dynamic/many options use `<nimbus-searchable-select>` (at `@shared/components/searchable-select/searchable-select.component.ts`). It is a drop-in `<select>` replacement with type-to-filter, keyboard navigation, and ControlValueAccessor support for `[(ngModel)]` and `formControlName`. Small static enum selects (2-5 hardcoded options) remain as native `<select>`.

---

## Documentation Standards

### File Headers
Every source file MUST include a header with:
1. **Overview**: What the file does (1-2 sentences)
2. **Architecture Reference**: How it relates to `docs/architecture.md`
3. **Dependencies**: External packages and internal modules used
4. **Concepts**: Key concepts from `concept.txt` this file implements

Example Python header:
```python
"""
Overview: Handles CMDB resource operations including CRUD and drift detection.
Architecture: Implements Service Layer pattern (Section 3.1, 3.3)
Dependencies: sqlalchemy, strawberry, app.models.cmdb, app.services.audit
Concepts: CMDB, Drift Detection, Semantic Layer
"""
```

Example TypeScript header:
```typescript
/**
 * Overview: CMDB resource list component with filtering and pagination.
 * Architecture: Implements Feature Module pattern (Section 3.2)
 * Dependencies: @angular/core, @taiga-ui/core, app/graphql/queries/cmdb
 * Concepts: CMDB, Semantic Layer
 */
```

---

## Security Patterns

### Authentication
- Support OIDC/SAML integration with local username/password fallback
- JWT tokens with refresh mechanism
- MFA enforcement configurable per permission tier
- Token structure must include: `sub`, `tenant_id`, `provider_id`, `roles`, `permissions`, `impersonating`

### Impersonation
- Only root-tenancy root users can impersonate
- Managed by ImpersonationWorkflow (Temporal) with time-limited sessions
- Separate audit trail for impersonation actions
- Re-authentication may be required
- Auto-revoke on timer expiry via Temporal

### HSM/Yubikey
- Production: HSM (PKCS#11) for critical operations
- Demo mode (`--debug`): Yubikey (WebAuthn)
- Required for: provider-level changes, tenant deletion, HSM key rotation, emergency access, bulk exports

### Data Protection
- Soft delete for all entities (preserve audit trail)
- All timestamps in UTC (display in user timezone)
- Encrypted credentials storage
- GDPR-compliant data export capability

### API Security Headers
Always include: CORS, CSP, HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection

### Input Validation
- Validate all inputs at API boundaries
- Use Pydantic schemas for request validation (backend)
- Sanitize user input to prevent XSS, SQL injection
- Rate limiting enabled by default (configurable per tenant/endpoint)

---

## Testing Requirements

### Backend Testing
- Framework: pytest
- Test files: `tests/` directory mirroring `app/` structure
- Required coverage areas:
  - Unit tests for all services
  - Integration tests for API endpoints
  - Tenant isolation verification tests
  - Permission boundary tests

### Frontend Testing
- Unit tests: Jest
- E2E tests: Playwright
- Test all components with tenant context
- Test permission-gated UI elements

### Security Testing
- Test authentication flows (local, OIDC, SAML)
- Verify tenant data isolation
- Test permission escalation boundaries
- Verify audit log generation

---

## Conventions

### Naming
- Python: snake_case for functions/variables, PascalCase for classes
- TypeScript: camelCase for functions/variables, PascalCase for classes/interfaces
- Database: snake_case for tables/columns
- GraphQL: camelCase for fields, PascalCase for types

### Error Handling
Standard error response format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": [],
    "trace_id": "correlation-id",
    "timestamp": "ISO8601"
  }
}
```

### Audit Logging
Every API call, resource change, login, and permission change must be audited with:
- Actor (who)
- Action (what)
- Resource (on what)
- Old/new values (for changes)
- Trace ID (for correlation)
- Priority flag (info/warn/err)

---

## Cloud Provider Abstraction

Use the semantic layer to normalize cloud provider differences:

| Nimbus Concept | Proxmox (Phase 7) | AWS | Azure | OCI |
|---|---|---|---|---|
| Tenancy | Datacenter/Cluster | Account | Subscription | Tenancy |
| Compartment | Pool | Tags/OUs | Resource Group | Compartment |
| Network | Bridge/SDN VNet | VPC | VNet | VCN |
| Compute | QEMU VM / LXC | EC2 | VM | Instance |
| Storage | ZFS/Ceph/LVM | S3/EBS | Blob/Disk | Object Storage |
| Database | N/A (VM-hosted) | RDS | SQL Database | ATP |

Implement `CloudProviderInterface` for each provider with methods:
- `list_resources(compartment_id)`
- `get_resource(resource_id)`
- `get_cost_data(start_date, end_date)`
- `map_to_semantic(resource) -> CIClass`
- `validate_credentials()`

---

## Background Processing & Workflow Engine (Temporal)

All background work — both durable workflows and recurring tasks — runs through Temporal. No Celery.

Workflows live in `backend/app/workflows/`. Task queue: `nimbus-workflows` | Namespace: `nimbus`

### Durable Workflows
- **ApprovalChainWorkflow**: Configurable approval chains with timeout/escalation
- **PulumiDeployWorkflow**: Preview → approve → execute → verify (saga rollback)
- **ImpersonationWorkflow**: Request → approve → re-auth → session → auto-revoke
- **BreakGlassWorkflow**: Multi-approval emergency access
- **DriftRemediationWorkflow**: Detect → notify → approve → remediate

Use Temporal Signals for external input (approval decisions, session extension).
Use Temporal Queries for reading workflow state (approval status, deploy progress).

### Temporal Schedules (Recurring Tasks)
- Drift scan trigger: Daily (tenant-configurable) — starts DriftRemediationWorkflow
- State export: Hourly
- Token cleanup: Every 15 minutes
- Audit archive: Daily
- Cost sync: Every 6 hours

---

## Real-time Updates

Use Socket.IO for WebSocket connections:
- GraphQL subscriptions for real-time data
- Room structure: `tenant:{id}`, `user:{id}`, `resource:{id}`
- Event types: `resource.*`, `drift.*`, `approval.*`, `notification.*`

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20 LTS
- Docker & Docker Compose

### Default Ports
- Backend API: 8000
- Frontend dev: 4200
- PostgreSQL: 5432
- MinIO: 9000 (API), 9001 (Console)
- Temporal Server: 7233
- Temporal UI: 8233
- Valkey: 6379 (added Phase 12 — caching, Socket.IO pub/sub)
- Grafana: 3000 (added Phase 19)
- Loki: 3100 (added Phase 19)

### Build System
PowerShell build script handles:
1. Environment validation
2. Backend/frontend builds
3. Docker Compose for infrastructure

---

## Key Implementation Notes

1. **No mock identity provider** - use real OIDC/SAML or local auth
2. **No sample data seeding** - start with empty database
3. **Windows compatibility required** - PowerShell scripts, proper path handling
4. **Monorepo structure** - backend and frontend together
5. **GitHub Flow** - feature branches merge to main, PR reviews not required
6. **MIT License**

---

## Reference Documents

- `concept.txt` - Feature specifications and requirements
- `docs/architecture.md` - Detailed architecture documentation

When implementing features, always cross-reference these documents to ensure alignment with the specified design.
