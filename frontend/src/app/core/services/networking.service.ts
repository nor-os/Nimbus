/**
 * Overview: Networking service — GraphQL queries and mutations for connectivity, peering, private endpoints, load balancers.
 * Architecture: Core service layer for managed networking entities (Section 6)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for LZ-level and per-environment networking entities.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  ConnectivityConfig,
  ConnectivityConfigInput,
  EnvironmentLoadBalancer,
  EnvironmentLoadBalancerInput,
  EnvironmentPrivateEndpoint,
  EnvironmentPrivateEndpointInput,
  PeeringConfig,
  PeeringConfigInput,
  PrivateEndpointPolicy,
  PrivateEndpointPolicyInput,
  SharedLoadBalancer,
  SharedLoadBalancerInput,
} from '@shared/models/networking.model';

const CONNECTIVITY_FIELDS = `
  id tenantId landingZoneId name description connectivityType providerType
  status config remoteConfig createdBy createdAt updatedAt
`;

const PEERING_FIELDS = `
  id tenantId landingZoneId environmentId name peeringType status
  hubConfig spokeConfig routingConfig createdBy createdAt updatedAt
`;

const PE_POLICY_FIELDS = `
  id tenantId landingZoneId name serviceName endpointType providerType
  config status createdBy createdAt updatedAt
`;

const ENV_PE_FIELDS = `
  id tenantId environmentId policyId serviceName endpointType
  config status cloudResourceId createdBy createdAt updatedAt
`;

const SHARED_LB_FIELDS = `
  id tenantId landingZoneId name lbType providerType
  config status cloudResourceId createdBy createdAt updatedAt
`;

const ENV_LB_FIELDS = `
  id tenantId environmentId sharedLbId name lbType
  config status cloudResourceId createdBy createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class NetworkingService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Connectivity ────────────────────────────────────────────────

  listConnectivityConfigs(landingZoneId: string): Observable<ConnectivityConfig[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ connectivityConfigs: ConnectivityConfig[] }>(`
      query ConnectivityConfigs($tenantId: UUID!, $landingZoneId: UUID!) {
        connectivityConfigs(tenantId: $tenantId, landingZoneId: $landingZoneId) {
          ${CONNECTIVITY_FIELDS}
        }
      }
    `, { tenantId, landingZoneId }).pipe(map(d => d.connectivityConfigs));
  }

  createConnectivityConfig(landingZoneId: string, input: ConnectivityConfigInput): Observable<ConnectivityConfig> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createConnectivityConfig: ConnectivityConfig }>(`
      mutation CreateConnectivityConfig($tenantId: UUID!, $landingZoneId: UUID!, $input: ConnectivityConfigInput!) {
        createConnectivityConfig(tenantId: $tenantId, landingZoneId: $landingZoneId, input: $input) {
          ${CONNECTIVITY_FIELDS}
        }
      }
    `, { tenantId, landingZoneId, input }).pipe(map(d => d.createConnectivityConfig));
  }

  deleteConnectivityConfig(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteConnectivityConfig: boolean }>(`
      mutation DeleteConnectivityConfig($tenantId: UUID!, $id: UUID!) {
        deleteConnectivityConfig(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deleteConnectivityConfig));
  }

  // ── Peering ─────────────────────────────────────────────────────

  listPeeringConfigs(landingZoneId: string): Observable<PeeringConfig[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ peeringConfigs: PeeringConfig[] }>(`
      query PeeringConfigs($tenantId: UUID!, $landingZoneId: UUID!) {
        peeringConfigs(tenantId: $tenantId, landingZoneId: $landingZoneId) {
          ${PEERING_FIELDS}
        }
      }
    `, { tenantId, landingZoneId }).pipe(map(d => d.peeringConfigs));
  }

  createPeeringConfig(landingZoneId: string, input: PeeringConfigInput): Observable<PeeringConfig> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPeeringConfig: PeeringConfig }>(`
      mutation CreatePeeringConfig($tenantId: UUID!, $landingZoneId: UUID!, $input: PeeringConfigInput!) {
        createPeeringConfig(tenantId: $tenantId, landingZoneId: $landingZoneId, input: $input) {
          ${PEERING_FIELDS}
        }
      }
    `, { tenantId, landingZoneId, input }).pipe(map(d => d.createPeeringConfig));
  }

  deletePeeringConfig(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePeeringConfig: boolean }>(`
      mutation DeletePeeringConfig($tenantId: UUID!, $id: UUID!) {
        deletePeeringConfig(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deletePeeringConfig));
  }

  // ── Private Endpoint Policies (LZ-level) ────────────────────────

  listPrivateEndpointPolicies(landingZoneId: string): Observable<PrivateEndpointPolicy[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ privateEndpointPolicies: PrivateEndpointPolicy[] }>(`
      query PrivateEndpointPolicies($tenantId: UUID!, $landingZoneId: UUID!) {
        privateEndpointPolicies(tenantId: $tenantId, landingZoneId: $landingZoneId) {
          ${PE_POLICY_FIELDS}
        }
      }
    `, { tenantId, landingZoneId }).pipe(map(d => d.privateEndpointPolicies));
  }

  createPrivateEndpointPolicy(landingZoneId: string, input: PrivateEndpointPolicyInput): Observable<PrivateEndpointPolicy> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPrivateEndpointPolicy: PrivateEndpointPolicy }>(`
      mutation CreatePrivateEndpointPolicy($tenantId: UUID!, $landingZoneId: UUID!, $input: PrivateEndpointPolicyInput!) {
        createPrivateEndpointPolicy(tenantId: $tenantId, landingZoneId: $landingZoneId, input: $input) {
          ${PE_POLICY_FIELDS}
        }
      }
    `, { tenantId, landingZoneId, input }).pipe(map(d => d.createPrivateEndpointPolicy));
  }

  deletePrivateEndpointPolicy(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePrivateEndpointPolicy: boolean }>(`
      mutation DeletePrivateEndpointPolicy($tenantId: UUID!, $id: UUID!) {
        deletePrivateEndpointPolicy(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deletePrivateEndpointPolicy));
  }

  // ── Environment Private Endpoints ──────────────────────────────

  listEnvironmentPrivateEndpoints(environmentId: string): Observable<EnvironmentPrivateEndpoint[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ environmentPrivateEndpoints: EnvironmentPrivateEndpoint[] }>(`
      query EnvironmentPrivateEndpoints($tenantId: UUID!, $environmentId: UUID!) {
        environmentPrivateEndpoints(tenantId: $tenantId, environmentId: $environmentId) {
          ${ENV_PE_FIELDS}
        }
      }
    `, { tenantId, environmentId }).pipe(map(d => d.environmentPrivateEndpoints));
  }

  createEnvironmentPrivateEndpoint(environmentId: string, input: EnvironmentPrivateEndpointInput): Observable<EnvironmentPrivateEndpoint> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEnvironmentPrivateEndpoint: EnvironmentPrivateEndpoint }>(`
      mutation CreateEnvironmentPrivateEndpoint($tenantId: UUID!, $environmentId: UUID!, $input: EnvironmentPrivateEndpointInput!) {
        createEnvironmentPrivateEndpoint(tenantId: $tenantId, environmentId: $environmentId, input: $input) {
          ${ENV_PE_FIELDS}
        }
      }
    `, { tenantId, environmentId, input }).pipe(map(d => d.createEnvironmentPrivateEndpoint));
  }

  deleteEnvironmentPrivateEndpoint(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEnvironmentPrivateEndpoint: boolean }>(`
      mutation DeleteEnvironmentPrivateEndpoint($tenantId: UUID!, $id: UUID!) {
        deleteEnvironmentPrivateEndpoint(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deleteEnvironmentPrivateEndpoint));
  }

  // ── Shared Load Balancers (LZ-level) ───────────────────────────

  listSharedLoadBalancers(landingZoneId: string): Observable<SharedLoadBalancer[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ sharedLoadBalancers: SharedLoadBalancer[] }>(`
      query SharedLoadBalancers($tenantId: UUID!, $landingZoneId: UUID!) {
        sharedLoadBalancers(tenantId: $tenantId, landingZoneId: $landingZoneId) {
          ${SHARED_LB_FIELDS}
        }
      }
    `, { tenantId, landingZoneId }).pipe(map(d => d.sharedLoadBalancers));
  }

  createSharedLoadBalancer(landingZoneId: string, input: SharedLoadBalancerInput): Observable<SharedLoadBalancer> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createSharedLoadBalancer: SharedLoadBalancer }>(`
      mutation CreateSharedLoadBalancer($tenantId: UUID!, $landingZoneId: UUID!, $input: SharedLoadBalancerInput!) {
        createSharedLoadBalancer(tenantId: $tenantId, landingZoneId: $landingZoneId, input: $input) {
          ${SHARED_LB_FIELDS}
        }
      }
    `, { tenantId, landingZoneId, input }).pipe(map(d => d.createSharedLoadBalancer));
  }

  deleteSharedLoadBalancer(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSharedLoadBalancer: boolean }>(`
      mutation DeleteSharedLoadBalancer($tenantId: UUID!, $id: UUID!) {
        deleteSharedLoadBalancer(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deleteSharedLoadBalancer));
  }

  // ── Environment Load Balancers ─────────────────────────────────

  listEnvironmentLoadBalancers(environmentId: string): Observable<EnvironmentLoadBalancer[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ environmentLoadBalancers: EnvironmentLoadBalancer[] }>(`
      query EnvironmentLoadBalancers($tenantId: UUID!, $environmentId: UUID!) {
        environmentLoadBalancers(tenantId: $tenantId, environmentId: $environmentId) {
          ${ENV_LB_FIELDS}
        }
      }
    `, { tenantId, environmentId }).pipe(map(d => d.environmentLoadBalancers));
  }

  createEnvironmentLoadBalancer(environmentId: string, input: EnvironmentLoadBalancerInput): Observable<EnvironmentLoadBalancer> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEnvironmentLoadBalancer: EnvironmentLoadBalancer }>(`
      mutation CreateEnvironmentLoadBalancer($tenantId: UUID!, $environmentId: UUID!, $input: EnvironmentLoadBalancerInput!) {
        createEnvironmentLoadBalancer(tenantId: $tenantId, environmentId: $environmentId, input: $input) {
          ${ENV_LB_FIELDS}
        }
      }
    `, { tenantId, environmentId, input }).pipe(map(d => d.createEnvironmentLoadBalancer));
  }

  deleteEnvironmentLoadBalancer(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEnvironmentLoadBalancer: boolean }>(`
      mutation DeleteEnvironmentLoadBalancer($tenantId: UUID!, $id: UUID!) {
        deleteEnvironmentLoadBalancer(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map(d => d.deleteEnvironmentLoadBalancer));
  }

  // ── GraphQL helper ─────────────────────────────────────────────

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
