/**
 * Overview: TypeScript interfaces for impersonation data structures.
 * Architecture: Core impersonation type definitions (Section 5)
 * Dependencies: none
 * Concepts: Impersonation, session lifecycle, configuration
 */

export type ImpersonationMode = 'STANDARD' | 'OVERRIDE';
export type ImpersonationStatus =
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'ACTIVE'
  | 'ENDED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED';

export interface ImpersonationSession {
  id: string;
  tenant_id: string;
  requester_id: string;
  target_user_id: string;
  mode: ImpersonationMode;
  status: ImpersonationStatus;
  reason: string;
  rejection_reason: string | null;
  approver_id: string | null;
  approval_decision_at: string | null;
  started_at: string | null;
  expires_at: string | null;
  ended_at: string | null;
  end_reason: string | null;
  workflow_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImpersonationSessionList {
  items: ImpersonationSession[];
  total: number;
}

export interface ImpersonationConfig {
  standard_duration_minutes: number;
  override_duration_minutes: number;
  standard_requires_approval: boolean;
  override_requires_approval: boolean;
  max_duration_minutes: number;
}

export interface ImpersonationRequest {
  target_user_id: string;
  tenant_id: string;
  mode: ImpersonationMode;
  reason: string;
  password: string;
}

export interface ImpersonationApproval {
  decision: 'approve' | 'reject';
  reason?: string;
}

export interface ImpersonationStatusInfo {
  is_impersonating: boolean;
  session_id: string | null;
  original_user_id: string | null;
  original_tenant_id: string | null;
  target_user_email: string | null;
  started_at: string | null;
  expires_at: string | null;
}

export interface ImpersonationTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  session_id: string;
}
