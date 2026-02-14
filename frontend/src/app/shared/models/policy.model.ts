/**
 * Overview: TypeScript interfaces for policy library, resolution, and compartment policy references.
 * Architecture: Frontend data models for governance policy library (Section 5)
 * Dependencies: None
 * Concepts: Policy library entries define reusable IAM policies. Compartment policy refs attach
 *     library or inline policies to topology compartments with inheritance and suppression.
 */

export type PolicyCategory = 'IAM' | 'NETWORK' | 'ENCRYPTION' | 'TAGGING' | 'COST';
export type PolicySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export interface PolicyStatement {
  sid: string;
  effect: 'allow' | 'deny';
  actions: string[];
  resources: string[];
  principals: string[];
  condition: string | null;
}

export interface PolicyVariable {
  type: string;
  default?: unknown;
  description?: string;
}

export interface PolicyLibraryEntry {
  id: string;
  tenantId: string | null;
  name: string;
  displayName: string;
  description: string | null;
  category: PolicyCategory;
  statements: PolicyStatement[];
  variables: Record<string, PolicyVariable> | null;
  severity: PolicySeverity;
  isSystem: boolean;
  tags: string[] | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface PolicyLibraryCreateInput {
  name: string;
  displayName: string;
  description?: string | null;
  category: PolicyCategory;
  statements: PolicyStatement[];
  variables?: Record<string, PolicyVariable> | null;
  severity?: PolicySeverity;
  tags?: string[] | null;
}

export interface PolicyLibraryUpdateInput {
  name?: string | null;
  displayName?: string | null;
  description?: string | null;
  category?: PolicyCategory | null;
  statements?: PolicyStatement[] | null;
  variables?: Record<string, PolicyVariable> | null;
  severity?: PolicySeverity | null;
  tags?: string[] | null;
}

export interface CompartmentPolicyRef {
  policyId?: string | null;
  inline?: {
    name: string;
    statements: PolicyStatement[];
    severity?: PolicySeverity;
    category?: PolicyCategory;
  } | null;
  inherit: boolean;
  variableOverrides?: Record<string, unknown> | null;
}

export interface ResolvedPolicy {
  policyId: string;
  name: string;
  source: 'library' | 'inline' | 'inherited_library' | 'inherited_inline';
  sourceCompartmentId: string | null;
  statements: PolicyStatement[];
  severity: PolicySeverity;
  category: PolicyCategory;
  canSuppress: boolean;
}

export interface PolicySummary {
  compartmentId: string;
  directPolicies: number;
  inheritedPolicies: number;
  totalStatements: number;
  denyCount: number;
  allowCount: number;
}
