# Phase 5: CMDB Core

## Status
- [x] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Implement Configuration Management Database with comprehensive CI classes, graph-based relationships, service catalog with pricing, full extensibility, snapshot versioning, and advanced graph analytics.

## Deliverables
- Comprehensive CI classes (Infrastructure, Services, Security, Monitoring, Cost centers)
- Service catalog with measuring units and tenant-specific pricing
- Graph model for CI relationships with full analytics
- Unlimited compartment nesting
- Full attribute extensibility (tags + custom definitions)
- Snapshot versioning for point-in-time views
- Full CI templates with constraints
- Advanced search with graph traversal and saved queries
- Standard ITIL lifecycle states
- Validation rules (schema, range, regex, uniqueness)
- Full visualization (list, tree, relationship graph)
- Impact analysis and dependency chain queries

## Dependencies
- Phase 2 complete (tenant context, basic Compartment model)
- Phase 4 complete (audit logging for CMDB operations)

---

## Refinement Questions & Decisions

### Q1: Initial CI Classes
**Question**: What CI classes to implement initially?
**Decision**: Comprehensive + Services with service catalog
**Rationale**: Full infrastructure coverage plus service catalog for MSP/service provider business model.

### Q2: Relationship Model
**Question**: How to model CI relationships?
**Decision**: Graph model
**Rationale**: Vertices/edges support complex traversal, impact analysis, and dependency mapping.

### Q3: Custom Attributes
**Question**: Support custom attributes?
**Decision**: Full extensibility
**Rationale**: Tags + custom attribute definitions per tenant/class for maximum flexibility.

### Q4: Compartment Hierarchy
**Question**: How deep can compartments nest?
**Decision**: Unlimited nesting
**Rationale**: Recursive hierarchy supports complex organizational structures.

### Q5: Search Capabilities
**Question**: What search features?
**Decision**: Advanced query
**Rationale**: Full-text + graph traversal + saved searches for complex CMDB exploration.

### Q6: Versioning
**Question**: How to handle CI history?
**Decision**: Snapshot versioning
**Rationale**: Complete snapshots enable point-in-time views and easy rollback analysis.

### Q7: Templates
**Question**: Support CI templates?
**Decision**: Full templates
**Rationale**: Reusable templates with predefined attributes, relationships, and constraints.

### Q8: Pricing Model
**Question**: Service catalog pricing approach?
**Decision**: Simple pricing with tenant-specific overrides
**Rationale**: Default price list with per-tenant overrides balances simplicity and flexibility.

### Q9: Lifecycle States
**Question**: CI lifecycle management?
**Decision**: Standard ITIL
**Rationale**: Industry-standard states (Planned, Active, Maintenance, Retired, Deleted).

### Q10: Validation Rules
**Question**: What validation capabilities?
**Decision**: Basic rules
**Rationale**: Schema + range checks, regex patterns, uniqueness constraints cover most needs.

### Q11: Visualization
**Question**: What visualization features?
**Decision**: Full visualization
**Rationale**: List, tree, and relationship graph for complete CMDB exploration.

### Q12: Bulk Operations
**Question**: Support bulk operations?
**Decision**: Single item only
**Rationale**: Keep Phase 5 focused; bulk import can be added later if needed.

### Q13: Class Management
**Question**: How to manage CI class definitions?
**Decision**: Extend system
**Rationale**: System classes provide foundation, tenants can add custom classes.

### Q14: Attachments
**Question**: Support documents/attachments?
**Decision**: Link references
**Rationale**: Store URLs to external documents, avoid file storage complexity.

### Q15: Graph Queries
**Question**: What graph query capabilities?
**Decision**: Full graph analytics
**Rationale**: Impact analysis and dependency chains are core CMDB value propositions.

### Q16: Compartment Model (Cross-Phase Consistency)
**Question**: How does CMDB Compartment relate to Phase 2 Compartment?
**Decision**: Extend Phase 2 model
**Rationale**: Phase 2 creates basic Compartment model (id, tenant_id, parent_id, name, description). Phase 5 extends it with CMDB-specific fields (cloud_id, provider_type) and adds the full hierarchy service.

---

## CI Class Hierarchy

```
CI Classes
├── Infrastructure
│   ├── Compute
│   │   ├── VirtualMachine
│   │   ├── Container
│   │   ├── ServerlessFunction
│   │   └── BareMetalServer
│   ├── Network
│   │   ├── VirtualNetwork (VPC/VNet/VCN)
│   │   ├── Subnet
│   │   ├── NetworkInterface
│   │   ├── LoadBalancer
│   │   ├── DNS
│   │   ├── CDN
│   │   └── VPNGateway
│   ├── Storage
│   │   ├── BlockStorage
│   │   ├── ObjectStorage
│   │   ├── FileStorage
│   │   └── Backup
│   └── Database
│       ├── RelationalDatabase
│       ├── NoSQLDatabase
│       ├── CacheService
│       └── DataWarehouse
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
├── Application
│   ├── Application
│   ├── Service
│   ├── Endpoint
│   └── Queue
└── ServiceCatalog
    ├── ServiceOffering
    ├── PriceListItem
    └── UsageMetric
```

---

## Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| contains | Parent contains child | VPC contains Subnet |
| belongs_to | Child belongs to parent | VM belongs to Subnet |
| connects_to | Network connection | VM connects to LoadBalancer |
| depends_on | Runtime dependency | App depends on Database |
| uses | Resource usage | App uses Storage |
| secures | Security relationship | SecurityGroup secures VM |
| monitors | Monitoring relationship | AlertRule monitors VM |
| backs_up | Backup relationship | Backup backs_up Database |

---

## Service Catalog & Pricing

```
ServiceOffering {
  id: UUID
  tenant_id: UUID
  name: string
  description: string
  category: string
  measuring_unit: enum (hour, day, month, GB, request, user, instance)
  ci_class: string (optional - linked CI class)
  is_active: boolean
}

PriceList {
  id: UUID
  tenant_id: UUID (null for default)
  name: string
  is_default: boolean
  effective_from: date
  effective_to: date (nullable)
}

PriceListItem {
  id: UUID
  price_list_id: UUID
  service_offering_id: UUID
  price_per_unit: decimal
  currency: string (default: EUR)
  min_quantity: decimal (optional)
  max_quantity: decimal (optional)
}

TenantPriceOverride {
  id: UUID
  tenant_id: UUID
  service_offering_id: UUID
  price_per_unit: decimal
  discount_percent: decimal (optional)
  effective_from: date
  effective_to: date (nullable)
}
```

---

## Tasks

### Backend Tasks

#### Task 5.1: CI Core Data Models
**Complexity**: L
**Description**: Create core CMDB models for CIs and classes. Extend Phase 2 Compartment model with CMDB fields.
**Files**:
- `backend/app/models/cmdb/ci.py` - ConfigurationItem model
- `backend/app/models/cmdb/ci_class.py` - CIClass definition model
- `backend/app/models/cmdb/ci_attribute.py` - Custom attribute definitions
- `backend/app/schemas/cmdb.py` - Pydantic schemas
- `backend/alembic/versions/005_cmdb_core.py` - Migration (extends Compartment table)
**Acceptance Criteria**:
- [ ] ConfigurationItem: id, tenant_id, ci_class_id, compartment_id, name, description, lifecycle_state, attributes (JSONB), tags (JSONB), cloud_resource_id, pulumi_urn, created_at, updated_at, deleted_at
- [ ] CIClass: id, tenant_id (null for system), name, parent_class_id, schema (JSON), icon, is_system, is_active
- [ ] CIAttributeDefinition: id, ci_class_id, tenant_id, name, data_type, is_required, default_value, validation_rules (JSON)
- [ ] Extend Phase 2 Compartment with: cloud_id, provider_type (CMDB-specific fields)
- [ ] Lifecycle states enum: planned, active, maintenance, retired, deleted
- [ ] Indexes for common queries
**Note**: Compartment base model (id, tenant_id, parent_id, name, description) created in Phase 2. This task adds CMDB-specific extensions.
**Tests**:
- [ ] CI CRUD works
- [ ] Compartment nesting works (unlimited)
- [ ] CI class inheritance works

---

#### Task 5.2: Graph Relationship Models
**Complexity**: L
**Description**: Implement graph-based relationship storage.
**Files**:
- `backend/app/models/cmdb/ci_relationship.py` - Relationship model
- `backend/app/models/cmdb/relationship_type.py` - Relationship type definitions
**Acceptance Criteria**:
- [ ] CIRelationship: id, source_ci_id, target_ci_id, relationship_type_id, attributes (JSONB), created_at
- [ ] RelationshipType: id, name, inverse_name, source_class_ids, target_class_ids, is_system
- [ ] System relationship types: contains, belongs_to, connects_to, depends_on, uses, secures, monitors, backs_up
- [ ] Tenant can create custom relationship types
- [ ] Indexes for graph traversal (source_ci_id, target_ci_id, type)
- [ ] Prevent self-referential relationships
- [ ] Prevent duplicate relationships
**Tests**:
- [ ] Relationships create correctly
- [ ] Inverse relationships work
- [ ] Duplicates prevented

---

#### Task 5.3: CI Snapshot Versioning
**Complexity**: M
**Description**: Implement snapshot versioning for CI history.
**Files**:
- `backend/app/models/cmdb/ci_snapshot.py` - Snapshot model
- `backend/app/services/cmdb/versioning_service.py` - Version management
**Acceptance Criteria**:
- [ ] CISnapshot: id, ci_id, version_number, snapshot_data (JSONB), changed_by, changed_at, change_reason
- [ ] Automatic snapshot on CI create/update
- [ ] get_ci_at_version(ci_id, version) - reconstruct CI at specific version
- [ ] get_ci_at_time(ci_id, timestamp) - point-in-time view
- [ ] list_ci_versions(ci_id) - version history
- [ ] compare_versions(ci_id, v1, v2) - diff between versions
- [ ] Snapshot includes: attributes, tags, relationships
**Tests**:
- [ ] Snapshots created on changes
- [ ] Point-in-time retrieval works
- [ ] Diff shows changes correctly

---

#### Task 5.4: Service Catalog Models
**Complexity**: M
**Description**: Implement service catalog with pricing.
**Files**:
- `backend/app/models/cmdb/service_offering.py` - Service offering model
- `backend/app/models/cmdb/price_list.py` - Price list models
- `backend/app/schemas/service_catalog.py` - Pydantic schemas
**Acceptance Criteria**:
- [ ] ServiceOffering: as defined in schema above
- [ ] PriceList: as defined above
- [ ] PriceListItem: as defined above
- [ ] TenantPriceOverride: as defined above
- [ ] Measuring units enum: hour, day, month, gb, request, user, instance
- [ ] get_price(tenant_id, service_offering_id) - returns effective price with overrides
- [ ] Price effective date handling
**Tests**:
- [ ] Service offerings CRUD
- [ ] Price calculation with overrides
- [ ] Effective date logic works

---

#### Task 5.5: CI Template System
**Complexity**: M
**Description**: Implement reusable CI templates.
**Files**:
- `backend/app/models/cmdb/ci_template.py` - Template model
- `backend/app/services/cmdb/template_service.py` - Template management
**Acceptance Criteria**:
- [ ] CITemplate: id, tenant_id, name, description, ci_class_id, attributes (JSONB), tags (JSONB), relationship_templates (JSON), constraints (JSON), is_active
- [ ] RelationshipTemplate: relationship_type, target_template_id or target_class
- [ ] create_ci_from_template(template_id, overrides) - instantiate template
- [ ] Template constraints: required relationships, attribute constraints
- [ ] Template versioning (simple version number)
- [ ] Clone template functionality
**Tests**:
- [ ] Template creates CI correctly
- [ ] Constraints validated
- [ ] Relationship templates work

---

#### Task 5.6: Validation Rules Engine
**Complexity**: M
**Description**: Implement CI validation rules.
**Files**:
- `backend/app/services/cmdb/validation_service.py` - Validation engine
- `backend/app/models/cmdb/validation_rule.py` - Custom validation rules
**Acceptance Criteria**:
- [ ] Schema validation: data types, required fields
- [ ] Range validation: min/max for numbers, length for strings
- [ ] Regex validation: pattern matching for strings
- [ ] Uniqueness validation: unique attributes within scope (tenant, compartment, class)
- [ ] validate_ci(ci_data, ci_class) - returns validation result
- [ ] ValidationResult: is_valid, errors (field, message, rule)
- [ ] Custom validation rules per CI class (stored in CIAttributeDefinition)
**Tests**:
- [ ] Schema validation works
- [ ] Range checks work
- [ ] Regex patterns work
- [ ] Uniqueness enforced

---

#### Task 5.7: CMDB Service Layer
**Complexity**: L
**Description**: Core CMDB service for CI operations. Extends Phase 2 compartment service with CMDB features.
**Files**:
- `backend/app/services/cmdb/__init__.py`
- `backend/app/services/cmdb/ci_service.py` - CI CRUD service
- `backend/app/services/cmdb/compartment_service.py` - Extends Phase 2 CompartmentService with CMDB features
**Acceptance Criteria**:
- [ ] create_ci(data) - validate, create, snapshot, audit log
- [ ] update_ci(ci_id, data) - validate, update, snapshot, audit log
- [ ] delete_ci(ci_id) - soft delete, snapshot, audit log
- [ ] get_ci(ci_id, version=None) - current or specific version
- [ ] list_cis(filters, pagination) - with compartment, class, state filters
- [ ] move_ci(ci_id, new_compartment_id) - move between compartments
- [ ] Extend Phase 2 CompartmentService with: cloud sync, provider mapping
- [ ] Lifecycle state transitions with validation
**Note**: Phase 2 provides basic compartment CRUD. This task adds CMDB-specific operations (cloud sync, CI-aware operations).
**Tests**:
- [ ] CRUD operations work
- [ ] Versioning triggered
- [ ] Audit logging works
- [ ] State transitions validated

---

#### Task 5.8: Graph Query Service
**Complexity**: L
**Description**: Implement graph traversal and analytics queries.
**Files**:
- `backend/app/services/cmdb/graph_service.py` - Graph query engine
- `backend/app/services/cmdb/impact_service.py` - Impact analysis
**Acceptance Criteria**:
- [ ] get_relationships(ci_id, direction, type) - direct relationships
- [ ] traverse(ci_id, relationship_types, max_depth) - multi-hop traversal
- [ ] find_path(source_ci_id, target_ci_id) - shortest path between CIs
- [ ] get_dependency_chain(ci_id, direction) - upstream/downstream dependencies
- [ ] impact_analysis(ci_id) - what would be affected if this CI fails
- [ ] reverse_impact(ci_id) - what does this CI depend on
- [ ] Cycle detection in relationships
- [ ] Query result caching (optional)
**Tests**:
- [ ] Traversal returns correct CIs
- [ ] Path finding works
- [ ] Impact analysis correct
- [ ] Cycles detected

---

#### Task 5.9: Advanced Search Service
**Complexity**: L
**Description**: Full-text and graph-aware search.
**Files**:
- `backend/app/services/cmdb/search_service.py` - Search implementation
- `backend/app/models/cmdb/saved_search.py` - Saved search model
**Acceptance Criteria**:
- [ ] Full-text search across: name, description, attribute values, tags
- [ ] Filter by: class, compartment, state, tags, custom attributes
- [ ] Graph-aware queries: "CIs connected to X", "CIs in dependency chain of X"
- [ ] Faceted search results (counts by class, state, compartment)
- [ ] SavedSearch: id, tenant_id, user_id, name, query (JSON), is_shared
- [ ] Search syntax: support AND/OR, quotes for phrases, field:value
- [ ] Pagination with total count
**Tests**:
- [ ] Full-text finds matches
- [ ] Filters work correctly
- [ ] Graph queries work
- [ ] Saved searches persist

---

#### Task 5.10: CI Class Management Service
**Complexity**: M
**Description**: Manage CI class definitions.
**Files**:
- `backend/app/services/cmdb/class_service.py` - CI class management
- `backend/app/services/cmdb/class_seed.py` - System class seeding
**Acceptance Criteria**:
- [ ] Seed system CI classes on initialization
- [ ] System classes: all from hierarchy above
- [ ] create_custom_class(tenant_id, data) - tenant custom classes
- [ ] Custom class can inherit from system class
- [ ] update_class(class_id, data) - update schema (tenant classes only)
- [ ] list_classes(tenant_id) - system + tenant classes
- [ ] Schema migration for existing CIs when class updated
- [ ] Cannot delete class with existing CIs
**Tests**:
- [ ] System classes seeded
- [ ] Custom class creation works
- [ ] Inheritance works
- [ ] Schema migration works

---

#### Task 5.11: CMDB REST API
**Complexity**: L
**Description**: REST endpoints for CMDB operations.
**Files**:
- `backend/app/api/v1/endpoints/cmdb/ci.py` - CI endpoints
- `backend/app/api/v1/endpoints/cmdb/compartment.py` - Compartment endpoints
- `backend/app/api/v1/endpoints/cmdb/relationship.py` - Relationship endpoints
- `backend/app/api/v1/endpoints/cmdb/class.py` - Class endpoints
- `backend/app/api/v1/endpoints/cmdb/template.py` - Template endpoints
- `backend/app/api/v1/endpoints/cmdb/search.py` - Search endpoints
**Acceptance Criteria**:
- [ ] CI: GET, POST, PATCH, DELETE /api/v1/cmdb/cis
- [ ] CI versions: GET /api/v1/cmdb/cis/{id}/versions
- [ ] Compartments: full CRUD
- [ ] Relationships: GET, POST, DELETE /api/v1/cmdb/relationships
- [ ] Classes: GET, POST (custom), PATCH (custom), DELETE (custom)
- [ ] Templates: full CRUD, POST .../instantiate
- [ ] Search: POST /api/v1/cmdb/search
- [ ] Graph: GET /api/v1/cmdb/cis/{id}/graph (relationships)
- [ ] Impact: GET /api/v1/cmdb/cis/{id}/impact
- [ ] Permission checks on all endpoints
**Tests**:
- [ ] All CRUD operations work
- [ ] Search returns results
- [ ] Graph endpoints work

---

#### Task 5.12: Service Catalog REST API
**Complexity**: M
**Description**: REST endpoints for service catalog.
**Files**:
- `backend/app/api/v1/endpoints/catalog/service.py` - Service offerings
- `backend/app/api/v1/endpoints/catalog/pricing.py` - Pricing endpoints
**Acceptance Criteria**:
- [ ] ServiceOfferings: full CRUD
- [ ] PriceLists: full CRUD
- [ ] PriceListItems: full CRUD
- [ ] TenantPriceOverrides: full CRUD
- [ ] GET /api/v1/catalog/price?tenant_id&service_id - effective price
- [ ] GET /api/v1/catalog/services?category - list by category
- [ ] Permission checks (provider manages catalog, tenants view)
**Tests**:
- [ ] CRUD operations work
- [ ] Price calculation endpoint works

---

#### Task 5.13: CMDB GraphQL API
**Complexity**: L
**Description**: GraphQL schema for CMDB.
**Files**:
- `backend/app/api/graphql/types/cmdb.py` - CMDB types
- `backend/app/api/graphql/queries/cmdb.py` - CMDB queries
- `backend/app/api/graphql/mutations/cmdb.py` - CMDB mutations
**Acceptance Criteria**:
- [ ] Query: ci(id), cis(filter), ciVersions(ciId), ciAtTime(ciId, timestamp)
- [ ] Query: compartment(id), compartments(parentId), compartmentTree
- [ ] Query: ciClass(id), ciClasses, ciTemplates
- [ ] Query: searchCIs(query), ciGraph(ciId, depth), ciImpact(ciId)
- [ ] Query: serviceOfferings, priceList, effectivePrice(tenantId, serviceId)
- [ ] Mutation: createCI, updateCI, deleteCI, moveCI
- [ ] Mutation: createRelationship, deleteRelationship
- [ ] Mutation: createCompartment, updateCompartment, deleteCompartment
- [ ] CI type includes: relationships, compartment, versions, class
**Tests**:
- [ ] Queries return correct data
- [ ] Mutations work
- [ ] Nested queries resolve

---

### Frontend Tasks

#### Task 5.14: CMDB Service (Frontend)
**Complexity**: M
**Description**: Angular service for CMDB operations.
**Files**:
- `frontend/src/app/core/services/cmdb.service.ts` - CMDB API service
- `frontend/src/app/core/services/catalog.service.ts` - Service catalog service
- `frontend/src/app/core/models/cmdb.model.ts` - CMDB types
**Acceptance Criteria**:
- [ ] CI CRUD methods
- [ ] Relationship methods
- [ ] Compartment methods
- [ ] Search methods
- [ ] Graph query methods
- [ ] Version retrieval methods
- [ ] Template methods
- [ ] Service catalog methods
**Tests**:
- [ ] Service methods work correctly

---

#### Task 5.15: CI List View
**Complexity**: M
**Description**: List view for browsing CIs.
**Files**:
- `frontend/src/app/features/cmdb/ci-list/ci-list.component.ts`
- `frontend/src/app/features/cmdb/ci-list/ci-filter-panel.component.ts`
- `frontend/src/app/features/cmdb/ci-list/ci-table.component.ts`
**Acceptance Criteria**:
- [ ] Filter panel: class, compartment, state, tags
- [ ] Search box with full-text search
- [ ] Results table: name, class, compartment, state, updated
- [ ] Class icon display
- [ ] Quick actions: view, edit, delete
- [ ] Compartment breadcrumb navigation
- [ ] Pagination
- [ ] Column customization
- [ ] Saved searches dropdown
**Tests**:
- [ ] Filters work
- [ ] Search returns results
- [ ] Table displays correctly

---

#### Task 5.16: CI Detail View
**Complexity**: L
**Description**: Detailed view of a single CI.
**Files**:
- `frontend/src/app/features/cmdb/ci-detail/ci-detail.component.ts`
- `frontend/src/app/features/cmdb/ci-detail/ci-attributes.component.ts`
- `frontend/src/app/features/cmdb/ci-detail/ci-relationships.component.ts`
- `frontend/src/app/features/cmdb/ci-detail/ci-history.component.ts`
**Acceptance Criteria**:
- [ ] Header: name, class, state badge, actions
- [ ] Tabs: Attributes, Relationships, History, Audit
- [ ] Attributes tab: all attributes with types, edit inline
- [ ] Tags display and editing
- [ ] Relationships tab: grouped by type, links to related CIs
- [ ] History tab: version list, diff viewer, point-in-time view
- [ ] Audit tab: filtered audit log for this CI
- [ ] Lifecycle state change with confirmation
- [ ] Link references section
**Tests**:
- [ ] Detail loads correctly
- [ ] Tabs work
- [ ] Edit saves correctly

---

#### Task 5.17: CI Form (Create/Edit)
**Complexity**: M
**Description**: Form for creating and editing CIs.
**Files**:
- `frontend/src/app/features/cmdb/ci-form/ci-form.component.ts`
- `frontend/src/app/features/cmdb/ci-form/attribute-field.component.ts`
- `frontend/src/app/features/cmdb/ci-form/relationship-picker.component.ts`
**Acceptance Criteria**:
- [ ] Class selector (create mode)
- [ ] Dynamic form based on CI class schema
- [ ] Attribute fields by type (text, number, date, select, etc.)
- [ ] Validation messages
- [ ] Compartment selector
- [ ] Tags editor
- [ ] Relationship picker: add relationships during create/edit
- [ ] Template selector (create from template)
- [ ] Save and continue editing option
**Tests**:
- [ ] Form generates from schema
- [ ] Validation works
- [ ] Save creates/updates CI

---

#### Task 5.18: Compartment Tree View
**Complexity**: M
**Description**: Tree view for compartment hierarchy.
**Files**:
- `frontend/src/app/features/cmdb/compartment-tree/compartment-tree.component.ts`
- `frontend/src/app/features/cmdb/compartment-tree/compartment-node.component.ts`
**Acceptance Criteria**:
- [ ] Hierarchical tree with expand/collapse
- [ ] CI count per compartment
- [ ] Click to filter CI list by compartment
- [ ] Context menu: create child, edit, delete
- [ ] Drag-and-drop to move compartments
- [ ] Search/filter compartments
- [ ] Create compartment dialog
- [ ] Visual indicator for cloud-synced compartments
**Tests**:
- [ ] Tree renders correctly
- [ ] Navigation works
- [ ] CRUD operations work

---

#### Task 5.19: Relationship Graph Visualization
**Complexity**: L
**Description**: Visual graph of CI relationships.
**Files**:
- `frontend/src/app/features/cmdb/graph-view/graph-view.component.ts`
- `frontend/src/app/features/cmdb/graph-view/graph-node.component.ts`
- `frontend/src/app/features/cmdb/graph-view/graph-edge.component.ts`
- `frontend/src/app/features/cmdb/graph-view/graph-controls.component.ts`
**Acceptance Criteria**:
- [ ] Force-directed graph layout
- [ ] Nodes represent CIs with class icons
- [ ] Edges represent relationships with type labels
- [ ] Click node to select, double-click to navigate
- [ ] Hover for CI summary tooltip
- [ ] Zoom and pan controls
- [ ] Depth control (how many hops to show)
- [ ] Filter by relationship type
- [ ] Highlight impact path
- [ ] Export graph as image
- [ ] Layout options (hierarchical, circular, force)
**Tests**:
- [ ] Graph renders correctly
- [ ] Interactions work
- [ ] Filtering works

---

#### Task 5.20: Impact Analysis View
**Complexity**: M
**Description**: UI for impact and dependency analysis.
**Files**:
- `frontend/src/app/features/cmdb/impact/impact-analysis.component.ts`
- `frontend/src/app/features/cmdb/impact/dependency-chain.component.ts`
**Acceptance Criteria**:
- [ ] Select CI for analysis
- [ ] Show downstream impact (what depends on this)
- [ ] Show upstream dependencies (what this depends on)
- [ ] Severity indicators based on CI class/state
- [ ] List view and graph view toggle
- [ ] Filter by relationship type
- [ ] Export impact report
- [ ] "What-if" scenario: simulate CI failure
**Tests**:
- [ ] Impact analysis loads
- [ ] Dependencies shown correctly
- [ ] Graph view works

---

#### Task 5.21: CI Template Management
**Complexity**: M
**Description**: UI for managing CI templates.
**Files**:
- `frontend/src/app/features/cmdb/templates/template-list.component.ts`
- `frontend/src/app/features/cmdb/templates/template-editor.component.ts`
- `frontend/src/app/features/cmdb/templates/template-preview.component.ts`
**Acceptance Criteria**:
- [ ] Template list by class
- [ ] Template editor: attributes, relationships, constraints
- [ ] Constraint builder for required relationships
- [ ] Preview generated CI
- [ ] Instantiate template dialog
- [ ] Clone template
- [ ] Template versioning display
**Tests**:
- [ ] Templates list correctly
- [ ] Editor saves correctly
- [ ] Instantiation works

---

#### Task 5.22: CI Class Browser
**Complexity**: M
**Description**: UI for browsing and managing CI classes.
**Files**:
- `frontend/src/app/features/cmdb/classes/class-browser.component.ts`
- `frontend/src/app/features/cmdb/classes/class-detail.component.ts`
- `frontend/src/app/features/cmdb/classes/class-editor.component.ts`
**Acceptance Criteria**:
- [ ] Class hierarchy tree view
- [ ] Class detail: schema, attributes, relationships
- [ ] Custom class creator (tenant classes)
- [ ] Schema editor: add/edit attributes
- [ ] Inherit from system class option
- [ ] View CIs of this class
- [ ] Cannot edit system classes (view only)
**Tests**:
- [ ] Classes display correctly
- [ ] Custom class creation works
- [ ] Schema editing works

---

#### Task 5.23: Service Catalog UI
**Complexity**: M
**Description**: UI for service catalog and pricing.
**Files**:
- `frontend/src/app/features/catalog/service-list.component.ts`
- `frontend/src/app/features/catalog/service-form.component.ts`
- `frontend/src/app/features/catalog/pricing-config.component.ts`
- `frontend/src/app/features/catalog/tenant-pricing.component.ts`
**Acceptance Criteria**:
- [ ] Service offering list by category
- [ ] Service detail: description, measuring unit, linked CI class
- [ ] Service form for create/edit (provider only)
- [ ] Price list management
- [ ] Price list item editor
- [ ] Tenant price override configuration
- [ ] Price calculator: select service, quantity, see price
- [ ] Effective price display per tenant
**Tests**:
- [ ] Service list displays
- [ ] Pricing configuration works
- [ ] Price calculation correct

---

#### Task 5.24: CMDB Dashboard
**Complexity**: M
**Description**: CMDB overview dashboard.
**Files**:
- `frontend/src/app/features/cmdb/dashboard/cmdb-dashboard.component.ts`
- `frontend/src/app/features/cmdb/dashboard/ci-stats.component.ts`
- `frontend/src/app/features/cmdb/dashboard/recent-changes.component.ts`
**Acceptance Criteria**:
- [ ] CI count by class (chart)
- [ ] CI count by state
- [ ] CI count by compartment
- [ ] Recent changes list
- [ ] Quick search
- [ ] Quick actions: create CI, create compartment
- [ ] Health indicators (planned vs active ratio)
- [ ] Service catalog summary
**Tests**:
- [ ] Dashboard loads with stats
- [ ] Charts render correctly
- [ ] Links navigate correctly

---

## Phase Completion Checklist

- [ ] All 24 tasks completed
- [ ] File headers follow documentation standards
- [ ] Function indices updated via script
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] CMDB functionality verified:
  - [ ] CI CRUD with all classes
  - [ ] Relationship graph works
  - [ ] Versioning captures changes
  - [ ] Search finds CIs correctly
  - [ ] Impact analysis works
  - [ ] Templates instantiate correctly
  - [ ] Service catalog pricing works
- [ ] UI tested end-to-end:
  - [ ] List/detail/form views work
  - [ ] Compartment tree navigates
  - [ ] Graph visualization renders
  - [ ] Impact analysis displays
  - [ ] Templates create CIs

## Dependencies for Next Phase
Phase 6 (Semantic Layer) will build on:
- CI class hierarchy (mapping to semantic concepts)
- Relationship graph (semantic relationships)
- Service catalog (semantic service mapping)

## Notes & Learnings
[To be filled during implementation]
