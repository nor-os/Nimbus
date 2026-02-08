/**
 * Overview: TypeScript interfaces for identity provider data structures.
 * Architecture: Core identity provider type definitions (Section 5.1)
 * Dependencies: none
 * Concepts: Identity providers, SSO, OIDC, SAML, claim mappings, SCIM
 */

export interface IdentityProvider {
  id: string;
  tenant_id: string;
  name: string;
  idp_type: 'local' | 'oidc' | 'saml';
  is_enabled: boolean;
  is_default: boolean;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimMapping {
  id: string;
  identity_provider_id: string;
  claim_name: string;
  claim_value: string;
  role_id: string;
  group_id: string | null;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface ClaimMappingCreate {
  claim_name: string;
  claim_value: string;
  role_id: string;
  group_id?: string | null;
  priority?: number;
}

export interface IdentityProviderCreate {
  name: string;
  idp_type: 'local' | 'oidc' | 'saml';
  is_enabled?: boolean;
  is_default?: boolean;
  config?: Record<string, unknown> | null;
}

export interface IdentityProviderUpdate {
  name?: string;
  is_enabled?: boolean;
  is_default?: boolean;
  config?: Record<string, unknown> | null;
}

export interface SCIMToken {
  id: string;
  tenant_id: string;
  description: string | null;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface SCIMTokenCreate {
  description?: string | null;
  expires_in_days?: number | null;
}

export interface SCIMTokenCreateResponse extends SCIMToken {
  token: string;
}

export interface SSOProviderInfo {
  id: string;
  name: string;
  idp_type: string;
}
