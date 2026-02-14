/**
 * Overview: TypeScript interfaces for tenant tag data models.
 * Architecture: Shared model definitions (Section 3.2)
 * Dependencies: None
 * Concepts: Tenant tags provide typed key-value configuration with JSON Schema validation.
 */

export interface TenantTag {
  id: string;
  tenantId: string;
  key: string;
  displayName: string;
  description: string | null;
  valueSchema: Record<string, unknown> | null;
  value: unknown;
  isSecret: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface TenantTagList {
  items: TenantTag[];
  total: number;
}

export interface TenantTagCreateInput {
  key: string;
  displayName?: string;
  description?: string;
  valueSchema?: Record<string, unknown>;
  value?: unknown;
  isSecret?: boolean;
  sortOrder?: number;
}

export interface TenantTagUpdateInput {
  displayName?: string;
  description?: string | null;
  valueSchema?: Record<string, unknown> | null;
  value?: unknown;
  isSecret?: boolean;
  sortOrder?: number;
}
