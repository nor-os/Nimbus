/**
 * Overview: Service for tenant CRUD operations via REST API.
 * Architecture: Core service layer for tenant management (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: Multi-tenancy, tenant lifecycle, quota management
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  TenantTag,
  TenantTagList,
  TenantTagCreateInput,
  TenantTagUpdateInput,
} from '@shared/models/tenant-tag.model';
import {
  Tenant,
  TenantDetail,
  TenantCreateRequest,
  TenantUpdateRequest,
  TenantHierarchy,
  TenantStats,
  TenantSetting,
  TenantSettingRequest,
  TenantQuota,
  Compartment,
  CompartmentTree,
  CompartmentCreateRequest,
} from '../models/tenant.model';

@Injectable({ providedIn: 'root' })
export class TenantService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // Tenant CRUD
  listTenants(offset = 0, limit = 50): Observable<Tenant[]> {
    return this.api.get<Tenant[]>(`/api/v1/tenants?offset=${offset}&limit=${limit}`);
  }

  getTenant(id: string): Observable<TenantDetail> {
    return this.api.get<TenantDetail>(`/api/v1/tenants/${id}`);
  }

  createTenant(data: TenantCreateRequest): Observable<Tenant> {
    return this.api.post<Tenant>('/api/v1/tenants', data);
  }

  updateTenant(id: string, data: TenantUpdateRequest): Observable<Tenant> {
    return this.api.patch<Tenant>(`/api/v1/tenants/${id}`, data);
  }

  deleteTenant(id: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/tenants/${id}`);
  }

  // Hierarchy & Stats
  getTenantHierarchy(id: string): Observable<TenantHierarchy> {
    return this.api.get<TenantHierarchy>(`/api/v1/tenants/${id}/hierarchy`);
  }

  getTenantStats(id: string): Observable<TenantStats> {
    return this.api.get<TenantStats>(`/api/v1/tenants/${id}/stats`);
  }

  // Settings
  updateSettings(tenantId: string, settings: TenantSettingRequest[]): Observable<TenantSetting[]> {
    return this.api.post<TenantSetting[]>(`/api/v1/tenants/${tenantId}/settings`, settings);
  }

  // Quotas
  updateQuota(
    tenantId: string,
    quotaType: string,
    data: { limit_value?: number; enforcement?: string },
  ): Observable<TenantQuota> {
    return this.api.patch<TenantQuota>(`/api/v1/tenants/${tenantId}/quotas/${quotaType}`, data);
  }

  // Compartments
  listCompartments(): Observable<Compartment[]> {
    return this.api.get<Compartment[]>('/api/v1/compartments');
  }

  getCompartmentTree(): Observable<CompartmentTree[]> {
    return this.api.get<CompartmentTree[]>('/api/v1/compartments/tree');
  }

  createCompartment(data: CompartmentCreateRequest): Observable<Compartment> {
    return this.api.post<Compartment>('/api/v1/compartments', data);
  }

  updateCompartment(id: string, data: Partial<CompartmentCreateRequest>): Observable<Compartment> {
    return this.api.patch<Compartment>(`/api/v1/compartments/${id}`, data);
  }

  deleteCompartment(id: string): Observable<void> {
    return this.api.delete<void>(`/api/v1/compartments/${id}`);
  }

  // Export
  startExport(tenantId: string): Observable<{ job_id: string }> {
    return this.api.post<{ job_id: string }>(`/api/v1/tenants/${tenantId}/export`, {});
  }

  getExportDownload(tenantId: string, jobId: string): Observable<{ download_url: string }> {
    return this.api.get<{ download_url: string }>(
      `/api/v1/tenants/${tenantId}/export/${jobId}/download`,
    );
  }

  // ── Tenant Tags (GraphQL) ──────────────────────────────────────────

  listTags(tenantId: string, search?: string): Observable<TenantTagList> {
    return this.gql<{ tenantTags: TenantTagList }>(`
      query TenantTags($tenantId: UUID!, $search: String) {
        tenantTags(tenantId: $tenantId, search: $search) {
          items {
            id tenantId key displayName description
            valueSchema value isSecret sortOrder
            createdAt updatedAt
          }
          total
        }
      }
    `, { tenantId, search }).pipe(map(d => d.tenantTags));
  }

  createTag(tenantId: string, input: TenantTagCreateInput): Observable<TenantTag> {
    return this.gql<{ createTenantTag: TenantTag }>(`
      mutation CreateTenantTag($tenantId: UUID!, $input: TenantTagCreateInput!) {
        createTenantTag(tenantId: $tenantId, input: $input) {
          id tenantId key displayName description
          valueSchema value isSecret sortOrder
          createdAt updatedAt
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createTenantTag));
  }

  updateTag(tenantId: string, id: string, input: TenantTagUpdateInput): Observable<TenantTag> {
    return this.gql<{ updateTenantTag: TenantTag }>(`
      mutation UpdateTenantTag($tenantId: UUID!, $id: UUID!, $input: TenantTagUpdateInput!) {
        updateTenantTag(tenantId: $tenantId, id: $id, input: $input) {
          id tenantId key displayName description
          valueSchema value isSecret sortOrder
          createdAt updatedAt
        }
      }
    `, { tenantId, id, input }).pipe(map(d => d.updateTenantTag));
  }

  deleteTag(tenantId: string, id: string): Observable<boolean> {
    return this.gql<{ deleteTenantTag: boolean }>(`
      mutation DeleteTenantTag($tenantId: UUID!, $id: UUID!) {
        deleteTenantTag(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deleteTenantTag));
  }

  private gql<T>(
    query: string,
    variables: Record<string, unknown> = {},
  ): Observable<T> {
    return this.api
      .post<{ data: T; errors?: Array<{ message: string }> }>(this.gqlUrl, {
        query,
        variables,
      })
      .pipe(
        map((response) => {
          if (response.errors?.length) {
            throw new Error(response.errors[0].message);
          }
          return response.data;
        }),
      );
  }
}
