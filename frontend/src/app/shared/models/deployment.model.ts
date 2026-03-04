/**
 * Overview: TypeScript interfaces for deployments.
 * Architecture: Frontend data models for deployments (Section 5)
 * Dependencies: None
 * Concepts: Deployment lifecycle, topology-to-environment binding
 */

export type DeploymentStatus =
  | 'PLANNED'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'DEPLOYING'
  | 'DEPLOYED'
  | 'FAILED'
  | 'ROLLED_BACK';

export type ResolutionStatus = 'PENDING' | 'RESOLVED' | 'FAILED';

export interface DeploymentCI {
  id: string;
  deploymentId: string;
  ciId: string | null;
  componentId: string;
  topologyNodeId: string | null;
  componentVersion: number | null;
  resolverOutputs: Record<string, unknown> | null;
  createdAt: string;
}

export interface UpgradableCI {
  deploymentCiId: string;
  ciId: string;
  componentId: string;
  componentDisplayName: string;
  deployedVersion: number;
  latestVersion: number;
  deploymentId: string;
  changelog: string | null;
}

export interface Deployment {
  id: string;
  tenantId: string;
  environmentId: string;
  topologyId: string | null;
  name: string;
  description: string | null;
  status: DeploymentStatus;
  parameters: Record<string, unknown> | null;
  resolvedParameters: Record<string, unknown> | null;
  resolutionStatus: ResolutionStatus | null;
  resolutionError: string | null;
  deployedBy: string;
  deployedAt: string | null;
  createdAt: string;
  updatedAt: string;
  cis: DeploymentCI[];
}

export type ComponentInstanceSourceType = 'standalone' | 'topology' | 'stack';

export interface ComponentInstance {
  id: string;
  componentId: string;
  componentDisplayName: string;
  componentVersion: number | null;
  environmentId: string | null;
  status: string;
  sourceType: ComponentInstanceSourceType;
  sourceId: string;
  sourceName: string;
  resolvedParameters: Record<string, unknown> | null;
  outputs: Record<string, unknown> | null;
  deployedAt: string | null;
  createdAt: string;
}

export interface ResolvedParameterInfo {
  key: string;
  value: unknown;
  source: string;
}

export interface ResolvedParametersPreview {
  parameters: Record<string, unknown>;
  details: ResolvedParameterInfo[];
}
