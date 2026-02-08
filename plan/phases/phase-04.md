# Phase 4: Audit Logging (Core)

## Status
- [x] Refinement complete
- [x] Implementation in progress
- [x] Implementation complete
- [x] Phase review complete

## Goal
Implement core audit logging with hot/cold storage, cryptographic tamper-evidence, configurable retention, and advanced querying. No real-time streaming, SIEM, or anomaly detection — those move to Phase 13 (Advanced Audit) after Valkey + Socket.IO infrastructure is available.

## Deliverables
- Comprehensive auto-logging (API, data changes, auth, permissions, system events)
- Hybrid storage (tenant schema for tenant events, core for provider/system)
- Hot/cold storage with configurable retention (default 30 days hot)
- Per-tenant and per-event-type retention policies
- Cryptographic hash chain for tamper detection
- Advanced search with full-text, complex filters, saved queries
- Export to JSON and CSV
- Configurable sensitive data redaction
- Archive retrieval from MinIO

## Not Included (Deferred to Phase 13)
- Real-time streaming via WebSocket (needs Valkey + Socket.IO from Phase 12)
- SIEM integration (webhook JSON + syslog CEF)
- Anomaly detection service
- Compliance dashboard with reports and anomaly alerts
- Audit timeline view
- User activity view
- Resource history view
- Real-time audit feed component

## Dependencies
- Phase 3 complete (permissions for audit access, user/group context)

---

## Refinement Questions & Decisions

### Q1: Auto-Logging Scope
**Question**: What events should be logged automatically?
**Decision**: Comprehensive
**Rationale**: Full visibility into API calls, data changes, auth events, permission checks, and system events.

### Q2: Storage Location
**Question**: Where should audit logs be stored?
**Decision**: Hybrid
**Rationale**: Tenant actions in tenant schema (isolation), provider/system events in core (centralized).

### Q3: Volume Handling
**Question**: How to handle high-volume audit data?
**Decision**: Hot/cold storage
**Rationale**: PostgreSQL for recent fast queries, MinIO for cost-effective long-term archive.

### Q4: Retention Model
**Question**: What retention model?
**Decision**: Per-tenant AND per-event-type
**Rationale**: Maximum flexibility - tenants set their policies, different events have different compliance needs.

### Q5: Query Capabilities
**Question**: What query features are needed?
**Decision**: Advanced search
**Rationale**: Full-text search, complex filters, and saved queries for security investigations.

### Q6: Export Formats
**Question**: What export formats?
**Decision**: JSON + CSV
**Rationale**: JSON for systems/automation, CSV for spreadsheets/reporting.

### Q7: Sensitive Data
**Question**: How to handle sensitive data in logs?
**Decision**: Configurable redaction
**Rationale**: Auto-redact known sensitive fields, allow tenants to add custom redaction rules.

### Q8: Hot Retention Default
**Question**: Default hot storage retention?
**Decision**: 30 days (configurable)
**Rationale**: Month of fast queries covers most operational needs.

### Q9: Immutability
**Question**: Should logs be tamper-evident?
**Decision**: Cryptographic hash chain
**Rationale**: Hash-chain linking records provides tamper detection for compliance.

### Q10: Archive Access
**Question**: Archive search capabilities?
**Decision**: Retrieval only
**Rationale**: Download archived logs for local analysis, reduces archive complexity.

---

## Event Categories

| Category | Events | Auto-Logged |
|----------|--------|-------------|
| API | Request/response, latency, status code | Yes |
| Auth | Login, logout, token refresh, MFA, failed attempts | Yes |
| Data | Create, update, delete on any entity | Yes |
| Permission | Permission check (denied), role/group changes | Yes |
| System | Startup, shutdown, config changes, migrations | Yes |
| Security | Break-glass, impersonation, HSM operations | Yes |
| Tenant | Tenant create/update/delete, quota changes | Yes |
| User | User create/update/delete, password changes | Yes |

---

## Audit Log Schema

```
AuditLog {
  id: UUID
  tenant_id: UUID (nullable for system events)

  # Event identification
  event_type: string (e.g., "auth.login", "data.create")
  event_category: enum (api, auth, data, permission, system, security, tenant, user)
  priority: enum (debug, info, warn, error, critical)

  # Actor
  actor_id: UUID (nullable for system)
  actor_type: enum (user, system, service, anonymous)
  actor_email: string (denormalized for search)
  impersonator_id: UUID (nullable)

  # Action
  action: string (e.g., "create", "read", "update", "delete", "login")
  resource_type: string (e.g., "user", "tenant", "cmdb:resource")
  resource_id: UUID (nullable)
  resource_name: string (denormalized)

  # Context
  ip_address: string
  user_agent: string
  trace_id: UUID
  request_method: string
  request_path: string

  # Payload (with redaction)
  request_body: JSONB (redacted)
  response_status: integer
  response_body: JSONB (redacted, optional)

  # Change tracking
  old_values: JSONB (for updates)
  new_values: JSONB (for creates/updates)

  # Tamper evidence
  previous_hash: string
  record_hash: string

  # Timestamps
  timestamp: timestamptz
  archived_at: timestamptz (nullable)
}
```

---

## Tasks

### Backend Tasks

#### Task 4.1: Audit Log Data Models
**Complexity**: L
**Description**: Create audit log models with hash chain support.
**Files**:
- `backend/app/models/audit_log.py` - Main audit log model
- `backend/app/models/audit_retention_policy.py` - Retention policy model
- `backend/app/models/audit_redaction_rule.py` - Redaction rule model
- `backend/app/models/audit_saved_query.py` - Saved query model
- `backend/app/schemas/audit.py` - Pydantic schemas
- `backend/alembic/versions/004_audit_logs.py` - Migration
**Acceptance Criteria**:
- [ ] AuditLog model with all fields from schema above
- [ ] AuditRetentionPolicy: tenant_id, event_category, event_type, hot_retention_days, archive_retention_days
- [ ] AuditRedactionRule: tenant_id, field_path, redaction_type (mask/remove/hash), pattern (optional regex)
- [ ] AuditSavedQuery: tenant_id, user_id, name, filters (JSON), is_shared
- [ ] Indexes on: tenant_id, timestamp, event_type, actor_id, resource_type, resource_id
- [ ] Composite index for common query patterns
- [ ] Hash chain fields (previous_hash, record_hash)
**Tests**:
- [ ] Models create correctly
- [ ] Indexes exist
- [ ] Retention policies work

---

#### Task 4.2: Hash Chain Service
**Complexity**: M
**Description**: Implement cryptographic hash chain for tamper detection.
**Files**:
- `backend/app/services/audit/hash_chain.py` - Hash chain implementation
**Acceptance Criteria**:
- [ ] calculate_record_hash(record, previous_hash) - SHA-256 of record + previous
- [ ] Hash includes: timestamp, event_type, actor_id, action, resource_id, payload hash
- [ ] verify_chain(start_id, end_id) - verify hash chain integrity
- [ ] Separate chains per tenant (or per partition)
- [ ] Chain initialization for new tenants
- [ ] Handle concurrent inserts (sequence/locking)
- [ ] Chain repair guidance for detected breaks
**Tests**:
- [ ] Hash calculated correctly
- [ ] Chain verification detects tampering
- [ ] Concurrent inserts maintain chain

---

#### Task 4.3: Audit Logging Service
**Complexity**: L
**Description**: Core service for creating audit log entries.
**Files**:
- `backend/app/services/audit/__init__.py`
- `backend/app/services/audit/service.py` - AuditService
- `backend/app/services/audit/context.py` - Audit context builder
**Acceptance Criteria**:
- [ ] log_event(event_type, action, resource, actor, payload, ...) - main logging method
- [ ] Context builder extracts: IP, user agent, trace ID, actor from request
- [ ] Automatic hash chain linking
- [ ] Async logging (non-blocking to request)
- [ ] Batch logging support for bulk operations
- [ ] Manual logging API for custom events
- [ ] Event enrichment (denormalize actor email, resource name)
**Tests**:
- [ ] Events logged correctly
- [ ] Context extracted properly
- [ ] Async doesn't block request
- [ ] Batch logging works

---

#### Task 4.4: Automatic Redaction Service
**Complexity**: M
**Description**: Redact sensitive data from audit log payloads.
**Files**:
- `backend/app/services/audit/redaction.py` - Redaction service
- `backend/app/services/audit/redaction_rules.py` - Default redaction rules
**Acceptance Criteria**:
- [ ] Default rules for: password, token, secret, key, authorization header, credit card
- [ ] Redaction types: mask (show partial), remove (delete field), hash (one-way hash)
- [ ] apply_redaction(payload, tenant_id) - applies tenant + default rules
- [ ] Regex pattern support for custom rules
- [ ] Nested field path support (e.g., "user.credentials.password")
- [ ] Tenant-specific rules override/extend defaults
- [ ] Redaction is irreversible (applied before storage)
**Tests**:
- [ ] Default fields redacted
- [ ] Custom rules apply
- [ ] Nested paths work
- [ ] Redaction irreversible

---

#### Task 4.5: Audit Middleware
**Complexity**: M
**Description**: Automatic audit logging for API requests.
**Files**:
- `backend/app/core/audit_middleware.py` - Request/response logging middleware
- `backend/app/core/audit_decorators.py` - Decorators for custom audit events
**Acceptance Criteria**:
- [ ] Log all API requests with: method, path, status, latency
- [ ] Include request body (redacted) for mutations
- [ ] Include response body (redacted, configurable)
- [ ] Skip health/metrics endpoints
- [ ] @audit_event("event_type") decorator for custom events
- [ ] Capture exceptions as error events
- [ ] Link to trace ID from request
**Tests**:
- [ ] All API calls logged
- [ ] Mutations include body
- [ ] Health endpoints skipped
- [ ] Decorator works

---

#### Task 4.6: Data Change Auditing
**Complexity**: M
**Description**: Automatic audit logging for database changes.
**Files**:
- `backend/app/db/audit_hooks.py` - SQLAlchemy event hooks
- `backend/app/services/audit/change_tracker.py` - Change detection
**Acceptance Criteria**:
- [ ] SQLAlchemy after_insert, after_update, after_delete hooks
- [ ] Capture old_values and new_values for updates
- [ ] Track which fields changed
- [ ] Link to current request context (actor, trace_id)
- [ ] Configurable per-model (opt-out for high-volume tables)
- [ ] Handle bulk operations efficiently
- [ ] Exclude audit log table from auditing (prevent recursion)
**Tests**:
- [ ] Insert creates audit log
- [ ] Update captures old/new values
- [ ] Delete logs with old values
- [ ] Bulk operations handled

---

#### Task 4.7: Retention and Archival Service
**Complexity**: L
**Description**: Manage hot/cold storage and retention policies.
**Files**:
- `backend/app/services/audit/retention_service.py` - Retention management
- `backend/app/services/audit/archive_service.py` - Archive to MinIO
- `backend/app/workflows/audit_archive.py` - Archival workflow
- `backend/app/workflows/activities/audit_archive.py` - Archive/purge activities
**Acceptance Criteria**:
- [ ] get_retention_policy(tenant_id, event_type) - returns applicable policy
- [ ] Default policy: 30 days hot, 365 days archive
- [ ] archive_old_logs() - Temporal scheduled workflow, moves logs past hot retention to MinIO
- [ ] Archive format: JSONL files, gzipped, organized by tenant/date
- [ ] purge_expired_archives() - delete archives past retention
- [ ] Archive manifest for retrieval
- [ ] Verify hash chain before archiving
- [ ] Mark archived records (archived_at timestamp)
**Tests**:
- [ ] Correct policy selected
- [ ] Archival moves to MinIO
- [ ] Purge deletes expired
- [ ] Chain verified before archive

---

#### Task 4.8: Audit Query Service
**Complexity**: L
**Description**: Advanced search and filtering for audit logs.
**Files**:
- `backend/app/services/audit/query_service.py` - Query building
- `backend/app/services/audit/search_service.py` - Full-text search
**Acceptance Criteria**:
- [ ] Filter by: date range, event_type, event_category, actor, resource, priority
- [ ] Full-text search across: actor_email, resource_name, request_body, response_body
- [ ] Complex filters: AND/OR grouping, nested conditions
- [ ] Sort by: timestamp (default), event_type, actor
- [ ] Pagination with cursor-based navigation
- [ ] Saved queries: save, load, share with tenant
- [ ] Query validation and sanitization
- [ ] Query timeout for large result sets
**Tests**:
- [ ] Filters work correctly
- [ ] Full-text search finds matches
- [ ] Complex queries execute
- [ ] Saved queries persist

---

#### Task 4.9: Archive Retrieval Service
**Complexity**: M
**Description**: Retrieve and download archived audit logs.
**Files**:
- `backend/app/services/audit/archive_retrieval.py` - Archive access
**Acceptance Criteria**:
- [ ] list_archives(tenant_id, date_range) - list available archives
- [ ] request_archive_download(archive_id) - generate signed download URL
- [ ] Download from MinIO with expiring URL
- [ ] Verify archive integrity (checksum)
- [ ] Bulk download request (multiple archives as ZIP)
- [ ] Audit log for archive access
**Tests**:
- [ ] Archives listed correctly
- [ ] Download URL works
- [ ] Integrity verified
- [ ] Access audited

---

#### Task 4.10: Export Service
**Complexity**: M
**Description**: Export audit logs to JSON and CSV formats.
**Files**:
- `backend/app/services/audit/export_service.py` - Export generation
- `backend/app/workflows/audit_export.py` - Async export workflow
**Acceptance Criteria**:
- [ ] Export with filters (date range, event type, etc.)
- [ ] Export formats: JSON (JSONL), CSV
- [ ] Async export for large datasets (Temporal workflow)
- [ ] Export stored in MinIO with expiration (7 days)
- [ ] Row limit per export (configurable, default 100k)
- [ ] Include hash chain verification in export metadata
**Tests**:
- [ ] JSON export correct format
- [ ] CSV export correct format
- [ ] Large export async
- [ ] Download works

---

#### Task 4.11: Audit REST API
**Complexity**: M
**Description**: REST endpoints for audit log access.
**Files**:
- `backend/app/api/v1/endpoints/audit.py` - Audit endpoints
**Acceptance Criteria**:
- [ ] `GET /api/v1/audit/logs` - query logs with filters
- [ ] `GET /api/v1/audit/logs/{id}` - get single log entry
- [ ] `GET /api/v1/audit/logs/actor/{id}` - logs by actor
- [ ] `GET /api/v1/audit/logs/resource/{type}/{id}` - logs by resource
- [ ] `POST /api/v1/audit/logs/search` - advanced search
- [ ] `GET /api/v1/audit/retention` - get retention policies
- [ ] `PUT /api/v1/audit/retention` - update retention policies
- [ ] `GET /api/v1/audit/redaction` - get redaction rules
- [ ] `POST /api/v1/audit/redaction` - create redaction rule
- [ ] `GET /api/v1/audit/queries` - list saved queries
- [ ] `POST /api/v1/audit/queries` - save query
- [ ] `POST /api/v1/audit/export` - request export with filters
- [ ] `GET /api/v1/audit/export/{job_id}` - check export status
- [ ] `GET /api/v1/audit/export/{job_id}/download` - download export
- [ ] `GET /api/v1/audit/archives` - list archives
- [ ] `GET /api/v1/audit/archives/{id}/download` - download archive
- [ ] Permission checks on all endpoints
**Tests**:
- [ ] Query returns correct logs
- [ ] Filters work
- [ ] Permissions enforced

---

#### Task 4.12: Audit GraphQL API
**Complexity**: M
**Description**: GraphQL schema for audit operations.
**Files**:
- `backend/app/api/graphql/types/audit.py` - Audit types
- `backend/app/api/graphql/queries/audit.py` - Audit queries
- `backend/app/api/graphql/mutations/audit.py` - Audit mutations
**Acceptance Criteria**:
- [ ] Query: auditLog(id), auditLogs(filter, pagination)
- [ ] Query: auditLogsByActor(actorId), auditLogsByResource(type, id)
- [ ] Query: retentionPolicies, redactionRules, savedQueries
- [ ] Query: verifyHashChain(startId, endId)
- [ ] Mutation: updateRetentionPolicy, createRedactionRule, deleteRedactionRule
- [ ] Mutation: saveQuery, deleteQuery
**Tests**:
- [ ] Queries return correct data
- [ ] Mutations work

---

### Frontend Tasks

#### Task 4.13: Audit Service (Frontend)
**Complexity**: M
**Description**: Angular service for audit log access.
**Files**:
- `frontend/src/app/core/services/audit.service.ts` - Audit API service
- `frontend/src/app/core/models/audit.model.ts` - Audit types
**Acceptance Criteria**:
- [ ] Query methods for all REST/GraphQL endpoints
- [ ] Export request and download
- [ ] Saved query management
- [ ] Retention policy management
**Tests**:
- [ ] Service methods work

---

#### Task 4.14: Audit Log Explorer
**Complexity**: L
**Description**: Main UI for browsing and searching audit logs.
**Files**:
- `frontend/src/app/features/audit/explorer/audit-explorer.component.ts`
- `frontend/src/app/features/audit/explorer/audit-filter-panel.component.ts`
- `frontend/src/app/features/audit/explorer/audit-log-table.component.ts`
- `frontend/src/app/features/audit/explorer/audit-log-detail.component.ts`
**Acceptance Criteria**:
- [ ] Filter panel: date range, event type, category, actor, resource, priority
- [ ] Full-text search box
- [ ] Results table with: timestamp, event, actor, resource, status
- [ ] Expandable row for details
- [ ] Detail modal with full event data
- [ ] Payload viewer with JSON formatting
- [ ] Old/new value diff viewer for updates
- [ ] Pagination with infinite scroll option
- [ ] Column customization
- [ ] Export button (JSON/CSV)
**Tests**:
- [ ] Filters work
- [ ] Search finds results
- [ ] Detail shows correctly

---

#### Task 4.15: Audit Configuration UI
**Complexity**: M
**Description**: UI for managing audit settings.
**Files**:
- `frontend/src/app/features/audit/config/retention-config.component.ts`
- `frontend/src/app/features/audit/config/redaction-config.component.ts`
- `frontend/src/app/features/audit/config/saved-queries.component.ts`
**Acceptance Criteria**:
- [ ] Retention config: set hot/archive days per event type
- [ ] Redaction rules: list, create, edit, delete rules
- [ ] Redaction rule builder: field path, type, pattern
- [ ] Saved queries: list, rename, delete, share toggle
- [ ] Archive browser: list archives, request download
**Tests**:
- [ ] Retention saves correctly
- [ ] Redaction rules work

---

## Phase Completion Checklist

- [ ] All 15 tasks completed
- [ ] File headers follow documentation standards
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] Audit system verified:
  - [ ] All event types logged automatically
  - [ ] Hash chain maintains integrity
  - [ ] Redaction removes sensitive data
  - [ ] Hot/cold storage works
  - [ ] Retention policies enforced
- [ ] UI tested end-to-end:
  - [ ] Explorer search works
  - [ ] Configuration saves correctly
  - [ ] Export downloads work

## Dependencies for Next Phase
Phase 5 (CMDB Core) will build on:
- Audit logging for all CMDB operations
- Query patterns for CMDB search

Phase 13 (Advanced Audit) will add:
- Real-time streaming (needs Phase 12 Valkey + Socket.IO)
- SIEM integration
- Anomaly detection
- Compliance dashboard
- Timeline, user activity, and resource history views

## Notes & Learnings
[To be filled during implementation]
