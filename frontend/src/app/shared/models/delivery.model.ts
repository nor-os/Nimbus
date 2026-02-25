/**
 * Overview: TypeScript interfaces for the service delivery engine data models.
 * Architecture: Shared model definitions for delivery regions, region acceptance,
 *     staff profiles, rate cards, activity templates, estimations, price list
 *     templates, and profitability analytics (Section 8)
 * Dependencies: None
 * Concepts: Delivery regions, region acceptance, staff profiles, internal rate cards,
 *     activity templates, service estimations, price list templates, profitability
 */

// ── Enums ───────────────────────────────────────────────────────────

export type ServiceType = 'resource' | 'labor';

export type OperatingModel = 'regional' | 'global' | 'follow_the_sun';

export type CoverageModel = 'business_hours' | 'extended' | '24x7';

export type RegionAcceptanceType = 'preferred' | 'accepted' | 'blocked';

export type EstimationStatus = 'draft' | 'submitted' | 'approved' | 'rejected';

export type PriceListTemplateStatus = 'draft' | 'active' | 'archived';

// ── Delivery Regions ────────────────────────────────────────────────

export interface DeliveryRegion {
  id: string;
  tenantId: string | null;
  parentRegionId: string | null;
  name: string;
  displayName: string;
  code: string;
  timezone: string | null;
  countryCode: string | null;
  isSystem: boolean;
  isActive: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface DeliveryRegionList {
  items: DeliveryRegion[];
  total: number;
}

export interface DeliveryRegionCreateInput {
  parentRegionId?: string | null;
  name: string;
  displayName: string;
  code: string;
  timezone?: string | null;
  countryCode?: string | null;
  sortOrder?: number;
}

export interface DeliveryRegionUpdateInput {
  displayName?: string | null;
  timezone?: string | null;
  countryCode?: string | null;
  isActive?: boolean | null;
  sortOrder?: number | null;
}

// ── Region Acceptance ───────────────────────────────────────────────

export interface RegionAcceptanceTemplate {
  id: string;
  tenantId: string | null;
  name: string;
  description: string | null;
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RegionAcceptanceTemplateRule {
  id: string;
  templateId: string;
  deliveryRegionId: string;
  acceptanceType: RegionAcceptanceType;
  reason: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TenantRegionAcceptance {
  id: string;
  tenantId: string;
  deliveryRegionId: string;
  acceptanceType: RegionAcceptanceType;
  reason: string | null;
  isComplianceEnforced: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface EffectiveRegionAcceptance {
  acceptanceType: RegionAcceptanceType;
  reason: string | null;
  isComplianceEnforced: boolean;
  source: string;
}

export interface RegionAcceptanceTemplateCreateInput {
  name: string;
  description?: string | null;
}

export interface RegionAcceptanceTemplateRuleCreateInput {
  deliveryRegionId: string;
  acceptanceType: RegionAcceptanceType;
  reason?: string | null;
}

export interface TenantRegionAcceptanceCreateInput {
  deliveryRegionId: string;
  acceptanceType: RegionAcceptanceType;
  reason?: string | null;
  isComplianceEnforced?: boolean;
}

// ── Staff Profiles & Rate Cards ─────────────────────────────────────

// ── Organizational Units ───────────────────────────────────────────

export interface OrganizationalUnit {
  id: string;
  tenantId: string | null;
  parentId: string | null;
  name: string;
  displayName: string;
  costCenter: string | null;
  isActive: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationalUnitCreateInput {
  name: string;
  displayName: string;
  parentId?: string | null;
  costCenter?: string | null;
  sortOrder?: number;
}

export interface OrganizationalUnitUpdateInput {
  displayName?: string | null;
  costCenter?: string | null;
  isActive?: boolean | null;
  sortOrder?: number | null;
}

// ── Staff Profiles & Rate Cards ─────────────────────────────────────

export interface StaffProfile {
  id: string;
  tenantId: string | null;
  orgUnitId: string | null;
  name: string;
  displayName: string;
  profileId: string | null;
  costCenter: string | null;
  defaultHourlyCost: number | null;
  defaultCurrency: string | null;
  isSystem: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface StaffProfileCreateInput {
  name: string;
  displayName: string;
  orgUnitId?: string | null;
  profileId?: string | null;
  costCenter?: string | null;
  defaultHourlyCost?: number | null;
  defaultCurrency?: string | null;
  sortOrder?: number;
}

export interface StaffProfileUpdateInput {
  displayName?: string | null;
  orgUnitId?: string | null;
  profileId?: string | null;
  costCenter?: string | null;
  defaultHourlyCost?: number | null;
  defaultCurrency?: string | null;
  sortOrder?: number | null;
}

export interface InternalRateCard {
  id: string;
  tenantId: string;
  staffProfileId: string;
  deliveryRegionId: string;
  hourlyCost: number;
  hourlySellRate: number | null;
  currency: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface InternalRateCardCreateInput {
  staffProfileId: string;
  deliveryRegionId: string;
  hourlyCost: number;
  hourlySellRate?: number | null;
  currency?: string;
  effectiveFrom: string;
  effectiveTo?: string | null;
}

// ── Activity Templates ──────────────────────────────────────────────

export interface LinkedAutomatedActivity {
  id: string;
  name: string;
  slug: string;
  category: string | null;
  operationKind: string;
  implementationType: string;
  isSystem: boolean;
}

export interface ActivityTemplate {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  version: number;
  automatedActivityId: string | null;
  automatedActivity: LinkedAutomatedActivity | null;
  definitions: ActivityDefinition[];
  createdAt: string;
  updatedAt: string;
}

export interface ActivityDefinition {
  id: string;
  templateId: string;
  name: string;
  staffProfileId: string;
  estimatedHours: number;
  sortOrder: number;
  isOptional: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ActivityTemplateList {
  items: ActivityTemplate[];
  total: number;
}

export interface ActivityTemplateCreateInput {
  name: string;
  description?: string | null;
}

export interface ActivityDefinitionCreateInput {
  name: string;
  staffProfileId: string;
  estimatedHours: number;
  sortOrder?: number;
  isOptional?: boolean;
}

export interface ActivityDefinitionUpdateInput {
  name?: string | null;
  staffProfileId?: string | null;
  estimatedHours?: number | null;
  sortOrder?: number | null;
  isOptional?: boolean | null;
}

// ── Service Processes ──────────────────────────────────────────────

export interface ServiceProcess {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  version: number;
  sortOrder: number;
  activityLinks: ProcessActivityLink[];
  createdAt: string;
  updatedAt: string;
}

export interface ProcessActivityLink {
  id: string;
  processId: string;
  activityTemplateId: string;
  sortOrder: number;
  isRequired: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceProcessList {
  items: ServiceProcess[];
  total: number;
}

export interface ServiceProcessCreateInput {
  name: string;
  description?: string | null;
  sortOrder?: number;
}

export interface ServiceProcessUpdateInput {
  name?: string | null;
  description?: string | null;
  sortOrder?: number | null;
}

export interface ProcessActivityLinkCreateInput {
  activityTemplateId: string;
  sortOrder?: number;
  isRequired?: boolean;
}

export interface ServiceProcessAssignment {
  id: string;
  tenantId: string;
  serviceOfferingId: string;
  processId: string;
  coverageModel: string | null;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceProcessAssignmentCreateInput {
  serviceOfferingId: string;
  processId: string;
  coverageModel?: string | null;
  isDefault?: boolean;
}

// ── Estimations ─────────────────────────────────────────────────────

export interface ServiceEstimation {
  id: string;
  tenantId: string;
  clientTenantId: string;
  serviceOfferingId: string;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  priceListId: string | null;
  status: EstimationStatus;
  quantity: number;
  sellPricePerUnit: number;
  sellCurrency: string;
  totalEstimatedCost: number | null;
  totalSellPrice: number | null;
  marginAmount: number | null;
  marginPercent: number | null;
  approvedBy: string | null;
  approvedAt: string | null;
  lineItems: EstimationLineItem[];
  createdAt: string;
  updatedAt: string;
}

export interface EstimationLineItem {
  id: string;
  estimationId: string;
  activityDefinitionId: string | null;
  rateCardId: string | null;
  name: string;
  staffProfileId: string;
  deliveryRegionId: string;
  estimatedHours: number;
  hourlyRate: number;
  rateCurrency: string;
  lineCost: number;
  actualHours: number | null;
  actualCost: number | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface EstimationList {
  items: ServiceEstimation[];
  total: number;
}

export interface ServiceEstimationCreateInput {
  clientTenantId: string;
  serviceOfferingId: string;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  priceListId?: string | null;
  quantity?: number;
  sellPricePerUnit?: number;
  sellCurrency?: string;
}

export interface ServiceEstimationUpdateInput {
  quantity?: number | null;
  sellPricePerUnit?: number | null;
  sellCurrency?: string | null;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  priceListId?: string | null;
}

export interface EstimationLineItemCreateInput {
  name: string;
  staffProfileId: string;
  deliveryRegionId: string;
  estimatedHours: number;
  hourlyRate?: number | null;
  rateCardId?: string | null;
  rateCurrency?: string;
  sortOrder?: number;
  activityDefinitionId?: string | null;
}

// ── Price List Templates ────────────────────────────────────────────

export interface PriceListTemplate {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  regionAcceptanceTemplateId: string | null;
  status: PriceListTemplateStatus;
  items: PriceListTemplateItem[];
  createdAt: string;
  updatedAt: string;
}

export interface PriceListTemplateItem {
  id: string;
  templateId: string;
  serviceOfferingId: string;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  pricePerUnit: number;
  currency: string;
  minQuantity: number | null;
  maxQuantity: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PriceListTemplateList {
  items: PriceListTemplate[];
  total: number;
}

export interface PriceListTemplateCreateInput {
  name: string;
  description?: string | null;
  regionAcceptanceTemplateId?: string | null;
  status?: PriceListTemplateStatus;
}

export interface PriceListTemplateItemCreateInput {
  serviceOfferingId: string;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  pricePerUnit: number;
  currency?: string;
  minQuantity?: number | null;
  maxQuantity?: number | null;
}

// ── Profitability ───────────────────────────────────────────────────

export interface ProfitabilityOverview {
  totalRevenue: number;
  totalCost: number;
  totalMargin: number;
  marginPercent: number;
  estimationCount: number;
}

export interface ProfitabilityByEntity {
  entityId: string;
  entityName: string;
  totalRevenue: number;
  totalCost: number;
  marginAmount: number;
  marginPercent: number;
  estimationCount: number;
}
