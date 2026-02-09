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

export interface PriceList {
  id: string;
  tenantId: string | null;
  name: string;
  isDefault: boolean;
  effectiveFrom: string;
  effectiveTo: string | null;
  items: PriceListItem[];
  createdAt: string;
  updatedAt: string;
}

export interface PriceListSummary {
  items: PriceList[];
  total: number;
}

export interface TenantPriceOverride {
  id: string;
  tenantId: string;
  serviceOfferingId: string;
  deliveryRegionId: string | null;
  coverageModel: string | null;
  pricePerUnit: number;
  discountPercent: number | null;
  effectiveFrom: string;
  effectiveTo: string | null;
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
  createdAt: string;
  updatedAt: string;
}

export interface CIClassActivityAssociationCreateInput {
  ciClassId: string;
  activityTemplateId: string;
  relationshipType?: string | null;
}

export interface PriceListCreateInput {
  name: string;
  isDefault?: boolean;
  effectiveFrom: string;
  effectiveTo?: string | null;
  clientTenantId?: string | null;
}

export interface PriceListItemCreateInput {
  serviceOfferingId: string;
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
  minQuantity?: number | null;
  maxQuantity?: number | null;
}

export interface PriceListCopyInput {
  sourceId: string;
  newName: string;
  clientTenantId?: string | null;
}

export interface TenantPriceOverrideCreateInput {
  serviceOfferingId: string;
  deliveryRegionId?: string | null;
  coverageModel?: string | null;
  pricePerUnit: number;
  discountPercent?: number | null;
  effectiveFrom: string;
  effectiveTo?: string | null;
}
