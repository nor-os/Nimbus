/**
 * Overview: TypeScript interfaces for the OS image catalog — images and provider mappings.
 * Architecture: Frontend data models for the OS image catalog (Section 5)
 * Dependencies: None
 * Concepts: OS images define abstract operating system choices. Provider mappings link
 *     images to provider-specific references (AMI IDs, Azure URNs, etc.).
 */

export interface OsImageTenantAssignment {
  id: string;
  osImageId: string;
  tenantId: string;
  tenantName: string;
  createdAt: string;
}

export interface OsImage {
  id: string;
  name: string;
  displayName: string;
  osFamily: string;
  version: string;
  architecture: string;
  description: string | null;
  icon: string | null;
  sortOrder: number;
  isSystem: boolean;
  providerMappings: OsImageProviderMapping[];
  tenantAssignments: OsImageTenantAssignment[];
  createdAt: string;
  updatedAt: string;
}

export interface OsImageProviderMapping {
  id: string;
  osImageId: string;
  providerId: string;
  providerName: string;
  providerDisplayName: string;
  imageReference: string;
  notes: string | null;
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface OsImageList {
  items: OsImage[];
  total: number;
}

// -- Input types --------------------------------------------------------

export interface OsImageInput {
  name: string;
  displayName: string;
  osFamily: string;
  version: string;
  architecture?: string;
  description?: string | null;
  icon?: string | null;
  sortOrder?: number;
}

export interface OsImageUpdateInput {
  displayName?: string;
  osFamily?: string;
  version?: string;
  architecture?: string;
  description?: string | null;
  icon?: string | null;
  sortOrder?: number;
}

export interface OsImageProviderMappingInput {
  osImageId: string;
  providerId: string;
  imageReference: string;
  notes?: string | null;
}

export interface OsImageProviderMappingUpdateInput {
  imageReference?: string;
  notes?: string | null;
}
