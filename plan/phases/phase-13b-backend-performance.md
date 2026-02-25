# Phase 13b: Backend Performance Optimization

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Maximize Python backend throughput and response latency without a language rewrite. The backend is entirely I/O-bound (database, HTTP, email, SSH) — no CPU-bound hot paths exist. Optimizations target serialization, async I/O, query efficiency, and caching integration.

*Decision context: A full language rewrite (C#, TypeScript, Rust) was evaluated and rejected. C# (.NET) was the best alternative (4-6 months, 2-3x gain), but Python optimizations can achieve comparable gains (3-5x) in days/weeks instead of months. See analysis below.*

## Language Rewrite Analysis (for reference)

| Language | Effort | Perf Gain | Ecosystem Fit | Verdict |
|----------|--------|-----------|---------------|---------|
| **C# (.NET 8+)** | 4-6 months, 2-3 devs | 2-5x throughput | 85% — best enterprise fit (EF Core, Hot Chocolate, ASP.NET Identity) | Best alternative if Python proves insufficient |
| **TypeScript (Node.js)** | 4-5 months, 2-3 devs | 1.5-3x I/O | 70% — great GraphQL, weak enterprise patterns (multi-tenancy, RLS) | Shared language with frontend, but fights ecosystem for enterprise |
| **Rust** | 8-12 months, 2-3 devs | 5-10x I/O, 10-50x CPU | 40% — Temporal SDK beta, no SCIM, everything manual | Overkill for I/O-bound SaaS; 3-4x code bloat |

**Key insight**: 133K lines, 83 models, 350+ GraphQL fields, 184 services, 86 migrations, 23 Temporal workflows. Rewrite cost is massive; real-world gain is limited because PostgreSQL query time dominates.

## Dependencies
- Phase 13 complete (Valkey caching layer required for Tasks 13b.5-13b.7)
- Phase 4 complete (audit middleware in request pipeline)

## Tasks

### Tier 1: Quick Wins (days)

#### Task 13b.1: Enable uvloop
**Complexity**: S
**Description**: Replace default asyncio event loop with uvloop for 2-4x faster async I/O.
**Files**:
- `backend/pyproject.toml` — add `uvloop` dependency
- `backend/app/main.py` — configure uvloop (or uvicorn CLI flag)
**Acceptance Criteria**:
- [ ] `uvloop` added to dependencies
- [ ] Uvicorn starts with uvloop event loop (`--loop uvloop` or programmatic)
- [ ] Verify with `asyncio.get_event_loop()` — should be `uvloop.Loop`
- [ ] All existing tests pass (no behavioral changes)
- [ ] Windows fallback: uvloop is Linux/macOS only — skip gracefully on Windows
**Tests**:
- [ ] Startup works on Linux with uvloop
- [ ] Startup works on Windows without uvloop (graceful fallback)

---

#### Task 13b.2: Add orjson for Fast Serialization
**Complexity**: S
**Description**: Replace stdlib `json` with `orjson` for 2-10x faster JSON serialization/deserialization. Affects every request/response.
**Files**:
- `backend/pyproject.toml` — add `orjson` dependency
- `backend/app/core/config.py` or `backend/app/main.py` — configure FastAPI to use orjson
**Acceptance Criteria**:
- [ ] `orjson` added to dependencies
- [ ] FastAPI configured with `ORJSONResponse` as default response class
- [ ] Pydantic models use orjson for serialization (Pydantic v2 supports this natively)
- [ ] GraphQL (Strawberry) serialization uses orjson where possible
- [ ] All existing tests pass
- [ ] Verify with benchmark: serialize large audit log response before/after
**Tests**:
- [ ] API responses use orjson (check Content-Type, verify speed)
- [ ] Complex nested objects serialize correctly (datetime, UUID, Decimal)

---

#### Task 13b.3: Connection Pool Tuning
**Complexity**: S
**Description**: Profile and tune asyncpg connection pool. Current: `pool_size=20, max_overflow=10`. May be under/over-provisioned.
**Files**:
- `backend/app/db/session.py` — pool configuration
- `backend/app/core/config.py` — add pool config settings
**Acceptance Criteria**:
- [ ] Pool size configurable via environment variables (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`)
- [ ] Add `pool_recycle=3600` (recycle connections after 1 hour to avoid stale connections)
- [ ] Add `pool_pre_ping=True` (already present — verify)
- [ ] Document recommended values for dev (5/5) vs production (20-50/10-20)
- [ ] Add pool statistics to `/ready` health endpoint (active, idle, overflow counts)
**Tests**:
- [ ] Pool stats visible in health endpoint
- [ ] Custom pool size works via env vars

---

### Tier 2: Query Optimization (1-2 weeks)

#### Task 13b.4: GraphQL Dataloader Implementation
**Complexity**: L
**Description**: Implement Strawberry dataloaders to eliminate N+1 query problems across all GraphQL resolvers. This is the single highest-impact optimization for GraphQL-heavy workloads.
**Files**:
- `backend/app/api/graphql/dataloaders/` — new directory for dataloader definitions
- `backend/app/api/graphql/dataloaders/__init__.py` — dataloader registry
- `backend/app/api/graphql/dataloaders/tenant.py` — tenant batch loader
- `backend/app/api/graphql/dataloaders/user.py` — user batch loader
- `backend/app/api/graphql/dataloaders/permission.py` — permission batch loader
- `backend/app/api/graphql/dataloaders/cmdb.py` — CI/relationship batch loaders
- `backend/app/api/graphql/dataloaders/audit.py` — audit log batch loader
- Update all GraphQL query/type resolvers to use dataloaders
**Acceptance Criteria**:
- [ ] `DataLoader` pattern from Strawberry integrated into GraphQL context
- [ ] Batch loaders for: tenants, users, roles, permissions, CIs, CI classes, audit logs, notifications, workflows, approvals, semantic types, providers
- [ ] Per-request dataloader instances (scoped to request lifecycle, not global)
- [ ] Verify N+1 elimination: querying a list of 50 CIs with relationships should produce O(1) queries per entity type, not O(N)
- [ ] Add query logging (DEBUG level) to count queries per request
- [ ] Benchmark: measure query count before/after for key operations (CI list, user list, audit log)
**Tests**:
- [ ] Batch loading works (2 queries instead of N+1 for list operations)
- [ ] Dataloader cache is request-scoped (no cross-request leaking)
- [ ] Complex nested queries use batching (e.g., CIs → relationships → target CIs)

---

### Tier 3: Caching (requires Phase 13 Valkey)

#### Task 13b.5: Permission Cache
**Complexity**: M
**Description**: Cache evaluated permissions in Valkey. Permission checks happen on every request; caching avoids repeated DB queries.
**Files**:
- `backend/app/services/permission/cache.py` — permission cache service
- `backend/app/services/permission/engine.py` — integrate cache into evaluation
- `backend/app/core/cache.py` — Valkey cache client (if not already from Phase 13)
**Acceptance Criteria**:
- [ ] Cache key: `perm:{tenant_id}:{user_id}` → serialized permission set
- [ ] TTL: 5 minutes (configurable)
- [ ] Invalidate on: role change, permission override change, group membership change
- [ ] Cache hit/miss metrics exposed to health endpoint
- [ ] Fallback to DB on cache failure (Valkey down = degraded, not broken)
**Tests**:
- [ ] Cache hit avoids DB query
- [ ] Cache invalidated on role change
- [ ] Fallback works when Valkey unavailable

---

#### Task 13b.6: Tenant Configuration Cache
**Complexity**: M
**Description**: Cache tenant settings, quotas, and schema mappings in Valkey. These rarely change but are read on every request.
**Files**:
- `backend/app/services/tenant/cache.py` — tenant config cache
- `backend/app/core/middleware.py` — integrate cached tenant lookup in middleware
**Acceptance Criteria**:
- [ ] Cache key: `tenant:{tenant_id}:config` → tenant settings + quotas
- [ ] Cache key: `tenant:{tenant_id}:schema` → schema name mapping
- [ ] TTL: 15 minutes (configurable)
- [ ] Invalidate on: tenant settings update, quota change
- [ ] TenantContextMiddleware checks cache before DB
**Tests**:
- [ ] Middleware uses cache on second request
- [ ] Cache invalidated on settings change
- [ ] Cache miss falls through to DB

---

#### Task 13b.7: GraphQL Query Result Cache
**Complexity**: M
**Description**: Cache frequently-read, rarely-changed GraphQL query results (semantic types, CI classes, service catalog).
**Files**:
- `backend/app/api/graphql/cache.py` — GraphQL result cache decorator
- Apply to: semantic type queries, CI class definitions, service catalog items, notification templates
**Acceptance Criteria**:
- [ ] `@cached_query(ttl=300, key_fn=...)` decorator for GraphQL resolvers
- [ ] Cache key includes: tenant_id + query args (deterministic hash)
- [ ] TTL per query type: semantic types (30m), CI classes (15m), catalog (10m)
- [ ] Invalidate on mutation (create/update/delete of cached entity type)
- [ ] Cache bypass header: `X-Cache-Bypass: true` for debugging
- [ ] Cache hit/miss in response headers: `X-Cache: HIT|MISS`
**Tests**:
- [ ] Cached query returns same result without DB hit
- [ ] Mutation invalidates relevant cache
- [ ] Bypass header works
- [ ] Different tenants get different cache entries

---

### Tier 4: Infrastructure (if needed after Tier 1-3)

#### Task 13b.8: Evaluate Granian ASGI Server
**Complexity**: S
**Description**: Benchmark Granian (Rust-based ASGI server) as a drop-in replacement for Uvicorn. Reports ~30% faster than Uvicorn for async workloads.
**Files**:
- `backend/pyproject.toml` — add `granian` as optional dependency
- Document benchmark results and decision
**Acceptance Criteria**:
- [ ] Granian added as optional dependency
- [ ] Benchmark: same workload on Uvicorn vs Granian (requests/sec, p50/p95/p99 latency)
- [ ] Test all middleware + GraphQL + WebSocket compatibility
- [ ] Document: if Granian is faster AND compatible, make it the default; otherwise keep Uvicorn
- [ ] Startup script supports both: `--server uvicorn` vs `--server granian`
**Tests**:
- [ ] All existing API tests pass under Granian
- [ ] WebSocket/Socket.IO works (if applicable from Phase 13)

---

#### Task 13b.9: asyncpg Prepared Statements
**Complexity**: M
**Description**: Use PostgreSQL prepared statements for frequently-executed queries to skip query parsing/planning overhead.
**Files**:
- `backend/app/db/session.py` — prepared statement configuration
- `backend/app/services/permission/engine.py` — permission check queries
- `backend/app/core/middleware.py` — tenant lookup queries
**Acceptance Criteria**:
- [ ] Identify top 10 most-frequent queries (permission checks, tenant lookups, audit inserts)
- [ ] Configure SQLAlchemy to use `prepared_statement_cache_size` with asyncpg
- [ ] Verify prepared statements are reused (asyncpg logs)
- [ ] Benchmark: latency improvement for permission check queries
**Tests**:
- [ ] Prepared statement cache populated after warm-up requests
- [ ] Query latency measurably lower for cached queries

---

#### Task 13b.10: Read Replica Support
**Complexity**: L
**Description**: Add support for PostgreSQL read replicas to scale read-heavy GraphQL queries horizontally.
**Files**:
- `backend/app/db/session.py` — add read replica engine
- `backend/app/db/routing.py` — new file, read/write routing logic
- `backend/app/core/config.py` — add `DATABASE_READ_URL` setting
- `backend/app/api/graphql/context.py` — route queries to read replica
**Acceptance Criteria**:
- [ ] Optional `DATABASE_READ_URL` env var (when absent, all queries go to primary)
- [ ] GraphQL queries (read) → read replica; mutations (write) → primary
- [ ] REST endpoints: GET → read replica; POST/PUT/DELETE → primary
- [ ] Replication lag awareness: configurable max lag threshold, fallback to primary
- [ ] Health endpoint shows replica status and lag
- [ ] All existing tests pass (single-DB mode when no replica configured)
**Tests**:
- [ ] Queries route to replica when configured
- [ ] Mutations always go to primary
- [ ] Fallback to primary when replica unavailable
- [ ] Single-DB mode works when `DATABASE_READ_URL` not set

---

## Expected Performance Impact

| Optimization | Expected Gain | Effort |
|-------------|--------------|--------|
| uvloop | 2-4x async I/O throughput | 1 hour |
| orjson | 2-10x serialization speed | 2 hours |
| Connection pool tuning | 10-30% fewer connection waits | 2 hours |
| GraphQL dataloaders | 5-50x fewer DB queries per request | 1-2 weeks |
| Permission cache (Valkey) | 90%+ cache hit rate, ~0ms permission checks | 2-3 days |
| Tenant config cache | Eliminate per-request tenant DB lookup | 1-2 days |
| Query result cache | 100% elimination of repeated reads | 2-3 days |
| Granian ASGI server | ~30% faster than Uvicorn | 1 day (benchmark) |
| Prepared statements | 10-20% faster for hot queries | 2-3 days |
| Read replicas | Horizontal read scaling | 3-5 days |

**Combined Tier 1-2 (no Valkey needed)**: 3-5x improvement in days/weeks
**Combined Tier 1-3 (with Valkey)**: 5-10x improvement
**Full optimization**: 10x+ improvement vs baseline, matching or exceeding a Node.js rewrite

## Phase Completion Checklist

- [ ] All tasks completed (or deferred with justification)
- [ ] File headers follow documentation standards
- [ ] All backend tests pass (pytest)
- [ ] Ruff linting passes
- [ ] Performance verified:
  - [ ] uvloop active in production mode
  - [ ] orjson used for all serialization
  - [ ] Dataloader eliminates N+1 queries
  - [ ] Valkey caching reduces DB load (cache hit rate > 80%)
  - [ ] Benchmark results documented
- [ ] No regressions in functionality
- [ ] Fallbacks work when optional components unavailable (uvloop on Windows, Valkey down)

## Notes & Learnings
[To be filled during implementation]
