/**
 * Overview: Staff profile management -- list, create, edit with full fields, and trace activities.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/forms, app/core/services/delivery.service
 * Concepts: Staff profiles, internal rate cards, delivery regions, activity tracing
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DeliveryService } from '@core/services/delivery.service';
import {
  ActivityDefinition,
  OrganizationalUnit,
  StaffProfile,
  StaffProfileCreateInput,
  StaffProfileUpdateInput,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-staff-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="staff-list-page">
        <div class="page-header">
          <h1>Staff Profiles</h1>
          <button
            *nimbusHasPermission="'catalog:staff:manage'"
            class="btn btn-primary"
            (click)="openCreateForm()"
          >
            Create Profile
          </button>
        </div>

        <!-- Create / Edit Dialog Overlay -->
        @if (showForm()) {
          <div class="dialog-overlay" (click)="cancelForm()">
            <div class="dialog" (click)="$event.stopPropagation()">
              <div class="dialog-header">
                <h2>{{ editingProfile() ? 'Edit Staff Profile' : 'New Staff Profile' }}</h2>
                <button class="dialog-close" (click)="cancelForm()">&#x2715;</button>
              </div>

              <div class="dialog-body">
                <!-- Row 1: Profile ID + Name -->
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">Profile ID</label>
                    <input
                      type="text"
                      [(ngModel)]="formProfileId"
                      placeholder="e.g. SE-001"
                      class="form-input mono-input"
                    />
                    <span class="form-hint">Human-readable identifier</span>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Name *</label>
                    <input
                      type="text"
                      [(ngModel)]="formName"
                      placeholder="e.g. senior_engineer"
                      class="form-input mono-input"
                      [disabled]="!!editingProfile()"
                    />
                  </div>
                </div>

                <!-- Row 2: Display Name + Org Unit -->
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">Display Name *</label>
                    <input
                      type="text"
                      [(ngModel)]="formDisplayName"
                      placeholder="e.g. Senior Engineer"
                      class="form-input"
                    />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Org Unit</label>
                    <nimbus-searchable-select
                      [(ngModel)]="formOrgUnitId"
                      [options]="orgUnitOptions()"
                      placeholder="None"
                      [allowClear]="true"
                    />
                  </div>
                </div>

                <!-- Row 3: Cost Center + Cost Rate + Currency -->
                <div class="form-row form-row-3">
                  <div class="form-group">
                    <label class="form-label">Cost Center</label>
                    <input
                      type="text"
                      [(ngModel)]="formCostCenter"
                      [placeholder]="inheritedCostCenter()"
                      class="form-input"
                    />
                    @if (inheritedCostCenter() !== 'None' && !formCostCenter.trim()) {
                      <span class="form-hint inherited">Inherited from org unit</span>
                    }
                    @if (formCostCenter.trim()) {
                      <span class="form-hint override">Override</span>
                    }
                  </div>
                  <div class="form-group">
                    <label class="form-label">Default Hourly Cost</label>
                    <input
                      type="number"
                      [(ngModel)]="formHourlyCost"
                      placeholder="0.00"
                      class="form-input"
                      step="0.01"
                      min="0"
                    />
                  </div>
                  <div class="form-group form-group-sm">
                    <label class="form-label">Currency</label>
                    <select class="form-input" [(ngModel)]="formCurrency">
                      <option value="EUR">EUR</option>
                      <option value="USD">USD</option>
                      <option value="GBP">GBP</option>
                      <option value="CHF">CHF</option>
                    </select>
                  </div>
                </div>

                <!-- Row 4: Sort Order -->
                <div class="form-row">
                  <div class="form-group form-group-sm">
                    <label class="form-label">Sort Order</label>
                    <input
                      type="number"
                      [(ngModel)]="formSortOrder"
                      class="form-input"
                      min="0"
                    />
                  </div>
                </div>
              </div>

              <div class="dialog-footer">
                <button
                  class="btn btn-primary"
                  (click)="submitForm()"
                  [disabled]="!formName.trim() || !formDisplayName.trim()"
                >
                  {{ editingProfile() ? 'Save Changes' : 'Create' }}
                </button>
                <button class="btn btn-secondary" (click)="cancelForm()">Cancel</button>
              </div>
            </div>
          </div>
        }

        <!-- Trace Activities Dialog -->
        @if (tracingProfile()) {
          <div class="dialog-overlay" (click)="closeTrace()">
            <div class="dialog dialog-wide" (click)="$event.stopPropagation()">
              <div class="dialog-header">
                <h2>Activities for {{ tracingProfile()!.displayName }}</h2>
                <button class="dialog-close" (click)="closeTrace()">&#x2715;</button>
              </div>
              <div class="dialog-body">
                @if (traceLoading()) {
                  <p class="loading-text">Loading activities...</p>
                } @else if (tracedActivities().length === 0) {
                  <p class="empty-text">No activity definitions reference this staff profile.</p>
                } @else {
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Activity Name</th>
                        <th>Estimated Hours</th>
                        <th>Optional</th>
                        <th>Sort</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (act of tracedActivities(); track act.id) {
                        <tr>
                          <td class="name-cell">{{ act.name }}</td>
                          <td>{{ act.estimatedHours }}h</td>
                          <td>
                            <span class="badge" [class.badge-system]="!act.isOptional" [class.badge-custom]="act.isOptional">
                              {{ act.isOptional ? 'Optional' : 'Required' }}
                            </span>
                          </td>
                          <td>{{ act.sortOrder }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                }
              </div>
              <div class="dialog-footer">
                <button class="btn btn-secondary" (click)="closeTrace()">Close</button>
              </div>
            </div>
          </div>
        }

        <!-- Table -->
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Profile ID</th>
                <th>Name</th>
                <th>Display Name</th>
                <th>Org Unit</th>
                <th>Cost Center</th>
                <th>Default Cost</th>
                <th>System?</th>
                <th>Sort</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (profile of profiles(); track profile.id) {
                <tr>
                  <td class="mono-cell">{{ profile.profileId || '\u2014' }}</td>
                  <td class="name-cell">{{ profile.name }}</td>
                  <td>{{ profile.displayName }}</td>
                  <td>{{ orgUnitNameForId(profile.orgUnitId) }}</td>
                  <td>{{ effectiveCostCenter(profile) }}</td>
                  <td>
                    @if (profile.defaultHourlyCost != null) {
                      {{ profile.defaultHourlyCost | number:'1.2-2' }} {{ profile.defaultCurrency || 'EUR' }}
                    } @else {
                      &mdash;
                    }
                  </td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-system]="profile.isSystem"
                      [class.badge-custom]="!profile.isSystem"
                    >
                      {{ profile.isSystem ? 'System' : 'Custom' }}
                    </span>
                  </td>
                  <td>{{ profile.sortOrder }}</td>
                  <td class="actions">
                    <button
                      class="btn-action btn-trace"
                      (click)="traceActivities(profile)"
                      title="Trace Activities"
                    >
                      Trace
                    </button>
                    <button
                      *nimbusHasPermission="'catalog:staff:manage'"
                      class="btn-action btn-edit"
                      (click)="openEditForm(profile)"
                      title="Edit"
                      [disabled]="profile.isSystem"
                    >
                      Edit
                    </button>
                    <button
                      *nimbusHasPermission="'catalog:staff:manage'"
                      class="btn-action btn-delete"
                      (click)="deleteProfile(profile)"
                      title="Delete"
                      [disabled]="profile.isSystem"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="9" class="empty-state">No staff profiles found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .staff-list-page { padding: 0; }

    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    /* ── Dialog overlay ─────────────────────────────────────────────── */

    .dialog-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.3);
      display: flex; align-items: center; justify-content: center; z-index: 100;
    }
    .dialog {
      background: #fff; border-radius: 10px; width: 600px; max-width: 90vw;
      max-height: 85vh; display: flex; flex-direction: column;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }
    .dialog-wide { width: 700px; }
    .dialog-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1.25rem 1.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .dialog-header h2 {
      margin: 0; font-size: 1.0625rem; font-weight: 600; color: #1e293b;
    }
    .dialog-close {
      background: none; border: none; cursor: pointer; font-size: 1.125rem;
      color: #94a3b8; padding: 0.25rem; line-height: 1; border-radius: 4px;
    }
    .dialog-close:hover { color: #475569; background: #f1f5f9; }
    .dialog-body {
      padding: 1.5rem; overflow-y: auto; flex: 1;
    }
    .dialog-footer {
      display: flex; gap: 0.5rem; padding: 1rem 1.5rem;
      border-top: 1px solid #f1f5f9;
    }

    /* ── Form layout ───────────────────────────────────────────────── */

    .form-row {
      display: flex; gap: 1rem; margin-bottom: 1.25rem;
    }
    .form-row-3 > .form-group { flex: 1; }
    .form-group { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .form-group-sm { flex: 0 0 100px; min-width: 80px; }
    .form-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem;
    }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b; font-family: inherit;
      transition: border-color 0.15s; width: 100%; box-sizing: border-box;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; }
    .mono-input {
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    }
    .form-hint {
      font-size: 0.6875rem; margin-top: 0.25rem;
    }
    .form-hint.inherited { color: #64748b; }
    .form-hint.override { color: #f59e0b; font-weight: 500; }

    /* ── Table ─────────────────────────────────────────────────────── */

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
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono-cell {
      font-family: 'SFMono-Regular', Consolas, monospace;
      font-size: 0.75rem; color: #475569;
    }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-system { background: #dbeafe; color: #2563eb; }
    .badge-custom { background: #f0fdf4; color: #16a34a; }

    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .loading-text { color: #64748b; font-size: 0.8125rem; text-align: center; padding: 1rem; }
    .empty-text { color: #94a3b8; font-size: 0.8125rem; text-align: center; padding: 1rem; }

    /* ── Action buttons ─────────────────────────────────────────────  */

    .actions { display: flex; gap: 0.375rem; align-items: center; }
    .btn-action {
      padding: 0.25rem 0.625rem; border-radius: 4px; font-size: 0.75rem;
      font-weight: 500; font-family: inherit; cursor: pointer; border: 1px solid transparent;
      transition: background 0.15s, color 0.15s;
    }
    .btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-edit {
      background: #f1f5f9; color: #475569; border-color: #e2e8f0;
    }
    .btn-edit:hover:not(:disabled) { background: #e2e8f0; color: #1e293b; }
    .btn-delete {
      background: #fff; color: #dc2626; border-color: #fecaca;
    }
    .btn-delete:hover:not(:disabled) { background: #fef2f2; }
    .btn-trace {
      background: #fff; color: #6366f1; border-color: #c7d2fe;
    }
    .btn-trace:hover { background: #eef2ff; }

    /* ── Shared button styles ──────────────────────────────────────── */

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      padding: 0.5rem 1rem; border: none;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary {
      background: #fff; color: #64748b; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; color: #1e293b; }
  `],
})
export class StaffListComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);

  profiles = signal<StaffProfile[]>([]);
  orgUnits = signal<OrganizationalUnit[]>([]);
  loading = signal(false);

  orgUnitOptions = computed(() => this.orgUnits().map(ou => ({ value: ou.id, label: ou.displayName })));

  // Form state
  showForm = signal(false);
  editingProfile = signal<StaffProfile | null>(null);

  formName = '';
  formDisplayName = '';
  formProfileId = '';
  formOrgUnitId = '';
  formCostCenter = '';
  formHourlyCost: number | null = null;
  formCurrency = 'EUR';
  formSortOrder = 0;

  // Trace state
  tracingProfile = signal<StaffProfile | null>(null);
  tracedActivities = signal<ActivityDefinition[]>([]);
  traceLoading = signal(false);

  inheritedCostCenter = computed(() => {
    const ouId = this.formOrgUnitId;
    if (!ouId) return 'None';
    const ou = this.orgUnits().find(u => u.id === ouId);
    return ou?.costCenter || 'None';
  });

  ngOnInit(): void {
    this.loadProfiles();
    this.loadOrgUnits();
  }

  loadProfiles(): void {
    this.loading.set(true);
    this.deliveryService.listStaffProfiles().subscribe({
      next: (items) => {
        this.profiles.set(items);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load staff profiles');
        this.loading.set(false);
      },
    });
  }

  // ── Create / Edit dialog ──────────────────────────────────────────

  openCreateForm(): void {
    this.editingProfile.set(null);
    this.resetForm();
    this.showForm.set(true);
  }

  openEditForm(profile: StaffProfile): void {
    this.editingProfile.set(profile);
    this.formName = profile.name;
    this.formDisplayName = profile.displayName;
    this.formProfileId = profile.profileId || '';
    this.formOrgUnitId = profile.orgUnitId || '';
    this.formCostCenter = profile.costCenter || '';
    this.formHourlyCost = profile.defaultHourlyCost;
    this.formCurrency = profile.defaultCurrency || 'EUR';
    this.formSortOrder = profile.sortOrder;
    this.showForm.set(true);
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editingProfile.set(null);
    this.resetForm();
  }

  submitForm(): void {
    const name = this.formName.trim();
    const displayName = this.formDisplayName.trim();
    if (!name || !displayName) return;

    const editing = this.editingProfile();
    if (editing) {
      const input: StaffProfileUpdateInput = {};
      if (displayName !== editing.displayName) input.displayName = displayName;
      if ((this.formOrgUnitId || null) !== editing.orgUnitId) input.orgUnitId = this.formOrgUnitId || null;
      if ((this.formProfileId.trim() || null) !== editing.profileId) input.profileId = this.formProfileId.trim() || null;
      if ((this.formCostCenter.trim() || null) !== editing.costCenter) input.costCenter = this.formCostCenter.trim() || null;
      if (this.formHourlyCost !== editing.defaultHourlyCost) input.defaultHourlyCost = this.formHourlyCost;
      if (this.formCurrency !== (editing.defaultCurrency || 'EUR')) input.defaultCurrency = this.formCurrency;
      if (this.formSortOrder !== editing.sortOrder) input.sortOrder = this.formSortOrder;

      if (Object.keys(input).length === 0) {
        this.cancelForm();
        return;
      }

      this.deliveryService.updateStaffProfile(editing.id, input).subscribe({
        next: () => {
          this.toastService.success(`Staff profile "${displayName}" updated`);
          this.cancelForm();
          this.loadProfiles();
        },
        error: (err) => this.toastService.error(err.message || 'Failed to update'),
      });
    } else {
      const input: StaffProfileCreateInput = {
        name,
        displayName,
        orgUnitId: this.formOrgUnitId || null,
        profileId: this.formProfileId.trim() || null,
        costCenter: this.formCostCenter.trim() || null,
        defaultHourlyCost: this.formHourlyCost,
        defaultCurrency: this.formCurrency,
        sortOrder: this.formSortOrder,
      };

      this.deliveryService.createStaffProfile(input).subscribe({
        next: () => {
          this.toastService.success(`Staff profile "${displayName}" created`);
          this.cancelForm();
          this.loadProfiles();
        },
        error: (err) => this.toastService.error(err.message || 'Failed to create'),
      });
    }
  }

  // ── Trace Activities ──────────────────────────────────────────────

  traceActivities(profile: StaffProfile): void {
    this.tracingProfile.set(profile);
    this.traceLoading.set(true);
    this.tracedActivities.set([]);

    this.deliveryService.staffProfileActivities(profile.id).subscribe({
      next: (defs) => {
        this.tracedActivities.set(defs);
        this.traceLoading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load activities');
        this.traceLoading.set(false);
      },
    });
  }

  closeTrace(): void {
    this.tracingProfile.set(null);
    this.tracedActivities.set([]);
  }

  // ── Delete ────────────────────────────────────────────────────────

  async deleteProfile(profile: StaffProfile): Promise<void> {
    if (profile.isSystem) return;

    const confirmed = await this.confirmService.confirm({
      title: 'Delete Staff Profile',
      message: `Are you sure you want to delete "${profile.displayName}"? This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!confirmed) return;

    this.deliveryService.deleteStaffProfile(profile.id).subscribe({
      next: () => {
        this.toastService.success(`Staff profile "${profile.displayName}" deleted`);
        this.loadProfiles();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete staff profile');
      },
    });
  }

  // ── Helpers ───────────────────────────────────────────────────────

  orgUnitNameForId(orgUnitId: string | null): string {
    if (!orgUnitId) return '\u2014';
    const ou = this.orgUnits().find((u) => u.id === orgUnitId);
    return ou ? ou.displayName : '\u2014';
  }

  effectiveCostCenter(profile: StaffProfile): string {
    if (profile.costCenter) return profile.costCenter;
    if (profile.orgUnitId) {
      const ou = this.orgUnits().find(u => u.id === profile.orgUnitId);
      return ou?.costCenter || '\u2014';
    }
    return '\u2014';
  }

  private resetForm(): void {
    this.formName = '';
    this.formDisplayName = '';
    this.formProfileId = '';
    this.formOrgUnitId = '';
    this.formCostCenter = '';
    this.formHourlyCost = null;
    this.formCurrency = 'EUR';
    this.formSortOrder = 0;
  }

  private loadOrgUnits(): void {
    this.deliveryService.listOrgUnits().subscribe({
      next: (items) => this.orgUnits.set(items),
    });
  }
}
