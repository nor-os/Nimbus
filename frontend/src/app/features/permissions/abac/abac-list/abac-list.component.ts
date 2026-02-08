/**
 * Overview: ABAC policy list with search filtering, sortable columns, inline toggle, bulk operations, and CRUD actions.
 * Architecture: Feature component for ABAC policy management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/permission.service
 * Concepts: ABAC, attribute-based access control, policy management, search, column sorting, bulk selection
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { PermissionService } from '@core/services/permission.service';
import { ABACPolicy } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { createTableSelection, TableSelection } from '@shared/utils/table-selection';

type SortColumn = 'name' | 'effect' | 'expression' | 'priority' | 'enabled' | 'created_at';
type SortDirection = 'asc' | 'desc';

@Component({
  selector: 'nimbus-abac-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="abac-list-page">
        <div class="page-header">
          <h1>ABAC Policies</h1>
          <a routerLink="/permissions/abac/create" class="btn btn-primary">Create Policy</a>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
            placeholder="Search by name, effect, or expression..."
            class="search-input"
          />
        </div>

        @if (selection.selectedCount() > 0) {
          <div class="bulk-toolbar">
            <span class="bulk-count">{{ selection.selectedCount() }} selected</span>
            <button class="btn btn-sm" (click)="bulkEnable()">Enable Selected</button>
            <button class="btn btn-sm" (click)="bulkDisable()">Disable Selected</button>
            <button class="btn btn-sm btn-sm-danger" (click)="bulkDelete()">Delete Selected</button>
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
                <th class="sortable" (click)="onSort('name')">
                  Name <span class="sort-icon">{{ getSortIcon('name') }}</span>
                </th>
                <th class="sortable" (click)="onSort('effect')">
                  Effect <span class="sort-icon">{{ getSortIcon('effect') }}</span>
                </th>
                <th class="sortable" (click)="onSort('expression')">
                  Expression <span class="sort-icon">{{ getSortIcon('expression') }}</span>
                </th>
                <th class="sortable" (click)="onSort('priority')">
                  Priority <span class="sort-icon">{{ getSortIcon('priority') }}</span>
                </th>
                <th class="sortable" (click)="onSort('enabled')">
                  Enabled <span class="sort-icon">{{ getSortIcon('enabled') }}</span>
                </th>
                <th class="sortable" (click)="onSort('created_at')">
                  Created <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (policy of displayedPolicies(); track policy.id) {
                <tr>
                  <td>
                    <input
                      type="checkbox"
                      [checked]="selection.isSelected(policy.id)"
                      (change)="selection.toggle(policy.id)"
                    />
                  </td>
                  <td class="name-cell">{{ policy.name }}</td>
                  <td>
                    <span class="badge" [class.badge-allow]="policy.effect === 'allow'" [class.badge-deny]="policy.effect === 'deny'">
                      {{ policy.effect }}
                    </span>
                  </td>
                  <td class="expr-cell" [title]="policy.expression">{{ truncateExpr(policy.expression) }}</td>
                  <td>{{ policy.priority }}</td>
                  <td>
                    <button
                      class="toggle-btn"
                      [class.toggle-on]="policy.is_enabled"
                      [class.toggle-off]="!policy.is_enabled"
                      (click)="toggleEnabled(policy)"
                      [title]="policy.is_enabled ? 'Disable policy' : 'Enable policy'"
                    >
                      <span class="toggle-knob"></span>
                    </button>
                  </td>
                  <td>{{ policy.created_at | date: 'medium' }}</td>
                  <td class="actions">
                    <a [routerLink]="['/permissions/abac', policy.id]" class="icon-btn" title="Edit">
                      <nimbus-icon name="pencil" />
                    </a>
                    <button class="icon-btn icon-btn-danger" title="Delete" (click)="onDelete(policy)">
                      <nimbus-icon name="trash" />
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="8" class="empty-state">No ABAC policies found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .abac-list-page { padding: 0; }
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
    .filters { margin-bottom: 1rem; }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .bulk-toolbar {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem;
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 1rem;
    }
    .bulk-count { font-size: 0.8125rem; font-weight: 600; color: #1d4ed8; margin-right: 0.5rem; }
    .btn-sm { padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem; font-family: inherit; }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm-danger { color: #dc2626; border-color: #fecaca; }
    .btn-sm-danger:hover { background: #fef2f2; }
    .th-check { width: 40px; }
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table th.sortable { cursor: pointer; user-select: none; }
    .table th.sortable:hover { color: #3b82f6; }
    .sort-icon { font-size: 0.625rem; margin-left: 0.25rem; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .expr-cell {
      font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.75rem;
      color: #64748b; max-width: 240px; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap;
    }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: uppercase;
    }
    .badge-allow { background: #dcfce7; color: #16a34a; }
    .badge-deny { background: #fef2f2; color: #dc2626; }
    .toggle-btn {
      width: 36px; height: 20px; border-radius: 10px; border: none;
      cursor: pointer; position: relative; transition: background 0.2s;
      padding: 0;
    }
    .toggle-on { background: #3b82f6; }
    .toggle-off { background: #cbd5e1; }
    .toggle-knob {
      position: absolute; top: 2px; width: 16px; height: 16px;
      border-radius: 50%; background: #fff; transition: left 0.2s;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    .toggle-on .toggle-knob { left: 18px; }
    .toggle-off .toggle-knob { left: 2px; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class ABACListComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  policies = signal<ABACPolicy[]>([]);
  searchTerm = '';
  sortColumn = signal<SortColumn>('name');
  sortDirection = signal<SortDirection>('asc');

  displayedPolicies = computed(() => {
    let items = this.policies();
    const term = this.searchTerm.toLowerCase().trim();
    if (term) {
      items = items.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.effect.toLowerCase().includes(term) ||
          p.expression.toLowerCase().includes(term),
      );
    }
    const col = this.sortColumn();
    const dir = this.sortDirection();
    return [...items].sort((a, b) => {
      const valA = this.getSortValue(a, col);
      const valB = this.getSortValue(b, col);
      const cmp = typeof valA === 'number' && typeof valB === 'number'
        ? valA - valB
        : String(valA).localeCompare(String(valB));
      return dir === 'asc' ? cmp : -cmp;
    });
  });

  selection = createTableSelection(this.displayedPolicies, (p) => p.id);

  ngOnInit(): void {
    this.loadPolicies();
  }

  onSearch(): void {
    this.policies.update((p) => [...p]);
  }

  onSort(column: SortColumn): void {
    if (this.sortColumn() === column) {
      this.sortDirection.update((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      this.sortColumn.set(column);
      this.sortDirection.set('asc');
    }
  }

  getSortIcon(column: SortColumn): string {
    if (this.sortColumn() !== column) return '\u2195';
    return this.sortDirection() === 'asc' ? '\u2191' : '\u2193';
  }

  truncateExpr(expr: string): string {
    return expr.length > 60 ? expr.substring(0, 57) + '...' : expr;
  }

  toggleEnabled(policy: ABACPolicy): void {
    this.permissionService
      .updateABACPolicy(policy.id, { is_enabled: !policy.is_enabled })
      .subscribe({
        next: (updated) => {
          this.policies.update((list) =>
            list.map((p) => (p.id === updated.id ? updated : p)),
          );
          this.toastService.success(`Policy "${policy.name}" ${updated.is_enabled ? 'enabled' : 'disabled'}`);
        },
        error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to toggle policy'),
      });
  }

  async onDelete(policy: ABACPolicy): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete ABAC Policy',
      message: `Are you sure you want to delete policy "${policy.name}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.deleteABACPolicy(policy.id).subscribe({
      next: () => {
        this.toastService.success(`Policy "${policy.name}" deleted`);
        this.loadPolicies();
      },
      error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete policy'),
    });
  }

  async bulkEnable(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    forkJoin(ids.map((id) => this.permissionService.updateABACPolicy(id, { is_enabled: true }))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} policy/policies enabled`);
        this.selection.clear();
        this.loadPolicies();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to enable policies');
      },
    });
  }

  async bulkDisable(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    forkJoin(ids.map((id) => this.permissionService.updateABACPolicy(id, { is_enabled: false }))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} policy/policies disabled`);
        this.selection.clear();
        this.loadPolicies();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to disable policies');
      },
    });
  }

  async bulkDelete(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Delete ABAC Policies',
      message: `Delete ${ids.length} selected policy/policies?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.permissionService.deleteABACPolicy(id))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} policy/policies deleted`);
        this.selection.clear();
        this.loadPolicies();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete policies');
      },
    });
  }

  loadPolicies(): void {
    this.permissionService.listABACPolicies().subscribe({
      next: (policies) => this.policies.set(policies),
    });
  }

  private getSortValue(policy: ABACPolicy, col: SortColumn): string | number {
    switch (col) {
      case 'name':
        return policy.name.toLowerCase();
      case 'effect':
        return policy.effect;
      case 'expression':
        return policy.expression.toLowerCase();
      case 'priority':
        return policy.priority;
      case 'enabled':
        return policy.is_enabled ? '1' : '0';
      case 'created_at':
        return policy.created_at;
    }
  }
}
