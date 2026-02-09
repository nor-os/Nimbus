/**
 * Overview: Catalog GraphQL service — queries and mutations for service offerings,
 *     price lists, price list items, tenant overrides, and effective pricing.
 * Architecture: Core service layer for service catalog data operations (Section 8)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for service catalog entities. All queries are tenant-scoped.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  CIClassActivityAssociation,
  CIClassActivityAssociationCreateInput,
  EffectivePrice,
  PriceList,
  PriceListCreateInput,
  PriceListItem,
  PriceListItemCreateInput,
  PriceListItemUpdateInput,
  PriceListSummary,
  ServiceOffering,
  ServiceOfferingCreateInput,
  ServiceOfferingList,
  ServiceOfferingUpdateInput,
  TenantPriceOverride,
  TenantPriceOverrideCreateInput,
} from '@shared/models/cmdb.model';

// ── Field constants ─────────────────────────────────────────────────

const OFFERING_FIELDS = `
  id tenantId name description category measuringUnit serviceType operatingModel
  defaultCoverageModel ciClassIds isActive regionIds createdAt updatedAt
`;

const CI_CLASS_ACTIVITY_ASSOC_FIELDS = `
  id tenantId ciClassId ciClassName ciClassDisplayName activityTemplateId
  activityTemplateName relationshipType createdAt updatedAt
`;

const PRICE_LIST_ITEM_FIELDS = `
  id priceListId serviceOfferingId deliveryRegionId coverageModel pricePerUnit
  currency minQuantity maxQuantity createdAt updatedAt
`;

const PRICE_LIST_FIELDS = `
  id tenantId name isDefault effectiveFrom effectiveTo
  items { ${PRICE_LIST_ITEM_FIELDS} }
  createdAt updatedAt
`;

const OVERRIDE_FIELDS = `
  id tenantId serviceOfferingId deliveryRegionId coverageModel pricePerUnit
  discountPercent effectiveFrom effectiveTo createdAt updatedAt
`;

const EFFECTIVE_PRICE_FIELDS = `
  serviceOfferingId serviceName pricePerUnit currency measuringUnit hasOverride
  discountPercent deliveryRegionId coverageModel complianceStatus
`;

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Service Offerings ───────────────────────────────────────────

  listOfferings(filters?: {
    category?: string;
    offset?: number;
    limit?: number;
  }): Observable<ServiceOfferingList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceOfferings: ServiceOfferingList }>(`
      query ServiceOfferings(
        $tenantId: UUID!
        $category: String
        $offset: Int
        $limit: Int
      ) {
        serviceOfferings(
          tenantId: $tenantId
          category: $category
          offset: $offset
          limit: $limit
        ) {
          items { ${OFFERING_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.serviceOfferings),
    );
  }

  getOffering(id: string): Observable<ServiceOffering | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceOffering: ServiceOffering | null }>(`
      query ServiceOffering($tenantId: UUID!, $id: UUID!) {
        serviceOffering(tenantId: $tenantId, id: $id) {
          ${OFFERING_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.serviceOffering),
    );
  }

  createOffering(input: ServiceOfferingCreateInput): Observable<ServiceOffering> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceOffering: ServiceOffering }>(`
      mutation CreateServiceOffering($tenantId: UUID!, $input: ServiceOfferingCreateInput!) {
        createServiceOffering(tenantId: $tenantId, input: $input) {
          ${OFFERING_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceOffering));
  }

  updateOffering(id: string, input: ServiceOfferingUpdateInput): Observable<ServiceOffering> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateServiceOffering: ServiceOffering }>(`
      mutation UpdateServiceOffering($tenantId: UUID!, $id: UUID!, $input: ServiceOfferingUpdateInput!) {
        updateServiceOffering(tenantId: $tenantId, id: $id, input: $input) {
          ${OFFERING_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateServiceOffering));
  }

  deleteOffering(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceOffering: boolean }>(`
      mutation DeleteServiceOffering($tenantId: UUID!, $id: UUID!) {
        deleteServiceOffering(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceOffering));
  }

  // ── Offering Regions ───────────────────────────────────────────

  setOfferingRegions(offeringId: string, regionIds: string[]): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setServiceOfferingRegions: string[] }>(`
      mutation SetServiceOfferingRegions(
        $tenantId: UUID!
        $offeringId: UUID!
        $regionIds: [UUID!]!
      ) {
        setServiceOfferingRegions(
          tenantId: $tenantId
          offeringId: $offeringId
          regionIds: $regionIds
        )
      }
    `, { tenantId, offeringId, regionIds }).pipe(
      map((d) => d.setServiceOfferingRegions),
    );
  }

  // ── Price Lists ─────────────────────────────────────────────────

  listPriceLists(offset: number = 0, limit: number = 50): Observable<PriceListSummary> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ priceLists: PriceListSummary }>(`
      query PriceLists($tenantId: UUID!, $offset: Int, $limit: Int) {
        priceLists(tenantId: $tenantId, offset: $offset, limit: $limit) {
          items { ${PRICE_LIST_FIELDS} }
          total
        }
      }
    `, { tenantId, offset, limit }).pipe(
      map((data) => data.priceLists),
    );
  }

  createPriceList(input: PriceListCreateInput): Observable<PriceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPriceList: PriceList }>(`
      mutation CreatePriceList($tenantId: UUID!, $input: PriceListCreateInput!) {
        createPriceList(tenantId: $tenantId, input: $input) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createPriceList));
  }

  deletePriceList(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePriceList: boolean }>(`
      mutation DeletePriceList($tenantId: UUID!, $id: UUID!) {
        deletePriceList(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deletePriceList));
  }

  copyPriceList(
    sourceId: string,
    newName: string,
    clientTenantId?: string | null,
  ): Observable<PriceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ copyPriceList: PriceList }>(`
      mutation CopyPriceList(
        $tenantId: UUID!
        $sourceId: UUID!
        $newName: String!
        $clientTenantId: UUID
      ) {
        copyPriceList(
          tenantId: $tenantId
          sourceId: $sourceId
          newName: $newName
          clientTenantId: $clientTenantId
        ) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, sourceId, newName, clientTenantId }).pipe(
      map((d) => d.copyPriceList),
    );
  }

  // ── Price List Items ────────────────────────────────────────────

  addPriceListItem(priceListId: string, input: PriceListItemCreateInput): Observable<PriceListItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addPriceListItem: PriceListItem }>(`
      mutation AddPriceListItem(
        $tenantId: UUID!
        $priceListId: UUID!
        $input: PriceListItemCreateInput!
      ) {
        addPriceListItem(tenantId: $tenantId, priceListId: $priceListId, input: $input) {
          ${PRICE_LIST_ITEM_FIELDS}
        }
      }
    `, { tenantId, priceListId, input }).pipe(map((d) => d.addPriceListItem));
  }

  updatePriceListItem(id: string, input: PriceListItemUpdateInput): Observable<PriceListItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updatePriceListItem: PriceListItem }>(`
      mutation UpdatePriceListItem($tenantId: UUID!, $id: UUID!, $input: PriceListItemUpdateInput!) {
        updatePriceListItem(tenantId: $tenantId, id: $id, input: $input) {
          ${PRICE_LIST_ITEM_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updatePriceListItem));
  }

  // ── Effective Pricing ───────────────────────────────────────────

  getEffectivePrice(serviceOfferingId: string): Observable<EffectivePrice | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ effectivePrice: EffectivePrice | null }>(`
      query EffectivePrice($tenantId: UUID!, $serviceOfferingId: UUID!) {
        effectivePrice(tenantId: $tenantId, serviceOfferingId: $serviceOfferingId) {
          ${EFFECTIVE_PRICE_FIELDS}
        }
      }
    `, { tenantId, serviceOfferingId }).pipe(
      map((data) => data.effectivePrice),
    );
  }

  // ── Tenant Price Overrides ──────────────────────────────────────

  listTenantOverrides(): Observable<TenantPriceOverride[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantPriceOverrides: TenantPriceOverride[] }>(`
      query TenantPriceOverrides($tenantId: UUID!) {
        tenantPriceOverrides(tenantId: $tenantId) {
          ${OVERRIDE_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.tenantPriceOverrides),
    );
  }

  createTenantOverride(input: TenantPriceOverrideCreateInput): Observable<TenantPriceOverride> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTenantPriceOverride: TenantPriceOverride }>(`
      mutation CreateTenantPriceOverride($tenantId: UUID!, $input: TenantPriceOverrideCreateInput!) {
        createTenantPriceOverride(tenantId: $tenantId, input: $input) {
          ${OVERRIDE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createTenantPriceOverride));
  }

  deleteTenantOverride(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTenantPriceOverride: boolean }>(`
      mutation DeleteTenantPriceOverride($tenantId: UUID!, $id: UUID!) {
        deleteTenantPriceOverride(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteTenantPriceOverride));
  }

  // ── Offering CI Classes ────────────────────────────────────────

  setOfferingCIClasses(offeringId: string, ciClassIds: string[]): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setServiceOfferingCiClasses: string[] }>(`
      mutation SetServiceOfferingCiClasses(
        $tenantId: UUID!
        $offeringId: UUID!
        $ciClassIds: [UUID!]!
      ) {
        setServiceOfferingCiClasses(
          tenantId: $tenantId
          offeringId: $offeringId
          ciClassIds: $ciClassIds
        )
      }
    `, { tenantId, offeringId, ciClassIds }).pipe(
      map((d) => d.setServiceOfferingCiClasses),
    );
  }

  // ── Categories ────────────────────────────────────────────────────

  listDistinctCategories(): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceOfferingCategories: string[] }>(`
      query ServiceOfferingCategories($tenantId: UUID!) {
        serviceOfferingCategories(tenantId: $tenantId)
      }
    `, { tenantId }).pipe(
      map((d) => d.serviceOfferingCategories),
    );
  }

  // ── CI Class ↔ Activity Associations ──────────────────────────────

  listCIClassActivityAssociations(filters?: {
    ciClassId?: string;
    activityTemplateId?: string;
  }): Observable<CIClassActivityAssociation[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ciClassActivityAssociations: CIClassActivityAssociation[] }>(`
      query CIClassActivityAssociations(
        $tenantId: UUID!
        $ciClassId: UUID
        $activityTemplateId: UUID
      ) {
        ciClassActivityAssociations(
          tenantId: $tenantId
          ciClassId: $ciClassId
          activityTemplateId: $activityTemplateId
        ) {
          ${CI_CLASS_ACTIVITY_ASSOC_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((d) => d.ciClassActivityAssociations),
    );
  }

  createCIClassActivityAssociation(
    input: CIClassActivityAssociationCreateInput,
  ): Observable<CIClassActivityAssociation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createCiClassActivityAssociation: CIClassActivityAssociation }>(`
      mutation CreateCIClassActivityAssociation(
        $tenantId: UUID!
        $input: CIClassActivityAssociationCreateInput!
      ) {
        createCiClassActivityAssociation(tenantId: $tenantId, input: $input) {
          ${CI_CLASS_ACTIVITY_ASSOC_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((d) => d.createCiClassActivityAssociation),
    );
  }

  deleteCIClassActivityAssociation(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteCiClassActivityAssociation: boolean }>(`
      mutation DeleteCIClassActivityAssociation($tenantId: UUID!, $id: UUID!) {
        deleteCiClassActivityAssociation(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(
      map((d) => d.deleteCiClassActivityAssociation),
    );
  }

  listRelationshipTypeSuggestions(): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ relationshipTypeSuggestions: string[] }>(`
      query RelationshipTypeSuggestions($tenantId: UUID!) {
        relationshipTypeSuggestions(tenantId: $tenantId)
      }
    `, { tenantId }).pipe(
      map((d) => d.relationshipTypeSuggestions),
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
