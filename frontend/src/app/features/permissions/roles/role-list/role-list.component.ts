/**
 * Overview: Role list page with search filtering, sortable columns, bulk selection, and CRUD actions.
 * Architecture: Feature component for role management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/permission.service
 * Concepts: RBAC, role management, search filtering, column sorting, bulk operations
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { PermissionService } from '@core/services/permission.service';
import { Role } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { createTableSelection } from '@shared/utils/table-selection';

type SortColumn = 'name' | 'scope' | 'type' | 'description' | 'created_at';
type SortDirection = 'asc' | 'desc';

@Component({
  selector: 'nimbus-role-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="role-list-page">
        <div class="page-header">
          <h1>Roles</h1>
          <a routerLink="/users/roles/create" class="btn btn-primary">Create Role</a>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
            placeholder="Search by name, scope, or description..."
            class="search-input"
          />
        </div>

        @if (selection.selectedCount() > 0) {
          <div class="bulk-toolbar">
            <span class="bulk-count">{{ selection.selectedCount() }} selected</span>
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
                <th class="sortable" (click)="onSort('scope')">
                  Scope <span class="sort-icon">{{ getSortIcon('scope') }}</span>
                </th>
                <th class="sortable" (click)="onSort('type')">
                  Type <span class="sort-icon">{{ getSortIcon('type') }}</span>
                </th>
                <th class="sortable" (click)="onSort('description')">
                  Description <span class="sort-icon">{{ getSortIcon('description') }}</span>
                </th>
                <th class="sortable" (click)="onSort('created_at')">
                  Created <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (role of displayedRoles(); track role.id) {
                <tr>
                  <td>
                    <input
                      type="checkbox"
                      [checked]="selection.isSelected(role.id)"
                      (change)="selection.toggle(role.id)"
                    />
                  </td>
                  <td class="name-cell">{{ role.name }}</td>
                  <td>
                    <span class="badge" [class]="'badge-scope-' + role.scope">
                      {{ getScopeLabel(role.scope) }}
                    </span>
                  </td>
                  <td>
                    <span class="badge" [class.badge-system]="role.is_system" [class.badge-custom]="!role.is_system">
                      {{ role.is_system ? 'System' : 'Custom' }}
                    </span>
                  </td>
                  <td class="desc-cell">{{ role.description || '\u2014' }}</td>
                  <td>{{ role.created_at | date: 'medium' }}</td>
                  <td class="actions">
                    <a [routerLink]="['/users/roles', role.id]" class="icon-btn" title="View">
                      <nimbus-icon name="eye" />
                    </a>
                    @if (!role.is_system) {
                      <button class="icon-btn icon-btn-danger" title="Delete" (click)="onDelete(role)">
                        <nimbus-icon name="trash" />
                      </button>
                    }
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="empty-state">No roles found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .role-list-page { padding: 0; }
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
    .desc-cell { color: #64748b; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .text-muted { color: #94a3b8; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-scope-provider { background: #fef2f2; color: #dc2626; }
    .badge-scope-tenant { background: #dbeafe; color: #1d4ed8; }
    .badge-system { background: #dbeafe; color: #1d4ed8; }
    .badge-custom { background: #f1f5f9; color: #64748b; }
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
export class RoleListComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  roles = signal<Role[]>([]);
  searchTerm = '';
  sortColumn = signal<SortColumn>('name');
  sortDirection = signal<SortDirection>('asc');

  displayedRoles = computed(() => {
    let items = this.roles();
    const term = this.searchTerm.toLowerCase().trim();
    if (term) {
      items = items.filter(
        (r) =>
          r.name.toLowerCase().includes(term) ||
          r.scope.toLowerCase().includes(term) ||
          (r.description?.toLowerCase().includes(term) ?? false),
      );
    }
    const col = this.sortColumn();
    const dir = this.sortDirection();
    return [...items].sort((a, b) => {
      const valA = this.getSortValue(a, col);
      const valB = this.getSortValue(b, col);
      const cmp = valA.localeCompare(valB);
      return dir === 'asc' ? cmp : -cmp;
    });
  });

  selection = createTableSelection(this.displayedRoles, (r) => r.id);

  ngOnInit(): void {
    this.loadRoles();
  }

  onSearch(): void {
    this.roles.update((r) => [...r]);
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

  getScopeLabel(scope: string): string {
    const labels: Record<string, string> = {
      provider: 'Provider',
      tenant: 'Tenant',
    };
    return labels[scope] ?? scope;
  }

  async onDelete(role: Role): Promise<void> {
    if (role.is_system) return;
    const ok = await this.confirmService.confirm({
      title: 'Delete Role',
      message: `Are you sure you want to delete role "${role.name}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.deleteRole(role.id).subscribe({
      next: () => {
        this.toastService.success(`Role "${role.name}" deleted`);
        this.loadRoles();
      },
      error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete role'),
    });
  }

  async bulkDelete(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const customIds = ids.filter((id) => {
      const role = this.roles().find((r) => r.id === id);
      return role && !role.is_system;
    });
    if (customIds.length === 0) {
      this.toastService.error('No custom roles selected — system roles cannot be deleted');
      return;
    }
    const ok = await this.confirmService.confirm({
      title: 'Delete Roles',
      message: `Delete ${customIds.length} custom role(s)?` + (customIds.length < ids.length ? ` (${ids.length - customIds.length} system role(s) will be skipped)` : ''),
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(customIds.map((id) => this.permissionService.deleteRole(id))).subscribe({
      next: () => {
        this.toastService.success(`${customIds.length} role(s) deleted`);
        this.selection.clear();
        this.loadRoles();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete roles');
      },
    });
  }

  loadRoles(): void {
    this.permissionService.listRoles().subscribe({
      next: (roles) => this.roles.set(roles),
    });
  }

  private getSortValue(role: Role, col: SortColumn): string {
    switch (col) {
      case 'name':
        return role.name.toLowerCase();
      case 'scope':
        return role.scope.toLowerCase();
      case 'type':
        return role.is_system ? 'system' : 'custom';
      case 'description':
        return (role.description ?? '').toLowerCase();
      case 'created_at':
        return role.created_at;
    }
  }
}
