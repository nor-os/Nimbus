/**
 * Overview: Service cluster GraphQL service — CRUD, slot management, blueprint parameters,
 *     and deployed stack queries.
 * Architecture: Core service layer for cluster data operations (Section 8)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD operations for blueprint clusters. All queries are tenant-scoped.
 *     CI assignment is not part of blueprints — it happens at deployment time.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  BlueprintParameterCreateInput,
  BlueprintParameterUpdateInput,
  ServiceCluster,
  ServiceClusterCreateInput,
  ServiceClusterList,
  ServiceClusterSlotCreateInput,
  ServiceClusterSlotUpdateInput,
  ServiceClusterUpdateInput,
  StackList,
} from '@shared/models/cluster.model';

// ── Field constants ─────────────────────────────────────────────────

const SLOT_FIELDS = `
  id clusterId name displayName description allowedCiClassIds
  semanticCategoryId semanticCategoryName semanticTypeId semanticTypeName
  minCount maxCount isRequired sortOrder
  createdAt updatedAt
`;

const PARAM_FIELDS = `
  id clusterId name displayName description
  parameterSchema defaultValue sourceType
  sourceSlotId sourceSlotName sourcePropertyPath
  isRequired sortOrder createdAt updatedAt
`;

const CLUSTER_FIELDS = `
  id tenantId name description clusterType
  architectureTopologyId topologyNodeId
  tags stackTagKey metadata
  slots { ${SLOT_FIELDS} }
  parameters { ${PARAM_FIELDS} }
  createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class ClusterService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Cluster CRUD ───────────────────────────────────────────────

  listClusters(filters?: {
    clusterType?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<ServiceClusterList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceClusters: ServiceClusterList }>(`
      query ServiceClusters(
        $tenantId: UUID!
        $clusterType: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        serviceClusters(
          tenantId: $tenantId
          clusterType: $clusterType
          search: $search
          offset: $offset
          limit: $limit
        ) {
          items { ${CLUSTER_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.serviceClusters),
    );
  }

  getCluster(id: string): Observable<ServiceCluster | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceCluster: ServiceCluster | null }>(`
      query ServiceCluster($tenantId: UUID!, $id: UUID!) {
        serviceCluster(tenantId: $tenantId, id: $id) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.serviceCluster),
    );
  }

  createCluster(input: ServiceClusterCreateInput): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceCluster: ServiceCluster }>(`
      mutation CreateServiceCluster($tenantId: UUID!, $input: ServiceClusterCreateInput!) {
        createServiceCluster(tenantId: $tenantId, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceCluster));
  }

  updateCluster(id: string, input: ServiceClusterUpdateInput): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateServiceCluster: ServiceCluster }>(`
      mutation UpdateServiceCluster($tenantId: UUID!, $id: UUID!, $input: ServiceClusterUpdateInput!) {
        updateServiceCluster(tenantId: $tenantId, id: $id, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateServiceCluster));
  }

  deleteCluster(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceCluster: boolean }>(`
      mutation DeleteServiceCluster($tenantId: UUID!, $id: UUID!) {
        deleteServiceCluster(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceCluster));
  }

  // ── Slot Management ────────────────────────────────────────────

  addSlot(clusterId: string, input: ServiceClusterSlotCreateInput): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addClusterSlot: ServiceCluster }>(`
      mutation AddClusterSlot($tenantId: UUID!, $clusterId: UUID!, $input: ServiceClusterSlotInput!) {
        addClusterSlot(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.addClusterSlot));
  }

  updateSlot(
    clusterId: string, slotId: string, input: ServiceClusterSlotUpdateInput
  ): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateClusterSlot: ServiceCluster }>(`
      mutation UpdateClusterSlot(
        $tenantId: UUID!, $clusterId: UUID!, $slotId: UUID!,
        $input: ServiceClusterSlotUpdateInput!
      ) {
        updateClusterSlot(tenantId: $tenantId, clusterId: $clusterId, slotId: $slotId, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, slotId, input }).pipe(map((d) => d.updateClusterSlot));
  }

  removeSlot(clusterId: string, slotId: string): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeClusterSlot: ServiceCluster }>(`
      mutation RemoveClusterSlot($tenantId: UUID!, $clusterId: UUID!, $slotId: UUID!) {
        removeClusterSlot(tenantId: $tenantId, clusterId: $clusterId, slotId: $slotId) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, slotId }).pipe(map((d) => d.removeClusterSlot));
  }

  // ── Blueprint Stacks ──────────────────────────────────────────

  getBlueprintStacks(blueprintId: string): Observable<StackList | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ blueprintStacks: StackList | null }>(`
      query BlueprintStacks($tenantId: UUID!, $blueprintId: UUID!) {
        blueprintStacks(tenantId: $tenantId, blueprintId: $blueprintId) {
          blueprintId blueprintName tagKey total
          stacks { tagValue ciCount activeCount plannedCount maintenanceCount }
        }
      }
    `, { tenantId, blueprintId }).pipe(map((d) => d.blueprintStacks));
  }

  // ── Blueprint Parameters ─────────────────────────────────────────

  syncParameters(clusterId: string): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ syncBlueprintParameters: ServiceCluster }>(`
      mutation SyncBlueprintParameters($tenantId: UUID!, $clusterId: UUID!) {
        syncBlueprintParameters(tenantId: $tenantId, clusterId: $clusterId) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.syncBlueprintParameters));
  }

  addParameter(clusterId: string, input: BlueprintParameterCreateInput): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addBlueprintParameter: ServiceCluster }>(`
      mutation AddBlueprintParameter($tenantId: UUID!, $clusterId: UUID!, $input: BlueprintParameterCreateInput!) {
        addBlueprintParameter(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.addBlueprintParameter));
  }

  updateParameter(
    clusterId: string, paramId: string, input: BlueprintParameterUpdateInput
  ): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateBlueprintParameter: ServiceCluster }>(`
      mutation UpdateBlueprintParameter(
        $tenantId: UUID!, $clusterId: UUID!, $paramId: UUID!,
        $input: BlueprintParameterUpdateInput!
      ) {
        updateBlueprintParameter(tenantId: $tenantId, clusterId: $clusterId, paramId: $paramId, input: $input) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, paramId, input }).pipe(map((d) => d.updateBlueprintParameter));
  }

  deleteParameter(clusterId: string, paramId: string): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteBlueprintParameter: ServiceCluster }>(`
      mutation DeleteBlueprintParameter($tenantId: UUID!, $clusterId: UUID!, $paramId: UUID!) {
        deleteBlueprintParameter(tenantId: $tenantId, clusterId: $clusterId, paramId: $paramId) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId, paramId }).pipe(map((d) => d.deleteBlueprintParameter));
  }

  // ── GraphQL helper ──────────────────────────────────────────────

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
