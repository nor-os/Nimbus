/**
 * Overview: Component service — GraphQL queries and mutations for components, resolvers, and governance.
 * Architecture: Core service layer for component framework (Section 11)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for components, version management, publish workflow, resolver configs, governance
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  Component,
  ComponentCreateInput,
  ComponentGovernance,
  ComponentOperation,
  ComponentOperationCreateInput,
  ComponentOperationUpdateInput,
  ComponentUpdateInput,
  ComponentVersion,
  Resolver,
  ResolverConfiguration,
  ResolverDefinitionCreateInput,
  ResolverDefinitionUpdateInput,
} from '@shared/models/component.model';

const VERSION_FIELDS = `id componentId version code inputSchema outputSchema resolverBindings changelog publishedAt publishedBy`;
const GOVERNANCE_FIELDS = `id componentId tenantId isAllowed parameterConstraints maxInstances createdAt updatedAt`;
const OPERATION_FIELDS = `id componentId name displayName description inputSchema outputSchema workflowDefinitionId workflowDefinitionName isDestructive requiresApproval estimatedDowntime sortOrder createdAt updatedAt`;
const COMPONENT_FIELDS = `id tenantId providerId semanticTypeId name displayName description language code inputSchema outputSchema resolverBindings version isPublished isSystem upgradeWorkflowId createdBy createdAt updatedAt providerName semanticTypeName versions { ${VERSION_FIELDS} } governanceRules { ${GOVERNANCE_FIELDS} } operations { ${OPERATION_FIELDS} }`;
const RESOLVER_FIELDS = `id resolverType displayName description inputSchema outputSchema handlerClass isSystem instanceConfigSchema code category supportsRelease supportsUpdate compatibleProviderIds`;
const RESOLVER_CONFIG_FIELDS = `id resolverId resolverType landingZoneId environmentId config createdAt updatedAt`;

@Injectable({ providedIn: 'root' })
export class ComponentService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Components ────────────────────────────────────────────────────

  listComponents(filters?: {
    providerId?: string;
    semanticTypeId?: string;
    publishedOnly?: boolean;
    search?: string;
    offset?: number;
    limit?: number;
    providerMode?: boolean;
  }): Observable<Component[]> {
    const { providerMode, ...rest } = filters || {};
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ components: Component[] }>(`
      query Components(
        $tenantId: UUID
        $providerId: UUID
        $semanticTypeId: UUID
        $publishedOnly: Boolean
        $search: String
        $offset: Int
        $limit: Int
      ) {
        components(
          tenantId: $tenantId
          providerId: $providerId
          semanticTypeId: $semanticTypeId
          publishedOnly: $publishedOnly
          search: $search
          offset: $offset
          limit: $limit
        ) { ${COMPONENT_FIELDS} }
      }
    `, { tenantId, ...rest }).pipe(map(d => d.components));
  }

  getComponent(componentId: string, providerMode = false): Observable<Component> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ component: Component }>(`
      query Component($tenantId: UUID, $componentId: UUID!) {
        component(tenantId: $tenantId, componentId: $componentId) {
          ${COMPONENT_FIELDS}
        }
      }
    `, { tenantId, componentId }).pipe(map(d => d.component));
  }

  createComponent(input: ComponentCreateInput, providerMode = false): Observable<Component> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ createComponent: Component }>(`
      mutation CreateComponent($tenantId: UUID, $input: ComponentCreateInput!) {
        createComponent(tenantId: $tenantId, input: $input) {
          ${COMPONENT_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createComponent));
  }

  updateComponent(componentId: string, input: ComponentUpdateInput, providerMode = false): Observable<Component> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ updateComponent: Component }>(`
      mutation UpdateComponent($tenantId: UUID, $componentId: UUID!, $input: ComponentUpdateInput!) {
        updateComponent(tenantId: $tenantId, componentId: $componentId, input: $input) {
          ${COMPONENT_FIELDS}
        }
      }
    `, { tenantId, componentId, input }).pipe(map(d => d.updateComponent));
  }

  publishComponent(componentId: string, changelog?: string, providerMode = false): Observable<Component> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ publishComponent: Component }>(`
      mutation PublishComponent($tenantId: UUID, $componentId: UUID!, $input: ComponentPublishInput!) {
        publishComponent(tenantId: $tenantId, componentId: $componentId, input: $input) {
          ${COMPONENT_FIELDS}
        }
      }
    `, { tenantId, componentId, input: { changelog } }).pipe(map(d => d.publishComponent));
  }

  deleteComponent(componentId: string, providerMode = false): Observable<boolean> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ deleteComponent: boolean }>(`
      mutation DeleteComponent($tenantId: UUID, $componentId: UUID!) {
        deleteComponent(tenantId: $tenantId, componentId: $componentId)
      }
    `, { tenantId, componentId }).pipe(map(d => d.deleteComponent));
  }

  getVersionHistory(componentId: string): Observable<ComponentVersion[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ componentVersions: ComponentVersion[] }>(`
      query ComponentVersions($tenantId: UUID!, $componentId: UUID!) {
        componentVersions(tenantId: $tenantId, componentId: $componentId) {
          ${VERSION_FIELDS}
        }
      }
    `, { tenantId, componentId }).pipe(map(d => d.componentVersions));
  }

  // ── Resolvers ─────────────────────────────────────────────────────

  listResolvers(): Observable<Resolver[]> {
    return this.gql<{ resolvers: Resolver[] }>(`
      query Resolvers {
        resolvers { ${RESOLVER_FIELDS} }
      }
    `).pipe(map(d => d.resolvers));
  }

  listResolverConfigurations(
    landingZoneId?: string,
    environmentId?: string,
  ): Observable<ResolverConfiguration[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ resolverConfigurations: ResolverConfiguration[] }>(`
      query ResolverConfigurations($tenantId: UUID!, $landingZoneId: UUID, $environmentId: UUID) {
        resolverConfigurations(tenantId: $tenantId, landingZoneId: $landingZoneId, environmentId: $environmentId) {
          ${RESOLVER_CONFIG_FIELDS}
        }
      }
    `, { tenantId, landingZoneId, environmentId }).pipe(map(d => d.resolverConfigurations));
  }

  setResolverConfiguration(input: {
    resolverId: string;
    config: Record<string, unknown>;
    landingZoneId?: string;
    environmentId?: string;
  }): Observable<ResolverConfiguration> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setResolverConfiguration: ResolverConfiguration }>(`
      mutation SetResolverConfiguration($tenantId: UUID!, $input: ResolverConfigurationInput!) {
        setResolverConfiguration(tenantId: $tenantId, input: $input) {
          ${RESOLVER_CONFIG_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.setResolverConfiguration));
  }

  deleteResolverConfiguration(configurationId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteResolverConfiguration: boolean }>(`
      mutation DeleteResolverConfiguration($tenantId: UUID!, $configurationId: UUID!) {
        deleteResolverConfiguration(tenantId: $tenantId, configurationId: $configurationId)
      }
    `, { tenantId, configurationId }).pipe(map(d => d.deleteResolverConfiguration));
  }

  // ── Resolver Definitions ────────────────────────────────────────

  listResolverDefinitions(providerId?: string): Observable<Resolver[]> {
    return this.gql<{ resolverDefinitions: Resolver[] }>(`
      query ResolverDefinitions($providerId: UUID) {
        resolverDefinitions(providerId: $providerId) { ${RESOLVER_FIELDS} }
      }
    `, { providerId }).pipe(map(d => d.resolverDefinitions));
  }

  getResolverDefinition(resolverId: string): Observable<Resolver | null> {
    return this.gql<{ resolverDefinition: Resolver | null }>(`
      query ResolverDefinition($resolverId: UUID!) {
        resolverDefinition(resolverId: $resolverId) { ${RESOLVER_FIELDS} }
      }
    `, { resolverId }).pipe(map(d => d.resolverDefinition));
  }

  createResolverDefinition(input: ResolverDefinitionCreateInput): Observable<Resolver> {
    return this.gql<{ createResolverDefinition: Resolver }>(`
      mutation CreateResolverDefinition($input: ResolverDefinitionCreateInput!) {
        createResolverDefinition(input: $input) { ${RESOLVER_FIELDS} }
      }
    `, { input }).pipe(map(d => d.createResolverDefinition));
  }

  updateResolverDefinition(resolverId: string, input: ResolverDefinitionUpdateInput): Observable<Resolver> {
    return this.gql<{ updateResolverDefinition: Resolver }>(`
      mutation UpdateResolverDefinition($resolverId: UUID!, $input: ResolverDefinitionUpdateInput!) {
        updateResolverDefinition(resolverId: $resolverId, input: $input) { ${RESOLVER_FIELDS} }
      }
    `, { resolverId, input }).pipe(map(d => d.updateResolverDefinition));
  }

  deleteResolverDefinition(resolverId: string): Observable<boolean> {
    return this.gql<{ deleteResolverDefinition: boolean }>(`
      mutation DeleteResolverDefinition($resolverId: UUID!) {
        deleteResolverDefinition(resolverId: $resolverId)
      }
    `, { resolverId }).pipe(map(d => d.deleteResolverDefinition));
  }

  suggestResolversForField(fieldType: string, providerId?: string): Observable<Array<{
    resolver_id: string;
    resolver_type: string;
    display_name: string;
    matching_fields: string[];
  }>> {
    return this.gql<{ suggestResolversForField: Array<Record<string, unknown>> }>(`
      query SuggestResolvers($fieldType: String!, $providerId: UUID) {
        suggestResolversForField(fieldType: $fieldType, providerId: $providerId)
      }
    `, { fieldType, providerId }).pipe(map(d => d.suggestResolversForField as Array<{
      resolver_id: string;
      resolver_type: string;
      display_name: string;
      matching_fields: string[];
    }>));
  }

  validateResolverBindings(componentId: string): Observable<string[]> {
    return this.gql<{ validateResolverBindings: string[] }>(`
      query ValidateBindings($componentId: UUID!) {
        validateResolverBindings(componentId: $componentId)
      }
    `, { componentId }).pipe(map(d => d.validateResolverBindings));
  }

  // ── Governance ────────────────────────────────────────────────────

  listGovernance(): Observable<ComponentGovernance[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ componentGovernance: ComponentGovernance[] }>(`
      query ComponentGovernance($tenantId: UUID!) {
        componentGovernance(tenantId: $tenantId) {
          ${GOVERNANCE_FIELDS}
        }
      }
    `, { tenantId }).pipe(map(d => d.componentGovernance));
  }

  setGovernance(input: {
    componentId: string;
    tenantId: string;
    isAllowed: boolean;
    parameterConstraints?: Record<string, unknown>;
    maxInstances?: number;
  }): Observable<ComponentGovernance> {
    return this.gql<{ setComponentGovernance: ComponentGovernance }>(`
      mutation SetComponentGovernance($input: GovernanceInput!) {
        setComponentGovernance(input: $input) {
          ${GOVERNANCE_FIELDS}
        }
      }
    `, { input }).pipe(map(d => d.setComponentGovernance));
  }

  deleteGovernance(componentId: string, tenantId: string): Observable<boolean> {
    return this.gql<{ deleteComponentGovernance: boolean }>(`
      mutation DeleteComponentGovernance($componentId: UUID!, $tenantId: UUID!) {
        deleteComponentGovernance(componentId: $componentId, tenantId: $tenantId)
      }
    `, { componentId, tenantId }).pipe(map(d => d.deleteComponentGovernance));
  }

  // ── Operations ──────────────────────────────────────────────────

  listOperations(componentId: string): Observable<ComponentOperation[]> {
    return this.gql<{ componentOperations: ComponentOperation[] }>(`
      query ComponentOperations($componentId: UUID!) {
        componentOperations(componentId: $componentId) {
          ${OPERATION_FIELDS}
        }
      }
    `, { componentId }).pipe(map(d => d.componentOperations));
  }

  createOperation(componentId: string, input: ComponentOperationCreateInput, providerMode = false): Observable<ComponentOperation> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ createComponentOperation: ComponentOperation }>(`
      mutation CreateComponentOperation($tenantId: UUID, $componentId: UUID!, $input: ComponentOperationCreateInput!) {
        createComponentOperation(tenantId: $tenantId, componentId: $componentId, input: $input) {
          ${OPERATION_FIELDS}
        }
      }
    `, { tenantId, componentId, input }).pipe(map(d => d.createComponentOperation));
  }

  updateOperation(operationId: string, input: ComponentOperationUpdateInput, providerMode = false): Observable<ComponentOperation> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ updateComponentOperation: ComponentOperation }>(`
      mutation UpdateComponentOperation($tenantId: UUID, $operationId: UUID!, $input: ComponentOperationUpdateInput!) {
        updateComponentOperation(tenantId: $tenantId, operationId: $operationId, input: $input) {
          ${OPERATION_FIELDS}
        }
      }
    `, { tenantId, operationId, input }).pipe(map(d => d.updateComponentOperation));
  }

  deleteOperation(operationId: string, providerMode = false): Observable<boolean> {
    const tenantId = providerMode ? null : this.tenantContext.currentTenantId();
    return this.gql<{ deleteComponentOperation: boolean }>(`
      mutation DeleteComponentOperation($tenantId: UUID, $operationId: UUID!) {
        deleteComponentOperation(tenantId: $tenantId, operationId: $operationId)
      }
    `, { tenantId, operationId }).pipe(map(d => d.deleteComponentOperation));
  }

  // ── GraphQL helper ────────────────────────────────────────────────

  private gql<T>(query: string, variables: Record<string, unknown> = {}): Observable<T> {
    return this.api.post<{ data: T; errors?: Array<{ message: string }> }>(
      this.gqlUrl, { query, variables }
    ).pipe(
      map(response => {
        if (response.errors?.length) {
          throw new Error(response.errors[0].message);
        }
        return response.data;
      })
    );
  }
}
