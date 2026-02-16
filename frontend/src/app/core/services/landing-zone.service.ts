/**
 * Overview: Landing zone & IPAM service — GraphQL queries and mutations for landing zones, environments, and IP address management.
 * Architecture: Core service layer for landing zone & IPAM data (Section 5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Full CRUD for landing zones, regions, tag policies, environments, address spaces, allocations, IP reservations
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  AddressAllocation,
  AddressSpace,
  CidrSuggestion,
  CidrSummary,
  EnvironmentTemplate,
  IpReservation,
  LandingZone,
  LandingZoneBlueprint,
  LandingZoneRegion,
  LandingZoneTagPolicy,
  LandingZoneValidation,
  ProviderHierarchy,
  TenantEnvironment,
} from '@shared/models/landing-zone.model';

const REGION_FIELDS = `id landingZoneId regionIdentifier displayName isPrimary isDr settings createdAt updatedAt`;
const TAG_POLICY_FIELDS = `id landingZoneId tagKey displayName description isRequired allowedValues defaultValue inherited createdAt updatedAt`;
const ZONE_FIELDS = `id tenantId backendId topologyId cloudTenancyId name description status version settings networkConfig iamConfig securityConfig namingConfig hierarchy createdBy createdAt updatedAt regions { ${REGION_FIELDS} } tagPolicies { ${TAG_POLICY_FIELDS} }`;
const TEMPLATE_FIELDS = `id providerId name displayName description icon color defaultTags defaultPolicies sortOrder isSystem createdAt updatedAt`;
const ENV_FIELDS = `id tenantId landingZoneId templateId name displayName description status rootCompartmentId tags policies settings networkConfig iamConfig securityConfig monitoringConfig providerName createdBy createdAt updatedAt`;
const RESERVATION_FIELDS = `id allocationId ipAddress hostname purpose ciId status reservedBy createdAt updatedAt`;
const ALLOCATION_FIELDS = `id addressSpaceId parentAllocationId tenantEnvironmentId name description cidr allocationType status purpose semanticTypeId cloudResourceId utilizationPercent metadata createdAt updatedAt children { id name cidr allocationType status purpose } reservations { ${RESERVATION_FIELDS} }`;
const SPACE_FIELDS = `id landingZoneId regionId name description cidr ipVersion status createdAt updatedAt allocations { ${ALLOCATION_FIELDS} }`;

@Injectable({ providedIn: 'root' })
export class LandingZoneService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Landing Zones ──────────────────────────────────────────────

  listLandingZones(filters?: {
    status?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<LandingZone[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ landingZones: LandingZone[] }>(`
      query LandingZones(
        $tenantId: UUID!
        $status: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        landingZones(
          tenantId: $tenantId
          status: $status
          search: $search
          offset: $offset
          limit: $limit
        ) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.landingZones));
  }

  getByBackendId(backendId: string): Observable<LandingZone | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ landingZoneByBackend: LandingZone | null }>(`
      query LandingZoneByBackend($tenantId: UUID!, $backendId: UUID!) {
        landingZoneByBackend(tenantId: $tenantId, backendId: $backendId) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, backendId }).pipe(map(d => d.landingZoneByBackend));
  }

  getNetworkConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ backendNetworkConfigSchema: Record<string, unknown> | null }>(`
      query BackendNetworkConfigSchema($tenantId: UUID!, $providerName: String!) {
        backendNetworkConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.backendNetworkConfigSchema));
  }

  getIamConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ backendIamConfigSchema: Record<string, unknown> | null }>(`
      query BackendIamConfigSchema($tenantId: UUID!, $providerName: String!) {
        backendIamConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.backendIamConfigSchema));
  }

  getSecurityConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ backendSecurityConfigSchema: Record<string, unknown> | null }>(`
      query BackendSecurityConfigSchema($tenantId: UUID!, $providerName: String!) {
        backendSecurityConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.backendSecurityConfigSchema));
  }

  getLandingZone(id: string): Observable<LandingZone | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ landingZone: LandingZone | null }>(`
      query LandingZone($tenantId: UUID!, $zoneId: UUID!) {
        landingZone(tenantId: $tenantId, zoneId: $zoneId) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, zoneId: id }).pipe(map(d => d.landingZone));
  }

  createLandingZone(input: {
    name: string;
    description?: string | null;
    backendId: string;
    topologyId: string;
    cloudTenancyId?: string | null;
    settings?: Record<string, unknown> | null;
  }): Observable<LandingZone> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createLandingZone: LandingZone }>(`
      mutation CreateLandingZone($tenantId: UUID!, $input: LandingZoneCreateInput!) {
        createLandingZone(tenantId: $tenantId, input: $input) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createLandingZone));
  }

  updateLandingZone(id: string, input: {
    name?: string | null;
    description?: string | null;
    cloudTenancyId?: string | null;
    settings?: Record<string, unknown> | null;
    networkConfig?: Record<string, unknown> | null;
    iamConfig?: Record<string, unknown> | null;
    securityConfig?: Record<string, unknown> | null;
    namingConfig?: Record<string, unknown> | null;
    hierarchy?: Record<string, unknown> | null;
  }): Observable<LandingZone | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateLandingZone: LandingZone | null }>(`
      mutation UpdateLandingZone($tenantId: UUID!, $zoneId: UUID!, $input: LandingZoneUpdateInput!) {
        updateLandingZone(tenantId: $tenantId, zoneId: $zoneId, input: $input) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, zoneId: id, input }).pipe(map(d => d.updateLandingZone));
  }

  publishLandingZone(id: string): Observable<LandingZone> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishLandingZone: LandingZone }>(`
      mutation PublishLandingZone($tenantId: UUID!, $zoneId: UUID!) {
        publishLandingZone(tenantId: $tenantId, zoneId: $zoneId) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, zoneId: id }).pipe(map(d => d.publishLandingZone));
  }

  archiveLandingZone(id: string): Observable<LandingZone> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveLandingZone: LandingZone }>(`
      mutation ArchiveLandingZone($tenantId: UUID!, $zoneId: UUID!) {
        archiveLandingZone(tenantId: $tenantId, zoneId: $zoneId) {
          ${ZONE_FIELDS}
        }
      }
    `, { tenantId, zoneId: id }).pipe(map(d => d.archiveLandingZone));
  }

  deleteLandingZone(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteLandingZone: boolean }>(`
      mutation DeleteLandingZone($tenantId: UUID!, $zoneId: UUID!) {
        deleteLandingZone(tenantId: $tenantId, zoneId: $zoneId)
      }
    `, { tenantId, zoneId: id }).pipe(map(d => d.deleteLandingZone));
  }

  // ── Regions ────────────────────────────────────────────────────

  addRegion(landingZoneId: string, input: {
    regionIdentifier: string;
    displayName: string;
    isPrimary?: boolean;
    isDr?: boolean;
    settings?: Record<string, unknown> | null;
  }): Observable<LandingZoneRegion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addLandingZoneRegion: LandingZoneRegion }>(`
      mutation AddLandingZoneRegion($tenantId: UUID!, $zoneId: UUID!, $input: LandingZoneRegionInput!) {
        addLandingZoneRegion(tenantId: $tenantId, zoneId: $zoneId, input: $input) {
          ${REGION_FIELDS}
        }
      }
    `, { tenantId, zoneId: landingZoneId, input }).pipe(map(d => d.addLandingZoneRegion));
  }

  removeRegion(landingZoneId: string, regionId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ removeLandingZoneRegion: boolean }>(`
      mutation RemoveLandingZoneRegion($tenantId: UUID!, $regionId: UUID!) {
        removeLandingZoneRegion(tenantId: $tenantId, regionId: $regionId)
      }
    `, { tenantId, regionId }).pipe(map(d => d.removeLandingZoneRegion));
  }

  // ── Tag Policies ───────────────────────────────────────────────

  createTagPolicy(landingZoneId: string, input: {
    tagKey: string;
    displayName: string;
    description?: string | null;
    isRequired?: boolean;
    allowedValues?: unknown | null;
    defaultValue?: string | null;
  }): Observable<LandingZoneTagPolicy> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTagPolicy: LandingZoneTagPolicy }>(`
      mutation CreateTagPolicy($tenantId: UUID!, $zoneId: UUID!, $input: TagPolicyInput!) {
        createTagPolicy(tenantId: $tenantId, zoneId: $zoneId, input: $input) {
          ${TAG_POLICY_FIELDS}
        }
      }
    `, { tenantId, zoneId: landingZoneId, input }).pipe(map(d => d.createTagPolicy));
  }

  updateTagPolicy(landingZoneId: string, policyId: string, input: {
    displayName?: string | null;
    description?: string | null;
    isRequired?: boolean;
    allowedValues?: unknown | null;
    defaultValue?: string | null;
  }): Observable<LandingZoneTagPolicy> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateTagPolicy: LandingZoneTagPolicy }>(`
      mutation UpdateTagPolicy($tenantId: UUID!, $policyId: UUID!, $input: TagPolicyInput!) {
        updateTagPolicy(tenantId: $tenantId, policyId: $policyId, input: $input) {
          ${TAG_POLICY_FIELDS}
        }
      }
    `, { tenantId, policyId, input }).pipe(map(d => d.updateTagPolicy));
  }

  deleteTagPolicy(landingZoneId: string, policyId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteTagPolicy: boolean }>(`
      mutation DeleteTagPolicy($tenantId: UUID!, $policyId: UUID!) {
        deleteTagPolicy(tenantId: $tenantId, policyId: $policyId)
      }
    `, { tenantId, policyId }).pipe(map(d => d.deleteTagPolicy));
  }

  // ── Environment Templates ──────────────────────────────────────

  listEnvironmentTemplates(filters?: {
    providerId?: string;
    offset?: number;
    limit?: number;
  }): Observable<EnvironmentTemplate[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ environmentTemplates: EnvironmentTemplate[] }>(`
      query EnvironmentTemplates(
        $tenantId: UUID!
        $providerId: UUID
        $offset: Int
        $limit: Int
      ) {
        environmentTemplates(
          tenantId: $tenantId
          providerId: $providerId
          offset: $offset
          limit: $limit
        ) {
          ${TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.environmentTemplates));
  }

  getEnvironmentTemplate(id: string): Observable<EnvironmentTemplate | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ environmentTemplate: EnvironmentTemplate | null }>(`
      query EnvironmentTemplate($tenantId: UUID!, $templateId: UUID!) {
        environmentTemplate(tenantId: $tenantId, templateId: $templateId) {
          ${TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, templateId: id }).pipe(map(d => d.environmentTemplate));
  }

  createEnvironmentTemplate(input: {
    providerId: string;
    name: string;
    displayName: string;
    description?: string | null;
    icon?: string | null;
    color?: string | null;
    defaultTags?: Record<string, unknown> | null;
    defaultPolicies?: Record<string, unknown> | null;
    sortOrder?: number;
  }): Observable<EnvironmentTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEnvironmentTemplate: EnvironmentTemplate }>(`
      mutation CreateEnvironmentTemplate($tenantId: UUID!, $input: EnvironmentTemplateInput!) {
        createEnvironmentTemplate(tenantId: $tenantId, input: $input) {
          ${TEMPLATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createEnvironmentTemplate));
  }

  deleteEnvironmentTemplate(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEnvironmentTemplate: boolean }>(`
      mutation DeleteEnvironmentTemplate($tenantId: UUID!, $templateId: UUID!) {
        deleteEnvironmentTemplate(tenantId: $tenantId, templateId: $templateId)
      }
    `, { tenantId, templateId: id }).pipe(map(d => d.deleteEnvironmentTemplate));
  }

  // ── Tenant Environments ────────────────────────────────────────

  listTenantEnvironments(filters?: {
    landingZoneId?: string;
    status?: string;
    offset?: number;
    limit?: number;
  }): Observable<TenantEnvironment[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantEnvironments: TenantEnvironment[] }>(`
      query TenantEnvironments(
        $tenantId: UUID!
        $landingZoneId: UUID
        $status: String
        $offset: Int
        $limit: Int
      ) {
        tenantEnvironments(
          tenantId: $tenantId
          landingZoneId: $landingZoneId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          ${ENV_FIELDS}
        }
      }
    `, { tenantId, ...filters }).pipe(map(d => d.tenantEnvironments));
  }

  getTenantEnvironment(id: string): Observable<TenantEnvironment | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ tenantEnvironment: TenantEnvironment | null }>(`
      query TenantEnvironment($tenantId: UUID!, $environmentId: UUID!) {
        tenantEnvironment(tenantId: $tenantId, environmentId: $environmentId) {
          ${ENV_FIELDS}
        }
      }
    `, { tenantId, environmentId: id }).pipe(map(d => d.tenantEnvironment));
  }

  createTenantEnvironment(input: {
    landingZoneId?: string | null;
    templateId?: string | null;
    name: string;
    displayName: string;
    description?: string | null;
    tags?: Record<string, unknown>;
    policies?: Record<string, unknown>;
    settings?: Record<string, unknown> | null;
  }): Observable<TenantEnvironment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createTenantEnvironment: TenantEnvironment }>(`
      mutation CreateTenantEnvironment($tenantId: UUID!, $input: TenantEnvironmentCreateInput!) {
        createTenantEnvironment(tenantId: $tenantId, input: $input) {
          ${ENV_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createTenantEnvironment));
  }

  // ── Environment Config Schemas ──────────────────────────────────

  getEnvNetworkConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ envNetworkConfigSchema: Record<string, unknown> | null }>(`
      query EnvNetworkConfigSchema($tenantId: UUID!, $providerName: String!) {
        envNetworkConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.envNetworkConfigSchema));
  }

  getEnvIamConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ envIamConfigSchema: Record<string, unknown> | null }>(`
      query EnvIamConfigSchema($tenantId: UUID!, $providerName: String!) {
        envIamConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.envIamConfigSchema));
  }

  getEnvSecurityConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ envSecurityConfigSchema: Record<string, unknown> | null }>(`
      query EnvSecurityConfigSchema($tenantId: UUID!, $providerName: String!) {
        envSecurityConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.envSecurityConfigSchema));
  }

  getEnvMonitoringConfigSchema(providerName: string): Observable<Record<string, unknown> | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ envMonitoringConfigSchema: Record<string, unknown> | null }>(`
      query EnvMonitoringConfigSchema($tenantId: UUID!, $providerName: String!) {
        envMonitoringConfigSchema(tenantId: $tenantId, providerName: $providerName)
      }
    `, { tenantId, providerName }).pipe(map(d => d.envMonitoringConfigSchema));
  }

  updateTenantEnvironment(id: string, input: {
    displayName?: string | null;
    description?: string | null;
    tags?: Record<string, unknown>;
    policies?: Record<string, unknown>;
    settings?: Record<string, unknown> | null;
    networkConfig?: Record<string, unknown> | null;
    iamConfig?: Record<string, unknown> | null;
    securityConfig?: Record<string, unknown> | null;
    monitoringConfig?: Record<string, unknown> | null;
  }): Observable<TenantEnvironment | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateTenantEnvironment: TenantEnvironment | null }>(`
      mutation UpdateTenantEnvironment($tenantId: UUID!, $environmentId: UUID!, $input: TenantEnvironmentUpdateInput!) {
        updateTenantEnvironment(tenantId: $tenantId, environmentId: $environmentId, input: $input) {
          ${ENV_FIELDS}
        }
      }
    `, { tenantId, environmentId: id, input }).pipe(map(d => d.updateTenantEnvironment));
  }

  decommissionEnvironment(id: string): Observable<TenantEnvironment> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ decommissionTenantEnvironment: TenantEnvironment }>(`
      mutation DecommissionTenantEnvironment($tenantId: UUID!, $environmentId: UUID!) {
        decommissionTenantEnvironment(tenantId: $tenantId, environmentId: $environmentId) {
          ${ENV_FIELDS}
        }
      }
    `, { tenantId, environmentId: id }).pipe(map(d => d.decommissionTenantEnvironment));
  }

  // ── IPAM: Address Spaces ───────────────────────────────────────

  listAddressSpaces(landingZoneId: string): Observable<AddressSpace[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addressSpaces: AddressSpace[] }>(`
      query AddressSpaces($tenantId: UUID!, $landingZoneId: UUID!) {
        addressSpaces(tenantId: $tenantId, landingZoneId: $landingZoneId) {
          ${SPACE_FIELDS}
        }
      }
    `, { tenantId, landingZoneId }).pipe(map(d => d.addressSpaces));
  }

  getAddressSpace(id: string): Observable<AddressSpace | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addressSpace: AddressSpace | null }>(`
      query AddressSpace($tenantId: UUID!, $addressSpaceId: UUID!) {
        addressSpace(tenantId: $tenantId, addressSpaceId: $addressSpaceId) {
          ${SPACE_FIELDS}
        }
      }
    `, { tenantId, addressSpaceId: id }).pipe(map(d => d.addressSpace));
  }

  createAddressSpace(input: {
    landingZoneId: string;
    regionId?: string | null;
    name: string;
    description?: string | null;
    cidr: string;
    ipVersion?: number;
  }): Observable<AddressSpace> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createAddressSpace: AddressSpace }>(`
      mutation CreateAddressSpace($tenantId: UUID!, $input: AddressSpaceInput!) {
        createAddressSpace(tenantId: $tenantId, input: $input) {
          ${SPACE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.createAddressSpace));
  }

  deleteAddressSpace(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteAddressSpace: boolean }>(`
      mutation DeleteAddressSpace($tenantId: UUID!, $addressSpaceId: UUID!) {
        deleteAddressSpace(tenantId: $tenantId, addressSpaceId: $addressSpaceId)
      }
    `, { tenantId, addressSpaceId: id }).pipe(map(d => d.deleteAddressSpace));
  }

  // ── IPAM: Allocations ──────────────────────────────────────────

  listAllocations(addressSpaceId: string): Observable<AddressAllocation[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ addressAllocations: AddressAllocation[] }>(`
      query AddressAllocations($tenantId: UUID!, $addressSpaceId: UUID!) {
        addressAllocations(tenantId: $tenantId, addressSpaceId: $addressSpaceId) {
          ${ALLOCATION_FIELDS}
        }
      }
    `, { tenantId, addressSpaceId }).pipe(map(d => d.addressAllocations));
  }

  allocateBlock(input: {
    addressSpaceId: string;
    parentAllocationId?: string | null;
    tenantEnvironmentId?: string | null;
    name: string;
    description?: string | null;
    cidr: string;
    allocationType: string;
    purpose?: string | null;
    semanticTypeId?: string | null;
    metadata?: Record<string, unknown> | null;
  }): Observable<AddressAllocation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ allocateAddressBlock: AddressAllocation }>(`
      mutation AllocateAddressBlock($tenantId: UUID!, $input: AddressAllocationInput!) {
        allocateAddressBlock(tenantId: $tenantId, input: $input) {
          ${ALLOCATION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.allocateAddressBlock));
  }

  releaseAllocation(allocationId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ releaseAddressAllocation: boolean }>(`
      mutation ReleaseAddressAllocation($tenantId: UUID!, $allocationId: UUID!) {
        releaseAddressAllocation(tenantId: $tenantId, allocationId: $allocationId)
      }
    `, { tenantId, allocationId }).pipe(map(d => d.releaseAddressAllocation));
  }

  suggestNextBlock(addressSpaceId: string, prefixLength: number, parentAllocationId?: string | null): Observable<CidrSuggestion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ suggestNextBlock: CidrSuggestion }>(`
      query SuggestNextBlock(
        $tenantId: UUID!
        $addressSpaceId: UUID!
        $prefixLength: Int!
        $parentAllocationId: UUID
      ) {
        suggestNextBlock(
          tenantId: $tenantId
          addressSpaceId: $addressSpaceId
          prefixLength: $prefixLength
          parentAllocationId: $parentAllocationId
        ) {
          cidr available
        }
      }
    `, { tenantId, addressSpaceId, prefixLength, parentAllocationId }).pipe(map(d => d.suggestNextBlock));
  }

  // ── IPAM: Reservations ─────────────────────────────────────────

  listReservations(allocationId: string): Observable<IpReservation[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ ipReservations: IpReservation[] }>(`
      query IpReservations($tenantId: UUID!, $allocationId: UUID!) {
        ipReservations(tenantId: $tenantId, allocationId: $allocationId) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, allocationId }).pipe(map(d => d.ipReservations));
  }

  reserveIp(input: {
    allocationId: string;
    ipAddress: string;
    hostname?: string | null;
    purpose: string;
    ciId?: string | null;
  }): Observable<IpReservation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ reserveIpAddress: IpReservation }>(`
      mutation ReserveIpAddress($tenantId: UUID!, $input: IpReservationInput!) {
        reserveIpAddress(tenantId: $tenantId, input: $input) {
          ${RESERVATION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map(d => d.reserveIpAddress));
  }

  releaseReservation(reservationId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ releaseIpReservation: boolean }>(`
      mutation ReleaseIpReservation($tenantId: UUID!, $reservationId: UUID!) {
        releaseIpReservation(tenantId: $tenantId, reservationId: $reservationId)
      }
    `, { tenantId, reservationId }).pipe(map(d => d.releaseIpReservation));
  }

  // ── IPAM: Utilities ────────────────────────────────────────────

  cidrSummary(cidr: string): Observable<CidrSummary> {
    return this.gql<{ cidrSummary: CidrSummary }>(`
      query CidrSummary($cidr: String!) {
        cidrSummary(cidr: $cidr) {
          network broadcast prefixLength totalAddresses usableAddresses ipVersion isPrivate
        }
      }
    `, { cidr }).pipe(map(d => d.cidrSummary));
  }

  // ── Hierarchy Levels ──────────────────────────────────────────

  getProviderHierarchyLevels(providerName: string): Observable<ProviderHierarchy | null> {
    return this.gql<{ providerHierarchyLevels: ProviderHierarchy | null }>(`
      query ProviderHierarchyLevels($providerName: String!) {
        providerHierarchyLevels(providerName: $providerName) {
          providerName rootType
          levels {
            typeId label icon allowedChildren supportsIpam supportsTags supportsEnvironment
          }
        }
      }
    `, { providerName }).pipe(map(d => d.providerHierarchyLevels));
  }

  // ── Blueprints ────────────────────────────────────────────────

  getBlueprints(providerName: string): Observable<LandingZoneBlueprint[]> {
    return this.gql<{ landingZoneBlueprints: LandingZoneBlueprint[] }>(`
      query LandingZoneBlueprints($providerName: String!) {
        landingZoneBlueprints(providerName: $providerName) {
          id name providerName description complexity features
          hierarchy networkConfig iamConfig securityConfig namingConfig
          defaultTags defaultAddressSpaces
        }
      }
    `, { providerName }).pipe(map(d => d.landingZoneBlueprints));
  }

  getBlueprint(blueprintId: string): Observable<LandingZoneBlueprint | null> {
    return this.gql<{ landingZoneBlueprint: LandingZoneBlueprint | null }>(`
      query LandingZoneBlueprint($blueprintId: String!) {
        landingZoneBlueprint(blueprintId: $blueprintId) {
          id name providerName description complexity features
          hierarchy networkConfig iamConfig securityConfig namingConfig
          defaultTags defaultAddressSpaces
        }
      }
    `, { blueprintId }).pipe(map(d => d.landingZoneBlueprint));
  }

  // ── Validation ───────────────────────────────────────────────

  validateLandingZone(zoneId: string): Observable<LandingZoneValidation> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ validateLandingZone: LandingZoneValidation }>(`
      query ValidateLandingZone($tenantId: UUID!, $zoneId: UUID!) {
        validateLandingZone(tenantId: $tenantId, zoneId: $zoneId) {
          ready
          checks { key label status message }
        }
      }
    `, { tenantId, zoneId }).pipe(map(d => d.validateLandingZone));
  }

  // ── Private GraphQL Helper ─────────────────────────────────────

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
