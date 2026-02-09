# Phase 11: Cloud Provider Integration (Proxmox)

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
First cloud provider implementation using Proxmox VE. Proxmox provides a free, self-hosted virtualization platform with a full REST API — ideal for developing and testing the entire provider integration pipeline without cloud provider accounts or costs.

*Was Phase 7. Now Phase 11.*

## Deliverables
- Proxmox provider implementing CloudProviderInterface (from Phase 5)
- Proxmox credential management (API token encrypted storage)
- Resource discovery from Proxmox (VMs, containers, storage, networks)
- Proxmox-to-semantic mapping (using Phase 5 semantic types)
- Resource usage tracking (CPU, memory, disk — Proxmox has no native billing)
- Proxmox connection wizard in frontend
- Pulumi Proxmox provider (`bpg/proxmox`) integration

## Dependencies
- Phase 5 complete (semantic layer interface / CloudProviderInterface)
- Phase 8 complete (CMDB for storing discovered resources as CIs)

## Key Questions for Refinement
- Which Proxmox resource types to support initially? (QEMU VMs, LXC containers, storage, networking)
- How to handle Proxmox authentication? (API tokens vs username/password)
- How to map Proxmox pools to compartments?
- How to handle resource usage tracking without native billing API?
- Single node or cluster support initially?
- Which Pulumi Proxmox provider to use? (`bpg/proxmox` is most actively maintained)

## Proxmox Semantic Mapping

| Nimbus Concept | Proxmox Equivalent |
|---|---|
| Tenancy | Datacenter / Cluster |
| Compartment | Pool |
| Network | Bridge / SDN VNet |
| Compute | QEMU VM / LXC Container |
| Storage | Storage (ZFS, Ceph, LVM, local, NFS) |
| Database | N/A (VM-hosted) |
| Load Balancer | N/A (VM-hosted) |
| Security Group | Firewall rules |

## Why Proxmox First

1. **Free and self-hosted** — no cloud accounts or billing needed during development
2. **Real infrastructure** — actual VMs, containers, networking (not mocks)
3. **Full REST API** — `https://<host>:8006/api2/json/` covers all operations
4. **Pulumi support** — `bpg/proxmox` community provider works with Automation API
5. **Drift detection testable** — change a VM config in Proxmox UI, Nimbus detects it
6. **End-to-end validation** — proves the CloudProviderInterface, semantic layer, CMDB population, and Pulumi deploy pipeline all work together before touching cloud providers

## Estimated Tasks
~8-10 tasks (to be refined before implementation)
