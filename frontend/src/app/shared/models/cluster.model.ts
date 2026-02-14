/**
 * Overview: TypeScript interfaces for service cluster (blueprint) data models.
 * Architecture: Shared model definitions (Section 8)
 * Dependencies: None
 * Concepts: Service clusters are pure blueprint templates with slots and parameters.
 *     CI assignment is a deployment-time concern, not part of the blueprint.
 */

// ── Core Interfaces ──────────────────────────────────────────────────

export interface ServiceClusterSlot {
  id: string;
  clusterId: string;
  name: string;
  displayName: string;
  description: string | null;
  allowedCiClassIds: string[] | null;
  semanticCategoryId: string | null;
  semanticCategoryName: string | null;
  semanticTypeId: string | null;
  semanticTypeName: string | null;
  minCount: number;
  maxCount: number | null;
  isRequired: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface StackBlueprintParameter {
  id: string;
  clusterId: string;
  name: string;
  displayName: string;
  description: string | null;
  parameterSchema: Record<string, unknown> | null;
  defaultValue: unknown;
  sourceType: 'slot_derived' | 'custom';
  sourceSlotId: string | null;
  sourceSlotName: string | null;
  sourcePropertyPath: string | null;
  isRequired: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceCluster {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  clusterType: string;
  architectureTopologyId: string | null;
  topologyNodeId: string | null;
  tags: Record<string, unknown>;
  semanticTypeName: string | null;
  stackTagKey: string | null;
  metadata: Record<string, unknown> | null;
  slots: ServiceClusterSlot[];
  parameters: StackBlueprintParameter[];
  createdAt: string;
  updatedAt: string;
}

export interface ServiceClusterList {
  items: ServiceCluster[];
  total: number;
}

// ── Stack Types ──────────────────────────────────────────────────────

export interface StackInstance {
  tagValue: string;
  ciCount: number;
  activeCount: number;
  plannedCount: number;
  maintenanceCount: number;
}

export interface StackList {
  blueprintId: string;
  blueprintName: string;
  tagKey: string;
  stacks: StackInstance[];
  total: number;
}

// ── Input Types ──────────────────────────────────────────────────────

export interface ServiceClusterSlotCreateInput {
  name: string;
  displayName?: string;
  description?: string;
  allowedCiClassIds?: string[];
  semanticCategoryId?: string;
  semanticTypeId?: string;
  minCount?: number;
  maxCount?: number;
  isRequired?: boolean;
  sortOrder?: number;
}

export interface ServiceClusterCreateInput {
  name: string;
  description?: string;
  clusterType?: string;
  architectureTopologyId?: string;
  topologyNodeId?: string;
  tags?: Record<string, unknown>;
  stackTagKey?: string;
  metadata?: Record<string, unknown>;
  slots?: ServiceClusterSlotCreateInput[];
}

export interface ServiceClusterUpdateInput {
  name?: string;
  description?: string;
  clusterType?: string;
  tags?: Record<string, unknown>;
  stackTagKey?: string;
  metadata?: Record<string, unknown>;
}

export interface BlueprintParameterCreateInput {
  name: string;
  displayName?: string;
  description?: string;
  parameterSchema?: Record<string, unknown>;
  defaultValue?: unknown;
  isRequired?: boolean;
  sortOrder?: number;
}

export interface BlueprintParameterUpdateInput {
  displayName?: string;
  description?: string | null;
  parameterSchema?: Record<string, unknown> | null;
  defaultValue?: unknown;
  isRequired?: boolean;
  sortOrder?: number;
}

export interface ServiceClusterSlotUpdateInput {
  displayName?: string;
  description?: string;
  allowedCiClassIds?: string[];
  semanticCategoryId?: string;
  semanticTypeId?: string;
  minCount?: number;
  maxCount?: number;
  isRequired?: boolean;
  sortOrder?: number;
}
