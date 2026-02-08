/**
 * Overview: TypeScript interfaces for authentication data.
 * Architecture: Auth type definitions (Section 5.1)
 * Dependencies: none
 * Concepts: Authentication, JWT tokens, user identity, tenant context
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  current_tenant_id: string | null;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string | null;
  provider_id: string;
  is_active: boolean;
  created_at: string;
}

export interface SessionInfo {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface SetupStatus {
  is_complete: boolean;
}

export interface SetupRequest {
  admin_email: string;
  admin_password: string;
  organization_name: string;
}

export interface DiscoverRequest {
  email: string;
}

export interface DiscoverResponse {
  found: boolean;
  tenant_id?: string;
  tenant_name?: string;
  tenant_slug?: string;
  has_local_auth?: boolean;
  sso_providers?: SSOProviderInfo[];
}

export interface SSOProviderInfo {
  id: string;
  name: string;
  idp_type: string;
}

export interface TenantLoginInfo {
  tenant_id: string;
  tenant_name: string;
  slug: string;
  has_local_auth: boolean;
  sso_providers: SSOProviderInfo[];
}
