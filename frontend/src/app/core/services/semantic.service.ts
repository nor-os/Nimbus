/**
 * Overview: Semantic layer service — GraphQL queries and mutations for managing the type catalog,
 *     relationship kinds, and providers.
 * Architecture: Core service layer for semantic layer data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD operations. System records (isSystem=true) protected from deletion/rename.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import { SemanticActivityType } from '@shared/models/cmdb.model';
import {
  OsImage,
  OsImageInput,
  OsImageList,
  OsImageProviderMapping,
  OsImageProviderMappingInput,
  OsImageProviderMappingUpdateInput,
  OsImageUpdateInput,
} from '@shared/models/os-image.model';
import {
  SemanticCategory,
  SemanticCategoryInput,
  SemanticCategoryUpdateInput,
  SemanticCategoryWithTypes,
  SemanticProvider,
  SemanticProviderInput,
  SemanticProviderUpdateInput,
  SemanticRelationshipKind,
  SemanticRelationshipKindInput,
  SemanticRelationshipKindUpdateInput,
  SemanticResourceType,
  SemanticResourceTypeInput,
  SemanticResourceTypeList,
  SemanticResourceTypeUpdateInput,
} from '@shared/models/semantic.model';

const CATEGORY_FIELDS = `
  id name displayName description icon sortOrder isSystem isInfrastructure createdAt updatedAt
`;

const TYPE_FIELDS = `
  id name displayName description icon isAbstract parentTypeName isSystem
  propertiesSchema allowedRelationshipKinds sortOrder
  category { ${CATEGORY_FIELDS} }
  children {
    id name displayName description icon isAbstract parentTypeName isSystem
    propertiesSchema allowedRelationshipKinds sortOrder
    category { ${CATEGORY_FIELDS} }
    children { id name displayName }
    createdAt updatedAt
  }
  createdAt updatedAt
`;

const RELATIONSHIP_KIND_FIELDS = `
  id name displayName description inverseName isSystem createdAt updatedAt
`;

const ACTIVITY_TYPE_FIELDS = `
  id name displayName category description icon
  applicableSemanticCategories applicableSemanticTypes
  defaultRelationshipKindId defaultRelationshipKindName
  propertiesSchema isSystem sortOrder createdAt updatedAt
`;

const PROVIDER_FIELDS = `
  id name displayName description icon providerType websiteUrl documentationUrl
  isSystem resourceTypeCount createdAt updatedAt
`;

const OS_IMAGE_MAPPING_FIELDS = `
  id osImageId providerId providerName providerDisplayName
  imageReference notes isSystem createdAt updatedAt
`;

const OS_IMAGE_TENANT_ASSIGNMENT_FIELDS = `
  id osImageId tenantId tenantName createdAt
`;

const OS_IMAGE_FIELDS = `
  id name displayName osFamily version architecture description icon
  sortOrder isSystem providerMappings { ${OS_IMAGE_MAPPING_FIELDS} }
  tenantAssignments { ${OS_IMAGE_TENANT_ASSIGNMENT_FIELDS} }
  createdAt updatedAt
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
    infrastructureOnly?: boolean;
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
        $infrastructureOnly: Boolean
        $search: String
        $offset: Int
        $limit: Int
      ) {
        semanticTypes(
          tenantId: $tenantId
          category: $category
          isAbstract: $isAbstract
          infrastructureOnly: $infrastructureOnly
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

  // -- Activity type queries ------------------------------------------------

  listActivityTypes(category?: string): Observable<SemanticActivityType[]> {
    const tenantId = this.tenantContext.currentTenantId();
    const vars: Record<string, unknown> = { tenantId };
    let categoryParam = '';
    let categoryArg = '';
    if (category) {
      vars['category'] = category;
      categoryParam = ', $category: String';
      categoryArg = ', category: $category';
    }
    return this.gql<{ semanticActivityTypes: SemanticActivityType[] }>(`
      query SemanticActivityTypes($tenantId: UUID!${categoryParam}) {
        semanticActivityTypes(tenantId: $tenantId${categoryArg}) {
          ${ACTIVITY_TYPE_FIELDS}
        }
      }
    `, vars).pipe(map((d) => d.semanticActivityTypes));
  }

  getActivityType(id: string): Observable<SemanticActivityType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ semanticActivityType: SemanticActivityType | null }>(`
      query SemanticActivityType($tenantId: UUID!, $id: UUID!) {
        semanticActivityType(tenantId: $tenantId, id: $id) {
          ${ACTIVITY_TYPE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.semanticActivityType));
  }

  createActivityType(input: Record<string, unknown>): Observable<SemanticActivityType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createSemanticActivityType: SemanticActivityType }>(`
      mutation CreateSemanticActivityType($tenantId: UUID!, $input: SemanticActivityTypeInput!) {
        createSemanticActivityType(tenantId: $tenantId, input: $input) {
          ${ACTIVITY_TYPE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createSemanticActivityType));
  }

  updateActivityType(id: string, input: Record<string, unknown>): Observable<SemanticActivityType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateSemanticActivityType: SemanticActivityType | null }>(`
      mutation UpdateSemanticActivityType($tenantId: UUID!, $id: UUID!, $input: SemanticActivityTypeUpdateInput!) {
        updateSemanticActivityType(tenantId: $tenantId, id: $id, input: $input) {
          ${ACTIVITY_TYPE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateSemanticActivityType));
  }

  deleteActivityType(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteSemanticActivityType: boolean }>(`
      mutation DeleteSemanticActivityType($tenantId: UUID!, $id: UUID!) {
        deleteSemanticActivityType(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteSemanticActivityType));
  }

  // -- OS Image queries ---------------------------------------------------

  listOsImages(filters?: {
    osFamily?: string;
    architecture?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<OsImageList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ osImages: OsImageList }>(`
      query OsImages(
        $tenantId: UUID!
        $osFamily: String
        $architecture: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        osImages(
          tenantId: $tenantId
          osFamily: $osFamily
          architecture: $architecture
          search: $search
          offset: $offset
          limit: $limit
        ) {
          items { ${OS_IMAGE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.osImages),
    );
  }

  getOsImage(id: string): Observable<OsImage | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ osImage: OsImage | null }>(`
      query OsImage($tenantId: UUID!, $id: UUID!) {
        osImage(tenantId: $tenantId, id: $id) {
          ${OS_IMAGE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.osImage),
    );
  }

  // -- OS Image mutations -------------------------------------------------

  createOsImage(input: OsImageInput): Observable<OsImage> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createOsImage: OsImage }>(`
      mutation CreateOsImage($tenantId: UUID!, $input: OsImageInput!) {
        createOsImage(tenantId: $tenantId, input: $input) {
          ${OS_IMAGE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createOsImage));
  }

  updateOsImage(id: string, input: OsImageUpdateInput): Observable<OsImage | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateOsImage: OsImage | null }>(`
      mutation UpdateOsImage($tenantId: UUID!, $id: UUID!, $input: OsImageUpdateInput!) {
        updateOsImage(tenantId: $tenantId, id: $id, input: $input) {
          ${OS_IMAGE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateOsImage));
  }

  deleteOsImage(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteOsImage: boolean }>(`
      mutation DeleteOsImage($tenantId: UUID!, $id: UUID!) {
        deleteOsImage(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteOsImage));
  }

  // -- OS Image Provider Mapping mutations --------------------------------

  createOsImageProviderMapping(input: OsImageProviderMappingInput): Observable<OsImageProviderMapping> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createOsImageProviderMapping: OsImageProviderMapping }>(`
      mutation CreateOsImageProviderMapping($tenantId: UUID!, $input: OsImageProviderMappingInput!) {
        createOsImageProviderMapping(tenantId: $tenantId, input: $input) {
          ${OS_IMAGE_MAPPING_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createOsImageProviderMapping));
  }

  updateOsImageProviderMapping(id: string, input: OsImageProviderMappingUpdateInput): Observable<OsImageProviderMapping | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateOsImageProviderMapping: OsImageProviderMapping | null }>(`
      mutation UpdateOsImageProviderMapping($tenantId: UUID!, $id: UUID!, $input: OsImageProviderMappingUpdateInput!) {
        updateOsImageProviderMapping(tenantId: $tenantId, id: $id, input: $input) {
          ${OS_IMAGE_MAPPING_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateOsImageProviderMapping));
  }

  deleteOsImageProviderMapping(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteOsImageProviderMapping: boolean }>(`
      mutation DeleteOsImageProviderMapping($tenantId: UUID!, $id: UUID!) {
        deleteOsImageProviderMapping(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteOsImageProviderMapping));
  }

  // -- OS Image Tenant Assignment mutations --------------------------------

  setOsImageTenants(osImageId: string, tenantIds: string[]): Observable<OsImage> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setOsImageTenants: OsImage }>(`
      mutation SetOsImageTenants($tenantId: UUID!, $input: SetImageTenantsInput!) {
        setOsImageTenants(tenantId: $tenantId, input: $input) {
          ${OS_IMAGE_FIELDS}
        }
      }
    `, { tenantId, input: { osImageId, tenantIds } }).pipe(map((d) => d.setOsImageTenants));
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
