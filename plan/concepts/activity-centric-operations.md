# Activity-Centric Operations Model

## 1. Overview

This document describes the redesigned operations architecture for Nimbus. The core shift is from an **operation-centric** model (where components have fixed operations like deploy/decommission) to an **activity-centric** model where:

- **Activities** are the atomic units of work (code + configuration)
- **Workflows** are ordered sequences of activities
- **Components** receive independent copies (forks) of workflows and activities from a provider-level library

This model enables reusable activity authoring, per-component customization, explicit versioning, and a unified view of all activities across the system.

---

## 2. Activity Categories

Every activity belongs to exactly one category:

### 2.1 Deployment Activities

- **Purpose**: Infrastructure lifecycle operations executed via Python/Pulumi
- **Examples**: Deploy VM, configure networking, provision storage, decommission resources, upgrade infrastructure
- **Runtime**: Python scripts executed through the Pulumi Automation API
- **Authoring**: Monaco editor with Python language support, input/output schema definition
- **Versioning**: Each save creates a new immutable version

### 2.2 Day-2 Activities

- **Purpose**: Post-deployment operational tasks executed via Python/Pulumi
- **Examples**: Scale horizontally, rotate credentials, patch OS, take snapshot, restore backup
- **Runtime**: Same Python/Pulumi execution environment as deployment activities
- **Authoring**: Same Monaco editor experience
- **Versioning**: Same version model

### 2.3 Builtin Activities

- **Purpose**: Native Nimbus operations implemented directly in the platform (not user-authored Python)
- **Examples**: Send email notification, publish message to Kafka, invoke webhook, write audit log entry, wait for approval, evaluate condition
- **Runtime**: Executed natively by the Nimbus workflow engine (Temporal activities)
- **Authoring**: Not editable by users — configuration only (e.g., email recipient, Kafka topic, webhook URL)
- **Availability**: Always present in the workflow editor node palette; available for inclusion in any workflow
- **Not forked**: Builtin activities are system-provided and shared — they are not copied into components

---

## 3. Activity Library (Provider Level)

The **Activity Library** is the provider-level registry of all reusable activity definitions. It lives at `Provider > Workflows > Activities` in the sidebar.

### 3.1 Purpose

- Central place to **author, version, and manage** activity definitions
- Component-agnostic — library activities define generic behavior, not component-specific configuration
- Serves as the **source of truth** for forking into components

### 3.2 Contents

The library contains:

| Activity Kind | Category | Deletable | Description |
|---------------|----------|-----------|-------------|
| **Mandatory** | Deployment | No | `deploy`, `decommission`, `upgrade` — every component needs these. Always present in the library. |
| **Optional Deployment** | Deployment | Yes | Additional deployment-phase activities (e.g., `configure-dns`, `setup-monitoring`) |
| **Day-2** | Day-2 | Yes | Post-deployment operational activities |
| **Builtin** | Builtin | No | System-provided, read-only in the library. Shown for reference. |

### 3.3 Versioning

- Each activity in the library is **versioned** (v1, v2, v3, ...)
- Every save creates a new immutable version
- The library always shows the latest version
- Version history is browsable and diffable
- Components fork at a specific version and can be explicitly upgraded later

### 3.4 UI Experience

- Card/list view of all library activities, filterable by category (Deployment / Day-2 / Builtin)
- Each card shows: name, slug, category badge, current version, description
- Click to open full activity editor: Monaco code editor, input/output schema builder, version history, test runner
- Mandatory activities are visually marked and cannot be deleted

---

## 4. Workflow Templates (Provider Level)

**Workflow templates** define the default workflow structure that components receive on creation. They live at `Provider > Workflows > Templates` in the sidebar.

### 4.1 Structure

A workflow template is a directed graph of **activity references**. Each node in the graph references a library activity (by ID + version).

Standard workflow templates:

| Template | Type | Activities (default pipeline) |
|----------|------|-------------------------------|
| **Deploy** | Deployment | Validate > Dry Run > Deploy > Verify |
| **Decommission** | Deployment | Validate > Decommission > Cleanup |
| **Upgrade** | Deployment | Validate > Dry Run > Upgrade > Verify |

### 4.2 Key Concepts

- **Validate**, **Dry Run**, and **Rollback** are **activities within workflows**, not standalone workflows. They appear as nodes in the workflow graph.
- Templates can include branching, conditions, approval gates, and error-handling paths (using the visual workflow editor)
- Builtin activities (email, Kafka, webhook) can be added to templates as intermediate steps (e.g., "notify on deploy start")

### 4.3 Editing

- Full workflow editor experience (Rete.js canvas) for template editing
- Node palette shows all library activities + builtin activities
- Changes to templates affect only **new** components — existing components keep their forked copy

---

## 5. Component Fork Model

When a new component is created, Nimbus **forks** (creates full independent copies of) the workflow templates and their referenced activities into the component.

### 5.1 What Gets Forked

1. **All mandatory workflow templates** (deploy, decommission, upgrade) are copied
2. **All activities referenced by those workflows** are copied at their current library version
3. Each forked activity gets its own independent version history from that point forward

### 5.2 Fork Characteristics

- **Full independent copy**: The component's workflows and activities are completely decoupled from the library after forking
- **Editable**: Component owners can modify forked activities (change code, update schemas) without affecting the library or other components
- **Deletable** (non-mandatory only): Custom activities added to a component's workflows can be removed
- **Mandatory protection**: The three mandatory activities (deploy, decommission, upgrade) cannot be deleted from a component, though their code/configuration can be customized

### 5.3 Component Versioning

- **Every change to a component** (activity code edit, workflow graph change, configuration update) **bumps the component's version**
- This provides a full audit trail of what changed and when
- Component version is independent of individual activity versions

### 5.4 Upgrade from Library

Upgrading a forked activity to a newer library version is:

- **Manual / explicit** — never automatic
- **Replace operation** — the forked activity's code is replaced with the latest library version
- **One-way** — custom modifications in the fork are overwritten (user is warned)
- **Per-activity** — each activity is upgraded independently, not all-or-nothing
- **Version-aware** — UI shows current fork version vs. latest library version, highlighting available upgrades

---

## 6. Unified Activities View

A single view at `Workflows > Activities` (tenant-level sidebar) shows **all activities** across the system in one filterable list.

### 6.1 Activity Classifications in the Unified View

| Classification | Description | Editable | Source |
|----------------|-------------|----------|--------|
| **Definition Only** | System/mandatory activity definitions (deploy, decommission, upgrade from library) | At provider level | Activity Library |
| **Component Activity** | Forked copy living on a specific component | Yes, inline | Component fork |
| **Builtin** | Native Nimbus activities (email, Kafka, etc.) | Config only | System |

### 6.2 Filtering & Columns

- **Filter by**: Classification (Definition Only / Component / Builtin), Category (Deployment / Day-2 / Builtin), Component, Search text
- **Columns**: Name, Category badge, Classification badge, Component (if applicable), Version, Last modified
- Clicking a component activity navigates to the component editor with that activity open for inline editing
- Clicking a definition-only activity navigates to the provider-level library editor

---

## 7. Inline Activity Editing in Component Editor

When editing a component's forked activities, the editing experience happens **inline within the component editor**, not on a separate page.

### 7.1 Component Editor Operations Tab Structure

The Operations tab on the component editor shows 4 sections:

#### Section A: Deployment Workflows
- The 3 mandatory workflows (deploy, decommission, upgrade) as cards
- Each shows: name, status, activity pipeline preview
- "Customize Workflow" opens the visual workflow editor for that component's forked workflow
- "Reset to Default" replaces with latest library template

#### Section B: Deployment Activities
- Grid of deployment-category activities forked into this component
- Each card shows: name, slug, version, category badge
- "Edit" expands inline to show the full activity editor (Monaco code editor, input/output schemas, version history, test runner)
- "Upgrade Available" indicator when library has a newer version

#### Section C: Day-2 Workflows
- Custom day-2 workflows defined on this component
- Expandable cards with inline creation

#### Section D: Day-2 Activities
- Grid of day-2 activities forked into this component
- Same card pattern and inline editing as Section B
- "+ New Activity" to create component-specific day-2 activities

### 7.2 Inline Editor Experience

When "Edit" is clicked on an activity card:
- The card expands to reveal the full activity editor below it (or in a slide-out panel)
- **Code tab**: Monaco editor with the activity's Python/Pulumi code
- **Input Schema tab**: JSON schema builder for activity inputs
- **Output Schema tab**: JSON schema builder for activity outputs
- **Versions tab**: Version history with diff viewer
- **Test tab**: Execute the activity in test mode with sample inputs
- Save creates a new version of this component's forked activity and bumps the component version

---

## 8. Sidebar Navigation

### Provider Section
```
Infrastructure
  Landing Zones
  Components
  Resolvers

Workflows
  Templates          (workflow template editor)
  Activities          (activity library — author & manage)
```

### Tenant Section
```
Workflows
  Definitions         (workflow instances)
  Activities          (unified view — all activities)
  Executions
  Approvals
  Manage

Events
  Event Types
  Subscriptions
  Event Log
```

**Removed**: "Infrastructure > Component Activities" (absorbed into unified Activities view and component editor inline editing)
**Removed**: "Automation Catalog" (absorbed into unified Activities view)

---

## 9. Data Model Summary

### Activity (AutomatedActivity)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | Tenant isolation |
| `name` | String | Display name |
| `slug` | String | URL-safe identifier |
| `description` | String | Optional description |
| `activity_type` | Enum | `DEPLOYMENT`, `DAY2`, `BUILTIN` |
| `operation_kind` | String | e.g., `deploy`, `decommission`, `upgrade`, `scale`, `patch` |
| `component_id` | UUID (nullable) | If set, this is a forked component activity |
| `template_activity_id` | UUID (nullable) | Reference to the library activity this was forked from |
| `forked_at_version` | Integer (nullable) | Library version at time of fork |
| `is_mandatory` | Boolean | If true, cannot be deleted from components |
| `code` | Text | Python/Pulumi source code (null for builtin) |
| `input_schema` | JSONB | Input parameter schema |
| `output_schema` | JSONB | Output parameter schema |
| `version` | Integer | Current version number |
| `status` | Enum | `DRAFT`, `ACTIVE`, `ARCHIVED` |

### Workflow Definition (WorkflowDefinition)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | Tenant isolation |
| `name` | String | Display name |
| `workflow_type` | Enum | `DEPLOYMENT`, `SYSTEM`, `AUTOMATION` |
| `is_template` | Boolean | True for provider-level templates |
| `template_source_id` | UUID (nullable) | Library template this was forked from |
| `component_id` | UUID (nullable) | If set, this workflow belongs to a specific component |
| `graph` | JSONB | Workflow graph (nodes + connections) |
| `version` | Integer | Current version |
| `status` | Enum | `DRAFT`, `ACTIVE`, `ARCHIVED` |

### Component Version Tracking

Each component tracks a `version` integer that increments on any change:
- Activity code edit
- Activity schema change
- Workflow graph modification
- Configuration update

---

## 10. Lifecycle Flows

### 10.1 New Component Creation

```
1. User creates component (name, type, landing zone)
2. System forks mandatory workflow templates (deploy, decommission, upgrade)
3. For each forked workflow, system forks all referenced activities from library
   - Each forked activity records: template_activity_id, forked_at_version
4. Component is created at version 1 with all forked workflows and activities
```

### 10.2 Activity Authoring (Library)

```
1. Provider navigates to Provider > Workflows > Activities
2. Creates new activity (name, category, operation_kind)
3. Writes Python/Pulumi code in Monaco editor
4. Defines input/output schemas
5. Saves → creates version 1
6. Subsequent saves create v2, v3, etc.
7. Activity is now available for inclusion in workflow templates
```

### 10.3 Component Activity Editing

```
1. User opens component editor > Operations tab
2. Clicks "Edit" on a deployment activity
3. Activity editor opens inline (Monaco + schemas + versions)
4. User modifies code, saves
5. New version of the forked activity is created
6. Component version is bumped
```

### 10.4 Library Upgrade

```
1. System shows "Upgrade Available" badge on forked activity (library v5, fork at v2)
2. User clicks "Upgrade"
3. Confirmation dialog warns: "This will replace your customized code with library version 5"
4. On confirm: forked activity code/schemas are replaced with library v5
5. forked_at_version updated to 5
6. Component version bumped
```

### 10.5 Workflow Execution (Deploy)

```
1. User triggers "Deploy" on a component
2. System loads the component's forked "deploy" workflow
3. Workflow engine (Temporal) executes activities in graph order:
   a. Validate (deployment activity) — check preconditions
   b. Dry Run (deployment activity) — simulate changes
   c. [Approval Gate] (builtin activity) — wait for approval if configured
   d. Deploy (deployment activity) — execute Pulumi stack operation
   e. Verify (deployment activity) — confirm success
   f. Notify (builtin activity) — send email/Kafka notification
4. Each activity's input/output flows through the workflow graph connections
```

---

## 11. Future Considerations

- **Activity Marketplace**: Share activities across tenants or publish to a community catalog
- **Activity Testing Framework**: Dedicated test harness with mocked infrastructure providers
- **Workflow Editor Replacement**: Evaluate alternatives to Rete.js for improved UX (separate phase)
- **Activity Dependency Graph**: Declare dependencies between activities for automatic ordering
- **Rollback Workflows**: Auto-generated rollback workflows based on deploy workflow (reverse activity order)
- **Custom Activity Categories**: Allow tenants to define additional categories beyond Deployment/Day-2/Builtin
