/**
 * Overview: Tenant settings page with editable General, Quotas, and Data Export tabs.
 * Architecture: Feature component for tenant configuration (Section 3.2)
 * Dependencies: @angular/core, @angular/router, app/core/services/tenant.service, app/shared/components/property-table
 * Concepts: Multi-tenancy, tenant settings, quota management, property editing, data export, danger zone
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TenantService } from '@core/services/tenant.service';
import { TenantDetail, TenantQuota } from '@core/models/tenant.model';
import { DomainMapping, DomainMappingService } from '@core/services/domain-mapping.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import {
  PropertyTableComponent,
  PropertyField,
  PropertyChangeEvent,
} from '@shared/components/property-table/property-table.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-tenant-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, PropertyTableComponent],
  template: `
    <nimbus-layout>
      <div class="settings-page">
        <h1>Settings: {{ tenant()?.name }}</h1>

        <div class="tabs">
          <button
            class="tab"
            [class.active]="activeTab() === 'general'"
            (click)="setTab('general')"
          >General</button>
          <button
            class="tab"
            [class.active]="activeTab() === 'quotas'"
            (click)="setTab('quotas')"
          >Quotas</button>
          <button
            class="tab"
            [class.active]="activeTab() === 'domains'"
            (click)="setTab('domains')"
          >Domains</button>
          <button
            class="tab"
            [class.active]="activeTab() === 'export'"
            (click)="setTab('export')"
          >Data Export</button>
        </div>

        <div class="tab-content">
          @if (activeTab() === 'general') {
            <div class="section">
              <h2>General Information</h2>
              @if (generalData()) {
                <nimbus-property-table
                  [fields]="generalFields()"
                  [data]="generalData()!"
                  [showSave]="true"
                  [saving]="generalSaving()"
                  (save)="onGeneralSave($event)"
                />
              }

              <div class="danger-zone">
                <h3>Danger Zone</h3>
                <p>Deleting this tenant will soft-delete it and all its data.</p>
                <button class="btn btn-danger" (click)="confirmDelete()">Delete Tenant</button>
              </div>
            </div>
          }

          @if (activeTab() === 'quotas') {
            <div class="section">
              <h2>Quota Management</h2>
              @if (quotaData()) {
                <nimbus-property-table
                  [fields]="quotaFields()"
                  [data]="quotaData()!"
                  [showSave]="false"
                  (valueChange)="onQuotaChange($event)"
                />
              }
              @if (!quotas().length) {
                <p class="empty">No quotas configured for this tenant.</p>
              }
            </div>
          }

          @if (activeTab() === 'domains') {
            <div class="section">
              <h2>Domain Mappings</h2>
              <p class="section-hint">Map email domains to this tenant so users are automatically routed here during login.</p>

              @if (domainError()) {
                <div class="domain-alert">{{ domainError() }}</div>
              }

              @if (showDomainForm()) {
                <div class="domain-form-card">
                  <form [formGroup]="domainForm" (ngSubmit)="onCreateDomain()">
                    <div class="domain-form-row">
                      <input formControlName="domain" type="text" placeholder="example.com" class="domain-input" />
                      <button type="submit" class="btn btn-primary" [disabled]="domainForm.invalid || domainSaving()">
                        {{ domainSaving() ? 'Adding...' : 'Add' }}
                      </button>
                      <button type="button" class="btn btn-secondary" (click)="showDomainForm.set(false)">Cancel</button>
                    </div>
                  </form>
                </div>
              } @else {
                <button class="btn btn-primary" (click)="showDomainForm.set(true)" style="margin-bottom: 1rem;">
                  + Add Domain
                </button>
              }

              @if (domainsLoading()) {
                <p class="empty">Loading...</p>
              } @else if (!domains().length) {
                <p class="empty">No domain mappings configured yet.</p>
              } @else {
                <table class="domain-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Added</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (d of domains(); track d.id) {
                      <tr>
                        <td class="domain-name">{{ d.domain }}</td>
                        <td class="date-col">{{ d.created_at | date: 'mediumDate' }}</td>
                        <td><button class="btn-icon-del" (click)="onDeleteDomain(d)" title="Remove">&#10005;</button></td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            </div>
          }

          @if (activeTab() === 'export') {
            <div class="section">
              <h2>Data Export</h2>
              <p>Export all tenant data as a ZIP archive.</p>
              <button class="btn btn-primary" (click)="startExport()" [disabled]="exporting()">
                {{ exporting() ? 'Exporting...' : 'Start Export' }}
              </button>
              @if (exportJobId()) {
                <div class="export-status">
                  <p>Export started. Job ID: {{ exportJobId() }}</p>
                  <button class="btn btn-secondary" (click)="downloadExport()">Download</button>
                </div>
              }
            </div>
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .settings-page { padding: 0; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; }
    .tabs {
      display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.5rem; gap: 0.25rem;
    }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; font-family: inherit;
      transition: color 0.15s;
    }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab:hover { color: #3b82f6; }
    .section { margin-bottom: 2rem; }
    .section h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin-bottom: 1rem; }
    .empty { color: #94a3b8; font-size: 0.8125rem; padding: 1rem; }
    .danger-zone {
      margin-top: 2rem; padding: 1.25rem; border: 1px solid #fecaca;
      border-radius: 8px; background: #fff;
    }
    .danger-zone h3 { color: #dc2626; font-size: 0.9375rem; font-weight: 600; margin-bottom: 0.5rem; }
    .danger-zone p { font-size: 0.8125rem; color: #64748b; margin-bottom: 0.75rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: background 0.15s; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover:not(:disabled) { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; border: none; }
    .btn-danger:hover { background: #b91c1c; }
    .export-status {
      margin-top: 1rem; padding: 0.75rem 1rem; background: #f0fdf4;
      border: 1px solid #bbf7d0; border-radius: 8px;
    }
    .export-status p { font-size: 0.8125rem; margin-bottom: 0.5rem; color: #166534; }
    .section-hint { font-size: 0.8125rem; color: #64748b; margin: -0.5rem 0 1rem; }
    .domain-alert {
      padding: 0.625rem 0.875rem; margin-bottom: 0.75rem; font-size: 0.8125rem;
      color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
    }
    .domain-form-card { margin-bottom: 1rem; }
    .domain-form-row { display: flex; gap: 0.5rem; align-items: center; }
    .domain-input {
      flex: 1; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit;
    }
    .domain-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .domain-table { width: 100%; border-collapse: collapse; }
    .domain-table th, .domain-table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 0.8125rem;
    }
    .domain-table th { color: #64748b; font-weight: 600; text-transform: uppercase; font-size: 0.6875rem; letter-spacing: 0.05em; }
    .domain-name { font-weight: 500; color: #1e293b; }
    .date-col { color: #64748b; }
    .btn-icon-del {
      padding: 0.2rem 0.4rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; cursor: pointer; font-size: 0.75rem; color: #dc2626;
    }
    .btn-icon-del:hover { background: #fef2f2; border-color: #fecaca; }
  `],
})
export class TenantSettingsComponent implements OnInit {
  private tenantService = inject(TenantService);
  private domainMappingService = inject(DomainMappingService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private datePipe = new DatePipe('en-US');

  tenant = signal<TenantDetail | null>(null);
  quotas = signal<TenantQuota[]>([]);
  activeTab = signal<'general' | 'quotas' | 'domains' | 'export'>('general');
  generalSaving = signal(false);
  exporting = signal(false);
  exportJobId = signal('');

  // Domain mappings
  domains = signal<DomainMapping[]>([]);
  domainsLoading = signal(false);
  domainSaving = signal(false);
  domainError = signal<string | null>(null);
  showDomainForm = signal(false);
  domainForm = new FormGroup({
    domain: new FormControl('', [
      Validators.required,
      Validators.pattern(/^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*\.[a-zA-Z]{2,}$/),
    ]),
  });

  private tenantId = '';

  generalFields = computed<PropertyField[]>(() => {
    return [
      { key: 'name', label: 'Name', controlType: 'text', required: true, placeholder: 'Tenant name' },
      { key: 'contact_email', label: 'Contact Email', controlType: 'email', placeholder: 'contact@example.com' },
      { key: 'description', label: 'Description', controlType: 'textarea', placeholder: 'Optional description' },
      { key: 'level', label: 'Level', controlType: 'readonly' },
      { key: 'created_at', label: 'Created', controlType: 'readonly' },
    ];
  });

  generalData = computed<Record<string, unknown> | null>(() => {
    const t = this.tenant();
    if (!t) return null;
    return {
      name: t.name,
      contact_email: t.contact_email ?? '',
      description: t.description ?? '',
      level: this.getLevelLabel(t.level),
      created_at: this.datePipe.transform(t.created_at, 'medium') ?? t.created_at,
    };
  });

  quotaFields = computed<PropertyField[]>(() => {
    return this.quotas().map((q) => {
      const label = this.formatQuotaLabel(q.quota_type);
      const suffix = this.getQuotaSuffix(q.quota_type);
      return {
        key: q.quota_type,
        label,
        controlType: 'number' as const,
        min: 0,
        suffix,
        hint: `Currently using ${q.current_usage} of ${q.limit_value}`,
        extras: [{
          key: 'enforcement',
          label: 'Enforcement',
          controlType: 'select' as const,
          options: [
            { label: 'Hard', value: 'hard' },
            { label: 'Soft', value: 'soft' },
          ],
          width: '100px',
        }],
      };
    });
  });

  quotaData = computed<Record<string, unknown> | null>(() => {
    const qs = this.quotas();
    if (!qs.length) return null;
    const data: Record<string, unknown> = {};
    for (const q of qs) {
      data[q.quota_type] = q.limit_value;
      data[`${q.quota_type}__enforcement`] = q.enforcement;
    }
    return data;
  });

  ngOnInit(): void {
    this.tenantId = this.route.snapshot.params['id'];

    const tabParam = this.route.snapshot.queryParams['tab'];
    if (tabParam === 'quotas' || tabParam === 'domains' || tabParam === 'export') {
      this.activeTab.set(tabParam);
    }

    this.loadTenant();
    this.loadStats();
  }

  setTab(tab: 'general' | 'quotas' | 'domains' | 'export'): void {
    this.activeTab.set(tab);
    if (tab === 'domains' && !this.domains().length && !this.domainsLoading()) {
      this.loadDomains();
    }
  }

  onGeneralSave(data: Record<string, unknown>): void {
    this.generalSaving.set(true);
    this.tenantService.updateTenant(this.tenantId, {
      name: data['name'] as string || undefined,
      contact_email: (data['contact_email'] as string) || null,
      description: (data['description'] as string) || null,
    }).subscribe({
      next: (updated) => {
        this.tenant.update((t) => t ? { ...t, name: updated.name, contact_email: updated.contact_email, description: updated.description } : t);
        this.generalSaving.set(false);
        this.toastService.success('Settings saved');
      },
      error: (err) => {
        this.generalSaving.set(false);
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to save settings');
      },
    });
  }

  onQuotaChange(event: PropertyChangeEvent): void {
    const quotaType = event.key;
    if (event.extraKey === 'enforcement') {
      this.tenantService.updateQuota(this.tenantId, quotaType, {
        enforcement: event.value as string,
      }).subscribe({
        next: (updated) => {
          this.updateQuotaInList(updated);
          this.toastService.success('Quota updated');
        },
        error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to update quota'),
      });
    } else {
      const numValue = typeof event.value === 'number' ? event.value : Number(event.value);
      if (isNaN(numValue)) return;
      this.tenantService.updateQuota(this.tenantId, quotaType, {
        limit_value: numValue,
      }).subscribe({
        next: (updated) => {
          this.updateQuotaInList(updated);
          this.toastService.success('Quota updated');
        },
        error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to update quota'),
      });
    }
  }

  startExport(): void {
    this.exporting.set(true);
    this.tenantService.startExport(this.tenantId).subscribe({
      next: (res) => {
        this.exportJobId.set(res.job_id);
        this.exporting.set(false);
        this.toastService.success('Export started');
      },
      error: (err) => {
        this.exporting.set(false);
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to start export');
      },
    });
  }

  downloadExport(): void {
    this.tenantService.getExportDownload(this.tenantId, this.exportJobId()).subscribe({
      next: (res) => window.open(res.download_url, '_blank'),
    });
  }

  async confirmDelete(): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Tenant',
      message: `Are you sure you want to delete "${this.tenant()?.name}"? This action will soft-delete the tenant and all its data.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.tenantService.deleteTenant(this.tenantId).subscribe({
      next: () => {
        this.toastService.success('Tenant deleted');
        this.router.navigate(['/tenants']);
      },
      error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete tenant'),
    });
  }

  // ── Domain mapping methods ──────────────────────────────────────

  loadDomains(): void {
    this.domainsLoading.set(true);
    this.domainMappingService.listForTenant(this.tenantId).subscribe({
      next: (data) => { this.domains.set(data); this.domainsLoading.set(false); },
      error: () => { this.domainError.set('Failed to load domain mappings.'); this.domainsLoading.set(false); },
    });
  }

  onCreateDomain(): void {
    if (this.domainForm.invalid) return;
    this.domainSaving.set(true);
    this.domainError.set(null);
    this.domainMappingService.createForTenant(this.tenantId, { domain: this.domainForm.value.domain! }).subscribe({
      next: () => {
        this.domainSaving.set(false);
        this.showDomainForm.set(false);
        this.domainForm.reset();
        this.loadDomains();
        this.toastService.success('Domain added');
      },
      error: (err) => {
        this.domainSaving.set(false);
        this.domainError.set(err.error?.error?.message ?? 'Failed to add domain.');
      },
    });
  }

  onDeleteDomain(d: DomainMapping): void {
    this.domainError.set(null);
    this.domainMappingService.deleteForTenant(this.tenantId, d.id).subscribe({
      next: () => { this.loadDomains(); this.toastService.success('Domain removed'); },
      error: (err) => this.domainError.set(err.error?.error?.message ?? 'Failed to remove domain.'),
    });
  }

  private loadTenant(): void {
    this.tenantService.getTenant(this.tenantId).subscribe({
      next: (t) => this.tenant.set(t),
    });
  }

  private loadStats(): void {
    this.tenantService.getTenantStats(this.tenantId).subscribe({
      next: (s) => this.quotas.set(s.quotas),
    });
  }

  private getLevelLabel(level: number): string {
    return ['Provider', 'Tenant', 'Sub-tenant'][level] ?? `Level ${level}`;
  }

  private formatQuotaLabel(quotaType: string): string {
    return quotaType.replace(/_/g, ' ').replace(/\bmax\b/i, 'Max').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  private getQuotaSuffix(quotaType: string): string {
    const suffixMap: Record<string, string> = {
      max_users: 'users',
      max_compartments: 'compartments',
      max_children: 'children',
      max_storage_gb: 'GB',
      max_resources: 'resources',
    };
    return suffixMap[quotaType] ?? '';
  }

  private updateQuotaInList(updated: TenantQuota): void {
    this.quotas.update((qs) =>
      qs.map((q) => q.quota_type === updated.quota_type ? updated : q),
    );
  }
}
