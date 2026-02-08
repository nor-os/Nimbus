# Nimbus

Pulumi-based SaaS Control Panel for multi-cloud infrastructure management (Proxmox, AWS, Azure, GCP, OCI). Multi-tenant, enterprise-grade.

**Status**: Phases 1-3 complete. Phase 4 (Audit Core) is next. 20-phase implementation plan in `plan/phases/`.

## Quick Reference

- Architecture doc: `docs/architecture.md`
- Feature spec: `concept.txt`
- Implementation plan: `plan/README.md` (20 phases in `plan/phases/`)
- Cross-phase decisions: `plan/cross-phase-consistency.md`
- Detailed Claude instructions: `.claude/instructions.md`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy (async), Strawberry GraphQL, Temporal |
| Frontend | Angular 17+, TypeScript, Taiga UI, Rete.js, Apollo Angular |
| Database | PostgreSQL (`nimbus` + `nimbus_temporal`), MinIO |
| Cache | Valkey (added Phase 12 — caching, Socket.IO pub/sub) |
| IaC | Pulumi Automation API |
| Workflows | Temporal (workflows + schedules — no Celery) |
| Quality | Ruff (Python), ESLint + Prettier (TS), pytest, Jest, Playwright |

## Commands

```bash
# Backend
uv run uvicorn app.main:app          # Start backend (port 8000)
uv run pytest                         # Run tests
uv run ruff check .                   # Lint
uv run ruff format .                  # Format

# Temporal (workflow engine)
uv run python -m app.workflows.worker # Start Temporal worker

# Frontend
npm start                             # Dev server (port 4200)
npm run build                         # Production build
npm run lint                          # Lint
npm run test                          # Unit tests
npm run e2e                           # E2E tests

# Infrastructure
docker-compose up                     # Start PostgreSQL, MinIO, Temporal Server+UI
docker-compose down                   # Stop all

# Migrations
alembic upgrade head                  # Apply migrations
alembic downgrade -1                  # Rollback one

# Build
./build.ps1                           # Full build (validates prereqs, installs deps, runs migrations)
```

## Critical Rules

- **Tenant isolation is mandatory.** Every data model includes `tenant_id`. All queries are tenant-aware. Strategy: schema-per-tenant + RLS (hardcoded).
- **Every source file needs a header** with Overview, Architecture Reference, Dependencies, and Concepts. See `.claude/instructions.md` for format.
- **Permission format**: `{domain}:{resource}:{action}[:{subtype}]` (e.g., `cmdb:ci:create:virtualmachine`)
- **Four permission tiers**: Provider > Tenant Admin > User > Read-Only
- **Audit everything.** Every operation logs: actor, action, resource, old/new values, trace_id, priority, IP.
- **Soft deletes only.** Never hard-delete; preserve audit trail.
- **All timestamps UTC.** Display in user's timezone.
- **REST** (`/api/v1/*`) for auth; **GraphQL** (`/graphql`) for data operations.
- **Error responses** always include `trace_id` for log correlation.
- **No mock identity providers, no sample data seeding.**
- **Windows compatibility required** (PowerShell scripts, proper path handling).

## Naming Conventions

| Context | Convention |
|---------|-----------|
| Python functions/vars | `snake_case` |
| Python classes | `PascalCase` |
| TypeScript functions/vars | `camelCase` |
| TypeScript classes/interfaces | `PascalCase` |
| Database tables/columns | `snake_case` |
| GraphQL fields | `camelCase` |
| GraphQL types | `PascalCase` |

## Architecture at a Glance

```
Request -> Auth Middleware -> Rate Limiter -> Trace ID -> Permission Check -> Service Layer -> Audit Log -> Response
```

Frontend uses standalone components, Angular Signals (not NgRx), and hash-based routing (`/#/route`).

Multi-tenancy schemas: `nimbus_core` (system), `nimbus_tenant_{id}` (per tenant).

## Workflow Engine (Temporal)

All background work runs through Temporal — no Celery.

| Durable Workflows | Temporal Schedules (recurring) |
|---------------------|-------------------------------|
| Approval chains | Token cleanup (every 15m) |
| Pulumi stack operations | Audit archival (daily) |
| Impersonation lifecycle | Cost sync (every 6h) |
| Break-glass emergency access | State export (hourly) |
| Drift remediation pipelines | Notification digests (daily) |

Workflows + activities: `backend/app/workflows/` | Task queue: `nimbus-workflows`
Temporal Server: port 7233 | Temporal UI: port 8233

## Cloud Provider Abstraction

All providers implement `CloudProviderInterface` with: `list_resources`, `get_resource`, `get_cost_data`, `map_to_semantic`, `validate_credentials`. Proxmox is the first provider (Phase 7) — free, self-hosted, validates the full pipeline. Cloud providers (AWS, Azure, GCP, OCI) follow in Phase 17. The semantic layer normalizes provider-specific concepts (Bridge/VPC/VNet/VCN -> Network, etc.).
