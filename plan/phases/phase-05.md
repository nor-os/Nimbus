# Phase 5: Semantic Layer

## Status
- [x] Refinement complete
- [x] Implementation in progress
- [x] Implementation complete
- [ ] Phase review complete

## Goal
Cloud provider abstraction layer defining abstract resource types/classes and their relationships. Normalizes provider-specific concepts (VPC/VNet/VCN -> Network, etc.) into a unified semantic model. This layer is foundational — the CMDB (Phase 8) uses semantic types as the basis for CI classes, and the Visual Architecture Planner (Phase 7) uses them for its component library.

*Was Phase 6. Decoupled from CMDB — defines abstract types independently. CMDB later imports/references these types.*

## Deliverables
- Semantic model definitions (abstract resource types and their properties)
- Cloud provider interface (abstract `CloudProviderInterface`)
- Provider-to-semantic mapping engine
- Semantic relationship types (how abstract types can relate)
- Unified resource view API
- Semantic layer configuration
- Mapping visualization in frontend

## Dependencies
- No incomplete dependencies (decoupled from CMDB)
- Phase 4 complete (audit logging for semantic layer operations)

## Key Questions for Refinement
- What semantic concepts to support initially?
- How to handle unmappable provider-specific resources?
- Should mappings be configurable per tenant?
- How to handle mapping conflicts?
- What properties should each semantic type define (min/max/required)?
- How do semantic types relate to Rete.js visual components (Phase 7)?

## Semantic Type Hierarchy (Initial)

```
Semantic Types
├── Compute
│   ├── VirtualMachine
│   ├── Container
│   ├── ServerlessFunction
│   └── BareMetalServer
├── Network
│   ├── VirtualNetwork (VPC/VNet/VCN/Bridge)
│   ├── Subnet
│   ├── NetworkInterface
│   ├── LoadBalancer
│   ├── DNS
│   ├── CDN
│   └── VPNGateway
├── Storage
│   ├── BlockStorage
│   ├── ObjectStorage
│   ├── FileStorage
│   └── Backup
├── Database
│   ├── RelationalDatabase
│   ├── NoSQLDatabase
│   ├── CacheService
│   └── DataWarehouse
├── Security
│   ├── SecurityGroup
│   ├── NetworkACL
│   ├── IAMRole
│   ├── IAMPolicy
│   ├── Certificate
│   ├── Secret
│   └── KeyVault
├── Monitoring
│   ├── AlertRule
│   ├── Dashboard
│   ├── LogGroup
│   └── Metric
└── Application
    ├── Application
    ├── Service
    ├── Endpoint
    └── Queue
```

## CloudProviderInterface

```python
class CloudProviderInterface(ABC):
    @abstractmethod
    async def list_resources(self, credential, filters) -> list[ProviderResource]: ...
    @abstractmethod
    async def get_resource(self, credential, resource_id) -> ProviderResource: ...
    @abstractmethod
    async def get_cost_data(self, credential, period) -> CostData: ...
    @abstractmethod
    async def map_to_semantic(self, resource: ProviderResource) -> SemanticResource: ...
    @abstractmethod
    async def validate_credentials(self, credential) -> bool: ...
```

## Estimated Tasks
~6-8 tasks (to be refined before implementation)

## Dependencies for Next Phases
- Phase 7 (Visual Architecture Planner) uses semantic types for component library
- Phase 8 (CMDB) uses semantic types as basis for CI classes
- Phase 11 (Proxmox) implements CloudProviderInterface
- Phase 18 (Cloud Providers) implements CloudProviderInterface for AWS/Azure/GCP/OCI
