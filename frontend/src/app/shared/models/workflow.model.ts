/**
 * Overview: TypeScript interfaces for workflow definitions, executions, and node types.
 * Architecture: Frontend data models for workflow editor (Section 7.2)
 * Dependencies: None
 * Concepts: Workflow definitions, executions, node types, validation results
 */

export type WorkflowDefinitionStatus = 'DRAFT' | 'ACTIVE' | 'ARCHIVED';
export type WorkflowExecutionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type WorkflowNodeExecutionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'CANCELLED';
export type WorkflowType = 'AUTOMATION' | 'SYSTEM' | 'DEPLOYMENT';

export interface WorkflowDefinition {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  version: number;
  graph: WorkflowGraph | null;
  status: WorkflowDefinitionStatus;
  createdBy: string;
  timeoutSeconds: number;
  maxConcurrent: number;
  workflowType: WorkflowType;
  sourceTopologyId: string | null;
  isSystem: boolean;
  applicableSemanticTypeId: string | null;
  applicableProviderId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
}

export interface WorkflowNode {
  id: string;
  type: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
  label?: string;
}

export interface WorkflowConnection {
  source: string;
  target: string;
  sourcePort: string;
  targetPort: string;
}

export interface WorkflowNodeExecution {
  id: string;
  executionId: string;
  nodeId: string;
  nodeType: string;
  status: WorkflowNodeExecutionStatus;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  startedAt: string | null;
  completedAt: string | null;
  attempt: number;
}

export interface WorkflowExecution {
  id: string;
  tenantId: string;
  definitionId: string;
  definitionVersion: number;
  temporalWorkflowId: string | null;
  status: WorkflowExecutionStatus;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  startedBy: string;
  startedAt: string;
  completedAt: string | null;
  isTest: boolean;
  nodeExecutions: WorkflowNodeExecution[];
}

export interface PortDef {
  name: string;
  direction: 'INPUT' | 'OUTPUT';
  portType: 'FLOW' | 'DATA';
  label: string;
  required: boolean;
  multiple: boolean;
}

export interface NodeTypeInfo {
  typeId: string;
  label: string;
  category: string;
  description: string;
  icon: string;
  ports: PortDef[];
  configSchema: Record<string, unknown>;
  isMarker: boolean;
}

export interface ValidationError {
  nodeId: string | null;
  message: string;
  severity: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface WorkflowDefinitionCreateInput {
  name: string;
  description?: string;
  graph?: WorkflowGraph;
  timeoutSeconds?: number;
  maxConcurrent?: number;
  workflowType?: WorkflowType;
  applicableSemanticTypeId?: string;
  applicableProviderId?: string;
}

export interface GenerateDeploymentWorkflowInput {
  topologyId: string;
  addApprovalGates?: boolean;
  addNotifications?: boolean;
}

export interface WorkflowDefinitionUpdateInput {
  name?: string;
  description?: string;
  graph?: WorkflowGraph;
  timeoutSeconds?: number;
  maxConcurrent?: number;
  applicableSemanticTypeId?: string | null;
  applicableProviderId?: string | null;
}

export interface WorkflowExecutionStartInput {
  definitionId: string;
  input?: Record<string, unknown>;
  isTest?: boolean;
  mockConfigs?: Record<string, unknown>;
}
