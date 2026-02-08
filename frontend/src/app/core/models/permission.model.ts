/**
 * Overview: TypeScript interfaces for permission system data structures.
 * Architecture: Core permission type definitions (Section 5.2)
 * Dependencies: app/core/models/user.model
 * Concepts: RBAC, ABAC, permissions, roles, groups
 */

import { User } from './user.model';

export interface Permission {
  id: string;
  domain: string;
  resource: string;
  action: string;
  subtype: string | null;
  description: string | null;
  is_system: boolean;
  key: string;
}

export interface Role {
  id: string;
  tenant_id: string | null;
  name: string;
  description: string | null;
  is_system: boolean;
  is_custom: boolean;
  scope: string;
  parent_role_id: string | null;
  max_level: number | null;
  created_at: string;
  updated_at: string;
}

export interface RoleDetail extends Role {
  permissions: Permission[];
}

export interface RoleCreate {
  name: string;
  description?: string | null;
  scope?: string;
  parent_role_id?: string | null;
  permission_ids?: string[];
  max_level?: number | null;
}

export interface RoleUpdate {
  name?: string;
  description?: string | null;
  permission_ids?: string[] | null;
  max_level?: number | null;
}

export interface Group {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface GroupCreate {
  name: string;
  description?: string | null;
}

export interface GroupMembersResponse {
  users: User[];
  groups: Group[];
}


export interface EffectivePermission {
  permission_key: string;
  source: string;
  role_name?: string | null;
  group_name?: string | null;
  source_tenant_id: string;
  source_tenant_name: string;
  is_inherited: boolean;
  is_denied: boolean;
  deny_source?: string | null;
}

export interface PermissionOverride {
  id: string;
  tenant_id: string;
  permission_id: string;
  permission_key: string;
  principal_type: string;
  principal_id: string;
  principal_name: string;
  effect: string;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PermissionCheckResult {
  allowed: boolean;
  permission_key: string;
  source: string | null;
}

export interface ABACPolicy {
  id: string;
  tenant_id: string;
  name: string;
  expression: string;
  effect: 'allow' | 'deny';
  priority: number;
  is_enabled: boolean;
  target_permission_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ABACPolicyCreate {
  name: string;
  expression: string;
  effect: 'allow' | 'deny';
  priority?: number;
  is_enabled?: boolean;
  target_permission_id?: string | null;
}

export interface SimulationResult {
  allowed: boolean;
  permission_key: string;
  source: string | null;
  evaluation_steps: string[];
}
