# Phase 15: Impersonation

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Secure impersonation workflows using Temporal for durable lifecycle management.

*Was old Phase 13.*

## Deliverables
- Impersonation request model
- ImpersonationWorkflow (Temporal): request → approve → re-auth → session → auto-revoke
  - Reuses ApprovalChainWorkflow (Phase 10) as child workflow for approval step
  - Temporal timer for automatic session expiry (default 30 minutes)
  - Temporal Signal to extend session duration
  - Temporal Signal to end session early
  - Temporal Query for active session status
- Separate audit trail for impersonation (audit activity at each workflow step)
- Re-authentication requirement
- Impersonation UI (request, active session indicator, extend/end controls)
- Emergency impersonation (HSM required, uses BreakGlassWorkflow)

## Dependencies
- Phase 10 complete (ApprovalChainWorkflow)
- Phase 4 complete (audit logging for impersonation trail)
- Phase 1 Temporal setup (worker, client)

## Key Questions for Refinement
- Who can request impersonation (provider admins only)?
- Should impersonation targets be configurable?
- How visible should impersonation be to the target?
- How to handle impersonation during active changes?

## Estimated Tasks
~8-10 tasks (to be refined before implementation)
