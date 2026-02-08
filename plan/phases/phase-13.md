# Phase 13: Advanced Audit

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Audit features that require Valkey + Socket.IO infrastructure (Phase 12). Completes the audit system started in Phase 4 with real-time streaming, SIEM integration, anomaly detection, and compliance dashboards.

*New phase — split from old Phase 4. These tasks were deferred because they need real-time infrastructure that wasn't available until Phase 12.*

## Deliverables
- Real-time audit event streaming (Socket.IO + Valkey pub/sub)
- SIEM integration (webhook JSON + syslog CEF)
- Anomaly detection service (Temporal scheduled, hourly)
- Compliance dashboard (overview, reports, anomaly alerts)
- Audit timeline view
- User activity view
- Resource history view
- Real-time audit feed component

## Dependencies
- Phase 12 complete (Valkey + Socket.IO for real-time streaming)
- Phase 4 complete (core audit logging infrastructure)

## Tasks (from old Phase 4, renumbered)

### Backend Tasks

#### Task 13.1: Real-time Streaming Service
**Complexity**: M
**Description**: WebSocket streaming for live audit events.
**Files**:
- `backend/app/services/audit/streaming_service.py` - Event streaming
- `backend/app/api/graphql/subscriptions/audit.py` - GraphQL subscription
**Acceptance Criteria**:
- [ ] GraphQL subscription: auditEvents(tenantId, filters)
- [ ] Filter stream by: event_category, event_type, priority, actor
- [ ] Publish audit events to Valkey pub/sub
- [ ] Socket.IO rooms per tenant
- [ ] Backpressure handling (drop old if client slow)
- [ ] Authentication required for subscription
- [ ] Rate limiting on subscriptions
**Tests**:
- [ ] Subscription receives events
- [ ] Filters work on stream
- [ ] Auth required
- [ ] Multiple subscribers work

---

#### Task 13.2: SIEM Integration Service
**Complexity**: M
**Description**: External streaming to SIEM systems.
**Files**:
- `backend/app/services/audit/siem_service.py` - SIEM integration
- `backend/app/services/audit/siem_webhook.py` - Webhook sender
- `backend/app/services/audit/siem_syslog.py` - Syslog sender (CEF)
- `backend/app/models/siem_config.py` - SIEM configuration model
**Acceptance Criteria**:
- [ ] SIEMConfig: tenant_id, type (webhook/syslog), endpoint, auth, filters, enabled
- [ ] Webhook: POST JSON to configured endpoint, retry on failure
- [ ] Syslog: CEF (Common Event Format) over TCP/UDP/TLS
- [ ] Filter which events to send (by category, priority)
- [ ] Batching for efficiency (configurable batch size/interval)
- [ ] Dead letter queue for failed deliveries
- [ ] Health check for SIEM endpoint
- [ ] Audit log for SIEM config changes
**Tests**:
- [ ] Webhook delivers events
- [ ] Syslog formats correctly
- [ ] Filtering works
- [ ] Retry on failure

---

#### Task 13.3: Anomaly Detection Service
**Complexity**: M
**Description**: Detect unusual patterns in audit logs.
**Files**:
- `backend/app/services/audit/anomaly_service.py` - Anomaly detection
- `backend/app/models/audit_anomaly.py` - Anomaly model
- `backend/app/workflows/anomaly_detection.py` - Scheduled detection workflow
**Acceptance Criteria**:
- [ ] Detect: unusual login times, geographic anomalies, brute force attempts
- [ ] Detect: permission escalation patterns, bulk data access
- [ ] Detect: failed operation spikes, unusual API patterns
- [ ] AuditAnomaly: tenant_id, type, severity, details, detected_at, acknowledged, acknowledged_by
- [ ] Temporal Schedule: run detection hourly
- [ ] Configurable detection rules per tenant
- [ ] Alert on high-severity anomalies (via Phase 9 notification service)
- [ ] Mark anomalies as acknowledged/false positive
**Tests**:
- [ ] Brute force detected
- [ ] Unusual time detected
- [ ] Alerts generated
- [ ] Acknowledgment works

---

#### Task 13.4: Advanced Audit GraphQL API
**Complexity**: M
**Description**: GraphQL extensions for advanced audit features.
**Files**:
- `backend/app/api/graphql/mutations/audit.py` - Extended mutations
- `backend/app/api/graphql/subscriptions/audit.py` - Audit subscription
**Acceptance Criteria**:
- [ ] Subscription: auditEvents (from Task 13.1)
- [ ] Mutation: configureSIEM, testSIEMConnection
- [ ] Query: anomalies(tenantId, filters)
- [ ] Mutation: acknowledgeAnomaly, markFalsePositive
**Tests**:
- [ ] Subscription streams events
- [ ] SIEM mutations work
- [ ] Anomaly queries return data

---

### Frontend Tasks

#### Task 13.5: Audit Timeline View
**Complexity**: M
**Description**: Timeline visualization of audit events.
**Files**:
- `frontend/src/app/features/audit/timeline/audit-timeline.component.ts`
- `frontend/src/app/features/audit/timeline/timeline-event.component.ts`
**Acceptance Criteria**:
- [ ] Vertical timeline with events as cards
- [ ] Color-coding by event category
- [ ] Icons by event type
- [ ] Expand card for details
- [ ] Filter timeline by criteria
- [ ] Zoom in/out (time range)
- [ ] Live updates (new events appear at top)
- [ ] Link to full explorer with filters
**Tests**:
- [ ] Timeline renders
- [ ] Events color-coded
- [ ] Live updates work

---

#### Task 13.6: User Activity View
**Complexity**: M
**Description**: View all audit events for a specific user.
**Files**:
- `frontend/src/app/features/audit/user-activity/user-activity.component.ts`
**Acceptance Criteria**:
- [ ] Select user from dropdown or link from user management
- [ ] Show all events where user is actor
- [ ] Summary stats: total events, by category, recent activity
- [ ] Session timeline (group by login sessions)
- [ ] Highlight security events (failed logins, permission denied)
- [ ] Export user activity report
**Tests**:
- [ ] Activity loads for user
- [ ] Sessions grouped correctly

---

#### Task 13.7: Resource History View
**Complexity**: M
**Description**: View audit trail for a specific resource.
**Files**:
- `frontend/src/app/features/audit/resource-history/resource-history.component.ts`
**Acceptance Criteria**:
- [ ] Select resource type and ID
- [ ] Show all events for that resource
- [ ] Timeline of changes
- [ ] Diff viewer between versions
- [ ] Who changed what and when
- [ ] Link from CMDB/other resource views
**Tests**:
- [ ] History loads for resource
- [ ] Diff viewer works

---

#### Task 13.8: Compliance Dashboard
**Complexity**: L
**Description**: Dashboard for compliance officers and auditors.
**Files**:
- `frontend/src/app/features/audit/compliance/compliance-dashboard.component.ts`
- `frontend/src/app/features/audit/compliance/compliance-report.component.ts`
- `frontend/src/app/features/audit/compliance/anomaly-list.component.ts`
**Acceptance Criteria**:
- [ ] Overview cards: total events, by category, by priority
- [ ] Event volume chart (time series)
- [ ] Top actors by activity
- [ ] Security events summary
- [ ] Anomaly alerts list (unacknowledged)
- [ ] Anomaly detail with acknowledge/false positive actions
- [ ] Pre-built compliance reports:
  - [ ] User access report
  - [ ] Permission changes report
  - [ ] Data access report
  - [ ] Security events report
- [ ] Hash chain verification status
**Tests**:
- [ ] Dashboard loads with data
- [ ] Reports generate correctly
- [ ] Anomaly actions work

---

#### Task 13.9: SIEM Configuration UI
**Complexity**: M
**Description**: UI for managing SIEM integration settings.
**Files**:
- `frontend/src/app/features/audit/config/siem-config.component.ts`
**Acceptance Criteria**:
- [ ] SIEM config: enable/disable, endpoint, auth, test connection
- [ ] Event filter configuration
- [ ] Delivery status monitoring
**Tests**:
- [ ] SIEM test connection works
- [ ] Config saves correctly

---

#### Task 13.10: Real-time Audit Feed
**Complexity**: S
**Description**: Live feed component showing audit events as they happen.
**Files**:
- `frontend/src/app/features/audit/feed/audit-feed.component.ts`
**Acceptance Criteria**:
- [ ] Subscribes to audit event stream
- [ ] Shows events as toast notifications or feed list
- [ ] Filter by category/priority
- [ ] Pause/resume feed
- [ ] Click event to view details
- [ ] Embeddable in dashboard
- [ ] Sound/visual alert for critical events
**Tests**:
- [ ] Feed receives events
- [ ] Filtering works
- [ ] Pause/resume works

---

## Phase Completion Checklist

- [ ] All 10 tasks completed
- [ ] File headers follow documentation standards
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] Advanced audit verified:
  - [ ] Real-time streaming works
  - [ ] SIEM integration delivers events
  - [ ] Anomaly detection runs on schedule
  - [ ] Compliance dashboard shows data
- [ ] UI tested end-to-end:
  - [ ] Timeline renders correctly
  - [ ] User activity view works
  - [ ] Resource history shows changes
  - [ ] Compliance dashboard reports generate
  - [ ] SIEM config saves and tests
  - [ ] Live feed receives events

## Notes & Learnings
[To be filled during implementation]
