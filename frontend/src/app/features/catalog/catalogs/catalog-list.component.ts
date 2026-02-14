/**
 * Overview: Service catalog listing -- paginated, filterable list of service catalogs
 *     with inline create form.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/catalog.service
 * Concepts: Service catalog CRUD, status filtering, pagination, inline creation
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CatalogService } from '@core/services/catalog.service';
import { TenantService } from '@core/services/tenant.service';
import {
  ServiceCatalog,
  ServiceCatalogList,
  TenantCatalogPin,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-catalog-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="catalog-list-page">
        <div class="page-header">
          <h1>Service Catalogs</h1>
          <button
            *nimbusHasPermission="'catalog:catalog:manage'"
            class="btn btn-primary"
            (click)="showCreateForm()"
          >
            Create Catalog
          </button>
        </div>

        <!-- Create form -->
        @if (creating()) {
          <div class="form-card">
            <h2 class="form-title">New Service Catalog</h2>
            <div class="form-group">
              <label class="form-label">Name *</label>
              <input
                class="form-input"
                [(ngModel)]="formName"
                placeholder="e.g. Enterprise Standard 2026"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <input
                class="form-input"
                [(ngModel)]="formDescription"
                placeholder="Optional description"
              />
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" (click)="cancelCreate()">Cancel</button>
              <button
                class="btn btn-primary"
                (click)="createCatalog()"
                [disabled]="!formName.trim()"
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
            (ngModelChange)="onFilterChange()"
            placeholder="Search catalogs..."
            class="filter-input"
          />
          <select
            [(ngModel)]="statusFilter"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        @if (loading()) {
          <div class="loading">Loading service catalogs...</div>
        }

        @if (!loading() && filteredCatalogs().length === 0 && !creating()) {
          <div class="empty-state">No service catalogs found.</div>
        }

        @if (!loading() && filteredCatalogs().length > 0) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Tenant Scope</th>
                  <th>Items</th>
                  <th>Pinned Tenants</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                @for (catalog of filteredCatalogs(); track catalog.id) {
                  <tr class="clickable-row" (click)="goToDetail(catalog.id)">
                    <td class="name-cell">{{ catalog.name }}</td>
                    <td>
                      <span class="badge badge-version">
                        {{ catalog.versionLabel }}
                      </span>
                    </td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-draft]="catalog.status === 'draft'"
                        [class.badge-published]="catalog.status === 'published'"
                        [class.badge-archived]="catalog.status === 'archived'"
                      >
                        {{ catalog.status }}
                      </span>
                    </td>
                    <td>{{ catalog.tenantId ? 'Tenant-specific' : 'System-wide' }}</td>
                    <td>{{ catalog.items.length }}</td>
                    <td>
                      @if (catalogPinsMap().get(catalog.id)?.length) {
                        <div class="tenant-chips">
                          @for (pin of catalogPinsMap().get(catalog.id)!; track pin.id) {
                            <span class="tenant-chip">{{ tenantNameForId(pin.tenantId) }}</span>
                          }
                        </div>
                      } @else {
                        <span class="text-muted">&mdash;</span>
                      }
                    </td>
                    <td class="td-actions" (click)="$event.stopPropagation()">
                      <button
                        *nimbusHasPermission="'catalog:catalog:manage'"
                        class="btn-icon btn-danger"
                        title="Delete catalog"
                        (click)="deleteCatalog(catalog)"
                      >
                        &times;
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="9" class="empty-state">No service catalogs found</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <!-- Pagination -->
        <div class="pagination">
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() === 0"
            (click)="prevPage()"
          >Previous</button>
          <span class="page-info">
            @if (total() > 0) {
              Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + catalogs().length }}
              of {{ total() }}
            } @else {
              No items
            }
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + catalogs().length >= total()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .catalog-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    /* -- Create form -------------------------------------------------- */
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
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }

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
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .th-actions, .td-actions { width: 48px; text-align: right; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-version { background: #dbeafe; color: #1d4ed8; }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-archived { background: #f1f5f9; color: #64748b; }

    .tenant-chips { display: flex; gap: 0.25rem; flex-wrap: wrap; }
    .tenant-chip {
      display: inline-block; padding: 0.125rem 0.5rem; background: #dbeafe;
      color: #1d4ed8; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .text-muted { color: #94a3b8; }

    /* -- States ------------------------------------------------------- */
    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Pagination --------------------------------------------------- */
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .page-info { color: #64748b; font-size: 0.8125rem; }

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
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; color: #374151; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class CatalogListComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  catalogs = signal<ServiceCatalog[]>([]);
  filteredCatalogs = signal<ServiceCatalog[]>([]);
  total = signal(0);
  currentOffset = signal(0);
  pageSize = 50;
  loading = signal(false);
  creating = signal(false);
  catalogPinsMap = signal<Map<string, TenantCatalogPin[]>>(new Map());
  private tenantMap = new Map<string, string>();

  // Filter fields
  searchFilter = '';
  statusFilter = '';

  // Create form fields
  formName = '';
  formDescription = '';

  private filterDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadCatalogs();
    this.loadTenants();
  }

  onFilterChange(): void {
    if (this.filterDebounceTimer) {
      clearTimeout(this.filterDebounceTimer);
    }
    this.filterDebounceTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.applyFilters();
    }, 300);
  }

  loadCatalogs(): void {
    this.loading.set(true);
    this.catalogService.listCatalogs({
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.catalogs.set(response.items);
        this.total.set(response.total);
        this.applyFilters();
        this.loading.set(false);
        this.loadPinsForAllCatalogs(response.items);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load service catalogs');
        this.loading.set(false);
      },
    });
  }

  private applyFilters(): void {
    let items = this.catalogs();

    if (this.statusFilter) {
      items = items.filter((c) => c.status === this.statusFilter);
    }

    if (this.searchFilter.trim()) {
      const q = this.searchFilter.trim().toLowerCase();
      items = items.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.description && c.description.toLowerCase().includes(q)),
      );
    }

    this.filteredCatalogs.set(items);
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadCatalogs();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadCatalogs();
  }

  goToDetail(id: string): void {
    this.router.navigate(['/catalog', 'catalogs', id]);
  }

  // -- Create form ---------------------------------------------------

  showCreateForm(): void {
    this.resetCreateForm();
    this.creating.set(true);
  }

  cancelCreate(): void {
    this.creating.set(false);
    this.resetCreateForm();
  }

  createCatalog(): void {
    this.catalogService.createCatalog({
      name: this.formName.trim(),
      description: this.formDescription.trim() || undefined,
    }).subscribe({
      next: (created) => {
        this.catalogs.update((list) => [created, ...list]);
        this.total.update((t) => t + 1);
        this.applyFilters();
        this.toastService.success(`Catalog "${created.name}" created`);
        this.cancelCreate();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create service catalog');
      },
    });
  }

  deleteCatalog(catalog: ServiceCatalog): void {
    this.catalogService.deleteCatalog(catalog.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.catalogs.update((list) => list.filter((c) => c.id !== catalog.id));
          this.total.update((t) => Math.max(0, t - 1));
          this.applyFilters();
          this.toastService.success(`Catalog "${catalog.name}" deleted`);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete catalog');
      },
    });
  }

  tenantNameForId(tenantId: string): string {
    return this.tenantMap.get(tenantId) || tenantId.substring(0, 8) + '...';
  }

  private loadTenants(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (list) => {
        for (const t of list) {
          this.tenantMap.set(t.id, t.name);
        }
      },
    });
  }

  private loadPinsForAllCatalogs(cats: ServiceCatalog[]): void {
    const newMap = new Map<string, TenantCatalogPin[]>();
    for (const cat of cats) {
      this.catalogService.listPinnedTenantsForCatalog(cat.id).subscribe({
        next: (pins) => {
          if (pins.length > 0) {
            newMap.set(cat.id, pins);
            this.catalogPinsMap.set(new Map(newMap));
          }
        },
      });
    }
  }

  private resetCreateForm(): void {
    this.formName = '';
    this.formDescription = '';
  }
}
