/**
 * Overview: TypeScript interfaces for tenant-related data structures.
 * Architecture: Core tenant type definitions (Section 4.2)
 * Dependencies: none
 * Concepts: Multi-tenancy, tenant hierarchy, quotas, compartments
 */

export interface Tenant {
  id: string;
  name: string;
  parent_id: string | null;
  provider_id: string;
  contact_email: string | null;
  is_root: boolean;
  level: number;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantDetail extends Tenant {
  billing_info: Record<string, unknown> | null;
  children_count: number;
  users_count: number;
}

export interface TenantSetting {
  id: string;
  key: string;
  value: string;
  value_type: string;
  created_at: string;
  updated_at: string;
}

export interface TenantQuota {
  id: string;
  quota_type: string;
  limit_value: number;
  current_usage: number;
  enforcement: string;
  created_at: string;
  updated_at: string;
}

export interface TenantHierarchy {
  id: string;
  name: string;
  level: number;
  is_root: boolean;
  children: TenantHierarchy[];
}

export interface TenantStats {
  tenant_id: string;
  name: string;
  total_users: number;
  total_compartments: number;
  total_children: number;
  quotas: TenantQuota[];
}

export interface TenantCreateRequest {
  name: string;
  parent_id?: string | null;
  contact_email?: string | null;
  billing_info?: Record<string, unknown> | null;
  description?: string | null;
}

export interface TenantUpdateRequest {
  name?: string;
  contact_email?: string | null;
  billing_info?: Record<string, unknown> | null;
  description?: string | null;
}

export interface TenantSettingRequest {
  key: string;
  value: string;
  value_type?: string;
}

export interface UserTenantInfo {
  tenant_id: string;
  tenant_name: string;
  parent_id: string | null;
  is_default: boolean;
  is_root: boolean;
  level: number;
  joined_at: string;
}

export interface Compartment {
  id: string;
  tenant_id: string;
  parent_id: string | null;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompartmentTree {
  id: string;
  name: string;
  description: string | null;
  children: CompartmentTree[];
}

export interface CompartmentCreateRequest {
  name: string;
  parent_id?: string | null;
  description?: string | null;
}
