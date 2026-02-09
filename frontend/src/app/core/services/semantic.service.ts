/**
 * Overview: Semantic layer service — GraphQL queries and mutations for managing the type catalog,
 *     relationship kinds, providers, provider resource types, and type mappings.
 * Architecture: Core service layer for semantic layer data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD operations. System records (isSystem=true) protected from deletion/rename.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  SemanticCategory,
  SemanticCategoryInput,
  SemanticCategoryUpdateInput,
  SemanticCategoryWithTypes,
  SemanticProvider,
  SemanticProviderInput,
  SemanticProviderResourceType,
  SemanticProviderResourceTypeInput,
  SemanticProviderResourceTypeUpdateInput,
  SemanticProviderUpdateInput,
  SemanticRelationshipKind,
  SemanticRelationshipKindInput,
  SemanticRelationshipKindUpdateInput,
  SemanticResourceType,
  SemanticResourceTypeInput,
  SemanticResourceTypeList,
  SemanticResourceTypeUpdateInput,
  SemanticTypeMapping,
  SemanticTypeMappingInput,
  SemanticTypeMappingUpdateInput,
} from '@shared/models/semantic.model';

const TYPE_MAPPING_FIELDS = `
  id providerResourceTypeId semanticTypeId
  providerName providerApiType providerDisplayName
  semanticTypeName semanticTypeDisplayName
  parameterMapping notes isSystem createdAt updatedAt
`;

const CATEGORY_FIELDS = `
  id name displayName description icon sortOrder isSystem createdAt updatedAt
`;

const TYPE_FIELDS = `
  id name displayName description icon isAbstract parentTypeName isSystem
  propertiesSchema allowedRelationshipKinds sortOrder
  category { ${CATEGORY_FIELDS} }
  mappings { ${TYPE_MAPPING_FIELDS} }
  children {
    id name displayName description icon isAbstract parentTypeName isSystem
    propertiesSchema allowedRelationshipKinds sortOrder
    category { ${CATEGORY_FIELDS} }
    mappings { ${TYPE_MAPPING_FIELDS} }
    children { id name displayName }
    createdAt updatedAt
  }
  createdAt updatedAt
`;

const RELATIONSHIP_KIND_FIELDS = `
  id name displayName description inverseName isSystem createdAt updatedAt
`;

const PROVIDER_FIELDS = `
  id name displayName description icon providerType websiteUrl documentationUrl
  isSystem resourceTypeCount createdAt updatedAt
`;

const PRT_FIELDS = `
  id providerId providerName apiType displayName description documentationUrl
  parameterSchema status isSystem semanticTypeName semanticTypeId createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class SemanticService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // -- Category queries ---------------------------------------------------

  listCategories(): Observable<SemanticCategoryWithTypes[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticCategories: SemanticCategoryWithTypes[] }>(`
      query SemanticCategories($tenantId: UUID!) {
        semanticCategories(tenantId: $tenantId) {
          ${CATEGORY_FIELDS}
          types { ${TYPE_FIELDS} }
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.semanticCategories),
    );
  }

  // -- Type queries -------------------------------------------------------

  listTypes(filters?: {
    category?: string;
    isAbstract?: boolean;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<SemanticResourceTypeList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticTypes: SemanticResourceTypeList }>(`
      query SemanticTypes(
        $tenantId: UUID!
        $category: String
        $isAbstract: Boolean
        $search: String
        $offset: Int
        $limit: Int
      ) {
        semanticTypes(
          tenantId: $tenantId
          category: $category
          isAbstract: $isAbstract
          search: $search
          offset: $offset
          limit: $limit
        ) {
          items { ${TYPE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.semanticTypes),
    );
  }

  getType(id: string): Observable<SemanticResourceType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticType: SemanticResourceType | null }>(`
      query SemanticType($tenantId: UUID!, $id: UUID!) {
        semanticType(tenantId: $tenantId, id: $id) {
          ${TYPE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.semanticType),
    );
  }

  // -- Relationship kind queries ------------------------------------------

  listRelationshipKinds(): Observable<SemanticRelationshipKind[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticRelationshipKinds: SemanticRelationshipKind[] }>(`
      query SemanticRelationshipKinds($tenantId: UUID!) {
        semanticRelationshipKinds(tenantId: $tenantId) {
          ${RELATIONSHIP_KIND_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.semanticRelationshipKinds),
    );
  }

  // -- Provider queries ---------------------------------------------------

  listProviders(): Observable<SemanticProvider[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticProviders: SemanticProvider[] }>(`
      query SemanticProviders($tenantId: UUID!) {
        semanticProviders(tenantId: $tenantId) {
          ${PROVIDER_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.semanticProviders),
    );
  }

  getProvider(id: string): Observable<SemanticProvider | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticProvider: SemanticProvider | null }>(`
      query SemanticProvider($tenantId: UUID!, $id: UUID!) {
        semanticProvider(tenantId: $tenantId, id: $id) {
          ${PROVIDER_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.semanticProvider),
    );
  }

  // -- Provider resource type queries -------------------------------------

  listProviderResourceTypes(providerId?: string, status?: string): Observable<SemanticProviderResourceType[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticProviderResourceTypes: SemanticProviderResourceType[] }>(`
      query SemanticProviderResourceTypes($tenantId: UUID!, $providerId: UUID, $status: String) {
        semanticProviderResourceTypes(tenantId: $tenantId, providerId: $providerId, status: $status) {
          ${PRT_FIELDS}
        }
      }
    `, { tenantId, providerId, status }).pipe(
      map((data) => data.semanticProviderResourceTypes),
    );
  }

  // -- Type mapping queries -----------------------------------------------

  listTypeMappings(filters?: {
    providerResourceTypeId?: string;
    semanticTypeId?: string;
    providerId?: string;
  }): Observable<SemanticTypeMapping[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticTypeMappings: SemanticTypeMapping[] }>(`
      query SemanticTypeMappings(
        $tenantId: UUID!
        $providerResourceTypeId: UUID
        $semanticTypeId: UUID
        $providerId: UUID
      ) {
        semanticTypeMappings(
          tenantId: $tenantId
          providerResourceTypeId: $providerResourceTypeId
          semanticTypeId: $semanticTypeId
          providerId: $providerId
        ) {
          ${TYPE_MAPPING_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.semanticTypeMappings),
    );
  }

  // -- Category mutations -------------------------------------------------

  createCategory(input: SemanticCategoryInput): Observable<SemanticCategory> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createSemanticCategory: SemanticCategory }>(`
      mutation CreateSemanticCategory($tenantId: UUID!, $input: SemanticCategoryInput!) {
        createSemanticCategory(tenantId: $tenantId, input: $input) {
          ${CATEGORY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createSemanticCategory));
  }

  updateCategory(id: string, input: SemanticCategoryUpdateInput): Observable<SemanticCategory | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateSemanticCategory: SemanticCategory | null }>(`
      mutation UpdateSemanticCategory($tenantId: UUID!, $id: UUID!, $input: SemanticCategoryUpdateInput!) {
        updateSemanticCategory(tenantId: $tenantId, id: $id, input: $input) {
          ${CATEGORY_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateSemanticCategory));
  }

  deleteCategory(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSemanticCategory: boolean }>(`
      mutation DeleteSemanticCategory($tenantId: UUID!, $id: UUID!) {
        deleteSemanticCategory(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteSemanticCategory));
  }

  // -- Type mutations -----------------------------------------------------

  createType(input: SemanticResourceTypeInput): Observable<SemanticResourceType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createSemanticType: SemanticResourceType }>(`
      mutation CreateSemanticType($tenantId: UUID!, $input: SemanticResourceTypeInput!) {
        createSemanticType(tenantId: $tenantId, input: $input) {
          ${TYPE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createSemanticType));
  }

  updateType(id: string, input: SemanticResourceTypeUpdateInput): Observable<SemanticResourceType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateSemanticType: SemanticResourceType | null }>(`
      mutation UpdateSemanticType($tenantId: UUID!, $id: UUID!, $input: SemanticResourceTypeUpdateInput!) {
        updateSemanticType(tenantId: $tenantId, id: $id, input: $input) {
          ${TYPE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateSemanticType));
  }

  deleteType(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSemanticType: boolean }>(`
      mutation DeleteSemanticType($tenantId: UUID!, $id: UUID!) {
        deleteSemanticType(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteSemanticType));
  }

  // -- Provider mutations -------------------------------------------------

  createProvider(input: SemanticProviderInput): Observable<SemanticProvider> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createSemanticProvider: SemanticProvider }>(`
      mutation CreateSemanticProvider($tenantId: UUID!, $input: SemanticProviderInput!) {
        createSemanticProvider(tenantId: $tenantId, input: $input) {
          ${PROVIDER_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createSemanticProvider));
  }

  updateProvider(id: string, input: SemanticProviderUpdateInput): Observable<SemanticProvider | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateSemanticProvider: SemanticProvider | null }>(`
      mutation UpdateSemanticProvider($tenantId: UUID!, $id: UUID!, $input: SemanticProviderUpdateInput!) {
        updateSemanticProvider(tenantId: $tenantId, id: $id, input: $input) {
          ${PROVIDER_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateSemanticProvider));
  }

  deleteProvider(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSemanticProvider: boolean }>(`
      mutation DeleteSemanticProvider($tenantId: UUID!, $id: UUID!) {
        deleteSemanticProvider(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteSemanticProvider));
  }

  // -- Provider resource type mutations -----------------------------------

  createProviderResourceType(input: SemanticProviderResourceTypeInput): Observable<SemanticProviderResourceType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createProviderResourceType: SemanticProviderResourceType }>(`
      mutation CreateProviderResourceType($tenantId: UUID!, $input: SemanticProviderResourceTypeInput!) {
        createProviderResourceType(tenantId: $tenantId, input: $input) {
          ${PRT_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createProviderResourceType));
  }

  updateProviderResourceType(id: string, input: SemanticProviderResourceTypeUpdateInput): Observable<SemanticProviderResourceType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateProviderResourceType: SemanticProviderResourceType | null }>(`
      mutation UpdateProviderResourceType($tenantId: UUID!, $id: UUID!, $input: SemanticProviderResourceTypeUpdateInput!) {
        updateProviderResourceType(tenantId: $tenantId, id: $id, input: $input) {
          ${PRT_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateProviderResourceType));
  }

  deleteProviderResourceType(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteProviderResourceType: boolean }>(`
      mutation DeleteProviderResourceType($tenantId: UUID!, $id: UUID!) {
        deleteProviderResourceType(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteProviderResourceType));
  }

  // -- Type mapping mutations ---------------------------------------------

  createTypeMapping(input: SemanticTypeMappingInput): Observable<SemanticTypeMapping> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTypeMapping: SemanticTypeMapping }>(`
      mutation CreateTypeMapping($tenantId: UUID!, $input: SemanticTypeMappingInput!) {
        createTypeMapping(tenantId: $tenantId, input: $input) {
          ${TYPE_MAPPING_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createTypeMapping));
  }

  updateTypeMapping(id: string, input: SemanticTypeMappingUpdateInput): Observable<SemanticTypeMapping | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateTypeMapping: SemanticTypeMapping | null }>(`
      mutation UpdateTypeMapping($tenantId: UUID!, $id: UUID!, $input: SemanticTypeMappingUpdateInput!) {
        updateTypeMapping(tenantId: $tenantId, id: $id, input: $input) {
          ${TYPE_MAPPING_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateTypeMapping));
  }

  deleteTypeMapping(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTypeMapping: boolean }>(`
      mutation DeleteTypeMapping($tenantId: UUID!, $id: UUID!) {
        deleteTypeMapping(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteTypeMapping));
  }

  // -- Relationship kind mutations ----------------------------------------

  createRelationshipKind(input: SemanticRelationshipKindInput): Observable<SemanticRelationshipKind> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createRelationshipKind: SemanticRelationshipKind }>(`
      mutation CreateRelationshipKind($tenantId: UUID!, $input: SemanticRelationshipKindInput!) {
        createRelationshipKind(tenantId: $tenantId, input: $input) {
          ${RELATIONSHIP_KIND_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createRelationshipKind));
  }

  updateRelationshipKind(id: string, input: SemanticRelationshipKindUpdateInput): Observable<SemanticRelationshipKind | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateRelationshipKind: SemanticRelationshipKind | null }>(`
      mutation UpdateRelationshipKind($tenantId: UUID!, $id: UUID!, $input: SemanticRelationshipKindUpdateInput!) {
        updateRelationshipKind(tenantId: $tenantId, id: $id, input: $input) {
          ${RELATIONSHIP_KIND_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateRelationshipKind));
  }

  deleteRelationshipKind(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteRelationshipKind: boolean }>(`
      mutation DeleteRelationshipKind($tenantId: UUID!, $id: UUID!) {
        deleteRelationshipKind(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteRelationshipKind));
  }

  // -- GraphQL helper -----------------------------------------------------

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
