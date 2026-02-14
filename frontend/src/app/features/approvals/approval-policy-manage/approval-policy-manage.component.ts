/**
 * Overview: Approval policy management — CRUD for per-tenant approval workflow policies.
 * Architecture: Feature component at /workflows/manage (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/approval.service
 * Concepts: Approval policy configuration, chain modes, approver resolution, tenant isolation
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ApprovalService } from '@core/services/approval.service';
import { DialogService } from '@shared/services/dialog.service';
import { AssignRoleDialogComponent } from '@shared/components/assign-role-dialog/assign-role-dialog.component';
import { AssignUserDialogComponent } from '@shared/components/assign-user-dialog/assign-user-dialog.component';
import { AssignGroupDialogComponent } from '@shared/components/assign-group-dialog/assign-group-dialog.component';
import { Role, Group } from '@core/models/permission.model';
import { User } from '@core/models/user.model';
import {
  ApprovalPolicy,
  ApprovalChainMode,
  ApprovalPolicyInput,
} from '@shared/models/approval.model';

@Component({
  selector: 'nimbus-approval-policy-manage',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, AssignRoleDialogComponent, AssignUserDialogComponent, AssignGroupDialogComponent],
  template: `
    <nimbus-layout>
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">Manage Approval Policies</h1>
        @if (!showForm()) {
          <button class="btn btn-primary" (click)="openCreateForm()">+ Add Policy</button>
        }
      </div>

      <!-- Create / Edit form -->
      @if (showForm()) {
        <div class="form-card">
          <h2 class="form-title">{{ editing() ? 'Edit Policy' : 'New Approval Policy' }}</h2>

          <div class="form-group">
            <label class="form-label">Operation Type</label>
            <select
              class="form-input"
              [(ngModel)]="formOperationType"
              [disabled]="!!editing()"
            >
              <option value="" disabled>Select an operation type</option>
              @for (op of operationTypes; track op.value) {
                <option [value]="op.value">{{ op.label }}</option>
              }
            </select>
            <span class="form-hint">
              Identifies which operation this policy governs. Cannot be changed after creation.
            </span>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Chain Mode</label>
              <select class="form-input" [(ngModel)]="formChainMode">
                <option value="SEQUENTIAL">Sequential</option>
                <option value="PARALLEL">Parallel</option>
                <option value="QUORUM">Quorum</option>
              </select>
              <span class="form-hint">
                Sequential: approvers in order. Parallel: all at once. Quorum: N-of-M.
              </span>
            </div>

            @if (formChainMode === 'QUORUM') {
              <div class="form-group">
                <label class="form-label">Quorum Required</label>
                <input
                  class="form-input"
                  type="number"
                  [(ngModel)]="formQuorumRequired"
                  min="1"
                />
                <span class="form-hint">
                  How many approvals needed out of the total approvers.
                </span>
              </div>
            }
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Timeout (minutes)</label>
              <input
                class="form-input"
                type="number"
                [(ngModel)]="formTimeoutMinutes"
                min="1"
              />
              <span class="form-hint">
                Per-step timeout. Default 1440 (24 hours).
              </span>
            </div>

            <div class="form-group">
              <label class="form-label">Active</label>
              <label class="toggle-label">
                <input type="checkbox" [(ngModel)]="formIsActive" />
                <span>{{ formIsActive ? 'Enabled' : 'Disabled' }}</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Approver Roles</label>
            <div class="chip-list">
              @for (role of formApproverRoles; track role.id; let i = $index) {
                <span class="chip">
                  {{ role.name }}
                  <button class="chip-remove" type="button" (click)="removeRole(i)">&times;</button>
                </span>
              }
              <button class="add-btn" type="button" (click)="addRole()">+ Add Role</button>
            </div>
            <span class="form-hint">
              Users with these roles can approve. Leave empty to use specific users below.
            </span>
          </div>

          <div class="form-group">
            <label class="form-label">Approver Groups</label>
            <div class="chip-list">
              @for (group of formApproverGroups; track group.id; let i = $index) {
                <span class="chip chip-group">
                  {{ group.name }}
                  <button class="chip-remove" type="button" (click)="removeGroup(i)">&times;</button>
                </span>
              }
              <button class="add-btn" type="button" (click)="addGroup()">+ Add Group</button>
            </div>
            <span class="form-hint">
              All members of these groups can approve.
            </span>
          </div>

          <div class="form-group">
            <label class="form-label">Approver Users</label>
            <div class="chip-list">
              @for (user of formApproverUsers; track user.id; let i = $index) {
                <span class="chip">
                  {{ user.label }}
                  <button class="chip-remove" type="button" (click)="removeApproverUser(i)">&times;</button>
                </span>
              }
              <button class="add-btn" type="button" (click)="addApproverUser()">+ Add User</button>
            </div>
            <span class="form-hint">
              Specific users who can approve.
            </span>
          </div>

          <div class="form-group">
            <label class="form-label">Escalation Users</label>
            <div class="chip-list">
              @for (user of formEscalationUsers; track user.id; let i = $index) {
                <span class="chip">
                  {{ user.label }}
                  <button class="chip-remove" type="button" (click)="removeEscalationUser(i)">&times;</button>
                </span>
              }
              <button class="add-btn" type="button" (click)="addEscalationUser()">+ Add User</button>
            </div>
            <span class="form-hint">
              Users notified when a step times out.
            </span>
          </div>

          <div class="form-actions">
            <button class="btn btn-secondary" (click)="cancelForm()">Cancel</button>
            <button
              class="btn btn-primary"
              (click)="savePolicy()"
              [disabled]="saving() || !formOperationType.trim()"
            >
              {{ saving() ? 'Saving...' : (editing() ? 'Update' : 'Create') }}
            </button>
          </div>
        </div>
      }

      <!-- Policy list -->
      @if (loading()) {
        <div class="loading">Loading policies...</div>
      } @else if (policies().length === 0 && !showForm()) {
        <div class="empty-state">
          <p>No approval policies configured for this tenant.</p>
          <p class="empty-hint">
            Create a policy to define how approvals work for specific operations
            (impersonation, deployments, etc.).
          </p>
        </div>
      } @else {
        <div class="policy-list">
          @for (policy of policies(); track policy.id) {
            <div class="policy-card" [class.inactive]="!policy.isActive">
              <div class="card-header">
                <span class="operation-type">{{ policy.operationType }}</span>
                <span class="chain-badge" [class]="'chain-' + policy.chainMode.toLowerCase()">
                  {{ policy.chainMode }}
                </span>
                @if (!policy.isActive) {
                  <span class="badge-inactive">Inactive</span>
                }
                <span class="card-actions">
                  <button class="btn-icon" title="Edit" (click)="openEditForm(policy)">&#9998;</button>
                  <button
                    class="btn-icon"
                    [title]="policy.isActive ? 'Deactivate' : 'Activate'"
                    (click)="toggleActive(policy)"
                  >
                    {{ policy.isActive ? '&#10003;' : '&#10007;' }}
                  </button>
                  <button class="btn-icon btn-danger" title="Delete" (click)="deletePolicy(policy)">
                    &#128465;
                  </button>
                </span>
              </div>
              <div class="card-body">
                <div class="card-meta">
                  @if (policy.chainMode === 'QUORUM') {
                    <span>Quorum: {{ policy.quorumRequired }}</span>
                  }
                  <span>Timeout: {{ formatTimeout(policy.timeoutMinutes) }}</span>
                </div>
                <div class="card-detail">
                  @if (policy.approverRoleNames?.length) {
                    <span class="detail-label">Roles:</span>
                    <span>{{ policy.approverRoleNames!.join(', ') }}</span>
                  }
                  @if (policy.approverGroupIds?.length) {
                    <span class="detail-label">Groups:</span>
                    <span class="mono">{{ policy.approverGroupIds!.length }} group(s)</span>
                  }
                  @if (policy.approverUserIds?.length) {
                    <span class="detail-label">Users:</span>
                    <span class="mono">{{ policy.approverUserIds!.length }} user(s)</span>
                  }
                  @if (policy.escalationUserIds?.length) {
                    <span class="detail-label">Escalation:</span>
                    <span class="mono">{{ policy.escalationUserIds!.length }} user(s)</span>
                  }
                </div>
              </div>
            </div>
          }
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page { padding: 0; max-width: 960px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;
    }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .loading { padding: 40px; text-align: center; color: #667; }
    .empty-state { padding: 60px; text-align: center; color: #667; }
    .empty-hint { font-size: 13px; color: #9ca3af; margin-top: 4px; }

    /* Form */
    .form-card {
      border: 1px solid #d0d5dd; border-radius: 10px; padding: 24px;
      background: #fff; margin-bottom: 20px;
    }
    .form-title { font-size: 17px; font-weight: 600; margin: 0 0 16px; }
    .form-group { margin-bottom: 14px; flex: 1; }
    .form-row { display: flex; gap: 16px; }
    .form-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: #344054; }
    .form-input {
      width: 100%; padding: 8px 10px; border: 1px solid #d0d5dd; border-radius: 6px;
      font-size: 13px; box-sizing: border-box; background: #fff;
    }
    .form-input:disabled { background: #f9fafb; color: #6b7280; }
    select.form-input { appearance: auto; }
    .form-hint { display: block; font-size: 11px; color: #9ca3af; margin-top: 3px; }
    .toggle-label {
      display: flex; align-items: center; gap: 8px; font-size: 13px; margin-top: 6px; cursor: pointer;
    }
    .form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }

    /* Buttons */
    .btn {
      padding: 7px 16px; border: none; border-radius: 6px;
      font-size: 13px; cursor: pointer; font-weight: 500;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-primary:hover:not(:disabled) { background: #1d4ed8; }
    .btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d0d5dd; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 4px 6px;
      font-size: 14px; border-radius: 4px; color: #667;
    }
    .btn-icon:hover { background: #f3f4f6; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fee2e2; }

    /* Policy list */
    .policy-list { display: flex; flex-direction: column; gap: 10px; }
    .policy-card {
      border: 1px solid #e4e7ec; border-radius: 8px; padding: 14px 16px;
      background: #fff; transition: box-shadow 0.15s;
    }
    .policy-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .policy-card.inactive { opacity: 0.6; }
    .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
    .operation-type { font-weight: 600; font-size: 14px; font-family: monospace; }
    .chain-badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .chain-sequential { background: #dbeafe; color: #1e40af; }
    .chain-parallel { background: #fef3c7; color: #92400e; }
    .chain-quorum { background: #d1fae5; color: #065f46; }
    .badge-inactive {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 11px; font-weight: 500; background: #f3f4f6; color: #6b7280;
    }
    .card-actions { margin-left: auto; display: flex; gap: 2px; }
    .card-body { font-size: 13px; }
    .card-meta { display: flex; gap: 16px; color: #6b7280; margin-bottom: 4px; }
    .card-detail { display: flex; gap: 12px; flex-wrap: wrap; }
    .detail-label { font-weight: 500; color: #374151; }
    .mono { font-family: monospace; font-size: 12px; }

    /* Chips */
    .chip-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; align-items: center; }
    .chip {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 3px 8px; background: #e0e7ff; color: #3730a3;
      border-radius: 4px; font-size: 12px; font-weight: 500;
    }
    .chip-remove {
      background: none; border: none; cursor: pointer; padding: 0 2px;
      color: #6366f1; font-size: 14px; line-height: 1;
    }
    .chip-group { background: #d1fae5; color: #065f46; }
    .chip-group .chip-remove { color: #10b981; }
    .chip-remove:hover { color: #dc2626; }
    .add-btn {
      padding: 4px 10px; font-size: 12px; border: 1px dashed #9ca3af;
      border-radius: 4px; background: none; cursor: pointer; color: #6b7280;
    }
    .add-btn:hover { border-color: #3b82f6; color: #3b82f6; }
  `],
})
export class ApprovalPolicyManageComponent implements OnInit {
  private approvalService = inject(ApprovalService);
  private dialogService = inject(DialogService);

  policies = signal<ApprovalPolicy[]>([]);
  loading = signal(true);
  saving = signal(false);
  showForm = signal(false);
  editing = signal<ApprovalPolicy | null>(null);

  readonly operationTypes = [
    { value: 'impersonation.standard', label: 'Standard Impersonation' },
    { value: 'impersonation.override', label: 'Override Impersonation' },
    { value: 'deployment', label: 'Deployment' },
    { value: 'drift_remediation', label: 'Drift Remediation' },
    { value: 'break_glass', label: 'Break Glass Access' },
  ];

  // Form fields
  formOperationType = '';
  formChainMode: ApprovalChainMode = 'SEQUENTIAL';
  formQuorumRequired = 1;
  formTimeoutMinutes = 1440;
  formIsActive = true;
  formApproverRoles: { id: string; name: string }[] = [];
  formApproverGroups: { id: string; name: string }[] = [];
  formApproverUsers: { id: string; label: string }[] = [];
  formEscalationUsers: { id: string; label: string }[] = [];

  ngOnInit(): void {
    this.loadPolicies();
  }

  loadPolicies(): void {
    this.loading.set(true);
    this.approvalService.listPolicies().subscribe({
      next: (policies) => {
        this.policies.set(policies);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  openCreateForm(): void {
    this.editing.set(null);
    this.resetForm();
    this.showForm.set(true);
  }

  openEditForm(policy: ApprovalPolicy): void {
    this.editing.set(policy);
    this.formOperationType = policy.operationType;
    this.formChainMode = policy.chainMode;
    this.formQuorumRequired = policy.quorumRequired;
    this.formTimeoutMinutes = policy.timeoutMinutes;
    this.formIsActive = policy.isActive;
    this.formApproverRoles = (policy.approverRoleNames ?? []).map((name) => ({ id: name, name }));
    this.formApproverGroups = (policy.approverGroupIds ?? []).map((id) => ({
      id,
      name: id.substring(0, 8) + '...',
    }));
    this.formApproverUsers = (policy.approverUserIds ?? []).map((id) => ({
      id,
      label: id.substring(0, 8) + '...',
    }));
    this.formEscalationUsers = (policy.escalationUserIds ?? []).map((id) => ({
      id,
      label: id.substring(0, 8) + '...',
    }));
    this.showForm.set(true);
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editing.set(null);
    this.resetForm();
  }

  savePolicy(): void {
    this.saving.set(true);

    const roleNames = this.formApproverRoles.map((r) => r.name);
    const groupIds = this.formApproverGroups.map((g) => g.id);
    const userIds = this.formApproverUsers.map((u) => u.id);
    const escalationIds = this.formEscalationUsers.map((u) => u.id);

    if (this.editing()) {
      const policy = this.editing()!;
      this.approvalService.updatePolicy(policy.id, {
        chainMode: this.formChainMode,
        quorumRequired: this.formQuorumRequired,
        timeoutMinutes: this.formTimeoutMinutes,
        isActive: this.formIsActive,
        approverRoleNames: roleNames.length ? roleNames : undefined,
        approverGroupIds: groupIds.length ? groupIds : undefined,
        approverUserIds: userIds.length ? userIds : undefined,
        escalationUserIds: escalationIds.length ? escalationIds : undefined,
      }).subscribe({
        next: (updated) => {
          this.saving.set(false);
          if (updated) {
            this.policies.set(
              this.policies().map((p) => (p.id === updated.id ? updated : p)),
            );
          }
          this.cancelForm();
        },
        error: () => {
          this.saving.set(false);
        },
      });
    } else {
      const input: ApprovalPolicyInput = {
        operationType: this.formOperationType.trim(),
        chainMode: this.formChainMode,
        quorumRequired: this.formQuorumRequired,
        timeoutMinutes: this.formTimeoutMinutes,
        isActive: this.formIsActive,
        approverRoleNames: roleNames.length ? roleNames : undefined,
        approverGroupIds: groupIds.length ? groupIds : undefined,
        approverUserIds: userIds.length ? userIds : undefined,
        escalationUserIds: escalationIds.length ? escalationIds : undefined,
      };

      this.approvalService.createPolicy(input).subscribe({
        next: (created) => {
          this.saving.set(false);
          this.policies.set([...this.policies(), created]);
          this.cancelForm();
        },
        error: () => {
          this.saving.set(false);
        },
      });
    }
  }

  toggleActive(policy: ApprovalPolicy): void {
    this.approvalService.updatePolicy(policy.id, {
      isActive: !policy.isActive,
    }).subscribe({
      next: (updated) => {
        if (updated) {
          this.policies.set(
            this.policies().map((p) => (p.id === updated.id ? updated : p)),
          );
        }
      },
    });
  }

  deletePolicy(policy: ApprovalPolicy): void {
    this.approvalService.deletePolicy(policy.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.policies.set(this.policies().filter((p) => p.id !== policy.id));
        }
      },
    });
  }

  formatTimeout(minutes: number): string {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const remaining = minutes % 60;
    if (remaining === 0) return `${hours}h`;
    return `${hours}h ${remaining}m`;
  }

  async addRole(): Promise<void> {
    const excludeIds = this.formApproverRoles.map((r) => r.id);
    const role = await this.dialogService.open<Role | undefined>(
      AssignRoleDialogComponent,
      { excludeIds },
    );
    if (role && !this.formApproverRoles.some((r) => r.name === role.name)) {
      this.formApproverRoles = [...this.formApproverRoles, { id: role.id, name: role.name }];
    }
  }

  removeRole(index: number): void {
    this.formApproverRoles = this.formApproverRoles.filter((_, i) => i !== index);
  }

  async addGroup(): Promise<void> {
    const excludeIds = this.formApproverGroups.map((g) => g.id);
    const group = await this.dialogService.open<Group | undefined>(
      AssignGroupDialogComponent,
      { excludeIds },
    );
    if (group && !this.formApproverGroups.some((g) => g.id === group.id)) {
      this.formApproverGroups = [...this.formApproverGroups, { id: group.id, name: group.name }];
    }
  }

  removeGroup(index: number): void {
    this.formApproverGroups = this.formApproverGroups.filter((_, i) => i !== index);
  }

  async addApproverUser(): Promise<void> {
    const excludeIds = this.formApproverUsers.map((u) => u.id);
    const user = await this.dialogService.open<User | undefined>(
      AssignUserDialogComponent,
      { excludeIds },
    );
    if (user && !this.formApproverUsers.some((u) => u.id === user.id)) {
      this.formApproverUsers = [
        ...this.formApproverUsers,
        { id: user.id, label: user.display_name || user.email },
      ];
    }
  }

  removeApproverUser(index: number): void {
    this.formApproverUsers = this.formApproverUsers.filter((_, i) => i !== index);
  }

  async addEscalationUser(): Promise<void> {
    const excludeIds = this.formEscalationUsers.map((u) => u.id);
    const user = await this.dialogService.open<User | undefined>(
      AssignUserDialogComponent,
      { excludeIds },
    );
    if (user && !this.formEscalationUsers.some((u) => u.id === user.id)) {
      this.formEscalationUsers = [
        ...this.formEscalationUsers,
        { id: user.id, label: user.display_name || user.email },
      ];
    }
  }

  removeEscalationUser(index: number): void {
    this.formEscalationUsers = this.formEscalationUsers.filter((_, i) => i !== index);
  }

  private resetForm(): void {
    this.formOperationType = '';
    this.formChainMode = 'SEQUENTIAL';
    this.formQuorumRequired = 1;
    this.formTimeoutMinutes = 1440;
    this.formIsActive = true;
    this.formApproverRoles = [];
    this.formApproverGroups = [];
    this.formApproverUsers = [];
    this.formEscalationUsers = [];
  }
}
