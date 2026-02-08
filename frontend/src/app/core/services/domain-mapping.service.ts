/**
 * Overview: Service for managing email domain-to-tenant mappings.
 * Architecture: Core service layer (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: Domain mapping CRUD, tenant-scoped API calls
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface DomainMapping {
  id: string;
  domain: string;
  tenant_id: string;
  identity_provider_id: string | null;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface DomainMappingCreate {
  domain: string;
  identity_provider_id?: string;
}

@Injectable({ providedIn: 'root' })
export class DomainMappingService {
  private api = inject(ApiService);

  private pathFor(tenantId: string): string {
    return `/api/v1/tenants/${tenantId}/domain-mappings`;
  }

  listForTenant(tenantId: string): Observable<DomainMapping[]> {
    return this.api.get<DomainMapping[]>(this.pathFor(tenantId));
  }

  createForTenant(tenantId: string, data: DomainMappingCreate): Observable<DomainMapping> {
    return this.api.post<DomainMapping>(this.pathFor(tenantId), data);
  }

  deleteForTenant(tenantId: string, mappingId: string): Observable<void> {
    return this.api.delete<void>(`${this.pathFor(tenantId)}/${mappingId}`);
  }
}
