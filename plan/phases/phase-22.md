# Phase 22: Enterprise Architecture Management

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Model application architecture alongside infrastructure architecture. Introduce enterprise architecture management (EAM) capabilities — application portfolio, business capabilities, technology radar, and application-to-infrastructure mapping. The existing Architecture Topology view (Phase 7) handles infrastructure topology; this phase adds the application/business layer on top.

## Deliverables

### Application Portfolio
- Application registry (CRUD) with lifecycle states (Plan, Build, Run, Retire)
- Application metadata: owner, team, criticality, compliance tags, SLA tier
- Application versioning and release tracking
- Technology stack declarations per application (languages, frameworks, databases)

### Business Capability Mapping
- Business capability hierarchy (multi-level tree)
- Application-to-capability mapping (many-to-many)
- Capability heatmaps (coverage, investment, risk)
- Gap analysis: capabilities without supporting applications

### Application-to-Infrastructure Mapping
- Link applications to infrastructure topologies (Phase 7) and CMDB CIs (Phase 8)
- Dependency graph: application → services → infrastructure resources
- Impact analysis: "if this infrastructure fails, which applications are affected?"
- Deployment mapping: which application runs on which infrastructure

### Technology Radar
- Technology catalog with adoption status (Assess, Trial, Adopt, Hold)
- Technology standards per domain (approved stacks)
- Technical debt tracking tied to applications
- Migration planning: applications on "Hold" technologies

### Visualization & Reporting
- Application landscape map (grid: capability × lifecycle stage)
- Application dependency graph (extends Rete.js canvas from Phase 6/7)
- Portfolio health dashboard (lifecycle distribution, tech debt, risk)
- Cross-layer drill-down: business capability → application → infrastructure

### Integration Points
- Semantic layer (Phase 5): application resource types
- CMDB (Phase 8): applications as CI class, relationships to infrastructure CIs
- Workflows (Phase 6): application lifecycle workflows (onboard, retire)
- Notifications (Phase 9): alerts on application health, tech debt thresholds
- Audit (Phase 4): full audit trail for application portfolio changes

## Dependencies
- Phase 7: Visual Architecture Planner (infrastructure topology canvas)
- Phase 8: CMDB Core (CI relationships)
- Phase 5: Semantic Layer (resource type abstractions)
- Phase 6: Visual Workflow Editor (Rete.js canvas, lifecycle workflows)

## Key Questions for Refinement
- Should applications be a new CI class in CMDB, or a separate top-level entity?
- How deep should business capability modeling go (TOGAF-aligned, lightweight, or configurable)?
- Should the technology radar support organizational standards enforcement (block deploys of "Hold" tech)?
- Integration with external APM tools (Datadog, New Relic) or is this purely declarative/manual?
- Should application teams be modeled separately from tenant users/groups?

## Permissions
- `eam:application:create`, `eam:application:read`, `eam:application:update`, `eam:application:delete`
- `eam:capability:create`, `eam:capability:read`, `eam:capability:update`, `eam:capability:delete`
- `eam:radar:manage` (technology radar administration)
- `eam:portfolio:read` (dashboard/reporting access)

## Estimated Tasks
~20-25 tasks (to be refined before implementation)
