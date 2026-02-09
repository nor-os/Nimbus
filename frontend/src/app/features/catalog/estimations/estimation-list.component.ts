/**
 * Overview: Service estimation listing — view and manage service delivery estimations.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/delivery.service
 * Concepts: Service estimations, profitability, margin calculation
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DeliveryService } from '@core/services/delivery.service';
import { CatalogService } from '@core/services/catalog.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { TenantService } from '@core/services/tenant.service';
import {
  ServiceEstimation,
  EstimationStatus,
  DeliveryRegion,
} from '@shared/models/delivery.model';
import { ServiceOffering } from '@shared/models/cmdb.model';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

@Component({
  selector: 'nimbus-estimation-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="estimation-list-page">
        <div class="page-header">
          <h1>Service Estimations</h1>
          <a
            *nimbusHasPermission="'catalog:estimation:manage'"
            routerLink="/catalog/estimations/new"
            class="btn btn-primary"
          >
            Create Estimation
          </a>
        </div>

        <div class="filters">
          <select
            [(ngModel)]="statusFilter"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            @for (opt of statusOptions; track opt.value) {
              <option [value]="opt.value">{{ opt.label }}</option>
            }
          </select>
        </div>

        @if (loading()) {
          <div class="loading">Loading estimations...</div>
        }

        @if (!loading()) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Service</th>
                  <th>Region</th>
                  <th>Status</th>
                  <th class="th-right">Sell Price</th>
                  <th class="th-right">Cost</th>
                  <th class="th-right">Margin %</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                @for (estimation of estimations(); track estimation.id) {
                  <tr class="clickable-row" (click)="goToDetail(estimation.id)">
                    <td class="name-cell">{{ clientName(estimation.clientTenantId) }}</td>
                    <td>{{ serviceName(estimation.serviceOfferingId) }}</td>
                    <td>{{ regionName(estimation.deliveryRegionId) }}</td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-draft]="estimation.status === 'draft'"
                        [class.badge-submitted]="estimation.status === 'submitted'"
                        [class.badge-approved]="estimation.status === 'approved'"
                        [class.badge-rejected]="estimation.status === 'rejected'"
                      >
                        {{ estimation.status | titlecase }}
                      </span>
                    </td>
                    <td class="td-right mono">
                      @if (estimation.totalSellPrice != null) {
                        {{ estimation.totalSellPrice | number: '1.2-2' }}
                        {{ estimation.sellCurrency }}
                      } @else {
                        <span class="text-muted">&mdash;</span>
                      }
                    </td>
                    <td class="td-right mono">
                      @if (estimation.totalEstimatedCost != null) {
                        {{ estimation.totalEstimatedCost | number: '1.2-2' }}
                      } @else {
                        <span class="text-muted">&mdash;</span>
                      }
                    </td>
                    <td class="td-right">
                      @if (estimation.marginPercent != null) {
                        <span
                          class="margin-value"
                          [class.margin-positive]="estimation.marginPercent >= 0"
                          [class.margin-negative]="estimation.marginPercent < 0"
                        >
                          {{ estimation.marginPercent | number: '1.1-1' }}%
                        </span>
                      } @else {
                        <span class="text-muted">&mdash;</span>
                      }
                    </td>
                    <td>{{ estimation.updatedAt | date: 'medium' }}</td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="8" class="empty-state">No estimations found</td>
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
                Showing {{ currentOffset() + 1 }}&ndash;{{ currentOffset() + estimations().length }}
                of {{ total() }}
              } @else {
                No items
              }
            </span>
            <button
              class="btn btn-sm"
              [disabled]="currentOffset() + estimations().length >= total()"
              (click)="nextPage()"
            >Next</button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .estimation-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
    }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; cursor: pointer; min-width: 180px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }

    .loading {
      padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

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
    .th-right, .td-right { text-align: right; }
    .table tbody tr { color: #334155; }
    .table tbody tr:hover { background: #f8fafc; }
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .text-muted { color: #94a3b8; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-submitted { background: #dbeafe; color: #1d4ed8; }
    .badge-approved { background: #dcfce7; color: #16a34a; }
    .badge-rejected { background: #fee2e2; color: #dc2626; }

    .margin-value { font-weight: 600; font-size: 0.8125rem; }
    .margin-positive { color: #16a34a; }
    .margin-negative { color: #dc2626; }

    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }

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
      border-radius: 6px; background: #fff; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class EstimationListComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  estimations = signal<ServiceEstimation[]>([]);
  total = signal(0);
  currentOffset = signal(0);
  loading = signal(false);
  pageSize = 50;
  statusFilter = '';

  readonly statusOptions = STATUS_OPTIONS;

  // Lookup maps for display names
  private clientMap = signal<Map<string, string>>(new Map());
  private serviceMap = signal<Map<string, string>>(new Map());
  private regionMap = signal<Map<string, string>>(new Map());

  ngOnInit(): void {
    this.loadLookups();
    this.loadEstimations();
  }

  onFilterChange(): void {
    this.currentOffset.set(0);
    this.loadEstimations();
  }

  loadEstimations(): void {
    this.loading.set(true);
    this.deliveryService.listEstimations({
      status: this.statusFilter || undefined,
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.estimations.set(response.items);
        this.total.set(response.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load estimations');
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadEstimations();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadEstimations();
  }

  goToDetail(id: string): void {
    this.router.navigate(['/catalog', 'estimations', id]);
  }

  clientName(id: string): string {
    return this.clientMap().get(id) || id.substring(0, 8) + '...';
  }

  serviceName(id: string): string {
    return this.serviceMap().get(id) || id.substring(0, 8) + '...';
  }

  regionName(id: string | null): string {
    if (!id) return '\u2014';
    return this.regionMap().get(id) || id.substring(0, 8) + '...';
  }

  // ── Private helpers ─────────────────────────────────────────────

  private loadLookups(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (tenants) => {
        const map = new Map<string, string>();
        tenants.forEach((t) => map.set(t.id, t.name));
        this.clientMap.set(map);
      },
    });

    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => {
        const map = new Map<string, string>();
        response.items.forEach((o) => map.set(o.id, o.name));
        this.serviceMap.set(map);
      },
    });

    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (response) => {
        const map = new Map<string, string>();
        response.items.forEach((r) => map.set(r.id, r.displayName));
        this.regionMap.set(map);
      },
    });
  }
}
