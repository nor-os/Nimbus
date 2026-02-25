/**
 * Overview: TypeScript interfaces for networking entities — connectivity, peering, private endpoints, load balancers.
 * Architecture: Frontend data models for managed networking entities (Section 6)
 * Dependencies: None
 * Concepts: LZ-level networking (connectivity, peering, PE policies, shared LBs) and per-env instances.
 */

// ── Connectivity ────────────────────────────────────────────────────

export type ConnectivityType = 'VPN' | 'EXPRESS_ROUTE' | 'DIRECT_CONNECT' | 'FAST_CONNECT' | 'HA_VPN' | 'CLOUD_INTERCONNECT' | 'SDN_OVERLAY';
export type NetworkingStatus = 'PLANNED' | 'PROVISIONING' | 'ACTIVE' | 'FAILED' | 'DECOMMISSIONED';

export interface ConnectivityConfig {
  id: string;
  tenantId: string;
  landingZoneId: string;
  name: string;
  description: string | null;
  connectivityType: ConnectivityType;
  providerType: string;
  status: NetworkingStatus;
  config: Record<string, unknown> | null;
  remoteConfig: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ConnectivityConfigInput {
  name: string;
  connectivityType: string;
  providerType: string;
  description?: string | null;
  status?: string;
  config?: Record<string, unknown> | null;
  remoteConfig?: Record<string, unknown> | null;
}

// ── Peering ─────────────────────────────────────────────────────────

export type PeeringType = 'VPC_PEERING' | 'VNET_PEERING' | 'TGW_ATTACHMENT' | 'DRG_ATTACHMENT' | 'SHARED_VPC';

export interface PeeringConfig {
  id: string;
  tenantId: string;
  landingZoneId: string;
  environmentId: string | null;
  name: string;
  peeringType: PeeringType;
  status: NetworkingStatus;
  hubConfig: Record<string, unknown> | null;
  spokeConfig: Record<string, unknown> | null;
  routingConfig: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PeeringConfigInput {
  name: string;
  peeringType: string;
  environmentId?: string | null;
  status?: string;
  hubConfig?: Record<string, unknown> | null;
  spokeConfig?: Record<string, unknown> | null;
  routingConfig?: Record<string, unknown> | null;
}

// ── Private Endpoints ───────────────────────────────────────────────

export type EndpointType = 'PRIVATE_LINK' | 'PRIVATE_ENDPOINT' | 'PRIVATE_SERVICE_CONNECT' | 'SERVICE_GATEWAY';

export interface PrivateEndpointPolicy {
  id: string;
  tenantId: string;
  landingZoneId: string;
  name: string;
  serviceName: string;
  endpointType: EndpointType;
  providerType: string;
  config: Record<string, unknown> | null;
  status: NetworkingStatus;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PrivateEndpointPolicyInput {
  name: string;
  serviceName: string;
  endpointType: string;
  providerType: string;
  config?: Record<string, unknown> | null;
  status?: string;
}

export interface EnvironmentPrivateEndpoint {
  id: string;
  tenantId: string;
  environmentId: string;
  policyId: string | null;
  serviceName: string;
  endpointType: EndpointType;
  config: Record<string, unknown> | null;
  status: NetworkingStatus;
  cloudResourceId: string | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EnvironmentPrivateEndpointInput {
  serviceName: string;
  endpointType: string;
  policyId?: string | null;
  config?: Record<string, unknown> | null;
  status?: string;
}

// ── Load Balancers ──────────────────────────────────────────────────

export type LbType = 'ALB' | 'NLB' | 'APP_GATEWAY' | 'AZURE_LB' | 'GCP_LB' | 'OCI_LB';

export interface SharedLoadBalancer {
  id: string;
  tenantId: string;
  landingZoneId: string;
  name: string;
  lbType: LbType;
  providerType: string;
  config: Record<string, unknown> | null;
  status: NetworkingStatus;
  cloudResourceId: string | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SharedLoadBalancerInput {
  name: string;
  lbType: string;
  providerType: string;
  config?: Record<string, unknown> | null;
  status?: string;
}

export interface EnvironmentLoadBalancer {
  id: string;
  tenantId: string;
  environmentId: string;
  sharedLbId: string | null;
  name: string;
  lbType: LbType;
  config: Record<string, unknown> | null;
  status: NetworkingStatus;
  cloudResourceId: string | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EnvironmentLoadBalancerInput {
  name: string;
  lbType: string;
  sharedLbId?: string | null;
  config?: Record<string, unknown> | null;
  status?: string;
}
