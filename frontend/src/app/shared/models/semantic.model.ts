/**
 * Overview: TypeScript interfaces for the semantic layer — categories, types, relationships,
 *     and providers.
 * Architecture: Frontend data models for the semantic type catalog (Section 5)
 * Dependencies: None
 * Concepts: Semantic types normalize provider resources into a unified model. Categories
 *     group types. Relationship kinds define connections. Providers are first-class entities.
 */

export type ProviderType = 'cloud' | 'on_prem' | 'saas' | 'custom';

export interface SemanticCategory {
  id: string;
  name: string;
  displayName: string;
  description: string | null;
  icon: string | null;
  sortOrder: number;
  isSystem: boolean;
  isInfrastructure: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SemanticProvider {
  id: string;
  name: string;
  displayName: string;
  description: string | null;
  icon: string | null;
  providerType: ProviderType;
  websiteUrl: string | null;
  documentationUrl: string | null;
  isSystem: boolean;
  resourceTypeCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface SemanticResourceType {
  id: string;
  name: string;
  displayName: string;
  category: SemanticCategory;
  description: string | null;
  icon: string | null;
  isAbstract: boolean;
  parentTypeName: string | null;
  propertiesSchema: PropertyDef[] | null;
  allowedRelationshipKinds: string[] | null;
  sortOrder: number;
  isSystem: boolean;
  children: SemanticResourceType[];
  createdAt: string;
  updatedAt: string;
}

export interface PropertyDef {
  name: string;
  display_name: string;
  data_type: string;
  required: boolean;
  default_value: string | null;
  unit: string | null;
  description: string;
  allowed_values: string[] | null;
}

export interface SemanticResourceTypeList {
  items: SemanticResourceType[];
  total: number;
}

export interface SemanticCategoryWithTypes extends SemanticCategory {
  types: SemanticResourceType[];
}

export interface SemanticRelationshipKind {
  id: string;
  name: string;
  displayName: string;
  description: string | null;
  inverseName: string;
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

// -- CRUD Input types --------------------------------------------------------

export interface SemanticCategoryInput {
  name: string;
  displayName: string;
  description?: string | null;
  icon?: string | null;
  sortOrder?: number;
}

export interface SemanticCategoryUpdateInput {
  displayName?: string;
  description?: string | null;
  icon?: string | null;
  sortOrder?: number;
}

export interface SemanticResourceTypeInput {
  name: string;
  displayName: string;
  categoryId: string;
  description?: string | null;
  icon?: string | null;
  isAbstract?: boolean;
  parentTypeId?: string | null;
  propertiesSchema?: unknown;
  allowedRelationshipKinds?: string[];
  sortOrder?: number;
}

export interface SemanticResourceTypeUpdateInput {
  displayName?: string;
  categoryId?: string;
  description?: string | null;
  icon?: string | null;
  isAbstract?: boolean;
  parentTypeId?: string | null;
  propertiesSchema?: unknown;
  allowedRelationshipKinds?: string[];
  sortOrder?: number;
}

export interface SemanticProviderInput {
  name: string;
  displayName: string;
  description?: string | null;
  icon?: string | null;
  providerType?: ProviderType;
  websiteUrl?: string | null;
  documentationUrl?: string | null;
}

export interface SemanticProviderUpdateInput {
  displayName?: string;
  description?: string | null;
  icon?: string | null;
  providerType?: ProviderType;
  websiteUrl?: string | null;
  documentationUrl?: string | null;
}

export interface SemanticRelationshipKindInput {
  name: string;
  displayName: string;
  description?: string | null;
  inverseName: string;
}

export interface SemanticRelationshipKindUpdateInput {
  displayName?: string;
  description?: string | null;
  inverseName?: string;
}

// Note: data_type in PropertyDef can also be 'os_image' — renders an image catalog picker.
