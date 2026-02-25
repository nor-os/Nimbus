/**
 * Overview: Process editor — edit name/description, manage linked activities (add, remove,
 *     reorder), and view assigned service offerings.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router, app/core/services/delivery.service
 * Concepts: Service processes group activities into ordered delivery workflows.
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
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { DeliveryService } from '@core/services/delivery.service';
import { CatalogService } from '@core/services/catalog.service';
import {
  ActivityTemplate,
  ProcessActivityLink,
  ServiceProcess,
  ServiceProcessAssignment,
} from '@shared/models/delivery.model';
import { ServiceOffering } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-process-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="editor-page">
        @if (loading()) {
          <div class="loading-state">Loading process...</div>
        } @else if (!process()) {
          <div class="empty-state">Process not found.</div>
        } @else {
          <div class="page-header">
            <button class="btn btn-secondary btn-back" (click)="goBack()">&larr; Back</button>
            <h1>{{ process()!.name }}</h1>
          </div>

          <!-- Edit name/description -->
          <div class="section-card">
            <h2 class="section-title">Details</h2>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Name</label>
                <input
                  type="text"
                  [(ngModel)]="editName"
                  class="form-input"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Description</label>
                <input
                  type="text"
                  [(ngModel)]="editDescription"
                  class="form-input"
                />
              </div>
              <div class="form-group form-group-sm">
                <label class="form-label">Sort Order</label>
                <input
                  type="number"
                  [(ngModel)]="editSortOrder"
                  class="form-input"
                  min="0"
                />
              </div>
            </div>
            <div class="form-actions">
              <button
                *nimbusHasPermission="'catalog:process:manage'"
                class="btn btn-primary"
                (click)="saveDetails()"
                [disabled]="!editName.trim()"
              >
                Save Changes
              </button>
            </div>
          </div>

          <!-- Linked Activities -->
          <div class="section-card">
            <div class="section-header">
              <h2 class="section-title">Linked Activities ({{ sortedLinks().length }})</h2>
              <button
                *nimbusHasPermission="'catalog:process:manage'"
                class="btn-link"
                (click)="showAddActivity.set(true)"
              >
                + Add Activity
              </button>
            </div>

            @if (showAddActivity()) {
              <div class="add-form">
                <nimbus-searchable-select class="add-field" [(ngModel)]="addActivityTemplateId" [options]="activityTemplateOptions()" placeholder="Select activity..." />
                <input
                  type="number"
                  [(ngModel)]="addSortOrder"
                  class="form-input add-field-sm"
                  placeholder="Order"
                  min="0"
                />
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="addIsRequired" />
                  <span>Required</span>
                </label>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="addActivity()"
                  [disabled]="!addActivityTemplateId"
                >Add</button>
                <button class="btn btn-sm btn-secondary" (click)="cancelAddActivity()">Cancel</button>
              </div>
            }

            @if (sortedLinks().length > 0) {
              <table class="table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Activity</th>
                    <th>Required?</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (link of sortedLinks(); track link.id) {
                    <tr>
                      <td>{{ link.sortOrder }}</td>
                      <td class="name-cell">
                        {{ activityNameForId(link.activityTemplateId) }}
                        @if (activityHasAutomation(link.activityTemplateId)) {
                          <span class="badge badge-automation" title="Has linked infrastructure automation">Automated</span>
                        }
                      </td>
                      <td>
                        <span
                          class="badge"
                          [class.badge-required]="link.isRequired"
                          [class.badge-optional]="!link.isRequired"
                        >
                          {{ link.isRequired ? 'Required' : 'Optional' }}
                        </span>
                      </td>
                      <td>
                        <button
                          *nimbusHasPermission="'catalog:process:manage'"
                          class="btn-action btn-delete"
                          (click)="removeActivity(link)"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <div class="no-items">No activities linked to this process.</div>
            }
          </div>

          <!-- Assigned Services -->
          <div class="section-card">
            <div class="section-header">
              <h2 class="section-title">Assigned Services ({{ assignments().length }})</h2>
              <button
                *nimbusHasPermission="'catalog:process:manage'"
                class="btn-link"
                (click)="showAddAssignment.set(true)"
              >
                + Assign Service
              </button>
            </div>

            @if (showAddAssignment()) {
              <div class="add-form">
                <nimbus-searchable-select class="add-field" [(ngModel)]="assignOfferingId" [options]="offeringOptions()" placeholder="Select service offering..." />
                <select
                  class="form-input add-field-sm"
                  [(ngModel)]="assignCoverage"
                >
                  <option value="">No coverage</option>
                  <option value="business_hours">Business Hours</option>
                  <option value="extended">Extended</option>
                  <option value="24x7">24x7</option>
                </select>
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="assignIsDefault" />
                  <span>Default</span>
                </label>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="addAssignment()"
                  [disabled]="!assignOfferingId"
                >Assign</button>
                <button class="btn btn-sm btn-secondary" (click)="cancelAddAssignment()">Cancel</button>
              </div>
            }

            @if (assignments().length > 0) {
              <table class="table">
                <thead>
                  <tr>
                    <th>Service Offering</th>
                    <th>Coverage</th>
                    <th>Default?</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (a of assignments(); track a.id) {
                    <tr>
                      <td class="name-cell">{{ offeringNameForId(a.serviceOfferingId) }}</td>
                      <td>{{ a.coverageModel || '\u2014' }}</td>
                      <td>{{ a.isDefault ? 'Yes' : 'No' }}</td>
                      <td>
                        <button
                          *nimbusHasPermission="'catalog:process:manage'"
                          class="btn-action btn-delete"
                          (click)="removeAssignment(a)"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <div class="no-items">No services assigned to this process.</div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .editor-page { padding: 0; max-width: 960px; }

    .page-header {
      display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    .loading-state, .empty-state {
      text-align: center; color: #64748b; padding: 3rem; font-size: 0.875rem;
    }

    /* ── Section cards ────────────────────────────────────────────── */

    .section-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; margin-bottom: 1.25rem;
    }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.75rem;
    }
    .section-title {
      margin: 0 0 0.75rem; font-size: 0.9375rem; font-weight: 600; color: #1e293b;
    }
    .section-header .section-title { margin-bottom: 0; }

    /* ── Form ─────────────────────────────────────────────────────── */

    .form-row {
      display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;
    }
    .form-group { display: flex; flex-direction: column; flex: 1; min-width: 180px; }
    .form-group-sm { flex: 0 0 120px; min-width: 100px; }
    .form-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem;
    }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; }
    .form-actions { display: flex; gap: 0.5rem; }

    /* ── Add form ─────────────────────────────────────────────────── */

    .add-form {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem;
      flex-wrap: wrap;
    }
    .add-field { flex: 2; min-width: 200px; }
    .add-field-sm { flex: 0 0 80px; min-width: 60px; }
    .toggle-label {
      display: flex; align-items: center; gap: 0.375rem;
      font-size: 0.8125rem; color: #374151; cursor: pointer;
    }

    /* ── Table ─────────────────────────────────────────────────────── */

    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-required { background: #dbeafe; color: #2563eb; }
    .badge-optional { background: #f0fdf4; color: #16a34a; }
    .badge-automation {
      background: #f0fdf4; color: #166534; font-size: 0.625rem;
      padding: 1px 5px; border-radius: 3px; margin-left: 0.375rem;
      vertical-align: middle; font-weight: 600;
    }

    .no-items { color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* ── Buttons ─────────────────────────────────────────────────── */

    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; font-weight: 500;
      padding: 0; text-decoration: none;
    }
    .btn-link:hover { text-decoration: underline; }

    .btn-action {
      padding: 0.25rem 0.625rem; border-radius: 4px; font-size: 0.75rem;
      font-weight: 500; font-family: inherit; cursor: pointer; border: 1px solid transparent;
      transition: background 0.15s, color 0.15s;
    }
    .btn-delete {
      background: #fff; color: #dc2626; border-color: #fecaca;
    }
    .btn-delete:hover { background: #fef2f2; }

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
    .btn-back { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
  `],
})
export class ProcessEditorComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);
  private catalogService = inject(CatalogService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  process = signal<ServiceProcess | null>(null);
  activityTemplates = signal<ActivityTemplate[]>([]);
  assignments = signal<ServiceProcessAssignment[]>([]);
  loading = signal(false);
  showAddActivity = signal(false);
  offerings = signal<ServiceOffering[]>([]);
  showAddAssignment = signal(false);

  activityTemplateOptions = computed(() => this.activityTemplates().map(t => ({ value: t.id, label: t.name })));
  offeringOptions = computed(() => this.offerings().map(o => ({ value: o.id, label: o.name })));

  // Edit fields
  editName = '';
  editDescription = '';
  editSortOrder = 0;

  // Add activity fields
  addActivityTemplateId = '';
  addSortOrder = 0;
  addIsRequired = true;

  // Add assignment fields
  assignOfferingId = '';
  assignCoverage = '';
  assignIsDefault = false;

  sortedLinks = signal<ProcessActivityLink[]>([]);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadProcess(id);
    }
  }

  loadProcess(id: string): void {
    this.loading.set(true);
    forkJoin({
      process: this.deliveryService.getProcess(id),
      templates: this.deliveryService.listActivityTemplates({ limit: 500 }),
      assignments: this.deliveryService.listAssignments(),
      offerings: this.catalogService.listOfferings({ limit: 500 }),
    }).subscribe({
      next: ({ process, templates, assignments, offerings }) => {
        this.process.set(process);
        this.activityTemplates.set(templates.items);
        this.offerings.set(offerings.items);
        if (process) {
          this.editName = process.name;
          this.editDescription = process.description || '';
          this.editSortOrder = process.sortOrder;
          this.sortedLinks.set(
            [...process.activityLinks].sort((a, b) => a.sortOrder - b.sortOrder),
          );
          this.assignments.set(
            assignments.filter((a) => a.processId === process.id),
          );
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load process');
        this.loading.set(false);
      },
    });
  }

  saveDetails(): void {
    const p = this.process();
    if (!p) return;

    this.deliveryService.updateProcess(p.id, {
      name: this.editName.trim(),
      description: this.editDescription.trim() || null,
      sortOrder: this.editSortOrder,
    }).subscribe({
      next: (updated) => {
        this.process.set(updated);
        this.toastService.success('Process details updated');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to update process');
      },
    });
  }

  addActivity(): void {
    const p = this.process();
    if (!p || !this.addActivityTemplateId) return;

    this.deliveryService.addProcessActivityLink(p.id, {
      activityTemplateId: this.addActivityTemplateId,
      sortOrder: this.addSortOrder,
      isRequired: this.addIsRequired,
    }).subscribe({
      next: () => {
        this.toastService.success('Activity linked to process');
        this.cancelAddActivity();
        this.loadProcess(p.id);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to link activity');
      },
    });
  }

  cancelAddActivity(): void {
    this.showAddActivity.set(false);
    this.addActivityTemplateId = '';
    this.addSortOrder = 0;
    this.addIsRequired = true;
  }

  async removeActivity(link: ProcessActivityLink): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: 'Remove Activity',
      message: `Remove "${this.activityNameForId(link.activityTemplateId)}" from this process?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!confirmed) return;

    this.deliveryService.removeProcessActivityLink(link.id).subscribe({
      next: () => {
        this.toastService.success('Activity removed from process');
        const p = this.process();
        if (p) this.loadProcess(p.id);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to remove activity');
      },
    });
  }

  activityNameForId(templateId: string): string {
    const tpl = this.activityTemplates().find((t) => t.id === templateId);
    return tpl ? tpl.name : templateId.substring(0, 8) + '...';
  }

  activityHasAutomation(templateId: string): boolean {
    const tpl = this.activityTemplates().find((t) => t.id === templateId);
    return !!tpl?.automatedActivityId;
  }

  goBack(): void {
    this.router.navigate(['/catalog/processes']);
  }

  addAssignment(): void {
    const p = this.process();
    if (!p || !this.assignOfferingId) return;

    this.deliveryService.createAssignment({
      serviceOfferingId: this.assignOfferingId,
      processId: p.id,
      coverageModel: this.assignCoverage || null,
      isDefault: this.assignIsDefault,
    }).subscribe({
      next: (a) => {
        this.assignments.update((list) => [...list, a]);
        this.cancelAddAssignment();
        this.toastService.success('Service assigned to process');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to assign service');
      },
    });
  }

  cancelAddAssignment(): void {
    this.showAddAssignment.set(false);
    this.assignOfferingId = '';
    this.assignCoverage = '';
    this.assignIsDefault = false;
  }

  async removeAssignment(assignment: ServiceProcessAssignment): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: 'Remove Assignment',
      message: `Remove "${this.offeringNameForId(assignment.serviceOfferingId)}" from this process?`,
      confirmLabel: 'Remove',
      variant: 'danger',
    });
    if (!confirmed) return;

    this.deliveryService.deleteAssignment(assignment.id).subscribe({
      next: () => {
        this.assignments.update((list) => list.filter((a) => a.id !== assignment.id));
        this.toastService.success('Service assignment removed');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to remove assignment');
      },
    });
  }

  offeringNameForId(offeringId: string): string {
    const o = this.offerings().find((off) => off.id === offeringId);
    return o ? o.name : offeringId.substring(0, 8) + '...';
  }
}
