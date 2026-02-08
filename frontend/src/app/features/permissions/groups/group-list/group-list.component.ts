/**
 * Overview: Flat group list with search, sort, bulk delete, and icon actions.
 * Architecture: Feature component for group management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/permission.service, app/shared/services/confirm.service, app/shared/services/toast.service
 * Concepts: RBAC, group management, flat list, bulk operations
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { PermissionService } from '@core/services/permission.service';
import { Group } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { createTableSelection } from '@shared/utils/table-selection';

@Component({
  selector: 'nimbus-group-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="group-list-page">
        <div class="page-header">
          <h1>Groups</h1>
          <div class="header-actions">
            @if (selection.selectedCount() > 0) {
              <button class="btn btn-danger btn-sm" (click)="bulkDelete()">
                Delete ({{ selection.selectedCount() }})
              </button>
            }
            <a routerLink="/users/groups/create" class="btn btn-primary">Create Group</a>
          </div>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            placeholder="Search by name or description..."
            class="search-input"
          />
        </div>

        <div class="table-container">
          @if (loading()) {
            <div class="empty-state">Loading groups...</div>
          } @else if (filteredGroups().length === 0) {
            <div class="empty-state">No groups found{{ searchTerm ? ' matching your search' : '. Create one to get started' }}.</div>
          } @else {
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
                  <th class="sortable" (click)="toggleSort('name')">
                    Name
                    @if (sortField() === 'name') {
                      <span class="sort-arrow">{{ sortDir() === 'asc' ? '&#9650;' : '&#9660;' }}</span>
                    }
                  </th>
                  <th>Description</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (group of filteredGroups(); track group.id) {
                  <tr>
                    <td class="td-check">
                      <input
                        type="checkbox"
                        [checked]="selection.isSelected(group.id)"
                        (change)="selection.toggle(group.id)"
                      />
                    </td>
                    <td class="name-cell">{{ group.name }}</td>
                    <td class="desc-cell">{{ group.description || '\u2014' }}</td>
                    <td>
                      <a [routerLink]="['/users/groups', group.id]" class="icon-btn" title="View">
                        <nimbus-icon name="eye" />
                      </a>
                      <button class="icon-btn icon-btn-danger" title="Delete" (click)="deleteGroup(group)">
                        <nimbus-icon name="trash" />
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .group-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-actions { display: flex; gap: 0.75rem; align-items: center; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      text-decoration: none; display: inline-block;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem; border: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-danger {
      background: #ef4444; color: #fff; padding: 0.5rem 1rem; border: none;
    }
    .btn-danger:hover { background: #dc2626; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .filters { margin-bottom: 1rem; }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .table-container {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em; background: #fafbfc;
    }
    .table tbody tr:hover { background: #f8fafc; }
    .th-check, .td-check { width: 40px; text-align: center; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .desc-cell { color: #64748b; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sortable { cursor: pointer; user-select: none; }
    .sortable:hover { color: #3b82f6; }
    .sort-arrow { font-size: 0.625rem; margin-left: 0.25rem; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; font-size: 0.8125rem; }
  `],
})
export class GroupListComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  groups = signal<Group[]>([]);
  loading = signal(true);
  searchTerm = '';
  sortField = signal<'name'>('name');
  sortDir = signal<'asc' | 'desc'>('asc');

  selection = createTableSelection<Group>(this.groups, (g) => g.id);

  filteredGroups = computed(() => {
    let list = this.groups();
    const term = this.searchTerm.toLowerCase().trim();
    if (term) {
      list = list.filter(
        (g) =>
          g.name.toLowerCase().includes(term) ||
          (g.description?.toLowerCase().includes(term) ?? false),
      );
    }
    const dir = this.sortDir() === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => a.name.localeCompare(b.name) * dir);
  });

  ngOnInit(): void {
    this.loadGroups();
  }

  toggleSort(field: 'name'): void {
    if (this.sortField() === field) {
      this.sortDir.update((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      this.sortField.set(field);
      this.sortDir.set('asc');
    }
  }

  async deleteGroup(group: Group): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Group',
      message: `Delete group "${group.name}"? This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.deleteGroup(group.id).subscribe({
      next: () => {
        this.toastService.success(`Group "${group.name}" deleted`);
        this.loadGroups();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete group');
      },
    });
  }

  async bulkDelete(): Promise<void> {
    const ids = [...this.selection.selectedIds()];
    const ok = await this.confirmService.confirm({
      title: 'Delete Groups',
      message: `Delete ${ids.length} selected group(s)? This action cannot be undone.`,
      confirmLabel: 'Delete All',
      variant: 'danger',
    });
    if (!ok) return;
    forkJoin(ids.map((id) => this.permissionService.deleteGroup(id))).subscribe({
      next: () => {
        this.toastService.success(`Deleted ${ids.length} group(s)`);
        this.selection.clear();
        this.loadGroups();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete some groups');
        this.loadGroups();
      },
    });
  }

  private loadGroups(): void {
    this.permissionService.listGroups().subscribe({
      next: (groups) => {
        this.groups.set(groups);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
