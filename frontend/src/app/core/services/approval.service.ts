/**
 * Overview: Approval service with GraphQL methods for policies, requests, inbox, decisions.
 * Architecture: Core service layer for approval workflows (Section 3.2)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Approval chains, GraphQL queries/mutations, inbox, decision submission
 */
import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  ApprovalPolicy,
  ApprovalRequest,
  ApprovalRequestListResponse,
  ApprovalPolicyInput,
  ApprovalPolicyUpdateInput,
  ApprovalDecisionInput,
  ApprovalDelegateInput,
} from '@shared/models/approval.model';

const APPROVAL_REQUEST_FIELDS = `
  id tenantId operationType requesterId workflowId parentWorkflowId
  chainMode quorumRequired status title description context resolvedAt
  createdAt updatedAt
  steps {
    id tenantId approvalRequestId stepOrder approverId delegateToId
    status decisionAt reason createdAt updatedAt
  }
`;

const POLICY_FIELDS = `
  id tenantId operationType chainMode quorumRequired timeoutMinutes
  escalationUserIds approverRoleNames approverUserIds approverGroupIds isActive
  createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class ApprovalService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  readonly pendingCount = signal(0);

  // -- Policy queries --

  listPolicies(): Observable<ApprovalPolicy[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ approvalPolicies: ApprovalPolicy[] }>(`
      query ApprovalPolicies($tenantId: UUID!) {
        approvalPolicies(tenantId: $tenantId) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map((data) => data.approvalPolicies),
    );
  }

  createPolicy(input: ApprovalPolicyInput): Observable<ApprovalPolicy> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createApprovalPolicy: ApprovalPolicy }>(`
      mutation CreatePolicy($tenantId: UUID!, $input: ApprovalPolicyInput!) {
        createApprovalPolicy(tenantId: $tenantId, input: $input) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((data) => data.createApprovalPolicy),
    );
  }

  updatePolicy(policyId: string, input: ApprovalPolicyUpdateInput): Observable<ApprovalPolicy | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateApprovalPolicy: ApprovalPolicy | null }>(`
      mutation UpdatePolicy($tenantId: UUID!, $policyId: UUID!, $input: ApprovalPolicyUpdateInput!) {
        updateApprovalPolicy(tenantId: $tenantId, policyId: $policyId, input: $input) {
          ${POLICY_FIELDS}
        }
      }
    `, { tenantId, policyId, input }).pipe(
      map((data) => data.updateApprovalPolicy),
    );
  }

  deletePolicy(policyId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteApprovalPolicy: boolean }>(`
      mutation DeletePolicy($tenantId: UUID!, $policyId: UUID!) {
        deleteApprovalPolicy(tenantId: $tenantId, policyId: $policyId)
      }
    `, { tenantId, policyId }).pipe(
      map((data) => data.deleteApprovalPolicy),
    );
  }

  // -- Request queries --

  listRequests(params: {
    status?: string;
    requesterId?: string;
    offset?: number;
    limit?: number;
  } = {}): Observable<ApprovalRequestListResponse> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ approvalRequests: ApprovalRequestListResponse }>(`
      query ApprovalRequests(
        $tenantId: UUID!
        $status: String
        $requesterId: UUID
        $offset: Int
        $limit: Int
      ) {
        approvalRequests(
          tenantId: $tenantId
          status: $status
          requesterId: $requesterId
          offset: $offset
          limit: $limit
        ) {
          items { ${APPROVAL_REQUEST_FIELDS} }
          total
        }
      }
    `, { tenantId, ...params }).pipe(
      map((data) => data.approvalRequests),
    );
  }

  getRequest(requestId: string): Observable<ApprovalRequest | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ approvalRequest: ApprovalRequest | null }>(`
      query ApprovalRequest($tenantId: UUID!, $requestId: UUID!) {
        approvalRequest(tenantId: $tenantId, requestId: $requestId) {
          ${APPROVAL_REQUEST_FIELDS}
        }
      }
    `, { tenantId, requestId }).pipe(
      map((data) => data.approvalRequest),
    );
  }

  // -- Inbox --

  getPendingApprovals(offset = 0, limit = 50): Observable<ApprovalRequestListResponse> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ pendingApprovals: ApprovalRequestListResponse }>(`
      query PendingApprovals($tenantId: UUID!, $offset: Int, $limit: Int) {
        pendingApprovals(tenantId: $tenantId, offset: $offset, limit: $limit) {
          items { ${APPROVAL_REQUEST_FIELDS} }
          total
        }
      }
    `, { tenantId, offset, limit }).pipe(
      tap((data) => this.pendingCount.set(data.pendingApprovals.total)),
      map((data) => data.pendingApprovals),
    );
  }

  // -- Decisions --

  submitDecision(input: ApprovalDecisionInput): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ submitApprovalDecision: boolean }>(`
      mutation SubmitDecision($tenantId: UUID!, $input: ApprovalDecisionGQLInput!) {
        submitApprovalDecision(tenantId: $tenantId, input: $input)
      }
    `, { tenantId, input }).pipe(
      map((data) => data.submitApprovalDecision),
    );
  }

  delegateStep(input: ApprovalDelegateInput): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ delegateApproval: boolean }>(`
      mutation DelegateApproval($tenantId: UUID!, $input: ApprovalDelegateGQLInput!) {
        delegateApproval(tenantId: $tenantId, input: $input)
      }
    `, { tenantId, input }).pipe(
      map((data) => data.delegateApproval),
    );
  }

  cancelRequest(requestId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cancelApprovalRequest: boolean }>(`
      mutation CancelApproval($tenantId: UUID!, $requestId: UUID!) {
        cancelApprovalRequest(tenantId: $tenantId, requestId: $requestId)
      }
    `, { tenantId, requestId }).pipe(
      map((data) => data.cancelApprovalRequest),
    );
  }

  // -- Private GraphQL helper --

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
