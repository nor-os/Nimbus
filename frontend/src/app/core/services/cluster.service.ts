/**
 * Overview: Service cluster GraphQL service — CRUD, slot management, blueprint parameters,
 *     versioning, components, bindings, governance, workflows, instances, reservations.
 * Architecture: Core service layer for cluster data operations (Section 8)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD operations for blueprint clusters. All queries are tenant-scoped.
 *     Evolved to full stack blueprints with PaaS-grade infrastructure compositions.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  BlueprintComponentInput,
  BlueprintParameterCreateInput,
  BlueprintParameterUpdateInput,
  BlueprintReservationTemplate,
  ComponentReservationTemplate,
  ComponentReservationTemplateInput,
  CreateReservationInput,
  DeployStackInput,
  GovernanceInput,
  ReservationTemplateInput,
  ServiceCluster,
  ServiceClusterCreateInput,
  ServiceClusterList,
  ServiceClusterSlotCreateInput,
  ServiceClusterSlotUpdateInput,
  ServiceClusterUpdateInput,
  StackBlueprintComponent,
  StackBlueprintGovernance,
  StackBlueprintVersion,
  StackList,
  StackReservation,
  StackReservationList,
  StackRuntimeInstance,
  StackRuntimeInstanceList,
  StackVariableBinding,
  StackWorkflow,
  StackWorkflowInput,
  SyncPolicyInput,
  VariableBindingInput,
  ReservationSyncPolicy,
} from '@shared/models/cluster.model';

// ── Field constants ─────────────────────────────────────────────────

const SLOT_FIELDS = `
  id clusterId name displayName description allowedCiClassIds
  semanticCategoryId semanticCategoryName semanticTypeId semanticTypeName
  minCount maxCount isRequired sortOrder componentId defaultParameters dependsOn
  createdAt updatedAt
`;

const PARAM_FIELDS = `
  id clusterId name displayName description
  parameterSchema defaultValue sourceType
  sourceSlotId sourceSlotName sourcePropertyPath
  isRequired sortOrder createdAt updatedAt
`;

const COMPONENT_FIELDS = `
  id blueprintId componentId nodeId label description
  sortOrder isOptional defaultParameters dependsOn
  componentName componentVersion
  createdAt updatedAt
`;

const BINDING_FIELDS = `
  id blueprintId direction variableName
  targetNodeId targetParameter transformExpression
  createdAt updatedAt
`;

const CLUSTER_FIELDS = `
  id tenantId name description clusterType
  architectureTopologyId topologyNodeId
  tags stackTagKey metadata
  providerId category icon inputSchema outputSchema
  version isPublished isSystem displayName createdBy
  haConfigSchema haConfigDefaults drConfigSchema drConfigDefaults
  slots { ${SLOT_FIELDS} }
  parameters { ${PARAM_FIELDS} }
  blueprintComponents { ${COMPONENT_FIELDS} }
  variableBindings { ${BINDING_FIELDS} }
  reservationTemplate {
    id blueprintId reservationType resourcePercentage
    targetEnvironmentLabel targetProviderId rtoSeconds rpoSeconds
    autoCreateOnDeploy syncPoliciesTemplate createdAt updatedAt
  }
  createdAt updatedAt
`;

const INSTANCE_COMPONENT_FIELDS = `
  id stackInstanceId blueprintComponentId componentId componentVersion
  ciId deploymentId status resolvedParameters outputs pulumiStateUrl
  createdAt updatedAt
`;

const INSTANCE_FIELDS = `
  id blueprintId blueprintVersion tenantId environmentId name
  status inputValues outputValues componentStates healthStatus
  deployedBy deployedAt haConfig drConfig
  components { ${INSTANCE_COMPONENT_FIELDS} }
  createdAt updatedAt
`;

const SYNC_POLICY_FIELDS = `
  id reservationId sourceNodeId targetNodeId syncMethod
  syncIntervalSeconds syncWorkflowId lastSyncedAt syncLagSeconds
  createdAt updatedAt
`;

const RESERVATION_FIELDS = `
  id stackInstanceId tenantId reservationType
  targetEnvironmentId targetProviderId reservedResources
  rtoSeconds rpoSeconds status costPerHour
  lastTestedAt testResult
  syncPolicies { ${SYNC_POLICY_FIELDS} }
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
    category?: string;
    isPublished?: boolean;
    providerId?: string;
  }): Observable<ServiceClusterList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceClusters: ServiceClusterList }>(`
      query ServiceClusters(
        $tenantId: UUID!
        $clusterType: String
        $search: String
        $offset: Int
        $limit: Int
        $category: String
        $isPublished: Boolean
        $providerId: UUID
      ) {
        serviceClusters(
          tenantId: $tenantId
          clusterType: $clusterType
          search: $search
          offset: $offset
          limit: $limit
          category: $category
          isPublished: $isPublished
          providerId: $providerId
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

  // ── Blueprint Publishing ───────────────────────────────────────

  publishBlueprint(clusterId: string, changelog?: string): Observable<StackBlueprintVersion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishBlueprint: StackBlueprintVersion }>(`
      mutation PublishBlueprint($tenantId: UUID!, $clusterId: UUID!, $changelog: String) {
        publishBlueprint(tenantId: $tenantId, clusterId: $clusterId, changelog: $changelog) {
          id blueprintId version inputSchema outputSchema
          componentGraph variableBindings changelog publishedBy createdAt
        }
      }
    `, { tenantId, clusterId, changelog }).pipe(map((d) => d.publishBlueprint));
  }

  archiveBlueprint(clusterId: string): Observable<ServiceCluster> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveBlueprint: ServiceCluster }>(`
      mutation ArchiveBlueprint($tenantId: UUID!, $clusterId: UUID!) {
        archiveBlueprint(tenantId: $tenantId, clusterId: $clusterId) {
          ${CLUSTER_FIELDS}
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.archiveBlueprint));
  }

  listBlueprintVersions(clusterId: string): Observable<StackBlueprintVersion[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackBlueprintVersions: StackBlueprintVersion[] }>(`
      query StackBlueprintVersions($tenantId: UUID!, $clusterId: UUID!) {
        stackBlueprintVersions(tenantId: $tenantId, clusterId: $clusterId) {
          id blueprintId version inputSchema outputSchema
          componentGraph variableBindings changelog publishedBy createdAt
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.stackBlueprintVersions));
  }

  // ── Blueprint Components ───────────────────────────────────────

  addBlueprintComponent(clusterId: string, input: BlueprintComponentInput): Observable<StackBlueprintComponent> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addBlueprintComponent: StackBlueprintComponent }>(`
      mutation AddBlueprintComponent($tenantId: UUID!, $clusterId: UUID!, $input: BlueprintComponentInput!) {
        addBlueprintComponent(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          ${COMPONENT_FIELDS}
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.addBlueprintComponent));
  }

  removeBlueprintComponent(clusterId: string, componentId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeBlueprintComponent: boolean }>(`
      mutation RemoveBlueprintComponent($tenantId: UUID!, $clusterId: UUID!, $componentId: UUID!) {
        removeBlueprintComponent(tenantId: $tenantId, clusterId: $clusterId, componentId: $componentId)
      }
    `, { tenantId, clusterId, componentId }).pipe(map((d) => d.removeBlueprintComponent));
  }

  // ── Variable Bindings ──────────────────────────────────────────

  setVariableBindings(clusterId: string, bindings: VariableBindingInput[]): Observable<StackVariableBinding[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setVariableBindings: StackVariableBinding[] }>(`
      mutation SetVariableBindings($tenantId: UUID!, $clusterId: UUID!, $bindings: [VariableBindingInput!]!) {
        setVariableBindings(tenantId: $tenantId, clusterId: $clusterId, bindings: $bindings) {
          ${BINDING_FIELDS}
        }
      }
    `, { tenantId, clusterId, bindings }).pipe(map((d) => d.setVariableBindings));
  }

  // ── Governance ─────────────────────────────────────────────────

  setBlueprintGovernance(clusterId: string, input: GovernanceInput): Observable<StackBlueprintGovernance> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setBlueprintGovernance: StackBlueprintGovernance }>(`
      mutation SetBlueprintGovernance($tenantId: UUID!, $clusterId: UUID!, $input: GovernanceInput!) {
        setBlueprintGovernance(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          id blueprintId tenantId isAllowed parameterConstraints maxInstances createdAt updatedAt
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.setBlueprintGovernance));
  }

  listBlueprintGovernance(clusterId: string): Observable<StackBlueprintGovernance[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackBlueprintGovernance: StackBlueprintGovernance[] }>(`
      query StackBlueprintGovernance($tenantId: UUID!, $clusterId: UUID!) {
        stackBlueprintGovernance(tenantId: $tenantId, clusterId: $clusterId) {
          id blueprintId tenantId isAllowed parameterConstraints maxInstances createdAt updatedAt
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.stackBlueprintGovernance));
  }

  // ── Stack Workflows ────────────────────────────────────────────

  bindStackWorkflow(clusterId: string, input: StackWorkflowInput): Observable<StackWorkflow> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ bindStackWorkflow: StackWorkflow }>(`
      mutation BindStackWorkflow($tenantId: UUID!, $clusterId: UUID!, $input: StackWorkflowInput!) {
        bindStackWorkflow(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          id blueprintId workflowDefinitionId workflowKind name displayName
          isRequired triggerConditions sortOrder createdAt updatedAt
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.bindStackWorkflow));
  }

  listBlueprintWorkflows(clusterId: string): Observable<StackWorkflow[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackWorkflows: StackWorkflow[] }>(`
      query StackWorkflows($tenantId: UUID!, $clusterId: UUID!) {
        stackWorkflows(tenantId: $tenantId, clusterId: $clusterId) {
          id blueprintId workflowDefinitionId workflowKind name displayName
          isRequired triggerConditions sortOrder createdAt updatedAt
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.stackWorkflows));
  }

  provisionStackWorkflows(clusterId: string): Observable<StackWorkflow[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ provisionStackWorkflows: StackWorkflow[] }>(`
      mutation ProvisionStackWorkflows($tenantId: UUID!, $clusterId: UUID!) {
        provisionStackWorkflows(tenantId: $tenantId, clusterId: $clusterId) {
          id blueprintId workflowDefinitionId workflowKind name displayName
          isRequired triggerConditions sortOrder createdAt updatedAt
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.provisionStackWorkflows));
  }

  resetStackWorkflow(clusterId: string, workflowId: string): Observable<StackWorkflow> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ resetStackWorkflow: StackWorkflow }>(`
      mutation ResetStackWorkflow($tenantId: UUID!, $clusterId: UUID!, $workflowId: UUID!) {
        resetStackWorkflow(tenantId: $tenantId, clusterId: $clusterId, workflowId: $workflowId) {
          id blueprintId workflowDefinitionId workflowKind name displayName
          isRequired triggerConditions sortOrder createdAt updatedAt
        }
      }
    `, { tenantId, clusterId, workflowId }).pipe(map((d) => d.resetStackWorkflow));
  }

  unbindStackWorkflow(clusterId: string, workflowId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ unbindStackWorkflow: boolean }>(`
      mutation UnbindStackWorkflow($tenantId: UUID!, $clusterId: UUID!, $workflowId: UUID!) {
        unbindStackWorkflow(tenantId: $tenantId, clusterId: $clusterId, workflowId: $workflowId)
      }
    `, { tenantId, clusterId, workflowId }).pipe(map((d) => d.unbindStackWorkflow));
  }

  // ── Stack Instances ────────────────────────────────────────────

  deployStack(input: DeployStackInput): Observable<StackRuntimeInstance> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deployStack: StackRuntimeInstance }>(`
      mutation DeployStack($tenantId: UUID!, $input: DeployStackInput!) {
        deployStack(tenantId: $tenantId, input: $input) {
          ${INSTANCE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.deployStack));
  }

  listStackInstances(filters?: {
    blueprintId?: string;
    environmentId?: string;
    status?: string;
    offset?: number;
    limit?: number;
  }): Observable<StackRuntimeInstanceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackInstances: StackRuntimeInstanceList }>(`
      query StackInstances(
        $tenantId: UUID!
        $blueprintId: UUID
        $environmentId: UUID
        $status: String
        $offset: Int
        $limit: Int
      ) {
        stackInstances(
          tenantId: $tenantId
          blueprintId: $blueprintId
          environmentId: $environmentId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          items { ${INSTANCE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(map((d) => d.stackInstances));
  }

  getStackInstance(id: string): Observable<StackRuntimeInstance | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackInstance: StackRuntimeInstance | null }>(`
      query StackInstance($tenantId: UUID!, $id: UUID!) {
        stackInstance(tenantId: $tenantId, id: $id) {
          ${INSTANCE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.stackInstance));
  }

  decommissionStack(id: string): Observable<StackRuntimeInstance> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ decommissionStack: StackRuntimeInstance }>(`
      mutation DecommissionStack($tenantId: UUID!, $id: UUID!) {
        decommissionStack(tenantId: $tenantId, id: $id) {
          ${INSTANCE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.decommissionStack));
  }

  // ── Reservation Templates ──────────────────────────────────────

  setReservationTemplate(clusterId: string, input: ReservationTemplateInput): Observable<BlueprintReservationTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setReservationTemplate: BlueprintReservationTemplate }>(`
      mutation SetReservationTemplate($tenantId: UUID!, $clusterId: UUID!, $input: ReservationTemplateInput!) {
        setReservationTemplate(tenantId: $tenantId, clusterId: $clusterId, input: $input) {
          id blueprintId reservationType resourcePercentage
          targetEnvironmentLabel targetProviderId rtoSeconds rpoSeconds
          autoCreateOnDeploy syncPoliciesTemplate createdAt updatedAt
        }
      }
    `, { tenantId, clusterId, input }).pipe(map((d) => d.setReservationTemplate));
  }

  removeReservationTemplate(clusterId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeReservationTemplate: boolean }>(`
      mutation RemoveReservationTemplate($tenantId: UUID!, $clusterId: UUID!) {
        removeReservationTemplate(tenantId: $tenantId, clusterId: $clusterId)
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.removeReservationTemplate));
  }

  // ── Component Reservation Templates ────────────────────────────

  listComponentReservationTemplates(clusterId: string): Observable<ComponentReservationTemplate[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ componentReservationTemplates: ComponentReservationTemplate[] }>(`
      query ComponentReservationTemplates($tenantId: UUID!, $clusterId: UUID!) {
        componentReservationTemplates(tenantId: $tenantId, clusterId: $clusterId) {
          id blueprintComponentId reservationType resourcePercentage
          targetEnvironmentLabel targetProviderId rtoSeconds rpoSeconds
          autoCreateOnDeploy syncPoliciesTemplate createdAt updatedAt
        }
      }
    `, { tenantId, clusterId }).pipe(map((d) => d.componentReservationTemplates));
  }

  setComponentReservationTemplate(
    blueprintComponentId: string, input: ComponentReservationTemplateInput
  ): Observable<ComponentReservationTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setComponentReservationTemplate: ComponentReservationTemplate }>(`
      mutation SetComponentReservationTemplate(
        $tenantId: UUID!, $blueprintComponentId: UUID!, $input: ComponentReservationTemplateInput!
      ) {
        setComponentReservationTemplate(
          tenantId: $tenantId, blueprintComponentId: $blueprintComponentId, input: $input
        ) {
          id blueprintComponentId reservationType resourcePercentage
          targetEnvironmentLabel targetProviderId rtoSeconds rpoSeconds
          autoCreateOnDeploy syncPoliciesTemplate createdAt updatedAt
        }
      }
    `, { tenantId, blueprintComponentId, input }).pipe(map((d) => d.setComponentReservationTemplate));
  }

  removeComponentReservationTemplate(blueprintComponentId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeComponentReservationTemplate: boolean }>(`
      mutation RemoveComponentReservationTemplate($tenantId: UUID!, $blueprintComponentId: UUID!) {
        removeComponentReservationTemplate(tenantId: $tenantId, blueprintComponentId: $blueprintComponentId)
      }
    `, { tenantId, blueprintComponentId }).pipe(map((d) => d.removeComponentReservationTemplate));
  }

  // ── Reservations ───────────────────────────────────────────────

  createReservation(input: CreateReservationInput): Observable<StackReservation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createReservation: StackReservation }>(`
      mutation CreateReservation($tenantId: UUID!, $input: CreateReservationInput!) {
        createReservation(tenantId: $tenantId, input: $input) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createReservation));
  }

  listReservations(filters?: {
    stackInstanceId?: string;
    status?: string;
    offset?: number;
    limit?: number;
  }): Observable<StackReservationList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackReservations: StackReservationList }>(`
      query StackReservations(
        $tenantId: UUID!
        $stackInstanceId: UUID
        $status: String
        $offset: Int
        $limit: Int
      ) {
        stackReservations(
          tenantId: $tenantId
          stackInstanceId: $stackInstanceId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          items { ${RESERVATION_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(map((d) => d.stackReservations));
  }

  getReservation(id: string): Observable<StackReservation | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ stackReservation: StackReservation | null }>(`
      query StackReservation($tenantId: UUID!, $id: UUID!) {
        stackReservation(tenantId: $tenantId, id: $id) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.stackReservation));
  }

  claimReservation(id: string): Observable<StackReservation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ claimReservation: StackReservation }>(`
      mutation ClaimReservation($tenantId: UUID!, $id: UUID!) {
        claimReservation(tenantId: $tenantId, id: $id) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.claimReservation));
  }

  releaseReservation(id: string): Observable<StackReservation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ releaseReservation: StackReservation }>(`
      mutation ReleaseReservation($tenantId: UUID!, $id: UUID!) {
        releaseReservation(tenantId: $tenantId, id: $id) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.releaseReservation));
  }

  testFailover(id: string, testResult: string): Observable<StackReservation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ testFailover: StackReservation }>(`
      mutation TestFailover($tenantId: UUID!, $id: UUID!, $testResult: String!) {
        testFailover(tenantId: $tenantId, id: $id, testResult: $testResult) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, id, testResult }).pipe(map((d) => d.testFailover));
  }

  addSyncPolicy(reservationId: string, input: SyncPolicyInput): Observable<ReservationSyncPolicy> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addSyncPolicy: ReservationSyncPolicy }>(`
      mutation AddSyncPolicy($tenantId: UUID!, $reservationId: UUID!, $input: SyncPolicyInput!) {
        addSyncPolicy(tenantId: $tenantId, reservationId: $reservationId, input: $input) {
          ${SYNC_POLICY_FIELDS}
        }
      }
    `, { tenantId, reservationId, input }).pipe(map((d) => d.addSyncPolicy));
  }

  removeSyncPolicy(reservationId: string, policyId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeSyncPolicy: boolean }>(`
      mutation RemoveSyncPolicy($tenantId: UUID!, $reservationId: UUID!, $policyId: UUID!) {
        removeSyncPolicy(tenantId: $tenantId, reservationId: $reservationId, policyId: $policyId)
      }
    `, { tenantId, reservationId, policyId }).pipe(map((d) => d.removeSyncPolicy));
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
