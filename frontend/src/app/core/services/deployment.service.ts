/**
 * Overview: Deployment service — GraphQL queries and mutations for topology-to-environment deployments.
 * Architecture: Core service layer for deployment data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Deployment CRUD, tenant-scoped queries, environment filtering
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import { Deployment, DeploymentCI, ResolvedParametersPreview } from '@shared/models/deployment.model';

const DEPLOYMENT_CI_FIELDS = `id deploymentId ciId componentId topologyNodeId resolverOutputs createdAt`;
const DEPLOYMENT_FIELDS = `id tenantId environmentId topologyId name description status parameters resolvedParameters resolutionStatus resolutionError deployedBy deployedAt createdAt updatedAt cis { ${DEPLOYMENT_CI_FIELDS} }`;

@Injectable({ providedIn: 'root' })
export class DeploymentService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  listDeployments(environmentId?: string): Observable<Deployment[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deployments: Deployment[] }>(`
      query Deployments($tenantId: UUID!, $environmentId: UUID) {
        deployments(tenantId: $tenantId, environmentId: $environmentId) {
          ${DEPLOYMENT_FIELDS}
        }
      }
    `, { tenantId, environmentId }).pipe(map(d => d.deployments));
  }

  getDeployment(id: string): Observable<Deployment | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deployment: Deployment | null }>(`
      query Deployment($tenantId: UUID!, $deploymentId: UUID!) {
        deployment(tenantId: $tenantId, deploymentId: $deploymentId) {
          ${DEPLOYMENT_FIELDS}
        }
      }
    `, { tenantId, deploymentId: id }).pipe(map(d => d.deployment));
  }

  createDeployment(input: {
    environmentId: string;
    topologyId: string;
    name: string;
    description?: string | null;
    parameters?: Record<string, unknown> | null;
  }): Observable<Deployment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createDeployment: Deployment }>(`
      mutation CreateDeployment($tenantId: UUID!, $input: DeploymentCreateInput!) {
        createDeployment(tenantId: $tenantId, input: $input) {
          ${DEPLOYMENT_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createDeployment));
  }

  updateDeployment(id: string, input: {
    name?: string | null;
    description?: string | null;
    status?: string | null;
    parameters?: Record<string, unknown> | null;
  }): Observable<Deployment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateDeployment: Deployment }>(`
      mutation UpdateDeployment($tenantId: UUID!, $deploymentId: UUID!, $input: DeploymentUpdateInput!) {
        updateDeployment(tenantId: $tenantId, deploymentId: $deploymentId, input: $input) {
          ${DEPLOYMENT_FIELDS}
        }
      }
    `, { tenantId, deploymentId: id, input }).pipe(map(d => d.updateDeployment));
  }

  deleteDeployment(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteDeployment: boolean }>(`
      mutation DeleteDeployment($tenantId: UUID!, $deploymentId: UUID!) {
        deleteDeployment(tenantId: $tenantId, deploymentId: $deploymentId)
      }
    `, { tenantId, deploymentId: id }).pipe(map(d => d.deleteDeployment));
  }

  executeDeployment(deploymentId: string): Observable<Deployment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ executeDeployment: Deployment }>(`
      mutation ExecuteDeployment($tenantId: UUID!, $deploymentId: UUID!) {
        executeDeployment(tenantId: $tenantId, deploymentId: $deploymentId) {
          ${DEPLOYMENT_FIELDS}
        }
      }
    `, { tenantId, deploymentId }).pipe(map(d => d.executeDeployment));
  }

  getDeploymentCis(deploymentId: string): Observable<DeploymentCI[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deploymentCis: DeploymentCI[] }>(`
      query DeploymentCis($tenantId: UUID!, $deploymentId: UUID!) {
        deploymentCis(tenantId: $tenantId, deploymentId: $deploymentId) {
          ${DEPLOYMENT_CI_FIELDS}
        }
      }
    `, { tenantId, deploymentId }).pipe(map(d => d.deploymentCis));
  }

  previewResolvedParameters(input: {
    componentId: string;
    environmentId?: string | null;
    landingZoneId?: string | null;
    userParams?: Record<string, unknown> | null;
  }): Observable<ResolvedParametersPreview> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ previewResolvedParameters: ResolvedParametersPreview }>(`
      mutation PreviewResolvedParameters($tenantId: UUID!, $input: ResolveParametersInput!) {
        previewResolvedParameters(tenantId: $tenantId, input: $input) {
          parameters
          details { key value source }
        }
      }
    `, { tenantId, input }).pipe(map(d => d.previewResolvedParameters));
  }

  // ── Private GraphQL Helper ─────────────────────────────────────

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
