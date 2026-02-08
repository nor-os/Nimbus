/**
 * Overview: Authentication settings page with tabbed layout for identity providers and SCIM tokens.
 * Architecture: Feature component for IdP management under Settings > Authentication (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/identity-provider.service
 * Concepts: Identity providers, SSO, SCIM provisioning, tabbed layout, search filtering, token lifecycle
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { IdentityProviderService } from '@core/services/identity-provider.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { IdentityProvider, SCIMToken, SCIMTokenCreateResponse } from '@core/models/identity-provider.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { createTableSelection } from '@shared/utils/table-selection';

type SortColumn = 'name' | 'type' | 'status' | 'default' | 'created_at';
type SortDirection = 'asc' | 'desc';
type ActiveTab = 'providers' | 'scim';

@Component({
  selector: 'nimbus-idp-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, ReactiveFormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="auth-page">
        <div class="page-header">
          <h1>Authentication</h1>
        </div>

        <div class="tabs">
          <button
            class="tab"
            [class.tab-active]="activeTab() === 'providers'"
            (click)="activeTab.set('providers')"
          >Providers</button>
          <button
            class="tab"
            [class.tab-active]="activeTab() === 'scim'"
            (click)="switchToScim()"
          >SCIM Tokens</button>
        </div>

        <!-- ─── Providers Tab ─────────────────────────── -->
        @if (activeTab() === 'providers') {
          <div class="tab-content">
            <div class="tab-toolbar">
              <input
                type="text"
                [(ngModel)]="searchTerm"
                (ngModelChange)="onSearch()"
                placeholder="Search by name or type..."
                class="search-input"
              />
              <a routerLink="/settings/auth/create" class="btn btn-primary">Create Provider</a>
            </div>

            @if (idpSelection.selectedCount() > 0) {
              <div class="bulk-toolbar">
                <span class="bulk-count">{{ idpSelection.selectedCount() }} selected</span>
                <button class="btn btn-sm btn-sm-danger" (click)="bulkDeleteIdp()">Delete Selected</button>
                <button class="btn-link" (click)="idpSelection.clear()">Clear</button>
              </div>
            }

            @if (loadingIdp()) {
              <div class="loading">Loading identity providers...</div>
            } @else {
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th class="th-check">
                        <input
                          type="checkbox"
                          [checked]="idpSelection.allSelected()"
                          [indeterminate]="idpSelection.someSelected()"
                          (change)="idpSelection.toggleAll()"
                        />
                      </th>
                      <th class="sortable" (click)="onSort('name')">
                        Name <span class="sort-icon">{{ getSortIcon('name') }}</span>
                      </th>
                      <th class="sortable" (click)="onSort('type')">
                        Type <span class="sort-icon">{{ getSortIcon('type') }}</span>
                      </th>
                      <th class="sortable" (click)="onSort('status')">
                        Status <span class="sort-icon">{{ getSortIcon('status') }}</span>
                      </th>
                      <th class="sortable" (click)="onSort('default')">
                        Default <span class="sort-icon">{{ getSortIcon('default') }}</span>
                      </th>
                      <th class="sortable" (click)="onSort('created_at')">
                        Created <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
                      </th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (provider of displayedProviders(); track provider.id) {
                      <tr>
                        <td>
                          <input
                            type="checkbox"
                            [checked]="idpSelection.isSelected(provider.id)"
                            (change)="idpSelection.toggle(provider.id)"
                          />
                        </td>
                        <td class="name-cell">{{ provider.name }}</td>
                        <td>
                          <span class="badge" [class]="'badge-type-' + provider.idp_type">
                            {{ provider.idp_type | uppercase }}
                          </span>
                        </td>
                        <td>
                          <span class="badge" [class]="provider.is_enabled ? 'badge-enabled' : 'badge-disabled'">
                            {{ provider.is_enabled ? 'Enabled' : 'Disabled' }}
                          </span>
                        </td>
                        <td class="default-cell">
                          @if (provider.is_default) {
                            <span class="checkmark">&#10003;</span>
                          } @else {
                            <span class="dash">&mdash;</span>
                          }
                        </td>
                        <td>{{ provider.created_at | date: 'medium' }}</td>
                        <td class="actions">
                          <a [routerLink]="['/settings/auth', provider.id]" class="action-link" title="Edit provider settings">
                            <nimbus-icon name="gear" /> Settings
                          </a>
                          <a [routerLink]="['/settings/auth', provider.id, 'claim-mappings']" class="action-link" title="Edit claim mappings">
                            <nimbus-icon name="link" /> Claims
                          </a>
                          <button class="icon-btn icon-btn-danger" title="Delete" (click)="confirmDeleteIdp(provider)">
                            <nimbus-icon name="trash" />
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr>
                        <td colspan="7" class="empty-state">No identity providers configured</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }

            @if (idpError()) {
              <div class="error-banner">{{ idpError() }}</div>
            }
          </div>
        }

        <!-- ─── SCIM Tokens Tab ───────────────────────── -->
        @if (activeTab() === 'scim') {
          <div class="tab-content">
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

            @if (scimSelection.selectedCount() > 0) {
              <div class="bulk-toolbar">
                <span class="bulk-count">{{ scimSelection.selectedCount() }} selected</span>
                <button class="btn btn-sm btn-sm-danger" (click)="bulkRevokeScim()">Revoke Selected</button>
                <button class="btn-link" (click)="scimSelection.clear()">Clear</button>
              </div>
            }

            @if (loadingScim()) {
              <div class="loading">Loading SCIM tokens...</div>
            } @else {
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th class="th-check">
                        <input
                          type="checkbox"
                          [checked]="scimSelection.allSelected()"
                          [indeterminate]="scimSelection.someSelected()"
                          (change)="scimSelection.toggleAll()"
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
                    @for (token of scimTokens(); track token.id) {
                      <tr>
                        <td>
                          <input
                            type="checkbox"
                            [checked]="scimSelection.isSelected(token.id)"
                            (change)="scimSelection.toggle(token.id)"
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
                            <button class="icon-btn icon-btn-danger" title="Revoke" (click)="confirmRevokeScim(token)">
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
              <form [formGroup]="scimForm" (ngSubmit)="onCreateScimToken()" class="create-form">
                <div class="form-row">
                  <div class="form-group">
                    <label for="scim_description">Description</label>
                    <input id="scim_description" formControlName="description" class="form-input" placeholder="e.g. Azure AD SCIM integration" />
                  </div>
                  <div class="form-group form-group-sm">
                    <label for="scim_expires">Expires In (days)</label>
                    <input id="scim_expires" formControlName="expires_in_days" type="number" class="form-input" min="1" placeholder="Optional" />
                  </div>
                </div>

                @if (scimError()) {
                  <div class="form-error">{{ scimError() }}</div>
                }

                <div class="form-actions">
                  <button type="submit" class="btn btn-primary" [disabled]="scimSubmitting()">
                    {{ scimSubmitting() ? 'Creating...' : 'Create Token' }}
                  </button>
                </div>
              </form>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .auth-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.25rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    /* ── Tabs ───────────────────────────────────── */
    .tabs {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0;
      margin-bottom: 1.25rem;
    }
    .tab {
      padding: 0.625rem 1.25rem; font-size: 0.8125rem; font-weight: 500;
      color: #64748b; background: none; border: none; cursor: pointer;
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      font-family: inherit; transition: color 0.15s, border-color 0.15s;
    }
    .tab:hover { color: #1e293b; }
    .tab-active { color: #3b82f6; border-bottom-color: #3b82f6; }

    /* ── Tab Content ────────────────────────────── */
    .tab-content { animation: fadeIn 0.15s ease; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    .tab-toolbar {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }

    /* ── Shared ─────────────────────────────────── */
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; border-radius: 6px; text-decoration: none; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
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
    .table th.sortable { cursor: pointer; user-select: none; }
    .table th.sortable:hover { color: #3b82f6; }
    .sort-icon { font-size: 0.625rem; margin-left: 0.25rem; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-type-local { background: #f1f5f9; color: #475569; }
    .badge-type-oidc { background: #dbeafe; color: #1d4ed8; }
    .badge-type-saml { background: #f3e8ff; color: #7c3aed; }
    .badge-enabled { background: #dcfce7; color: #16a34a; }
    .badge-disabled { background: #fef2f2; color: #dc2626; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-revoked { background: #fef2f2; color: #dc2626; }
    .default-cell { text-align: center; }
    .checkmark { color: #16a34a; font-weight: 600; font-size: 0.875rem; }
    .dash { color: #94a3b8; }
    .actions { display: flex; gap: 0.5rem; align-items: center; }
    .action-link {
      display: inline-flex; align-items: center; gap: 0.25rem;
      padding: 0.25rem 0.5rem; border-radius: 4px;
      color: #64748b; font-size: 0.75rem; font-weight: 500;
      text-decoration: none; transition: background 0.15s, color 0.15s;
      white-space: nowrap;
    }
    .action-link:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .text-muted { color: #94a3b8; font-size: 0.8125rem; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .error-banner {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-top: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .bulk-toolbar {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem;
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 1rem;
    }
    .bulk-count { font-size: 0.8125rem; font-weight: 600; color: #1d4ed8; margin-right: 0.5rem; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; transition: background 0.15s; white-space: nowrap;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm-danger { color: #dc2626; border-color: #fecaca; }
    .btn-sm-danger:hover { background: #fef2f2; }
    .btn-link {
      color: #3b82f6; text-decoration: none; font-size: 0.8125rem; font-weight: 500;
      background: none; border: none; cursor: pointer; font-family: inherit; padding: 0;
    }
    .btn-link:hover { text-decoration: underline; }
    .th-check { width: 40px; }

    /* ── SCIM Token Reveal ──────────────────────── */
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

    /* ── SCIM Create Form ──────────────────────── */
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
  `],
})
export class IdpListComponent implements OnInit {
  private idpService = inject(IdentityProviderService);
  private tenantContext = inject(TenantContextService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private fb = inject(FormBuilder);

  activeTab = signal<ActiveTab>('providers');

  // ── Providers state ──────────────────────────
  providers = signal<IdentityProvider[]>([]);
  loadingIdp = signal(false);
  idpError = signal('');
  searchTerm = '';
  sortColumn = signal<SortColumn>('name');
  sortDirection = signal<SortDirection>('asc');

  displayedProviders = computed(() => {
    let items = this.providers();
    const term = this.searchTerm.toLowerCase().trim();
    if (term) {
      items = items.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.idp_type.toLowerCase().includes(term),
      );
    }
    const col = this.sortColumn();
    const dir = this.sortDirection();
    return [...items].sort((a, b) => {
      const valA = this.getIdpSortValue(a, col);
      const valB = this.getIdpSortValue(b, col);
      const cmp = valA.localeCompare(valB);
      return dir === 'asc' ? cmp : -cmp;
    });
  });

  idpSelection = createTableSelection(this.displayedProviders, (p) => p.id);

  // ── SCIM state ───────────────────────────────
  scimTokens = signal<SCIMToken[]>([]);
  loadingScim = signal(false);
  scimSubmitting = signal(false);
  scimError = signal('');
  newToken = signal('');
  copied = signal(false);
  private scimLoaded = false;

  scimSelection = createTableSelection(this.scimTokens, (t) => t.id);

  scimForm = this.fb.group({
    description: [''],
    expires_in_days: [null as number | null],
  });

  ngOnInit(): void {
    this.loadProviders();
  }

  // ── Tab switching ────────────────────────────
  switchToScim(): void {
    this.activeTab.set('scim');
    if (!this.scimLoaded) {
      this.loadScimTokens();
      this.scimLoaded = true;
    }
  }

  // ── Providers ────────────────────────────────
  onSearch(): void {
    this.providers.update((p) => [...p]);
  }

  onSort(column: SortColumn): void {
    if (this.sortColumn() === column) {
      this.sortDirection.update((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      this.sortColumn.set(column);
      this.sortDirection.set('asc');
    }
  }

  getSortIcon(column: SortColumn): string {
    if (this.sortColumn() !== column) return '\u2195';
    return this.sortDirection() === 'asc' ? '\u2191' : '\u2193';
  }

  loadProviders(): void {
    if (!this.tenantContext.currentTenantId()) {
      this.idpError.set('No tenant selected');
      return;
    }
    this.loadingIdp.set(true);
    this.idpError.set('');
    this.idpService.listProviders().subscribe({
      next: (providers) => {
        this.providers.set(providers);
        this.loadingIdp.set(false);
      },
      error: (err) => {
        this.idpError.set(err.error?.detail?.error?.message || 'Failed to load identity providers');
        this.loadingIdp.set(false);
      },
    });
  }

  async confirmDeleteIdp(provider: IdentityProvider): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Identity Provider',
      message: `Are you sure you want to delete "${provider.name}"? This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.idpService.deleteProvider(provider.id).subscribe({
      next: () => {
        this.toastService.success(`Provider "${provider.name}" deleted`);
        this.loadProviders();
      },
      error: (err) => {
        const msg = err.error?.detail?.error?.message || 'Failed to delete provider';
        this.idpError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async bulkDeleteIdp(): Promise<void> {
    const ids = [...this.idpSelection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Delete Identity Providers',
      message: `Delete ${ids.length} selected identity provider(s)?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.idpService.deleteProvider(id))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} identity provider(s) deleted`);
        this.idpSelection.clear();
        this.loadProviders();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete providers');
      },
    });
  }

  // ── SCIM Tokens ──────────────────────────────
  loadScimTokens(): void {
    if (!this.tenantContext.currentTenantId()) return;
    this.loadingScim.set(true);
    this.idpService.listSCIMTokens().subscribe({
      next: (tokens) => {
        this.scimTokens.set(tokens);
        this.loadingScim.set(false);
      },
      error: (err) => {
        this.scimError.set(err.error?.detail?.error?.message || 'Failed to load tokens');
        this.loadingScim.set(false);
      },
    });
  }

  onCreateScimToken(): void {
    this.scimSubmitting.set(true);
    this.scimError.set('');
    this.newToken.set('');
    this.copied.set(false);

    const values = this.scimForm.value;
    this.idpService.createSCIMToken({
      description: values.description || undefined,
      expires_in_days: values.expires_in_days ?? undefined,
    }).subscribe({
      next: (response: SCIMTokenCreateResponse) => {
        this.newToken.set(response.token);
        this.scimSubmitting.set(false);
        this.toastService.success('Token created');
        this.scimForm.reset({ description: '', expires_in_days: null });
        this.loadScimTokens();
      },
      error: (err) => {
        this.scimSubmitting.set(false);
        const msg = err.error?.detail?.error?.message || 'Failed to create token';
        this.scimError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async confirmRevokeScim(token: SCIMToken): Promise<void> {
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
        this.loadScimTokens();
      },
      error: (err) => {
        const msg = err.error?.detail?.error?.message || 'Failed to revoke token';
        this.scimError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async bulkRevokeScim(): Promise<void> {
    const ids = [...this.scimSelection.selectedIds()];
    const activeIds = ids.filter((id) => {
      const token = this.scimTokens().find((t) => t.id === id);
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
        this.scimSelection.clear();
        this.loadScimTokens();
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

  private getIdpSortValue(provider: IdentityProvider, col: SortColumn): string {
    switch (col) {
      case 'name':
        return provider.name.toLowerCase();
      case 'type':
        return provider.idp_type.toLowerCase();
      case 'status':
        return provider.is_enabled ? '1' : '0';
      case 'default':
        return provider.is_default ? '1' : '0';
      case 'created_at':
        return provider.created_at;
    }
  }
}
