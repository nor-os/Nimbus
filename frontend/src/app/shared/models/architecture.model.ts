/**
 * Overview: TypeScript interfaces for architecture topologies, graphs, nodes, and connections.
 * Architecture: Frontend data models for visual architecture planner (Section 5)
 * Dependencies: None
 * Concepts: Architecture topologies store visual infrastructure designs using semantic types.
 *     Nodes represent resources, connections represent relationships with semantic kinds.
 */

export type TopologyStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

export interface TopologyNode {
  id: string;
  semanticTypeId: string;
  label: string | null;
  position: { x: number; y: number };
  properties: Record<string, unknown>;
  compartmentId?: string | null;
}

export interface TopologyConnection {
  id: string;
  source: string;
  target: string;
  relationshipKindId: string;
  label: string | null;
}

export interface TopologyCompartment {
  id: string;
  label: string;
  semanticTypeId?: string | null;
  parentCompartmentId?: string | null;
  position: { x: number; y: number };
  size: { width: number; height: number };
  defaults: Record<string, unknown>;
  properties: Record<string, unknown>;
  policies?: import('./policy.model').CompartmentPolicyRef[];
  suppressedPolicies?: string[];
}

export interface ParameterOverride {
  type: 'explicit' | 'tag_ref';
  value?: unknown;
  tagKey?: string;
}

export interface TopologyStackInstance {
  id: string;
  blueprintId: string;
  label: string;
  compartmentId?: string | null;
  position: { x: number; y: number };
  parameterOverrides: Record<string, ParameterOverride>;
  dependsOn: string[];
  tags: Record<string, unknown>;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  connections: TopologyConnection[];
  compartments?: TopologyCompartment[];
  stacks?: TopologyStackInstance[];
}

export interface ArchitectureTopology {
  id: string;
  tenantId: string | null;
  name: string;
  description: string | null;
  graph: TopologyGraph | null;
  status: TopologyStatus;
  version: number;
  isTemplate: boolean;
  isSystem: boolean;
  tags: string[] | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface TopologyValidationError {
  nodeId: string | null;
  message: string;
  severity: string;
}

export interface TopologyValidationResult {
  valid: boolean;
  errors: TopologyValidationError[];
  warnings: TopologyValidationError[];
}

export interface TopologyExportResult {
  data: unknown;
  format: string;
}

export interface TopologyCreateInput {
  name: string;
  description?: string | null;
  graph?: Record<string, unknown> | null;
  tags?: string[] | null;
  isTemplate?: boolean;
}

export interface TopologyUpdateInput {
  name?: string | null;
  description?: string | null;
  graph?: Record<string, unknown> | null;
  tags?: string[] | null;
}

export interface TopologyImportInput {
  name: string;
  description?: string | null;
  graph?: Record<string, unknown> | null;
  tags?: string[] | null;
  isTemplate?: boolean;
}

// ── Resolution Types ──────────────────────────────────────────────

export interface ResolvedParameter {
  name: string;
  displayName: string;
  value: unknown;
  source: 'explicit' | 'tag_ref' | 'compartment_default' | 'blueprint_default' | 'unresolved';
  isRequired: boolean;
  tagKey: string | null;
}

export interface StackResolution {
  stackId: string;
  stackLabel: string;
  blueprintId: string;
  parameters: ResolvedParameter[];
  isComplete: boolean;
  unresolvedCount: number;
}

export interface ResolutionPreview {
  topologyId: string;
  stacks: StackResolution[];
  deploymentOrder: string[][];
  allComplete: boolean;
  totalUnresolved: number;
}

export interface DeploymentOrder {
  groups: string[][];
}
