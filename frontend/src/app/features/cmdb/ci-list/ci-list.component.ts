/**
 * Overview: CI list component — paginated, filterable list of configuration items.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/cmdb.service
 * Concepts: CI listing with search, class/state/compartment filters, pagination, bulk operations
 */
import { Component, inject, signal, computed, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { CmdbService } from '@core/services/cmdb.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { ConfigurationItem, CIClass, LifecycleState } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { createTableSelection } from '@shared/utils/table-selection';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

const LIFECYCLE_STATES: LifecycleState[] = ['planned', 'active', 'maintenance', 'retired'];

@Component({
  selector: 'nimbus-ci-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="ci-list-page">
        <div class="page-header">
          <h1>Configuration Items</h1>
          <a *nimbusHasPermission="'cmdb:ci:create'" routerLink="/cmdb/create" class="btn btn-primary">
            Create CI
          </a>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
            placeholder="Search by name or description..."
            class="search-input"
          />
          <nimbus-searchable-select
            [(ngModel)]="selectedClassId"
            [options]="classOptions()"
            placeholder="All Classes"
            (ngModelChange)="onFilterChange()"
            [allowClear]="true"
          />
          <select
            [(ngModel)]="selectedState"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            <option value="">All States</option>
            @for (state of lifecycleStates; track state) {
              <option [value]="state">{{ state | titlecase }}</option>
            }
          </select>
        </div>

        @if (selection.selectedCount() > 0) {
          <div class="bulk-toolbar">
            <span class="bulk-count">{{ selection.selectedCount() }} selected</span>
            <button
              *nimbusHasPermission="'cmdb:ci:delete'"
              class="btn btn-sm btn-sm-danger"
              (click)="bulkDelete()"
            >Delete</button>
            <button class="btn-link" (click)="selection.clear()">Clear</button>
          </div>
        }

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th class="th-check">
                  <input
                    type="checkbox"
                    [checked]="selection.allSelected()"
                    [indeterminate]="selection.someSelected()"
                    (change)="selection.toggleAll()"
                  />
                </th>
                <th>Name</th>
                <th>Class</th>
                <th>State</th>
                <th>Compartment</th>
                <th>Tags</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              @for (ci of cis(); track ci.id) {
                <tr class="clickable-row" (click)="goToDetail(ci.id)">
                  <td (click)="$event.stopPropagation()">
                    <input
                      type="checkbox"
                      [checked]="selection.isSelected(ci.id)"
                      (change)="selection.toggle(ci.id)"
                    />
                  </td>
                  <td class="name-cell">{{ ci.name }}</td>
                  <td>{{ ci.ciClassName }}</td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-planned]="ci.lifecycleState === 'planned'"
                      [class.badge-active]="ci.lifecycleState === 'active'"
                      [class.badge-maintenance]="ci.lifecycleState === 'maintenance'"
                      [class.badge-retired]="ci.lifecycleState === 'retired'"
                    >
                      {{ ci.lifecycleState | titlecase }}
                    </span>
                  </td>
                  <td>{{ ci.compartmentId ? ci.compartmentId : '\u2014' }}</td>
                  <td>
                    @if (ci.tags && objectKeys(ci.tags).length > 0) {
                      <span class="tag-count">{{ objectKeys(ci.tags).length }} tag(s)</span>
                    } @else {
                      <span class="text-muted">\u2014</span>
                    }
                  </td>
                  <td>{{ ci.updatedAt | date: 'medium' }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="empty-state">No configuration items found</td>
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
            @if (totalCIs() > 0) {
              Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + cis().length }}
              of {{ totalCIs() }}
            } @else {
              No items
            }
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + cis().length >= totalCIs()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .ci-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; border-radius: 6px; text-decoration: none; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
    }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; font-family: inherit; cursor: pointer;
      min-width: 160px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }
    .bulk-toolbar {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem;
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 1rem;
    }
    .bulk-count { font-size: 0.8125rem; font-weight: 600; color: #1d4ed8; margin-right: 0.5rem; }
    .btn-sm-danger { color: #dc2626; border-color: #fecaca; }
    .btn-sm-danger:hover { background: #fef2f2; }
    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; text-decoration: underline;
    }
    .btn-link:hover { color: #2563eb; }
    .th-check { width: 40px; }
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
    .table tbody tr:hover { background: #f8fafc; }
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-planned { background: #f1f5f9; color: #64748b; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-maintenance { background: #fef9c3; color: #a16207; }
    .badge-retired { background: #fef2f2; color: #dc2626; }
    .tag-count { font-size: 0.75rem; color: #64748b; }
    .text-muted { color: #94a3b8; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
    .page-info { color: #64748b; font-size: 0.8125rem; }
  `],
})
export class CIListComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private tenantContext = inject(TenantContextService);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  cis = signal<ConfigurationItem[]>([]);
  totalCIs = signal(0);
  currentOffset = signal(0);
  pageSize = 50;
  searchTerm = '';
  selectedClassId = '';
  selectedState = '';
  classes = signal<CIClass[]>([]);

  classOptions = computed(() => this.classes().map(cls => ({ value: cls.id, label: cls.displayName })));

  readonly lifecycleStates = LIFECYCLE_STATES;

  selection = createTableSelection(this.cis, (ci) => ci.id);

  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadCIs();
    this.loadClasses();
  }

  onSearch(): void {
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.loadCIs();
    }, 300);
  }

  onFilterChange(): void {
    this.currentOffset.set(0);
    this.loadCIs();
  }

  loadCIs(): void {
    this.cmdbService.listCIs({
      search: this.searchTerm.trim() || undefined,
      ciClassId: this.selectedClassId || undefined,
      lifecycleState: this.selectedState || undefined,
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.cis.set(response.items);
        this.totalCIs.set(response.total);
      },
    });
  }

  loadClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => {
        this.classes.set(classes);
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadCIs();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadCIs();
  }

  goToDetail(ciId: string): void {
    this.router.navigate(['/cmdb', ciId]);
  }

  async bulkDelete(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Delete Configuration Items',
      message: `Delete ${ids.length} selected configuration item(s)? This action uses soft delete.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.cmdbService.deleteCI(id))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} configuration item(s) deleted`);
        this.selection.clear();
        this.loadCIs();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete configuration items');
      },
    });
  }

  objectKeys(obj: Record<string, unknown>): string[] {
    return Object.keys(obj);
  }
}
