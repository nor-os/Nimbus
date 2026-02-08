/**
 * Overview: Service for permission, role, group, and ABAC policy operations.
 * Architecture: Core service layer for permission system (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: RBAC, ABAC, permissions, roles, groups, policies
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import {
  Role,
  RoleDetail,
  RoleCreate,
  RoleUpdate,
  Group,
  GroupCreate,
  GroupMembersResponse,
  EffectivePermission,
  PermissionCheckResult,
  PermissionOverride,
  ABACPolicy,
  ABACPolicyCreate,
  SimulationResult,
  Permission,
} from '../models/permission.model';

@Injectable({ providedIn: 'root' })
export class PermissionService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);

  private get tenantId(): string | null {
    return this.tenantContext.currentTenantId();
  }

  // Permissions
  listPermissions(): Observable<Permission[]> {
    return this.api.get<Permission[]>(`/api/v1/tenants/${this.tenantId}/permissions`);
  }

  checkPermission(permissionKey: string): Observable<PermissionCheckResult> {
    return this.api.post<PermissionCheckResult>('/api/v1/permissions/check', { permission_key: permissionKey });
  }

  getMyPermissions(): Observable<EffectivePermission[]> {
    return this.api.get<EffectivePermission[]>('/api/v1/permissions/me');
  }

  getUserPermissions(userId: string): Observable<EffectivePermission[]> {
    return this.api.get<EffectivePermission[]>(`/api/v1/permissions/users/${userId}`);
  }

  simulatePermission(userId: string, permissionKey: string, resource?: Record<string, unknown>, context?: Record<string, unknown>): Observable<SimulationResult> {
    return this.api.post<SimulationResult>('/api/v1/permissions/simulate', {
      user_id: userId, permission_key: permissionKey, resource, context,
    });
  }

  // Roles
  listRoles(): Observable<Role[]> {
    return this.api.get<Role[]>(`/api/v1/tenants/${this.tenantId}/roles`);
  }

  getRole(roleId: string): Observable<RoleDetail> {
    return this.api.get<RoleDetail>(`/api/v1/tenants/${this.tenantId}/roles/${roleId}`);
  }

  createRole(data: RoleCreate): Observable<Role> {
    return this.api.post<Role>(`/api/v1/tenants/${this.tenantId}/roles`, data);
  }

  updateRole(roleId: string, data: RoleUpdate): Observable<Role> {
    return this.api.patch<Role>(`/api/v1/tenants/${this.tenantId}/roles/${roleId}`, data);
  }

  deleteRole(roleId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/roles/${roleId}`);
  }

  assignRole(userId: string, roleId: string, compartmentId?: string, expiresAt?: string): Observable<unknown> {
    return this.api.post(`/api/v1/tenants/${this.tenantId}/roles/assign`, {
      user_id: userId, role_id: roleId, compartment_id: compartmentId, expires_at: expiresAt,
    });
  }

  unassignRole(userId: string, roleId: string): Observable<void> {
    return this.api.post<void>(`/api/v1/tenants/${this.tenantId}/roles/unassign`, { user_id: userId, role_id: roleId });
  }

  // Permission Overrides
  listOverrides(): Observable<PermissionOverride[]> {
    return this.api.get<PermissionOverride[]>(`/api/v1/tenants/${this.tenantId}/permission-overrides`);
  }

  createOverride(data: { permission_id: string; principal_type: string; principal_id: string; reason?: string }): Observable<PermissionOverride> {
    return this.api.post<PermissionOverride>(`/api/v1/tenants/${this.tenantId}/permission-overrides`, data);
  }

  deleteOverride(overrideId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/permission-overrides/${overrideId}`);
  }

  // Groups
  listGroups(): Observable<Group[]> {
    return this.api.get<Group[]>(`/api/v1/tenants/${this.tenantId}/groups`);
  }

  getGroup(groupId: string): Observable<Group> {
    return this.api.get<Group>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}`);
  }

  createGroup(data: GroupCreate): Observable<Group> {
    return this.api.post<Group>(`/api/v1/tenants/${this.tenantId}/groups`, data);
  }

  updateGroup(groupId: string, data: Partial<GroupCreate>): Observable<Group> {
    return this.api.patch<Group>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}`, data);
  }

  deleteGroup(groupId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}`);
  }

  getGroupMembers(groupId: string): Observable<GroupMembersResponse> {
    return this.api.get<GroupMembersResponse>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/members`);
  }

  addGroupMember(groupId: string, userId: string): Observable<unknown> {
    return this.api.post(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/members`, { user_id: userId });
  }

  removeGroupMember(groupId: string, userId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/members/${userId}`);
  }

  addChildGroup(groupId: string, childGroupId: string): Observable<unknown> {
    return this.api.post(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/members/group`, { group_id: childGroupId });
  }

  removeChildGroup(groupId: string, childGroupId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/members/group/${childGroupId}`);
  }

  getGroupMemberOf(groupId: string): Observable<Group[]> {
    return this.api.get<Group[]>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/member-of`);
  }

  getGroupRoles(groupId: string): Observable<Role[]> {
    return this.api.get<Role[]>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/roles`);
  }

  assignGroupRole(groupId: string, roleId: string): Observable<unknown> {
    return this.api.post(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/roles`, { role_id: roleId });
  }

  unassignGroupRole(groupId: string, roleId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/groups/${groupId}/roles/${roleId}`);
  }

  // ABAC Policies
  listABACPolicies(): Observable<ABACPolicy[]> {
    return this.api.get<ABACPolicy[]>(`/api/v1/tenants/${this.tenantId}/abac-policies`);
  }

  getABACPolicy(policyId: string): Observable<ABACPolicy> {
    return this.api.get<ABACPolicy>(`/api/v1/tenants/${this.tenantId}/abac-policies/${policyId}`);
  }

  createABACPolicy(data: ABACPolicyCreate): Observable<ABACPolicy> {
    return this.api.post<ABACPolicy>(`/api/v1/tenants/${this.tenantId}/abac-policies`, data);
  }

  updateABACPolicy(policyId: string, data: Partial<ABACPolicyCreate>): Observable<ABACPolicy> {
    return this.api.patch<ABACPolicy>(`/api/v1/tenants/${this.tenantId}/abac-policies/${policyId}`, data);
  }

  deleteABACPolicy(policyId: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${this.tenantId}/abac-policies/${policyId}`);
  }

  validateABACExpression(expression: string): Observable<{ valid: boolean; error: string | null }> {
    return this.api.post<{ valid: boolean; error: string | null }>(`/api/v1/tenants/${this.tenantId}/abac-policies/validate`, { expression });
  }
}
