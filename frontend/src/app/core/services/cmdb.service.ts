/**
 * Overview: CMDB GraphQL service — queries and mutations for configuration items, classes,
 *     relationships, versioning, graph traversal, compartments, templates, and search.
 * Architecture: Core service layer for CMDB data operations (Section 8)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD operations for CMDB entities. All queries are tenant-scoped.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  CIAttributeDefinitionCreateInput,
  CIAttributeDefinitionUpdateInput,
  CIClass,
  CIClassCreateInput,
  CIClassDetail,
  CIClassUpdateInput,
  CICreateInput,
  CIFromTemplateInput,
  CIList,
  CIRelationship,
  CIRelationshipInput,
  CITemplate,
  CITemplateCreateInput,
  CITemplateList,
  CITemplateUpdateInput,
  CIUpdateInput,
  CIVersionList,
  CompartmentCreateInput,
  CompartmentNode,
  CompartmentUpdateInput,
  ConfigurationItem,
  ExplorerSummary,
  GraphNode,
  RelationshipType,
  SavedSearch,
  SavedSearchInput,
  VersionDiff,
} from '@shared/models/cmdb.model';

// ── Field constants ─────────────────────────────────────────────────

const CLASS_FIELDS = `
  id tenantId name displayName parentClassId semanticTypeId schemaDef
  icon isSystem isActive createdAt updatedAt
`;

const ATTR_DEF_FIELDS = `
  id ciClassId name displayName dataType isRequired defaultValue
  validationRules sortOrder
`;

const CLASS_DETAIL_FIELDS = `
  id tenantId name displayName parentClassId semanticTypeId schemaDef
  icon isSystem isActive
  attributeDefinitions { ${ATTR_DEF_FIELDS} }
  createdAt updatedAt
`;

const CI_FIELDS = `
  id tenantId ciClassId ciClassName compartmentId name description
  lifecycleState attributes tags cloudResourceId pulumiUrn
  backendId backendName createdAt updatedAt
`;

const RELATIONSHIP_TYPE_FIELDS = `
  id name displayName inverseName description sourceClassIds targetClassIds
  isSystem domain sourceEntityType targetEntityType
  sourceSemanticTypes targetSemanticTypes sourceSemanticCategories targetSemanticCategories
  createdAt updatedAt
`;

const RELATIONSHIP_FIELDS = `
  id tenantId sourceCiId sourceCiName targetCiId targetCiName
  relationshipTypeId relationshipTypeName attributes createdAt updatedAt
`;

const SNAPSHOT_FIELDS = `
  id ciId tenantId versionNumber snapshotData changedBy changedAt
  changeReason changeType
`;

const TEMPLATE_FIELDS = `
  id tenantId name description ciClassId ciClassName attributes tags
  relationshipTemplates constraints isActive version createdAt updatedAt
`;

const GRAPH_NODE_FIELDS = `ciId name ciClass depth path`;

const COMPARTMENT_FIELDS = `
  id name description
  children { id name description children { id name description children { id name } } }
`;

const SAVED_SEARCH_FIELDS = `
  id tenantId userId name queryText filters sortConfig isDefault
`;

@Injectable({ providedIn: 'root' })
export class CmdbService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Configuration Items ─────────────────────────────────────────

  listCIs(filters?: {
    ciClassId?: string;
    compartmentId?: string;
    lifecycleState?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<CIList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cis: CIList }>(`
      query CIs(
        $tenantId: UUID!
        $ciClassId: UUID
        $compartmentId: UUID
        $lifecycleState: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        cis(
          tenantId: $tenantId
          ciClassId: $ciClassId
          compartmentId: $compartmentId
          lifecycleState: $lifecycleState
          search: $search
          offset: $offset
          limit: $limit
        ) {
          items { ${CI_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.cis),
    );
  }

  getCI(id: string, version?: number): Observable<ConfigurationItem | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ci: ConfigurationItem | null }>(`
      query CI($tenantId: UUID!, $id: UUID!, $version: Int) {
        ci(tenantId: $tenantId, id: $id, version: $version) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, id, version }).pipe(
      map((data) => data.ci),
    );
  }

  createCI(input: CICreateInput): Observable<ConfigurationItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCi: ConfigurationItem }>(`
      mutation CreateCI($tenantId: UUID!, $input: CICreateInput!) {
        createCi(tenantId: $tenantId, input: $input) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createCi));
  }

  updateCI(id: string, input: CIUpdateInput): Observable<ConfigurationItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateCi: ConfigurationItem }>(`
      mutation UpdateCI($tenantId: UUID!, $id: UUID!, $input: CIUpdateInput!) {
        updateCi(tenantId: $tenantId, id: $id, input: $input) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateCi));
  }

  deleteCI(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCi: boolean }>(`
      mutation DeleteCI($tenantId: UUID!, $id: UUID!) {
        deleteCi(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteCi));
  }

  moveCI(id: string, compartmentId: string | null): Observable<ConfigurationItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ moveCi: ConfigurationItem }>(`
      mutation MoveCI($tenantId: UUID!, $id: UUID!, $compartmentId: UUID) {
        moveCi(tenantId: $tenantId, id: $id, compartmentId: $compartmentId) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, id, compartmentId }).pipe(map((d) => d.moveCi));
  }

  changeCIState(id: string, newState: string): Observable<ConfigurationItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ changeCiState: ConfigurationItem }>(`
      mutation ChangeCIState($tenantId: UUID!, $id: UUID!, $newState: String!) {
        changeCiState(tenantId: $tenantId, id: $id, newState: $newState) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, id, newState }).pipe(map((d) => d.changeCiState));
  }

  // ── CI Classes ──────────────────────────────────────────────────

  listClasses(includeSystem: boolean = true): Observable<CIClass[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciClasses: CIClass[] }>(`
      query CIClasses($tenantId: UUID!, $includeSystem: Boolean) {
        ciClasses(tenantId: $tenantId, includeSystem: $includeSystem) {
          ${CLASS_FIELDS}
        }
      }
    `, { tenantId, includeSystem }).pipe(
      map((data) => data.ciClasses),
    );
  }

  getClass(id: string): Observable<CIClassDetail | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciClass: CIClassDetail | null }>(`
      query CIClass($tenantId: UUID!, $id: UUID!) {
        ciClass(tenantId: $tenantId, id: $id) {
          ${CLASS_DETAIL_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.ciClass),
    );
  }

  createClass(input: CIClassCreateInput): Observable<CIClass> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCiClass: CIClass }>(`
      mutation CreateCIClass($tenantId: UUID!, $input: CIClassCreateInput!) {
        createCiClass(tenantId: $tenantId, input: $input) {
          ${CLASS_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createCiClass));
  }

  updateClass(id: string, input: CIClassUpdateInput): Observable<CIClassDetail> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateCiClass: CIClassDetail }>(`
      mutation UpdateCIClass($tenantId: UUID!, $id: UUID!, $input: CIClassUpdateInput!) {
        updateCiClass(tenantId: $tenantId, id: $id, input: $input) {
          ${CLASS_DETAIL_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateCiClass));
  }

  deleteClass(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCiClass: boolean }>(`
      mutation DeleteCIClass($tenantId: UUID!, $id: UUID!) {
        deleteCiClass(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteCiClass));
  }

  addAttributeDefinition(
    classId: string,
    input: CIAttributeDefinitionCreateInput,
  ): Observable<CIClassDetail> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addAttributeDefinition: CIClassDetail }>(`
      mutation AddAttrDef(
        $tenantId: UUID!
        $classId: UUID!
        $input: CIAttributeDefinitionInput!
      ) {
        addAttributeDefinition(tenantId: $tenantId, classId: $classId, input: $input) {
          ${CLASS_DETAIL_FIELDS}
        }
      }
    `, { tenantId, classId, input }).pipe(map((d) => d.addAttributeDefinition));
  }

  updateAttributeDefinition(
    classId: string,
    attrId: string,
    input: CIAttributeDefinitionUpdateInput,
  ): Observable<CIClassDetail> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateAttributeDefinition: CIClassDetail }>(`
      mutation UpdateAttrDef(
        $tenantId: UUID!
        $classId: UUID!
        $attrId: UUID!
        $input: CIAttributeDefinitionUpdateInput!
      ) {
        updateAttributeDefinition(
          tenantId: $tenantId
          classId: $classId
          attrId: $attrId
          input: $input
        ) {
          ${CLASS_DETAIL_FIELDS}
        }
      }
    `, { tenantId, classId, attrId, input }).pipe(
      map((d) => d.updateAttributeDefinition),
    );
  }

  removeAttributeDefinition(
    classId: string,
    attrId: string,
  ): Observable<CIClassDetail> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeAttributeDefinition: CIClassDetail }>(`
      mutation RemoveAttrDef(
        $tenantId: UUID!
        $classId: UUID!
        $attrId: UUID!
      ) {
        removeAttributeDefinition(
          tenantId: $tenantId
          classId: $classId
          attrId: $attrId
        ) {
          ${CLASS_DETAIL_FIELDS}
        }
      }
    `, { tenantId, classId, attrId }).pipe(
      map((d) => d.removeAttributeDefinition),
    );
  }

  // ── Relationship Types ──────────────────────────────────────────

  listRelationshipTypes(): Observable<RelationshipType[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ relationshipTypes: RelationshipType[] }>(`
      query RelationshipTypes($tenantId: UUID!) {
        relationshipTypes(tenantId: $tenantId) {
          ${RELATIONSHIP_TYPE_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.relationshipTypes),
    );
  }

  updateRelationshipTypeConstraints(
    id: string,
    input: {
      sourceSemanticCategories?: string[] | null;
      targetSemanticCategories?: string[] | null;
    },
  ): Observable<RelationshipType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateRelationshipTypeConstraints: RelationshipType }>(`
      mutation UpdateRelationshipTypeConstraints(
        $tenantId: UUID!
        $id: UUID!
        $input: RelationshipTypeConstraintInput!
      ) {
        updateRelationshipTypeConstraints(tenantId: $tenantId, id: $id, input: $input) {
          ${RELATIONSHIP_TYPE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(
      map((d) => d.updateRelationshipTypeConstraints),
    );
  }

  // ── CI Relationships ────────────────────────────────────────────

  getCIRelationships(
    ciId: string,
    relationshipTypeId?: string,
    direction: string = 'both',
  ): Observable<CIRelationship[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciRelationships: CIRelationship[] }>(`
      query CIRelationships(
        $tenantId: UUID!
        $ciId: UUID!
        $relationshipTypeId: UUID
        $direction: String
      ) {
        ciRelationships(
          tenantId: $tenantId
          ciId: $ciId
          relationshipTypeId: $relationshipTypeId
          direction: $direction
        ) {
          ${RELATIONSHIP_FIELDS}
        }
      }
    `, { tenantId, ciId, relationshipTypeId, direction }).pipe(
      map((data) => data.ciRelationships),
    );
  }

  createRelationship(input: CIRelationshipInput): Observable<CIRelationship> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createRelationship: CIRelationship }>(`
      mutation CreateRelationship($tenantId: UUID!, $input: CIRelationshipInput!) {
        createRelationship(tenantId: $tenantId, input: $input) {
          ${RELATIONSHIP_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createRelationship));
  }

  deleteRelationship(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteRelationship: boolean }>(`
      mutation DeleteRelationship($tenantId: UUID!, $id: UUID!) {
        deleteRelationship(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteRelationship));
  }

  // ── Versioning ──────────────────────────────────────────────────

  getCIVersions(ciId: string, offset: number = 0, limit: number = 50): Observable<CIVersionList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciVersions: CIVersionList }>(`
      query CIVersions($tenantId: UUID!, $ciId: UUID!, $offset: Int, $limit: Int) {
        ciVersions(tenantId: $tenantId, ciId: $ciId, offset: $offset, limit: $limit) {
          items { ${SNAPSHOT_FIELDS} }
          total
        }
      }
    `, { tenantId, ciId, offset, limit }).pipe(
      map((data) => data.ciVersions),
    );
  }

  getCIVersionDiff(ciId: string, versionA: number, versionB: number): Observable<VersionDiff> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciVersionDiff: VersionDiff }>(`
      query CIVersionDiff(
        $tenantId: UUID!
        $ciId: UUID!
        $versionA: Int!
        $versionB: Int!
      ) {
        ciVersionDiff(
          tenantId: $tenantId
          ciId: $ciId
          versionA: $versionA
          versionB: $versionB
        ) {
          versionA versionB changes
        }
      }
    `, { tenantId, ciId, versionA, versionB }).pipe(
      map((data) => data.ciVersionDiff),
    );
  }

  // ── Graph & Impact ──────────────────────────────────────────────

  getCIGraph(
    ciId: string,
    options?: {
      relationshipTypes?: string[];
      direction?: string;
      maxDepth?: number;
    },
  ): Observable<GraphNode[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciGraph: GraphNode[] }>(`
      query CIGraph(
        $tenantId: UUID!
        $ciId: UUID!
        $relationshipTypes: [String!]
        $direction: String
        $maxDepth: Int
      ) {
        ciGraph(
          tenantId: $tenantId
          ciId: $ciId
          relationshipTypes: $relationshipTypes
          direction: $direction
          maxDepth: $maxDepth
        ) {
          ${GRAPH_NODE_FIELDS}
        }
      }
    `, {
      tenantId,
      ciId,
      relationshipTypes: options?.relationshipTypes,
      direction: options?.direction ?? 'outgoing',
      maxDepth: options?.maxDepth ?? 3,
    }).pipe(
      map((data) => data.ciGraph),
    );
  }

  getCIImpact(
    ciId: string,
    direction: string = 'downstream',
    maxDepth: number = 5,
  ): Observable<GraphNode[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciImpact: GraphNode[] }>(`
      query CIImpact(
        $tenantId: UUID!
        $ciId: UUID!
        $direction: String
        $maxDepth: Int
      ) {
        ciImpact(
          tenantId: $tenantId
          ciId: $ciId
          direction: $direction
          maxDepth: $maxDepth
        ) {
          ${GRAPH_NODE_FIELDS}
        }
      }
    `, { tenantId, ciId, direction, maxDepth }).pipe(
      map((data) => data.ciImpact),
    );
  }

  // ── Compartments ────────────────────────────────────────────────

  getCompartmentTree(): Observable<CompartmentNode[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ compartmentTree: CompartmentNode[] }>(`
      query CompartmentTree($tenantId: UUID!) {
        compartmentTree(tenantId: $tenantId) {
          ${COMPARTMENT_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.compartmentTree),
    );
  }

  createCompartment(input: CompartmentCreateInput): Observable<CompartmentNode> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCompartment: CompartmentNode }>(`
      mutation CreateCompartment($tenantId: UUID!, $input: CompartmentCreateInput!) {
        createCompartment(tenantId: $tenantId, input: $input) {
          id name description children { id name }
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createCompartment));
  }

  updateCompartment(id: string, input: CompartmentUpdateInput): Observable<CompartmentNode> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateCompartment: CompartmentNode }>(`
      mutation UpdateCompartment($tenantId: UUID!, $id: UUID!, $input: CompartmentUpdateInput!) {
        updateCompartment(tenantId: $tenantId, id: $id, input: $input) {
          id name description children { id name }
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateCompartment));
  }

  deleteCompartment(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCompartment: boolean }>(`
      mutation DeleteCompartment($tenantId: UUID!, $id: UUID!) {
        deleteCompartment(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteCompartment));
  }

  // ── Templates ───────────────────────────────────────────────────

  listTemplates(filters?: {
    ciClassId?: string;
    offset?: number;
    limit?: number;
  }): Observable<CITemplateList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciTemplates: CITemplateList }>(`
      query CITemplates(
        $tenantId: UUID!
        $ciClassId: UUID
        $offset: Int
        $limit: Int
      ) {
        ciTemplates(
          tenantId: $tenantId
          ciClassId: $ciClassId
          offset: $offset
          limit: $limit
        ) {
          items { ${TEMPLATE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.ciTemplates),
    );
  }

  createTemplate(input: CITemplateCreateInput): Observable<CITemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTemplate: CITemplate }>(`
      mutation CreateTemplate($tenantId: UUID!, $input: CITemplateCreateInput!) {
        createTemplate(tenantId: $tenantId, input: $input) {
          ${TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createTemplate));
  }

  updateTemplate(id: string, input: CITemplateUpdateInput): Observable<CITemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateTemplate: CITemplate }>(`
      mutation UpdateTemplate($tenantId: UUID!, $id: UUID!, $input: CITemplateUpdateInput!) {
        updateTemplate(tenantId: $tenantId, id: $id, input: $input) {
          ${TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateTemplate));
  }

  deleteTemplate(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTemplate: boolean }>(`
      mutation DeleteTemplate($tenantId: UUID!, $id: UUID!) {
        deleteTemplate(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteTemplate));
  }

  createCIFromTemplate(input: CIFromTemplateInput): Observable<ConfigurationItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCiFromTemplate: ConfigurationItem }>(`
      mutation CreateCIFromTemplate($tenantId: UUID!, $input: CIFromTemplateInput!) {
        createCiFromTemplate(tenantId: $tenantId, input: $input) {
          ${CI_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createCiFromTemplate));
  }

  // ── Search ──────────────────────────────────────────────────────

  searchCIs(filters?: {
    query?: string;
    ciClassId?: string;
    compartmentId?: string;
    lifecycleState?: string;
    offset?: number;
    limit?: number;
  }): Observable<CIList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ searchCis: CIList }>(`
      query SearchCIs(
        $tenantId: UUID!
        $query: String
        $ciClassId: UUID
        $compartmentId: UUID
        $lifecycleState: String
        $offset: Int
        $limit: Int
      ) {
        searchCis(
          tenantId: $tenantId
          query: $query
          ciClassId: $ciClassId
          compartmentId: $compartmentId
          lifecycleState: $lifecycleState
          offset: $offset
          limit: $limit
        ) {
          items { ${CI_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.searchCis),
    );
  }

  savedSearches(userId: string): Observable<SavedSearch[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ savedSearches: SavedSearch[] }>(`
      query SavedSearches($tenantId: UUID!, $userId: UUID!) {
        savedSearches(tenantId: $tenantId, userId: $userId) {
          ${SAVED_SEARCH_FIELDS}
        }
      }
    `, { tenantId, userId }).pipe(
      map((data) => data.savedSearches),
    );
  }

  saveSearch(userId: string, input: SavedSearchInput): Observable<SavedSearch> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ saveSearch: SavedSearch }>(`
      mutation SaveSearch($tenantId: UUID!, $userId: UUID!, $input: SavedSearchInput!) {
        saveSearch(tenantId: $tenantId, userId: $userId, input: $input) {
          ${SAVED_SEARCH_FIELDS}
        }
      }
    `, { tenantId, userId, input }).pipe(map((d) => d.saveSearch));
  }

  deleteSavedSearch(id: string, userId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSavedSearch: boolean }>(`
      mutation DeleteSavedSearch($tenantId: UUID!, $id: UUID!, $userId: UUID!) {
        deleteSavedSearch(tenantId: $tenantId, id: $id, userId: $userId)
      }
    `, { tenantId, id, userId }).pipe(map((d) => d.deleteSavedSearch));
  }

  // ── Explorer Summary ────────────────────────────────────────────

  getExplorerSummary(
    compartmentId?: string,
    backendId?: string,
  ): Observable<ExplorerSummary> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ explorerSummary: ExplorerSummary }>(`
      query ExplorerSummary(
        $tenantId: UUID!
        $compartmentId: UUID
        $backendId: UUID
      ) {
        explorerSummary(
          tenantId: $tenantId
          compartmentId: $compartmentId
          backendId: $backendId
        ) {
          totalCis
          categories {
            categoryId
            categoryName
            categoryIcon
            totalCount
            types {
              semanticTypeId
              semanticTypeName
              ciClassId
              ciClassName
              ciClassIcon
              count
            }
          }
          backends {
            backendId
            backendName
            providerName
            ciCount
          }
        }
      }
    `, { tenantId, compartmentId, backendId }).pipe(
      map((data) => data.explorerSummary),
    );
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
