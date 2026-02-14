/**
 * Overview: Catalog GraphQL service — queries and mutations for service offerings,
 *     price lists, price list items, overlay items, pin minimums, and effective pricing.
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
  CatalogDiff,
  CatalogOverlayItem,
  CatalogOverlayItemCreateInput,
  CIClassActivityAssociation,
  CIClassActivityAssociationCreateInput,
  EffectivePrice,
  OfferingCostBreakdown,
  PinMinimumCharge,
  PinMinimumChargeCreateInput,
  PriceList,
  PriceListCreateInput,
  PriceListDiff,
  PriceListItem,
  PriceListItemCreateInput,
  PriceListItemUpdateInput,
  PriceListOverlayItem,
  PriceListOverlayItemCreateInput,
  PriceListSummary,
  ProviderSku,
  ProviderSkuList,
  ServiceCatalog,
  ServiceCatalogList,
  ServiceGroup,
  ServiceGroupItem,
  ServiceGroupList,
  ServiceOffering,
  ServiceOfferingCreateInput,
  ServiceOfferingList,
  ServiceOfferingSku,
  ServiceOfferingUpdateInput,
  TenantCatalogAssignment,
  TenantCatalogPin,
  TenantPriceListAssignment,
  TenantPriceListPin,
} from '@shared/models/cmdb.model';

// ── Field constants ─────────────────────────────────────────────────

const OFFERING_FIELDS = `
  id tenantId name description category measuringUnit serviceType operatingModel
  defaultCoverageModel ciClassIds isActive regionIds status clonedFromId baseFee feePeriod
  minimumAmount minimumCurrency minimumPeriod
  createdAt updatedAt
`;

const CI_CLASS_ACTIVITY_ASSOC_FIELDS = `
  id tenantId ciClassId ciClassName ciClassDisplayName activityTemplateId
  activityTemplateName relationshipType createdAt updatedAt
`;

const PRICE_LIST_ITEM_FIELDS = `
  id priceListId serviceOfferingId providerSkuId activityDefinitionId deliveryRegionId
  coverageModel pricePerUnit markupPercent currency minQuantity maxQuantity createdAt updatedAt
`;

const PRICE_LIST_FIELDS = `
  id tenantId name isDefault
  groupId versionMajor versionMinor versionLabel status
  deliveryRegionId parentVersionId clonedFromPriceListId regionConstraintIds
  items { ${PRICE_LIST_ITEM_FIELDS} }
  createdAt updatedAt
`;

const OVERLAY_ITEM_FIELDS = `
  id tenantId pinId overlayAction baseItemId serviceOfferingId providerSkuId
  activityDefinitionId deliveryRegionId coverageModel pricePerUnit currency
  markupPercent discountPercent minQuantity maxQuantity createdAt updatedAt
`;

const PIN_MINIMUM_FIELDS = `
  id tenantId pinId category minimumAmount currency period
  effectiveFrom effectiveTo createdAt updatedAt
`;

const PIN_FIELDS = `
  id tenantId priceListId
  priceList { ${PRICE_LIST_FIELDS} }
  overlayItems { ${OVERLAY_ITEM_FIELDS} }
  minimumCharges { ${PIN_MINIMUM_FIELDS} }
  effectiveFrom effectiveTo
  createdAt updatedAt
`;

const EFFECTIVE_PRICE_FIELDS = `
  serviceOfferingId serviceName pricePerUnit currency measuringUnit hasOverride
  discountPercent deliveryRegionId coverageModel complianceStatus sourceType markupPercent
  priceListId
`;

const CATALOG_ITEM_FIELDS = `
  id catalogId serviceOfferingId serviceGroupId sortOrder createdAt updatedAt
`;

const CATALOG_FIELDS = `
  id tenantId name description groupId versionMajor versionMinor versionLabel status
  parentVersionId clonedFromCatalogId regionConstraintIds
  items { ${CATALOG_ITEM_FIELDS} }
  createdAt updatedAt
`;

const CATALOG_OVERLAY_FIELDS = `
  id tenantId pinId overlayAction baseItemId serviceOfferingId serviceGroupId
  sortOrder createdAt updatedAt
`;

const CATALOG_PIN_FIELDS = `
  id tenantId catalogId
  catalog { ${CATALOG_FIELDS} }
  overlayItems { ${CATALOG_OVERLAY_FIELDS} }
  effectiveFrom effectiveTo
  createdAt updatedAt
`;

const SKU_FIELDS = `
  id providerId externalSkuId name displayName description ciClassId
  measuringUnit category unitCost costCurrency attributes isActive
  semanticTypeId semanticTypeName resourceType
  createdAt updatedAt
`;

const OFFERING_SKU_FIELDS = `
  id serviceOfferingId providerSkuId defaultQuantity isRequired sortOrder
  createdAt updatedAt
`;

const GROUP_ITEM_FIELDS = `
  id groupId serviceOfferingId offeringName isRequired sortOrder createdAt updatedAt
`;

const GROUP_FIELDS = `
  id tenantId name displayName description status
  items { ${GROUP_ITEM_FIELDS} }
  createdAt updatedAt
`;

const COST_BREAKDOWN_FIELDS = `
  sourceType sourceId sourceName quantity isRequired pricePerUnit currency
  measuringUnit markupPercent
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

  getEffectivePrice(
    serviceOfferingId: string,
    options?: { tenantId?: string; deliveryRegionId?: string; coverageModel?: string; priceListId?: string },
  ): Observable<EffectivePrice | null> {
    const tenantId = options?.tenantId || this.tenantContext.currentTenantId();
    return this.gql<{ effectivePrice: EffectivePrice | null }>(`
      query EffectivePrice($tenantId: UUID!, $serviceOfferingId: UUID!, $deliveryRegionId: UUID, $coverageModel: String, $priceListId: UUID) {
        effectivePrice(tenantId: $tenantId, serviceOfferingId: $serviceOfferingId, deliveryRegionId: $deliveryRegionId, coverageModel: $coverageModel, priceListId: $priceListId) {
          ${EFFECTIVE_PRICE_FIELDS}
        }
      }
    `, {
      tenantId,
      serviceOfferingId,
      deliveryRegionId: options?.deliveryRegionId || null,
      coverageModel: options?.coverageModel || null,
      priceListId: options?.priceListId || null,
    }).pipe(
      map((data) => data.effectivePrice),
    );
  }

  // ── Price List Overlay Items ────────────────────────────────────

  createPriceListOverlay(tenantId: string, pinId: string, input: PriceListOverlayItemCreateInput): Observable<PriceListOverlayItem> {
    return this.gql<{ createPriceListOverlayItem: PriceListOverlayItem }>(`
      mutation CreatePriceListOverlayItem($tenantId: UUID!, $pinId: UUID!, $input: PriceListOverlayItemCreateInput!) {
        createPriceListOverlayItem(tenantId: $tenantId, pinId: $pinId, input: $input) {
          ${OVERLAY_ITEM_FIELDS}
        }
      }
    `, { tenantId, pinId, input }).pipe(map((d) => d.createPriceListOverlayItem));
  }

  deletePriceListOverlay(tenantId: string, itemId: string): Observable<boolean> {
    return this.gql<{ deletePriceListOverlayItem: boolean }>(`
      mutation DeletePriceListOverlayItem($tenantId: UUID!, $itemId: UUID!) {
        deletePriceListOverlayItem(tenantId: $tenantId, itemId: $itemId)
      }
    `, { tenantId, itemId }).pipe(map((d) => d.deletePriceListOverlayItem));
  }

  // ── Catalog Overlay Items ─────────────────────────────────────

  createCatalogOverlay(tenantId: string, pinId: string, input: CatalogOverlayItemCreateInput): Observable<CatalogOverlayItem> {
    return this.gql<{ createCatalogOverlayItem: CatalogOverlayItem }>(`
      mutation CreateCatalogOverlayItem($tenantId: UUID!, $pinId: UUID!, $input: CatalogOverlayItemCreateInput!) {
        createCatalogOverlayItem(tenantId: $tenantId, pinId: $pinId, input: $input) {
          ${CATALOG_OVERLAY_FIELDS}
        }
      }
    `, { tenantId, pinId, input }).pipe(map((d) => d.createCatalogOverlayItem));
  }

  deleteCatalogOverlay(tenantId: string, itemId: string): Observable<boolean> {
    return this.gql<{ deleteCatalogOverlayItem: boolean }>(`
      mutation DeleteCatalogOverlayItem($tenantId: UUID!, $itemId: UUID!) {
        deleteCatalogOverlayItem(tenantId: $tenantId, itemId: $itemId)
      }
    `, { tenantId, itemId }).pipe(map((d) => d.deleteCatalogOverlayItem));
  }

  // ── Pin Minimum Charges ───────────────────────────────────────

  createPinMinimumCharge(tenantId: string, pinId: string, input: PinMinimumChargeCreateInput): Observable<PinMinimumCharge> {
    return this.gql<{ createPinMinimumCharge: PinMinimumCharge }>(`
      mutation CreatePinMinimumCharge($tenantId: UUID!, $pinId: UUID!, $input: PinMinimumChargeCreateInput!) {
        createPinMinimumCharge(tenantId: $tenantId, pinId: $pinId, input: $input) {
          ${PIN_MINIMUM_FIELDS}
        }
      }
    `, { tenantId, pinId, input }).pipe(map((d) => d.createPinMinimumCharge));
  }

  deletePinMinimumCharge(tenantId: string, chargeId: string): Observable<boolean> {
    return this.gql<{ deletePinMinimumCharge: boolean }>(`
      mutation DeletePinMinimumCharge($tenantId: UUID!, $chargeId: UUID!) {
        deletePinMinimumCharge(tenantId: $tenantId, chargeId: $chargeId)
      }
    `, { tenantId, chargeId }).pipe(map((d) => d.deletePinMinimumCharge));
  }

  // ── Region Constraints ────────────────────────────────────────

  setPriceListRegionConstraints(priceListId: string, regionIds: string[]): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setPriceListRegionConstraints: string[] }>(`
      mutation SetPriceListRegionConstraints($tenantId: UUID!, $priceListId: UUID!, $regionIds: [UUID!]!) {
        setPriceListRegionConstraints(tenantId: $tenantId, priceListId: $priceListId, regionIds: $regionIds)
      }
    `, { tenantId, priceListId, regionIds }).pipe(map((d) => d.setPriceListRegionConstraints));
  }

  setCatalogRegionConstraints(catalogId: string, regionIds: string[]): Observable<string[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setCatalogRegionConstraints: string[] }>(`
      mutation SetCatalogRegionConstraints($tenantId: UUID!, $catalogId: UUID!, $regionIds: [UUID!]!) {
        setCatalogRegionConstraints(tenantId: $tenantId, catalogId: $catalogId, regionIds: $regionIds)
      }
    `, { tenantId, catalogId, regionIds }).pipe(map((d) => d.setCatalogRegionConstraints));
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

  // ── Price List Versioning ────────────────────────────────────────

  createPriceListVersion(priceListId: string, bump: 'minor' | 'major' = 'minor'): Observable<PriceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPriceListVersion: PriceList }>(`
      mutation CreatePriceListVersion($tenantId: UUID!, $input: PriceListVersionInput!) {
        createPriceListVersion(tenantId: $tenantId, input: $input) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, input: { priceListId, bump } }).pipe(
      map((d) => d.createPriceListVersion),
    );
  }

  publishPriceList(priceListId: string): Observable<PriceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishPriceList: PriceList }>(`
      mutation PublishPriceList($tenantId: UUID!, $priceListId: UUID!) {
        publishPriceList(tenantId: $tenantId, priceListId: $priceListId) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, priceListId }).pipe(map((d) => d.publishPriceList));
  }

  archivePriceList(priceListId: string): Observable<PriceList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archivePriceList: PriceList }>(`
      mutation ArchivePriceList($tenantId: UUID!, $priceListId: UUID!) {
        archivePriceList(tenantId: $tenantId, priceListId: $priceListId) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, priceListId }).pipe(map((d) => d.archivePriceList));
  }

  listPriceListVersions(groupId: string): Observable<PriceList[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ priceListVersions: PriceList[] }>(`
      query PriceListVersions($tenantId: UUID!, $groupId: UUID!) {
        priceListVersions(tenantId: $tenantId, groupId: $groupId) {
          ${PRICE_LIST_FIELDS}
        }
      }
    `, { tenantId, groupId }).pipe(map((d) => d.priceListVersions));
  }

  // ── Tenant Price List Pins ──────────────────────────────────────

  pinTenantToPriceList(
    targetTenantId: string,
    priceListId: string,
    effectiveFrom?: string,
    effectiveTo?: string | null,
  ): Observable<TenantPriceListPin> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ pinTenantToPriceList: TenantPriceListPin }>(`
      mutation PinTenantToPriceList($tenantId: UUID!, $priceListId: UUID!, $effectiveFrom: Date, $effectiveTo: Date) {
        pinTenantToPriceList(tenantId: $tenantId, priceListId: $priceListId, effectiveFrom: $effectiveFrom, effectiveTo: $effectiveTo) {
          ${PIN_FIELDS}
        }
      }
    `, { tenantId: targetTenantId, priceListId, effectiveFrom, effectiveTo }).pipe(
      map((d) => d.pinTenantToPriceList),
    );
  }

  unpinTenantFromPriceList(targetTenantId: string, priceListId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ unpinTenantFromPriceList: boolean }>(`
      mutation UnpinTenantFromPriceList($tenantId: UUID!, $priceListId: UUID!) {
        unpinTenantFromPriceList(tenantId: $tenantId, priceListId: $priceListId)
      }
    `, { tenantId: targetTenantId, priceListId }).pipe(
      map((d) => d.unpinTenantFromPriceList),
    );
  }

  listTenantPins(targetTenantId: string): Observable<TenantPriceListPin[]> {
    return this.gql<{ tenantPriceListPins: TenantPriceListPin[] }>(`
      query TenantPriceListPins($tenantId: UUID!) {
        tenantPriceListPins(tenantId: $tenantId) {
          ${PIN_FIELDS}
        }
      }
    `, { tenantId: targetTenantId }).pipe(
      map((d) => d.tenantPriceListPins),
    );
  }

  // ── Service Catalogs ──────────────────────────────────────────────

  listCatalogs(filters?: { status?: string; offset?: number; limit?: number }): Observable<ServiceCatalogList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceCatalogs: ServiceCatalogList }>(`
      query ServiceCatalogs($tenantId: UUID!, $status: String, $offset: Int, $limit: Int) {
        serviceCatalogs(tenantId: $tenantId, status: $status, offset: $offset, limit: $limit) {
          items { ${CATALOG_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(map((d) => d.serviceCatalogs));
  }

  getCatalog(id: string): Observable<ServiceCatalog | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceCatalog: ServiceCatalog | null }>(`
      query ServiceCatalog($tenantId: UUID!, $id: UUID!) {
        serviceCatalog(tenantId: $tenantId, id: $id) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.serviceCatalog));
  }

  listCatalogVersions(groupId: string): Observable<ServiceCatalog[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceCatalogVersions: ServiceCatalog[] }>(`
      query ServiceCatalogVersions($tenantId: UUID!, $groupId: UUID!) {
        serviceCatalogVersions(tenantId: $tenantId, groupId: $groupId) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, groupId }).pipe(map((d) => d.serviceCatalogVersions));
  }

  createCatalog(input: { name: string; description?: string }): Observable<ServiceCatalog> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceCatalog: ServiceCatalog }>(`
      mutation CreateServiceCatalog($tenantId: UUID!, $input: ServiceCatalogCreateInput!) {
        createServiceCatalog(tenantId: $tenantId, input: $input) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceCatalog));
  }

  deleteCatalog(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceCatalog: boolean }>(`
      mutation DeleteServiceCatalog($tenantId: UUID!, $id: UUID!) {
        deleteServiceCatalog(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceCatalog));
  }

  createCatalogVersion(catalogId: string, bump: 'minor' | 'major' = 'minor'): Observable<ServiceCatalog> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceCatalogVersion: ServiceCatalog }>(`
      mutation CreateServiceCatalogVersion($tenantId: UUID!, $input: ServiceCatalogVersionInput!) {
        createServiceCatalogVersion(tenantId: $tenantId, input: $input) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, input: { catalogId, bump } }).pipe(map((d) => d.createServiceCatalogVersion));
  }

  publishCatalog(catalogId: string): Observable<ServiceCatalog> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishServiceCatalog: ServiceCatalog }>(`
      mutation PublishServiceCatalog($tenantId: UUID!, $catalogId: UUID!) {
        publishServiceCatalog(tenantId: $tenantId, catalogId: $catalogId) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, catalogId }).pipe(map((d) => d.publishServiceCatalog));
  }

  archiveCatalog(catalogId: string): Observable<ServiceCatalog> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveServiceCatalog: ServiceCatalog }>(`
      mutation ArchiveServiceCatalog($tenantId: UUID!, $catalogId: UUID!) {
        archiveServiceCatalog(tenantId: $tenantId, catalogId: $catalogId) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, catalogId }).pipe(map((d) => d.archiveServiceCatalog));
  }

  cloneCatalogForTenant(catalogId: string, targetTenantId: string): Observable<ServiceCatalog> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneCatalogForTenant: ServiceCatalog }>(`
      mutation CloneCatalogForTenant($tenantId: UUID!, $catalogId: UUID!, $targetTenantId: UUID!) {
        cloneCatalogForTenant(tenantId: $tenantId, catalogId: $catalogId, targetTenantId: $targetTenantId) { ${CATALOG_FIELDS} }
      }
    `, { tenantId, catalogId, targetTenantId }).pipe(map((d) => d.cloneCatalogForTenant));
  }

  addCatalogItem(catalogId: string, serviceOfferingId?: string, serviceGroupId?: string, sortOrder?: number): Observable<any> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addCatalogItem: any }>(`
      mutation AddCatalogItem($tenantId: UUID!, $catalogId: UUID!, $serviceOfferingId: UUID, $serviceGroupId: UUID, $sortOrder: Int) {
        addCatalogItem(tenantId: $tenantId, catalogId: $catalogId, serviceOfferingId: $serviceOfferingId, serviceGroupId: $serviceGroupId, sortOrder: $sortOrder) { ${CATALOG_ITEM_FIELDS} }
      }
    `, { tenantId, catalogId, serviceOfferingId, serviceGroupId, sortOrder }).pipe(map((d) => d.addCatalogItem));
  }

  removeCatalogItem(itemId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeCatalogItem: boolean }>(`
      mutation RemoveCatalogItem($tenantId: UUID!, $itemId: UUID!) {
        removeCatalogItem(tenantId: $tenantId, itemId: $itemId)
      }
    `, { tenantId, itemId }).pipe(map((d) => d.removeCatalogItem));
  }

  listCatalogPins(): Observable<TenantCatalogPin[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantCatalogPins: TenantCatalogPin[] }>(`
      query TenantCatalogPins($tenantId: UUID!) {
        tenantCatalogPins(tenantId: $tenantId) { ${CATALOG_PIN_FIELDS} }
      }
    `, { tenantId }).pipe(map((d) => d.tenantCatalogPins));
  }

  pinTenantToCatalog(
    targetTenantId: string,
    catalogId: string,
    effectiveFrom?: string,
    effectiveTo?: string | null,
  ): Observable<TenantCatalogPin> {
    return this.gql<{ pinTenantToCatalog: TenantCatalogPin }>(`
      mutation PinTenantToCatalog($tenantId: UUID!, $catalogId: UUID!, $effectiveFrom: Date, $effectiveTo: Date) {
        pinTenantToCatalog(tenantId: $tenantId, catalogId: $catalogId, effectiveFrom: $effectiveFrom, effectiveTo: $effectiveTo) { ${CATALOG_PIN_FIELDS} }
      }
    `, { tenantId: targetTenantId, catalogId, effectiveFrom, effectiveTo }).pipe(map((d) => d.pinTenantToCatalog));
  }

  unpinTenantFromCatalog(targetTenantId: string, catalogId: string): Observable<boolean> {
    return this.gql<{ unpinTenantFromCatalog: boolean }>(`
      mutation UnpinTenantFromCatalog($tenantId: UUID!, $catalogId: UUID!) {
        unpinTenantFromCatalog(tenantId: $tenantId, catalogId: $catalogId)
      }
    `, { tenantId: targetTenantId, catalogId }).pipe(map((d) => d.unpinTenantFromCatalog));
  }

  // ── Provider SKUs ─────────────────────────────────────────────────

  listSkus(filters?: { providerId?: string; category?: string; activeOnly?: boolean; offset?: number; limit?: number }): Observable<ProviderSkuList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ providerSkus: ProviderSkuList }>(`
      query ProviderSkus($tenantId: UUID!, $providerId: UUID, $category: String, $activeOnly: Boolean, $offset: Int, $limit: Int) {
        providerSkus(tenantId: $tenantId, providerId: $providerId, category: $category, activeOnly: $activeOnly, offset: $offset, limit: $limit) {
          items { ${SKU_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(map((d) => d.providerSkus));
  }

  getSku(id: string): Observable<ProviderSku | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ providerSku: ProviderSku | null }>(`
      query ProviderSku($tenantId: UUID!, $id: UUID!) {
        providerSku(tenantId: $tenantId, id: $id) { ${SKU_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.providerSku));
  }

  createSku(input: Record<string, unknown>): Observable<ProviderSku> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createProviderSku: ProviderSku }>(`
      mutation CreateProviderSku($tenantId: UUID!, $input: ProviderSkuCreateInput!) {
        createProviderSku(tenantId: $tenantId, input: $input) { ${SKU_FIELDS} }
      }
    `, { tenantId, input }).pipe(map((d) => d.createProviderSku));
  }

  updateSku(id: string, input: Record<string, unknown>): Observable<ProviderSku> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateProviderSku: ProviderSku }>(`
      mutation UpdateProviderSku($tenantId: UUID!, $id: UUID!, $input: ProviderSkuUpdateInput!) {
        updateProviderSku(tenantId: $tenantId, id: $id, input: $input) { ${SKU_FIELDS} }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateProviderSku));
  }

  deactivateSku(id: string): Observable<ProviderSku> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deactivateProviderSku: ProviderSku }>(`
      mutation DeactivateProviderSku($tenantId: UUID!, $id: UUID!) {
        deactivateProviderSku(tenantId: $tenantId, id: $id) { ${SKU_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.deactivateProviderSku));
  }

  listOfferingSkus(serviceOfferingId: string): Observable<ServiceOfferingSku[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ offeringSkus: ServiceOfferingSku[] }>(`
      query OfferingSkus($tenantId: UUID!, $serviceOfferingId: UUID!) {
        offeringSkus(tenantId: $tenantId, serviceOfferingId: $serviceOfferingId) {
          ${OFFERING_SKU_FIELDS}
        }
      }
    `, { tenantId, serviceOfferingId }).pipe(map((d) => d.offeringSkus));
  }

  addSkuToOffering(serviceOfferingId: string, providerSkuId: string, defaultQuantity?: number, isRequired?: boolean, sortOrder?: number): Observable<ServiceOfferingSku> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addSkuToOffering: ServiceOfferingSku }>(`
      mutation AddSkuToOffering($tenantId: UUID!, $serviceOfferingId: UUID!, $providerSkuId: UUID!, $defaultQuantity: Int, $isRequired: Boolean, $sortOrder: Int) {
        addSkuToOffering(tenantId: $tenantId, serviceOfferingId: $serviceOfferingId, providerSkuId: $providerSkuId, defaultQuantity: $defaultQuantity, isRequired: $isRequired, sortOrder: $sortOrder) { ${OFFERING_SKU_FIELDS} }
      }
    `, { tenantId, serviceOfferingId, providerSkuId, defaultQuantity, isRequired, sortOrder }).pipe(map((d) => d.addSkuToOffering));
  }

  removeSkuFromOffering(linkId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeSkuFromOffering: boolean }>(`
      mutation RemoveSkuFromOffering($tenantId: UUID!, $linkId: UUID!) {
        removeSkuFromOffering(tenantId: $tenantId, linkId: $linkId)
      }
    `, { tenantId, linkId }).pipe(map((d) => d.removeSkuFromOffering));
  }

  // ── Offering Lifecycle ────────────────────────────────────────────

  cloneOffering(offeringId: string): Observable<ServiceOffering> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneOffering: ServiceOffering }>(`
      mutation CloneOffering($tenantId: UUID!, $offeringId: UUID!) {
        cloneOffering(tenantId: $tenantId, offeringId: $offeringId) { ${OFFERING_FIELDS} }
      }
    `, { tenantId, offeringId }).pipe(map((d) => d.cloneOffering));
  }

  publishOffering(offeringId: string): Observable<ServiceOffering> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishOffering: ServiceOffering }>(`
      mutation PublishOffering($tenantId: UUID!, $offeringId: UUID!) {
        publishOffering(tenantId: $tenantId, offeringId: $offeringId) { ${OFFERING_FIELDS} }
      }
    `, { tenantId, offeringId }).pipe(map((d) => d.publishOffering));
  }

  archiveOffering(offeringId: string): Observable<ServiceOffering> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveOffering: ServiceOffering }>(`
      mutation ArchiveOffering($tenantId: UUID!, $offeringId: UUID!) {
        archiveOffering(tenantId: $tenantId, offeringId: $offeringId) { ${OFFERING_FIELDS} }
      }
    `, { tenantId, offeringId }).pipe(map((d) => d.archiveOffering));
  }

  // ── Service Groups ────────────────────────────────────────────────

  listGroups(offset: number = 0, limit: number = 50, status?: string): Observable<ServiceGroupList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceGroups: ServiceGroupList }>(`
      query ServiceGroups($tenantId: UUID!, $status: String, $offset: Int, $limit: Int) {
        serviceGroups(tenantId: $tenantId, status: $status, offset: $offset, limit: $limit) {
          items { ${GROUP_FIELDS} }
          total
        }
      }
    `, { tenantId, status, offset, limit }).pipe(map((d) => d.serviceGroups));
  }

  getGroup(id: string): Observable<ServiceGroup | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceGroup: ServiceGroup | null }>(`
      query ServiceGroup($tenantId: UUID!, $id: UUID!) {
        serviceGroup(tenantId: $tenantId, id: $id) { ${GROUP_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.serviceGroup));
  }

  createGroup(input: { name: string; displayName?: string; description?: string }): Observable<ServiceGroup> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceGroup: ServiceGroup }>(`
      mutation CreateServiceGroup($tenantId: UUID!, $input: ServiceGroupCreateInput!) {
        createServiceGroup(tenantId: $tenantId, input: $input) { ${GROUP_FIELDS} }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceGroup));
  }

  updateGroup(id: string, input: Record<string, unknown>): Observable<ServiceGroup> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateServiceGroup: ServiceGroup }>(`
      mutation UpdateServiceGroup($tenantId: UUID!, $id: UUID!, $input: ServiceGroupUpdateInput!) {
        updateServiceGroup(tenantId: $tenantId, id: $id, input: $input) { ${GROUP_FIELDS} }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateServiceGroup));
  }

  deleteGroup(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceGroup: boolean }>(`
      mutation DeleteServiceGroup($tenantId: UUID!, $id: UUID!) {
        deleteServiceGroup(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceGroup));
  }

  addGroupItem(groupId: string, serviceOfferingId: string, isRequired?: boolean, sortOrder?: number): Observable<ServiceGroupItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addGroupItem: ServiceGroupItem }>(`
      mutation AddGroupItem($tenantId: UUID!, $groupId: UUID!, $serviceOfferingId: UUID!, $isRequired: Boolean, $sortOrder: Int) {
        addGroupItem(tenantId: $tenantId, groupId: $groupId, serviceOfferingId: $serviceOfferingId, isRequired: $isRequired, sortOrder: $sortOrder) { ${GROUP_ITEM_FIELDS} }
      }
    `, { tenantId, groupId, serviceOfferingId, isRequired, sortOrder }).pipe(map((d) => d.addGroupItem));
  }

  removeGroupItem(itemId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeGroupItem: boolean }>(`
      mutation RemoveGroupItem($tenantId: UUID!, $itemId: UUID!) {
        removeGroupItem(tenantId: $tenantId, itemId: $itemId)
      }
    `, { tenantId, itemId }).pipe(map((d) => d.removeGroupItem));
  }

  // ── Service Group Lifecycle ─────────────────────────────────────────

  publishGroup(id: string): Observable<ServiceGroup> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishServiceGroup: ServiceGroup }>(`
      mutation PublishServiceGroup($tenantId: UUID!, $id: UUID!) {
        publishServiceGroup(tenantId: $tenantId, id: $id) { ${GROUP_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.publishServiceGroup));
  }

  archiveGroup(id: string): Observable<ServiceGroup> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveServiceGroup: ServiceGroup }>(`
      mutation ArchiveServiceGroup($tenantId: UUID!, $id: UUID!) {
        archiveServiceGroup(tenantId: $tenantId, id: $id) { ${GROUP_FIELDS} }
      }
    `, { tenantId, id }).pipe(map((d) => d.archiveServiceGroup));
  }

  cloneGroup(id: string, targetTenantId?: string): Observable<ServiceGroup> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneServiceGroup: ServiceGroup }>(`
      mutation CloneServiceGroup($tenantId: UUID!, $id: UUID!, $targetTenantId: UUID) {
        cloneServiceGroup(tenantId: $tenantId, id: $id, targetTenantId: $targetTenantId) { ${GROUP_FIELDS} }
      }
    `, { tenantId, id, targetTenantId }).pipe(map((d) => d.cloneServiceGroup));
  }

  // ── Offering Cost Breakdown ───────────────────────────────────────

  getOfferingCostBreakdown(
    offeringId: string,
    options?: { deliveryRegionId?: string; coverageModel?: string; priceListId?: string; tenantId?: string },
  ): Observable<OfferingCostBreakdown[]> {
    const tenantId = options?.tenantId || this.tenantContext.currentTenantId();
    return this.gql<{ offeringCostBreakdown: OfferingCostBreakdown[] }>(`
      query OfferingCostBreakdown($tenantId: UUID!, $offeringId: UUID!, $deliveryRegionId: UUID, $coverageModel: String, $priceListId: UUID) {
        offeringCostBreakdown(tenantId: $tenantId, offeringId: $offeringId, deliveryRegionId: $deliveryRegionId, coverageModel: $coverageModel, priceListId: $priceListId) { ${COST_BREAKDOWN_FIELDS} }
      }
    `, {
      tenantId,
      offeringId,
      deliveryRegionId: options?.deliveryRegionId || null,
      coverageModel: options?.coverageModel || null,
      priceListId: options?.priceListId || null,
    }).pipe(map((d) => d.offeringCostBreakdown));
  }

  getCICountForOffering(tenantId: string, offeringId: string): Observable<number> {
    return this.gql<{ ciCountForOffering: number }>(`
      query CICountForOffering($tenantId: UUID!, $offeringId: UUID!) {
        ciCountForOffering(tenantId: $tenantId, offeringId: $offeringId)
      }
    `, { tenantId, offeringId }).pipe(map((d) => d.ciCountForOffering));
  }

  // ── Reverse Lookups (by price list / catalog) ──────────────────

  listPinnedTenantsForPriceList(priceListId: string): Observable<TenantPriceListPin[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ pinnedTenantsForPriceList: TenantPriceListPin[] }>(`
      query PinnedTenantsForPriceList($tenantId: UUID!, $priceListId: UUID!) {
        pinnedTenantsForPriceList(tenantId: $tenantId, priceListId: $priceListId) {
          ${PIN_FIELDS}
        }
      }
    `, { tenantId, priceListId }).pipe(map((d) => d.pinnedTenantsForPriceList));
  }

  getPriceListTenantAssignments(priceListId: string): Observable<TenantPriceListAssignment[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantPriceListAssignments: TenantPriceListAssignment[] }>(`
      query TenantPriceListAssignments($tenantId: UUID!, $priceListId: UUID!) {
        tenantPriceListAssignments(tenantId: $tenantId, priceListId: $priceListId) {
          tenantId assignmentType priceListId clonePriceListId
          additions deletions isCustomized
        }
      }
    `, { tenantId, priceListId }).pipe(map((d) => d.tenantPriceListAssignments));
  }

  getPriceListDiff(sourcePriceListId: string, clonePriceListId: string): Observable<PriceListDiff> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ priceListDiff: PriceListDiff }>(`
      query PriceListDiff($tenantId: UUID!, $sourcePriceListId: UUID!, $clonePriceListId: UUID!) {
        priceListDiff(tenantId: $tenantId, sourcePriceListId: $sourcePriceListId, clonePriceListId: $clonePriceListId) {
          sourcePriceListId clonePriceListId
          additions { ${PRICE_LIST_ITEM_FIELDS} }
          deletions { ${PRICE_LIST_ITEM_FIELDS} }
          common { ${PRICE_LIST_ITEM_FIELDS} }
        }
      }
    `, { tenantId, sourcePriceListId, clonePriceListId }).pipe(map((d) => d.priceListDiff));
  }

  listPinnedTenantsForCatalog(catalogId: string): Observable<TenantCatalogPin[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ pinnedTenantsForCatalog: TenantCatalogPin[] }>(`
      query PinnedTenantsForCatalog($tenantId: UUID!, $catalogId: UUID!) {
        pinnedTenantsForCatalog(tenantId: $tenantId, catalogId: $catalogId) {
          ${CATALOG_PIN_FIELDS}
        }
      }
    `, { tenantId, catalogId }).pipe(map((d) => d.pinnedTenantsForCatalog));
  }

  getTenantAssignments(catalogId: string): Observable<TenantCatalogAssignment[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantCatalogAssignments: TenantCatalogAssignment[] }>(`
      query TenantCatalogAssignments($tenantId: UUID!, $catalogId: UUID!) {
        tenantCatalogAssignments(tenantId: $tenantId, catalogId: $catalogId) {
          tenantId assignmentType catalogId cloneCatalogId
          additions deletions isCustomized
        }
      }
    `, { tenantId, catalogId }).pipe(map((d) => d.tenantCatalogAssignments));
  }

  getCatalogDiff(sourceCatalogId: string, cloneCatalogId: string): Observable<CatalogDiff> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ catalogDiff: CatalogDiff }>(`
      query CatalogDiff($tenantId: UUID!, $sourceCatalogId: UUID!, $cloneCatalogId: UUID!) {
        catalogDiff(tenantId: $tenantId, sourceCatalogId: $sourceCatalogId, cloneCatalogId: $cloneCatalogId) {
          sourceCatalogId cloneCatalogId
          additions { ${CATALOG_ITEM_FIELDS} }
          deletions { ${CATALOG_ITEM_FIELDS} }
          common { ${CATALOG_ITEM_FIELDS} }
        }
      }
    `, { tenantId, sourceCatalogId, cloneCatalogId }).pipe(map((d) => d.catalogDiff));
  }

  // ── Tenant Catalog Pins (for specific tenant) ──────────────────

  listCatalogPinsForTenant(targetTenantId: string): Observable<TenantCatalogPin[]> {
    return this.gql<{ tenantCatalogPins: TenantCatalogPin[] }>(`
      query TenantCatalogPins($tenantId: UUID!) {
        tenantCatalogPins(tenantId: $tenantId) { ${CATALOG_PIN_FIELDS} }
      }
    `, { tenantId: targetTenantId }).pipe(map((d) => d.tenantCatalogPins));
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
