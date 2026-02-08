/**
 * Overview: Group create/detail with inline editing and Members/Member of/Roles tabs in detail mode.
 * Architecture: Feature component for group CRUD (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/permission.service, app/shared/services/dialog.service, app/shared/services/confirm.service, app/shared/services/toast.service
 * Concepts: RBAC, group management, flat groups, many-to-many membership, dialog-based assignment
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { PermissionService } from '@core/services/permission.service';
import { Group, Role } from '@core/models/permission.model';
import { User } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { DialogService } from '@shared/services/dialog.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { AssignRoleDialogComponent } from '@shared/components/assign-role-dialog/assign-role-dialog.component';
import { AssignUserDialogComponent } from '@shared/components/assign-user-dialog/assign-user-dialog.component';
import { AssignGroupDialogComponent } from '@shared/components/assign-group-dialog/assign-group-dialog.component';

@Component({
  selector: 'nimbus-group-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="group-form-page">
        @if (!isDetailMode()) {
          <!-- Create mode -->
          <h1>Create Group</h1>

          <form [formGroup]="form" (ngSubmit)="onCreate()" class="form">
            <div class="form-group">
              <label for="name">Name *</label>
              <input id="name" formControlName="name" class="form-input" placeholder="Enter group name" />
              @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                <span class="error">Name is required</span>
              }
            </div>

            <div class="form-group">
              <label for="description">Description</label>
              <textarea id="description" formControlName="description" class="form-input" rows="3" placeholder="Optional description"></textarea>
            </div>

            @if (errorMessage()) {
              <div class="form-error">{{ errorMessage() }}</div>
            }

            <div class="form-actions">
              <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
                {{ submitting() ? 'Creating...' : 'Create' }}
              </button>
              <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
            </div>
          </form>
        } @else {
          <!-- Detail mode -->
          <h1>{{ group()?.name || 'Group' }}</h1>

          <div class="inline-edit-section">
            <div class="inline-field">
              <label>Name</label>
              <input class="form-input" [(ngModel)]="editName" (ngModelChange)="markDirty()" />
            </div>
            <div class="inline-field">
              <label>Description</label>
              <textarea class="form-input" rows="2" [(ngModel)]="editDescription" (ngModelChange)="markDirty()"></textarea>
            </div>
            @if (isDirty()) {
              <div class="save-bar">
                <button class="btn btn-primary btn-sm" (click)="saveChanges()" [disabled]="saving()">
                  {{ saving() ? 'Saving...' : 'Save Changes' }}
                </button>
                <button class="btn btn-secondary btn-sm" (click)="discardChanges()">Discard</button>
              </div>
            }
          </div>

          <div class="tabs">
            <button class="tab" [class.active]="activeTab() === 'members'" (click)="setTab('members')">Members</button>
            <button class="tab" [class.active]="activeTab() === 'memberOf'" (click)="setTab('memberOf')">Member of</button>
            <button class="tab" [class.active]="activeTab() === 'roles'" (click)="setTab('roles')">Roles</button>
          </div>

          <!-- Members tab -->
          @if (activeTab() === 'members') {
            <div class="section">
              <div class="section-header">
                <h2>User Members</h2>
                <button class="btn btn-primary btn-sm" (click)="openAddUser()">Add User</button>
              </div>
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Display Name</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (member of userMembers(); track member.id) {
                      <tr>
                        <td>{{ member.email }}</td>
                        <td>{{ member.display_name || '\u2014' }}</td>
                        <td>
                          <button class="icon-btn icon-btn-danger" title="Remove" (click)="removeUser(member.id, member.email)">
                            <nimbus-icon name="x" />
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr><td colspan="3" class="empty-state">No user members</td></tr>
                    }
                  </tbody>
                </table>
              </div>

              <div class="section-header" style="margin-top: 1.5rem;">
                <h2>Group Members</h2>
                <button class="btn btn-primary btn-sm" (click)="openAddChildGroup()">Add Group</button>
              </div>
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Group Name</th>
                      <th>Description</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (g of groupMembers(); track g.id) {
                      <tr>
                        <td class="name-cell">{{ g.name }}</td>
                        <td>{{ g.description || '\u2014' }}</td>
                        <td>
                          <button class="icon-btn icon-btn-danger" title="Remove" (click)="removeChildGroup(g.id, g.name)">
                            <nimbus-icon name="x" />
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr><td colspan="3" class="empty-state">No group members</td></tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }

          <!-- Member of tab -->
          @if (activeTab() === 'memberOf') {
            <div class="section">
              <div class="section-header">
                <h2>Member of</h2>
                <button class="btn btn-primary btn-sm" (click)="openJoinGroup()">Join Group</button>
              </div>
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Group Name</th>
                      <th>Description</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (g of parentGroups(); track g.id) {
                      <tr>
                        <td class="name-cell">{{ g.name }}</td>
                        <td>{{ g.description || '\u2014' }}</td>
                        <td>
                          <button class="icon-btn icon-btn-danger" title="Leave group" (click)="leaveGroup(g.id, g.name)">
                            <nimbus-icon name="x" />
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr><td colspan="3" class="empty-state">Not a member of any group</td></tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }

          <!-- Roles tab -->
          @if (activeTab() === 'roles') {
            <div class="section">
              <div class="section-header">
                <h2>Assigned Roles</h2>
                <button class="btn btn-primary btn-sm" (click)="openAssignRole()">Assign Role</button>
              </div>
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Role Name</th>
                      <th>Scope</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (role of groupRoles(); track role.id) {
                      <tr>
                        <td class="name-cell">{{ role.name }}</td>
                        <td>
                          <span class="badge" [class]="'badge-scope-' + role.scope">{{ role.scope }}</span>
                        </td>
                        <td>
                          <button class="icon-btn icon-btn-danger" title="Unassign" (click)="unassignRole(role.id, role.name)">
                            <nimbus-icon name="x" />
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr><td colspan="3" class="empty-state">No roles assigned</td></tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .group-form-page { padding: 0; max-width: 720px; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; }
    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1.25rem; }
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
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; transition: background 0.15s; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem; border: none;
    }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1.5rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .inline-edit-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem;
      margin-bottom: 1.5rem;
    }
    .inline-field { margin-bottom: 1rem; }
    .inline-field:last-of-type { margin-bottom: 0; }
    .inline-field label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .save-bar { display: flex; gap: 0.5rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f1f5f9; }
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
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .text-muted { color: #94a3b8; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-scope-provider { background: #fef2f2; color: #dc2626; }
    .badge-scope-tenant { background: #dbeafe; color: #1d4ed8; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class GroupFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private permissionService = inject(PermissionService);
  private dialogService = inject(DialogService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  isDetailMode = signal(false);
  submitting = signal(false);
  saving = signal(false);
  isDirty = signal(false);
  errorMessage = signal('');
  activeTab = signal<'members' | 'memberOf' | 'roles'>('members');
  group = signal<Group | null>(null);
  userMembers = signal<User[]>([]);
  groupMembers = signal<Group[]>([]);
  parentGroups = signal<Group[]>([]);
  groupRoles = signal<Role[]>([]);

  editName = '';
  editDescription = '';
  private groupId = '';

  form = this.fb.group({
    name: ['', Validators.required],
    description: [''],
  });

  ngOnInit(): void {
    this.groupId = this.route.snapshot.params['id'] || '';
    if (this.groupId) {
      this.isDetailMode.set(true);
      this.loadGroup();
      this.loadMembers();
      this.loadMemberOf();
      this.loadGroupRoles();
    }
  }

  setTab(tab: 'members' | 'memberOf' | 'roles'): void {
    this.activeTab.set(tab);
  }

  // ── Create mode ─────────────────────────────────────────────────

  onCreate(): void {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;
    this.permissionService
      .createGroup({
        name: values.name!,
        description: values.description || null,
      })
      .subscribe({
        next: (created) => this.router.navigate(['/users/groups', created.id]),
        error: (err) => {
          this.submitting.set(false);
          this.errorMessage.set(err.error?.detail?.error?.message || 'Failed to create group');
        },
      });
  }

  // ── Inline edit ─────────────────────────────────────────────────

  markDirty(): void {
    const g = this.group();
    if (!g) return;
    this.isDirty.set(
      this.editName !== g.name || this.editDescription !== (g.description || ''),
    );
  }

  saveChanges(): void {
    this.saving.set(true);
    this.permissionService
      .updateGroup(this.groupId, {
        name: this.editName || undefined,
        description: this.editDescription || null,
      })
      .subscribe({
        next: (updated) => {
          this.group.set(updated);
          this.isDirty.set(false);
          this.saving.set(false);
          this.toastService.success('Group updated');
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error(err.error?.detail?.error?.message || 'Failed to update group');
        },
      });
  }

  discardChanges(): void {
    const g = this.group();
    if (g) {
      this.editName = g.name;
      this.editDescription = g.description || '';
    }
    this.isDirty.set(false);
  }

  // ── User member management ──────────────────────────────────────

  async openAddUser(): Promise<void> {
    const excludeIds = this.userMembers().map((m) => m.id);
    const user = await this.dialogService.open<User | undefined>(
      AssignUserDialogComponent,
      { excludeIds },
    );
    if (!user) return;
    this.permissionService.addGroupMember(this.groupId, user.id).subscribe({
      next: () => {
        this.toastService.success(`Added ${user.email} to group`);
        this.loadMembers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to add member');
      },
    });
  }

  async removeUser(userId: string, email: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Remove Member',
      message: `Remove ${email} from this group?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.removeGroupMember(this.groupId, userId).subscribe({
      next: () => {
        this.toastService.success(`Removed ${email} from group`);
        this.loadMembers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to remove member');
      },
    });
  }

  // ── Child group management ──────────────────────────────────────

  async openAddChildGroup(): Promise<void> {
    const excludeIds = [this.groupId, ...this.groupMembers().map((g) => g.id)];
    const group = await this.dialogService.open<Group | undefined>(
      AssignGroupDialogComponent,
      { excludeIds },
    );
    if (!group) return;
    this.permissionService.addChildGroup(this.groupId, group.id).subscribe({
      next: () => {
        this.toastService.success(`Added "${group.name}" as member`);
        this.loadMembers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to add group member');
      },
    });
  }

  async removeChildGroup(childId: string, childName: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Remove Group Member',
      message: `Remove "${childName}" from this group?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.removeChildGroup(this.groupId, childId).subscribe({
      next: () => {
        this.toastService.success(`Removed "${childName}" from group`);
        this.loadMembers();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to remove group member');
      },
    });
  }

  // ── Member of (parent group) management ─────────────────────────

  async openJoinGroup(): Promise<void> {
    const excludeIds = [this.groupId, ...this.parentGroups().map((g) => g.id)];
    const group = await this.dialogService.open<Group | undefined>(
      AssignGroupDialogComponent,
      { excludeIds },
    );
    if (!group) return;
    // This group becomes a child of the selected group
    this.permissionService.addChildGroup(group.id, this.groupId).subscribe({
      next: () => {
        this.toastService.success(`Joined "${group.name}"`);
        this.loadMemberOf();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to join group');
      },
    });
  }

  async leaveGroup(parentId: string, parentName: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Leave Group',
      message: `Remove this group from "${parentName}"?`,
      confirmLabel: 'Leave',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.removeChildGroup(parentId, this.groupId).subscribe({
      next: () => {
        this.toastService.success(`Left "${parentName}"`);
        this.loadMemberOf();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to leave group');
      },
    });
  }

  // ── Role management ─────────────────────────────────────────────

  async openAssignRole(): Promise<void> {
    const excludeIds = this.groupRoles().map((r) => r.id);
    const role = await this.dialogService.open<Role | undefined>(
      AssignRoleDialogComponent,
      { excludeIds },
    );
    if (!role) return;
    this.permissionService.assignGroupRole(this.groupId, role.id).subscribe({
      next: () => {
        this.toastService.success(`Role "${role.name}" assigned`);
        this.loadGroupRoles();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to assign role');
      },
    });
  }

  async unassignRole(roleId: string, roleName: string): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Unassign Role',
      message: `Unassign role "${roleName}" from this group?`,
      confirmLabel: 'Unassign',
      variant: 'danger',
    });
    if (!ok) return;
    this.permissionService.unassignGroupRole(this.groupId, roleId).subscribe({
      next: () => {
        this.toastService.success(`Role "${roleName}" unassigned`);
        this.loadGroupRoles();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to unassign role');
      },
    });
  }

  cancel(): void {
    this.router.navigate(['/users/groups']);
  }

  // ── Private ─────────────────────────────────────────────────────

  private loadGroup(): void {
    this.permissionService.getGroup(this.groupId).subscribe({
      next: (group) => {
        this.group.set(group);
        this.editName = group.name;
        this.editDescription = group.description || '';
      },
    });
  }

  private loadMembers(): void {
    this.permissionService.getGroupMembers(this.groupId).subscribe({
      next: (data) => {
        this.userMembers.set(data.users);
        this.groupMembers.set(data.groups);
      },
    });
  }

  private loadMemberOf(): void {
    this.permissionService.getGroupMemberOf(this.groupId).subscribe({
      next: (groups) => this.parentGroups.set(groups),
    });
  }

  private loadGroupRoles(): void {
    this.permissionService.getGroupRoles(this.groupId).subscribe({
      next: (roles) => this.groupRoles.set(roles),
    });
  }
}
