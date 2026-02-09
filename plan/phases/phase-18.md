# Phase 18: Additional Cloud Providers

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
AWS, Azure, GCP, and OCI provider implementations.

*Was old Phase 18 / originally Phase 16.*

## Deliverables
- AWS provider implementation
- Azure provider implementation
- GCP provider implementation
- OCI provider implementation
- Provider-specific credential management
- Cross-cloud resource view
- Provider selection in frontend

## Dependencies
- Phase 5 complete (semantic layer interface)
- Phase 11 complete (Proxmox as reference implementation)

## Key Questions for Refinement
- Which services per provider to support?
- How to handle provider-specific features?
- Should providers be implemented in parallel or sequentially?
- What authentication methods per provider?
- How to handle OCI-specific concepts (tenancy, compartments) that map closely to Nimbus concepts?

## Estimated Tasks
~15-20 tasks (to be refined before implementation)
