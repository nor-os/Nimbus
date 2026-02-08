# Phase 10: Approval Workflows (Temporal)

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Configurable approval chains using Temporal workflows. This phase defines the reusable ApprovalChainWorkflow that other phases (drift, impersonation, break-glass, deployments) consume. Now has the notification system (Phase 9) available for approval notifications.

## Deliverables
- ApprovalChainWorkflow (Temporal) — core reusable workflow
  - Configurable approver chain (sequential, parallel, quorum-based)
  - Temporal Signals for approve/reject decisions
  - Temporal Queries for status inspection
  - Timeout + escalation policies (Temporal timers)
  - Denial short-circuit (reject stops chain immediately)
- Approval chain configuration model (DB)
  - Per-tenant approval policies
  - Per-operation type overrides
  - Approver roles/users configuration
- Approval activities (Temporal)
  - send_approval_request (notify approver via Phase 9 notification service)
  - check_approval_status (poll/signal)
  - apply_approved_change (execute the approved operation)
  - send_notification (approval result via Phase 9)
  - record_audit_event (audit trail per step)
- Approval REST/GraphQL API
  - Start approval workflow
  - Submit decision (approve/reject via Temporal Signal)
  - Query workflow status (via Temporal Query)
  - List pending approvals (Temporal visibility API)
- Approval inbox in frontend
- Workflow status dashboard (leveraging Temporal UI + custom views)

## Dependencies
- Phase 9 complete (notification system for approval notifications)
- Phase 1 Temporal setup (worker, client)

## Key Questions for Refinement
- What operations require approval by default?
- ~~How to handle approval timeouts?~~ → Temporal timers with configurable escalation
- Should approvals support delegation? (Temporal Signal to reassign)
- ~~How to handle chain modifications mid-approval?~~ → Temporal versioning for workflow evolution
- Quorum approvals vs sequential chain vs parallel?

## Estimated Tasks
~10-12 tasks (to be refined before implementation)
