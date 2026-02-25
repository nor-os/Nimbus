/**
 * Overview: Activity template editor — create/edit process step templates with definitions
 *     and bidirectional CI class ↔ activity associations.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/delivery.service,
 *     app/core/services/catalog.service, app/core/services/cmdb.service
 * Concepts: Activity templates, activity definitions, staff profiles, effort estimation,
 *     CI class ↔ activity associations with relationship types
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
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { DeliveryService } from '@core/services/delivery.service';
import { CatalogService } from '@core/services/catalog.service';
import { CmdbService } from '@core/services/cmdb.service';
import { AutomatedActivityService } from '@core/services/automated-activity.service';
import {
  ActivityTemplate,
  ActivityDefinition,
  ActivityDefinitionCreateInput,
  ActivityDefinitionUpdateInput,
  LinkedAutomatedActivity,
  StaffProfile,
} from '@shared/models/delivery.model';
import { AutomatedActivity } from '@shared/models/automated-activity.model';
import { CIClass, CIClassActivityAssociation } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface DefinitionRow {
  /** null for unsaved rows */
  id: string | null;
  sortOrder: number;
  name: string;
  staffProfileId: string;
  estimatedHours: number;
  isOptional: boolean;
  /** Track whether this row has been modified from its persisted state */
  dirty: boolean;
  /** Track rows that exist on the server (for update vs create) */
  persisted: boolean;
}

@Component({
  selector: 'nimbus-activity-template-editor',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="editor-page">
        <div class="page-header">
          <h1>{{ isEditMode() ? 'Edit Activity' : 'Create Activity' }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading...</div>
        }

        @if (!loading()) {
          <!-- Template header form -->
          <div class="form">
            <div class="form-row">
              <div class="form-group form-group-wide">
                <label for="templateName">Template Name *</label>
                <input
                  id="templateName"
                  [formControl]="nameControl"
                  class="form-input"
                  placeholder="Activity template name"
                />
                @if (nameControl.hasError('required') && nameControl.touched) {
                  <span class="error">Name is required</span>
                }
              </div>
            </div>
            <div class="form-row">
              <div class="form-group form-group-wide">
                <label for="templateDesc">Description</label>
                <textarea
                  id="templateDesc"
                  [formControl]="descriptionControl"
                  class="form-input form-textarea"
                  placeholder="Optional description"
                  rows="2"
                ></textarea>
              </div>
            </div>
          </div>

          <!-- Activity definitions (steps) -->
          <div class="steps-section">
            <div class="steps-header">
              <h2>Steps</h2>
              <button class="btn btn-sm btn-add" (click)="addStep()">Add Step</button>
            </div>

            @if (definitions().length === 0) {
              <div class="empty-steps">No steps defined. Click "Add Step" to begin.</div>
            }

            @for (def of definitions(); track $index) {
              <div class="step-row">
                <div class="step-field step-field-order">
                  <label>Order</label>
                  <input
                    type="number"
                    class="form-input"
                    [value]="def.sortOrder"
                    (change)="onFieldChange($index, 'sortOrder', $event)"
                    min="0"
                  />
                </div>

                <div class="step-field step-field-name">
                  <label>Name *</label>
                  <input
                    type="text"
                    class="form-input"
                    [value]="def.name"
                    (input)="onFieldChange($index, 'name', $event)"
                    placeholder="Step name"
                  />
                </div>

                <div class="step-field step-field-profile">
                  <label>Staff Profile *</label>
                  <nimbus-searchable-select [ngModel]="def.staffProfileId" (ngModelChange)="onProfileChange($index, $event)" [options]="staffProfileOptions()" placeholder="Select profile..." />
                </div>

                <div class="step-field step-field-hours">
                  <label>Est. Hours *</label>
                  <input
                    type="number"
                    class="form-input"
                    [value]="def.estimatedHours"
                    (change)="onFieldChange($index, 'estimatedHours', $event)"
                    min="0"
                    step="0.5"
                  />
                </div>

                <div class="step-field step-field-optional">
                  <label>Optional</label>
                  <label class="toggle-label">
                    <input
                      type="checkbox"
                      [checked]="def.isOptional"
                      (change)="onToggleOptional($index)"
                    />
                    <span>{{ def.isOptional ? 'Yes' : 'No' }}</span>
                  </label>
                </div>

                <div class="step-field step-field-action">
                  <label>&nbsp;</label>
                  <button
                    class="btn btn-sm btn-remove"
                    (click)="removeStep($index)"
                    title="Remove step"
                  >
                    Remove
                  </button>
                </div>
              </div>
            }
          </div>

          <!-- Linked Automation (edit mode only) -->
          @if (isEditMode() && templateId) {
            <div class="assoc-section">
              <div class="assoc-header">
                <h2>Infrastructure Automation</h2>
              </div>

              @if (linkedAutomation()) {
                <div class="automation-link-card">
                  <div class="automation-info">
                    <span class="automation-name">{{ linkedAutomation()!.name }}</span>
                    <span class="badge badge-operation">{{ linkedAutomation()!.operationKind }}</span>
                    <span class="badge badge-impl">{{ formatImplType(linkedAutomation()!.implementationType) }}</span>
                    @if (linkedAutomation()!.isSystem) {
                      <span class="badge badge-system">System</span>
                    }
                    <span class="automation-slug">{{ linkedAutomation()!.slug }}</span>
                  </div>
                  <div class="automation-actions">
                    <a class="btn-link" [routerLink]="['/workflows/activities', linkedAutomation()!.id]">View</a>
                    <button class="btn btn-sm btn-remove" (click)="unlinkAutomation()">Unlink</button>
                  </div>
                </div>
              } @else {
                <div class="automation-picker">
                  <p class="picker-hint">Link an automated activity to enable infrastructure execution from this process step.</p>
                  <div class="assoc-add-form">
                    <div class="assoc-add-field">
                      <label>Activity</label>
                      <select class="form-input form-select" [(ngModel)]="linkActivityId">
                        <option value="">Select automated activity...</option>
                        @for (act of availableActivities(); track act.id) {
                          <option [value]="act.id">{{ act.name }} ({{ act.operationKind | lowercase }}, {{ act.category || 'uncategorized' }})</option>
                        }
                      </select>
                    </div>
                    <div class="assoc-add-field assoc-add-action">
                      <label>&nbsp;</label>
                      <button class="btn btn-sm btn-add" [disabled]="!linkActivityId" (click)="linkAutomation()">Link</button>
                    </div>
                  </div>
                </div>
              }
            </div>
          }

          <!-- CI Class Associations (edit mode only) -->
          @if (isEditMode() && templateId) {
            <div class="assoc-section">
              <div class="assoc-header">
                <h2>CI Class Associations</h2>
              </div>

              @if (ciClassAssociations().length === 0) {
                <div class="empty-assoc">No CI class associations yet.</div>
              }

              @for (assoc of ciClassAssociations(); track assoc.id) {
                <div class="assoc-row">
                  <span class="assoc-class">{{ assoc.ciClassDisplayName || assoc.ciClassName }}</span>
                  <span class="assoc-arrow">→</span>
                  <span class="assoc-type">{{ assoc.relationshipType || '—' }}</span>
                  <span class="assoc-arrow">→</span>
                  <span class="assoc-template">{{ assoc.activityTemplateName }}</span>
                  <button class="btn btn-sm btn-remove" (click)="removeAssociation(assoc.id)">Remove</button>
                </div>
              }

              <div class="assoc-add-form">
                <div class="assoc-add-field">
                  <label>CI Class</label>
                  <select class="form-input form-select" [(ngModel)]="newAssocCIClassId">
                    <option value="">Select CI class...</option>
                    @for (cls of allCIClasses(); track cls.id) {
                      <option [value]="cls.id">{{ cls.displayName }}</option>
                    }
                  </select>
                </div>
                <div class="assoc-add-field">
                  <label>Relationship Type</label>
                  <input
                    class="form-input"
                    [(ngModel)]="newAssocRelType"
                    placeholder="e.g. manages, monitors"
                    [attr.list]="'rel-type-suggestions'"
                  />
                  <datalist id="rel-type-suggestions">
                    @for (sug of relationshipTypeSuggestions(); track sug) {
                      <option [value]="sug"></option>
                    }
                  </datalist>
                </div>
                <div class="assoc-add-field assoc-add-action">
                  <label>&nbsp;</label>
                  <button
                    class="btn btn-sm btn-add"
                    [disabled]="!newAssocCIClassId"
                    (click)="addAssociation()"
                  >Add</button>
                </div>
              </div>
            </div>
          }

          <!-- Error message -->
          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <!-- Actions -->
          <div class="form-actions">
            <button
              class="btn btn-primary"
              [disabled]="saving() || nameControl.invalid"
              (click)="save()"
            >
              {{ saving() ? 'Saving...' : (isEditMode() ? 'Save Changes' : 'Create Template') }}
            </button>
            <button class="btn btn-secondary" (click)="cancel()">Cancel</button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .editor-page { padding: 0; max-width: 960px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* ── Template header form ─────────────────────────────────────────── */
    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .form-row { margin-bottom: 1rem; }
    .form-row:last-child { margin-bottom: 0; }
    .form-group { margin-bottom: 0; }
    .form-group-wide { width: 100%; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .form-textarea { resize: vertical; min-height: 50px; }
    .form-select { cursor: pointer; }
    .form-select option { background: #fff; color: #1e293b; }

    .error { color: #dc2626; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }

    /* ── Steps section ────────────────────────────────────────────────── */
    .steps-section { margin-bottom: 1.5rem; }
    .steps-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.75rem;
    }
    .steps-header h2 { margin: 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }

    .empty-steps {
      text-align: center; padding: 2rem; color: #94a3b8; font-size: 0.8125rem;
      background: #fff; border: 1px dashed #e2e8f0; border-radius: 8px;
    }

    .step-row {
      display: flex; gap: 0.75rem; align-items: flex-end;
      padding: 0.75rem 1rem; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; margin-bottom: 0.5rem;
    }
    .step-row:hover { border-color: #cbd5e1; }

    .step-field { display: flex; flex-direction: column; }
    .step-field label {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;
    }
    .step-field .form-input { width: 100%; }

    .step-field-order { width: 70px; flex-shrink: 0; }
    .step-field-name { flex: 1; min-width: 160px; }
    .step-field-profile { width: 200px; flex-shrink: 0; }
    .step-field-hours { width: 100px; flex-shrink: 0; }
    .step-field-optional { width: 80px; flex-shrink: 0; }
    .step-field-action { width: 80px; flex-shrink: 0; }

    .toggle-label {
      display: flex; align-items: center; gap: 0.375rem;
      font-size: 0.8125rem; color: #334155; cursor: pointer;
      padding: 0.375rem 0;
    }
    .toggle-label input[type="checkbox"] { cursor: pointer; }

    /* ── Buttons ──────────────────────────────────────────────────────── */
    .form-actions { display: flex; gap: 0.75rem; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem; border: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #334155; border: 1px solid #e2e8f0;
      padding: 0.5rem 1.5rem;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-add { color: #3b82f6; border-color: #bfdbfe; }
    .btn-add:hover { background: #eff6ff; }
    .btn-remove { color: #dc2626; border-color: #fecaca; }
    .btn-remove:hover { background: #fef2f2; }

    /* ── CI Class Associations ──────────────────────────────────────── */
    .assoc-section { margin-bottom: 1.5rem; }
    .assoc-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.75rem;
    }
    .assoc-header h2 { margin: 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }

    .empty-assoc {
      text-align: center; padding: 1.5rem; color: #94a3b8; font-size: 0.8125rem;
      background: #fff; border: 1px dashed #e2e8f0; border-radius: 8px;
      margin-bottom: 0.75rem;
    }

    .assoc-row {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.5rem 0.75rem; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; margin-bottom: 0.375rem; font-size: 0.8125rem;
    }
    .assoc-row:hover { border-color: #cbd5e1; }
    .assoc-class { font-weight: 600; color: #1e293b; }
    .assoc-arrow { color: #94a3b8; font-size: 0.75rem; }
    .assoc-type { color: #3b82f6; font-style: italic; }
    .assoc-template { color: #334155; flex: 1; }

    .assoc-add-form {
      display: flex; gap: 0.75rem; align-items: flex-end;
      padding: 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; margin-top: 0.75rem;
    }
    .assoc-add-field { display: flex; flex-direction: column; flex: 1; }
    .assoc-add-field label {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;
    }
    .assoc-add-action { flex: 0; }

    /* ── Automation link ───────────────────────────────────────────── */
    .automation-link-card {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 1rem; background: #f0fdf4; border: 1px solid #bbf7d0;
      border-radius: 8px;
    }
    .automation-info {
      display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
    }
    .automation-name { font-weight: 600; color: #1e293b; font-size: 0.875rem; }
    .automation-slug { font-size: 0.75rem; color: #94a3b8; font-family: monospace; }
    .automation-actions { display: flex; gap: 0.5rem; align-items: center; }
    .badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.6875rem; font-weight: 600; }
    .badge-operation { background: #dbeafe; color: #1d4ed8; }
    .badge-impl { background: #fef3c7; color: #92400e; }
    .badge-system { background: #e0e7ff; color: #3730a3; }
    .picker-hint { font-size: 0.8125rem; color: #64748b; margin: 0 0 0.75rem; }
  `],
})
export class ActivityTemplateEditorComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private catalogService = inject(CatalogService);
  private cmdbService = inject(CmdbService);
  private automatedActivityService = inject(AutomatedActivityService);
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  loading = signal(false);
  saving = signal(false);
  errorMessage = signal('');
  staffProfiles = signal<StaffProfile[]>([]);
  definitions = signal<DefinitionRow[]>([]);
  existingTemplate = signal<ActivityTemplate | null>(null);

  // Linked automation
  linkedAutomation = signal<LinkedAutomatedActivity | null>(null);
  availableActivities = signal<AutomatedActivity[]>([]);
  linkActivityId = '';

  // CI Class Associations
  ciClassAssociations = signal<CIClassActivityAssociation[]>([]);
  allCIClasses = signal<CIClass[]>([]);
  relationshipTypeSuggestions = signal<string[]>([]);
  newAssocCIClassId = '';
  newAssocRelType = '';

  staffProfileOptions = computed(() => this.staffProfiles().map(p => ({ value: p.id, label: p.displayName })));

  nameControl = this.fb.control('', [Validators.required]);
  descriptionControl = this.fb.control('');

  /** IDs of definitions that have been removed (need server-side deletion on save) */
  private removedDefinitionIds: string[] = [];
  templateId: string | null = null;

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam && idParam !== 'new') {
      this.templateId = idParam;
      this.isEditMode.set(true);
    }

    this.loadStaffProfiles();

    if (this.templateId) {
      this.loading.set(true);
      this.loadExistingTemplate(this.templateId);
      this.loadAssociationData(this.templateId);
      this.loadAvailableActivities();
    }
  }

  // ── Step management ──────────────────────────────────────────────

  addStep(): void {
    const currentDefs = this.definitions();
    const maxOrder = currentDefs.length > 0
      ? Math.max(...currentDefs.map((d) => d.sortOrder))
      : 0;

    this.definitions.update((defs) => [
      ...defs,
      {
        id: null,
        sortOrder: maxOrder + 1,
        name: '',
        staffProfileId: '',
        estimatedHours: 0,
        isOptional: false,
        dirty: true,
        persisted: false,
      },
    ]);
  }

  removeStep(index: number): void {
    const row = this.definitions()[index];
    if (row.id && row.persisted) {
      this.removedDefinitionIds.push(row.id);
    }
    this.definitions.update((defs) => defs.filter((_, i) => i !== index));
  }

  onFieldChange(index: number, field: string, event: Event): void {
    const el = event.target as HTMLInputElement | HTMLSelectElement;
    this.definitions.update((defs) => {
      const updated = [...defs];
      const row = { ...updated[index], dirty: true };

      switch (field) {
        case 'sortOrder':
          row.sortOrder = parseInt((el as HTMLInputElement).value, 10) || 0;
          break;
        case 'name':
          row.name = el.value;
          break;
        case 'staffProfileId':
          row.staffProfileId = el.value;
          break;
        case 'estimatedHours':
          row.estimatedHours = parseFloat((el as HTMLInputElement).value) || 0;
          break;
      }

      updated[index] = row;
      return updated;
    });
  }

  onProfileChange(index: number, value: string): void {
    this.definitions.update((defs) => {
      const updated = [...defs];
      updated[index] = { ...updated[index], staffProfileId: value, dirty: true };
      return updated;
    });
  }

  onToggleOptional(index: number): void {
    this.definitions.update((defs) => {
      const updated = [...defs];
      updated[index] = {
        ...updated[index],
        isOptional: !updated[index].isOptional,
        dirty: true,
      };
      return updated;
    });
  }

  // ── CI Class Associations ──────────────────────────────────────────

  addAssociation(): void {
    if (!this.newAssocCIClassId || !this.templateId) return;

    this.catalogService.createCIClassActivityAssociation({
      ciClassId: this.newAssocCIClassId,
      activityTemplateId: this.templateId,
      relationshipType: this.newAssocRelType || null,
    }).subscribe({
      next: (assoc) => {
        this.ciClassAssociations.update((list) => [...list, assoc]);
        this.newAssocCIClassId = '';
        this.newAssocRelType = '';
        this.toastService.success('Association added');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to add association');
      },
    });
  }

  removeAssociation(id: string): void {
    this.catalogService.deleteCIClassActivityAssociation(id).subscribe({
      next: () => {
        this.ciClassAssociations.update((list) => list.filter((a) => a.id !== id));
        this.toastService.success('Association removed');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to remove association');
      },
    });
  }

  // ── Automation link ──────────────────────────────────────────────

  linkAutomation(): void {
    if (!this.linkActivityId || !this.templateId) return;
    this.automatedActivityService.linkActivityTemplate(this.templateId, this.linkActivityId).subscribe({
      next: () => {
        const act = this.availableActivities().find(a => a.id === this.linkActivityId);
        if (act) {
          this.linkedAutomation.set({
            id: act.id,
            name: act.name,
            slug: act.slug,
            category: act.category,
            operationKind: act.operationKind,
            implementationType: act.implementationType,
            isSystem: act.isSystem,
          });
        }
        this.linkActivityId = '';
        this.toastService.success('Automation linked');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to link automation'),
    });
  }

  unlinkAutomation(): void {
    if (!this.templateId) return;
    this.automatedActivityService.unlinkActivityTemplate(this.templateId).subscribe({
      next: () => {
        this.linkedAutomation.set(null);
        this.toastService.success('Automation unlinked');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to unlink automation'),
    });
  }

  formatImplType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\bHttp\b/, 'HTTP');
  }

  // ── Save ─────────────────────────────────────────────────────────

  save(): void {
    if (this.nameControl.invalid) return;

    this.saving.set(true);
    this.errorMessage.set('');

    if (this.isEditMode() && this.templateId) {
      this.saveExisting(this.templateId);
    } else {
      this.saveNew();
    }
  }

  cancel(): void {
    this.router.navigate(['/catalog', 'processes']);
  }

  // ── Private helpers ──────────────────────────────────────────────

  private saveNew(): void {
    this.deliveryService.createActivityTemplate({
      name: this.nameControl.value!,
      description: this.descriptionControl.value || null,
    }).subscribe({
      next: (template) => {
        // Now save all definitions
        this.saveDefinitions(template.id, () => {
          this.toastService.success(`Template "${template.name}" created`);
          this.saving.set(false);
          this.router.navigate(['/catalog', 'activities', template.id]);
        });
      },
      error: (err) => {
        this.saving.set(false);
        const msg = err.message || 'Failed to create template';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private saveExisting(id: string): void {
    this.deliveryService.updateActivityTemplate(id, {
      name: this.nameControl.value!,
      description: this.descriptionControl.value || null,
    }).subscribe({
      next: (template) => {
        this.saveDefinitions(template.id, () => {
          this.toastService.success(`Template "${template.name}" updated`);
          this.saving.set(false);
          this.loadExistingTemplate(template.id);
        });
      },
      error: (err) => {
        this.saving.set(false);
        const msg = err.message || 'Failed to update template';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private saveDefinitions(templateId: string, onComplete: () => void): void {
    const defs = this.definitions();
    const operations: Array<ReturnType<typeof this.deliveryService.addActivityDefinition>> = [];

    // Delete removed definitions
    for (const removedId of this.removedDefinitionIds) {
      operations.push(this.deliveryService.deleteActivityDefinition(removedId) as any);
    }

    // Create or update definitions
    for (const def of defs) {
      if (!def.name.trim() || !def.staffProfileId) continue;

      if (def.persisted && def.id && def.dirty) {
        const updateInput: ActivityDefinitionUpdateInput = {
          name: def.name,
          staffProfileId: def.staffProfileId,
          estimatedHours: def.estimatedHours,
          sortOrder: def.sortOrder,
          isOptional: def.isOptional,
        };
        operations.push(this.deliveryService.updateActivityDefinition(def.id, updateInput) as any);
      } else if (!def.persisted) {
        const createInput: ActivityDefinitionCreateInput = {
          name: def.name,
          staffProfileId: def.staffProfileId,
          estimatedHours: def.estimatedHours,
          sortOrder: def.sortOrder,
          isOptional: def.isOptional,
        };
        operations.push(this.deliveryService.addActivityDefinition(templateId, createInput) as any);
      }
    }

    if (operations.length === 0) {
      this.removedDefinitionIds = [];
      onComplete();
      return;
    }

    forkJoin(operations).subscribe({
      next: () => {
        this.removedDefinitionIds = [];
        onComplete();
      },
      error: (err) => {
        this.saving.set(false);
        const msg = err.message || 'Failed to save step definitions';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private loadAssociationData(templateId: string): void {
    this.catalogService.listCIClassActivityAssociations({ activityTemplateId: templateId }).subscribe({
      next: (assocs) => this.ciClassAssociations.set(assocs),
      error: () => this.toastService.error('Failed to load CI class associations'),
    });

    this.cmdbService.listClasses().subscribe({
      next: (classes) => this.allCIClasses.set(classes),
      error: () => {},
    });

    this.catalogService.listRelationshipTypeSuggestions().subscribe({
      next: (suggestions) => this.relationshipTypeSuggestions.set(suggestions),
      error: () => {},
    });
  }

  private loadAvailableActivities(): void {
    this.automatedActivityService.listActivities({ limit: 500 }).subscribe({
      next: (list) => this.availableActivities.set(list),
      error: () => {},
    });
  }

  private loadStaffProfiles(): void {
    this.deliveryService.listStaffProfiles().subscribe({
      next: (profiles) => this.staffProfiles.set(profiles),
      error: () => {
        this.toastService.error('Failed to load staff profiles');
      },
    });
  }

  private loadExistingTemplate(id: string): void {
    this.deliveryService.getActivityTemplate(id).subscribe({
      next: (template) => {
        if (!template) {
          this.loading.set(false);
          this.toastService.error('Activity template not found');
          this.router.navigate(['/catalog', 'processes']);
          return;
        }

        this.existingTemplate.set(template);
        this.linkedAutomation.set(template.automatedActivity || null);
        this.nameControl.setValue(template.name);
        this.descriptionControl.setValue(template.description || '');

        const rows: DefinitionRow[] = template.definitions
          .slice()
          .sort((a, b) => a.sortOrder - b.sortOrder)
          .map((def) => ({
            id: def.id,
            sortOrder: def.sortOrder,
            name: def.name,
            staffProfileId: def.staffProfileId,
            estimatedHours: def.estimatedHours,
            isOptional: def.isOptional,
            dirty: false,
            persisted: true,
          }));

        this.definitions.set(rows);
        this.removedDefinitionIds = [];
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load activity template');
        this.router.navigate(['/catalog', 'processes']);
      },
    });
  }
}
