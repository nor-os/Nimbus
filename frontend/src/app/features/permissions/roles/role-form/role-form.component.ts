/**
 * Overview: Role create/edit form with permission picker grouped by domain.
 * Architecture: Feature component for role CRUD (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/permission.service
 * Concepts: RBAC, role creation, permission assignment, domain-grouped picker
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { PermissionService } from '@core/services/permission.service';
import { Permission, Role, RoleDetail } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

interface DomainGroup {
  domain: string;
  expanded: boolean;
  permissions: Permission[];
}

@Component({
  selector: 'nimbus-role-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="role-form-page">
        <h1>{{ isEditMode() ? 'Edit Role' : 'Create Role' }}</h1>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
          <div class="form-group">
            <label for="name">Name *</label>
            <input id="name" formControlName="name" class="form-input" placeholder="Enter role name" />
            @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
              <span class="error">Name is required</span>
            }
          </div>

          <div class="form-group">
            <label for="description">Description</label>
            <textarea id="description" formControlName="description" class="form-input" rows="3" placeholder="Optional description"></textarea>
          </div>

          <div class="form-row">
            <div class="form-group form-group-half">
              <label for="scope">Scope</label>
              <select id="scope" formControlName="scope" class="form-input">
                <option value="tenant">Tenant</option>
                <option value="provider">Provider</option>
              </select>
            </div>

            <div class="form-group form-group-half">
              <label for="maxLevel">Max Level</label>
              <input id="maxLevel" formControlName="maxLevel" type="number" class="form-input" min="0" placeholder="e.g. 2" />
            </div>
          </div>

          <div class="form-group">
            <label for="parentRoleId">Parent Role</label>
            <select id="parentRoleId" formControlName="parentRoleId" class="form-input">
              <option value="">None</option>
              @for (role of availableParentRoles(); track role.id) {
                <option [value]="role.id">{{ role.name }}</option>
              }
            </select>
          </div>

          <div class="permission-picker">
            <label class="picker-label">Permissions</label>
            <p class="picker-hint">Select permissions to assign to this role, grouped by domain.</p>

            @if (domainGroups().length === 0) {
              <p class="empty">Loading permissions...</p>
            }

            @for (group of domainGroups(); track group.domain) {
              <div class="domain-section">
                <button type="button" class="domain-header" (click)="toggleDomain(group.domain)">
                  <span class="chevron" [class.expanded]="group.expanded">&#9654;</span>
                  <span class="domain-name">{{ group.domain }}</span>
                  <span class="domain-count">{{ getSelectedCount(group) }}/{{ group.permissions.length }}</span>
                </button>
                @if (group.expanded) {
                  <div class="domain-body">
                    @for (perm of group.permissions; track perm.id) {
                      <label class="perm-item">
                        <input
                          type="checkbox"
                          [checked]="isPermissionSelected(perm.id)"
                          (change)="togglePermission(perm.id)"
                        />
                        <span class="perm-key">{{ perm.key }}</span>
                        @if (perm.description) {
                          <span class="perm-desc">{{ perm.description }}</span>
                        }
                      </label>
                    }
                  </div>
                }
              </div>
            }
          </div>

          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
              {{ submitting() ? 'Saving...' : (isEditMode() ? 'Update' : 'Create') }}
            </button>
            <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
          </div>
        </form>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .role-form-page { padding: 0; max-width: 720px; }
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
    .form-row { display: flex; gap: 1rem; }
    .form-group-half { flex: 1; }
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .permission-picker { margin-bottom: 1.5rem; }
    .picker-label { display: block; font-size: 0.8125rem; font-weight: 600; color: #374151; margin-bottom: 0.25rem; }
    .picker-hint { font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.75rem; }
    .empty { color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0; }
    .domain-section {
      border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 0.5rem; overflow: hidden;
    }
    .domain-header {
      display: flex; align-items: center; gap: 0.5rem; width: 100%;
      padding: 0.625rem 0.75rem; border: none; background: #f8fafc;
      cursor: pointer; font-size: 0.8125rem; font-family: inherit; text-align: left;
    }
    .domain-header:hover { background: #f1f5f9; }
    .chevron {
      font-size: 0.625rem; color: #64748b; transition: transform 0.15s;
      display: inline-block;
    }
    .chevron.expanded { transform: rotate(90deg); }
    .domain-name { font-weight: 600; color: #1e293b; text-transform: capitalize; }
    .domain-count { margin-left: auto; color: #64748b; font-size: 0.75rem; }
    .domain-body { padding: 0.5rem 0.75rem; }
    .perm-item {
      display: flex; align-items: flex-start; gap: 0.5rem;
      padding: 0.375rem 0; font-size: 0.8125rem; cursor: pointer;
    }
    .perm-item input[type="checkbox"] { margin-top: 0.125rem; accent-color: #3b82f6; }
    .perm-key { font-weight: 500; color: #1e293b; white-space: nowrap; }
    .perm-desc { color: #94a3b8; font-size: 0.75rem; }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem;
      border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1.5rem;
      border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-secondary:hover { background: #f8fafc; }
  `],
})
export class RoleFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private permissionService = inject(PermissionService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  submitting = signal(false);
  errorMessage = signal('');
  availableParentRoles = signal<Role[]>([]);
  domainGroups = signal<DomainGroup[]>([]);
  selectedPermissionIds = signal<Set<string>>(new Set());

  private roleId = '';

  form = this.fb.group({
    name: ['', Validators.required],
    description: [''],
    scope: ['tenant'],
    parentRoleId: [''],
    maxLevel: [null as number | null],
  });

  ngOnInit(): void {
    this.roleId = this.route.snapshot.params['id'] || '';
    if (this.roleId) {
      this.isEditMode.set(true);
      this.loadRole();
    }

    this.loadPermissions();
    this.loadParentRoles();
  }

  toggleDomain(domain: string): void {
    this.domainGroups.update((groups) =>
      groups.map((g) =>
        g.domain === domain ? { ...g, expanded: !g.expanded } : g,
      ),
    );
  }

  isPermissionSelected(permId: string): boolean {
    return this.selectedPermissionIds().has(permId);
  }

  togglePermission(permId: string): void {
    this.selectedPermissionIds.update((set) => {
      const next = new Set(set);
      if (next.has(permId)) {
        next.delete(permId);
      } else {
        next.add(permId);
      }
      return next;
    });
  }

  getSelectedCount(group: DomainGroup): number {
    const ids = this.selectedPermissionIds();
    return group.permissions.filter((p) => ids.has(p.id)).length;
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;
    const permissionIds = Array.from(this.selectedPermissionIds());

    if (this.isEditMode()) {
      this.permissionService
        .updateRole(this.roleId, {
          name: values.name || undefined,
          description: values.description || null,
          permission_ids: permissionIds.length > 0 ? permissionIds : null,
          max_level: values.maxLevel ?? null,
        })
        .subscribe({
          next: () => {
            this.toastService.success('Role updated');
            this.router.navigate(['/users/roles', this.roleId]);
          },
          error: (err) => {
            this.submitting.set(false);
            const msg = err.error?.detail?.error?.message || 'Failed to update role';
            this.errorMessage.set(msg);
            this.toastService.error(msg);
          },
        });
    } else {
      this.permissionService
        .createRole({
          name: values.name!,
          description: values.description || null,
          scope: values.scope || 'tenant',
          parent_role_id: values.parentRoleId || null,
          permission_ids: permissionIds,
          max_level: values.maxLevel ?? null,
        })
        .subscribe({
          next: (role) => {
            this.toastService.success('Role created');
            this.router.navigate(['/users/roles', role.id]);
          },
          error: (err) => {
            this.submitting.set(false);
            const msg = err.error?.detail?.error?.message || 'Failed to create role';
            this.errorMessage.set(msg);
            this.toastService.error(msg);
          },
        });
    }
  }

  cancel(): void {
    this.router.navigate(['/users/roles']);
  }

  private loadRole(): void {
    this.permissionService.getRole(this.roleId).subscribe({
      next: (role: RoleDetail) => {
        this.form.patchValue({
          name: role.name,
          description: role.description || '',
          scope: role.scope || 'tenant',
          parentRoleId: role.parent_role_id || '',
          maxLevel: role.max_level,
        });
        this.selectedPermissionIds.set(new Set(role.permissions.map((p) => p.id)));
      },
    });
  }

  private loadPermissions(): void {
    this.permissionService.listPermissions().subscribe({
      next: (permissions) => {
        const grouped = new Map<string, Permission[]>();
        for (const perm of permissions) {
          const existing = grouped.get(perm.domain) || [];
          existing.push(perm);
          grouped.set(perm.domain, existing);
        }
        const groups: DomainGroup[] = [];
        for (const [domain, perms] of grouped) {
          groups.push({ domain, expanded: false, permissions: perms });
        }
        groups.sort((a, b) => a.domain.localeCompare(b.domain));
        this.domainGroups.set(groups);
      },
    });
  }

  private loadParentRoles(): void {
    this.permissionService.listRoles().subscribe({
      next: (roles) => {
        this.availableParentRoles.set(
          roles.filter((r) => r.id !== this.roleId),
        );
      },
    });
  }
}
