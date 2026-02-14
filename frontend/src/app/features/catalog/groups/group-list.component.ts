/**
 * Overview: Service group list — table-based view with status filter, create form, and
 *     clickable rows that navigate to the group detail page.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router,
 *     app/core/services/catalog.service
 * Concepts: Service group lifecycle (draft/published/archived), status filter, table list
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
import { CatalogService } from '@core/services/catalog.service';
import { ServiceGroup } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-group-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="groups-page">
        <div class="page-header">
          <h1>Service Groups</h1>
          <button
            *nimbusHasPermission="'catalog:group:manage'"
            class="btn btn-primary"
            (click)="showCreateForm()"
          >
            + Create Group
          </button>
        </div>

        <!-- Create group form -->
        @if (creating()) {
          <div class="form-card">
            <h2 class="form-title">New Service Group</h2>
            <div class="form-group">
              <label class="form-label">Name *</label>
              <input
                class="form-input"
                [(ngModel)]="formName"
                placeholder="e.g. core-compute"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Display Name</label>
              <input
                class="form-input"
                [(ngModel)]="formDisplayName"
                placeholder="e.g. Core Compute Services"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <textarea
                class="form-input form-textarea"
                [(ngModel)]="formDescription"
                placeholder="Optional description..."
                rows="3"
              ></textarea>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" (click)="cancelCreate()">Cancel</button>
              <button
                class="btn btn-primary"
                (click)="createGroup()"
                [disabled]="!formName.trim()"
              >
                Create
              </button>
            </div>
          </div>
        }

        <!-- Status filter -->
        <div class="filters">
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
          <div class="loading">Loading service groups...</div>
        }

        @if (!loading()) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Display Name</th>
                  <th>Status</th>
                  <th>Items</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                @for (group of groups(); track group.id) {
                  <tr class="clickable-row" (click)="goToDetail(group.id)">
                    <td class="name-cell">
                      <button
                        class="expand-btn"
                        [class.expanded]="expandedGroups().has(group.id)"
                        (click)="toggleExpand(group.id, $event)"
                        [disabled]="group.items.length === 0"
                        [attr.aria-label]="expandedGroups().has(group.id) ? 'Collapse' : 'Expand'"
                      >
                        <span class="expand-icon">&#9654;</span>
                      </button>
                      {{ group.name }}
                    </td>
                    <td>{{ group.displayName || '\u2014' }}</td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-draft]="group.status === 'draft'"
                        [class.badge-published]="group.status === 'published'"
                        [class.badge-archived]="group.status === 'archived'"
                      >
                        {{ group.status | titlecase }}
                      </span>
                    </td>
                    <td class="mono">{{ group.items.length }}</td>
                    <td>{{ group.updatedAt | date: 'medium' }}</td>
                  </tr>
                  @if (expandedGroups().has(group.id) && group.items.length > 0) {
                    <tr class="expand-row">
                      <td colspan="5" class="expand-cell">
                        <div class="group-items">
                          <div class="group-items-header">
                            <span class="col-name">Offering</span>
                            <span class="col-required">Required</span>
                            <span class="col-order">Order</span>
                          </div>
                          @for (item of group.items; track item.id) {
                            <div class="group-item-row">
                              <span class="col-name">{{ item.offeringName || item.serviceOfferingId }}</span>
                              <span class="col-required">
                                <span class="req-badge" [class.req-yes]="item.isRequired" [class.req-no]="!item.isRequired">
                                  {{ item.isRequired ? 'Yes' : 'No' }}
                                </span>
                              </span>
                              <span class="col-order mono">{{ item.sortOrder }}</span>
                            </div>
                          }
                        </div>
                      </td>
                    </tr>
                  }
                } @empty {
                  <tr>
                    <td colspan="5" class="empty-state">
                      {{ creating() ? '' : 'No service groups found.' }}
                    </td>
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
                Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + groups().length }}
                of {{ total() }}
              } @else {
                No items
              }
            </span>
            <button
              class="btn btn-sm"
              [disabled]="currentOffset() + groups().length >= total()"
              (click)="nextPage()"
            >Next</button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .groups-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Create form ------------------------------------------------ */
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
    .form-textarea { resize: vertical; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }

    /* -- Filters ---------------------------------------------------- */
    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem;
    }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b;
      font-family: inherit; cursor: pointer; min-width: 160px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }

    /* -- Table ------------------------------------------------------ */
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
    .name-cell { font-weight: 500; color: #1e293b; display: flex; align-items: center; gap: 0.5rem; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }

    /* -- Expand button ---------------------------------------------- */
    .expand-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 20px; height: 20px; padding: 0; border: none; background: transparent;
      cursor: pointer; border-radius: 4px; flex-shrink: 0;
      transition: background 0.15s;
    }
    .expand-btn:hover { background: #e2e8f0; }
    .expand-btn:disabled { opacity: 0.25; cursor: default; }
    .expand-btn:disabled:hover { background: transparent; }
    .expand-icon {
      font-size: 0.625rem; color: #64748b; display: inline-block;
      transition: transform 0.15s;
    }
    .expand-btn.expanded .expand-icon { transform: rotate(90deg); }

    /* -- Expanded row ----------------------------------------------- */
    .expand-row:hover { background: transparent !important; }
    .expand-row td { padding: 0; border-bottom: 1px solid #f1f5f9; }
    .expand-cell { background: #f8fafc; }
    .group-items {
      padding: 0.5rem 1rem 0.5rem 3rem;
      font-size: 0.8125rem;
    }
    .group-items-header {
      display: flex; gap: 1rem; padding: 0.25rem 0;
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 1px solid #e2e8f0; margin-bottom: 0.25rem;
    }
    .group-item-row {
      display: flex; gap: 1rem; padding: 0.375rem 0;
      border-bottom: 1px solid #f1f5f9; color: #374151;
    }
    .group-item-row:last-child { border-bottom: none; }
    .col-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .col-required { width: 70px; text-align: center; }
    .col-order { width: 50px; text-align: center; }
    .req-badge {
      padding: 0.0625rem 0.375rem; border-radius: 8px;
      font-size: 0.6875rem; font-weight: 500;
    }
    .req-yes { background: #dcfce7; color: #166534; }
    .req-no { background: #fef3c7; color: #92400e; }

    /* -- Badges ----------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-archived { background: #f1f5f9; color: #64748b; }

    /* -- Pagination ------------------------------------------------- */
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .page-info { color: #64748b; font-size: 0.8125rem; }

    /* -- Buttons ---------------------------------------------------- */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
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
export class GroupListComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  groups = signal<ServiceGroup[]>([]);
  loading = signal(false);
  creating = signal(false);
  total = signal(0);
  currentOffset = signal(0);
  expandedGroups = signal<Set<string>>(new Set());
  pageSize = 50;
  statusFilter = '';

  // Create form fields
  formName = '';
  formDisplayName = '';
  formDescription = '';

  ngOnInit(): void {
    this.loadGroups();
  }

  // -- Filtering / pagination ------------------------------------

  onFilterChange(): void {
    this.currentOffset.set(0);
    this.loadGroups();
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadGroups();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadGroups();
  }

  // -- Expand / collapse ------------------------------------------

  toggleExpand(groupId: string, event: Event): void {
    event.stopPropagation();
    const next = new Set(this.expandedGroups());
    if (next.has(groupId)) {
      next.delete(groupId);
    } else {
      next.add(groupId);
    }
    this.expandedGroups.set(next);
  }

  // -- Navigate to detail ----------------------------------------

  goToDetail(groupId: string): void {
    this.router.navigate(['/catalog', 'groups', groupId]);
  }

  // -- Create group -----------------------------------------------

  showCreateForm(): void {
    this.resetCreateForm();
    this.creating.set(true);
  }

  cancelCreate(): void {
    this.creating.set(false);
    this.resetCreateForm();
  }

  createGroup(): void {
    const input: { name: string; displayName?: string; description?: string } = {
      name: this.formName.trim(),
    };
    if (this.formDisplayName.trim()) {
      input.displayName = this.formDisplayName.trim();
    }
    if (this.formDescription.trim()) {
      input.description = this.formDescription.trim();
    }

    this.catalogService.createGroup(input).subscribe({
      next: (created) => {
        this.toastService.success(`Service group "${created.displayName || created.name}" created`);
        this.cancelCreate();
        this.loadGroups();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create service group');
      },
    });
  }

  // -- Private loaders --------------------------------------------

  private loadGroups(): void {
    this.loading.set(true);
    this.catalogService.listGroups(
      this.currentOffset(),
      this.pageSize,
      this.statusFilter || undefined,
    ).subscribe({
      next: (response) => {
        this.groups.set(response.items);
        this.total.set(response.total);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load service groups');
      },
    });
  }

  private resetCreateForm(): void {
    this.formName = '';
    this.formDisplayName = '';
    this.formDescription = '';
  }
}
