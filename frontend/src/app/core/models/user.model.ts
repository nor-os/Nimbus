/**
 * Overview: TypeScript interfaces for user management data structures.
 * Architecture: Core user type definitions (Section 5.1)
 * Dependencies: none
 * Concepts: User management, roles, groups
 */

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  provider_id: string;
  identity_provider_id: string | null;
  external_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserRoleInfo {
  id: string;
  role_id: string;
  role_name: string;
  tenant_id: string;
  compartment_id: string | null;
  granted_at: string;
  expires_at: string | null;
}

export interface UserGroupInfo {
  id: string;
  group_id: string;
  group_name: string;
}

export interface UserDetail extends User {
  roles: UserRoleInfo[];
  groups: UserGroupInfo[];
  effective_permissions: string[];
}

export interface UserCreateRequest {
  email: string;
  password?: string | null;
  display_name?: string | null;
  role_ids?: string[];
  group_ids?: string[];
  identity_provider_id?: string | null;
  external_id?: string | null;
}

export interface UserUpdateRequest {
  display_name?: string | null;
  is_active?: boolean;
}

export interface UserListResponse {
  items: User[];
  total: number;
  offset: number;
  limit: number;
}
