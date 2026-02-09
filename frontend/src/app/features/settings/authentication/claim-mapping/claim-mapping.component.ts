/**
 * Overview: Claim mapping management for a specific identity provider with inline add form.
 * Architecture: Feature component for IdP claim-to-role/group mapping (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/identity-provider.service, app/core/services/permission.service
 * Concepts: Claim mappings, RBAC integration, SSO attribute mapping, role assignment
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { IdentityProviderService } from '@core/services/identity-provider.service';
import { PermissionService } from '@core/services/permission.service';
import { ClaimMapping } from '@core/models/identity-provider.model';
import { Role, Group } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-claim-mapping',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, IconComponent, SearchableSelectComponent],
  template: `
    <nimbus-layout>
      <div class="claim-mapping-page">
        <div class="page-header">
          <h1>Claim Mappings: {{ providerName() }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading claim mappings...</div>
        } @else {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Claim Name</th>
                  <th>Claim Value</th>
                  <th>Role</th>
                  <th>Group</th>
                  <th>Priority</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (mapping of mappings(); track mapping.id) {
                  <tr>
                    <td class="mono">{{ mapping.claim_name }}</td>
                    <td class="mono">{{ mapping.claim_value }}</td>
                    <td>{{ getRoleName(mapping.role_id) }}</td>
                    <td>{{ mapping.group_id ? getGroupName(mapping.group_id) : '\u2014' }}</td>
                    <td>{{ mapping.priority }}</td>
                    <td class="actions">
                      <button class="icon-btn icon-btn-danger" title="Delete" (click)="confirmDelete(mapping)">
                        <nimbus-icon name="trash" />
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="empty-state">No claim mappings configured</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <div class="add-section">
            <h2>Add Claim Mapping</h2>
            <form [formGroup]="form" (ngSubmit)="onAdd()" class="add-form">
              <div class="form-row">
                <div class="form-group">
                  <label for="claim_name">Claim Name *</label>
                  <input id="claim_name" formControlName="claim_name" class="form-input" placeholder="e.g. groups" />
                </div>

                <div class="form-group">
                  <label for="claim_value">Claim Value *</label>
                  <input id="claim_value" formControlName="claim_value" class="form-input" placeholder="e.g. admin" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label for="role_id">Role *</label>
                  <nimbus-searchable-select formControlName="role_id" [options]="roleOptions()" placeholder="Select role..." />
                </div>

                <div class="form-group">
                  <label for="group_id">Group (optional)</label>
                  <nimbus-searchable-select formControlName="group_id" [options]="groupOptions()" placeholder="Select group..." [allowClear]="true" />
                </div>

                <div class="form-group form-group-sm">
                  <label for="priority">Priority</label>
                  <input id="priority" formControlName="priority" type="number" class="form-input" min="0" />
                </div>
              </div>

              @if (errorMessage()) {
                <div class="form-error">{{ errorMessage() }}</div>
              }

              <div class="form-actions">
                <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
                  {{ submitting() ? 'Adding...' : 'Add Mapping' }}
                </button>
              </div>
            </form>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .claim-mapping-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .loading { color: #64748b; font-size: 0.8125rem; padding: 2rem; text-align: center; }
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
    .table tbody tr:hover { background: #f8fafc; }
    .mono { font-family: 'SF Mono', 'Consolas', 'Liberation Mono', monospace; font-size: 0.75rem; color: #475569; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .icon-btn-danger { color: #dc2626; }
    .icon-btn-danger:hover { background: #fef2f2; color: #b91c1c; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .add-section {
      margin-top: 1.5rem; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem;
    }
    .add-section h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b;
      margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .form-row { display: flex; gap: 1rem; margin-bottom: 1rem; }
    .form-row .form-group { flex: 1; }
    .form-group { margin-bottom: 0; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-group-sm { flex: 0 0 100px !important; }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem;
      border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class ClaimMappingComponent implements OnInit {
  private fb = inject(FormBuilder);
  private idpService = inject(IdentityProviderService);
  private permissionService = inject(PermissionService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private route = inject(ActivatedRoute);


  providerName = signal('');
  mappings = signal<ClaimMapping[]>([]);
  roles = signal<Role[]>([]);
  groups = signal<Group[]>([]);

  roleOptions = computed(() => this.roles().map(r => ({ value: r.id, label: r.name })));
  groupOptions = computed(() => this.groups().map(g => ({ value: g.id, label: g.name })));

  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');

  private providerId = '';

  form = this.fb.group({
    claim_name: ['', Validators.required],
    claim_value: ['', Validators.required],
    role_id: ['', Validators.required],
    group_id: [''],
    priority: [0],
  });

  ngOnInit(): void {
    this.providerId = this.route.snapshot.params['id'];
    this.loadProvider();
    this.loadMappings();
    this.loadRolesAndGroups();
  }

  getRoleName(roleId: string): string {
    const role = this.roles().find((r) => r.id === roleId);
    return role?.name ?? roleId;
  }

  getGroupName(groupId: string): string {
    const group = this.groups().find((g) => g.id === groupId);
    return group?.name ?? groupId;
  }

  onAdd(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;
    this.idpService.createClaimMapping(this.providerId, {
      claim_name: values.claim_name!,
      claim_value: values.claim_value!,
      role_id: values.role_id!,
      group_id: values.group_id || undefined,
      priority: values.priority ?? 0,
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.toastService.success('Claim mapping created');
        this.form.reset({ claim_name: '', claim_value: '', role_id: '', group_id: '', priority: 0 });
        this.loadMappings();
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.error?.detail?.error?.message || 'Failed to create claim mapping';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  async confirmDelete(mapping: ClaimMapping): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Claim Mapping',
      message: `Delete mapping "${mapping.claim_name} = ${mapping.claim_value}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.idpService.deleteClaimMapping(this.providerId, mapping.id).subscribe({
      next: () => {
        this.toastService.success('Claim mapping deleted');
        this.loadMappings();
      },
      error: (err) => {
        const msg = err.error?.detail?.error?.message || 'Failed to delete claim mapping';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private loadProvider(): void {
    this.idpService.getProvider(this.providerId).subscribe({
      next: (provider) => this.providerName.set(provider.name),
    });
  }

  private loadMappings(): void {
    this.loading.set(true);
    this.idpService.listClaimMappings(this.providerId).subscribe({
      next: (mappings) => {
        this.mappings.set(mappings);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(err.error?.detail?.error?.message || 'Failed to load claim mappings');
        this.loading.set(false);
      },
    });
  }

  private loadRolesAndGroups(): void {
    this.permissionService.listRoles().subscribe({
      next: (roles) => this.roles.set(roles),
    });
    this.permissionService.listGroups().subscribe({
      next: (groups) => this.groups.set(groups),
    });
  }
}
