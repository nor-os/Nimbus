/**
 * Overview: Interfaces for guided environment configuration option catalog.
 * Architecture: Shared model for env config option tiles (Section 7.2)
 * Dependencies: None
 * Concepts: ConfigOption represents a browseable tile; ConfigOptionCategory groups tiles.
 */

export interface ConfigOption {
  id: string;
  domain: string;
  category: string;
  providerName: string;
  name: string;
  displayName: string;
  description: string;
  detail: string;
  icon: string;
  implications: string[];
  configValues: Record<string, unknown>;
  conflictsWith: string[];
  requires: string[];
  relatedResolverTypes: string[];
  relatedComponentNames: string[];
  sortOrder: number;
  isDefault: boolean;
  tags: string[];
  hierarchyImplications?: {
    description: string;
    nodes: { typeId: string; label: string; parentId: string | null }[];
  } | null;
}

export interface ConfigOptionCategory {
  name: string;
  displayName: string;
  description: string;
  icon: string;
}
