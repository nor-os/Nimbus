/**
 * Overview: Cloud backend detail — tabbed view with Overview (edit fields), Credentials
 *     (dynamic form + test connection), and IAM Mappings (inline CRUD).
 * Architecture: Feature component for cloud backend detail/edit (Section 11)
 * Dependencies: @angular/core, @angular/router, @angular/forms, cloud-backend.service
 * Concepts: Credentials are write-only (set but never read back). Connectivity testing
 *     validates credentials against the provider. IAM mappings link Nimbus roles to cloud identities.
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import {
  CloudBackend,
  CloudBackendIAMMapping,
  CloudBackendIAMMappingInput,
  CloudBackendUpdateInput,
} from '@shared/models/cloud-backend.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

type TabKey = 'overview' | 'credentials' | 'iam';

@Component({
  selector: 'nimbus-backend-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="detail-page">
        @if (loading()) {
          <div class="loading">Loading backend...</div>
        }

        @if (!loading() && !backend()) {
          <div class="empty-state">Backend not found.</div>
        }

        @if (!loading() && backend(); as b) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <button class="btn-back" (click)="goBack()">&larr;</button>
              <div>
                <h1>{{ b.name }}</h1>
                <div class="header-meta">
                  <span class="badge badge-provider">{{ b.providerDisplayName }}</span>
                  <span class="badge" [class]="'badge-' + b.status">{{ b.status }}</span>
                  @if (b.isShared) {
                    <span class="badge badge-shared">Shared</span>
                  }
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button
                *nimbusHasPermission="'cloud:backend:test'"
                class="btn btn-secondary"
                (click)="testConnectivity()"
                [disabled]="testing()"
              >
                {{ testing() ? 'Testing...' : 'Test Connection' }}
              </button>
            </div>
          </div>

          <!-- Tabs -->
          <div class="tabs">
            <button
              class="tab" [class.active]="activeTab() === 'overview'"
              (click)="activeTab.set('overview')"
            >Overview</button>
            <button
              class="tab" [class.active]="activeTab() === 'credentials'"
              (click)="activeTab.set('credentials')"
            >Credentials</button>
            <button
              class="tab" [class.active]="activeTab() === 'iam'"
              (click)="loadIAMMappings(); activeTab.set('iam')"
            >IAM Mappings ({{ b.iamMappingCount }})</button>
          </div>

          <!-- Overview Tab -->
          @if (activeTab() === 'overview') {
            <div class="tab-content">
              <div class="form-card">
                <div class="form-row">
                  <div class="form-group half">
                    <label class="form-label">Name</label>
                    <input class="form-input" [(ngModel)]="editName" />
                  </div>
                  <div class="form-group half">
                    <label class="form-label">Status</label>
                    <select class="form-input" [(ngModel)]="editStatus">
                      <option value="active">Active</option>
                      <option value="disabled">Disabled</option>
                      <option value="error">Error</option>
                    </select>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">Description</label>
                  <textarea
                    class="form-input textarea"
                    [(ngModel)]="editDescription"
                    rows="2"
                  ></textarea>
                </div>
                <div class="form-row">
                  <div class="form-group half">
                    <label class="form-label">Endpoint URL</label>
                    <input class="form-input" [(ngModel)]="editEndpointUrl" placeholder="https://..." />
                  </div>
                  <div class="form-group half">
                    <label class="form-label">Scope Config (JSON)</label>
                    <textarea
                      class="form-input textarea mono"
                      [(ngModel)]="editScopeConfig"
                      rows="3"
                      placeholder='{"regions": ["us-east-1"]}'
                    ></textarea>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-check-label">
                    <input type="checkbox" [(ngModel)]="editIsShared" class="form-check" />
                    Share with child tenants
                  </label>
                </div>
                <div class="form-actions">
                  <button
                    *nimbusHasPermission="'cloud:backend:update'"
                    class="btn btn-primary"
                    (click)="saveOverview()"
                    [disabled]="saving()"
                  >
                    {{ saving() ? 'Saving...' : 'Save Changes' }}
                  </button>
                </div>

                <!-- Connectivity info -->
                @if (b.lastConnectivityCheck) {
                  <div class="connectivity-info">
                    <h3>Last Connectivity Check</h3>
                    <div class="info-row">
                      <span class="info-label">Status:</span>
                      <span class="badge"
                        [class.badge-connected]="b.lastConnectivityStatus === 'connected'"
                        [class.badge-failed]="b.lastConnectivityStatus === 'failed'"
                      >{{ b.lastConnectivityStatus }}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Checked:</span>
                      <span>{{ b.lastConnectivityCheck }}</span>
                    </div>
                    @if (b.lastConnectivityError) {
                      <div class="info-row error-text">
                        <span class="info-label">Error:</span>
                        <span>{{ b.lastConnectivityError }}</span>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }

          <!-- Credentials Tab -->
          @if (activeTab() === 'credentials') {
            <div class="tab-content">
              <div class="form-card">
                <div class="cred-status">
                  <span class="info-label">Current status:</span>
                  <span class="badge" [class.badge-has-creds]="b.hasCredentials" [class.badge-no-creds]="!b.hasCredentials">
                    {{ b.hasCredentials ? 'Credentials configured' : 'No credentials' }}
                  </span>
                </div>
                <p class="cred-notice">
                  Credentials are encrypted at rest and never returned by the API. Enter new credentials below to set or replace them.
                </p>
                <div class="form-group">
                  <label class="form-label">Credentials (JSON)</label>
                  <textarea
                    class="form-input textarea mono"
                    [(ngModel)]="credentialsJson"
                    rows="8"
                    placeholder='{ "auth_type": "api_token", "cluster_url": "https://...", "token_id": "...", "secret": "..." }'
                  ></textarea>
                </div>
                <div class="form-actions">
                  <button class="btn btn-secondary" (click)="loadCredentialSchema()">
                    View Schema for {{ b.providerName }}
                  </button>
                  <button
                    *nimbusHasPermission="'cloud:backend:update'"
                    class="btn btn-primary"
                    (click)="saveCredentials()"
                    [disabled]="saving() || !credentialsJson.trim()"
                  >
                    {{ saving() ? 'Saving...' : 'Save Credentials' }}
                  </button>
                </div>

                @if (credentialSchema()) {
                  <div class="schema-preview">
                    <h3>Credential Schema: {{ b.providerName }}</h3>
                    <pre>{{ credentialSchema() | json }}</pre>
                  </div>
                }
              </div>
            </div>
          }

          <!-- IAM Mappings Tab -->
          @if (activeTab() === 'iam') {
            <div class="tab-content">
              <div class="form-card">
                <div class="section-header">
                  <h3>IAM Mappings</h3>
                  <button
                    *nimbusHasPermission="'cloud:backend:manage_iam'"
                    class="btn btn-primary btn-sm"
                    (click)="showIAMForm.set(true)"
                  >
                    Add Mapping
                  </button>
                </div>

                @if (showIAMForm()) {
                  <div class="iam-form">
                    <div class="form-row">
                      <div class="form-group half">
                        <label class="form-label">Role ID</label>
                        <input class="form-input" [(ngModel)]="iamRoleId" placeholder="UUID of Nimbus role" />
                      </div>
                      <div class="form-group half">
                        <label class="form-label">Description</label>
                        <input class="form-input" [(ngModel)]="iamDescription" />
                      </div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Cloud Identity (JSON)</label>
                      <textarea
                        class="form-input textarea mono"
                        [(ngModel)]="iamCloudIdentity"
                        rows="3"
                        placeholder='{ "role_arn": "arn:aws:iam::123:role/NimbusAdmin" }'
                      ></textarea>
                    </div>
                    <div class="form-actions">
                      <button class="btn btn-secondary btn-sm" (click)="showIAMForm.set(false)">Cancel</button>
                      <button
                        class="btn btn-primary btn-sm"
                        (click)="createIAMMapping()"
                        [disabled]="!iamRoleId.trim() || !iamCloudIdentity.trim()"
                      >Create</button>
                    </div>
                  </div>
                }

                @if (iamMappings().length === 0 && !showIAMForm()) {
                  <div class="empty-state-sm">No IAM mappings configured.</div>
                }

                @if (iamMappings().length > 0) {
                  <div class="table-container">
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Role</th>
                          <th>Cloud Identity</th>
                          <th>Active</th>
                          <th class="th-actions"></th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (m of iamMappings(); track m.id) {
                          <tr>
                            <td class="name-cell">{{ m.roleName }}</td>
                            <td class="mono-cell"><pre class="identity-json">{{ m.cloudIdentity | json }}</pre></td>
                            <td>
                              <span class="badge" [class.badge-active]="m.isActive" [class.badge-disabled]="!m.isActive">
                                {{ m.isActive ? 'Active' : 'Inactive' }}
                              </span>
                            </td>
                            <td class="td-actions">
                              <button
                                *nimbusHasPermission="'cloud:backend:manage_iam'"
                                class="btn-icon btn-danger"
                                title="Delete"
                                (click)="deleteIAMMapping(m)"
                              >&times;</button>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }
              </div>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .detail-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 1rem; }
    .header-left h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-meta { display: flex; gap: 0.5rem; margin-top: 0.25rem; }
    .header-actions { display: flex; gap: 0.5rem; }
    .btn-back {
      background: none; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 0.375rem 0.75rem; cursor: pointer; font-size: 1rem; color: #64748b;
    }
    .btn-back:hover { background: #f8fafc; }

    /* -- Tabs --------------------------------------------------------- */
    .tabs {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem;
    }
    .tab {
      padding: 0.75rem 1.25rem; font-size: 0.8125rem; font-weight: 500;
      color: #64748b; background: none; border: none; cursor: pointer;
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      font-family: inherit; transition: color 0.15s;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { animation: fadeIn 0.15s ease-in; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    /* -- Form card ---------------------------------------------------- */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1rem; }
    .form-label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .textarea { resize: vertical; min-height: 2.5rem; }
    .mono { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.75rem; }
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }
    .form-check { margin-right: 0.5rem; }
    .form-check-label {
      font-size: 0.8125rem; color: #374151; cursor: pointer;
      display: flex; align-items: center;
    }

    /* -- Connectivity info -------------------------------------------- */
    .connectivity-info {
      margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    .connectivity-info h3 {
      font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem;
    }
    .info-row { font-size: 0.8125rem; color: #374151; margin-bottom: 0.375rem; }
    .info-label { font-weight: 600; margin-right: 0.5rem; color: #64748b; }
    .error-text { color: #dc2626; }

    /* -- Credential tab ----------------------------------------------- */
    .cred-status { margin-bottom: 0.75rem; }
    .cred-notice {
      font-size: 0.8125rem; color: #64748b; margin-bottom: 1rem;
      padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
    }
    .schema-preview {
      margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    .schema-preview h3 {
      font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 0.5rem;
    }
    .schema-preview pre {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1rem; font-size: 0.75rem; overflow-x: auto; color: #374151;
    }

    /* -- IAM tab ------------------------------------------------------ */
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-header h3 {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0;
    }
    .iam-form {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1rem; margin-bottom: 1rem;
    }
    .identity-json {
      margin: 0; font-size: 0.6875rem; white-space: pre-wrap;
      max-width: 350px; overflow: hidden;
    }
    .mono-cell { font-family: monospace; }
    .empty-state-sm {
      padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* -- Table -------------------------------------------------------- */
    .table-container {
      overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 6px; margin-top: 1rem;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr { color: #374151; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .th-actions, .td-actions { width: 60px; text-align: right; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-active { background: #dcfce7; color: #166534; }
    .badge-disabled { background: #f1f5f9; color: #64748b; }
    .badge-error { background: #fef2f2; color: #dc2626; }
    .badge-provider { background: #dbeafe; color: #1d4ed8; }
    .badge-shared { background: #ede9fe; color: #6d28d9; }
    .badge-has-creds { background: #dcfce7; color: #166534; }
    .badge-no-creds { background: #fef3c7; color: #92400e; }
    .badge-connected { background: #dcfce7; color: #166534; }
    .badge-failed { background: #fef2f2; color: #dc2626; }

    /* -- States ------------------------------------------------------- */
    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Buttons ------------------------------------------------------ */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      border: none;
    }
    .btn-sm { font-size: 0.75rem; padding: 0.375rem 0.75rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class BackendDetailComponent implements OnInit {
  private backendService = inject(CloudBackendService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  backend = signal<CloudBackend | null>(null);
  iamMappings = signal<CloudBackendIAMMapping[]>([]);
  loading = signal(false);
  saving = signal(false);
  testing = signal(false);
  activeTab = signal<TabKey>('overview');
  credentialSchema = signal<Record<string, unknown> | null>(null);
  showIAMForm = signal(false);

  // Overview edit fields
  editName = '';
  editDescription = '';
  editEndpointUrl = '';
  editStatus = 'active';
  editScopeConfig = '';
  editIsShared = false;

  // Credentials
  credentialsJson = '';

  // IAM form
  iamRoleId = '';
  iamDescription = '';
  iamCloudIdentity = '';

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadBackend(id);
    }
  }

  loadBackend(id: string): void {
    this.loading.set(true);
    this.backendService.getBackend(id).subscribe({
      next: (b) => {
        this.backend.set(b);
        if (b) {
          this.editName = b.name;
          this.editDescription = b.description || '';
          this.editEndpointUrl = b.endpointUrl || '';
          this.editStatus = b.status;
          this.editScopeConfig = b.scopeConfig ? JSON.stringify(b.scopeConfig, null, 2) : '';
          this.editIsShared = b.isShared;
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load backend');
        this.loading.set(false);
      },
    });
  }

  saveOverview(): void {
    const b = this.backend();
    if (!b) return;

    let scopeConfig: Record<string, unknown> | null = null;
    if (this.editScopeConfig.trim()) {
      try {
        scopeConfig = JSON.parse(this.editScopeConfig);
      } catch {
        this.toastService.error('Invalid JSON in Scope Config');
        return;
      }
    }

    const input: CloudBackendUpdateInput = {
      name: this.editName.trim(),
      description: this.editDescription.trim() || null,
      endpointUrl: this.editEndpointUrl.trim() || null,
      status: this.editStatus,
      scopeConfig,
      isShared: this.editIsShared,
    };

    this.saving.set(true);
    this.backendService.updateBackend(b.id, input).subscribe({
      next: (updated) => {
        this.saving.set(false);
        if (updated) {
          this.backend.set(updated);
          this.toastService.success('Backend updated');
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.message || 'Failed to update backend');
      },
    });
  }

  saveCredentials(): void {
    const b = this.backend();
    if (!b) return;

    let credentials: Record<string, unknown>;
    try {
      credentials = JSON.parse(this.credentialsJson);
    } catch {
      this.toastService.error('Invalid JSON in credentials');
      return;
    }

    this.saving.set(true);
    this.backendService.updateBackend(b.id, { credentials }).subscribe({
      next: (updated) => {
        this.saving.set(false);
        if (updated) {
          this.backend.set(updated);
          this.credentialsJson = '';
          this.toastService.success('Credentials saved (encrypted)');
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.message || 'Failed to save credentials');
      },
    });
  }

  testConnectivity(): void {
    const b = this.backend();
    if (!b) return;

    this.testing.set(true);
    this.backendService.testConnectivity(b.id).subscribe({
      next: (result) => {
        this.testing.set(false);
        if (result.success) {
          this.toastService.success(result.message);
        } else {
          this.toastService.error(result.message);
        }
        // Refresh backend to get updated connectivity fields
        this.loadBackend(b.id);
      },
      error: (err) => {
        this.testing.set(false);
        this.toastService.error(err.message || 'Connectivity test failed');
      },
    });
  }

  loadCredentialSchema(): void {
    const b = this.backend();
    if (!b) return;
    this.backendService.getCredentialSchema(b.providerName).subscribe({
      next: (schema) => this.credentialSchema.set(schema),
      error: () => this.toastService.error('Failed to load credential schema'),
    });
  }

  // -- IAM Mappings --------------------------------------------------------

  loadIAMMappings(): void {
    const b = this.backend();
    if (!b) return;
    this.backendService.listIAMMappings(b.id).subscribe({
      next: (mappings) => this.iamMappings.set(mappings),
      error: () => this.toastService.error('Failed to load IAM mappings'),
    });
  }

  createIAMMapping(): void {
    const b = this.backend();
    if (!b) return;

    let cloudIdentity: Record<string, unknown>;
    try {
      cloudIdentity = JSON.parse(this.iamCloudIdentity);
    } catch {
      this.toastService.error('Invalid JSON in Cloud Identity');
      return;
    }

    const input: CloudBackendIAMMappingInput = {
      roleId: this.iamRoleId.trim(),
      cloudIdentity,
      description: this.iamDescription.trim() || undefined,
    };

    this.backendService.createIAMMapping(b.id, input).subscribe({
      next: (mapping) => {
        if (mapping) {
          this.iamMappings.update((list) => [...list, mapping]);
          this.iamRoleId = '';
          this.iamDescription = '';
          this.iamCloudIdentity = '';
          this.showIAMForm.set(false);
          this.toastService.success('IAM mapping created');
          // Update backend to reflect new count
          this.loadBackend(b.id);
        }
      },
      error: (err) => this.toastService.error(err.message || 'Failed to create IAM mapping'),
    });
  }

  deleteIAMMapping(m: CloudBackendIAMMapping): void {
    const b = this.backend();
    if (!b) return;

    this.backendService.deleteIAMMapping(b.id, m.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.iamMappings.update((list) => list.filter((x) => x.id !== m.id));
          this.toastService.success('IAM mapping deleted');
          this.loadBackend(b.id);
        }
      },
      error: (err) => this.toastService.error(err.message || 'Failed to delete IAM mapping'),
    });
  }

  goBack(): void {
    this.router.navigate(['/backends']);
  }
}
