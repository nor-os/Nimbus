/**
 * Overview: TypeScript interfaces for the component model, resolvers, and governance.
 * Architecture: Frontend data models for component framework (Section 11)
 * Dependencies: None
 * Concepts: Components, versions, resolvers, resolver configs, governance rules
 */

export type ComponentLanguage = 'typescript' | 'python';

export interface Component {
  id: string;
  tenantId: string | null;
  providerId: string;
  semanticTypeId: string;
  name: string;
  displayName: string;
  description: string | null;
  language: ComponentLanguage;
  code: string;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  resolverBindings: Record<string, unknown> | null;
  version: number;
  isPublished: boolean;
  isSystem: boolean;
  upgradeWorkflowId: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  versions: ComponentVersion[];
  governanceRules: ComponentGovernance[];
  operations: ComponentOperation[];
  providerName: string | null;
  semanticTypeName: string | null;
}

export interface ComponentVersion {
  id: string;
  componentId: string;
  version: number;
  code: string;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  resolverBindings: Record<string, unknown> | null;
  changelog: string | null;
  publishedAt: string;
  publishedBy: string;
}

export interface Resolver {
  id: string;
  resolverType: string;
  displayName: string;
  description: string | null;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  handlerClass: string;
  isSystem: boolean;
  instanceConfigSchema: Record<string, unknown> | null;
  code: string | null;
  category: string | null;
  supportsRelease: boolean;
  supportsUpdate: boolean;
  compatibleProviderIds: string[];
}

export interface ResolverDefinitionCreateInput {
  resolverType: string;
  displayName: string;
  handlerClass: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  instanceConfigSchema?: Record<string, unknown>;
  code?: string;
  category?: string;
  supportsRelease?: boolean;
  supportsUpdate?: boolean;
  compatibleProviderIds?: string[];
}

export interface ResolverDefinitionUpdateInput {
  displayName?: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  instanceConfigSchema?: Record<string, unknown>;
  code?: string;
  category?: string;
  supportsRelease?: boolean;
  supportsUpdate?: boolean;
  compatibleProviderIds?: string[];
}

export interface ResolverConfiguration {
  id: string;
  resolverId: string;
  resolverType: string;
  landingZoneId: string | null;
  environmentId: string | null;
  config: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface ComponentGovernance {
  id: string;
  componentId: string;
  tenantId: string;
  isAllowed: boolean;
  parameterConstraints: Record<string, unknown> | null;
  maxInstances: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface ComponentCreateInput {
  name: string;
  displayName: string;
  providerId: string;
  semanticTypeId: string;
  language: ComponentLanguage;
  description?: string;
  code?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  resolverBindings?: Record<string, unknown>;
}

export type EstimatedDowntime = 'NONE' | 'BRIEF' | 'EXTENDED';
export type OperationCategory = 'DEPLOYMENT' | 'DAY2';
export type OperationKind = 'CREATE' | 'DELETE' | 'RESTORE' | 'UPDATE' | 'VALIDATE' | 'READ';

export interface ComponentOperation {
  id: string;
  componentId: string;
  name: string;
  displayName: string;
  description: string | null;
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  workflowDefinitionId: string;
  workflowDefinitionName: string | null;
  isDestructive: boolean;
  requiresApproval: boolean;
  estimatedDowntime: EstimatedDowntime;
  operationCategory: OperationCategory;
  operationKind: OperationKind | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface ComponentOperationCreateInput {
  name: string;
  displayName: string;
  workflowDefinitionId: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  isDestructive?: boolean;
  requiresApproval?: boolean;
  estimatedDowntime?: EstimatedDowntime;
  sortOrder?: number;
}

export interface ComponentOperationUpdateInput {
  name?: string;
  displayName?: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  workflowDefinitionId?: string;
  isDestructive?: boolean;
  requiresApproval?: boolean;
  estimatedDowntime?: EstimatedDowntime;
  sortOrder?: number;
}

export interface ComponentUpdateInput {
  name?: string;
  displayName?: string;
  description?: string;
  code?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  resolverBindings?: Record<string, unknown>;
  language?: ComponentLanguage;
}
