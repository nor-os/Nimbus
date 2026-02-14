/**
 * Overview: Cloud backend service — GraphQL queries and mutations for managing backend
 *     connections, credentials, connectivity testing, and IAM mappings.
 * Architecture: Core service layer for cloud backend management (Section 11)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD, write-only credentials, connectivity testing, IAM mapping resolution.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  CloudBackend,
  CloudBackendIAMMapping,
  CloudBackendIAMMappingInput,
  CloudBackendIAMMappingUpdateInput,
  CloudBackendInput,
  CloudBackendUpdateInput,
  ConnectivityTestResult,
} from '@shared/models/cloud-backend.model';

const BACKEND_FIELDS = `
  id tenantId providerId providerName providerDisplayName providerIcon
  name description status hasCredentials credentialsSchemaVersion
  scopeConfig endpointUrl isShared
  lastConnectivityCheck lastConnectivityStatus lastConnectivityError
  iamMappingCount createdBy createdAt updatedAt
`;

const IAM_MAPPING_FIELDS = `
  id backendId roleId roleName cloudIdentity description isActive createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class CloudBackendService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // -- Backend queries -----------------------------------------------------

  listBackends(options?: {
    includeShared?: boolean;
    status?: string;
    providerId?: string;
  }): Observable<CloudBackend[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloudBackends: CloudBackend[] }>(`
      query CloudBackends(
        $tenantId: UUID!
        $includeShared: Boolean
        $status: String
        $providerId: UUID
      ) {
        cloudBackends(
          tenantId: $tenantId
          includeShared: $includeShared
          status: $status
          providerId: $providerId
        ) {
          ${BACKEND_FIELDS}
        }
      }
    `, { tenantId, ...options }).pipe(
      map((data) => data.cloudBackends),
    );
  }

  getBackend(id: string): Observable<CloudBackend | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloudBackend: CloudBackend | null }>(`
      query CloudBackend($tenantId: UUID!, $id: UUID!) {
        cloudBackend(tenantId: $tenantId, id: $id) {
          ${BACKEND_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.cloudBackend),
    );
  }

  // -- Backend mutations ---------------------------------------------------

  createBackend(input: CloudBackendInput): Observable<CloudBackend> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCloudBackend: CloudBackend }>(`
      mutation CreateCloudBackend($tenantId: UUID!, $input: CloudBackendInput!) {
        createCloudBackend(tenantId: $tenantId, input: $input) {
          ${BACKEND_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((data) => data.createCloudBackend),
    );
  }

  updateBackend(id: string, input: CloudBackendUpdateInput): Observable<CloudBackend | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateCloudBackend: CloudBackend | null }>(`
      mutation UpdateCloudBackend($tenantId: UUID!, $id: UUID!, $input: CloudBackendUpdateInput!) {
        updateCloudBackend(tenantId: $tenantId, id: $id, input: $input) {
          ${BACKEND_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(
      map((data) => data.updateCloudBackend),
    );
  }

  deleteBackend(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCloudBackend: boolean }>(`
      mutation DeleteCloudBackend($tenantId: UUID!, $id: UUID!) {
        deleteCloudBackend(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(
      map((data) => data.deleteCloudBackend),
    );
  }

  // -- Connectivity testing ------------------------------------------------

  testConnectivity(id: string): Observable<ConnectivityTestResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ testCloudBackendConnectivity: ConnectivityTestResult }>(`
      mutation TestCloudBackendConnectivity($tenantId: UUID!, $id: UUID!) {
        testCloudBackendConnectivity(tenantId: $tenantId, id: $id) {
          success message checkedAt
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.testCloudBackendConnectivity),
    );
  }

  // -- IAM Mapping queries -------------------------------------------------

  listIAMMappings(backendId: string): Observable<CloudBackendIAMMapping[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloudBackendIamMappings: CloudBackendIAMMapping[] }>(`
      query CloudBackendIAMMappings($tenantId: UUID!, $backendId: UUID!) {
        cloudBackendIamMappings(tenantId: $tenantId, backendId: $backendId) {
          ${IAM_MAPPING_FIELDS}
        }
      }
    `, { tenantId, backendId }).pipe(
      map((data) => data.cloudBackendIamMappings),
    );
  }

  // -- IAM Mapping mutations -----------------------------------------------

  createIAMMapping(
    backendId: string,
    input: CloudBackendIAMMappingInput,
  ): Observable<CloudBackendIAMMapping | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCloudBackendIamMapping: CloudBackendIAMMapping | null }>(`
      mutation CreateCloudBackendIAMMapping(
        $tenantId: UUID!, $backendId: UUID!, $input: CloudBackendIAMMappingInput!
      ) {
        createCloudBackendIamMapping(
          tenantId: $tenantId, backendId: $backendId, input: $input
        ) {
          ${IAM_MAPPING_FIELDS}
        }
      }
    `, { tenantId, backendId, input }).pipe(
      map((data) => data.createCloudBackendIamMapping),
    );
  }

  updateIAMMapping(
    backendId: string,
    id: string,
    input: CloudBackendIAMMappingUpdateInput,
  ): Observable<CloudBackendIAMMapping | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateCloudBackendIamMapping: CloudBackendIAMMapping | null }>(`
      mutation UpdateCloudBackendIAMMapping(
        $tenantId: UUID!, $backendId: UUID!, $id: UUID!,
        $input: CloudBackendIAMMappingUpdateInput!
      ) {
        updateCloudBackendIamMapping(
          tenantId: $tenantId, backendId: $backendId, id: $id, input: $input
        ) {
          ${IAM_MAPPING_FIELDS}
        }
      }
    `, { tenantId, backendId, id, input }).pipe(
      map((data) => data.updateCloudBackendIamMapping),
    );
  }

  deleteIAMMapping(backendId: string, id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCloudBackendIamMapping: boolean }>(`
      mutation DeleteCloudBackendIAMMapping(
        $tenantId: UUID!, $backendId: UUID!, $id: UUID!
      ) {
        deleteCloudBackendIamMapping(
          tenantId: $tenantId, backendId: $backendId, id: $id
        )
      }
    `, { tenantId, backendId, id }).pipe(
      map((data) => data.deleteCloudBackendIamMapping),
    );
  }

  // -- Schema queries ------------------------------------------------------

  getCredentialSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloudCredentialSchema: Record<string, unknown> | null }>(`
      query CloudCredentialSchema($tenantId: UUID!, $providerName: String!) {
        cloudCredentialSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(
      map((data) => data.cloudCredentialSchema),
    );
  }

  getScopeSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloudScopeSchema: Record<string, unknown> | null }>(`
      query CloudScopeSchema($tenantId: UUID!, $providerName: String!) {
        cloudScopeSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(
      map((data) => data.cloudScopeSchema),
    );
  }

  // -- GraphQL helper ------------------------------------------------------

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
