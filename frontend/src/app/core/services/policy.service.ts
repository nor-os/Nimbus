/**
 * Overview: Policy service — GraphQL queries and mutations for policy library and resolution.
 * Architecture: Core service layer for governance policy data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for policy library, compartment policy resolution, permission-gated
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  PolicyLibraryEntry,
  PolicyLibraryCreateInput,
  PolicyLibraryUpdateInput,
  ResolvedPolicy,
  PolicySummary,
} from '@shared/models/policy.model';

const POLICY_FIELDS = `
  id tenantId name displayName description category statements variables
  severity isSystem tags createdBy createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class PolicyService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  list(filters?: {
    category?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<PolicyLibraryEntry[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ policyLibraryEntries: PolicyLibraryEntry[] }>(`
      query PolicyLibraryEntries(
        $tenantId: UUID!
        $category: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        policyLibraryEntries(
          tenantId: $tenantId
          category: $category
          search: $search
          offset: $offset
          limit: $limit
        ) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.policyLibraryEntries));
  }

  get(policyId: string): Observable<PolicyLibraryEntry | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ policyLibraryEntry: PolicyLibraryEntry | null }>(`
      query PolicyLibraryEntry($tenantId: UUID!, $policyId: UUID!) {
        policyLibraryEntry(tenantId: $tenantId, policyId: $policyId) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, policyId }).pipe(map(d => d.policyLibraryEntry));
  }

  create(input: PolicyLibraryCreateInput): Observable<PolicyLibraryEntry> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPolicyLibraryEntry: PolicyLibraryEntry }>(`
      mutation CreatePolicyLibraryEntry($tenantId: UUID!, $input: PolicyLibraryCreateInput!) {
        createPolicyLibraryEntry(tenantId: $tenantId, input: $input) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createPolicyLibraryEntry));
  }

  update(policyId: string, input: PolicyLibraryUpdateInput): Observable<PolicyLibraryEntry | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updatePolicyLibraryEntry: PolicyLibraryEntry | null }>(`
      mutation UpdatePolicyLibraryEntry($tenantId: UUID!, $policyId: UUID!, $input: PolicyLibraryUpdateInput!) {
        updatePolicyLibraryEntry(tenantId: $tenantId, policyId: $policyId, input: $input) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, policyId, input }).pipe(map(d => d.updatePolicyLibraryEntry));
  }

  delete(policyId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePolicyLibraryEntry: boolean }>(`
      mutation DeletePolicyLibraryEntry($tenantId: UUID!, $policyId: UUID!) {
        deletePolicyLibraryEntry(tenantId: $tenantId, policyId: $policyId)
      }
    `, { tenantId, policyId }).pipe(map(d => d.deletePolicyLibraryEntry));
  }

  resolveCompartmentPolicies(topologyId: string, compartmentId: string): Observable<ResolvedPolicy[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ resolveCompartmentPolicies: ResolvedPolicy[] }>(`
      query ResolveCompartmentPolicies($tenantId: UUID!, $topologyId: UUID!, $compartmentId: String!) {
        resolveCompartmentPolicies(tenantId: $tenantId, topologyId: $topologyId, compartmentId: $compartmentId) {
          policyId name source sourceCompartmentId statements severity category canSuppress
        }
      }
    `, { tenantId, topologyId, compartmentId }).pipe(map(d => d.resolveCompartmentPolicies));
  }

  getPolicySummary(topologyId: string, compartmentId: string): Observable<PolicySummary> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ compartmentPolicySummary: PolicySummary }>(`
      query CompartmentPolicySummary($tenantId: UUID!, $topologyId: UUID!, $compartmentId: String!) {
        compartmentPolicySummary(tenantId: $tenantId, topologyId: $topologyId, compartmentId: $compartmentId) {
          compartmentId directPolicies inheritedPolicies totalStatements denyCount allowCount
        }
      }
    `, { tenantId, topologyId, compartmentId }).pipe(map(d => d.compartmentPolicySummary));
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
