/**
 * Overview: CI form component — create or edit a configuration item.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/cmdb.service
 * Concepts: Dynamic form generation from CI class schema, attribute validation
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
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators, FormGroup } from '@angular/forms';
import { CmdbService } from '@core/services/cmdb.service';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import {
  CIClass,
  CIClassDetail,
  CIAttributeDefinition,
  ConfigurationItem,
  LifecycleState,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

const LIFECYCLE_STATES: LifecycleState[] = ['planned', 'active', 'maintenance', 'retired'];

@Component({
  selector: 'nimbus-ci-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="ci-form-page">
        <div class="page-header">
          <h1>{{ isEditMode() ? 'Edit Configuration Item' : 'Create Configuration Item' }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading...</div>
        }

        @if (!loading()) {
          <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
            @if (!isEditMode()) {
              <!-- Create mode: CI Class first -->
              <div class="form-group">
                <label for="ciClassId">CI Class *</label>
                <nimbus-searchable-select
                  formControlName="ciClassId"
                  [options]="classOptions()"
                  placeholder="Select a class..."
                  [allowClear]="true"
                />
                @if (form.get('ciClassId')?.hasError('required') && form.get('ciClassId')?.touched) {
                  <span class="error">CI class is required</span>
                }
                @if (!form.get('ciClassId')?.value) {
                  <span class="field-hint">Select the type of configuration item to create</span>
                }
              </div>

              @if (!selectedClassDetail() && form.get('ciClassId')?.value) {
                <div class="loading-attrs">Loading class schema...</div>
              }

              @if (selectedClassDetail()) {
                <!-- Name -->
                <div class="form-group">
                  <label for="name">Name *</label>
                  <input
                    id="name"
                    formControlName="name"
                    class="form-input"
                    placeholder="Configuration item name"
                  />
                  @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                    <span class="error">Name is required</span>
                  }
                </div>

                <!-- Description -->
                <div class="form-group">
                  <label for="description">Description</label>
                  <textarea
                    id="description"
                    formControlName="description"
                    class="form-input form-textarea"
                    placeholder="Optional description"
                    rows="3"
                  ></textarea>
                </div>

                <!-- Lifecycle State -->
                <div class="form-group">
                  <label for="lifecycleState">Lifecycle State</label>
                  <select
                    id="lifecycleState"
                    formControlName="lifecycleState"
                    class="form-input form-select"
                  >
                    @for (state of lifecycleStates; track state) {
                      <option [value]="state">{{ state | titlecase }}</option>
                    }
                  </select>
                </div>

                <!-- Dynamic Attributes -->
                @if (selectedClassDetail(); as classDetail) {
                  @if (classDetail.attributeDefinitions.length > 0) {
                    <fieldset class="fieldset">
                      <legend>Attributes ({{ classDetail.displayName }})</legend>
                      @for (attrDef of classDetail.attributeDefinitions; track attrDef.id) {
                        <div class="form-group">
                          <label [for]="'attr_' + attrDef.name">
                            {{ attrDef.displayName }}{{ attrDef.isRequired ? ' *' : '' }}
                            <span class="attr-type">({{ attrDef.dataType }})</span>
                          </label>
                          @switch (attrDef.dataType) {
                            @case ('boolean') {
                              <select
                                [id]="'attr_' + attrDef.name"
                                [formControlName]="'attr_' + attrDef.name"
                                class="form-input form-select"
                              >
                                <option value="">Not set</option>
                                <option value="true">True</option>
                                <option value="false">False</option>
                              </select>
                            }
                            @case ('integer') {
                              <input
                                [id]="'attr_' + attrDef.name"
                                [formControlName]="'attr_' + attrDef.name"
                                type="number"
                                class="form-input"
                                step="1"
                                [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                              />
                            }
                            @case ('float') {
                              <input
                                [id]="'attr_' + attrDef.name"
                                [formControlName]="'attr_' + attrDef.name"
                                type="number"
                                class="form-input"
                                step="any"
                                [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                              />
                            }
                            @default {
                              <input
                                [id]="'attr_' + attrDef.name"
                                [formControlName]="'attr_' + attrDef.name"
                                class="form-input"
                                [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                              />
                            }
                          }
                          @if (form.get('attr_' + attrDef.name)?.hasError('required') && form.get('attr_' + attrDef.name)?.touched) {
                            <span class="error">{{ attrDef.displayName }} is required</span>
                          }
                        </div>
                      }
                    </fieldset>
                  }
                }

                <!-- Tags (key-value pairs) -->
                <fieldset class="fieldset" formGroupName="tagsGroup">
                  <legend>
                    Tags
                    <button type="button" class="btn-link-inline" (click)="addTag()">+ Add Tag</button>
                  </legend>
                  @for (tag of tagEntries(); track $index) {
                    <div class="tag-row">
                      <input
                        class="form-input tag-key-input"
                        [value]="tag.key"
                        (input)="updateTagKey($index, $event)"
                        placeholder="Key"
                      />
                      <input
                        class="form-input tag-value-input"
                        [value]="tag.value"
                        (input)="updateTagValue($index, $event)"
                        placeholder="Value"
                      />
                      <button type="button" class="btn-icon-remove" (click)="removeTag($index)" title="Remove tag">
                        &times;
                      </button>
                    </div>
                  }
                  @if (tagEntries().length === 0) {
                    <div class="empty-hint">No tags defined. Click "+ Add Tag" to add one.</div>
                  }
                </fieldset>

                <!-- Error message -->
                @if (errorMessage()) {
                  <div class="form-error">{{ errorMessage() }}</div>
                }

                <!-- Actions -->
                <div class="form-actions">
                  <button
                    type="submit"
                    class="btn btn-primary"
                    [disabled]="form.invalid || submitting()"
                  >
                    {{ submitting() ? 'Saving...' : 'Create' }}
                  </button>
                  <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
                </div>
              }
            } @else {
              <!-- Edit mode: CI Class readonly at top, then all fields -->
              <div class="form-group">
                <label>CI Class</label>
                <div class="readonly-value">{{ existingCI()?.ciClassName || '\u2014' }}</div>
              </div>

              <!-- Name -->
              <div class="form-group">
                <label for="name">Name *</label>
                <input
                  id="name"
                  formControlName="name"
                  class="form-input"
                  placeholder="Configuration item name"
                />
                @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                  <span class="error">Name is required</span>
                }
              </div>

              <!-- Description -->
              <div class="form-group">
                <label for="description">Description</label>
                <textarea
                  id="description"
                  formControlName="description"
                  class="form-input form-textarea"
                  placeholder="Optional description"
                  rows="3"
                ></textarea>
              </div>

              <!-- Dynamic Attributes -->
              @if (selectedClassDetail(); as classDetail) {
                @if (classDetail.attributeDefinitions.length > 0) {
                  <fieldset class="fieldset">
                    <legend>Attributes ({{ classDetail.displayName }})</legend>
                    @for (attrDef of classDetail.attributeDefinitions; track attrDef.id) {
                      <div class="form-group">
                        <label [for]="'attr_' + attrDef.name">
                          {{ attrDef.displayName }}{{ attrDef.isRequired ? ' *' : '' }}
                          <span class="attr-type">({{ attrDef.dataType }})</span>
                        </label>
                        @switch (attrDef.dataType) {
                          @case ('boolean') {
                            <select
                              [id]="'attr_' + attrDef.name"
                              [formControlName]="'attr_' + attrDef.name"
                              class="form-input form-select"
                            >
                              <option value="">Not set</option>
                              <option value="true">True</option>
                              <option value="false">False</option>
                            </select>
                          }
                          @case ('integer') {
                            <input
                              [id]="'attr_' + attrDef.name"
                              [formControlName]="'attr_' + attrDef.name"
                              type="number"
                              class="form-input"
                              step="1"
                              [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                            />
                          }
                          @case ('float') {
                            <input
                              [id]="'attr_' + attrDef.name"
                              [formControlName]="'attr_' + attrDef.name"
                              type="number"
                              class="form-input"
                              step="any"
                              [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                            />
                          }
                          @default {
                            <input
                              [id]="'attr_' + attrDef.name"
                              [formControlName]="'attr_' + attrDef.name"
                              class="form-input"
                              [placeholder]="attrDef.defaultValue != null ? 'Default: ' + attrDef.defaultValue : ''"
                            />
                          }
                        }
                        @if (form.get('attr_' + attrDef.name)?.hasError('required') && form.get('attr_' + attrDef.name)?.touched) {
                          <span class="error">{{ attrDef.displayName }} is required</span>
                        }
                      </div>
                    }
                  </fieldset>
                }
              }

              <!-- Schema-based attributes fallback (edit mode without attribute definitions) -->
              @if (!selectedClassDetail()) {
                @if (existingAttrKeys().length > 0) {
                  <fieldset class="fieldset">
                    <legend>Attributes</legend>
                    @for (key of existingAttrKeys(); track key) {
                      <div class="form-group">
                        <label [for]="'attr_' + key">{{ key }}</label>
                        <input
                          [id]="'attr_' + key"
                          [formControlName]="'attr_' + key"
                          class="form-input"
                        />
                      </div>
                    }
                  </fieldset>
                }
              }

              <!-- Tags (key-value pairs) -->
              <fieldset class="fieldset" formGroupName="tagsGroup">
                <legend>
                  Tags
                  <button type="button" class="btn-link-inline" (click)="addTag()">+ Add Tag</button>
                </legend>
                @for (tag of tagEntries(); track $index) {
                  <div class="tag-row">
                    <input
                      class="form-input tag-key-input"
                      [value]="tag.key"
                      (input)="updateTagKey($index, $event)"
                      placeholder="Key"
                    />
                    <input
                      class="form-input tag-value-input"
                      [value]="tag.value"
                      (input)="updateTagValue($index, $event)"
                      placeholder="Value"
                    />
                    <button type="button" class="btn-icon-remove" (click)="removeTag($index)" title="Remove tag">
                      &times;
                    </button>
                  </div>
                }
                @if (tagEntries().length === 0) {
                  <div class="empty-hint">No tags defined. Click "+ Add Tag" to add one.</div>
                }
              </fieldset>

              <!-- Error message -->
              @if (errorMessage()) {
                <div class="form-error">{{ errorMessage() }}</div>
              }

              <!-- Actions -->
              <div class="form-actions">
                <button
                  type="submit"
                  class="btn btn-primary"
                  [disabled]="form.invalid || submitting()"
                >
                  {{ submitting() ? 'Saving...' : 'Update' }}
                </button>
                <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
              </div>
            }
          </form>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .ci-form-page { padding: 0; max-width: 780px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading, .loading-attrs {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1.25rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .attr-type {
      font-weight: 400; color: #94a3b8; font-size: 0.75rem; margin-left: 0.25rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    .form-textarea { resize: vertical; min-height: 60px; }
    .form-select { cursor: pointer; }
    .readonly-value {
      padding: 0.5rem 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; color: #64748b;
    }

    .fieldset {
      border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem;
      margin-bottom: 1.25rem; background: #fafbfc;
    }
    .fieldset legend {
      font-size: 0.875rem; font-weight: 600; color: #1e293b;
      padding: 0 0.5rem; display: flex; align-items: center; gap: 0.75rem;
    }

    .tag-row {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem;
    }
    .tag-key-input { flex: 1; }
    .tag-value-input { flex: 2; }
    .btn-icon-remove {
      background: none; border: 1px solid #fecaca; border-radius: 6px;
      color: #dc2626; cursor: pointer; font-size: 1.125rem; line-height: 1;
      width: 32px; height: 32px; display: flex; align-items: center;
      justify-content: center; flex-shrink: 0; transition: background 0.15s;
    }
    .btn-icon-remove:hover { background: #fef2f2; }
    .btn-link-inline {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; font-weight: 500;
      padding: 0; text-decoration: none;
    }
    .btn-link-inline:hover { text-decoration: underline; }
    .empty-hint {
      color: #94a3b8; font-size: 0.75rem; padding: 0.5rem 0;
    }

    .field-hint {
      color: #64748b; font-size: 0.75rem; margin-top: 0.375rem; display: block;
    }
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }

    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1.5rem;
      transition: background 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
  `],
})
export class CIFormComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');

  classes = signal<CIClass[]>([]);
  selectedClassDetail = signal<CIClassDetail | null>(null);
  existingCI = signal<ConfigurationItem | null>(null);
  tagEntries = signal<{ key: string; value: string }[]>([]);

  readonly lifecycleStates = LIFECYCLE_STATES;

  /** Keys from existing CI attributes (edit mode fallback). */
  existingAttrKeys = computed(() => {
    const ci = this.existingCI();
    if (!ci?.attributes) return [];
    return Object.keys(ci.attributes).sort();
  });

  classOptions = computed(() =>
    this.classes().map(cls => ({ value: cls.id, label: `${cls.displayName} (${cls.name})` })),
  );

  form: FormGroup = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
    ciClassId: ['', [Validators.required]],
    compartmentId: [''],
    lifecycleState: ['planned'],
    tagsGroup: this.fb.group({}),
  });

  private ciId: string | null = null;

  ngOnInit(): void {
    this.ciId = this.route.snapshot.paramMap.get('id') ?? null;
    this.isEditMode.set(!!this.ciId);

    this.loadClasses();

    // React to CI class changes via formControl valueChanges (replaces native (change) event)
    this.form.get('ciClassId')?.valueChanges.subscribe(() => this.onClassChange());

    if (this.ciId) {
      this.loading.set(true);
      this.loadExistingCI(this.ciId);
    }
  }

  onClassChange(): void {
    const classId = this.form.get('ciClassId')?.value;
    if (!classId) {
      this.selectedClassDetail.set(null);
      this.removeAttributeControls();
      return;
    }
    this.loadClassDetail(classId);
  }

  addTag(): void {
    this.tagEntries.update((entries) => [...entries, { key: '', value: '' }]);
  }

  removeTag(index: number): void {
    this.tagEntries.update((entries) => entries.filter((_, i) => i !== index));
  }

  updateTagKey(index: number, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.tagEntries.update((entries) =>
      entries.map((e, i) => (i === index ? { ...e, key: value } : e)),
    );
  }

  updateTagValue(index: number, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.tagEntries.update((entries) =>
      entries.map((e, i) => (i === index ? { ...e, value: value } : e)),
    );
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    if (this.isEditMode() && this.ciId) {
      this.submitUpdate(this.ciId);
    } else {
      this.submitCreate();
    }
  }

  cancel(): void {
    if (this.isEditMode() && this.ciId) {
      this.router.navigate(['/cmdb', this.ciId]);
    } else {
      this.router.navigate(['/cmdb']);
    }
  }

  // ── Private helpers ─────────────────────────────────────────────

  private submitCreate(): void {
    const values = this.form.value;
    const attributes = this.collectAttributes();
    const tags = this.collectTags();

    this.cmdbService.createCI({
      ciClassId: values.ciClassId,
      name: values.name,
      description: values.description || null,
      compartmentId: values.compartmentId || null,
      lifecycleState: values.lifecycleState || 'planned',
      attributes: Object.keys(attributes).length > 0 ? attributes : null,
      tags: Object.keys(tags).length > 0 ? tags : null,
    }).subscribe({
      next: (ci) => {
        this.toastService.success(`"${ci.name}" created`);
        this.router.navigate(['/cmdb', ci.id]);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to create configuration item';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private submitUpdate(ciId: string): void {
    const values = this.form.value;
    const attributes = this.collectAttributes();
    const tags = this.collectTags();

    this.cmdbService.updateCI(ciId, {
      name: values.name,
      description: values.description || null,
      attributes: Object.keys(attributes).length > 0 ? attributes : null,
      tags: Object.keys(tags).length > 0 ? tags : null,
    }).subscribe({
      next: (ci) => {
        this.toastService.success(`"${ci.name}" updated`);
        this.router.navigate(['/cmdb', ci.id]);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to update configuration item';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private collectAttributes(): Record<string, unknown> {
    const attrs: Record<string, unknown> = {};
    const classDetail = this.selectedClassDetail();

    if (classDetail) {
      for (const attrDef of classDetail.attributeDefinitions) {
        const controlName = 'attr_' + attrDef.name;
        const rawValue = this.form.get(controlName)?.value;
        if (rawValue !== '' && rawValue !== null && rawValue !== undefined) {
          attrs[attrDef.name] = this.coerceAttributeValue(rawValue, attrDef.dataType);
        }
      }
    } else {
      // Edit mode fallback: collect from existing attribute keys
      for (const key of this.existingAttrKeys()) {
        const controlName = 'attr_' + key;
        const rawValue = this.form.get(controlName)?.value;
        if (rawValue !== '' && rawValue !== null && rawValue !== undefined) {
          attrs[key] = rawValue;
        }
      }
    }

    return attrs;
  }

  private coerceAttributeValue(value: string, dataType: string): unknown {
    if (dataType === 'boolean') {
      return value === 'true';
    }
    if (dataType === 'integer') {
      const parsed = parseInt(value, 10);
      return isNaN(parsed) ? value : parsed;
    }
    if (dataType === 'float') {
      const parsed = parseFloat(value);
      return isNaN(parsed) ? value : parsed;
    }
    return value;
  }

  private collectTags(): Record<string, string> {
    const tags: Record<string, string> = {};
    for (const entry of this.tagEntries()) {
      const key = entry.key.trim();
      if (key) {
        tags[key] = entry.value;
      }
    }
    return tags;
  }

  private loadClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => this.classes.set(classes),
    });
  }

  private loadExistingCI(ciId: string): void {
    this.cmdbService.getCI(ciId).subscribe({
      next: (ci) => {
        if (!ci) {
          this.loading.set(false);
          this.toastService.error('Configuration item not found');
          this.router.navigate(['/cmdb']);
          return;
        }

        this.existingCI.set(ci);
        this.form.patchValue({
          name: ci.name,
          description: ci.description || '',
        });

        // Remove ciClassId required validator in edit mode
        this.form.get('ciClassId')?.clearValidators();
        this.form.get('ciClassId')?.updateValueAndValidity();

        // Populate tags
        if (ci.tags) {
          const entries = Object.entries(ci.tags).map(([key, val]) => ({
            key,
            value: String(val ?? ''),
          }));
          this.tagEntries.set(entries);
        }

        // Load class detail for attribute definitions
        this.cmdbService.getClass(ci.ciClassId).subscribe({
          next: (classDetail) => {
            if (classDetail) {
              this.selectedClassDetail.set(classDetail);
              this.buildAttributeControls(classDetail.attributeDefinitions, ci.attributes);
            } else {
              // Fallback: create controls from existing attribute keys
              this.buildFallbackAttributeControls(ci.attributes);
            }
            this.loading.set(false);
          },
          error: () => {
            this.buildFallbackAttributeControls(ci.attributes);
            this.loading.set(false);
          },
        });
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load configuration item');
        this.router.navigate(['/cmdb']);
      },
    });
  }

  private loadClassDetail(classId: string): void {
    this.removeAttributeControls();
    this.cmdbService.getClass(classId).subscribe({
      next: (classDetail) => {
        this.selectedClassDetail.set(classDetail);
        if (classDetail) {
          this.buildAttributeControls(classDetail.attributeDefinitions);
        }
      },
    });
  }

  private buildAttributeControls(
    definitions: CIAttributeDefinition[],
    existingValues?: Record<string, unknown>,
  ): void {
    this.removeAttributeControls();
    for (const attrDef of definitions) {
      const controlName = 'attr_' + attrDef.name;
      const existingVal = existingValues?.[attrDef.name];
      const defaultVal = existingVal != null ? String(existingVal) : '';
      const validators = attrDef.isRequired ? [Validators.required] : [];
      this.form.addControl(controlName, this.fb.control(defaultVal, validators));
    }
  }

  private buildFallbackAttributeControls(attributes: Record<string, unknown>): void {
    this.removeAttributeControls();
    if (!attributes) return;
    for (const key of Object.keys(attributes).sort()) {
      const controlName = 'attr_' + key;
      const value = attributes[key];
      this.form.addControl(controlName, this.fb.control(value != null ? String(value) : ''));
    }
  }

  private removeAttributeControls(): void {
    const controlNames = Object.keys(this.form.controls).filter((k) => k.startsWith('attr_'));
    for (const name of controlNames) {
      this.form.removeControl(name);
    }
  }

}
