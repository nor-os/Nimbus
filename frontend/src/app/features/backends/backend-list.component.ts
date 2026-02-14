/**
 * Overview: Cloud backend list — manage configured provider connections with status,
 *     credentials, and connectivity testing.
 * Architecture: Feature component for cloud backend management (Section 11)
 * Dependencies: @angular/core, @angular/router, @angular/forms, cloud-backend.service, semantic.service
 * Concepts: Lists CloudBackend instances (not SemanticProviders). Supports create, edit,
 *     test connectivity, delete. Provider type shown as badge.
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
import { Router } from '@angular/router';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { SemanticService } from '@core/services/semantic.service';
import { CloudBackend, CloudBackendInput } from '@shared/models/cloud-backend.model';
import { SemanticProvider } from '@shared/models/semantic.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-backend-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="backend-list-page">
        <div class="page-header">
          <h1>Backends</h1>
          <button
            *nimbusHasPermission="'cloud:backend:create'"
            class="btn btn-primary"
            (click)="showCreateForm()"
          >
            Add Backend
          </button>
        </div>

        <!-- Create form -->
        @if (formMode()) {
          <div class="form-card">
            <h2 class="form-title">New Backend</h2>
            <div class="form-row">
              <div class="form-group half">
                <label class="form-label">Provider Type *</label>
                <select
                  class="form-input"
                  [(ngModel)]="formProviderId"
                >
                  <option value="">Select a provider...</option>
                  @for (p of providers(); track p.id) {
                    <option [value]="p.id">{{ p.displayName }}</option>
                  }
                </select>
              </div>
              <div class="form-group half">
                <label class="form-label">Name *</label>
                <input
                  class="form-input"
                  [(ngModel)]="formName"
                  placeholder="e.g. Production AWS (us-east-1)"
                />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group half">
                <label class="form-label">Endpoint URL</label>
                <input
                  class="form-input"
                  [(ngModel)]="formEndpointUrl"
                  placeholder="https://... (for self-hosted providers)"
                />
              </div>
              <div class="form-group half">
                <label class="form-label">Status</label>
                <select class="form-input" [(ngModel)]="formStatus">
                  <option value="active">Active</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <textarea
                class="form-input textarea"
                [(ngModel)]="formDescription"
                placeholder="Optional description"
                rows="2"
              ></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-check-label">
                  <input
                    type="checkbox"
                    [(ngModel)]="formIsShared"
                    class="form-check"
                  />
                  Share with child tenants
                </label>
              </div>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" (click)="cancelForm()">Cancel</button>
              <button
                class="btn btn-primary"
                (click)="submitCreate()"
                [disabled]="!formProviderId || !formName.trim()"
              >
                Create
              </button>
            </div>
          </div>
        }

        <!-- Filters -->
        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchFilter"
            (ngModelChange)="applyFilters()"
            placeholder="Search backends..."
            class="filter-input"
          />
          <select
            [(ngModel)]="statusFilter"
            (ngModelChange)="applyFilters()"
            class="filter-select"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
            <option value="error">Error</option>
          </select>
          <select
            [(ngModel)]="providerFilter"
            (ngModelChange)="applyFilters()"
            class="filter-select"
          >
            <option value="">All Providers</option>
            @for (p of providers(); track p.id) {
              <option [value]="p.id">{{ p.displayName }}</option>
            }
          </select>
        </div>

        @if (loading()) {
          <div class="loading">Loading backends...</div>
        }

        @if (!loading() && filtered().length === 0 && !formMode()) {
          <div class="empty-state">No cloud backends configured yet. Add one to connect to your infrastructure.</div>
        }

        @if (!loading() && filtered().length > 0) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Endpoint</th>
                  <th>Credentials</th>
                  <th>IAM</th>
                  <th>Last Check</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                @for (b of filtered(); track b.id) {
                  <tr>
                    <td class="name-cell">
                      @if (b.providerIcon) {
                        <span class="provider-icon">{{ b.providerIcon }}</span>
                      }
                      <span>{{ b.name }}</span>
                      @if (b.isShared) {
                        <span class="badge badge-shared" title="Shared with child tenants">Shared</span>
                      }
                    </td>
                    <td>
                      <span class="badge badge-provider">{{ b.providerDisplayName }}</span>
                    </td>
                    <td>
                      <span class="badge" [class]="'badge-' + b.status">
                        {{ b.status }}
                      </span>
                    </td>
                    <td class="endpoint-cell">{{ b.endpointUrl || '\u2014' }}</td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-has-creds]="b.hasCredentials"
                        [class.badge-no-creds]="!b.hasCredentials"
                      >
                        {{ b.hasCredentials ? 'Configured' : 'Missing' }}
                      </span>
                    </td>
                    <td>{{ b.iamMappingCount }}</td>
                    <td class="check-cell">
                      @if (b.lastConnectivityStatus) {
                        <span
                          class="badge"
                          [class.badge-connected]="b.lastConnectivityStatus === 'connected'"
                          [class.badge-failed]="b.lastConnectivityStatus === 'failed'"
                        >
                          {{ b.lastConnectivityStatus }}
                        </span>
                      } @else {
                        <span class="text-muted">\u2014</span>
                      }
                    </td>
                    <td class="td-actions">
                      <button
                        *nimbusHasPermission="'cloud:backend:test'"
                        class="btn-icon"
                        title="Test Connectivity"
                        (click)="testConnectivity(b)"
                        [disabled]="testing() === b.id"
                      >&#9889;</button>
                      <button
                        *nimbusHasPermission="'cloud:backend:update'"
                        class="btn-icon"
                        title="Details"
                        (click)="goToDetail(b)"
                      >&#9998;</button>
                      <button
                        *nimbusHasPermission="'cloud:backend:delete'"
                        class="btn-icon btn-danger"
                        title="Delete"
                        (click)="deleteBackend(b)"
                      >&times;</button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .backend-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    /* -- Form --------------------------------------------------------- */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .form-title {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
      padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;
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
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }
    .form-check { margin-right: 0.5rem; }
    .form-check-label {
      font-size: 0.8125rem; color: #374151; cursor: pointer;
      display: flex; align-items: center;
    }

    /* -- Filters ------------------------------------------------------ */
    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
    }
    .filter-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 280px; font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; transition: border-color 0.15s;
    }
    .filter-input::placeholder { color: #94a3b8; }
    .filter-input:focus { border-color: #3b82f6; outline: none; }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; cursor: pointer; min-width: 160px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }

    /* -- Table -------------------------------------------------------- */
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
    .table tbody tr { color: #374151; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell {
      font-weight: 500; color: #1e293b;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .provider-icon { font-size: 1rem; }
    .endpoint-cell {
      max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      font-size: 0.75rem; color: #64748b;
    }
    .check-cell { white-space: nowrap; }
    .text-muted { color: #94a3b8; }
    .th-actions, .td-actions { width: 110px; text-align: right; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-active { background: #dcfce7; color: #166534; }
    .badge-disabled { background: #f1f5f9; color: #64748b; }
    .badge-error { background: #fef2f2; color: #dc2626; }
    .badge-provider { background: #dbeafe; color: #1d4ed8; }
    .badge-shared { background: #ede9fe; color: #6d28d9; font-size: 0.625rem; }
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
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-icon:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class BackendListComponent implements OnInit {
  private backendService = inject(CloudBackendService);
  private semanticService = inject(SemanticService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  backends = signal<CloudBackend[]>([]);
  filtered = signal<CloudBackend[]>([]);
  providers = signal<SemanticProvider[]>([]);
  loading = signal(false);
  formMode = signal(false);
  testing = signal<string | null>(null);

  searchFilter = '';
  statusFilter = '';
  providerFilter = '';

  // Form fields
  formProviderId = '';
  formName = '';
  formDescription = '';
  formEndpointUrl = '';
  formStatus = 'active';
  formIsShared = false;

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.semanticService.listProviders().subscribe({
      next: (list) => this.providers.set(list),
      error: () => {},
    });
    this.backendService.listBackends({ includeShared: true }).subscribe({
      next: (list) => {
        this.backends.set(list);
        this.applyFilters();
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load backends');
        this.loading.set(false);
      },
    });
  }

  applyFilters(): void {
    let items = this.backends();
    if (this.statusFilter) {
      items = items.filter((b) => b.status === this.statusFilter);
    }
    if (this.providerFilter) {
      items = items.filter((b) => b.providerId === this.providerFilter);
    }
    if (this.searchFilter.trim()) {
      const q = this.searchFilter.trim().toLowerCase();
      items = items.filter(
        (b) =>
          b.name.toLowerCase().includes(q) ||
          b.providerDisplayName.toLowerCase().includes(q) ||
          (b.description && b.description.toLowerCase().includes(q)) ||
          (b.endpointUrl && b.endpointUrl.toLowerCase().includes(q)),
      );
    }
    this.filtered.set(items);
  }

  showCreateForm(): void {
    this.resetForm();
    this.formMode.set(true);
  }

  cancelForm(): void {
    this.formMode.set(false);
    this.resetForm();
  }

  submitCreate(): void {
    const input: CloudBackendInput = {
      providerId: this.formProviderId,
      name: this.formName.trim(),
      description: this.formDescription.trim() || undefined,
      endpointUrl: this.formEndpointUrl.trim() || undefined,
      status: this.formStatus,
      isShared: this.formIsShared,
    };
    this.backendService.createBackend(input).subscribe({
      next: (created) => {
        this.backends.update((list) => [...list, created]);
        this.applyFilters();
        this.toastService.success(`Backend "${created.name}" created`);
        this.cancelForm();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create backend');
      },
    });
  }

  testConnectivity(b: CloudBackend): void {
    this.testing.set(b.id);
    this.backendService.testConnectivity(b.id).subscribe({
      next: (result) => {
        this.testing.set(null);
        if (result.success) {
          this.toastService.success(result.message);
        } else {
          this.toastService.error(result.message);
        }
        // Refresh to update status
        this.backendService.getBackend(b.id).subscribe({
          next: (updated) => {
            if (updated) {
              this.backends.update((list) =>
                list.map((x) => (x.id === b.id ? updated : x)),
              );
              this.applyFilters();
            }
          },
        });
      },
      error: (err) => {
        this.testing.set(null);
        this.toastService.error(err.message || 'Connectivity test failed');
      },
    });
  }

  deleteBackend(b: CloudBackend): void {
    this.backendService.deleteBackend(b.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.backends.update((list) => list.filter((x) => x.id !== b.id));
          this.applyFilters();
          this.toastService.success(`Backend "${b.name}" deleted`);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete backend');
      },
    });
  }

  goToDetail(b: CloudBackend): void {
    this.router.navigate(['/backends', b.id]);
  }

  private resetForm(): void {
    this.formProviderId = '';
    this.formName = '';
    this.formDescription = '';
    this.formEndpointUrl = '';
    this.formStatus = 'active';
    this.formIsShared = false;
  }
}
