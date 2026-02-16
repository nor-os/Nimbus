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
  ciId: string;
  componentId: string;
  topologyNodeId: string | null;
  resolverOutputs: Record<string, unknown> | null;
  createdAt: string;
}

export interface Deployment {
  id: string;
  tenantId: string;
  environmentId: string;
  topologyId: string;
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

export interface ResolvedParameterInfo {
  key: string;
  value: unknown;
  source: string;
}

export interface ResolvedParametersPreview {
  parameters: Record<string, unknown>;
  details: ResolvedParameterInfo[];
}
