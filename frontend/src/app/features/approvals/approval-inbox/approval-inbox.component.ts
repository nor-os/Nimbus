/**
 * Overview: Approval inbox — pending approvals for the current user with decision actions.
 * Architecture: Feature component at /approvals (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/core/services/approval.service
 * Concepts: Approval inbox, decision submission, delegation, status badges, pagination
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { Router } from '@angular/router';
import { ApprovalService } from '@core/services/approval.service';
import {
  ApprovalRequest,
} from '@shared/models/approval.model';

@Component({
  selector: 'nimbus-approval-inbox',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">Approval Inbox</h1>
        <div class="header-actions">
          <select class="filter-select" (change)="onStatusChange($event)">
            <option value="">Pending (default)</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="EXPIRED">Expired</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading approvals...</div>
      } @else if (requests().length === 0) {
        <div class="empty-state">
          <p>No {{ statusFilter() || 'pending' }} approval requests.</p>
        </div>
      } @else {
        <div class="approval-list">
          @for (req of requests(); track req.id) {
            <div class="approval-card" [class.resolved]="req.status !== 'PENDING'">
              <div class="card-header">
                <span class="badge" [class]="'badge-' + req.status.toLowerCase()">
                  {{ req.status }}
                </span>
                <span class="operation-type">{{ req.operationType }}</span>
                <span class="created-at">{{ formatTime(req.createdAt) }}</span>
              </div>
              <div class="card-body">
                <h3 class="card-title">{{ req.title }}</h3>
                @if (req.description) {
                  <p class="card-desc">{{ req.description }}</p>
                }
                <div class="card-meta">
                  <span>Mode: {{ req.chainMode }}</span>
                  @if (req.chainMode === 'QUORUM') {
                    <span>Quorum: {{ req.quorumRequired }}</span>
                  }
                </div>
              </div>

              <!-- Steps -->
              <div class="steps">
                @for (step of req.steps; track step.id) {
                  <div class="step" [class]="'step-' + step.status.toLowerCase()">
                    <span class="step-badge" [class]="'badge-' + step.status.toLowerCase()">
                      {{ step.status }}
                    </span>
                    <span class="step-approver">Step {{ step.stepOrder + 1 }}</span>
                    @if (step.reason) {
                      <span class="step-reason">{{ step.reason }}</span>
                    }
                    @if (step.decisionAt) {
                      <span class="step-time">{{ formatTime(step.decisionAt) }}</span>
                    }

                    <!-- Action buttons for pending steps assigned to current user -->
                    @if (step.status === 'PENDING' && req.status === 'PENDING') {
                      <div class="step-actions">
                        <button
                          class="btn btn-approve"
                          (click)="submitDecision(step.id, 'approve')"
                          [disabled]="submitting()"
                        >
                          Approve
                        </button>
                        <button
                          class="btn btn-reject"
                          (click)="openRejectDialog(step.id)"
                          [disabled]="submitting()"
                        >
                          Reject
                        </button>
                        <button
                          class="btn btn-delegate"
                          (click)="openDelegateDialog(step.id)"
                          [disabled]="submitting()"
                        >
                          Delegate
                        </button>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }
        </div>

        <!-- Pagination -->
        @if (total() > limit) {
          <div class="pagination">
            <button
              class="btn btn-secondary"
              [disabled]="offset() === 0"
              (click)="prevPage()"
            >
              Previous
            </button>
            <span class="page-info">
              {{ offset() + 1 }}–{{ offset() + requests().length }} of {{ total() }}
            </span>
            <button
              class="btn btn-secondary"
              [disabled]="offset() + limit >= total()"
              (click)="nextPage()"
            >
              Next
            </button>
          </div>
        }
      }

      <!-- Reject reason dialog -->
      @if (showRejectDialog()) {
        <div class="dialog-overlay" (click)="closeDialogs()">
          <div class="dialog" (click)="$event.stopPropagation()">
            <h3>Reject Approval</h3>
            <textarea
              [(ngModel)]="rejectReason"
              placeholder="Reason for rejection (optional)"
              rows="3"
              class="dialog-input"
            ></textarea>
            <div class="dialog-actions">
              <button class="btn btn-secondary" (click)="closeDialogs()">Cancel</button>
              <button class="btn btn-reject" (click)="confirmReject()">Reject</button>
            </div>
          </div>
        </div>
      }

      <!-- Delegate dialog -->
      @if (showDelegateDialog()) {
        <div class="dialog-overlay" (click)="closeDialogs()">
          <div class="dialog" (click)="$event.stopPropagation()">
            <h3>Delegate Approval</h3>
            <input
              [(ngModel)]="delegateUserId"
              placeholder="User ID to delegate to"
              class="dialog-input"
            />
            <div class="dialog-actions">
              <button class="btn btn-secondary" (click)="closeDialogs()">Cancel</button>
              <button class="btn btn-primary" (click)="confirmDelegate()">Delegate</button>
            </div>
          </div>
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page { padding: 0; max-width: 960px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-actions { display: flex; gap: 8px; }
    .filter-select { padding: 6px 10px; border: 1px solid #d0d5dd; border-radius: 6px; font-size: 13px; }
    .loading { padding: 40px; text-align: center; color: #667; }
    .empty-state { padding: 60px; text-align: center; color: #667; }
    .approval-list { display: flex; flex-direction: column; gap: 12px; }
    .approval-card {
      border: 1px solid #e4e7ec; border-radius: 8px; padding: 16px;
      background: #fff; transition: box-shadow 0.15s;
    }
    .approval-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .approval-card.resolved { opacity: 0.75; }
    .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .badge-pending { background: #fef3c7; color: #92400e; }
    .badge-approved { background: #d1fae5; color: #065f46; }
    .badge-rejected { background: #fee2e2; color: #991b1b; }
    .badge-expired { background: #e5e7eb; color: #374151; }
    .badge-cancelled { background: #e5e7eb; color: #6b7280; }
    .badge-delegated { background: #dbeafe; color: #1e40af; }
    .badge-skipped { background: #f3f4f6; color: #6b7280; }
    .operation-type { font-size: 12px; color: #667; font-family: monospace; }
    .created-at { font-size: 12px; color: #9ca3af; margin-left: auto; }
    .card-body { margin-bottom: 10px; }
    .card-title { font-size: 15px; font-weight: 500; margin: 0 0 4px; }
    .card-desc { font-size: 13px; color: #555; margin: 0; }
    .card-meta { font-size: 12px; color: #9ca3af; display: flex; gap: 12px; margin-top: 4px; }
    .steps { display: flex; flex-direction: column; gap: 6px; }
    .step {
      display: flex; align-items: center; gap: 8px; padding: 8px 12px;
      background: #f9fafb; border-radius: 6px; font-size: 13px;
    }
    .step-badge { font-size: 10px; }
    .step-approver { font-weight: 500; }
    .step-reason { color: #6b7280; font-style: italic; }
    .step-time { color: #9ca3af; font-size: 11px; margin-left: auto; }
    .step-actions { display: flex; gap: 6px; margin-left: auto; }
    .btn {
      padding: 5px 12px; border: none; border-radius: 5px;
      font-size: 12px; cursor: pointer; font-weight: 500;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-approve { background: #059669; color: #fff; }
    .btn-approve:hover:not(:disabled) { background: #047857; }
    .btn-reject { background: #dc2626; color: #fff; }
    .btn-reject:hover:not(:disabled) { background: #b91c1c; }
    .btn-delegate { background: #2563eb; color: #fff; }
    .btn-delegate:hover:not(:disabled) { background: #1d4ed8; }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d0d5dd; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 16px 0; }
    .page-info { font-size: 13px; color: #667; }
    .dialog-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.4);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 10px; padding: 24px;
      width: 400px; max-width: 90vw; box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }
    .dialog h3 { margin: 0 0 12px; font-size: 16px; }
    .dialog-input {
      width: 100%; padding: 8px 10px; border: 1px solid #d0d5dd;
      border-radius: 6px; font-size: 13px; box-sizing: border-box; margin-bottom: 12px;
    }
    textarea.dialog-input { resize: vertical; }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
  `],
})
export class ApprovalInboxComponent implements OnInit {
  private approvalService = inject(ApprovalService);
  private router = inject(Router);

  requests = signal<ApprovalRequest[]>([]);
  total = signal(0);
  loading = signal(true);
  submitting = signal(false);
  statusFilter = signal('');
  offset = signal(0);
  limit = 20;

  showRejectDialog = signal(false);
  showDelegateDialog = signal(false);
  activeStepId = '';
  rejectReason = '';
  delegateUserId = '';

  ngOnInit(): void {
    this.loadPending();
  }

  onStatusChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.statusFilter.set(value);
    this.offset.set(0);
    if (value) {
      this.loadAll();
    } else {
      this.loadPending();
    }
  }

  loadPending(): void {
    this.loading.set(true);
    this.approvalService.getPendingApprovals(this.offset(), this.limit).subscribe({
      next: (data) => {
        this.requests.set(data.items);
        this.total.set(data.total);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  loadAll(): void {
    this.loading.set(true);
    this.approvalService.listRequests({
      status: this.statusFilter() || undefined,
      offset: this.offset(),
      limit: this.limit,
    }).subscribe({
      next: (data) => {
        this.requests.set(data.items);
        this.total.set(data.total);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  submitDecision(stepId: string, decision: 'approve' | 'reject', reason?: string): void {
    this.submitting.set(true);
    this.approvalService.submitDecision({ stepId, decision, reason }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.loadPending();
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  openRejectDialog(stepId: string): void {
    this.activeStepId = stepId;
    this.rejectReason = '';
    this.showRejectDialog.set(true);
  }

  openDelegateDialog(stepId: string): void {
    this.activeStepId = stepId;
    this.delegateUserId = '';
    this.showDelegateDialog.set(true);
  }

  closeDialogs(): void {
    this.showRejectDialog.set(false);
    this.showDelegateDialog.set(false);
  }

  confirmReject(): void {
    this.closeDialogs();
    this.submitDecision(this.activeStepId, 'reject', this.rejectReason || undefined);
  }

  confirmDelegate(): void {
    if (!this.delegateUserId.trim()) return;
    this.closeDialogs();
    this.submitting.set(true);
    this.approvalService.delegateStep({
      stepId: this.activeStepId,
      delegateToId: this.delegateUserId.trim(),
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.loadPending();
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  prevPage(): void {
    this.offset.set(Math.max(0, this.offset() - this.limit));
    this.refresh();
  }

  nextPage(): void {
    this.offset.set(this.offset() + this.limit);
    this.refresh();
  }

  private refresh(): void {
    if (this.statusFilter()) {
      this.loadAll();
    } else {
      this.loadPending();
    }
  }

  formatTime(iso: string): string {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }
}
