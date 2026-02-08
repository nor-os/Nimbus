# Phase 8: Pulumi Integration

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Infrastructure-as-Code integration using Pulumi Automation API, with Temporal workflows for long-running stack operations.

## Deliverables
- Pulumi Automation API integration
- Stack management (create, update, destroy)
- State export and import
- Pulumi Cloud webhook handlers
- Stack event processing
- PulumiDeployWorkflow (Temporal) for preview → approve → execute → verify pipeline
- Saga pattern for rollback on failure
- Pulumi operation progress via Temporal Signals/Queries
- Pulumi status in frontend

## Dependencies
- Phase 7 complete (Proxmox provider as reference implementation)
- Phase 1 Temporal setup (worker, client)

## Key Questions for Refinement
- LocalWorkspace vs RemoteWorkspace?
- How to manage Pulumi project templates?
- Should state be stored in Pulumi Cloud or self-hosted?
- ~~How to handle long-running operations?~~ → Temporal workflows handle this

## Estimated Tasks
~10-12 tasks (to be refined before implementation)
