/**
 * Overview: Permission override management page with CRUD for explicit deny overrides.
 * Architecture: Feature component for deny override management (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/permission.service, app/core/services/user.service
 * Concepts: Permission overrides, explicit deny, principal targeting, deny management
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { UserService } from '@core/services/user.service';
import { Permission, PermissionOverride, Role, Group } from '@core/models/permission.model';
import { User } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

type PrincipalType = 'user' | 'group' | 'role';

@Component({
  selector: 'nimbus-override-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="override-page">
        <div class="page-header">
          <h1>Permission Overrides</h1>
          <button class="btn btn-primary" (click)="showForm = !showForm">
            {{ showForm ? 'Cancel' : 'Add Override' }}
          </button>
        </div>

        @if (showForm) {
          <div class="add-form">
            <h2>New Deny Override</h2>

            <div class="form-group">
              <label for="permission">Permission</label>
              <input
                id="permission"
                type="text"
                class="form-input"
                placeholder="Search permissions..."
                [(ngModel)]="permissionSearch"
                (ngModelChange)="filterPermissions()"
                (focus)="permDropdownOpen = true"
              />
              @if (permDropdownOpen && filteredPermissions().length > 0) {
                <div class="dropdown">
                  @for (perm of filteredPermissions(); track perm.id) {
                    <div class="dropdown-item" (click)="selectPermission(perm)">
                      <span class="dropdown-key">{{ perm.key }}</span>
                      @if (perm.description) {
                        <span class="dropdown-desc">{{ perm.description }}</span>
                      }
                    </div>
                  }
                </div>
              }
              @if (selectedPermission()) {
                <span class="selected-badge">{{ selectedPermission()!.key }}
                  <button class="badge-remove" (click)="clearPermission()">&times;</button>
                </span>
              }
            </div>

            <div class="form-group">
              <label>Target Type</label>
              <div class="radio-group">
                @for (type of principalTypes; track type) {
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="principalType"
                      [value]="type"
                      [(ngModel)]="selectedPrincipalType"
                      (ngModelChange)="onPrincipalTypeChange()"
                    />
                    {{ type | titlecase }}
                  </label>
                }
              </div>
            </div>

            <div class="form-group">
              <label for="principal">{{ selectedPrincipalType | titlecase }}</label>
              <input
                id="principal"
                type="text"
                class="form-input"
                [placeholder]="'Search ' + selectedPrincipalType + 's...'"
                [(ngModel)]="principalSearch"
                (ngModelChange)="filterPrincipals()"
                (focus)="principalDropdownOpen = true"
              />
              @if (principalDropdownOpen && filteredPrincipals().length > 0) {
                <div class="dropdown">
                  @for (p of filteredPrincipals(); track p.id) {
                    <div class="dropdown-item" (click)="selectPrincipal(p)">
                      <span class="dropdown-key">{{ p.name }}</span>
                    </div>
                  }
                </div>
              }
              @if (selectedPrincipal()) {
                <span class="selected-badge">{{ selectedPrincipal()!.name }}
                  <button class="badge-remove" (click)="clearPrincipal()">&times;</button>
                </span>
              }
            </div>

            <div class="form-group">
              <label for="reason">Reason</label>
              <textarea
                id="reason"
                class="form-input"
                rows="2"
                placeholder="Why is this permission denied? (optional)"
                [(ngModel)]="reason"
              ></textarea>
            </div>

            <div class="form-actions">
              <button
                class="btn btn-danger"
                [disabled]="!selectedPermission() || !selectedPrincipal() || submitting()"
                (click)="onCreateOverride()"
              >
                {{ submitting() ? 'Creating...' : 'Create Deny Override' }}
              </button>
            </div>
          </div>
        }

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="applySearch()"
            placeholder="Search by permission, target, or reason..."
            class="search-input"
          />
          <span class="result-count">{{ displayedOverrides().length }} override(s)</span>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Permission</th>
                <th>Target</th>
                <th>Type</th>
                <th>Reason</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (o of displayedOverrides(); track o.id) {
                <tr>
                  <td class="key-cell">{{ o.permission_key }}</td>
                  <td class="name-cell">{{ o.principal_name }}</td>
                  <td>
                    <span class="badge" [class]="'badge-type-' + o.principal_type">
                      {{ o.principal_type | titlecase }}
                    </span>
                  </td>
                  <td class="reason-cell">{{ o.reason || '\u2014' }}</td>
                  <td>{{ o.created_at | date: 'medium' }}</td>
                  <td class="actions">
                    <button class="icon-btn icon-btn-danger" title="Remove override" (click)="onDelete(o)">
                      <nimbus-icon name="trash" />
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="6" class="empty-state">
                    @if (loading()) {
                      Loading overrides...
                    } @else {
                      No permission overrides found
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
    .override-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-danger {
      background: #dc2626; color: #fff; padding: 0.5rem 1.25rem;
      border: none; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; font-family: inherit; transition: background 0.15s;
    }
    .btn-danger:hover { background: #b91c1c; }
    .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

    .add-form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .add-form h2 { margin: 0 0 1rem 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; position: relative; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }

    .radio-group { display: flex; gap: 1.5rem; }
    .radio-label {
      display: flex; align-items: center; gap: 0.375rem;
      font-size: 0.8125rem; color: #374151; cursor: pointer;
    }
    .radio-label input { accent-color: #3b82f6; }

    .dropdown {
      position: absolute; z-index: 10; left: 0; right: 0; top: calc(100% - 0.5rem);
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      max-height: 200px; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .dropdown-item {
      padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.8125rem;
      display: flex; flex-direction: column; gap: 0.125rem;
    }
    .dropdown-item:hover { background: #f1f5f9; }
    .dropdown-key { font-weight: 500; color: #1e293b; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.75rem; }
    .dropdown-desc { color: #94a3b8; font-size: 0.6875rem; }

    .selected-badge {
      display: inline-flex; align-items: center; gap: 0.375rem;
      margin-top: 0.375rem; padding: 0.25rem 0.625rem; background: #eff6ff;
      border: 1px solid #bfdbfe; border-radius: 6px; font-size: 0.75rem;
      font-weight: 500; color: #1d4ed8;
      font-family: 'SFMono-Regular', Consolas, monospace;
    }
    .badge-remove {
      background: none; border: none; color: #1d4ed8; font-size: 0.875rem;
      cursor: pointer; padding: 0; line-height: 1;
    }
    .badge-remove:hover { color: #dc2626; }

    .filters {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;
    }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
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
    .key-cell {
      font-weight: 500; color: #1e293b;
      font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.75rem;
    }
    .name-cell { font-weight: 500; color: #1e293b; }
    .reason-cell { color: #64748b; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-type-user { background: #dcfce7; color: #16a34a; }
    .badge-type-group { background: #dbeafe; color: #1d4ed8; }
    .badge-type-role { background: #f3e8ff; color: #7c3aed; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
    }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class OverrideListComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private userService = inject(UserService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  // List state
  allOverrides = signal<PermissionOverride[]>([]);
  filteredOverrides = signal<PermissionOverride[]>([]);
  loading = signal(true);
  searchTerm = '';

  displayedOverrides = computed(() => this.filteredOverrides());

  // Form state
  showForm = false;
  submitting = signal(false);
  principalTypes: PrincipalType[] = ['user', 'group', 'role'];
  selectedPrincipalType: PrincipalType = 'user';
  reason = '';

  // Permission autocomplete
  allPermissions = signal<Permission[]>([]);
  filteredPermissions = signal<Permission[]>([]);
  selectedPermission = signal<Permission | null>(null);
  permissionSearch = '';
  permDropdownOpen = false;

  // Principal autocomplete
  private allUsers = signal<{ id: string; name: string }[]>([]);
  private allGroups = signal<{ id: string; name: string }[]>([]);
  private allRoles = signal<{ id: string; name: string }[]>([]);
  filteredPrincipals = signal<{ id: string; name: string }[]>([]);
  selectedPrincipal = signal<{ id: string; name: string } | null>(null);
  principalSearch = '';
  principalDropdownOpen = false;

  ngOnInit(): void {
    this.loadOverrides();
    this.loadPermissions();
    this.loadAllPrincipals();
  }

  applySearch(): void {
    const term = this.searchTerm.toLowerCase().trim();
    if (!term) {
      this.filteredOverrides.set(this.allOverrides());
      return;
    }
    this.filteredOverrides.set(
      this.allOverrides().filter(
        (o) =>
          o.permission_key.toLowerCase().includes(term) ||
          o.principal_name.toLowerCase().includes(term) ||
          o.principal_type.toLowerCase().includes(term) ||
          (o.reason?.toLowerCase().includes(term) ?? false),
      ),
    );
  }

  filterPermissions(): void {
    const q = this.permissionSearch.toLowerCase().trim();
    if (!q) {
      this.filteredPermissions.set(this.allPermissions().slice(0, 20));
      return;
    }
    this.filteredPermissions.set(
      this.allPermissions()
        .filter(
          (p) =>
            p.key.toLowerCase().includes(q) ||
            (p.description?.toLowerCase().includes(q) ?? false),
        )
        .slice(0, 20),
    );
  }

  selectPermission(perm: Permission): void {
    this.selectedPermission.set(perm);
    this.permissionSearch = perm.key;
    this.permDropdownOpen = false;
  }

  clearPermission(): void {
    this.selectedPermission.set(null);
    this.permissionSearch = '';
  }

  onPrincipalTypeChange(): void {
    this.clearPrincipal();
    this.principalSearch = '';
    this.filterPrincipals();
  }

  filterPrincipals(): void {
    const q = this.principalSearch.toLowerCase().trim();
    const source = this.getPrincipalSource();
    if (!q) {
      this.filteredPrincipals.set(source.slice(0, 20));
      return;
    }
    this.filteredPrincipals.set(
      source.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 20),
    );
  }

  selectPrincipal(principal: { id: string; name: string }): void {
    this.selectedPrincipal.set(principal);
    this.principalSearch = principal.name;
    this.principalDropdownOpen = false;
  }

  clearPrincipal(): void {
    this.selectedPrincipal.set(null);
    this.principalSearch = '';
  }

  onCreateOverride(): void {
    const perm = this.selectedPermission();
    const principal = this.selectedPrincipal();
    if (!perm || !principal) return;

    this.submitting.set(true);
    this.permissionService
      .createOverride({
        permission_id: perm.id,
        principal_type: this.selectedPrincipalType,
        principal_id: principal.id,
        reason: this.reason || undefined,
      })
      .subscribe({
        next: () => {
          this.toastService.success('Deny override created');
          this.resetForm();
          this.loadOverrides();
        },
        error: (err) => {
          this.submitting.set(false);
          this.toastService.error(
            err.error?.detail?.error?.message || 'Failed to create override',
          );
        },
      });
  }

  async onDelete(override: PermissionOverride): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Remove Override',
      message: `Remove deny override for "${override.permission_key}" on ${override.principal_type} "${override.principal_name}"?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.deleteOverride(override.id).subscribe({
      next: () => {
        this.toastService.success('Override removed');
        this.loadOverrides();
      },
      error: (err) =>
        this.toastService.error(
          err.error?.detail?.error?.message || 'Failed to remove override',
        ),
    });
  }

  private resetForm(): void {
    this.showForm = false;
    this.submitting.set(false);
    this.selectedPermission.set(null);
    this.selectedPrincipal.set(null);
    this.permissionSearch = '';
    this.principalSearch = '';
    this.reason = '';
    this.selectedPrincipalType = 'user';
  }

  private loadOverrides(): void {
    this.loading.set(true);
    this.permissionService.listOverrides().subscribe({
      next: (overrides) => {
        this.allOverrides.set(overrides);
        this.filteredOverrides.set(overrides);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadPermissions(): void {
    this.permissionService.listPermissions().subscribe({
      next: (permissions) => this.allPermissions.set(permissions),
    });
  }

  private loadAllPrincipals(): void {
    this.userService.listUsers(0, 200).subscribe({
      next: (resp) =>
        this.allUsers.set(
          resp.items.map((u) => ({ id: u.id, name: u.display_name || u.email })),
        ),
    });
    this.permissionService.listGroups().subscribe({
      next: (groups) =>
        this.allGroups.set(groups.map((g) => ({ id: g.id, name: g.name }))),
    });
    this.permissionService.listRoles().subscribe({
      next: (roles) =>
        this.allRoles.set(roles.map((r) => ({ id: r.id, name: r.name }))),
    });
  }

  private getPrincipalSource(): { id: string; name: string }[] {
    switch (this.selectedPrincipalType) {
      case 'user':
        return this.allUsers();
      case 'group':
        return this.allGroups();
      case 'role':
        return this.allRoles();
    }
  }
}
