/**
 * Overview: Service for identity provider configuration and SCIM token management.
 * Architecture: Core service layer for IdP operations (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: Identity providers, SSO configuration, claim mappings, SCIM tokens
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import {
  IdentityProvider,
  IdentityProviderCreate,
  IdentityProviderUpdate,
  ClaimMapping,
  ClaimMappingCreate,
  SCIMToken,
  SCIMTokenCreate,
  SCIMTokenCreateResponse,
} from '../models/identity-provider.model';

@Injectable({ providedIn: 'root' })
export class IdentityProviderService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);

  private get basePath(): string {
    return `/api/v1/tenants/${this.tenantContext.currentTenantId()}/identity-providers`;
  }

  private get scimPath(): string {
    return `/api/v1/tenants/${this.tenantContext.currentTenantId()}/scim-tokens`;
  }

  // IdP CRUD
  listProviders(): Observable<IdentityProvider[]> {
    return this.api.get<IdentityProvider[]>(this.basePath);
  }

  getProvider(id: string): Observable<IdentityProvider> {
    return this.api.get<IdentityProvider>(`${this.basePath}/${id}`);
  }

  createProvider(data: IdentityProviderCreate): Observable<IdentityProvider> {
    return this.api.post<IdentityProvider>(this.basePath, data);
  }

  updateProvider(id: string, data: IdentityProviderUpdate): Observable<IdentityProvider> {
    return this.api.patch<IdentityProvider>(`${this.basePath}/${id}`, data);
  }

  deleteProvider(id: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/${id}`);
  }

  // Claim Mappings
  listClaimMappings(providerId: string): Observable<ClaimMapping[]> {
    return this.api.get<ClaimMapping[]>(`${this.basePath}/${providerId}/claim-mappings`);
  }

  createClaimMapping(providerId: string, data: ClaimMappingCreate): Observable<ClaimMapping> {
    return this.api.post<ClaimMapping>(`${this.basePath}/${providerId}/claim-mappings`, data);
  }

  deleteClaimMapping(providerId: string, mappingId: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/${providerId}/claim-mappings/${mappingId}`);
  }

  // SCIM Tokens
  listSCIMTokens(): Observable<SCIMToken[]> {
    return this.api.get<SCIMToken[]>(this.scimPath);
  }

  createSCIMToken(data: SCIMTokenCreate): Observable<SCIMTokenCreateResponse> {
    return this.api.post<SCIMTokenCreateResponse>(this.scimPath, data);
  }

  revokeSCIMToken(tokenId: string): Observable<void> {
    return this.api.delete<void>(`${this.scimPath}/${tokenId}`);
  }
}
