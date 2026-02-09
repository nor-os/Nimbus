/**
 * Overview: Delivery region listing with hierarchical display, system/active badges,
 *     parent region lookup, and CRUD navigation.
 * Architecture: Catalog feature component for delivery region management (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/common,
 *     app/core/services/delivery.service, app/shared/services/toast.service,
 *     app/shared/services/confirm.service
 * Concepts: Delivery regions, hierarchical listing, system vs tenant regions,
 *     permission-gated actions, soft-delete with confirmation
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { DeliveryService } from '@core/services/delivery.service';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

interface DisplayRegion extends DeliveryRegion {
  parentDisplayName: string | null;
  depth: number;
}

@Component({
  selector: 'nimbus-region-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="region-list-page">
        <div class="page-header">
          <h1>Delivery Regions</h1>
          <a
            *nimbusHasPermission="'catalog:region:manage'"
            routerLink="/catalog/regions/create"
            class="btn btn-primary"
          >
            Create Region
          </a>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Timezone</th>
                <th>Country</th>
                <th>Parent</th>
                <th>System?</th>
                <th>Active?</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (region of displayRegions(); track region.id) {
                <tr>
                  <td class="name-cell" [style.paddingLeft]="(region.depth * 1.5 + 1) + 'rem'">
                    {{ region.displayName }}
                  </td>
                  <td>{{ region.code }}</td>
                  <td>{{ region.timezone || '\u2014' }}</td>
                  <td>{{ region.countryCode || '\u2014' }}</td>
                  <td>{{ region.parentDisplayName || '\u2014' }}</td>
                  <td>
                    @if (region.isSystem) {
                      <span class="badge badge-system">System</span>
                    } @else {
                      <span class="badge badge-tenant">Tenant</span>
                    }
                  </td>
                  <td>
                    @if (region.isActive) {
                      <span class="badge badge-active">Active</span>
                    } @else {
                      <span class="badge badge-inactive">Inactive</span>
                    }
                  </td>
                  <td class="actions">
                    <a
                      [routerLink]="['/catalog', 'regions', region.id]"
                      class="icon-btn"
                      title="Edit"
                    >
                      &#9998;
                    </a>
                    <button
                      *nimbusHasPermission="'catalog:region:manage'"
                      class="icon-btn icon-btn-danger"
                      title="Delete"
                      [disabled]="region.isSystem"
                      (click)="confirmDelete(region)"
                    >
                      &#10005;
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="8" class="empty-state">No delivery regions found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .region-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

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
    .name-cell { font-weight: 500; color: #1e293b; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fee2e2; color: #dc2626; }
    .badge-system { background: #dbeafe; color: #2563eb; }
    .badge-tenant { background: #f1f5f9; color: #64748b; }

    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none; font-size: 0.875rem;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn:disabled { opacity: 0.35; cursor: not-allowed; }
    .icon-btn:disabled:hover { background: none; color: #64748b; }
    .icon-btn-danger:hover:not(:disabled) { color: #dc2626; background: #fef2f2; }

    .empty-state { text-align: center; color: #64748b; padding: 2rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; text-decoration: none;
    }
    .btn-primary:hover { background: #2563eb; }
  `],
})
export class RegionListComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private router = inject(Router);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);

  allRegions = signal<DeliveryRegion[]>([]);

  displayRegions = computed<DisplayRegion[]>(() => {
    const regions = this.allRegions();
    const regionMap = new Map<string, DeliveryRegion>();
    for (const r of regions) {
      regionMap.set(r.id, r);
    }

    // Build a tree: top-level first, then children indented under parent
    const topLevel = regions
      .filter((r) => !r.parentRegionId)
      .sort((a, b) => a.sortOrder - b.sortOrder || a.displayName.localeCompare(b.displayName));

    const result: DisplayRegion[] = [];

    const addRegion = (region: DeliveryRegion, depth: number): void => {
      const parentDisplayName = region.parentRegionId
        ? regionMap.get(region.parentRegionId)?.displayName ?? null
        : null;

      result.push({ ...region, parentDisplayName, depth });

      // Find and add children
      const children = regions
        .filter((r) => r.parentRegionId === region.id)
        .sort((a, b) => a.sortOrder - b.sortOrder || a.displayName.localeCompare(b.displayName));

      for (const child of children) {
        addRegion(child, depth + 1);
      }
    };

    for (const region of topLevel) {
      addRegion(region, 0);
    }

    return result;
  });

  ngOnInit(): void {
    this.loadRegions();
  }

  loadRegions(): void {
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (response) => {
        this.allRegions.set(response.items);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load delivery regions');
      },
    });
  }

  async confirmDelete(region: DisplayRegion): Promise<void> {
    if (region.isSystem) return;

    const ok = await this.confirmService.confirm({
      title: 'Delete Region',
      message: `Are you sure you want to delete "${region.displayName}"? This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.deliveryService.deleteRegion(region.id).subscribe({
      next: () => {
        this.toastService.success(`"${region.displayName}" deleted`);
        this.loadRegions();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete region');
      },
    });
  }
}
