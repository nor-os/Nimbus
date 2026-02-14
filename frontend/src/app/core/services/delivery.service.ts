/**
 * Overview: Delivery engine GraphQL service — queries and mutations for delivery regions,
 *     region acceptance, staff profiles, rate cards, activity templates, estimations,
 *     price list templates, and profitability analytics.
 * Architecture: Core service layer for service delivery data operations (Section 8)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for delivery engine entities. All queries are tenant-scoped.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  ActivityDefinition,
  ActivityDefinitionCreateInput,
  ActivityDefinitionUpdateInput,
  ActivityTemplate,
  ActivityTemplateCreateInput,
  ActivityTemplateList,
  DeliveryRegion,
  DeliveryRegionCreateInput,
  DeliveryRegionList,
  DeliveryRegionUpdateInput,
  EffectiveRegionAcceptance,
  EstimationLineItem,
  EstimationLineItemCreateInput,
  EstimationList,
  InternalRateCard,
  InternalRateCardCreateInput,
  OrganizationalUnit,
  OrganizationalUnitCreateInput,
  OrganizationalUnitUpdateInput,
  PriceListTemplate,
  PriceListTemplateCreateInput,
  PriceListTemplateItem,
  PriceListTemplateItemCreateInput,
  PriceListTemplateList,
  ProcessActivityLink,
  ProcessActivityLinkCreateInput,
  ProfitabilityByEntity,
  ProfitabilityOverview,
  RegionAcceptanceTemplate,
  RegionAcceptanceTemplateCreateInput,
  RegionAcceptanceTemplateRule,
  RegionAcceptanceTemplateRuleCreateInput,
  ServiceProcess,
  ServiceProcessAssignment,
  ServiceProcessAssignmentCreateInput,
  ServiceProcessCreateInput,
  ServiceProcessList,
  ServiceProcessUpdateInput,
  ServiceEstimation,
  ServiceEstimationCreateInput,
  ServiceEstimationUpdateInput,
  StaffProfile,
  StaffProfileCreateInput,
  StaffProfileUpdateInput,
  TenantRegionAcceptance,
  TenantRegionAcceptanceCreateInput,
} from '@shared/models/delivery.model';

// ── Field constants ─────────────────────────────────────────────────

const REGION_FIELDS = `
  id tenantId parentRegionId name displayName code timezone countryCode
  isSystem isActive sortOrder createdAt updatedAt
`;

const ACCEPTANCE_TEMPLATE_FIELDS = `
  id tenantId name description isSystem createdAt updatedAt
`;

const ACCEPTANCE_TEMPLATE_RULE_FIELDS = `
  id templateId deliveryRegionId acceptanceType reason createdAt updatedAt
`;

const TENANT_ACCEPTANCE_FIELDS = `
  id tenantId deliveryRegionId acceptanceType reason isComplianceEnforced
  createdAt updatedAt
`;

const EFFECTIVE_ACCEPTANCE_FIELDS = `
  acceptanceType reason isComplianceEnforced source
`;

const ORG_UNIT_FIELDS = `
  id tenantId parentId name displayName costCenter isActive sortOrder
  createdAt updatedAt
`;

const STAFF_PROFILE_FIELDS = `
  id tenantId orgUnitId name displayName profileId costCenter
  defaultHourlyCost defaultCurrency isSystem sortOrder createdAt updatedAt
`;

const RATE_CARD_FIELDS = `
  id tenantId staffProfileId deliveryRegionId hourlyCost hourlySellRate currency
  effectiveFrom effectiveTo createdAt updatedAt
`;

const ACTIVITY_DEFINITION_FIELDS = `
  id templateId name staffProfileId estimatedHours sortOrder isOptional
  createdAt updatedAt
`;

const ACTIVITY_TEMPLATE_FIELDS = `
  id tenantId name description version
  definitions { ${ACTIVITY_DEFINITION_FIELDS} }
  createdAt updatedAt
`;

const PROCESS_ACTIVITY_LINK_FIELDS = `
  id processId activityTemplateId sortOrder isRequired createdAt updatedAt
`;

const PROCESS_FIELDS = `
  id tenantId name description version sortOrder
  activityLinks { ${PROCESS_ACTIVITY_LINK_FIELDS} }
  createdAt updatedAt
`;

const ASSIGNMENT_FIELDS = `
  id tenantId serviceOfferingId processId coverageModel isDefault
  createdAt updatedAt
`;

const ESTIMATION_LINE_ITEM_FIELDS = `
  id estimationId activityDefinitionId rateCardId name staffProfileId deliveryRegionId
  estimatedHours hourlyRate rateCurrency lineCost actualHours actualCost
  sortOrder createdAt updatedAt
`;

const ESTIMATION_FIELDS = `
  id tenantId clientTenantId serviceOfferingId deliveryRegionId coverageModel
  priceListId status quantity sellPricePerUnit sellCurrency totalEstimatedCost totalSellPrice
  marginAmount marginPercent approvedBy approvedAt
  lineItems { ${ESTIMATION_LINE_ITEM_FIELDS} }
  createdAt updatedAt
`;

const PRICE_LIST_TEMPLATE_ITEM_FIELDS = `
  id templateId serviceOfferingId deliveryRegionId coverageModel pricePerUnit
  currency minQuantity maxQuantity createdAt updatedAt
`;

const PRICE_LIST_TEMPLATE_FIELDS = `
  id tenantId name description regionAcceptanceTemplateId status
  items { ${PRICE_LIST_TEMPLATE_ITEM_FIELDS} }
  createdAt updatedAt
`;

const PROFITABILITY_OVERVIEW_FIELDS = `
  totalRevenue totalCost totalMargin marginPercent estimationCount
`;

const PROFITABILITY_BY_ENTITY_FIELDS = `
  entityId entityName totalRevenue totalCost marginAmount marginPercent estimationCount
`;

@Injectable({ providedIn: 'root' })
export class DeliveryService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Delivery Regions ──────────────────────────────────────────────

  listRegions(filters?: {
    parentRegionId?: string;
    isActive?: boolean;
    offset?: number;
    limit?: number;
  }): Observable<DeliveryRegionList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deliveryRegions: DeliveryRegionList }>(`
      query DeliveryRegions(
        $tenantId: UUID!
        $parentRegionId: UUID
        $isActive: Boolean
        $offset: Int
        $limit: Int
      ) {
        deliveryRegions(
          tenantId: $tenantId
          parentRegionId: $parentRegionId
          isActive: $isActive
          offset: $offset
          limit: $limit
        ) {
          items { ${REGION_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.deliveryRegions),
    );
  }

  getRegion(id: string): Observable<DeliveryRegion | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deliveryRegion: DeliveryRegion | null }>(`
      query DeliveryRegion($tenantId: UUID!, $id: UUID!) {
        deliveryRegion(tenantId: $tenantId, id: $id) {
          ${REGION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.deliveryRegion),
    );
  }

  getRegionChildren(id: string): Observable<DeliveryRegion[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deliveryRegionChildren: DeliveryRegion[] }>(`
      query DeliveryRegionChildren($tenantId: UUID!, $id: UUID!) {
        deliveryRegionChildren(tenantId: $tenantId, id: $id) {
          ${REGION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.deliveryRegionChildren),
    );
  }

  createRegion(input: DeliveryRegionCreateInput): Observable<DeliveryRegion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createDeliveryRegion: DeliveryRegion }>(`
      mutation CreateDeliveryRegion($tenantId: UUID!, $input: DeliveryRegionCreateInput!) {
        createDeliveryRegion(tenantId: $tenantId, input: $input) {
          ${REGION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createDeliveryRegion));
  }

  updateRegion(id: string, input: DeliveryRegionUpdateInput): Observable<DeliveryRegion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateDeliveryRegion: DeliveryRegion }>(`
      mutation UpdateDeliveryRegion($tenantId: UUID!, $id: UUID!, $input: DeliveryRegionUpdateInput!) {
        updateDeliveryRegion(tenantId: $tenantId, id: $id, input: $input) {
          ${REGION_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateDeliveryRegion));
  }

  deleteRegion(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteDeliveryRegion: boolean }>(`
      mutation DeleteDeliveryRegion($tenantId: UUID!, $id: UUID!) {
        deleteDeliveryRegion(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteDeliveryRegion));
  }

  // ── Region Acceptance Templates ───────────────────────────────────

  listAcceptanceTemplates(): Observable<RegionAcceptanceTemplate[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ regionAcceptanceTemplates: RegionAcceptanceTemplate[] }>(`
      query RegionAcceptanceTemplates($tenantId: UUID!) {
        regionAcceptanceTemplates(tenantId: $tenantId) {
          ${ACCEPTANCE_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.regionAcceptanceTemplates),
    );
  }

  listTemplateRules(templateId: string): Observable<RegionAcceptanceTemplateRule[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ regionAcceptanceTemplateRules: RegionAcceptanceTemplateRule[] }>(`
      query RegionAcceptanceTemplateRules($tenantId: UUID!, $templateId: UUID!) {
        regionAcceptanceTemplateRules(tenantId: $tenantId, templateId: $templateId) {
          ${ACCEPTANCE_TEMPLATE_RULE_FIELDS}
        }
      }
    `, { tenantId, templateId }).pipe(
      map((data) => data.regionAcceptanceTemplateRules),
    );
  }

  createAcceptanceTemplate(input: RegionAcceptanceTemplateCreateInput): Observable<RegionAcceptanceTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createRegionAcceptanceTemplate: RegionAcceptanceTemplate }>(`
      mutation CreateRegionAcceptanceTemplate($tenantId: UUID!, $input: RegionAcceptanceTemplateCreateInput!) {
        createRegionAcceptanceTemplate(tenantId: $tenantId, input: $input) {
          ${ACCEPTANCE_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createRegionAcceptanceTemplate));
  }

  deleteAcceptanceTemplate(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteRegionAcceptanceTemplate: boolean }>(`
      mutation DeleteRegionAcceptanceTemplate($tenantId: UUID!, $id: UUID!) {
        deleteRegionAcceptanceTemplate(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteRegionAcceptanceTemplate));
  }

  addTemplateRule(
    templateId: string,
    input: RegionAcceptanceTemplateRuleCreateInput,
  ): Observable<RegionAcceptanceTemplateRule> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addRegionAcceptanceTemplateRule: RegionAcceptanceTemplateRule }>(`
      mutation AddRegionAcceptanceTemplateRule(
        $tenantId: UUID!
        $templateId: UUID!
        $input: RegionAcceptanceTemplateRuleCreateInput!
      ) {
        addRegionAcceptanceTemplateRule(tenantId: $tenantId, templateId: $templateId, input: $input) {
          ${ACCEPTANCE_TEMPLATE_RULE_FIELDS}
        }
      }
    `, { tenantId, templateId, input }).pipe(map((d) => d.addRegionAcceptanceTemplateRule));
  }

  deleteTemplateRule(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteRegionAcceptanceTemplateRule: boolean }>(`
      mutation DeleteRegionAcceptanceTemplateRule($tenantId: UUID!, $id: UUID!) {
        deleteRegionAcceptanceTemplateRule(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteRegionAcceptanceTemplateRule));
  }

  // ── Tenant Region Acceptance ──────────────────────────────────────

  listTenantAcceptances(): Observable<TenantRegionAcceptance[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantRegionAcceptances: TenantRegionAcceptance[] }>(`
      query TenantRegionAcceptances($tenantId: UUID!) {
        tenantRegionAcceptances(tenantId: $tenantId) {
          ${TENANT_ACCEPTANCE_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.tenantRegionAcceptances),
    );
  }

  setTenantAcceptance(input: TenantRegionAcceptanceCreateInput): Observable<TenantRegionAcceptance> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ setTenantRegionAcceptance: TenantRegionAcceptance }>(`
      mutation SetTenantRegionAcceptance($tenantId: UUID!, $input: TenantRegionAcceptanceCreateInput!) {
        setTenantRegionAcceptance(tenantId: $tenantId, input: $input) {
          ${TENANT_ACCEPTANCE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.setTenantRegionAcceptance));
  }

  deleteTenantAcceptance(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTenantRegionAcceptance: boolean }>(`
      mutation DeleteTenantRegionAcceptance($tenantId: UUID!, $id: UUID!) {
        deleteTenantRegionAcceptance(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteTenantRegionAcceptance));
  }

  getEffectiveAcceptance(regionId: string): Observable<EffectiveRegionAcceptance> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ effectiveRegionAcceptance: EffectiveRegionAcceptance }>(`
      query EffectiveRegionAcceptance($tenantId: UUID!, $regionId: UUID!) {
        effectiveRegionAcceptance(tenantId: $tenantId, regionId: $regionId) {
          ${EFFECTIVE_ACCEPTANCE_FIELDS}
        }
      }
    `, { tenantId, regionId }).pipe(
      map((data) => data.effectiveRegionAcceptance),
    );
  }

  // ── Organizational Units ─────────────────────────────────────────

  listOrgUnits(): Observable<OrganizationalUnit[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ organizationalUnits: OrganizationalUnit[] }>(`
      query OrganizationalUnits($tenantId: UUID) {
        organizationalUnits(tenantId: $tenantId) {
          ${ORG_UNIT_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.organizationalUnits),
    );
  }

  createOrgUnit(input: OrganizationalUnitCreateInput): Observable<OrganizationalUnit> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createOrganizationalUnit: OrganizationalUnit }>(`
      mutation CreateOrganizationalUnit($tenantId: UUID!, $input: OrganizationalUnitCreateInput!) {
        createOrganizationalUnit(tenantId: $tenantId, input: $input) {
          ${ORG_UNIT_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createOrganizationalUnit));
  }

  updateOrgUnit(id: string, input: OrganizationalUnitUpdateInput): Observable<OrganizationalUnit> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateOrganizationalUnit: OrganizationalUnit }>(`
      mutation UpdateOrganizationalUnit($tenantId: UUID!, $id: UUID!, $input: OrganizationalUnitUpdateInput!) {
        updateOrganizationalUnit(tenantId: $tenantId, id: $id, input: $input) {
          ${ORG_UNIT_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateOrganizationalUnit));
  }

  deleteOrgUnit(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteOrganizationalUnit: boolean }>(`
      mutation DeleteOrganizationalUnit($tenantId: UUID!, $id: UUID!) {
        deleteOrganizationalUnit(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteOrganizationalUnit));
  }

  // ── Staff Profiles ────────────────────────────────────────────────

  listStaffProfiles(): Observable<StaffProfile[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ staffProfiles: StaffProfile[] }>(`
      query StaffProfiles($tenantId: UUID!) {
        staffProfiles(tenantId: $tenantId) {
          ${STAFF_PROFILE_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.staffProfiles),
    );
  }

  createStaffProfile(input: StaffProfileCreateInput): Observable<StaffProfile> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createStaffProfile: StaffProfile }>(`
      mutation CreateStaffProfile($tenantId: UUID!, $input: StaffProfileCreateInput!) {
        createStaffProfile(tenantId: $tenantId, input: $input) {
          ${STAFF_PROFILE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createStaffProfile));
  }

  updateStaffProfile(id: string, input: StaffProfileUpdateInput): Observable<StaffProfile> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateStaffProfile: StaffProfile }>(`
      mutation UpdateStaffProfile($tenantId: UUID!, $id: UUID!, $input: StaffProfileUpdateInput!) {
        updateStaffProfile(tenantId: $tenantId, id: $id, input: $input) {
          ${STAFF_PROFILE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateStaffProfile));
  }

  deleteStaffProfile(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteStaffProfile: boolean }>(`
      mutation DeleteStaffProfile($tenantId: UUID!, $id: UUID!) {
        deleteStaffProfile(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteStaffProfile));
  }

  staffProfileActivities(staffProfileId: string): Observable<ActivityDefinition[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ staffProfileActivities: ActivityDefinition[] }>(`
      query StaffProfileActivities($tenantId: UUID!, $staffProfileId: UUID!) {
        staffProfileActivities(tenantId: $tenantId, staffProfileId: $staffProfileId) {
          ${ACTIVITY_DEFINITION_FIELDS}
        }
      }
    `, { tenantId, staffProfileId }).pipe(
      map((data) => data.staffProfileActivities),
    );
  }

  // ── Internal Rate Cards ───────────────────────────────────────────

  listRateCards(filters?: {
    staffProfileId?: string;
    deliveryRegionId?: string;
  }): Observable<InternalRateCard[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ internalRateCards: InternalRateCard[] }>(`
      query InternalRateCards(
        $tenantId: UUID!
        $staffProfileId: UUID
        $deliveryRegionId: UUID
      ) {
        internalRateCards(
          tenantId: $tenantId
          staffProfileId: $staffProfileId
          deliveryRegionId: $deliveryRegionId
        ) {
          ${RATE_CARD_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.internalRateCards),
    );
  }

  createRateCard(input: InternalRateCardCreateInput): Observable<InternalRateCard> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createInternalRateCard: InternalRateCard }>(`
      mutation CreateInternalRateCard($tenantId: UUID!, $input: InternalRateCardCreateInput!) {
        createInternalRateCard(tenantId: $tenantId, input: $input) {
          ${RATE_CARD_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createInternalRateCard));
  }

  deleteRateCard(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteInternalRateCard: boolean }>(`
      mutation DeleteInternalRateCard($tenantId: UUID!, $id: UUID!) {
        deleteInternalRateCard(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteInternalRateCard));
  }

  // ── Activity Templates ────────────────────────────────────────────

  listActivityTemplates(filters?: {
    offset?: number;
    limit?: number;
  }): Observable<ActivityTemplateList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ activityTemplates: ActivityTemplateList }>(`
      query ActivityTemplates($tenantId: UUID!, $offset: Int, $limit: Int) {
        activityTemplates(tenantId: $tenantId, offset: $offset, limit: $limit) {
          items { ${ACTIVITY_TEMPLATE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.activityTemplates),
    );
  }

  getActivityTemplate(id: string): Observable<ActivityTemplate | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ activityTemplate: ActivityTemplate | null }>(`
      query ActivityTemplate($tenantId: UUID!, $id: UUID!) {
        activityTemplate(tenantId: $tenantId, id: $id) {
          ${ACTIVITY_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.activityTemplate),
    );
  }

  createActivityTemplate(input: ActivityTemplateCreateInput): Observable<ActivityTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createActivityTemplate: ActivityTemplate }>(`
      mutation CreateActivityTemplate($tenantId: UUID!, $input: ActivityTemplateCreateInput!) {
        createActivityTemplate(tenantId: $tenantId, input: $input) {
          ${ACTIVITY_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createActivityTemplate));
  }

  updateActivityTemplate(
    id: string,
    input: ActivityTemplateCreateInput,
  ): Observable<ActivityTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateActivityTemplate: ActivityTemplate }>(`
      mutation UpdateActivityTemplate(
        $tenantId: UUID!
        $id: UUID!
        $input: ActivityTemplateUpdateInput!
      ) {
        updateActivityTemplate(tenantId: $tenantId, id: $id, input: $input) {
          ${ACTIVITY_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateActivityTemplate));
  }

  deleteActivityTemplate(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteActivityTemplate: boolean }>(`
      mutation DeleteActivityTemplate($tenantId: UUID!, $id: UUID!) {
        deleteActivityTemplate(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteActivityTemplate));
  }

  cloneActivityTemplate(id: string): Observable<ActivityTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneActivityTemplate: ActivityTemplate }>(`
      mutation CloneActivityTemplate($tenantId: UUID!, $id: UUID!) {
        cloneActivityTemplate(tenantId: $tenantId, id: $id) {
          ${ACTIVITY_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.cloneActivityTemplate));
  }

  // ── Activity Definitions ──────────────────────────────────────────

  addActivityDefinition(
    templateId: string,
    input: ActivityDefinitionCreateInput,
  ): Observable<ActivityDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addActivityDefinition: ActivityDefinition }>(`
      mutation AddActivityDefinition(
        $tenantId: UUID!
        $templateId: UUID!
        $input: ActivityDefinitionCreateInput!
      ) {
        addActivityDefinition(tenantId: $tenantId, templateId: $templateId, input: $input) {
          ${ACTIVITY_DEFINITION_FIELDS}
        }
      }
    `, { tenantId, templateId, input }).pipe(map((d) => d.addActivityDefinition));
  }

  updateActivityDefinition(
    id: string,
    input: ActivityDefinitionUpdateInput,
  ): Observable<ActivityDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateActivityDefinition: ActivityDefinition }>(`
      mutation UpdateActivityDefinition(
        $tenantId: UUID!
        $id: UUID!
        $input: ActivityDefinitionUpdateInput!
      ) {
        updateActivityDefinition(tenantId: $tenantId, id: $id, input: $input) {
          ${ACTIVITY_DEFINITION_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateActivityDefinition));
  }

  deleteActivityDefinition(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteActivityDefinition: boolean }>(`
      mutation DeleteActivityDefinition($tenantId: UUID!, $id: UUID!) {
        deleteActivityDefinition(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteActivityDefinition));
  }

  // ── Service Processes ────────────────────────────────────────────

  listProcesses(filters?: {
    offset?: number;
    limit?: number;
  }): Observable<ServiceProcessList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceProcesses: ServiceProcessList }>(`
      query ServiceProcesses($tenantId: UUID!, $offset: Int, $limit: Int) {
        serviceProcesses(tenantId: $tenantId, offset: $offset, limit: $limit) {
          items { ${PROCESS_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.serviceProcesses),
    );
  }

  getProcess(id: string): Observable<ServiceProcess | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceProcess: ServiceProcess | null }>(`
      query ServiceProcess($tenantId: UUID!, $id: UUID!) {
        serviceProcess(tenantId: $tenantId, id: $id) {
          ${PROCESS_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.serviceProcess),
    );
  }

  createProcess(input: ServiceProcessCreateInput): Observable<ServiceProcess> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceProcess: ServiceProcess }>(`
      mutation CreateServiceProcess($tenantId: UUID!, $input: ServiceProcessCreateInput!) {
        createServiceProcess(tenantId: $tenantId, input: $input) {
          ${PROCESS_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceProcess));
  }

  updateProcess(id: string, input: ServiceProcessUpdateInput): Observable<ServiceProcess> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateServiceProcess: ServiceProcess }>(`
      mutation UpdateServiceProcess($tenantId: UUID!, $id: UUID!, $input: ServiceProcessUpdateInput!) {
        updateServiceProcess(tenantId: $tenantId, id: $id, input: $input) {
          ${PROCESS_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateServiceProcess));
  }

  deleteProcess(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceProcess: boolean }>(`
      mutation DeleteServiceProcess($tenantId: UUID!, $id: UUID!) {
        deleteServiceProcess(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceProcess));
  }

  // ── Process Activity Links ─────────────────────────────────────

  addProcessActivityLink(
    processId: string,
    input: ProcessActivityLinkCreateInput,
  ): Observable<ProcessActivityLink> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addProcessActivityLink: ProcessActivityLink }>(`
      mutation AddProcessActivityLink(
        $tenantId: UUID!
        $processId: UUID!
        $input: ProcessActivityLinkCreateInput!
      ) {
        addProcessActivityLink(tenantId: $tenantId, processId: $processId, input: $input) {
          ${PROCESS_ACTIVITY_LINK_FIELDS}
        }
      }
    `, { tenantId, processId, input }).pipe(map((d) => d.addProcessActivityLink));
  }

  removeProcessActivityLink(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeProcessActivityLink: boolean }>(`
      mutation RemoveProcessActivityLink($tenantId: UUID!, $id: UUID!) {
        removeProcessActivityLink(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.removeProcessActivityLink));
  }

  // ── Service Process Assignments ────────────────────────────────

  listAssignments(serviceOfferingId?: string): Observable<ServiceProcessAssignment[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ serviceProcessAssignments: ServiceProcessAssignment[] }>(`
      query ServiceProcessAssignments($tenantId: UUID!, $serviceOfferingId: UUID) {
        serviceProcessAssignments(tenantId: $tenantId, serviceOfferingId: $serviceOfferingId) {
          ${ASSIGNMENT_FIELDS}
        }
      }
    `, { tenantId, serviceOfferingId }).pipe(
      map((data) => data.serviceProcessAssignments),
    );
  }

  createAssignment(input: ServiceProcessAssignmentCreateInput): Observable<ServiceProcessAssignment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createServiceProcessAssignment: ServiceProcessAssignment }>(`
      mutation CreateServiceProcessAssignment(
        $tenantId: UUID!
        $input: ServiceProcessAssignmentCreateInput!
      ) {
        createServiceProcessAssignment(tenantId: $tenantId, input: $input) {
          ${ASSIGNMENT_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createServiceProcessAssignment));
  }

  deleteAssignment(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteServiceProcessAssignment: boolean }>(`
      mutation DeleteServiceProcessAssignment($tenantId: UUID!, $id: UUID!) {
        deleteServiceProcessAssignment(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteServiceProcessAssignment));
  }

  // ── Service Estimations ───────────────────────────────────────────

  listEstimations(filters?: {
    clientTenantId?: string;
    serviceOfferingId?: string;
    status?: string;
    offset?: number;
    limit?: number;
  }): Observable<EstimationList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ estimations: EstimationList }>(`
      query Estimations(
        $tenantId: UUID!
        $clientTenantId: UUID
        $serviceOfferingId: UUID
        $status: String
        $offset: Int
        $limit: Int
      ) {
        estimations(
          tenantId: $tenantId
          clientTenantId: $clientTenantId
          serviceOfferingId: $serviceOfferingId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          items { ${ESTIMATION_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.estimations),
    );
  }

  getEstimation(id: string): Observable<ServiceEstimation | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ estimation: ServiceEstimation | null }>(`
      query Estimation($tenantId: UUID!, $id: UUID!) {
        estimation(tenantId: $tenantId, id: $id) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.estimation),
    );
  }

  createEstimation(input: ServiceEstimationCreateInput): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEstimation: ServiceEstimation }>(`
      mutation CreateEstimation($tenantId: UUID!, $input: ServiceEstimationCreateInput!) {
        createEstimation(tenantId: $tenantId, input: $input) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createEstimation));
  }

  updateEstimation(id: string, input: ServiceEstimationUpdateInput): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateEstimation: ServiceEstimation }>(`
      mutation UpdateEstimation(
        $tenantId: UUID!
        $id: UUID!
        $input: ServiceEstimationUpdateInput!
      ) {
        updateEstimation(tenantId: $tenantId, id: $id, input: $input) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateEstimation));
  }

  // ── Estimation Line Items ─────────────────────────────────────────

  addLineItem(
    estimationId: string,
    input: EstimationLineItemCreateInput,
  ): Observable<EstimationLineItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addEstimationLineItem: EstimationLineItem }>(`
      mutation AddEstimationLineItem(
        $tenantId: UUID!
        $estimationId: UUID!
        $input: EstimationLineItemCreateInput!
      ) {
        addEstimationLineItem(tenantId: $tenantId, estimationId: $estimationId, input: $input) {
          ${ESTIMATION_LINE_ITEM_FIELDS}
        }
      }
    `, { tenantId, estimationId, input }).pipe(map((d) => d.addEstimationLineItem));
  }

  updateLineItem(
    id: string,
    input: Partial<EstimationLineItemCreateInput>,
  ): Observable<EstimationLineItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateEstimationLineItem: EstimationLineItem }>(`
      mutation UpdateEstimationLineItem(
        $tenantId: UUID!
        $id: UUID!
        $input: EstimationLineItemUpdateInput!
      ) {
        updateEstimationLineItem(tenantId: $tenantId, id: $id, input: $input) {
          ${ESTIMATION_LINE_ITEM_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updateEstimationLineItem));
  }

  deleteLineItem(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEstimationLineItem: boolean }>(`
      mutation DeleteEstimationLineItem($tenantId: UUID!, $id: UUID!) {
        deleteEstimationLineItem(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deleteEstimationLineItem));
  }

  // ── Estimation Lifecycle ──────────────────────────────────────────

  submitEstimation(id: string): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ submitEstimation: ServiceEstimation }>(`
      mutation SubmitEstimation($tenantId: UUID!, $id: UUID!) {
        submitEstimation(tenantId: $tenantId, id: $id) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.submitEstimation));
  }

  approveEstimation(id: string): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ approveEstimation: ServiceEstimation }>(`
      mutation ApproveEstimation($tenantId: UUID!, $id: UUID!) {
        approveEstimation(tenantId: $tenantId, id: $id) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.approveEstimation));
  }

  rejectEstimation(id: string): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ rejectEstimation: ServiceEstimation }>(`
      mutation RejectEstimation($tenantId: UUID!, $id: UUID!) {
        rejectEstimation(tenantId: $tenantId, id: $id) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(map((d) => d.rejectEstimation));
  }

  // ── Estimation Process Import & Rate Refresh ────────────────────────

  resolveEffectiveRate(
    staffProfileId: string,
    deliveryRegionId: string,
  ): Observable<InternalRateCard | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ resolveEffectiveRate: InternalRateCard | null }>(`
      query ResolveEffectiveRate(
        $tenantId: UUID!
        $staffProfileId: UUID!
        $deliveryRegionId: UUID!
      ) {
        resolveEffectiveRate(
          tenantId: $tenantId
          staffProfileId: $staffProfileId
          deliveryRegionId: $deliveryRegionId
        ) {
          ${RATE_CARD_FIELDS}
        }
      }
    `, { tenantId, staffProfileId, deliveryRegionId }).pipe(
      map((data) => data.resolveEffectiveRate),
    );
  }

  importProcessToEstimation(
    estimationId: string,
    processId: string,
    deliveryRegionId?: string | null,
  ): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ importProcessToEstimation: ServiceEstimation }>(`
      mutation ImportProcessToEstimation(
        $tenantId: UUID!
        $estimationId: UUID!
        $processId: UUID!
        $deliveryRegionId: UUID
      ) {
        importProcessToEstimation(
          tenantId: $tenantId
          estimationId: $estimationId
          processId: $processId
          deliveryRegionId: $deliveryRegionId
        ) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, estimationId, processId, deliveryRegionId }).pipe(
      map((d) => d.importProcessToEstimation),
    );
  }

  refreshEstimationRates(estimationId: string): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ refreshEstimationRates: ServiceEstimation }>(`
      mutation RefreshEstimationRates($tenantId: UUID!, $estimationId: UUID!) {
        refreshEstimationRates(tenantId: $tenantId, estimationId: $estimationId) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, estimationId }).pipe(
      map((d) => d.refreshEstimationRates),
    );
  }

  refreshEstimationPrices(estimationId: string): Observable<ServiceEstimation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ refreshEstimationPrices: ServiceEstimation }>(`
      mutation RefreshEstimationPrices($tenantId: UUID!, $estimationId: UUID!) {
        refreshEstimationPrices(tenantId: $tenantId, estimationId: $estimationId) {
          ${ESTIMATION_FIELDS}
        }
      }
    `, { tenantId, estimationId }).pipe(
      map((d) => d.refreshEstimationPrices),
    );
  }

  // ── Price List Templates ──────────────────────────────────────────

  listPriceListTemplates(filters?: {
    status?: string;
    offset?: number;
    limit?: number;
  }): Observable<PriceListTemplateList> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ priceListTemplates: PriceListTemplateList }>(`
      query PriceListTemplates(
        $tenantId: UUID!
        $status: String
        $offset: Int
        $limit: Int
      ) {
        priceListTemplates(
          tenantId: $tenantId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          items { ${PRICE_LIST_TEMPLATE_FIELDS} }
          total
        }
      }
    `, { tenantId, ...filters }).pipe(
      map((data) => data.priceListTemplates),
    );
  }

  getPriceListTemplate(id: string): Observable<PriceListTemplate | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ priceListTemplate: PriceListTemplate | null }>(`
      query PriceListTemplate($tenantId: UUID!, $id: UUID!) {
        priceListTemplate(tenantId: $tenantId, id: $id) {
          ${PRICE_LIST_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.priceListTemplate),
    );
  }

  createPriceListTemplate(input: PriceListTemplateCreateInput): Observable<PriceListTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createPriceListTemplate: PriceListTemplate }>(`
      mutation CreatePriceListTemplate($tenantId: UUID!, $input: PriceListTemplateCreateInput!) {
        createPriceListTemplate(tenantId: $tenantId, input: $input) {
          ${PRICE_LIST_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createPriceListTemplate));
  }

  updatePriceListTemplate(
    id: string,
    input: Partial<PriceListTemplateCreateInput>,
  ): Observable<PriceListTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updatePriceListTemplate: PriceListTemplate }>(`
      mutation UpdatePriceListTemplate(
        $tenantId: UUID!
        $id: UUID!
        $input: PriceListTemplateUpdateInput!
      ) {
        updatePriceListTemplate(tenantId: $tenantId, id: $id, input: $input) {
          ${PRICE_LIST_TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(map((d) => d.updatePriceListTemplate));
  }

  deletePriceListTemplate(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePriceListTemplate: boolean }>(`
      mutation DeletePriceListTemplate($tenantId: UUID!, $id: UUID!) {
        deletePriceListTemplate(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deletePriceListTemplate));
  }

  // ── Price List Template Items ─────────────────────────────────────

  addTemplateItem(
    templateId: string,
    input: PriceListTemplateItemCreateInput,
  ): Observable<PriceListTemplateItem> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addPriceListTemplateItem: PriceListTemplateItem }>(`
      mutation AddPriceListTemplateItem(
        $tenantId: UUID!
        $templateId: UUID!
        $input: PriceListTemplateItemCreateInput!
      ) {
        addPriceListTemplateItem(tenantId: $tenantId, templateId: $templateId, input: $input) {
          ${PRICE_LIST_TEMPLATE_ITEM_FIELDS}
        }
      }
    `, { tenantId, templateId, input }).pipe(map((d) => d.addPriceListTemplateItem));
  }

  deleteTemplateItem(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deletePriceListTemplateItem: boolean }>(`
      mutation DeletePriceListTemplateItem($tenantId: UUID!, $id: UUID!) {
        deletePriceListTemplateItem(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(map((d) => d.deletePriceListTemplateItem));
  }

  cloneTemplateToPriceList(
    templateId: string,
  ): Observable<{ priceListId: string }> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ clonePriceListTemplateToPriceList: { priceListId: string } }>(`
      mutation ClonePriceListTemplateToPriceList(
        $tenantId: UUID!
        $templateId: UUID!
      ) {
        clonePriceListTemplateToPriceList(
          tenantId: $tenantId
          templateId: $templateId
        ) {
          priceListId
        }
      }
    `, { tenantId, templateId }).pipe(
      map((d) => d.clonePriceListTemplateToPriceList),
    );
  }

  // ── Profitability ─────────────────────────────────────────────────

  getProfitabilityOverview(): Observable<ProfitabilityOverview> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ profitabilityOverview: ProfitabilityOverview }>(`
      query ProfitabilityOverview($tenantId: UUID!) {
        profitabilityOverview(tenantId: $tenantId) {
          ${PROFITABILITY_OVERVIEW_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.profitabilityOverview),
    );
  }

  getProfitabilityByClient(): Observable<ProfitabilityByEntity[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ profitabilityByClient: ProfitabilityByEntity[] }>(`
      query ProfitabilityByClient($tenantId: UUID!) {
        profitabilityByClient(tenantId: $tenantId) {
          ${PROFITABILITY_BY_ENTITY_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.profitabilityByClient),
    );
  }

  getProfitabilityByRegion(): Observable<ProfitabilityByEntity[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ profitabilityByRegion: ProfitabilityByEntity[] }>(`
      query ProfitabilityByRegion($tenantId: UUID!) {
        profitabilityByRegion(tenantId: $tenantId) {
          ${PROFITABILITY_BY_ENTITY_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.profitabilityByRegion),
    );
  }

  getProfitabilityByService(): Observable<ProfitabilityByEntity[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ profitabilityByService: ProfitabilityByEntity[] }>(`
      query ProfitabilityByService($tenantId: UUID!) {
        profitabilityByService(tenantId: $tenantId) {
          ${PROFITABILITY_BY_ENTITY_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.profitabilityByService),
    );
  }

  // ── GraphQL helper ────────────────────────────────────────────────

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
