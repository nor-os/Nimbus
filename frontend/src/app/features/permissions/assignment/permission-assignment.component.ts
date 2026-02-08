/**
 * Overview: Per-user effective permission view with inheritance visualization and deny status.
 * Architecture: Feature component for permission inspection (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/permission.service, app/core/services/user.service
 * Concepts: Effective permissions, tenant hierarchy inheritance, deny overrides, permission auditing
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { UserService } from '@core/services/user.service';
import { EffectivePermission } from '@core/models/permission.model';
import { UserDetail } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

type FilterMode = 'all' | 'inherited' | 'direct' | 'denied';

@Component({
  selector: 'nimbus-permission-assignment',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="assignment-page">
        <div class="page-header">
          <div class="header-left">
            <button class="btn btn-secondary" (click)="goBack()">&#8592; Back</button>
            <h1>Effective Permissions</h1>
          </div>
        </div>

        @if (user()) {
          <div class="user-card">
            <div class="user-info">
              <span class="user-name">{{ user()!.display_name || user()!.email }}</span>
              <span class="user-email">{{ user()!.email }}</span>
            </div>
            <span class="badge" [class.badge-active]="user()!.is_active" [class.badge-inactive]="!user()!.is_active">
              {{ user()!.is_active ? 'Active' : 'Inactive' }}
            </span>
          </div>
        }

        <div class="summary-bar">
          <span class="summary-stat">{{ allPermissions().length }} permissions</span>
          <span class="summary-divider">|</span>
          <span class="summary-stat stat-inherited">{{ inheritedCount() }} inherited</span>
          <span class="summary-divider">|</span>
          <span class="summary-stat stat-direct">{{ directCount() }} direct</span>
          <span class="summary-divider">|</span>
          <span class="summary-stat stat-denied">{{ deniedCount() }} denied</span>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="applyFilters()"
            placeholder="Filter by permission key or source..."
            class="search-input"
          />
          <select [(ngModel)]="filterMode" (ngModelChange)="applyFilters()" class="filter-select">
            <option value="all">All</option>
            <option value="inherited">Inherited</option>
            <option value="direct">Direct</option>
            <option value="denied">Denied</option>
          </select>
          <span class="result-count">{{ filteredPermissions().length }} result(s)</span>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Permission Key</th>
                <th>Source</th>
                <th>Tenant</th>
                <th>Inherited</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              @for (perm of filteredPermissions(); track perm.permission_key) {
                <tr [class.row-denied]="perm.is_denied" [class.row-inherited]="perm.is_inherited && !perm.is_denied">
                  <td class="key-cell" [class.key-denied]="perm.is_denied">{{ perm.permission_key }}</td>
                  <td>
                    <span class="badge badge-source">{{ perm.source }}</span>
                  </td>
                  <td class="tenant-cell">{{ perm.source_tenant_name || '\u2014' }}</td>
                  <td>
                    @if (perm.is_inherited) {
                      <span class="inherit-icon" title="Inherited from parent tenant">&#128279;</span>
                    } @else {
                      <span class="text-muted">&mdash;</span>
                    }
                  </td>
                  <td>
                    @if (perm.is_denied) {
                      <span class="badge badge-denied" [title]="perm.deny_source || 'Denied'">Denied</span>
                    } @else {
                      <span class="badge badge-allowed">Allowed</span>
                    }
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="empty-state">
                    @if (loading()) {
                      Loading permissions...
                    } @else {
                      No permissions found
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .assignment-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 1rem; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1rem;
      border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .user-card {
      display: flex; justify-content: space-between; align-items: center;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .user-info { display: flex; flex-direction: column; gap: 0.125rem; }
    .user-name { font-weight: 600; color: #1e293b; font-size: 0.9375rem; }
    .user-email { color: #64748b; font-size: 0.8125rem; }
    .summary-bar {
      display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.25rem;
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1rem; font-size: 0.8125rem;
    }
    .summary-stat { font-weight: 600; color: #1e293b; }
    .summary-divider { color: #cbd5e1; }
    .stat-inherited { color: #6366f1; }
    .stat-direct { color: #059669; }
    .stat-denied { color: #dc2626; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }
    .badge-source { background: #f3e8ff; color: #7c3aed; font-size: 0.625rem; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .badge-allowed { background: #dcfce7; color: #16a34a; }
    .badge-denied { background: #fef2f2; color: #dc2626; }
    .filters {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;
    }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 280px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; font-family: inherit; cursor: pointer;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }
    .result-count { color: #64748b; font-size: 0.8125rem; }
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
    .table tbody tr:hover { background: #f8fafc; }
    .row-denied { background: #fff5f5; }
    .row-denied:hover { background: #fef2f2 !important; }
    .row-inherited { color: #64748b; }
    .key-cell { font-weight: 500; color: #1e293b; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.75rem; }
    .key-denied { text-decoration: line-through; color: #dc2626; }
    .tenant-cell { color: #64748b; }
    .inherit-icon { font-size: 0.875rem; }
    .text-muted { color: #94a3b8; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class PermissionAssignmentComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private userService = inject(UserService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  user = signal<UserDetail | null>(null);
  allPermissions = signal<EffectivePermission[]>([]);
  filteredPermissions = signal<EffectivePermission[]>([]);
  loading = signal(true);
  searchTerm = '';
  filterMode: FilterMode = 'all';

  inheritedCount = computed(() => this.allPermissions().filter((p) => p.is_inherited).length);
  directCount = computed(() => this.allPermissions().filter((p) => !p.is_inherited).length);
  deniedCount = computed(() => this.allPermissions().filter((p) => p.is_denied).length);

  private userId = '';

  ngOnInit(): void {
    this.userId = this.route.snapshot.params['userId'];
    this.loadUser();
    this.loadPermissions();
  }

  applyFilters(): void {
    let items = this.allPermissions();

    // Filter by mode
    switch (this.filterMode) {
      case 'inherited':
        items = items.filter((p) => p.is_inherited);
        break;
      case 'direct':
        items = items.filter((p) => !p.is_inherited);
        break;
      case 'denied':
        items = items.filter((p) => p.is_denied);
        break;
    }

    // Filter by search term
    const term = this.searchTerm.toLowerCase().trim();
    if (term) {
      items = items.filter(
        (p) =>
          p.permission_key.toLowerCase().includes(term) ||
          p.source.toLowerCase().includes(term) ||
          p.source_tenant_name.toLowerCase().includes(term),
      );
    }

    this.filteredPermissions.set(items);
  }

  goBack(): void {
    this.router.navigate(['/users', this.userId]);
  }

  private loadUser(): void {
    this.userService.getUser(this.userId).subscribe({
      next: (user) => this.user.set(user),
    });
  }

  private loadPermissions(): void {
    this.permissionService.getUserPermissions(this.userId).subscribe({
      next: (permissions) => {
        this.allPermissions.set(permissions);
        this.filteredPermissions.set(permissions);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
