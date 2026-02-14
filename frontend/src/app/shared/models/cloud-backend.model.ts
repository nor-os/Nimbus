/**
 * Overview: TypeScript interfaces for cloud backend connections and IAM mappings.
 * Architecture: Frontend model definitions for cloud backend management (Section 11)
 * Dependencies: None
 * Concepts: CloudBackend = configured provider connection. IAM mappings link Nimbus roles
 *     to cloud-specific identities. Credentials are write-only (only hasCredentials exposed).
 */

export interface CloudBackend {
  id: string;
  tenantId: string;
  providerId: string;
  providerName: string;
  providerDisplayName: string;
  providerIcon: string | null;
  name: string;
  description: string | null;
  status: 'active' | 'disabled' | 'error';
  hasCredentials: boolean;
  credentialsSchemaVersion: number;
  scopeConfig: Record<string, unknown> | null;
  endpointUrl: string | null;
  isShared: boolean;
  lastConnectivityCheck: string | null;
  lastConnectivityStatus: string | null;
  lastConnectivityError: string | null;
  iamMappingCount: number;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CloudBackendIAMMapping {
  id: string;
  backendId: string;
  roleId: string;
  roleName: string;
  cloudIdentity: Record<string, unknown>;
  description: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ConnectivityTestResult {
  success: boolean;
  message: string;
  checkedAt: string | null;
}

export interface CloudBackendInput {
  providerId: string;
  name: string;
  description?: string | null;
  status?: string;
  credentials?: Record<string, unknown> | null;
  scopeConfig?: Record<string, unknown> | null;
  endpointUrl?: string | null;
  isShared?: boolean;
}

export interface CloudBackendUpdateInput {
  name?: string;
  description?: string | null;
  status?: string;
  credentials?: Record<string, unknown> | null;
  scopeConfig?: Record<string, unknown> | null;
  endpointUrl?: string | null;
  isShared?: boolean;
}

export interface CloudBackendIAMMappingInput {
  roleId: string;
  cloudIdentity: Record<string, unknown>;
  description?: string | null;
  isActive?: boolean;
}

export interface CloudBackendIAMMappingUpdateInput {
  cloudIdentity?: Record<string, unknown>;
  description?: string | null;
  isActive?: boolean;
}
