# Phase 17: Drift Detection

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Detect and manage configuration drift between desired (Pulumi state) and actual (cloud provider) state. Uses approval workflows (Phase 10) for remediation approval and notifications (Phase 9) for alerting.

*Was old Phase 11 / originally Phase 9. Moved because it depends on Pulumi state (Phase 12) and approval workflows (Phase 10).*

## Deliverables
- Drift scan trigger (Temporal Schedule)
- Drift detection engine (compare Pulumi state vs live provider state)
- Drift delta table model
- DriftRemediationWorkflow (Temporal): detect → notify → approve → remediate pipeline
- Drift severity classification
- Drift notifications (via Phase 9 notification service)
- Auto-approve option for low-severity drift
- Drift report dashboard
- Drift detail view with diff

## Dependencies
- Phase 12 complete (Pulumi state for comparison)
- Phase 10 complete (ApprovalChainWorkflow for remediation approval)
- Phase 1 Temporal setup (worker, client)

## Key Questions for Refinement
- How to calculate drift (state diff vs live check)?
- What drift severity levels to support?
- How to handle acceptable vs unacceptable drift?
- Should drift auto-remediation be supported? → Via Temporal workflow with configurable auto-approve

## Estimated Tasks
~10-12 tasks (to be refined before implementation)
