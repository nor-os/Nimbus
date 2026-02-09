# Phase 6: Visual Workflow Editor

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Visual, node-based workflow editor using Rete.js. Lets any permitted user design custom automation workflows as full directed acyclic graphs with loops, parallel execution, conditional branching, and human-in-the-loop gates. Workflows compile to Temporal workflow definitions and execute via a generic dynamic executor. Establishes the Rete.js canvas foundation that Phase 7 (Visual Architecture Planner) reuses for infrastructure topology.

## Deliverables
- Rete.js 2 integration in Angular with custom node rendering
- Workflow definition data model (graph-as-JSONB, versioned)
- Extensible node type registry (control flow, actions, integrations)
- Expression engine for conditions, transforms, variable access
- Graph validator (structure, types, reachability, loop safety)
- Workflow compiler (graph → execution plan)
- Dynamic Temporal workflow executor (interprets execution plan at runtime)
- Built-in node types:
  - **Control Flow**: Start, End, Condition (if/else), Switch, Loop (for-each/while), Parallel (fan-out), Merge (fan-in), Delay, Sub-Workflow
  - **Actions**: Approval Gate, Notification, HTTP/Webhook, Script (sandboxed expression), Log/Audit
  - **Data**: Variable Set, Variable Get, Transform
- Workflow definition management (CRUD, versioning, draft → active → archived)
- Workflow execution service (start, cancel, query, retry)
- GraphQL API for definitions and executions
- Frontend: canvas editor, node palette, properties panel, execution monitor, dry-run testing
- Permissions: `workflow:definition:*`, `workflow:execution:*`

## Not Included (Available as Node Types When Their Phases Complete)
- Pulumi Deploy node (requires Phase 12)
- Drift Scan / Remediate nodes (requires Phase 17)
- Cost Check node (requires Phase 19)
- Live execution updates via WebSocket (requires Phase 13 Valkey + Socket.IO; polling until then)

## Dependencies
- Phase 10 complete (ApprovalChainWorkflow for approval gate node)
- Phase 9 complete (notification service for notification node)
- Phase 4 complete (audit logging for all workflow operations)
- Phase 1 Temporal setup (worker, client)

---

## Refinement Questions & Decisions

### Q1: Execution Model
**Question**: How should visual graphs be executed — interpret at runtime or generate Temporal workflow code?
**Decision**: Interpreter pattern (dynamic executor)
**Rationale**: A single generic `DynamicWorkflowExecutor` Temporal workflow reads the graph and calls node-type activities. Simpler than code generation, no compilation step, supports hot-reload of definitions. Performance is adequate since the bottleneck is the nodes themselves (HTTP calls, approvals), not the orchestration overhead.

### Q2: Expression Language
**Question**: What expression language for conditions and transforms?
**Decision**: Safe subset of Python-like expressions (no imports, no I/O, no exec)
**Rationale**: Familiar syntax for operators. Use a restricted evaluator (AST-based, allowlisted operators/functions). Built-in functions for string ops, math, date/time, comparisons, JSON path access. Variables accessed as `$variable_name` or `$nodes.node_id.output.field`.

### Q3: Loop Safety
**Question**: How to prevent infinite loops?
**Decision**: Configurable iteration limit + timeout
**Rationale**: Loop nodes have a `max_iterations` config (default 1000). The dynamic executor enforces this plus an overall workflow timeout (from definition). Temporal's built-in workflow timeout provides a final safety net.

### Q4: Variable Scoping
**Question**: How do variables flow between nodes?
**Decision**: Workflow-level variable store + node output references
**Rationale**: Each node produces typed output accessible via `$nodes.<node_id>.output`. A workflow-level variable store allows Set/Get nodes. Loop nodes expose `$loop.index`, `$loop.item`. Condition nodes expose which branch was taken. Sub-workflows have isolated scope with explicit input/output mapping.

### Q5: Sandboxed Script Node
**Question**: How much scripting power should the Script node have?
**Decision**: Expression-only (no arbitrary Python execution)
**Rationale**: Script nodes evaluate expressions using the same engine as conditions. They can transform data, compute values, and format strings — but cannot import modules, make network calls, or access the filesystem. For side effects, use dedicated node types (HTTP, Notification, etc.).

### Q6: Graph Storage Format
**Question**: How to store the visual graph?
**Decision**: Single JSONB column with versioned schema
**Rationale**: The graph is stored as a JSONB blob in `WorkflowDefinition.graph` containing `{nodes: [...], edges: [...], variables: [...], metadata: {...}}`. Each node stores its type, config, position (x/y for canvas), and port definitions. This avoids join-heavy queries and keeps the graph atomic for versioning.

### Q7: Rete.js Version
**Question**: Rete.js v1 or v2?
**Decision**: Rete.js v2 with Angular render plugin
**Rationale**: v2 is the current maintained version with better TypeScript support, plugin architecture, and Angular-specific rendering. Uses `rete-angular-plugin` for custom node components.

---

## Graph Schema

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "node_abc123",
      "type": "condition",
      "label": "Check cost threshold",
      "position": { "x": 400, "y": 200 },
      "config": {
        "expression": "$nodes.get_cost.output.total > 1000"
      },
      "ports": {
        "inputs": [{ "id": "in", "type": "flow" }],
        "outputs": [
          { "id": "true", "type": "flow", "label": "Yes" },
          { "id": "false", "type": "flow", "label": "No" }
        ]
      }
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source_node": "node_start",
      "source_port": "out",
      "target_node": "node_abc123",
      "target_port": "in"
    }
  ],
  "variables": [
    { "name": "request_id", "type": "string", "default": "" },
    { "name": "approved", "type": "boolean", "default": false }
  ],
  "metadata": {
    "canvas_zoom": 1.0,
    "canvas_offset": { "x": 0, "y": 0 }
  }
}
```

---

## Node Type Registry Schema

```python
@dataclass
class NodeTypeDefinition:
    type_id: str                    # e.g., "condition", "approval_gate"
    category: str                   # "control_flow", "actions", "integrations", "data"
    display_name: str               # "Condition (If/Else)"
    description: str
    icon: str                       # Icon identifier for frontend
    input_ports: list[PortDef]      # [{"id": "in", "type": "flow", "required": True}]
    output_ports: list[PortDef]     # [{"id": "true", "type": "flow"}, {"id": "false", "type": "flow"}]
    config_schema: dict             # JSON Schema for node configuration
    executor_class: str             # Fully qualified class name for activity execution
    supports_retry: bool = True
    max_timeout_seconds: int = 3600
```

---

## Tasks

### Backend Tasks

#### Task 6.1: Workflow Data Models & Migration
**Complexity**: L
**Description**: Create database models for workflow definitions and executions, plus Alembic migration.
**Files**:
- `backend/app/models/workflow_definition.py` — WorkflowDefinition model
- `backend/app/models/workflow_execution.py` — WorkflowExecution + WorkflowNodeExecution models
- `backend/app/schemas/workflow.py` — Pydantic schemas
- `backend/alembic/versions/006_workflow_editor.py` — Migration
- `backend/app/models/__init__.py` — Register models
**Acceptance Criteria**:
- [ ] `WorkflowDefinition`: id, tenant_id, name, description, version (int), graph (JSONB), status (draft/active/archived), created_by, created_at, updated_at, is_deleted
- [ ] `WorkflowExecution`: id, definition_id, definition_version, tenant_id, temporal_workflow_id, status (pending/running/completed/failed/cancelled), input (JSONB), output (JSONB), error (text), started_by, started_at, completed_at
- [ ] `WorkflowNodeExecution`: id, execution_id, node_id (from graph), node_type, status, input (JSONB), output (JSONB), error (text), started_at, completed_at, attempt (int)
- [ ] Indexes: tenant_id, status, created_by, name (unique per tenant+active version)
- [ ] Soft delete on WorkflowDefinition
- [ ] Version increment on publish (draft versions don't increment)
**Tests**:
- [ ] Models create correctly
- [ ] Indexes exist
- [ ] Version constraints enforced
- [ ] Soft delete works

---

#### Task 6.2: Node Type Registry
**Complexity**: M
**Description**: Extensible registry for node type definitions. Other phases register new node types.
**Files**:
- `backend/app/services/workflow/node_registry.py` — Registry singleton
- `backend/app/services/workflow/node_types/__init__.py` — Package init
- `backend/app/services/workflow/node_types/base.py` — Base node executor class
**Acceptance Criteria**:
- [ ] `NodeTypeRegistry.register(definition: NodeTypeDefinition)` — register a node type
- [ ] `NodeTypeRegistry.get(type_id: str)` — get definition by type ID
- [ ] `NodeTypeRegistry.list_all()` — all registered types
- [ ] `NodeTypeRegistry.list_by_category(category: str)` — filter by category
- [ ] `BaseNodeExecutor` abstract class with `execute(config, inputs, context) -> NodeOutput`
- [ ] Config schema validation via JSON Schema on registration
- [ ] Duplicate type_id prevention
- [ ] Auto-discovery of node types on startup
**Tests**:
- [ ] Registration works
- [ ] Duplicate detection
- [ ] Lookup by type and category
- [ ] Invalid config schema rejected

---

#### Task 6.3: Built-in Control Flow Nodes
**Complexity**: L
**Description**: Implement core control flow node types.
**Files**:
- `backend/app/services/workflow/node_types/start_end.py` — Start, End nodes
- `backend/app/services/workflow/node_types/condition.py` — Condition (if/else), Switch
- `backend/app/services/workflow/node_types/loop.py` — For-Each, While loop
- `backend/app/services/workflow/node_types/parallel.py` — Parallel (fan-out), Merge (fan-in)
- `backend/app/services/workflow/node_types/delay.py` — Delay/timer node
- `backend/app/services/workflow/node_types/subworkflow.py` — Sub-workflow invocation
**Acceptance Criteria**:
- [ ] **Start node**: single output port, no config, injects workflow input variables
- [ ] **End node**: single input port, captures workflow output
- [ ] **Condition node**: expression config, evaluates to true/false, routes to respective output port
- [ ] **Switch node**: expression + case list config, routes to matching case output or default
- [ ] **For-Each Loop node**: collection expression, body output port, done output port, exposes `$loop.index` and `$loop.item`, `max_iterations` config
- [ ] **While Loop node**: condition expression, body output port, done output port, `max_iterations` config
- [ ] **Parallel node**: N output ports (configurable), fans out to all simultaneously
- [ ] **Merge node**: N input ports, waits for all (AND) or any (OR) based on config
- [ ] **Delay node**: duration config (seconds/expression), pauses execution
- [ ] **Sub-Workflow node**: definition_id config, input mapping, output mapping, isolated scope
**Tests**:
- [ ] Condition routes correctly for true/false
- [ ] Switch routes to correct case and default
- [ ] For-Each iterates collection, respects max_iterations
- [ ] While loops until condition false, respects max_iterations
- [ ] Parallel fans out, Merge waits for correct inputs
- [ ] Delay pauses for correct duration
- [ ] Sub-Workflow executes and returns output

---

#### Task 6.4: Built-in Action & Data Nodes
**Complexity**: L
**Description**: Implement action and data manipulation node types.
**Files**:
- `backend/app/services/workflow/node_types/approval_gate.py` — Approval gate
- `backend/app/services/workflow/node_types/notification.py` — Send notification
- `backend/app/services/workflow/node_types/http_request.py` — HTTP/Webhook call
- `backend/app/services/workflow/node_types/script.py` — Sandboxed expression script
- `backend/app/services/workflow/node_types/audit_log.py` — Create audit entry
- `backend/app/services/workflow/node_types/variables.py` — Variable Set, Variable Get, Transform
**Acceptance Criteria**:
- [ ] **Approval Gate**: creates ApprovalChainWorkflow (Phase 10), blocks until approved/rejected, outputs decision + reason
- [ ] **Notification**: sends via NotificationService (Phase 9), configurable channel/template/recipients
- [ ] **HTTP Request**: method, URL, headers, body (all support expressions), timeout, response parsing, error handling
- [ ] **Script**: expression evaluation, access to all workflow variables, produces typed output
- [ ] **Audit Log**: create custom audit entry with configurable event_type, priority, details
- [ ] **Variable Set**: assigns expression result to named workflow variable
- [ ] **Variable Get**: reads workflow variable to output port (shortcut for expression)
- [ ] **Transform**: applies expression to input, produces transformed output (map/filter/format)
- [ ] All action nodes support retry configuration (max_attempts, backoff)
**Tests**:
- [ ] Approval gate starts sub-workflow and receives decision signal
- [ ] Notification sends via correct channel
- [ ] HTTP request makes call, handles response and errors
- [ ] Script evaluates expressions safely, rejects unsafe operations
- [ ] Variables set/get correctly across nodes
- [ ] Transform produces expected output

---

#### Task 6.5: Expression Engine
**Complexity**: M
**Description**: Safe expression evaluator for conditions, transforms, and variable access.
**Files**:
- `backend/app/services/workflow/expression_engine.py` — Expression parser and evaluator
- `backend/app/services/workflow/expression_functions.py` — Built-in function library
**Acceptance Criteria**:
- [ ] Parse expressions like `$nodes.get_cost.output.total > 1000 && $vars.region == "us-east"`
- [ ] Variable resolution: `$vars.<name>`, `$nodes.<id>.output.<path>`, `$loop.index`, `$loop.item`, `$input.<path>`
- [ ] Operators: `==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`, `!`, `+`, `-`, `*`, `/`, `%`
- [ ] Built-in functions: `len()`, `contains()`, `startsWith()`, `endsWith()`, `lower()`, `upper()`, `trim()`, `now()`, `formatDate()`, `parseInt()`, `parseFloat()`, `jsonPath()`, `coalesce()`, `typeOf()`
- [ ] String interpolation: `"Hello, ${$vars.name}!"`
- [ ] AST-based evaluation — no `eval()`, no `exec()`, no imports
- [ ] Allowlisted operations only — reject anything not explicitly supported
- [ ] Expression validation without execution (for editor feedback)
- [ ] Type inference for editor autocomplete hints
- [ ] Maximum expression complexity limit (AST depth)
**Tests**:
- [ ] All operators evaluate correctly
- [ ] Variable resolution works for all reference types
- [ ] Built-in functions return correct results
- [ ] Unsafe expressions rejected (import, exec, file access, etc.)
- [ ] Complex nested expressions work
- [ ] String interpolation works
- [ ] Validation catches syntax errors

---

#### Task 6.6: Graph Validator
**Complexity**: M
**Description**: Validate workflow graph structure and semantics before publishing or executing.
**Files**:
- `backend/app/services/workflow/graph_validator.py` — Graph validation logic
**Acceptance Criteria**:
- [ ] Exactly one Start node, at least one End node
- [ ] All nodes reachable from Start
- [ ] All paths can reach an End node (no dead ends except inside loops)
- [ ] Port type compatibility: flow ports connect to flow ports, data ports match types
- [ ] No unconnected required input ports
- [ ] Loop nodes must have body path that returns to loop input
- [ ] No cycles outside of explicit Loop nodes
- [ ] All node configs valid per their JSON Schema
- [ ] All expressions parse and validate (syntax, variable references)
- [ ] Sub-workflow references exist and are active
- [ ] Parallel/Merge nodes are balanced (every Parallel has a corresponding Merge)
- [ ] Returns structured validation result: `{valid: bool, errors: [{node_id, port_id, message, severity}]}`
**Tests**:
- [ ] Valid graph passes
- [ ] Missing Start/End detected
- [ ] Unreachable nodes detected
- [ ] Dead-end paths detected
- [ ] Type mismatches detected
- [ ] Illegal cycles detected
- [ ] Valid loops pass
- [ ] Unbalanced parallel/merge detected
- [ ] Invalid expressions caught

---

#### Task 6.7: Workflow Compiler
**Complexity**: L
**Description**: Compile validated graph into an execution plan for the dynamic executor.
**Files**:
- `backend/app/services/workflow/compiler.py` — Graph → ExecutionPlan compiler
- `backend/app/services/workflow/execution_plan.py` — ExecutionPlan data structures
**Acceptance Criteria**:
- [ ] `ExecutionPlan` structure: ordered steps, each with node reference, dependencies, parallel group
- [ ] Topological sort of nodes respecting edge dependencies
- [ ] Parallel group detection: nodes between Parallel/Merge become a parallel group
- [ ] Loop compilation: Loop body becomes a repeatable sub-plan
- [ ] Condition/Switch compilation: branches become conditional sub-plans
- [ ] Sub-workflow compilation: reference to another definition's plan
- [ ] Variable scope tracking: which variables are available at each step
- [ ] Plan serialization (JSON) for Temporal workflow input
- [ ] Plan caching: same definition version → same plan (cache by definition_id + version)
**Tests**:
- [ ] Linear graph produces sequential plan
- [ ] Parallel group correctly identified
- [ ] Loop body correctly extracted as sub-plan
- [ ] Conditional branches correctly extracted
- [ ] Complex graph (mixed parallel + conditions + loops) compiles correctly
- [ ] Plan is deterministic for same input

---

#### Task 6.8: Dynamic Workflow Executor (Temporal)
**Complexity**: L
**Description**: Generic Temporal workflow that executes any compiled workflow definition.
**Files**:
- `backend/app/workflows/dynamic_workflow.py` — DynamicWorkflowExecutor workflow
- `backend/app/workflows/activities/workflow_nodes.py` — Node execution activities
**Acceptance Criteria**:
- [ ] `DynamicWorkflowExecutor` Temporal workflow: accepts definition_id, version, input variables
- [ ] Loads execution plan and traverses steps in order
- [ ] Sequential steps execute one-by-one
- [ ] Parallel groups execute concurrently (Temporal async activities)
- [ ] Condition/Switch evaluation routes to correct branch
- [ ] Loop execution with iteration counter and max_iterations enforcement
- [ ] Workflow-level variable store passed between activities
- [ ] `execute_node` activity: dispatches to correct node executor based on type
- [ ] Node output stored in execution context (accessible by downstream nodes)
- [ ] Temporal Signals: `pause`, `resume`, `cancel`, `inject_variable`
- [ ] Temporal Queries: `get_status` (overall + per-node), `get_variables`
- [ ] Error handling per node: retry (configurable), skip (if node marked optional), fail workflow
- [ ] `WorkflowNodeExecution` records updated as each node starts/completes/fails
- [ ] Overall workflow timeout from definition config
- [ ] Heartbeat from long-running activities
**Tests**:
- [ ] Simple linear workflow executes correctly
- [ ] Parallel branches execute concurrently
- [ ] Condition routes correctly
- [ ] Loop iterates and terminates
- [ ] Max iterations enforced
- [ ] Node failure with retry works
- [ ] Node failure without retry fails workflow
- [ ] Cancel signal stops execution
- [ ] Status query returns accurate state
- [ ] Variable injection works mid-execution

---

#### Task 6.9: Workflow Definition Service
**Complexity**: M
**Description**: Business logic for managing workflow definitions.
**Files**:
- `backend/app/services/workflow/__init__.py`
- `backend/app/services/workflow/definition_service.py` — CRUD + versioning
**Acceptance Criteria**:
- [ ] `create_definition(tenant_id, name, description, graph)` → draft version 0
- [ ] `update_definition(id, graph)` — only drafts can be updated
- [ ] `publish_definition(id)` — validates graph, increments version, sets status=active, archives previous active version
- [ ] `archive_definition(id)` — sets status=archived, cannot be executed
- [ ] `get_definition(id, version?)` — get specific or latest active version
- [ ] `list_definitions(tenant_id, status?, search?)` — paginated list
- [ ] `clone_definition(id, new_name)` — deep copy as new draft
- [ ] `delete_definition(id)` — soft delete
- [ ] `export_definition(id)` → JSON with graph + metadata
- [ ] `import_definition(tenant_id, json)` → new draft from exported JSON
- [ ] Version history: list all versions of a definition with timestamps and changers
- [ ] Audit logging for all operations
**Tests**:
- [ ] CRUD operations work
- [ ] Version increments on publish
- [ ] Cannot update published definition
- [ ] Clone produces independent copy
- [ ] Export/import round-trips correctly
- [ ] Soft delete works

---

#### Task 6.10: Workflow Execution Service
**Complexity**: M
**Description**: Business logic for starting and managing workflow executions.
**Files**:
- `backend/app/services/workflow/execution_service.py` — Start, cancel, query
**Acceptance Criteria**:
- [ ] `start_execution(definition_id, input, started_by)` — validates definition is active, compiles plan, starts Temporal workflow, creates execution record
- [ ] `cancel_execution(execution_id)` — sends cancel signal to Temporal workflow
- [ ] `get_execution(execution_id)` — execution status + node statuses from DB
- [ ] `list_executions(tenant_id, definition_id?, status?, date_range?)` — paginated
- [ ] `retry_execution(execution_id)` — re-start failed execution with same input
- [ ] `get_node_execution(execution_id, node_id)` — detailed node execution (input/output/error)
- [ ] Execution status sync: Temporal workflow updates DB records via activities
- [ ] Concurrent execution limit per definition (configurable, default 10)
- [ ] Audit logging for start, cancel, retry
**Tests**:
- [ ] Start creates execution and Temporal workflow
- [ ] Cancel signals Temporal workflow
- [ ] Status reflects Temporal state
- [ ] Concurrent limit enforced
- [ ] Retry starts new execution

---

#### Task 6.11: GraphQL API
**Complexity**: L
**Description**: GraphQL types, queries, and mutations for workflow editor.
**Files**:
- `backend/app/api/graphql/types/workflow.py` — GraphQL types
- `backend/app/api/graphql/queries/workflow.py` — Queries
- `backend/app/api/graphql/mutations/workflow.py` — Mutations
- `backend/app/api/graphql/schema.py` — Register in schema
**Acceptance Criteria**:
- [ ] Types: `WorkflowDefinition`, `WorkflowGraph`, `WorkflowNode`, `WorkflowEdge`, `WorkflowVariable`, `WorkflowExecution`, `WorkflowNodeExecution`, `NodeTypeInfo`, `ValidationResult`
- [ ] Queries:
  - `workflowDefinitions(status, search, pagination)` — list definitions
  - `workflowDefinition(id, version?)` — single definition with graph
  - `workflowDefinitionVersions(id)` — version history
  - `workflowExecutions(definitionId?, status?, pagination)` — list executions
  - `workflowExecution(id)` — single execution with node statuses
  - `nodeTypes` — all registered node types with config schemas
  - `validateWorkflowGraph(graph)` — validate without saving
- [ ] Mutations:
  - `createWorkflowDefinition(input)` — create draft
  - `updateWorkflowDefinition(id, input)` — update draft graph/metadata
  - `publishWorkflowDefinition(id)` — validate and publish
  - `archiveWorkflowDefinition(id)` — archive
  - `cloneWorkflowDefinition(id, name)` — clone
  - `deleteWorkflowDefinition(id)` — soft delete
  - `startWorkflowExecution(definitionId, input)` — start execution
  - `cancelWorkflowExecution(id)` — cancel
  - `retryWorkflowExecution(id)` — retry failed
- [ ] Permission checks: `workflow:definition:*`, `workflow:execution:*`
- [ ] Tenant scoping on all operations
**Tests**:
- [ ] All queries return correct data
- [ ] All mutations work
- [ ] Permission checks enforced
- [ ] Tenant isolation verified

---

#### Task 6.12: Permissions & Migration
**Complexity**: M
**Description**: Permission keys, role assignments, and migration for workflow editor permissions.
**Files**:
- `backend/alembic/versions/006_workflow_editor.py` — Add to same migration as models
**Acceptance Criteria**:
- [ ] Permission keys:
  - `workflow:definition:create` — create new definitions
  - `workflow:definition:read` — view definitions and graphs
  - `workflow:definition:update` — edit draft definitions
  - `workflow:definition:delete` — soft delete definitions
  - `workflow:definition:publish` — publish drafts to active
  - `workflow:execution:start` — start workflow executions
  - `workflow:execution:read` — view execution status and history
  - `workflow:execution:cancel` — cancel running executions
- [ ] Role assignments:
  - `Provider Admin`: all workflow permissions
  - `Tenant Admin`: all workflow permissions
  - `User`: definition:read, execution:start, execution:read
  - `Read Only`: definition:read, execution:read
- [ ] Migration adds permissions and role_permissions using correct PascalCase role names
**Tests**:
- [ ] Permissions created in migration
- [ ] Role assignments correct

---

### Frontend Tasks

#### Task 6.13: Rete.js Angular Integration
**Complexity**: L
**Description**: Set up Rete.js v2 with Angular render plugin, custom node components, and canvas infrastructure.
**Files**:
- `frontend/src/app/features/workflows/editor/workflow-canvas.component.ts` — Main canvas wrapper
- `frontend/src/app/features/workflows/editor/rete/rete-editor.service.ts` — Rete.js editor service
- `frontend/src/app/features/workflows/editor/rete/custom-node.component.ts` — Base custom node Angular component
- `frontend/src/app/features/workflows/editor/rete/custom-connection.component.ts` — Custom edge component
- `frontend/src/app/features/workflows/editor/rete/custom-socket.component.ts` — Custom port component
**Acceptance Criteria**:
- [ ] Rete.js v2 editor with Angular render plugin (`rete-angular-plugin`)
- [ ] Canvas with zoom (scroll wheel), pan (click-drag on background), fit-to-view
- [ ] Minimap plugin showing full graph overview
- [ ] Custom node component rendering based on node type (icon, label, ports, status indicator)
- [ ] Connection drawing between ports (drag from output to input)
- [ ] Node selection (click), multi-select (shift-click or box-select)
- [ ] Keyboard shortcuts: Delete (remove selected), Ctrl+C/V (copy/paste), Ctrl+Z/Y (undo/redo)
- [ ] Canvas theming matching Taiga UI dark/light modes
- [ ] Responsive layout — canvas fills available space
- [ ] Graph serialization: canvas state ↔ graph JSONB (bidirectional)
**Tests**:
- [ ] Canvas renders and accepts interaction
- [ ] Nodes can be placed and connected
- [ ] Serialization round-trips correctly
- [ ] Keyboard shortcuts work

---

#### Task 6.14: Node Palette & Properties Panel
**Complexity**: M
**Description**: Left-side node library and right-side properties editor.
**Files**:
- `frontend/src/app/features/workflows/editor/node-palette/node-palette.component.ts` — Node library sidebar
- `frontend/src/app/features/workflows/editor/properties-panel/properties-panel.component.ts` — Dynamic properties editor
- `frontend/src/app/features/workflows/editor/properties-panel/expression-editor.component.ts` — Expression input with validation
- `frontend/src/app/features/workflows/editor/properties-panel/port-config.component.ts` — Port configuration
**Acceptance Criteria**:
- [ ] Node palette: categorized list (Control Flow, Actions, Integrations, Data)
- [ ] Search/filter in palette
- [ ] Drag from palette → drop onto canvas creates node
- [ ] Node icons and descriptions in palette
- [ ] Properties panel appears on node selection (right sidebar)
- [ ] Dynamic form generated from node type's config JSON Schema
- [ ] Expression editor: text input with syntax highlighting, variable autocomplete, inline validation
- [ ] Port labels editable for Parallel/Switch nodes
- [ ] Panel shows node type info (description, port types, help text)
- [ ] Panel hides when no node selected (shows workflow-level properties: name, description, variables)
**Tests**:
- [ ] All node types appear in palette
- [ ] Drag-and-drop creates node on canvas
- [ ] Properties form matches node type schema
- [ ] Expression validation shows errors inline

---

#### Task 6.15: Edge System & Client-Side Graph Validation
**Complexity**: M
**Description**: Connection rules, visual validation, and client-side graph checks.
**Files**:
- `frontend/src/app/features/workflows/editor/rete/connection-rules.ts` — Connection validation rules
- `frontend/src/app/features/workflows/editor/validation/graph-validator.service.ts` — Client-side graph validator
- `frontend/src/app/features/workflows/editor/validation/validation-overlay.component.ts` — Visual error overlay
**Acceptance Criteria**:
- [ ] Port type enforcement: flow→flow, data→data (matching types)
- [ ] Prevent self-connections (node to itself)
- [ ] Prevent duplicate connections (same source port → same target port)
- [ ] Visual feedback during drag: green highlight on valid target, red on invalid
- [ ] Connection snapping to nearest valid port
- [ ] Client-side graph validation mirrors backend (reachability, dead ends, type checks)
- [ ] Validation errors shown as:
  - Red border on invalid nodes
  - Error icon on nodes with config issues
  - Tooltip with error message on hover
  - Validation panel (bottom) listing all errors with click-to-navigate
- [ ] Validation runs on graph change (debounced) and before publish
**Tests**:
- [ ] Invalid connections rejected
- [ ] Visual feedback correct
- [ ] Validation errors displayed on correct nodes
- [ ] Click-to-navigate works

---

#### Task 6.16: Workflow Definition Management UI
**Complexity**: M
**Description**: List, create, version, and manage workflow definitions.
**Files**:
- `frontend/src/app/features/workflows/workflow-list/workflow-list.component.ts` — Definition list page
- `frontend/src/app/features/workflows/workflow-detail/workflow-detail.component.ts` — Definition detail (version history, metadata)
- `frontend/src/app/features/workflows/editor/workflow-editor.component.ts` — Full editor page (canvas + palette + properties)
- `frontend/src/app/core/services/workflow.service.ts` — GraphQL service
- `frontend/src/app/shared/models/workflow.model.ts` — TypeScript types
**Acceptance Criteria**:
- [ ] Workflow list: table with name, status (draft/active/archived), version, last modified, created by
- [ ] Status filter tabs: All, Draft, Active, Archived
- [ ] Search by name
- [ ] Create new workflow → opens editor with empty canvas
- [ ] Edit workflow → opens editor with loaded graph
- [ ] Publish button (validates first, shows errors if invalid)
- [ ] Archive/restore actions
- [ ] Clone action → creates new draft with "(Copy)" suffix
- [ ] Delete action with confirmation dialog
- [ ] Version history panel: list of versions with timestamps, click to view read-only
- [ ] Export/import JSON
- [ ] Breadcrumb: Workflows > [Name] > Editor
- [ ] Route: `/#/workflows`, `/#/workflows/:id`, `/#/workflows/:id/edit`
- [ ] Permission-gated: create/edit/publish/delete buttons visible based on permissions
**Tests**:
- [ ] List loads and filters
- [ ] CRUD operations work
- [ ] Version history displays
- [ ] Permissions hide/show actions

---

#### Task 6.17: Workflow Execution Monitor
**Complexity**: L
**Description**: View running and historical workflow executions with per-node status.
**Files**:
- `frontend/src/app/features/workflows/execution-list/execution-list.component.ts` — Execution list page
- `frontend/src/app/features/workflows/execution-detail/execution-detail.component.ts` — Execution detail with canvas overlay
- `frontend/src/app/features/workflows/execution-detail/node-execution-panel.component.ts` — Node execution detail sidebar
**Acceptance Criteria**:
- [ ] Execution list: table with definition name, status, started by, started at, duration
- [ ] Status filter (pending, running, completed, failed, cancelled)
- [ ] Definition filter (dropdown)
- [ ] Date range filter
- [ ] Execution detail: read-only canvas view with node status overlay
  - Pending nodes: gray
  - Running nodes: blue with pulse animation
  - Completed nodes: green
  - Failed nodes: red
  - Skipped nodes: yellow/dimmed
  - Cancelled nodes: gray strikethrough
- [ ] Click node → side panel shows: input, output, error, duration, attempt count
- [ ] Execution timeline bar showing progress through graph
- [ ] Cancel button for running executions
- [ ] Retry button for failed executions
- [ ] Auto-refresh (polling every 5s) for running executions
- [ ] Route: `/#/workflows/executions`, `/#/workflows/executions/:id`
**Tests**:
- [ ] List loads with filters
- [ ] Node status overlay renders correctly
- [ ] Node click shows execution details
- [ ] Cancel and retry work

---

#### Task 6.18: Workflow Testing & Dry Run
**Complexity**: M
**Description**: Test workflows in the editor before publishing, with mock capabilities.
**Files**:
- `frontend/src/app/features/workflows/editor/test-panel/test-panel.component.ts` — Test configuration panel
- `frontend/src/app/features/workflows/editor/test-panel/test-variables.component.ts` — Test input variables
- `frontend/src/app/features/workflows/editor/test-panel/mock-config.component.ts` — Node mock configuration
- `backend/app/services/workflow/test_runner.py` — Backend test execution service
**Acceptance Criteria**:
- [ ] "Test" button in editor toolbar opens test panel (bottom drawer)
- [ ] Test input variables form: define values for workflow input variables
- [ ] Mock configuration per node: skip, return fixed output, simulate delay, simulate failure
- [ ] Start test execution (runs actual Temporal workflow with `is_test=true` flag)
- [ ] Test execution shown on canvas with same status overlay as execution monitor
- [ ] Test executions marked in DB (not shown in production execution list by default)
- [ ] Step-through mode: set breakpoints on nodes, execution pauses at breakpoints
  - Continue, Step Over, Stop buttons
  - Variable inspector at breakpoint (shows current variable state)
  - Uses Temporal signals: `pause_at_node`, `continue_execution`
- [ ] Test results summary: pass/fail per node, total duration, variable final state
**Tests**:
- [ ] Test execution starts and completes
- [ ] Mocks applied correctly
- [ ] Breakpoints pause execution
- [ ] Step-through works

---

#### Task 6.19: Sidebar, Routes & Navigation
**Complexity**: S
**Description**: Add workflow editor to sidebar navigation and configure routes.
**Files**:
- `frontend/src/app/app.routes.ts` — Add routes
- `frontend/src/app/shared/components/sidebar/sidebar.component.ts` — Add nav item
**Acceptance Criteria**:
- [ ] Sidebar: "Workflows" nav item under Automation section, icon: `tuiIconGitBranch` or similar
- [ ] Permission-gated: visible when user has `workflow:definition:read`
- [ ] Routes:
  - `/#/workflows` — definition list
  - `/#/workflows/new` — new definition editor
  - `/#/workflows/:id` — definition detail (version history)
  - `/#/workflows/:id/edit` — definition editor
  - `/#/workflows/executions` — execution list
  - `/#/workflows/executions/:id` — execution detail
- [ ] Route guards: `workflow:definition:read` for list/detail, `workflow:definition:create` for new, `workflow:definition:update` for edit, `workflow:execution:read` for executions
- [ ] Breadcrumb integration
**Tests**:
- [ ] Navigation renders for permitted users
- [ ] Routes resolve correctly
- [ ] Guards redirect unauthorized users

---

#### Task 6.20: Integration Tests
**Complexity**: M
**Description**: End-to-end tests for workflow editor.
**Files**:
- `backend/tests/test_workflow_definition.py` — Definition CRUD tests
- `backend/tests/test_workflow_execution.py` — Execution lifecycle tests
- `backend/tests/test_workflow_compiler.py` — Compiler tests
- `backend/tests/test_expression_engine.py` — Expression evaluator tests
- `backend/tests/test_graph_validator.py` — Graph validation tests
**Acceptance Criteria**:
- [ ] Full lifecycle: create draft → edit graph → validate → publish → start execution → monitor → complete
- [ ] Complex graph execution: parallel branches + conditions + loops in single workflow
- [ ] Approval gate integration: workflow pauses at approval, resumes on decision
- [ ] Expression engine: comprehensive test suite covering all operators, functions, edge cases
- [ ] Graph validator: test suite with valid and invalid graph permutations
- [ ] Compiler: test suite with linear, parallel, conditional, loop, and mixed graphs
- [ ] Error scenarios: node failure with retry, max iterations, workflow timeout, cancel
- [ ] Permission enforcement: unauthorized users rejected
- [ ] Tenant isolation: definitions and executions scoped to tenant
**Tests**:
- [ ] All test suites pass
- [ ] Coverage adequate for critical paths

---

## Phase Completion Checklist

- [ ] All 20 tasks completed
- [ ] File headers follow documentation standards
- [ ] All backend tests pass (pytest)
- [ ] All frontend tests pass (Jest)
- [ ] Ruff linting passes
- [ ] ESLint + Prettier pass
- [ ] Workflow editor verified:
  - [ ] Canvas renders with drag-and-drop node creation
  - [ ] All built-in node types available in palette
  - [ ] Connections enforce type rules
  - [ ] Graph validation catches errors and displays inline
  - [ ] Publish validates before activating
  - [ ] Execution runs through Temporal correctly
  - [ ] Parallel, conditional, and loop execution works
  - [ ] Approval gate blocks and resumes on decision
  - [ ] Expression engine handles all supported operations
  - [ ] Execution monitor shows real-time node status
  - [ ] Test/dry-run mode works with mocks and breakpoints
- [ ] UI tested end-to-end:
  - [ ] Create → edit → publish → execute → monitor full lifecycle
  - [ ] Version management (multiple versions, view history)
  - [ ] Clone and import/export
  - [ ] Permission-gated actions work correctly

## Dependencies for Next Phase
Phase 7 (Visual Architecture Planner) will reuse:
- Rete.js canvas infrastructure (Task 6.13)
- Custom node rendering pattern
- Properties panel pattern
- Canvas serialization/deserialization

Future phases can extend the workflow editor with new node types:
- Phase 12 (Pulumi) → Deploy Stack, Destroy Stack node types
- Phase 17 (Drift) → Drift Scan, Drift Remediate node types
- Phase 19 (Cost) → Cost Check, Budget Alert node types

## Notes & Learnings
[To be filled during implementation]
