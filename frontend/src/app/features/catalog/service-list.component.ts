/**
 * Overview: Service catalog listing — paginated, filterable list of service offerings.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/catalog.service, app/core/services/cmdb.service
 * Concepts: Service offering listing with category/active filters, pagination, link to form
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
import { TenantContextService } from '@core/services/tenant-context.service';
import {
  ServiceOffering,
  MeasuringUnit,
} from '@shared/models/cmdb.model';
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

@Component({
  selector: 'nimbus-service-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="service-list-page">
        <div class="page-header">
          <h1>Service Catalog</h1>
          <a
            *nimbusHasPermission="'catalog:offering:create'"
            routerLink="/catalog/services/new"
            class="btn btn-primary"
          >
            Create Service
          </a>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="categoryFilter"
            (ngModelChange)="onFilterChange()"
            placeholder="Filter by category..."
            class="filter-input"
          />
          <select
            [(ngModel)]="activeFilter"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            <option value="">All Statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Measuring Unit</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              @for (offering of offerings(); track offering.id) {
                <tr class="clickable-row" (click)="goToEdit(offering.id)">
                  <td class="name-cell">{{ offering.name }}</td>
                  <td>{{ offering.category || '\u2014' }}</td>
                  <td>{{ unitLabel(offering.measuringUnit) }}</td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-active]="offering.isActive"
                      [class.badge-inactive]="!offering.isActive"
                    >
                      {{ offering.isActive ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ offering.updatedAt | date: 'medium' }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="empty-state">No service offerings found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() === 0"
            (click)="prevPage()"
          >Previous</button>
          <span class="page-info">
            @if (total() > 0) {
              Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + offerings().length }}
              of {{ total() }}
            } @else {
              No items
            }
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + offerings().length >= total()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .service-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

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
      border: none; text-decoration: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; color: #374151; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class ServiceListComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private tenantContext = inject(TenantContextService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  offerings = signal<ServiceOffering[]>([]);
  total = signal(0);
  currentOffset = signal(0);
  pageSize = 50;
  categoryFilter = '';
  activeFilter = '';

  private filterDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadOfferings();
  }

  onFilterChange(): void {
    if (this.filterDebounceTimer) {
      clearTimeout(this.filterDebounceTimer);
    }
    this.filterDebounceTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.loadOfferings();
    }, 300);
  }

  loadOfferings(): void {
    this.catalogService.listOfferings({
      category: this.categoryFilter.trim() || undefined,
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        let items = response.items;
        // Client-side active filter since the API may not support it directly
        if (this.activeFilter === 'true') {
          items = items.filter((o) => o.isActive);
        } else if (this.activeFilter === 'false') {
          items = items.filter((o) => !o.isActive);
        }
        this.offerings.set(items);
        this.total.set(response.total);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load service offerings');
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadOfferings();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadOfferings();
  }

  goToEdit(id: string): void {
    this.router.navigate(['/catalog', 'services', id]);
  }

  unitLabel(unit: string): string {
    return MEASURING_UNIT_LABELS[unit as MeasuringUnit] || unit;
  }
}
