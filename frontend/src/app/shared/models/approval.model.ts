/**
 * Overview: TypeScript interfaces for approval workflow data.
 * Architecture: Frontend data models for approval policies, requests, steps (Section 7.2)
 * Dependencies: None
 * Concepts: Approval chains, policy configuration, decision submission, delegation
 */

export type ApprovalChainMode = 'SEQUENTIAL' | 'PARALLEL' | 'QUORUM';
export type ApprovalRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';
export type ApprovalStepStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'DELEGATED' | 'SKIPPED' | 'EXPIRED';

export interface ApprovalPolicy {
  id: string;
  tenantId: string;
  operationType: string;
  chainMode: ApprovalChainMode;
  quorumRequired: number;
  timeoutMinutes: number;
  escalationUserIds: string[] | null;
  approverRoleNames: string[] | null;
  approverUserIds: string[] | null;
  approverGroupIds: string[] | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ApprovalStep {
  id: string;
  tenantId: string;
  approvalRequestId: string;
  stepOrder: number;
  approverId: string;
  delegateToId: string | null;
  status: ApprovalStepStatus;
  decisionAt: string | null;
  reason: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ApprovalRequest {
  id: string;
  tenantId: string;
  operationType: string;
  requesterId: string;
  workflowId: string | null;
  parentWorkflowId: string | null;
  chainMode: string;
  quorumRequired: number;
  status: ApprovalRequestStatus;
  title: string;
  description: string | null;
  context: Record<string, unknown> | null;
  resolvedAt: string | null;
  steps: ApprovalStep[];
  createdAt: string;
  updatedAt: string;
}

export interface ApprovalRequestListResponse {
  items: ApprovalRequest[];
  total: number;
}

export interface ApprovalPolicyInput {
  operationType: string;
  chainMode: ApprovalChainMode;
  quorumRequired: number;
  timeoutMinutes: number;
  escalationUserIds?: string[];
  approverRoleNames?: string[];
  approverUserIds?: string[];
  approverGroupIds?: string[];
  isActive: boolean;
}

export interface ApprovalPolicyUpdateInput {
  chainMode?: ApprovalChainMode;
  quorumRequired?: number;
  timeoutMinutes?: number;
  escalationUserIds?: string[];
  approverRoleNames?: string[];
  approverUserIds?: string[];
  approverGroupIds?: string[];
  isActive?: boolean;
}

export interface ApprovalDecisionInput {
  stepId: string;
  decision: 'approve' | 'reject';
  reason?: string;
}

export interface ApprovalDelegateInput {
  stepId: string;
  delegateToId: string;
}
