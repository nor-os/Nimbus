/**
 * Overview: TypeScript interfaces for service cluster (blueprint) data models.
 * Architecture: Shared model definitions (Section 8)
 * Dependencies: None
 * Concepts: Service clusters are pure blueprint templates with slots and parameters.
 *     Evolved to full stack blueprints with versioning, components, instances,
 *     governance, operational workflows, and DR reservations.
 */

// ── Enums ────────────────────────────────────────────────────────────

export type BlueprintCategory =
  'COMPUTE' | 'DATABASE' | 'NETWORKING' | 'STORAGE' | 'PLATFORM' |
  'SECURITY' | 'MONITORING' | 'CUSTOM';

export type BindingDirection = 'INPUT' | 'OUTPUT';

export type StackWorkflowKind =
  'PROVISION' | 'DEPROVISION' | 'UPDATE' | 'SCALE' | 'BACKUP' |
  'RESTORE' | 'FAILOVER' | 'HEALTH_CHECK' | 'CUSTOM';

export type StackInstanceStatus =
  'PLANNED' | 'PROVISIONING' | 'ACTIVE' | 'UPDATING' | 'DEGRADED' |
  'DECOMMISSIONING' | 'DECOMMISSIONED' | 'FAILED';

export type HealthStatus = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'UNKNOWN';

export type ComponentInstanceStatus =
  'PENDING' | 'PROVISIONING' | 'ACTIVE' | 'UPDATING' | 'FAILED' | 'DECOMMISSIONED';

export type ReservationType = 'HOT_STANDBY' | 'WARM_STANDBY' | 'COLD_STANDBY' | 'PILOT_LIGHT';

export type ReservationStatus = 'PENDING' | 'ACTIVE' | 'CLAIMED' | 'RELEASED' | 'EXPIRED';

export type SyncMethod = 'REAL_TIME' | 'SCHEDULED' | 'ON_DEMAND' | 'WORKFLOW';

export type TestResult = 'PASSED' | 'FAILED' | 'PARTIAL' | 'NOT_TESTED';

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
  componentId: string | null;
  defaultParameters: Record<string, unknown> | null;
  dependsOn: Record<string, unknown> | null;
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

export interface StackBlueprintVersion {
  id: string;
  blueprintId: string;
  version: number;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  componentGraph: Record<string, unknown> | null;
  variableBindings: Record<string, unknown> | null;
  changelog: string | null;
  publishedBy: string | null;
  createdAt: string;
}

export interface StackBlueprintComponent {
  id: string;
  blueprintId: string;
  componentId: string;
  nodeId: string;
  label: string;
  description: string | null;
  sortOrder: number;
  isOptional: boolean;
  defaultParameters: Record<string, unknown> | null;
  dependsOn: Record<string, unknown> | null;
  componentName: string | null;
  componentVersion: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface StackVariableBinding {
  id: string;
  blueprintId: string;
  direction: BindingDirection;
  variableName: string;
  targetNodeId: string;
  targetParameter: string;
  transformExpression: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StackBlueprintGovernance {
  id: string;
  blueprintId: string;
  tenantId: string;
  isAllowed: boolean;
  parameterConstraints: Record<string, unknown> | null;
  maxInstances: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface StackWorkflow {
  id: string;
  blueprintId: string;
  workflowDefinitionId: string;
  workflowKind: StackWorkflowKind;
  name: string;
  displayName: string | null;
  isRequired: boolean;
  triggerConditions: Record<string, unknown> | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface StackInstanceComponent {
  id: string;
  stackInstanceId: string;
  blueprintComponentId: string | null;
  componentId: string;
  componentVersion: number | null;
  ciId: string | null;
  deploymentId: string | null;
  status: ComponentInstanceStatus;
  resolvedParameters: Record<string, unknown> | null;
  outputs: Record<string, unknown> | null;
  pulumiStateUrl: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StackRuntimeInstance {
  id: string;
  blueprintId: string;
  blueprintVersion: number;
  tenantId: string;
  environmentId: string | null;
  name: string;
  status: StackInstanceStatus;
  inputValues: Record<string, unknown> | null;
  outputValues: Record<string, unknown> | null;
  componentStates: Record<string, unknown> | null;
  healthStatus: HealthStatus;
  deployedBy: string | null;
  deployedAt: string | null;
  haConfig: Record<string, unknown> | null;
  drConfig: Record<string, unknown> | null;
  components: StackInstanceComponent[];
  createdAt: string;
  updatedAt: string;
}

export interface StackRuntimeInstanceList {
  items: StackRuntimeInstance[];
  total: number;
}

export interface ReservationSyncPolicy {
  id: string;
  reservationId: string;
  sourceNodeId: string;
  targetNodeId: string;
  syncMethod: SyncMethod;
  syncIntervalSeconds: number | null;
  syncWorkflowId: string | null;
  lastSyncedAt: string | null;
  syncLagSeconds: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface StackReservation {
  id: string;
  stackInstanceId: string;
  tenantId: string;
  reservationType: ReservationType;
  targetEnvironmentId: string | null;
  targetProviderId: string | null;
  reservedResources: Record<string, unknown> | null;
  rtoSeconds: number | null;
  rpoSeconds: number | null;
  status: ReservationStatus;
  costPerHour: number | null;
  lastTestedAt: string | null;
  testResult: TestResult | null;
  syncPolicies: ReservationSyncPolicy[];
  createdAt: string;
  updatedAt: string;
}

export interface StackReservationList {
  items: StackReservation[];
  total: number;
}

export interface BlueprintReservationTemplate {
  id: string;
  blueprintId: string;
  reservationType: ReservationType;
  resourcePercentage: number;
  targetEnvironmentLabel: string | null;
  targetProviderId: string | null;
  rtoSeconds: number | null;
  rpoSeconds: number | null;
  autoCreateOnDeploy: boolean;
  syncPoliciesTemplate: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface ComponentReservationTemplate {
  id: string;
  blueprintComponentId: string;
  reservationType: ReservationType;
  resourcePercentage: number;
  targetEnvironmentLabel: string | null;
  targetProviderId: string | null;
  rtoSeconds: number | null;
  rpoSeconds: number | null;
  autoCreateOnDeploy: boolean;
  syncPoliciesTemplate: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface ComponentReservationTemplateInput {
  reservationType: ReservationType;
  resourcePercentage?: number;
  targetEnvironmentLabel?: string;
  targetProviderId?: string;
  rtoSeconds?: number;
  rpoSeconds?: number;
  autoCreateOnDeploy?: boolean;
  syncPoliciesTemplate?: Record<string, unknown>;
}

export interface ReservationTemplateInput {
  reservationType: ReservationType;
  resourcePercentage?: number;
  targetEnvironmentLabel?: string;
  targetProviderId?: string;
  rtoSeconds?: number;
  rpoSeconds?: number;
  autoCreateOnDeploy?: boolean;
  syncPoliciesTemplate?: Record<string, unknown>;
}

export interface ServiceCluster {
  id: string;
  tenantId: string | null;
  name: string;
  description: string | null;
  clusterType: string;
  architectureTopologyId: string | null;
  topologyNodeId: string | null;
  tags: Record<string, unknown>;
  semanticTypeName: string | null;
  stackTagKey: string | null;
  metadata: Record<string, unknown> | null;
  providerId: string | null;
  category: BlueprintCategory | null;
  icon: string | null;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  version: number;
  isPublished: boolean;
  isSystem: boolean;
  displayName: string | null;
  createdBy: string | null;
  haConfigSchema: Record<string, unknown> | null;
  haConfigDefaults: Record<string, unknown> | null;
  drConfigSchema: Record<string, unknown> | null;
  drConfigDefaults: Record<string, unknown> | null;
  slots: ServiceClusterSlot[];
  parameters: StackBlueprintParameter[];
  blueprintComponents: StackBlueprintComponent[];
  variableBindings: StackVariableBinding[];
  reservationTemplate: BlueprintReservationTemplate | null;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceClusterList {
  items: ServiceCluster[];
  total: number;
}

// ── Legacy Stack Tag Types ──────────────────────────────────────────

export interface StackTagGroup {
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
  stacks: StackTagGroup[];
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
  providerId?: string;
  category?: BlueprintCategory;
  icon?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  displayName?: string;
  haConfigSchema?: Record<string, unknown>;
  haConfigDefaults?: Record<string, unknown>;
  drConfigSchema?: Record<string, unknown>;
  drConfigDefaults?: Record<string, unknown>;
}

export interface ServiceClusterUpdateInput {
  name?: string;
  description?: string;
  clusterType?: string;
  tags?: Record<string, unknown>;
  stackTagKey?: string;
  metadata?: Record<string, unknown>;
  providerId?: string;
  category?: BlueprintCategory;
  icon?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  displayName?: string;
  haConfigSchema?: Record<string, unknown>;
  haConfigDefaults?: Record<string, unknown>;
  drConfigSchema?: Record<string, unknown>;
  drConfigDefaults?: Record<string, unknown>;
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

export interface BlueprintComponentInput {
  componentId: string;
  nodeId: string;
  label?: string;
  description?: string;
  sortOrder?: number;
  isOptional?: boolean;
  defaultParameters?: Record<string, unknown>;
  dependsOn?: Record<string, unknown>;
}

export interface VariableBindingInput {
  direction: BindingDirection;
  variableName: string;
  targetNodeId: string;
  targetParameter: string;
  transformExpression?: string;
}

export interface GovernanceInput {
  governanceTenantId: string;
  isAllowed?: boolean;
  parameterConstraints?: Record<string, unknown>;
  maxInstances?: number;
}

export interface StackWorkflowInput {
  workflowDefinitionId: string;
  workflowKind: StackWorkflowKind;
  name: string;
  displayName?: string;
  isRequired?: boolean;
  triggerConditions?: Record<string, unknown>;
  sortOrder?: number;
}

export interface DeployStackInput {
  blueprintId: string;
  name: string;
  environmentId?: string;
  inputValues?: Record<string, unknown>;
  haConfig?: Record<string, unknown>;
  drConfig?: Record<string, unknown>;
}

export interface CreateReservationInput {
  stackInstanceId: string;
  reservationType: ReservationType;
  targetEnvironmentId?: string;
  targetProviderId?: string;
  reservedResources?: Record<string, unknown>;
  rtoSeconds?: number;
  rpoSeconds?: number;
  costPerHour?: number;
}

export interface SyncPolicyInput {
  sourceNodeId: string;
  targetNodeId: string;
  syncMethod: SyncMethod;
  syncIntervalSeconds?: number;
  syncWorkflowId?: string;
}
