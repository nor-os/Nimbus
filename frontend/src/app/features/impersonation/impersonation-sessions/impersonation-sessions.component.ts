/**
 * Overview: Impersonation hub with user picker to start sessions and sessions table with actions.
 * Architecture: Feature component for impersonation management under Users & Roles (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services
 * Concepts: Impersonation sessions, user search, approval workflow, session management
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ImpersonationService } from '@core/services/impersonation.service';
import { UserService } from '@core/services/user.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { ImpersonationSession, ImpersonationMode } from '@core/models/impersonation.model';
import { User } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

type ActiveTab = 'sessions' | 'request';

@Component({
  selector: 'nimbus-impersonation-sessions',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LayoutComponent, HasPermissionDirective],
  template: `
    <nimbus-layout>
      <div class="page">
        <div class="page-header">
          <h1>Impersonate</h1>
          <p class="subtitle">Impersonate a user to troubleshoot issues or verify permissions in their context.</p>
        </div>

        <!-- Tabs -->
        <div class="tabs">
          <button
            class="tab"
            [class.active]="activeTab() === 'request'"
            (click)="activeTab.set('request')"
            *hasPermission="'impersonation:session:create'"
          >Request</button>
          <button
            class="tab"
            [class.active]="activeTab() === 'sessions'"
            (click)="switchToSessions()"
          >Sessions @if (sessionCount() > 0) { <span class="tab-count">{{ sessionCount() }}</span> }</button>
        </div>

        <!-- Request tab -->
        @if (activeTab() === 'request') {
          <div class="card">
            <h2>Start Impersonation</h2>
            <p class="card-desc">Search for a user in the current tenant, then provide a reason and your password to request an impersonation session.</p>

            <!-- User search -->
            <div class="field">
              <label for="user-search">Find User</label>
              <div class="search-row">
                <input
                  id="user-search"
                  type="text"
                  class="form-input"
                  [(ngModel)]="userSearch"
                  (input)="searchUsers()"
                  placeholder="Search by email or name..."
                  autocomplete="off"
                />
              </div>
            </div>

            @if (searchLoading()) {
              <div class="search-status">Searching...</div>
            }

            @if (searchResults().length > 0 && !selectedUser()) {
              <div class="user-results">
                @for (u of searchResults(); track u.id) {
                  <button class="user-row" (click)="selectUser(u)">
                    <span class="user-avatar">{{ (u.display_name || u.email).charAt(0).toUpperCase() }}</span>
                    <div class="user-info">
                      <span class="user-name">{{ u.display_name || u.email }}</span>
                      @if (u.display_name) {
                        <span class="user-email">{{ u.email }}</span>
                      }
                    </div>
                    <span class="user-status" [class.inactive]="!u.is_active">{{ u.is_active ? 'Active' : 'Inactive' }}</span>
                  </button>
                }
              </div>
            }

            <!-- Selected user + request form -->
            @if (selectedUser()) {
              <div class="selected-card">
                <div class="selected-header">
                  <div class="selected-user">
                    <span class="user-avatar lg">{{ (selectedUser()!.display_name || selectedUser()!.email).charAt(0).toUpperCase() }}</span>
                    <div class="user-info">
                      <span class="user-name">{{ selectedUser()!.display_name || selectedUser()!.email }}</span>
                      @if (selectedUser()!.display_name) {
                        <span class="user-email">{{ selectedUser()!.email }}</span>
                      }
                    </div>
                  </div>
                  <button class="clear-btn" (click)="clearSelection()">Change</button>
                </div>

                <div class="field">
                  <label>Mode</label>
                  <div class="mode-toggle">
                    <button class="mode-btn" [class.active]="requestMode === 'STANDARD'" (click)="requestMode = 'STANDARD'">
                      Standard
                    </button>
                    <button class="mode-btn override" [class.active]="requestMode === 'OVERRIDE'" (click)="requestMode = 'OVERRIDE'"
                      *hasPermission="'impersonation:override:create'"
                    >
                      Override
                    </button>
                  </div>
                  <p class="hint">
                    @if (requestMode === 'STANDARD') {
                      Act as this user via temporary token. Their account is unaffected.
                    } @else {
                      Emergency access: deactivate user and set temporary password. Restored on session end.
                    }
                  </p>
                </div>

                <div class="field">
                  <label for="reason">Reason</label>
                  <textarea
                    id="reason"
                    class="form-input"
                    [(ngModel)]="requestReason"
                    placeholder="Explain why impersonation is needed (min 10 characters)..."
                    rows="3"
                  ></textarea>
                </div>

                <div class="field">
                  <label for="password">Your Password</label>
                  <input
                    id="password"
                    type="password"
                    class="form-input"
                    [(ngModel)]="requestPassword"
                    placeholder="Re-enter your password to confirm"
                  />
                </div>

                @if (requestError()) {
                  <div class="error-msg">{{ requestError() }}</div>
                }

                <div class="form-actions">
                  <button
                    class="btn btn-primary"
                    [disabled]="requestSubmitting() || requestReason.length < 10 || !requestPassword"
                    (click)="submitRequest()"
                  >
                    {{ requestSubmitting() ? 'Submitting...' : 'Request Impersonation' }}
                  </button>
                </div>
              </div>
            }
          </div>
        }

        <!-- Sessions tab -->
        @if (activeTab() === 'sessions') {
          @if (sessionsLoading()) {
            <div class="loading">Loading sessions...</div>
          } @else if (sessions().length === 0) {
            <div class="empty-state">
              <div class="empty-icon">&#9783;</div>
              <p class="empty-title">No sessions</p>
              <p class="empty-desc">Impersonation sessions will appear here once created. Use the Request tab to impersonate a user.</p>
            </div>
          } @else {
            <div class="table-container">
              <table class="table">
                <thead>
                  <tr>
                    <th>Requester</th>
                    <th>Target</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Expires</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (s of sessions(); track s.id) {
                    <tr>
                      <td>{{ s.requester_id | slice:0:8 }}...</td>
                      <td>{{ s.target_user_id | slice:0:8 }}...</td>
                      <td>
                        <span class="badge" [class.badge-override]="s.mode === 'OVERRIDE'">
                          {{ s.mode }}
                        </span>
                      </td>
                      <td>
                        <span class="status-badge" [attr.data-status]="s.status">
                          {{ formatStatus(s.status) }}
                        </span>
                      </td>
                      <td>{{ s.created_at | date:'short' }}</td>
                      <td>{{ s.expires_at ? (s.expires_at | date:'short') : '\u2014' }}</td>
                      <td class="actions">
                        @if (s.status === 'PENDING_APPROVAL') {
                          <button class="action-btn approve" (click)="approve(s)">Approve</button>
                          <button class="action-btn reject" (click)="reject(s)">Reject</button>
                        }
                        @if (s.status === 'ACTIVE') {
                          <button class="action-btn end" (click)="end(s)">End</button>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page { padding: 0; }
    .page-header { margin-bottom: 1.25rem; }
    .page-header h1 { margin: 0 0 0.25rem; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .subtitle { margin: 0; font-size: 0.8125rem; color: #64748b; }

    /* ── Tabs ────────────────────────────────── */
    .tabs {
      display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.25rem;
    }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      cursor: pointer; font-family: inherit; border-bottom: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab-count {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 1.25rem; height: 1.25rem; padding: 0 0.375rem;
      background: #e2e8f0; border-radius: 10px; font-size: 0.6875rem; font-weight: 600;
      margin-left: 0.375rem;
    }
    .tab.active .tab-count { background: #dbeafe; color: #1d4ed8; }

    /* ── Request card ────────────────────────── */
    .card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .card h2 { margin: 0 0 0.25rem; font-size: 1rem; font-weight: 600; color: #1e293b; }
    .card-desc { margin: 0 0 1.25rem; font-size: 0.8125rem; color: #64748b; }
    .field { margin-bottom: 1rem; }
    .field label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit;
      box-sizing: border-box;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .search-status { font-size: 0.75rem; color: #64748b; padding: 0.5rem 0; }
    .hint { font-size: 0.75rem; color: #64748b; margin: 0.375rem 0 0; }

    /* ── User search results ─────────────────── */
    .user-results {
      border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 1rem;
      max-height: 240px; overflow-y: auto;
    }
    .user-row {
      display: flex; align-items: center; gap: 0.75rem; width: 100%;
      padding: 0.625rem 0.75rem; border: none; background: #fff;
      cursor: pointer; font-family: inherit; text-align: left;
      border-bottom: 1px solid #f1f5f9; transition: background 0.1s;
    }
    .user-row:last-child { border-bottom: none; }
    .user-row:hover { background: #f8fafc; }
    .user-avatar {
      display: flex; align-items: center; justify-content: center;
      width: 2rem; height: 2rem; border-radius: 50%;
      background: #e0e7ff; color: #4338ca; font-size: 0.8125rem; font-weight: 600;
      flex-shrink: 0;
    }
    .user-avatar.lg { width: 2.5rem; height: 2.5rem; font-size: 1rem; }
    .user-info { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .user-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .user-email { font-size: 0.75rem; color: #64748b; }
    .user-status {
      font-size: 0.6875rem; font-weight: 600; color: #166534;
      padding: 0.125rem 0.5rem; background: #dcfce7; border-radius: 10px;
    }
    .user-status.inactive { color: #dc2626; background: #fef2f2; }

    /* ── Selected user ───────────────────────── */
    .selected-card {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1rem; margin-top: 0.25rem;
    }
    .selected-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #e2e8f0;
    }
    .selected-user { display: flex; align-items: center; gap: 0.75rem; }
    .clear-btn {
      padding: 0.25rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; font-size: 0.75rem; font-weight: 500; color: #64748b;
      cursor: pointer; font-family: inherit;
    }
    .clear-btn:hover { background: #f1f5f9; color: #374151; }

    /* ── Mode toggle ─────────────────────────── */
    .mode-toggle { display: flex; gap: 0.5rem; }
    .mode-btn {
      flex: 1; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px;
      background: #fff; font-size: 0.8125rem; font-weight: 500; cursor: pointer;
      font-family: inherit; transition: all 0.15s; max-width: 200px;
    }
    .mode-btn.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .mode-btn.override.active { background: #d97706; border-color: #d97706; }

    .error-msg {
      background: #fef2f2; color: #dc2626; padding: 0.5rem 0.75rem;
      border-radius: 6px; font-size: 0.8125rem; border: 1px solid #fecaca;
      margin-bottom: 1rem;
    }
    .form-actions { display: flex; justify-content: flex-end; padding-top: 0.25rem; }
    .btn {
      padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; font-family: inherit; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Sessions table ──────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr:hover { background: #f8fafc; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #dbeafe; color: #1d4ed8;
    }
    .badge-override { background: #fef3c7; color: #92400e; }
    .status-badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #f1f5f9; color: #475569;
    }
    .status-badge[data-status="ACTIVE"] { background: #dcfce7; color: #166534; }
    .status-badge[data-status="PENDING_APPROVAL"] { background: #fef3c7; color: #92400e; }
    .status-badge[data-status="REJECTED"] { background: #fef2f2; color: #dc2626; }
    .status-badge[data-status="EXPIRED"] { background: #f1f5f9; color: #64748b; }
    .status-badge[data-status="ENDED"] { background: #f1f5f9; color: #64748b; }
    .actions { display: flex; gap: 0.375rem; }
    .action-btn {
      padding: 0.25rem 0.625rem; border: none; border-radius: 4px;
      font-size: 0.6875rem; font-weight: 600; cursor: pointer; font-family: inherit;
    }
    .action-btn.approve { background: #dcfce7; color: #166534; }
    .action-btn.approve:hover { background: #bbf7d0; }
    .action-btn.reject { background: #fef2f2; color: #dc2626; }
    .action-btn.reject:hover { background: #fecaca; }
    .action-btn.end { background: #fef3c7; color: #92400e; }
    .action-btn.end:hover { background: #fde68a; }

    /* ── Empty state ─────────────────────────── */
    .loading { color: #64748b; font-size: 0.8125rem; padding: 2rem; text-align: center; }
    .empty-state {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 3rem 2rem; text-align: center;
    }
    .empty-icon { font-size: 2rem; color: #cbd5e1; margin-bottom: 0.75rem; }
    .empty-title { margin: 0 0 0.25rem; font-size: 0.9375rem; font-weight: 600; color: #475569; }
    .empty-desc { margin: 0; font-size: 0.8125rem; color: #94a3b8; max-width: 360px; margin-inline: auto; }
  `],
})
export class ImpersonationSessionsComponent implements OnInit {
  private impersonationService = inject(ImpersonationService);
  private userService = inject(UserService);
  private tenantContext = inject(TenantContextService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);

  activeTab = signal<ActiveTab>('request');
  sessions = signal<ImpersonationSession[]>([]);
  sessionsLoading = signal(false);
  sessionCount = signal(0);
  private sessionsLoaded = false;

  // Request tab state
  userSearch = '';
  searchResults = signal<User[]>([]);
  searchLoading = signal(false);
  selectedUser = signal<User | null>(null);
  requestMode: ImpersonationMode = 'STANDARD';
  requestReason = '';
  requestPassword = '';
  requestSubmitting = signal(false);
  requestError = signal('');

  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    // Pre-fetch session count for the tab badge
    this.impersonationService.getActiveSessions(0, 1).subscribe({
      next: (result) => this.sessionCount.set(result.total),
      error: () => {},
    });
  }

  switchToSessions(): void {
    this.activeTab.set('sessions');
    if (!this.sessionsLoaded) {
      this.loadSessions();
      this.sessionsLoaded = true;
    }
  }

  searchUsers(): void {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    const term = this.userSearch.trim();
    if (term.length < 2) {
      this.searchResults.set([]);
      return;
    }
    this.searchTimeout = setTimeout(() => {
      if (!this.tenantContext.currentTenantId()) return;
      this.searchLoading.set(true);
      this.userService.listUsers(0, 10, term).subscribe({
        next: (res) => {
          this.searchResults.set(res.items);
          this.searchLoading.set(false);
        },
        error: () => {
          this.searchLoading.set(false);
        },
      });
    }, 300);
  }

  selectUser(user: User): void {
    this.selectedUser.set(user);
    this.searchResults.set([]);
    this.userSearch = user.display_name || user.email;
    this.requestError.set('');
  }

  clearSelection(): void {
    this.selectedUser.set(null);
    this.userSearch = '';
    this.searchResults.set([]);
    this.requestReason = '';
    this.requestPassword = '';
    this.requestMode = 'STANDARD';
    this.requestError.set('');
  }

  submitRequest(): void {
    const user = this.selectedUser();
    const tenantId = this.tenantContext.currentTenantId();
    if (!user || !tenantId) return;

    this.requestSubmitting.set(true);
    this.requestError.set('');

    this.impersonationService
      .requestImpersonation({
        target_user_id: user.id,
        tenant_id: tenantId,
        mode: this.requestMode,
        reason: this.requestReason,
        password: this.requestPassword,
      })
      .subscribe({
        next: (session) => {
          this.requestSubmitting.set(false);
          this.toastService.success(
            session.status === 'PENDING_APPROVAL'
              ? 'Impersonation request submitted for approval'
              : 'Impersonation session started',
          );
          this.clearSelection();
          this.sessionCount.update((c) => c + 1);
          this.sessionsLoaded = false;
        },
        error: (err) => {
          this.requestSubmitting.set(false);
          this.requestError.set(err.error?.detail?.error?.message || 'Request failed');
        },
      });
  }

  formatStatus(status: string): string {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // ── Sessions tab methods ───────────────────────

  loadSessions(): void {
    this.sessionsLoading.set(true);
    this.impersonationService.getActiveSessions().subscribe({
      next: (result) => {
        this.sessions.set(result.items);
        this.sessionCount.set(result.total);
        this.sessionsLoading.set(false);
      },
      error: () => {
        this.sessionsLoading.set(false);
        this.toastService.error('Failed to load sessions');
      },
    });
  }

  approve(session: ImpersonationSession): void {
    this.impersonationService
      .approveRequest(session.id, { decision: 'approve' })
      .subscribe({
        next: () => {
          this.toastService.success('Request approved');
          this.loadSessions();
        },
        error: (err) => {
          this.toastService.error(err.error?.detail?.error?.message || 'Approval failed');
        },
      });
  }

  async reject(session: ImpersonationSession): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Reject Request',
      message: 'Reject this impersonation request?',
      confirmLabel: 'Reject',
      variant: 'danger',
    });
    if (!ok) return;

    this.impersonationService
      .approveRequest(session.id, { decision: 'reject', reason: 'Rejected by admin' })
      .subscribe({
        next: () => {
          this.toastService.success('Request rejected');
          this.loadSessions();
        },
        error: (err) => {
          this.toastService.error(err.error?.detail?.error?.message || 'Rejection failed');
        },
      });
  }

  async end(session: ImpersonationSession): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'End Session',
      message: 'End this impersonation session?',
      confirmLabel: 'End Session',
      variant: 'danger',
    });
    if (!ok) return;

    this.impersonationService.endSession(session.id).subscribe({
      next: () => {
        this.toastService.success('Session ended');
        this.loadSessions();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to end session');
      },
    });
  }
}
