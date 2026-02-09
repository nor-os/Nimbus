/**
 * Overview: User list page with search filtering, sortable columns, pagination, status badges, bulk operations, and CRUD navigation.
 * Architecture: Feature component for user management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/user.service, rxjs, @shared/utils/table-selection
 * Concepts: User management, tenant-scoped users, paginated listing, search, column sorting, bulk selection, local IdP gating
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { UserService } from '@core/services/user.service';
import { User } from '@core/models/user.model';
import { PermissionService } from '@core/services/permission.service';
import { IdentityProviderService } from '@core/services/identity-provider.service';
import { Role } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { createTableSelection } from '@shared/utils/table-selection';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { DialogService } from '@shared/services/dialog.service';
import { AssignRoleDialogComponent } from '@shared/components/assign-role-dialog/assign-role-dialog.component';

type SortColumn = 'email' | 'display_name' | 'status' | 'created_at';
type SortDirection = 'asc' | 'desc';

@Component({
  selector: 'nimbus-user-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="user-list-page">
        <div class="page-header">
          <h1>Users</h1>
          @if (hasLocalAuth()) {
            <a routerLink="/users/create" class="btn btn-primary">Create User</a>
          } @else {
            <span class="btn btn-primary btn-disabled" title="This tenant has no local authentication provider configured">Create User</span>
          }
        </div>

        @if (!hasLocalAuth()) {
          <div class="info-banner">
            Local authentication is not configured for this tenant. Users can only be provisioned via SSO or SCIM.
          </div>
        }

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
            placeholder="Search by email or name..."
            class="search-input"
          />
        </div>

        @if (selection.selectedCount() > 0) {
          <div class="bulk-toolbar">
            <span class="bulk-count">{{ selection.selectedCount() }} selected</span>
            <button class="btn btn-sm" (click)="bulkAssignRole()">Assign Role</button>
            <button class="btn btn-sm" (click)="bulkActivate()">Activate</button>
            <button class="btn btn-sm btn-sm-danger" (click)="bulkDeactivate()">Deactivate</button>
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
                <th class="sortable" (click)="onSort('email')">
                  Email <span class="sort-icon">{{ getSortIcon('email') }}</span>
                </th>
                <th class="sortable" (click)="onSort('display_name')">
                  Display Name <span class="sort-icon">{{ getSortIcon('display_name') }}</span>
                </th>
                <th class="sortable" (click)="onSort('status')">
                  Status <span class="sort-icon">{{ getSortIcon('status') }}</span>
                </th>
                <th class="sortable" (click)="onSort('created_at')">
                  Created <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (user of displayedUsers(); track user.id) {
                <tr>
                  <td>
                    <input
                      type="checkbox"
                      [checked]="selection.isSelected(user.id)"
                      (change)="selection.toggle(user.id)"
                    />
                  </td>
                  <td class="email-cell">{{ user.email }}</td>
                  <td>{{ user.display_name || '\u2014' }}</td>
                  <td>
                    <span class="badge" [class.badge-active]="user.is_active" [class.badge-inactive]="!user.is_active">
                      {{ user.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ user.created_at | date: 'medium' }}</td>
                  <td class="actions">
                    <a [routerLink]="['/users', user.id]" class="icon-btn" title="View">
                      <nimbus-icon name="eye" />
                    </a>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="6" class="empty-state">No users found</td>
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
            Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + users().length }}
            of {{ totalUsers() }}
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + users().length >= totalUsers()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .user-list-page { padding: 0; }
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
    .btn-disabled {
      opacity: 0.5; cursor: not-allowed; display: inline-block;
    }
    .btn-disabled:hover { background: #3b82f6; }
    .info-banner {
      padding: 0.625rem 0.875rem; margin-bottom: 1rem; font-size: 0.8125rem;
      color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px;
    }
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
    .btn-sm-danger { color: #dc2626; border-color: #fecaca; }
    .btn-sm-danger:hover { background: #fef2f2; }
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
    .table th { font-weight: 600; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .table th.sortable { cursor: pointer; user-select: none; }
    .table th.sortable:hover { color: #3b82f6; }
    .sort-icon { font-size: 0.625rem; margin-left: 0.25rem; }
    .table tbody tr:hover { background: #f8fafc; }
    .email-cell { font-weight: 500; color: #1e293b; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
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
export class UserListComponent implements OnInit {
  private userService = inject(UserService);
  private permissionService = inject(PermissionService);
  private idpService = inject(IdentityProviderService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private dialogService = inject(DialogService);

  users = signal<User[]>([]);
  totalUsers = signal(0);
  currentOffset = signal(0);
  hasLocalAuth = signal(true); // optimistic default, updated on init
  searchTerm = '';
  pageSize = 50;
  sortColumn = signal<SortColumn>('email');
  sortDirection = signal<SortDirection>('asc');

  displayedUsers = computed(() => {
    const items = this.users();
    const col = this.sortColumn();
    const dir = this.sortDirection();
    return [...items].sort((a, b) => {
      const valA = this.getSortValue(a, col);
      const valB = this.getSortValue(b, col);
      const cmp = valA.localeCompare(valB);
      return dir === 'asc' ? cmp : -cmp;
    });
  });

  selection = createTableSelection(this.displayedUsers, (u) => u.id);

  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadUsers();
    this.checkLocalAuth();
  }

  onSearch(): void {
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.loadUsers();
    }, 300);
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

  loadUsers(): void {
    const search = this.searchTerm.trim() || undefined;
    this.userService.listUsers(this.currentOffset(), this.pageSize, search).subscribe({
      next: (response) => {
        this.users.set(response.items);
        this.totalUsers.set(response.total);
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadUsers();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadUsers();
  }

  async bulkAssignRole(): Promise<void> {
    const role = await this.dialogService.open<Role | undefined>(
      AssignRoleDialogComponent,
      {},
    );
    if (!role) return;
    const ids = [...this.selection.selectedIds()];
    forkJoin(ids.map((id) => this.permissionService.assignRole(id, role.id))).subscribe({
      next: () => {
        this.toastService.success(`Role "${role.name}" assigned to ${ids.length} user(s)`);
        this.selection.clear();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to assign role');
      },
    });
  }

  async bulkActivate(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Activate Users',
      message: `Activate ${ids.length} selected user(s)?`,
      confirmLabel: 'Activate',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.userService.updateUser(id, { is_active: true }))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} user(s) activated`);
        this.selection.clear();
        this.loadUsers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to activate users');
      },
    });
  }

  async bulkDeactivate(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Deactivate Users',
      message: `Deactivate ${ids.length} selected user(s)?`,
      confirmLabel: 'Deactivate',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.userService.updateUser(id, { is_active: false }))).subscribe({
      next: () => {
        this.toastService.success(`${ids.length} user(s) deactivated`);
        this.selection.clear();
        this.loadUsers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to deactivate users');
      },
    });
  }

  private checkLocalAuth(): void {
    this.idpService.listProviders().subscribe({
      next: (providers) => {
        this.hasLocalAuth.set(providers.some((p) => p.idp_type === 'local' && p.is_enabled));
      },
      error: () => {
        // On error, keep optimistic default
      },
    });
  }

  private getSortValue(user: User, col: SortColumn): string {
    switch (col) {
      case 'email':
        return user.email.toLowerCase();
      case 'display_name':
        return (user.display_name ?? '').toLowerCase();
      case 'status':
        return user.is_active ? '1' : '0';
      case 'created_at':
        return user.created_at;
    }
  }
}
