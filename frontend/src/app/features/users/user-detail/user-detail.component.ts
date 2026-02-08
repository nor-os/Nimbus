/**
 * Overview: User detail page with inline editing, tabbed role/group/permission management via dialogs.
 * Architecture: Feature component for user detail view and management hub (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/user.service, app/core/services/permission.service, app/shared/components/property-table, app/shared/services/dialog.service, app/shared/services/confirm.service, app/shared/services/toast.service
 * Concepts: User management, inline editing, role assignments, group membership, effective permissions, tabbed navigation, dialog-based assignment
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { UserService } from '@core/services/user.service';
import { PermissionService } from '@core/services/permission.service';
import { UserDetail } from '@core/models/user.model';
import { Role } from '@core/models/permission.model';
import { Group } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import {
  PropertyTableComponent,
  PropertyField,
} from '@shared/components/property-table/property-table.component';
import { DialogService } from '@shared/services/dialog.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { IconComponent } from '@shared/components/icon/icon.component';
import { AssignRoleDialogComponent } from '@shared/components/assign-role-dialog/assign-role-dialog.component';
import { AssignGroupDialogComponent } from '@shared/components/assign-group-dialog/assign-group-dialog.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ImpersonationService } from '@core/services/impersonation.service';
import { TenantContextService } from '@core/services/tenant-context.service';

@Component({
  selector: 'nimbus-user-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, PropertyTableComponent, IconComponent, HasPermissionDirective],
  template: `
    <nimbus-layout>
      <div class="user-detail-page">
        @if (user()) {
          <div class="page-header">
            <div class="header-info">
              <h1>{{ user()!.display_name || user()!.email }}</h1>
              @if (user()!.display_name) {
                <span class="header-email">{{ user()!.email }}</span>
              }
            </div>
          </div>

          <div class="tenant-actions">
            <button
              *hasPermission="'impersonation:session:create'"
              class="btn btn-amber btn-sm"
              (click)="impersonate()"
            >
              Impersonate
            </button>
            <button class="btn btn-outline btn-sm" (click)="removeFromTenant()">
              Remove from Tenant
            </button>
          </div>

          <div class="edit-fields">
            <div class="field-row">
              <label class="field-label">Email</label>
              <span class="field-readonly">{{ user()!.email }}</span>
            </div>
            <div class="field-row">
              <label class="field-label" for="displayName">Display Name</label>
              <input
                id="displayName"
                type="text"
                class="form-input"
                [(ngModel)]="editDisplayName"
                (ngModelChange)="markDirty()"
              />
            </div>
            <div class="field-row">
              <label class="field-label">Active</label>
              <label class="toggle-wrapper">
                <input
                  type="checkbox"
                  class="toggle-input"
                  [(ngModel)]="editIsActive"
                  (ngModelChange)="markDirty()"
                />
                <span class="toggle-track"><span class="toggle-thumb"></span></span>
                <span class="toggle-label">{{ editIsActive ? 'Active' : 'Inactive' }}</span>
              </label>
            </div>
            @if (isDirty()) {
              <div class="save-row">
                <button class="btn btn-primary" [disabled]="saving()" (click)="saveChanges()">
                  {{ saving() ? 'Saving...' : 'Save Changes' }}
                </button>
              </div>
            }
          </div>

          <div class="tabs">
            <button
              class="tab"
              [class.active]="activeTab() === 'roles'"
              (click)="setTab('roles')"
            >Roles ({{ user()!.roles.length }})</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'groups'"
              (click)="setTab('groups')"
            >Member of ({{ user()!.groups.length }})</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'permissions'"
              (click)="setTab('permissions')"
            >Permissions ({{ user()!.effective_permissions.length }})</button>
          </div>

          <div class="tab-content">
            @switch (activeTab()) {
              @case ('roles') {
                <div class="section">
                  <div class="section-header">
                    <h2>Assigned Roles</h2>
                    <button class="btn btn-primary btn-sm" (click)="openAssignRole()">Assign Role</button>
                  </div>
                  @if (user()!.roles.length) {
                    <div class="table-container">
                      <table class="table">
                        <thead>
                          <tr>
                            <th>Role Name</th>
                            <th>Compartment</th>
                            <th>Granted</th>
                            <th>Expires</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (role of user()!.roles; track role.id) {
                            <tr>
                              <td class="role-name">{{ role.role_name }}</td>
                              <td>{{ role.compartment_id || '\u2014' }}</td>
                              <td>{{ role.granted_at | date: 'medium' }}</td>
                              <td>
                                @if (role.expires_at) {
                                  {{ role.expires_at | date: 'medium' }}
                                } @else {
                                  <span class="text-muted">Never</span>
                                }
                              </td>
                              <td class="actions">
                                <button class="icon-btn icon-btn-danger" title="Unassign" (click)="unassignRole(role.role_id, role.role_name)">
                                  <nimbus-icon name="x" />
                                </button>
                              </td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else {
                    <div class="empty-state-box">
                      <p>No roles assigned to this user.</p>
                    </div>
                  }
                </div>
              }

              @case ('groups') {
                <div class="section">
                  <div class="section-header">
                    <h2>Group Membership</h2>
                    <button class="btn btn-primary btn-sm" (click)="openAddToGroup()">Add to Group</button>
                  </div>
                  @if (user()!.groups.length) {
                    <div class="table-container">
                      <table class="table">
                        <thead>
                          <tr>
                            <th>Group Name</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (group of user()!.groups; track group.id) {
                            <tr>
                              <td>{{ group.group_name }}</td>
                              <td class="actions">
                                <button class="icon-btn icon-btn-danger" title="Remove" (click)="removeFromGroup(group.group_id, group.group_name)">
                                  <nimbus-icon name="x" />
                                </button>
                              </td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else {
                    <div class="empty-state-box">
                      <p>No groups assigned to this user.</p>
                    </div>
                  }
                </div>
              }

              @case ('permissions') {
                <div class="section">
                  @if (user()!.effective_permissions.length) {
                    <div class="permissions-grid">
                      @for (perm of user()!.effective_permissions; track perm) {
                        <span class="badge badge-perm">{{ perm }}</span>
                      }
                    </div>
                  } @else {
                    <div class="empty-state-box">
                      <p>No effective permissions for this user.</p>
                    </div>
                  }
                </div>
              }
            }
          </div>
        } @else if (loading()) {
          <div class="loading">Loading user details...</div>
        } @else if (errorMessage()) {
          <div class="form-error">{{ errorMessage() }}</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .user-detail-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .header-info { display: flex; flex-direction: column; gap: 0.25rem; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-email { font-size: 0.8125rem; color: #64748b; }
    .edit-fields {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; margin-bottom: 1.5rem;
    }
    .field-row {
      display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem;
    }
    .field-row:last-child { margin-bottom: 0; }
    .field-label {
      font-size: 0.8125rem; font-weight: 600; color: #374151;
      width: 120px; flex-shrink: 0;
    }
    .field-readonly { font-size: 0.8125rem; color: #64748b; }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit; transition: border-color 0.15s;
      width: 320px; box-sizing: border-box;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .toggle-wrapper { display: flex; align-items: center; cursor: pointer; gap: 0.5rem; }
    .toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
    .toggle-track {
      position: relative; width: 36px; height: 20px; background: #cbd5e1;
      border-radius: 10px; transition: background 0.2s; flex-shrink: 0;
    }
    .toggle-input:checked + .toggle-track { background: #3b82f6; }
    .toggle-thumb {
      position: absolute; top: 2px; left: 2px; width: 16px; height: 16px;
      background: #fff; border-radius: 50%; transition: transform 0.2s;
    }
    .toggle-input:checked + .toggle-track .toggle-thumb { transform: translateX(16px); }
    .toggle-label { font-size: 0.8125rem; color: #374151; font-weight: 400; }
    .save-row { margin-top: 0.75rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: background 0.15s; text-decoration: none; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .tabs {
      display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.5rem; gap: 0.25rem;
    }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; font-family: inherit;
      transition: color 0.15s;
    }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab:hover { color: #3b82f6; }
    .section { margin-bottom: 2rem; }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-header h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0; }
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
    .table tbody tr:hover { background: #f8fafc; }
    .role-name { font-weight: 500; color: #1e293b; }
    .text-muted { color: #94a3b8; }
    .permissions-grid {
      display: flex; flex-wrap: wrap; gap: 0.5rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem;
    }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .badge-perm { background: #dbeafe; color: #1d4ed8; }
    .empty-state-box {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 2rem; text-align: center;
    }
    .empty-state-box p { color: #94a3b8; font-size: 0.8125rem; margin: 0; }
    .tenant-actions {
      display: flex; gap: 0.5rem; margin-bottom: 1rem;
    }
    .btn-amber {
      background: #f59e0b; color: #fff; border: none;
    }
    .btn-amber:hover { background: #d97706; }
    .btn-outline {
      background: #fff; color: #dc2626; border: 1px solid #fecaca;
    }
    .btn-outline:hover { background: #fef2f2; }
    .loading { color: #64748b; font-size: 0.8125rem; padding: 2rem; text-align: center; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; font-size: 0.8125rem; border: 1px solid #fecaca;
    }
  `],
})
export class UserDetailComponent implements OnInit {
  private userService = inject(UserService);
  private permissionService = inject(PermissionService);
  private impersonationService = inject(ImpersonationService);
  private tenantContext = inject(TenantContextService);
  private dialogService = inject(DialogService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  user = signal<UserDetail | null>(null);
  loading = signal(true);
  errorMessage = signal('');
  activeTab = signal<'roles' | 'groups' | 'permissions'>('roles');
  isDirty = signal(false);
  saving = signal(false);

  editDisplayName = '';
  editIsActive = true;

  private userId = '';

  ngOnInit(): void {
    this.userId = this.route.snapshot.params['id'];

    const tabParam = this.route.snapshot.queryParams['tab'];
    if (tabParam === 'roles' || tabParam === 'groups' || tabParam === 'permissions') {
      this.activeTab.set(tabParam);
    }

    this.loadUser();
  }

  setTab(tab: 'roles' | 'groups' | 'permissions'): void {
    this.activeTab.set(tab);
  }

  markDirty(): void {
    const u = this.user();
    if (!u) return;
    const nameChanged = this.editDisplayName !== (u.display_name ?? '');
    const activeChanged = this.editIsActive !== u.is_active;
    this.isDirty.set(nameChanged || activeChanged);
  }

  saveChanges(): void {
    this.saving.set(true);
    this.userService
      .updateUser(this.userId, {
        display_name: this.editDisplayName || null,
        is_active: this.editIsActive,
      })
      .subscribe({
        next: () => {
          this.toastService.success('User updated');
          this.saving.set(false);
          this.isDirty.set(false);
          this.loadUser();
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error(err.error?.detail?.error?.message || 'Failed to update user');
        },
      });
  }

  async openAssignRole(): Promise<void> {
    const excludeIds = this.user()?.roles.map((r) => r.role_id) ?? [];
    const role = await this.dialogService.open<Role | undefined>(
      AssignRoleDialogComponent,
      { excludeIds },
    );
    if (!role) return;
    this.permissionService.assignRole(this.userId, role.id).subscribe({
      next: () => {
        this.toastService.success(`Role "${role.name}" assigned`);
        this.loadUser();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to assign role');
      },
    });
  }

  async unassignRole(roleId: string, roleName: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Unassign Role',
      message: `Unassign role "${roleName}" from this user?`,
      confirmLabel: 'Unassign',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.unassignRole(this.userId, roleId).subscribe({
      next: () => {
        this.toastService.success(`Role "${roleName}" unassigned`);
        this.loadUser();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to unassign role');
      },
    });
  }

  async openAddToGroup(): Promise<void> {
    const excludeIds = this.user()?.groups.map((g) => g.group_id) ?? [];
    const group = await this.dialogService.open<Group | undefined>(
      AssignGroupDialogComponent,
      { excludeIds },
    );
    if (!group) return;
    this.permissionService.addGroupMember(group.id, this.userId).subscribe({
      next: () => {
        this.toastService.success(`Added to group "${group.name}"`);
        this.loadUser();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to add to group');
      },
    });
  }

  async removeFromGroup(groupId: string, groupName: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Remove from Group',
      message: `Remove this user from group "${groupName}"?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.removeGroupMember(groupId, this.userId).subscribe({
      next: () => {
        this.toastService.success(`Removed from group "${groupName}"`);
        this.loadUser();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to remove from group');
      },
    });
  }

  async removeFromTenant(): Promise<void> {
    const u = this.user();
    if (!u) return;
    const ok = await this.confirmService.confirm({
      title: 'Remove from Tenant',
      message: `Remove "${u.display_name || u.email}" from this tenant? This will revoke all tenant-specific roles and access.`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!ok) return;
    this.userService.removeUserFromTenant(this.userId).subscribe({
      next: () => {
        this.toastService.success('User removed from tenant');
        this.router.navigate(['/users']);
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to remove user from tenant');
      },
    });
  }

  async impersonate(): Promise<void> {
    const u = this.user();
    if (!u) return;
    const tenantId = this.tenantContext.currentTenantId();
    if (!tenantId) {
      this.toastService.error('No tenant context');
      return;
    }

    const ok = await this.confirmService.confirm({
      title: 'Impersonate User',
      message: `Request impersonation of "${u.display_name || u.email}"? You will need to provide a reason and your password.`,
      confirmLabel: 'Continue',
    });
    if (!ok) return;

    // For now, navigate to sessions page where the full dialog can be implemented
    this.router.navigate(['/users/impersonate']);
  }

  loadUser(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.userService.getUser(this.userId).subscribe({
      next: (user) => {
        this.user.set(user);
        this.editDisplayName = user.display_name ?? '';
        this.editIsActive = user.is_active;
        this.isDirty.set(false);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMessage.set(err.error?.detail?.error?.message || 'Failed to load user');
      },
    });
  }
}
