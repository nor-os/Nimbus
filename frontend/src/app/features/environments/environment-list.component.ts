/**
 * Overview: Tenant-facing environment list with status filters, provider column, config indicators, and create form.
 * Architecture: Feature component for environment management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common, @angular/forms, landing-zone.service
 * Concepts: Environment listing, status filtering, config completion indicators, inline create form, light theme
 */
import { Component, OnInit, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { TenantEnvironment } from '@shared/models/landing-zone.model';
import { ToastService } from '@shared/services/toast.service';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';

type StatusFilter = 'ALL' | 'PLANNED' | 'ACTIVE' | 'SUSPENDED';

@Component({
  selector: 'nimbus-environment-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Environments</h1>
            <p class="page-subtitle">Manage tenant environments linked to landing zones</p>
          </div>
          <div class="header-actions">
            <button
              *nimbusHasPermission="'landingzone:environment:create'"
              class="btn btn-primary"
              (click)="showCreate.set(!showCreate())"
            >{{ showCreate() ? 'Cancel' : '+ Create Environment' }}</button>
          </div>
        </div>

        <!-- Create form -->
        @if (showCreate()) {
          <div class="create-form-card">
            <h3 class="form-title">Create Environment</h3>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Name</label>
                <input type="text" class="form-input" [(ngModel)]="createForm.name" placeholder="e.g. production" />
              </div>
              <div class="form-group">
                <label class="form-label">Display Name</label>
                <input type="text" class="form-input" [(ngModel)]="createForm.displayName" placeholder="e.g. Production" />
              </div>
              <div class="form-group">
                <label class="form-label">Description</label>
                <input type="text" class="form-input" [(ngModel)]="createForm.description" placeholder="Optional description" />
              </div>
            </div>
            <div class="form-actions">
              <button class="btn btn-primary" (click)="onCreate()" [disabled]="!createForm.name || !createForm.displayName">Create</button>
              <button class="btn btn-outline" (click)="showCreate.set(false)">Cancel</button>
            </div>
          </div>
        }

        <!-- Status filter tabs -->
        <div class="filter-tabs">
          @for (f of statusFilters; track f.value) {
            <button
              class="filter-tab"
              [class.active]="statusFilter() === f.value"
              (click)="statusFilter.set(f.value)"
            >
              {{ f.label }}
              <span class="filter-count">{{ getStatusCount(f.value) }}</span>
            </button>
          }
        </div>

        <!-- Table -->
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Provider</th>
                <th>Landing Zone</th>
                <th>Status</th>
                <th>Config</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (env of filteredEnvironments(); track env.id) {
                <tr>
                  <td>
                    <a [routerLink]="['/environments', env.id]" class="name-link">{{ env.displayName }}</a>
                    <div class="name-sub">{{ env.name }}</div>
                  </td>
                  <td>
                    <span class="provider-name">{{ env.providerName || '—' }}</span>
                  </td>
                  <td class="lz-id">{{ env.landingZoneId.substring(0, 8) || '—' }}</td>
                  <td>
                    <span class="status-badge" [class]="'badge-' + env.status.toLowerCase()">
                      {{ env.status }}
                    </span>
                  </td>
                  <td>
                    <div class="config-indicators">
                      <span class="config-dot" [class.configured]="hasConfig(env.networkConfig)" title="Network">N</span>
                      <span class="config-dot" [class.configured]="hasConfig(env.iamConfig)" title="IAM">I</span>
                      <span class="config-dot" [class.configured]="hasConfig(env.securityConfig)" title="Security">S</span>
                      <span class="config-dot" [class.configured]="hasConfig(env.monitoringConfig)" title="Monitoring">M</span>
                    </div>
                  </td>
                  <td>{{ env.createdAt | date:'short' }}</td>
                  <td>
                    <div class="action-btns">
                      <a [routerLink]="['/environments', env.id]" class="action-btn">View</a>
                    </div>
                  </td>
                </tr>
              }
              @if (filteredEnvironments().length === 0 && !loading()) {
                <tr>
                  <td colspan="7" class="empty-cell">
                    @if (statusFilter() !== 'ALL') {
                      No {{ statusFilter().toLowerCase() }} environments found.
                    } @else {
                      No environments found. Create one to get started.
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .header-actions { display: flex; gap: 8px; }
    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
      cursor: pointer; text-decoration: none; border: none; display: inline-flex;
      align-items: center; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }

    .create-form-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .form-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 16px; }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    .form-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    .form-input {
      padding: 8px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      outline: none;
      font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; }
    .form-actions { display: flex; gap: 8px; margin-top: 16px; }

    /* Status filter tabs */
    .filter-tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid #e2e8f0;
      margin-bottom: 16px;
    }
    .filter-tab {
      padding: 8px 14px;
      font-size: 0.8125rem;
      font-weight: 500;
      color: #64748b;
      background: none;
      border: none;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      font-family: inherit;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: color 0.15s;
    }
    .filter-tab:hover { color: #1e293b; }
    .filter-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .filter-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 20px;
      height: 18px;
      padding: 0 5px;
      border-radius: 9px;
      font-size: 0.6875rem;
      font-weight: 600;
      background: #f1f5f9;
      color: #64748b;
    }
    .filter-tab.active .filter-count { background: #dbeafe; color: #3b82f6; }

    .table-container {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .table { width: 100%; border-collapse: collapse; }
    .table th {
      padding: 10px 16px;
      text-align: left;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
      border-bottom: 1px solid #e2e8f0;
      background: #fafbfc;
    }
    .table td {
      padding: 12px 16px;
      font-size: 0.8125rem;
      color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .table tr:last-child td { border-bottom: none; }
    .table tr:hover td { background: #fafbfc; }
    .name-link { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .name-link:hover { text-decoration: underline; }
    .name-sub { font-size: 0.6875rem; color: #94a3b8; margin-top: 2px; }
    .provider-name { font-size: 0.8125rem; color: #475569; font-weight: 500; }
    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-planned { background: #fef3c7; color: #92400e; }
    .badge-provisioning { background: #dbeafe; color: #1e40af; }
    .badge-active { background: #d1fae5; color: #065f46; }
    .badge-suspended { background: #fee2e2; color: #991b1b; }
    .badge-decommissioning { background: #fef3c7; color: #92400e; }
    .badge-decommissioned { background: #f1f5f9; color: #64748b; }

    /* Config completion indicators */
    .config-indicators { display: flex; gap: 4px; }
    .config-dot {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      font-size: 0.625rem;
      font-weight: 700;
      background: #f1f5f9;
      color: #94a3b8;
      border: 1px solid #e2e8f0;
    }
    .config-dot.configured {
      background: #d1fae5;
      color: #065f46;
      border-color: #a7f3d0;
    }

    .action-btns { display: flex; gap: 8px; }
    .action-btn {
      padding: 4px 8px;
      border: none;
      background: none;
      color: #3b82f6;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      font-family: inherit;
      text-decoration: none;
    }
    .action-btn:hover { text-decoration: underline; }
    .empty-cell {
      text-align: center;
      padding: 32px 16px !important;
      color: #94a3b8;
    }
  `],
})
export class EnvironmentListComponent implements OnInit {
  private lzService = inject(LandingZoneService);
  private toast = inject(ToastService);

  environments = signal<TenantEnvironment[]>([]);
  loading = signal(false);
  showCreate = signal(false);
  statusFilter = signal<StatusFilter>('ALL');

  statusFilters: { value: StatusFilter; label: string }[] = [
    { value: 'ALL', label: 'All' },
    { value: 'PLANNED', label: 'Planned' },
    { value: 'ACTIVE', label: 'Active' },
    { value: 'SUSPENDED', label: 'Suspended' },
  ];

  filteredEnvironments = computed(() => {
    const envs = this.environments();
    const filter = this.statusFilter();
    if (filter === 'ALL') return envs;
    return envs.filter(e => e.status === filter);
  });

  createForm = {
    name: '',
    displayName: '',
    description: '',
  };

  ngOnInit(): void {
    this.loadEnvironments();
  }

  loadEnvironments(): void {
    this.loading.set(true);
    this.lzService.listTenantEnvironments().subscribe({
      next: (envs: TenantEnvironment[]) => {
        this.environments.set(envs);
        this.loading.set(false);
      },
      error: () => {
        this.toast.error('Failed to load environments');
        this.loading.set(false);
      },
    });
  }

  getStatusCount(filter: StatusFilter): number {
    const envs = this.environments();
    if (filter === 'ALL') return envs.length;
    return envs.filter(e => e.status === filter).length;
  }

  hasConfig(config: Record<string, unknown> | null | undefined): boolean {
    return config !== null && config !== undefined && Object.keys(config).length > 0;
  }

  onCreate(): void {
    if (!this.createForm.name || !this.createForm.displayName) return;
    this.lzService.createTenantEnvironment({
      name: this.createForm.name,
      displayName: this.createForm.displayName,
      description: this.createForm.description || undefined,
    }).subscribe({
      next: () => {
        this.toast.success('Environment created');
        this.showCreate.set(false);
        this.createForm = { name: '', displayName: '', description: '' };
        this.loadEnvironments();
      },
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to create environment'),
    });
  }
}
