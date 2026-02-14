/**
 * Overview: Architecture service — GraphQL queries and mutations for topology management.
 * Architecture: Core service layer for architecture planner data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD, publish, clone, export/import, template management, graph validation
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  ArchitectureTopology,
  DeploymentOrder,
  ResolvedParameter,
  ResolutionPreview,
  TopologyCreateInput,
  TopologyExportResult,
  TopologyImportInput,
  TopologyUpdateInput,
  TopologyValidationResult,
} from '@shared/models/architecture.model';

const TOPOLOGY_FIELDS = `
  id tenantId name description graph status version
  isTemplate isSystem tags createdBy createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class ArchitectureService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  listTopologies(filters?: {
    status?: string;
    isTemplate?: boolean;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<ArchitectureTopology[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ topologies: ArchitectureTopology[] }>(`
      query Topologies(
        $tenantId: UUID!
        $status: String
        $isTemplate: Boolean
        $search: String
        $offset: Int
        $limit: Int
      ) {
        topologies(
          tenantId: $tenantId
          status: $status
          isTemplate: $isTemplate
          search: $search
          offset: $offset
          limit: $limit
        ) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.topologies));
  }

  getTopology(id: string): Observable<ArchitectureTopology | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ topology: ArchitectureTopology | null }>(`
      query Topology($tenantId: UUID!, $topologyId: UUID!) {
        topology(tenantId: $tenantId, topologyId: $topologyId) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId: id }).pipe(map(d => d.topology));
  }

  getTopologyVersions(name: string): Observable<ArchitectureTopology[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ topologyVersions: ArchitectureTopology[] }>(`
      query TopologyVersions($tenantId: UUID!, $name: String!) {
        topologyVersions(tenantId: $tenantId, name: $name) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, name }).pipe(map(d => d.topologyVersions));
  }

  createTopology(input: TopologyCreateInput): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTopology: ArchitectureTopology }>(`
      mutation CreateTopology($tenantId: UUID!, $input: TopologyCreateInput!) {
        createTopology(tenantId: $tenantId, input: $input) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createTopology));
  }

  updateTopology(id: string, input: TopologyUpdateInput): Observable<ArchitectureTopology | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateTopology: ArchitectureTopology | null }>(`
      mutation UpdateTopology($tenantId: UUID!, $topologyId: UUID!, $input: TopologyUpdateInput!) {
        updateTopology(tenantId: $tenantId, topologyId: $topologyId, input: $input) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId: id, input }).pipe(map(d => d.updateTopology));
  }

  publishTopology(id: string): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishTopology: ArchitectureTopology }>(`
      mutation PublishTopology($tenantId: UUID!, $topologyId: UUID!) {
        publishTopology(tenantId: $tenantId, topologyId: $topologyId) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId: id }).pipe(map(d => d.publishTopology));
  }

  archiveTopology(id: string): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveTopology: ArchitectureTopology }>(`
      mutation ArchiveTopology($tenantId: UUID!, $topologyId: UUID!) {
        archiveTopology(tenantId: $tenantId, topologyId: $topologyId) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId: id }).pipe(map(d => d.archiveTopology));
  }

  cloneTopology(id: string): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneTopology: ArchitectureTopology }>(`
      mutation CloneTopology($tenantId: UUID!, $topologyId: UUID!) {
        cloneTopology(tenantId: $tenantId, topologyId: $topologyId) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId: id }).pipe(map(d => d.cloneTopology));
  }

  deleteTopology(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTopology: boolean }>(`
      mutation DeleteTopology($tenantId: UUID!, $topologyId: UUID!) {
        deleteTopology(tenantId: $tenantId, topologyId: $topologyId)
      }
    `, { tenantId, topologyId: id }).pipe(map(d => d.deleteTopology));
  }

  exportTopology(id: string, format: string = 'json'): Observable<TopologyExportResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ exportTopology: TopologyExportResult }>(`
      mutation ExportTopology($tenantId: UUID!, $topologyId: UUID!, $format: String!) {
        exportTopology(tenantId: $tenantId, topologyId: $topologyId, format: $format) {
          data format
        }
      }
    `, { tenantId, topologyId: id, format }).pipe(map(d => d.exportTopology));
  }

  importTopology(input: TopologyImportInput): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ importTopology: ArchitectureTopology }>(`
      mutation ImportTopology($tenantId: UUID!, $input: TopologyImportInput!) {
        importTopology(tenantId: $tenantId, input: $input) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.importTopology));
  }

  validateGraph(graph: Record<string, unknown>): Observable<TopologyValidationResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ validateTopologyGraph: TopologyValidationResult }>(`
      query ValidateTopologyGraph($tenantId: UUID!, $graph: JSON!) {
        validateTopologyGraph(tenantId: $tenantId, graph: $graph) {
          valid
          errors { nodeId message severity }
          warnings { nodeId message severity }
        }
      }
    `, { tenantId, graph }).pipe(map(d => d.validateTopologyGraph));
  }

  listTemplates(filters?: {
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<ArchitectureTopology[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ topologyTemplates: ArchitectureTopology[] }>(`
      query TopologyTemplates(
        $tenantId: UUID!
        $search: String
        $offset: Int
        $limit: Int
      ) {
        topologyTemplates(
          tenantId: $tenantId
          search: $search
          offset: $offset
          limit: $limit
        ) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.topologyTemplates));
  }

  createTemplate(topologyId: string): Observable<ArchitectureTopology> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTopologyTemplate: ArchitectureTopology }>(`
      mutation CreateTopologyTemplate($tenantId: UUID!, $topologyId: UUID!) {
        createTopologyTemplate(tenantId: $tenantId, topologyId: $topologyId) {
          ${TOPOLOGY_FIELDS}
        }
      }
    `, { tenantId, topologyId }).pipe(map(d => d.createTopologyTemplate));
  }

  // ── Resolution Queries ────────────────────────────────────────

  resolveStackParameters(topologyId: string, stackId: string): Observable<ResolvedParameter[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ resolveStackParameters: ResolvedParameter[] }>(`
      query ResolveStackParameters($tenantId: UUID!, $topologyId: UUID!, $stackId: String!) {
        resolveStackParameters(tenantId: $tenantId, topologyId: $topologyId, stackId: $stackId) {
          name displayName value source isRequired tagKey
        }
      }
    `, { tenantId, topologyId, stackId }).pipe(map(d => d.resolveStackParameters));
  }

  previewResolution(topologyId: string): Observable<ResolutionPreview> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ previewTopologyResolution: ResolutionPreview }>(`
      query PreviewTopologyResolution($tenantId: UUID!, $topologyId: UUID!) {
        previewTopologyResolution(tenantId: $tenantId, topologyId: $topologyId) {
          topologyId
          allComplete
          totalUnresolved
          deploymentOrder
          stacks {
            stackId stackLabel blueprintId isComplete unresolvedCount
            parameters { name displayName value source isRequired tagKey }
          }
        }
      }
    `, { tenantId, topologyId }).pipe(map(d => d.previewTopologyResolution));
  }

  getDeploymentOrder(topologyId: string): Observable<DeploymentOrder> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ topologyDeploymentOrder: DeploymentOrder }>(`
      query TopologyDeploymentOrder($tenantId: UUID!, $topologyId: UUID!) {
        topologyDeploymentOrder(tenantId: $tenantId, topologyId: $topologyId) {
          groups
        }
      }
    `, { tenantId, topologyId }).pipe(map(d => d.topologyDeploymentOrder));
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
