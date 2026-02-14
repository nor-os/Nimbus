/**
 * Overview: Provider SKU listing — paginated, filterable list of provider SKUs with inline
 *     create form for adding new SKUs.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/catalog.service,
 *     app/core/services/semantic.service, app/core/services/cmdb.service
 * Concepts: Provider SKU listing with provider/category/active filters, pagination, inline create form
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CatalogService } from '@core/services/catalog.service';
import { SemanticService } from '@core/services/semantic.service';
import { CmdbService } from '@core/services/cmdb.service';
import {
  ProviderSku,
  MeasuringUnit,
  CIClass,
} from '@shared/models/cmdb.model';
import { SemanticProvider } from '@shared/models/semantic.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const MEASURING_UNIT_LABELS: Record<MeasuringUnit, string> = {
  hour: 'Hour',
  day: 'Day',
  month: 'Month',
  gb: 'GB',
  request: 'Request',
  user: 'User',
  instance: 'Instance',
};

const MEASURING_UNIT_OPTIONS: { value: MeasuringUnit; label: string }[] = [
  { value: 'hour', label: 'Hour' },
  { value: 'day', label: 'Day' },
  { value: 'month', label: 'Month' },
  { value: 'gb', label: 'GB' },
  { value: 'request', label: 'Request' },
  { value: 'user', label: 'User' },
  { value: 'instance', label: 'Instance' },
];

@Component({
  selector: 'nimbus-sku-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="sku-list-page">
        <div class="page-header">
          <h1>Provider SKUs</h1>
          <button
            *nimbusHasPermission="'catalog:sku:manage'"
            class="btn btn-primary"
            (click)="showCreate = !showCreate"
          >
            {{ showCreate ? 'Cancel' : 'Create SKU' }}
          </button>
        </div>

        <!-- Create Form -->
        @if (showCreate) {
          <div class="create-card">
            <h2 class="create-title">New Provider SKU</h2>
            <div class="create-form">
              <div class="form-row">
                <div class="form-group">
                  <label for="createProvider">Provider *</label>
                  <select
                    id="createProvider"
                    [(ngModel)]="createForm.providerId"
                    class="form-input form-select"
                  >
                    <option value="">Select provider...</option>
                    @for (p of providers(); track p.id) {
                      <option [value]="p.id">{{ p.displayName }}</option>
                    }
                  </select>
                </div>
                <div class="form-group">
                  <label for="createExternalSkuId">External SKU ID *</label>
                  <input
                    id="createExternalSkuId"
                    [(ngModel)]="createForm.externalSkuId"
                    class="form-input"
                    placeholder="e.g. vm.standard.e4.flex"
                  />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label for="createName">Name *</label>
                  <input
                    id="createName"
                    [(ngModel)]="createForm.name"
                    class="form-input"
                    placeholder="SKU name"
                  />
                </div>
                <div class="form-group">
                  <label for="createDisplayName">Display Name</label>
                  <input
                    id="createDisplayName"
                    [(ngModel)]="createForm.displayName"
                    class="form-input"
                    placeholder="Human-friendly name"
                  />
                </div>
              </div>
              <div class="form-group">
                <label for="createDescription">Description</label>
                <textarea
                  id="createDescription"
                  [(ngModel)]="createForm.description"
                  class="form-input form-textarea"
                  placeholder="Optional description"
                  rows="2"
                ></textarea>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label for="createCiClass">CI Class</label>
                  <select
                    id="createCiClass"
                    [(ngModel)]="createForm.ciClassId"
                    class="form-input form-select"
                  >
                    <option value="">None</option>
                    @for (cls of ciClasses(); track cls.id) {
                      <option [value]="cls.id">{{ cls.displayName }}</option>
                    }
                  </select>
                </div>
                <div class="form-group">
                  <label for="createMeasuringUnit">Measuring Unit</label>
                  <select
                    id="createMeasuringUnit"
                    [(ngModel)]="createForm.measuringUnit"
                    class="form-input form-select"
                  >
                    @for (u of measuringUnitOptions; track u.value) {
                      <option [value]="u.value">{{ u.label }}</option>
                    }
                  </select>
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label for="createCategory">Category</label>
                  <input
                    id="createCategory"
                    [(ngModel)]="createForm.category"
                    class="form-input"
                    placeholder="e.g. Compute, Storage"
                  />
                </div>
                <div class="form-group">
                  <label for="createUnitCost">Unit Cost</label>
                  <input
                    id="createUnitCost"
                    type="number"
                    [(ngModel)]="createForm.unitCost"
                    class="form-input"
                    placeholder="0.00"
                    step="0.01"
                  />
                </div>
                <div class="form-group">
                  <label for="createCurrency">Currency</label>
                  <input
                    id="createCurrency"
                    [(ngModel)]="createForm.costCurrency"
                    class="form-input"
                    placeholder="EUR"
                  />
                </div>
              </div>
              @if (createError()) {
                <div class="form-error">{{ createError() }}</div>
              }
              <div class="form-actions">
                <button
                  class="btn btn-primary"
                  [disabled]="!createForm.providerId || !createForm.externalSkuId || !createForm.name || creating()"
                  (click)="submitCreate()"
                >
                  {{ creating() ? 'Creating...' : 'Create' }}
                </button>
                <button class="btn btn-secondary" (click)="showCreate = false">Cancel</button>
              </div>
            </div>
          </div>
        }

        <!-- Filters -->
        <div class="filters">
          <select
            [(ngModel)]="providerFilter"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            <option value="">All Providers</option>
            @for (p of providers(); track p.id) {
              <option [value]="p.id">{{ p.displayName }}</option>
            }
          </select>
          <input
            type="text"
            [(ngModel)]="categoryFilter"
            (ngModelChange)="onFilterChange()"
            placeholder="Filter by category..."
            class="filter-input"
          />
          <label class="toggle-label">
            <input
              type="checkbox"
              [(ngModel)]="activeOnly"
              (ngModelChange)="onFilterChange()"
            />
            <span>Active only</span>
          </label>
        </div>

        <!-- Table -->
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Provider</th>
                <th>External SKU ID</th>
                <th>Category</th>
                <th>Semantic Type</th>
                <th>Resource Type</th>
                <th>Unit Cost</th>
                <th>Measuring Unit</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              @for (sku of skus(); track sku.id) {
                <tr class="clickable-row" (click)="goToDetail(sku.id)">
                  <td class="name-cell">{{ sku.name }}</td>
                  <td>{{ providerName(sku.providerId) }}</td>
                  <td><code class="code-badge">{{ sku.externalSkuId }}</code></td>
                  <td>{{ sku.category || '\u2014' }}</td>
                  <td>{{ sku.semanticTypeName || '\u2014' }}</td>
                  <td><code class="code-badge" *ngIf="sku.resourceType">{{ sku.resourceType }}</code><span *ngIf="!sku.resourceType">\u2014</span></td>
                  <td>{{ sku.unitCost !== null ? (sku.unitCost | number:'1.2-2') + ' ' + sku.costCurrency : '\u2014' }}</td>
                  <td>{{ unitLabel(sku.measuringUnit) }}</td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-active]="sku.isActive"
                      [class.badge-inactive]="!sku.isActive"
                    >
                      {{ sku.isActive ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="9" class="empty-state">No provider SKUs found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="pagination">
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() === 0"
            (click)="prevPage()"
          >Previous</button>
          <span class="page-info">
            @if (total() > 0) {
              Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + skus().length }}
              of {{ total() }}
            } @else {
              No items
            }
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + skus().length >= total()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .sku-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .create-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .create-title { margin: 0 0 1rem; font-size: 1rem; font-weight: 600; color: #1e293b; }
    .create-form { display: flex; flex-direction: column; gap: 0; }
    .form-row { display: flex; gap: 0.75rem; }
    .form-row .form-group { flex: 1; }
    .form-group { margin-bottom: 1rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
    .form-textarea { resize: vertical; min-height: 48px; }
    .form-select { cursor: pointer; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }

    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
      align-items: center;
    }
    .filter-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 220px; font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; transition: border-color 0.15s;
    }
    .filter-input::placeholder { color: #94a3b8; }
    .filter-input:focus { border-color: #3b82f6; outline: none; }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; cursor: pointer; min-width: 180px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }
    .toggle-label {
      display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem;
      color: #374151; cursor: pointer;
    }
    .toggle-label input[type="checkbox"] { cursor: pointer; }

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
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }

    .code-badge {
      padding: 0.125rem 0.375rem; background: #f1f5f9; border: 1px solid #e2e8f0;
      border-radius: 4px; font-size: 0.75rem; color: #475569; font-family: monospace;
    }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fee2e2; color: #dc2626; }

    .empty-state { text-align: center; color: #64748b; padding: 2rem; }

    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .page-info { color: #64748b; font-size: 0.8125rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; color: #374151; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class SkuListComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private semanticService = inject(SemanticService);
  private cmdbService = inject(CmdbService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  skus = signal<ProviderSku[]>([]);
  total = signal(0);
  currentOffset = signal(0);
  pageSize = 50;
  providers = signal<SemanticProvider[]>([]);
  ciClasses = signal<CIClass[]>([]);

  providerFilter = '';
  categoryFilter = '';
  activeOnly = false;
  showCreate = false;
  creating = signal(false);
  createError = signal('');

  createForm = {
    providerId: '',
    externalSkuId: '',
    name: '',
    displayName: '',
    description: '',
    ciClassId: '',
    measuringUnit: 'month' as string,
    category: '',
    unitCost: null as number | null,
    costCurrency: 'EUR',
  };

  readonly measuringUnitOptions = MEASURING_UNIT_OPTIONS;

  private filterDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadProviders();
    this.loadCIClasses();
    this.loadSkus();
  }

  onFilterChange(): void {
    if (this.filterDebounceTimer) {
      clearTimeout(this.filterDebounceTimer);
    }
    this.filterDebounceTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.loadSkus();
    }, 300);
  }

  loadSkus(): void {
    this.catalogService.listSkus({
      providerId: this.providerFilter || undefined,
      category: this.categoryFilter.trim() || undefined,
      activeOnly: this.activeOnly || undefined,
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.skus.set(response.items);
        this.total.set(response.total);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load provider SKUs');
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadSkus();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadSkus();
  }

  goToDetail(id: string): void {
    this.router.navigate(['/catalog', 'skus', id]);
  }

  providerName(providerId: string): string {
    const p = this.providers().find((prov) => prov.id === providerId);
    return p ? p.displayName : providerId.substring(0, 8) + '...';
  }

  unitLabel(unit: string): string {
    return MEASURING_UNIT_LABELS[unit as MeasuringUnit] || unit;
  }

  submitCreate(): void {
    if (!this.createForm.providerId || !this.createForm.externalSkuId || !this.createForm.name) {
      return;
    }
    this.creating.set(true);
    this.createError.set('');

    const input: Record<string, unknown> = {
      providerId: this.createForm.providerId,
      externalSkuId: this.createForm.externalSkuId,
      name: this.createForm.name,
      displayName: this.createForm.displayName || null,
      description: this.createForm.description || null,
      ciClassId: this.createForm.ciClassId || null,
      measuringUnit: this.createForm.measuringUnit,
      category: this.createForm.category || null,
      unitCost: this.createForm.unitCost,
      costCurrency: this.createForm.costCurrency || 'EUR',
    };

    this.catalogService.createSku(input).subscribe({
      next: (sku) => {
        this.creating.set(false);
        this.toastService.success(`SKU "${sku.name}" created`);
        this.showCreate = false;
        this.resetCreateForm();
        this.loadSkus();
      },
      error: (err) => {
        this.creating.set(false);
        const msg = err.message || 'Failed to create provider SKU';
        this.createError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private resetCreateForm(): void {
    this.createForm = {
      providerId: '',
      externalSkuId: '',
      name: '',
      displayName: '',
      description: '',
      ciClassId: '',
      measuringUnit: 'month',
      category: '',
      unitCost: null,
      costCurrency: 'EUR',
    };
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => this.providers.set(providers),
    });
  }

  private loadCIClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => this.ciClasses.set(classes),
    });
  }
}
