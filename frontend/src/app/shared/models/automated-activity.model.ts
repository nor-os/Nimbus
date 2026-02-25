/**
 * Overview: TypeScript interfaces for automated activities, versions, executions, and config changes.
 * Architecture: Frontend model definitions for activity catalog (Section 11.5)
 * Dependencies: None
 * Concepts: Activity catalog with versioned source code, execution tracking, config mutation engine.
 */

export type OperationKind = 'CREATE' | 'READ' | 'UPDATE' | 'DELETE' | 'REMEDIATE' | 'VALIDATE' | 'BACKUP' | 'RESTORE';

export type ImplementationType = 'PYTHON_SCRIPT' | 'HTTP_WEBHOOK' | 'PULUMI_OPERATION' | 'SHELL_SCRIPT' | 'MANUAL';

export type MutationType = 'SET' | 'SET_FROM_INPUT' | 'INCREMENT' | 'DECREMENT' | 'APPEND' | 'REMOVE';

export type ActivityScope = 'COMPONENT' | 'WORKFLOW';

export type ActivityExecutionStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';

export interface AutomatedActivity {
  id: string;
  tenantId: string | null;
  name: string;
  slug: string;
  description: string | null;
  category: string | null;
  semanticActivityTypeId: string | null;
  semanticTypeId: string | null;
  providerId: string | null;
  operationKind: OperationKind;
  implementationType: ImplementationType;
  scope: ActivityScope;
  idempotent: boolean;
  timeoutSeconds: number;
  isSystem: boolean;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
  versions: AutomatedActivityVersion[];
}

export interface AutomatedActivityVersion {
  id: string;
  activityId: string;
  version: number;
  sourceCode: string | null;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  configMutations: Record<string, unknown> | null;
  rollbackMutations: Record<string, unknown> | null;
  changelog: string | null;
  publishedAt: string | null;
  publishedBy: string | null;
  runtimeConfig: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface ActivityExecution {
  id: string;
  tenantId: string;
  activityVersionId: string;
  workflowExecutionId: string | null;
  ciId: string | null;
  deploymentId: string | null;
  inputSnapshot: Record<string, unknown> | null;
  outputSnapshot: Record<string, unknown> | null;
  status: ActivityExecutionStatus;
  error: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
  configChanges: ConfigurationChange[];
}

export interface ConfigurationChange {
  id: string;
  tenantId: string;
  deploymentId: string;
  activityExecutionId: string | null;
  version: number;
  parameterPath: string;
  mutationType: string;
  oldValue: unknown | null;
  newValue: unknown | null;
  appliedAt: string;
  appliedBy: string | null;
  rollbackOf: string | null;
}

export interface AutomatedActivityCreateInput {
  name: string;
  slug?: string | null;
  description?: string | null;
  category?: string | null;
  semanticActivityTypeId?: string | null;
  semanticTypeId?: string | null;
  providerId?: string | null;
  operationKind?: string;
  implementationType?: string;
  scope?: ActivityScope;
  idempotent?: boolean;
  timeoutSeconds?: number;
}

export interface AutomatedActivityUpdateInput {
  name?: string;
  slug?: string;
  description?: string | null;
  category?: string | null;
  semanticActivityTypeId?: string | null;
  semanticTypeId?: string | null;
  providerId?: string | null;
  operationKind?: string;
  implementationType?: string;
  scope?: ActivityScope;
  idempotent?: boolean;
  timeoutSeconds?: number;
}

export interface ActivityVersionCreateInput {
  sourceCode?: string | null;
  inputSchema?: Record<string, unknown> | null;
  outputSchema?: Record<string, unknown> | null;
  configMutations?: Record<string, unknown> | null;
  rollbackMutations?: Record<string, unknown> | null;
  changelog?: string | null;
  runtimeConfig?: Record<string, unknown> | null;
}
