/**
 * Overview: SCIM token management page with token creation, display, copy, and revocation.
 * Architecture: Feature component for SCIM provisioning token lifecycle (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/identity-provider.service
 * Concepts: SCIM provisioning, API tokens, secure token display, token lifecycle
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { IdentityProviderService } from '@core/services/identity-provider.service';
import { SCIMToken, SCIMTokenCreateResponse } from '@core/models/identity-provider.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { createTableSelection } from '@shared/utils/table-selection';

@Component({
  selector: 'nimbus-scim-tokens',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="scim-tokens-page">
        <div class="page-header">
          <h1>SCIM Tokens</h1>
        </div>

        @if (newToken()) {
          <div class="token-reveal">
            <div class="token-reveal-header">
              <strong>New Token Created</strong>
              <span class="token-reveal-hint">Copy this token now. It will not be shown again.</span>
            </div>
            <div class="token-value-row">
              <code class="token-value">{{ newToken() }}</code>
              <button class="btn btn-sm" (click)="copyToken()">
                {{ copied() ? 'Copied!' : 'Copy' }}
              </button>
            </div>
            <button class="icon-btn" title="Dismiss" (click)="dismissToken()">
              <nimbus-icon name="x" />
            </button>
          </div>
        }

        @if (selection.selectedCount() > 0) {
          <div class="bulk-toolbar">
            <span class="bulk-count">{{ selection.selectedCount() }} selected</span>
            <button class="btn btn-sm btn-sm-danger" (click)="bulkRevoke()">Revoke Selected</button>
            <button class="btn-link-toolbar" (click)="selection.clear()">Clear</button>
          </div>
        }

        @if (loading()) {
          <div class="loading">Loading SCIM tokens...</div>
        } @else {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th class="th-check">
                    <input
                      type="checkbox"
                      [checked]="selection.allSelected()"
                      [indeterminate]="selection.someSelected()"
                      (change)="selection.toggleAll()"
                    />
                  </th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Expires At</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (token of tokens(); track token.id) {
                  <tr>
                    <td>
                      <input
                        type="checkbox"
                        [checked]="selection.isSelected(token.id)"
                        (change)="selection.toggle(token.id)"
                      />
                    </td>
                    <td>{{ token.description || '\u2014' }}</td>
                    <td>
                      <span class="badge" [class]="token.is_active ? 'badge-active' : 'badge-revoked'">
                        {{ token.is_active ? 'Active' : 'Revoked' }}
                      </span>
                    </td>
                    <td>{{ token.expires_at ? (token.expires_at | date: 'medium') : 'Never' }}</td>
                    <td>{{ token.created_at | date: 'medium' }}</td>
                    <td class="actions">
                      @if (token.is_active) {
                        <button class="icon-btn icon-btn-danger" title="Revoke" (click)="confirmRevoke(token)">
                          <nimbus-icon name="shield-x" />
                        </button>
                      } @else {
                        <span class="text-muted">Revoked</span>
                      }
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="empty-state">No SCIM tokens created</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <div class="create-section">
          <h2>Create Token</h2>
          <form [formGroup]="form" (ngSubmit)="onCreate()" class="create-form">
            <div class="form-row">
              <div class="form-group">
                <label for="description">Description</label>
                <input id="description" formControlName="description" class="form-input" placeholder="e.g. Azure AD SCIM integration" />
              </div>

              <div class="form-group form-group-sm">
                <label for="expires_in_days">Expires In (days)</label>
                <input id="expires_in_days" formControlName="expires_in_days" type="number" class="form-input" min="1" placeholder="Optional" />
              </div>
            </div>

            @if (errorMessage()) {
              <div class="form-error">{{ errorMessage() }}</div>
            }

            <div class="form-actions">
              <button type="submit" class="btn btn-primary" [disabled]="submitting()">
                {{ submitting() ? 'Creating...' : 'Create Token' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .scim-tokens-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .token-reveal {
      background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1.5rem;
    }
    .token-reveal-header { margin-bottom: 0.75rem; }
    .token-reveal-header strong { display: block; color: #92400e; font-size: 0.875rem; margin-bottom: 0.25rem; }
    .token-reveal-hint { font-size: 0.75rem; color: #a16207; }
    .token-value-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }
    .token-value {
      flex: 1; padding: 0.5rem 0.75rem; background: #fef3c7; border: 1px solid #fde68a;
      border-radius: 6px; font-family: 'SF Mono', 'Consolas', 'Liberation Mono', monospace;
      font-size: 0.75rem; color: #78350f; word-break: break-all; user-select: all;
    }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; transition: background 0.15s; white-space: nowrap;
    }
    .btn-sm:hover { background: #f8fafc; }
    .loading { color: #64748b; font-size: 0.8125rem; padding: 2rem; text-align: center; }
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
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
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-revoked { background: #fef2f2; color: #dc2626; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .text-muted { color: #94a3b8; font-size: 0.8125rem; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .create-section {
      margin-top: 1.5rem; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem;
    }
    .create-section h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b;
      margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .form-row { display: flex; gap: 1rem; margin-bottom: 1rem; }
    .form-row .form-group { flex: 1; }
    .form-group { margin-bottom: 0; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-group-sm { flex: 0 0 160px !important; }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem;
      border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .bulk-toolbar {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem;
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 1rem;
    }
    .bulk-count { font-size: 0.8125rem; font-weight: 600; color: #1d4ed8; margin-right: 0.5rem; }
    .btn-sm-danger { color: #dc2626; border-color: #fecaca; }
    .btn-sm-danger:hover { background: #fef2f2; }
    .btn-link-toolbar { color: #3b82f6; text-decoration: none; font-size: 0.8125rem; font-weight: 500; background: none; border: none; cursor: pointer; font-family: inherit; padding: 0; }
    .btn-link-toolbar:hover { text-decoration: underline; }
    .th-check { width: 40px; }
  `],
})
export class ScimTokensComponent implements OnInit {
  private fb = inject(FormBuilder);
  private idpService = inject(IdentityProviderService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  tokens = signal<SCIMToken[]>([]);
  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');
  newToken = signal('');
  copied = signal(false);

  selection = createTableSelection(this.tokens, (t) => t.id);

  form = this.fb.group({
    description: [''],
    expires_in_days: [null as number | null],
  });

  ngOnInit(): void {
    this.loadTokens();
  }

  onCreate(): void {
    this.submitting.set(true);
    this.errorMessage.set('');
    this.newToken.set('');
    this.copied.set(false);

    const values = this.form.value;
    this.idpService.createSCIMToken({
      description: values.description || undefined,
      expires_in_days: values.expires_in_days ?? undefined,
    }).subscribe({
      next: (response: SCIMTokenCreateResponse) => {
        this.newToken.set(response.token);
        this.submitting.set(false);
        this.toastService.success('Token created');
        this.form.reset({ description: '', expires_in_days: null });
        this.loadTokens();
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.error?.detail?.error?.message || 'Failed to create token';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async confirmRevoke(token: SCIMToken): Promise<void> {
    const desc = token.description || token.id;
    const ok = await this.confirmService.confirm({
      title: 'Revoke Token',
      message: `Revoke token "${desc}"? This cannot be undone.`,
      confirmLabel: 'Revoke',
      variant: 'danger',
    });
    if (!ok) return;
    this.idpService.revokeSCIMToken(token.id).subscribe({
      next: () => {
        this.toastService.success('Token revoked');
        this.loadTokens();
      },
      error: (err) => {
        const msg = err.error?.detail?.error?.message || 'Failed to revoke token';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async bulkRevoke(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const activeIds = ids.filter((id) => {
      const token = this.tokens().find((t) => t.id === id);
      return token && token.is_active;
    });
    if (activeIds.length === 0) {
      this.toastService.error('No active tokens selected');
      return;
    }
    const ok = await this.confirmService.confirm({
      title: 'Revoke Tokens',
      message: `Revoke ${activeIds.length} active token(s)?` + (activeIds.length < ids.length ? ` (${ids.length - activeIds.length} already revoked will be skipped)` : ''),
      confirmLabel: 'Revoke',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(activeIds.map((id) => this.idpService.revokeSCIMToken(id))).subscribe({
      next: () => {
        this.toastService.success(`${activeIds.length} token(s) revoked`);
        this.selection.clear();
        this.loadTokens();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to revoke tokens');
      },
    });
  }

  copyToken(): void {
    const token = this.newToken();
    if (!token) return;

    navigator.clipboard.writeText(token).then(() => {
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    });
  }

  dismissToken(): void {
    this.newToken.set('');
    this.copied.set(false);
  }

  loadTokens(): void {
    this.loading.set(true);
    this.idpService.listSCIMTokens().subscribe({
      next: (tokens) => {
        this.tokens.set(tokens);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(err.error?.detail?.error?.message || 'Failed to load tokens');
        this.loading.set(false);
      },
    });
  }
}
