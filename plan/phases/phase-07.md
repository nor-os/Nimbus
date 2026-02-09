# Phase 7: Visual Architecture Planner

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Drag-and-drop infrastructure designer using Rete.js. Users design abstract architectures using semantic types (Phase 5) as the component library. Designs can trigger approval workflows (Phase 10) before deployment. Notification integration (Phase 9) for design change alerts and collaboration.

*Was Phase 16. Now Phase 7. Dependencies changed: no longer needs CMDB or Pulumi — works with abstract semantic types only. Pulumi code generation deferred until Phase 12 (Pulumi Integration) is complete.*

## Deliverables
- Rete.js integration in Angular
- Pre-built component library based on semantic types (Phase 5)
- Component connection rules derived from semantic relationship types
- Architecture template management (save/load/share designs)
- Template versioning
- Architecture canvas in frontend
- Component properties panel
- Design validation (checks connection rules)
- Export design as JSON/YAML
- Approval workflow integration (submit design for approval via Phase 10)
- Notification on design changes (via Phase 9)

## Deferred (until Phase 12)
- Template-to-Pulumi code generation (needs Pulumi Integration)
- Direct deploy from canvas (needs Pulumi + provider)

## Dependencies
- Phase 5 complete (semantic types for component library)
- Phase 6 complete (Rete.js canvas infrastructure from Workflow Editor)
- Phase 9 complete (notifications for design change alerts)
- Phase 10 complete (approval workflows for design approval)

## Key Questions for Refinement
- What components to include in initial library? (All semantic types or subset?)
- How to represent cross-cloud architectures?
- Should templates be shareable across tenants?
- What validation rules for connections?
- How to handle component properties (form generated from semantic type schema)?
- Real-time collaboration (deferred to Phase 13 Valkey, or basic version now)?

## Estimated Tasks
~12-15 tasks (to be refined before implementation)
