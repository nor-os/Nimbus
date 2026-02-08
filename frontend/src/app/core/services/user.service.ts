/**
 * Overview: Service for user management operations via REST API.
 * Architecture: Core service layer for user lifecycle (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: User management, tenant-scoped users, CRUD
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import {
  User,
  UserDetail,
  UserCreateRequest,
  UserUpdateRequest,
  UserListResponse,
} from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);

  private get basePath(): string {
    return `/api/v1/tenants/${this.tenantContext.currentTenantId()}/users`;
  }

  listUsers(offset = 0, limit = 50, search?: string): Observable<UserListResponse> {
    let path = `${this.basePath}?offset=${offset}&limit=${limit}`;
    if (search) path += `&search=${encodeURIComponent(search)}`;
    return this.api.get<UserListResponse>(path);
  }

  getUser(userId: string): Observable<UserDetail> {
    return this.api.get<UserDetail>(`${this.basePath}/${userId}`);
  }

  createUser(data: UserCreateRequest): Observable<User> {
    return this.api.post<User>(this.basePath, data);
  }

  updateUser(userId: string, data: UserUpdateRequest): Observable<User> {
    return this.api.patch<User>(`${this.basePath}/${userId}`, data);
  }

  deactivateUser(userId: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/${userId}`);
  }

  addUserToTenant(userId: string): Observable<{ user_id: string; tenant_id: string }> {
    return this.api.post<{ user_id: string; tenant_id: string }>(
      `${this.basePath}/${userId}/tenant-membership`,
      {},
    );
  }

  removeUserFromTenant(userId: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/${userId}/tenant-membership`);
  }
}
