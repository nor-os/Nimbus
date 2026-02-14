/**
 * Overview: TypeScript interfaces for CMDB data models.
 * Architecture: Shared model definitions (Section 8)
 * Dependencies: None
 * Concepts: CI classes, configuration items, relationships, snapshots, templates, catalog
 */

// ── Enums ───────────────────────────────────────────────────────────

export type LifecycleState = 'planned' | 'active' | 'maintenance' | 'retired' | 'deleted';

export type MeasuringUnit = 'hour' | 'day' | 'month' | 'gb' | 'request' | 'user' | 'instance';

// ── CI Classes ──────────────────────────────────────────────────────

export interface CIClass {
  id: string;
  tenantId: string | null;
  name: string;
  displayName: string;
  parentClassId: string | null;
  semanticTypeId: string | null;
  schemaDef: Record<string, unknown> | null;
  icon: string | null;
  isSystem: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CIAttributeDefinition {
  id: string;
  ciClassId: string;
  name: string;
  displayName: string;
  dataType: string;
  isRequired: boolean;
  defaultValue: unknown | null;
  validationRules: Record<string, unknown> | null;
  sortOrder: number;
}

export interface CIClassDetail {
  id: string;
  tenantId: string | null;
  name: string;
  displayName: string;
  parentClassId: string | null;
  semanticTypeId: string | null;
  schemaDef: Record<string, unknown> | null;
  icon: string | null;
  isSystem: boolean;
  isActive: boolean;
  attributeDefinitions: CIAttributeDefinition[];
  createdAt: string;
  updatedAt: string;
}

// ── Configuration Items ─────────────────────────────────────────────

export interface ConfigurationItem {
  id: string;
  tenantId: string;
  ciClassId: string;
  ciClassName: string;
  compartmentId: string | null;
  name: string;
  description: string | null;
  lifecycleState: LifecycleState;
  attributes: Record<string, unknown>;
  tags: Record<string, unknown>;
  cloudResourceId: string | null;
  pulumiUrn: string | null;
  backendId: string | null;
  backendName: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CIList {
  items: ConfigurationItem[];
  total: number;
}

// ── Relationship Types ──────────────────────────────────────────────

export interface RelationshipType {
  id: string;
  name: string;
  displayName: string;
  inverseName: string;
  description: string | null;
  sourceClassIds: string[] | null;
  targetClassIds: string[] | null;
  isSystem: boolean;
  domain: string;
  sourceEntityType: string;
  targetEntityType: string;
  sourceSemanticTypes: string[] | null;
  targetSemanticTypes: string[] | null;
  sourceSemanticCategories: string[] | null;
  targetSemanticCategories: string[] | null;
  createdAt: string;
  updatedAt: string;
}

// ── CI Relationships ────────────────────────────────────────────────

export interface CIRelationship {
  id: string;
  tenantId: string;
  sourceCiId: string;
  sourceCiName: string;
  targetCiId: string;
  targetCiName: string;
  relationshipTypeId: string;
  relationshipTypeName: string;
  attributes: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

// ── Snapshots & Versioning ──────────────────────────────────────────

export interface CISnapshot {
  id: string;
  ciId: string;
  tenantId: string;
  versionNumber: number;
  snapshotData: Record<string, unknown>;
  changedBy: string | null;
  changedAt: string;
  changeReason: string | null;
  changeType: string;
}

export interface CIVersionList {
  items: CISnapshot[];
  total: number;
}

export interface VersionDiff {
  versionA: number;
  versionB: number;
  changes: Record<string, unknown>;
}

// ── Templates ───────────────────────────────────────────────────────

export interface CITemplate {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  ciClassId: string;
  ciClassName: string;
  attributes: Record<string, unknown>;
  tags: Record<string, unknown>;
  relationshipTemplates: Record<string, unknown> | null;
  constraints: Record<string, unknown> | null;
  isActive: boolean;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface CITemplateList {
  items: CITemplate[];
  total: number;
}

// ── Graph & Impact ──────────────────────────────────────────────────

export interface GraphNode {
  ciId: string;
  name: string;
  ciClass: string;
  depth: number;
  path: string[];
}

// ── Compartments ────────────────────────────────────────────────────

export interface CompartmentNode {
  id: string;
  name: string;
  description: string | null;
  cloudId: string | null;
  providerType: string | null;
  children: CompartmentNode[];
}

// ── Saved Searches ──────────────────────────────────────────────────

export interface SavedSearch {
  id: string;
  tenantId: string;
  userId: string;
  name: string;
  queryText: string | null;
  filters: Record<string, unknown> | null;
  sortConfig: Record<string, unknown> | null;
  isDefault: boolean;
}

// ── Service Catalog ─────────────────────────────────────────────────

export type OfferingStatus = 'draft' | 'published' | 'archived';

export interface ServiceOffering {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  category: string | null;
  measuringUnit: string;
  serviceType: string;
  operatingModel: string | null;
  defaultCoverageModel: string | null;
  ciClassIds?: string[];
  isActive: boolean;
  status: OfferingStatus;
  clonedFromId: string | null;
  baseFee: number | null;
  feePeriod: string | null;
  minimumAmount: number | null;
  minimumCurrency: string | null;
  minimumPeriod: string | null;
  regionIds?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ServiceOfferingList {
  items: ServiceOffering[];
  total: number;
}

export interface PriceListItem {
  id: string;
  priceListId: string;
  serviceOfferingId: string | null;
  providerSkuId: string | null;
  activityDefinitionId: string | null;
  markupPercent: number | null;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  pricePerUnit: number;
  currency: string;
  minQuantity: number | null;
  maxQuantity: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PriceList {
  id: string;
  tenantId: string | null;
  name: string;
  isDefault: boolean;
  groupId: string | null;
  versionMajor: number;
  versionMinor: number;
  versionLabel: string;
  status: string;
  deliveryRegionId: string | null;
  parentVersionId: string | null;
  clonedFromPriceListId: string | null;
  regionConstraintIds: string[];
  items: PriceListItem[];
  createdAt: string;
  updatedAt: string;
}

export interface TenantPriceListAssignment {
  tenantId: string;
  assignmentType: string;
  priceListId: string;
  clonePriceListId: string | null;
  additions: number;
  deletions: number;
  isCustomized: boolean;
}

export interface PriceListDiffItem {
  id: string;
  priceListId: string;
  serviceOfferingId: string | null;
  providerSkuId: string | null;
  activityDefinitionId: string | null;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  pricePerUnit: number;
  markupPercent: number | null;
  currency: string;
  minQuantity: number | null;
  maxQuantity: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PriceListDiff {
  sourcePriceListId: string;
  clonePriceListId: string;
  additions: PriceListDiffItem[];
  deletions: PriceListDiffItem[];
  common: PriceListDiffItem[];
}

export interface PriceListSummary {
  items: PriceList[];
  total: number;
}

export interface PriceListOverlayItem {
  id: string;
  tenantId: string;
  pinId: string;
  overlayAction: string;
  baseItemId: string | null;
  serviceOfferingId: string | null;
  providerSkuId: string | null;
  activityDefinitionId: string | null;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  pricePerUnit: number | null;
  currency: string | null;
  markupPercent: number | null;
  discountPercent: number | null;
  minQuantity: number | null;
  maxQuantity: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PinMinimumCharge {
  id: string;
  tenantId: string;
  pinId: string;
  category: string | null;
  minimumAmount: number;
  currency: string;
  period: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TenantPriceListPin {
  id: string;
  tenantId: string;
  priceListId: string;
  priceList: PriceList | null;
  overlayItems: PriceListOverlayItem[];
  minimumCharges: PinMinimumCharge[];
  effectiveFrom: string;
  effectiveTo: string;
  createdAt: string;
  updatedAt: string;
}

export interface EffectivePrice {
  serviceOfferingId: string;
  serviceName: string;
  pricePerUnit: number;
  currency: string;
  measuringUnit: string;
  hasOverride: boolean;
  discountPercent: number | null;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  complianceStatus: string | null;
  sourceType: string | null;
  markupPercent: number | null;
  priceListId: string | null;
}

// ── Service Catalogs ───────────────────────────────────────────────

export interface ServiceCatalogItem {
  id: string;
  catalogId: string;
  serviceOfferingId: string | null;
  serviceGroupId: string | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceCatalog {
  id: string;
  tenantId: string | null;
  name: string;
  description: string | null;
  groupId: string | null;
  versionMajor: number;
  versionMinor: number;
  versionLabel: string;
  status: string;
  parentVersionId: string | null;
  clonedFromCatalogId: string | null;
  regionConstraintIds: string[];
  items: ServiceCatalogItem[];
  createdAt: string;
  updatedAt: string;
}

export interface ServiceCatalogList {
  items: ServiceCatalog[];
  total: number;
}

export interface CatalogOverlayItem {
  id: string;
  tenantId: string;
  pinId: string;
  overlayAction: string;
  baseItemId: string | null;
  serviceOfferingId: string | null;
  serviceGroupId: string | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface TenantCatalogPin {
  id: string;
  tenantId: string;
  catalogId: string;
  catalog: ServiceCatalog | null;
  overlayItems: CatalogOverlayItem[];
  effectiveFrom: string;
  effectiveTo: string;
  createdAt: string;
  updatedAt: string;
}

export interface TenantCatalogAssignment {
  tenantId: string;
  assignmentType: string;
  catalogId: string;
  cloneCatalogId: string | null;
  additions: number;
  deletions: number;
  isCustomized: boolean;
}

export interface CatalogDiffItem {
  id: string;
  catalogId: string;
  serviceOfferingId: string | null;
  serviceGroupId: string | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface CatalogDiff {
  sourceCatalogId: string;
  cloneCatalogId: string;
  additions: CatalogDiffItem[];
  deletions: CatalogDiffItem[];
  common: CatalogDiffItem[];
}

// ── Provider SKUs ──────────────────────────────────────────────────

export interface ProviderSku {
  id: string;
  providerId: string;
  externalSkuId: string;
  name: string;
  displayName: string | null;
  description: string | null;
  ciClassId: string | null;
  measuringUnit: string;
  category: string | null;
  unitCost: number | null;
  costCurrency: string;
  attributes: Record<string, unknown> | null;
  isActive: boolean;
  semanticTypeId: string | null;
  semanticTypeName: string | null;
  resourceType: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProviderSkuList {
  items: ProviderSku[];
  total: number;
}

export interface ServiceOfferingSku {
  id: string;
  serviceOfferingId: string;
  providerSkuId: string;
  defaultQuantity: number;
  isRequired: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

// ── Service Groups ─────────────────────────────────────────────────

export interface ServiceGroupItem {
  id: string;
  groupId: string;
  serviceOfferingId: string;
  offeringName: string | null;
  isRequired: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export type ServiceGroupStatus = 'draft' | 'published' | 'archived';

export interface ServiceGroup {
  id: string;
  tenantId: string | null;
  name: string;
  displayName: string | null;
  description: string | null;
  status: ServiceGroupStatus;
  items: ServiceGroupItem[];
  createdAt: string;
  updatedAt: string;
}

export interface ServiceGroupList {
  items: ServiceGroup[];
  total: number;
}

// ── Offering Cost Breakdown ────────────────────────────────────────

export interface OfferingCostBreakdown {
  sourceType: string;
  sourceId: string;
  sourceName: string;
  quantity: number;
  isRequired: boolean;
  pricePerUnit: number;
  currency: string;
  measuringUnit: string;
  markupPercent: number | null;
}

// ── Explorer Summary ────────────────────────────────────────────────

export interface ExplorerTypeSummary {
  semanticTypeId: string | null;
  semanticTypeName: string;
  ciClassId: string;
  ciClassName: string;
  ciClassIcon: string | null;
  count: number;
}

export interface ExplorerCategorySummary {
  categoryId: string | null;
  categoryName: string;
  categoryIcon: string | null;
  types: ExplorerTypeSummary[];
  totalCount: number;
}

export interface ExplorerBackendSummary {
  backendId: string;
  backendName: string;
  providerName: string;
  ciCount: number;
}

export interface ExplorerSummary {
  totalCis: number;
  categories: ExplorerCategorySummary[];
  backends: ExplorerBackendSummary[];
}

// ── Input types ─────────────────────────────────────────────────────

export interface CICreateInput {
  ciClassId: string;
  name: string;
  description?: string | null;
  compartmentId?: string | null;
  lifecycleState?: string;
  attributes?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
  cloudResourceId?: string | null;
  pulumiUrn?: string | null;
}

export interface CIUpdateInput {
  name?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
  cloudResourceId?: string | null;
  pulumiUrn?: string | null;
}

export interface CIClassCreateInput {
  name: string;
  displayName: string;
  parentClassId?: string | null;
  schemaDef?: Record<string, unknown> | null;
  icon?: string | null;
}

export interface CIClassUpdateInput {
  displayName?: string | null;
  icon?: string | null;
  isActive?: boolean | null;
  schemaDef?: Record<string, unknown> | null;
}

export interface CIAttributeDefinitionCreateInput {
  name: string;
  displayName: string;
  dataType: string;
  isRequired?: boolean;
  defaultValue?: unknown | null;
  validationRules?: Record<string, unknown> | null;
  sortOrder?: number;
}

export interface CIAttributeDefinitionUpdateInput {
  displayName?: string | null;
  dataType?: string | null;
  isRequired?: boolean | null;
  defaultValue?: unknown | null;
  validationRules?: Record<string, unknown> | null;
  sortOrder?: number | null;
}

export interface CIRelationshipInput {
  sourceCiId: string;
  targetCiId: string;
  relationshipTypeId: string;
  attributes?: Record<string, unknown> | null;
}

export interface CITemplateCreateInput {
  name: string;
  ciClassId: string;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
  relationshipTemplates?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
}

export interface CITemplateUpdateInput {
  name?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
  relationshipTemplates?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
  isActive?: boolean | null;
}

export interface CIFromTemplateInput {
  templateId: string;
  name: string;
  compartmentId?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
  lifecycleState?: string;
}

export interface CompartmentCreateInput {
  name: string;
  description?: string | null;
  parentId?: string | null;
  cloudId?: string | null;
  providerType?: string | null;
}

export interface CompartmentUpdateInput {
  name?: string | null;
  description?: string | null;
  cloudId?: string | null;
  providerType?: string | null;
}

export interface SavedSearchInput {
  name: string;
  queryText?: string | null;
  filters?: Record<string, unknown> | null;
  sortConfig?: Record<string, unknown> | null;
}

export interface ServiceOfferingCreateInput {
  name: string;
  description?: string | null;
  category?: string | null;
  measuringUnit?: string;
  serviceType?: string;
  operatingModel?: string | null;
  defaultCoverageModel?: string | null;
  ciClassIds?: string[] | null;
  baseFee?: number | null;
  feePeriod?: string | null;
  minimumAmount?: number | null;
  minimumCurrency?: string | null;
  minimumPeriod?: string | null;
}

export interface ServiceOfferingUpdateInput {
  name?: string | null;
  description?: string | null;
  category?: string | null;
  measuringUnit?: string | null;
  serviceType?: string | null;
  operatingModel?: string | null;
  defaultCoverageModel?: string | null;
  ciClassIds?: string[] | null;
  isActive?: boolean | null;
  minimumAmount?: number | null;
  minimumCurrency?: string | null;
  minimumPeriod?: string | null;
}

export interface CIClassActivityAssociation {
  id: string;
  tenantId: string;
  ciClassId: string;
  ciClassName: string;
  ciClassDisplayName: string;
  activityTemplateId: string;
  activityTemplateName: string;
  relationshipType: string | null;
  relationshipTypeId: string | null;
  relationshipTypeName: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CIClassActivityAssociationCreateInput {
  ciClassId: string;
  activityTemplateId: string;
  relationshipType?: string | null;
  relationshipTypeId?: string | null;
}

export interface SemanticActivityType {
  id: string;
  name: string;
  displayName: string;
  category: string | null;
  description: string | null;
  icon: string | null;
  applicableSemanticCategories: string[] | null;
  applicableSemanticTypes: string[] | null;
  defaultRelationshipKindId: string | null;
  defaultRelationshipKindName: string | null;
  propertiesSchema: Record<string, unknown> | null;
  isSystem: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface PriceListCreateInput {
  name: string;
  isDefault?: boolean;
  clientTenantId?: string | null;
  deliveryRegionId?: string | null;
}

export interface PriceListVersionInput {
  priceListId: string;
  bump: 'minor' | 'major';
}

export interface PriceListItemCreateInput {
  serviceOfferingId?: string | null;
  providerSkuId?: string | null;
  activityDefinitionId?: string | null;
  markupPercent?: number | null;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  pricePerUnit: number;
  currency?: string;
  minQuantity?: number | null;
  maxQuantity?: number | null;
}

export interface PriceListItemUpdateInput {
  pricePerUnit?: number | null;
  currency?: string | null;
  markupPercent?: number | null;
  minQuantity?: number | null;
  maxQuantity?: number | null;
}

export interface PriceListCopyInput {
  sourceId: string;
  newName: string;
  clientTenantId?: string | null;
}

// ── Overlay & Pin Minimum Input Types ─────────────────────────────

export interface PriceListOverlayItemCreateInput {
  overlayAction: string;
  baseItemId?: string | null;
  serviceOfferingId?: string | null;
  providerSkuId?: string | null;
  activityDefinitionId?: string | null;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  pricePerUnit?: number | null;
  currency?: string | null;
  markupPercent?: number | null;
  discountPercent?: number | null;
  minQuantity?: number | null;
  maxQuantity?: number | null;
}

export interface CatalogOverlayItemCreateInput {
  overlayAction: string;
  baseItemId?: string | null;
  serviceOfferingId?: string | null;
  serviceGroupId?: string | null;
  sortOrder?: number;
}

export interface PinMinimumChargeCreateInput {
  category?: string | null;
  minimumAmount: number;
  currency?: string;
  period?: string;
  effectiveFrom: string;
  effectiveTo?: string | null;
}
