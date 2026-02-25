/**
 * Overview: TypeScript interfaces for landing zones, environments, and IPAM.
 * Architecture: Frontend data models for landing zones & IPAM (Section 5)
 * Dependencies: None
 * Concepts: Landing zones, environments, address spaces, allocations, IP reservations
 */

// ── Hierarchy Types ──────────────────────────────────────────────────

export interface HierarchyLevelDef {
  typeId: string;
  label: string;
  icon: string;
  allowedChildren: string[];
  supportsIpam: boolean;
  supportsTags: boolean;
  supportsEnvironment: boolean;
}

export interface ProviderHierarchy {
  providerName: string;
  rootType: string;
  levels: HierarchyLevelDef[];
}

export interface HierarchyNode {
  id: string;
  parentId: string | null;
  typeId: string;
  label: string;
  properties: {
    tagPolicies?: Array<{ tagKey: string; displayName: string; isRequired: boolean; allowedValues?: string[]; defaultValue?: string; inherited?: boolean; inheritedFrom?: string }>;
    ipam?: { cidr: string };
    networkConfig?: Record<string, unknown>;
    securityConfig?: Record<string, unknown>;
    namingConfig?: { template: string };
    environmentDesignation?: string;
    description?: string;
    [key: string]: unknown;
  };
}

export interface LandingZoneHierarchy {
  nodes: HierarchyNode[];
}

// ── Landing Zone Types ──────────────────────────────────────────────

export type LandingZoneStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
export type EnvironmentStatus = 'PLANNED' | 'PROVISIONING' | 'ACTIVE' | 'SUSPENDED' | 'DECOMMISSIONING' | 'DECOMMISSIONED';
export type AddressSpaceStatus = 'ACTIVE' | 'EXHAUSTED' | 'RESERVED';
export type AllocationType = 'REGION' | 'PROVIDER_RESERVED' | 'TENANT_POOL' | 'VCN' | 'SUBNET';
export type AllocationStatus = 'PLANNED' | 'ALLOCATED' | 'IN_USE' | 'RELEASED';
export type ReservationStatus = 'RESERVED' | 'IN_USE' | 'RELEASED';

export interface LandingZoneTagPolicy {
  id: string;
  landingZoneId: string;
  tagKey: string;
  displayName: string;
  description: string | null;
  isRequired: boolean;
  allowedValues: unknown | null;
  defaultValue: string | null;
  inherited: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface BackendRegionRef {
  id: string;
  regionIdentifier: string;
  displayName: string;
}

export interface LandingZone {
  id: string;
  tenantId: string;
  backendId: string;
  regionId: string | null;
  region: BackendRegionRef | null;
  topologyId: string | null;
  cloudTenancyId: string | null;
  name: string;
  description: string | null;
  status: LandingZoneStatus;
  version: number;
  settings: Record<string, unknown> | null;
  networkConfig: Record<string, unknown> | null;
  iamConfig: Record<string, unknown> | null;
  securityConfig: Record<string, unknown> | null;
  namingConfig: Record<string, unknown> | null;
  hierarchy: LandingZoneHierarchy | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  tagPolicies: LandingZoneTagPolicy[];
}

export interface EnvironmentTemplate {
  id: string;
  providerId: string;
  name: string;
  displayName: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  defaultTags: Record<string, unknown> | null;
  defaultPolicies: Record<string, unknown> | null;
  sortOrder: number;
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

export type FailoverMode = 'active_passive' | 'active_active' | 'pilot_light' | 'warm_standby';

export interface DrConfig {
  failoverMode: FailoverMode;
  rpoHours: number;
  rtoHours: number;
  replicationConfig?: Record<string, unknown>;
  failoverPriority?: number;
  healthCheckUrl?: string;
}

export interface TenantEnvironment {
  id: string;
  tenantId: string;
  landingZoneId: string;
  templateId: string | null;
  regionId: string | null;
  region: BackendRegionRef | null;
  drSourceEnvId: string | null;
  drConfig: DrConfig | null;
  name: string;
  displayName: string;
  description: string | null;
  status: EnvironmentStatus;
  rootCompartmentId: string | null;
  tags: Record<string, unknown>;
  policies: Record<string, unknown>;
  settings: Record<string, unknown> | null;
  networkConfig: Record<string, unknown> | null;
  iamConfig: Record<string, unknown> | null;
  securityConfig: Record<string, unknown> | null;
  monitoringConfig: Record<string, unknown> | null;
  providerName: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface IpReservation {
  id: string;
  allocationId: string;
  ipAddress: string;
  hostname: string | null;
  purpose: string;
  ciId: string | null;
  status: ReservationStatus;
  reservedBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface AddressAllocation {
  id: string;
  addressSpaceId: string;
  parentAllocationId: string | null;
  tenantEnvironmentId: string | null;
  name: string;
  description: string | null;
  cidr: string;
  allocationType: AllocationType;
  status: AllocationStatus;
  purpose: string | null;
  semanticTypeId: string | null;
  cloudResourceId: string | null;
  utilizationPercent: number | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
  children: AddressAllocation[];
  reservations: IpReservation[];
}

export interface AddressSpace {
  id: string;
  landingZoneId: string;
  regionId: string | null;
  name: string;
  description: string | null;
  cidr: string;
  ipVersion: number;
  status: AddressSpaceStatus;
  createdAt: string;
  updatedAt: string;
  allocations: AddressAllocation[];
}

export interface CidrSuggestion {
  cidr: string | null;
  available: boolean;
}

export interface CidrSummary {
  network: string;
  broadcast: string;
  prefixLength: number;
  totalAddresses: number;
  usableAddresses: number;
  ipVersion: number;
  isPrivate: boolean;
}

// ── Blueprint Types ─────────────────────────────────────────────────

export interface LandingZoneBlueprint {
  id: string;
  name: string;
  providerName: string;
  description: string;
  complexity: 'basic' | 'standard' | 'advanced';
  features: string[];
  hierarchy: LandingZoneHierarchy;
  networkConfig: Record<string, unknown>;
  iamConfig: Record<string, unknown>;
  securityConfig: Record<string, unknown>;
  namingConfig: Record<string, unknown>;
  defaultTags: Array<{
    tagKey: string;
    displayName: string;
    isRequired: boolean;
    allowedValues?: string[];
  }>;
  defaultAddressSpaces: Array<{
    name: string;
    cidr: string;
    description: string;
  }>;
}

// ── Validation Types ────────────────────────────────────────────────

export interface LandingZoneCheck {
  key: string;
  label: string;
  status: 'pass' | 'warning' | 'error';
  message: string;
}

export interface LandingZoneValidation {
  ready: boolean;
  checks: LandingZoneCheck[];
}
