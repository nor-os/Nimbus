/**
 * Overview: CI template editor component -- create or edit a CI template with class selection,
 *     attribute key-value editing, tags, and active/inactive toggle.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/cmdb.service
 * Concepts: Template CRUD, JSON attribute editing, version tracking, active toggle
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators, FormGroup } from '@angular/forms';
import { CmdbService } from '@core/services/cmdb.service';
import {
  CIClass,
  CITemplate,
  CITemplateCreateInput,
  CITemplateUpdateInput,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-template-editor',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="template-editor-page">
        <div class="page-header">
          <h1>{{ isEditMode() ? 'Edit Template' : 'Create Template' }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading...</div>
        }

        @if (!loading()) {
          <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
            <!-- Name -->
            <div class="form-group">
              <label for="name">Name *</label>
              <input
                id="name"
                formControlName="name"
                class="form-input"
                placeholder="Template name"
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

            <!-- CI Class -->
            @if (!isEditMode()) {
              <div class="form-group">
                <label for="ciClassId">CI Class *</label>
                <select
                  id="ciClassId"
                  formControlName="ciClassId"
                  class="form-input form-select"
                >
                  <option value="">Select a class...</option>
                  @for (cls of classes(); track cls.id) {
                    <option [value]="cls.id">{{ cls.displayName }} ({{ cls.name }})</option>
                  }
                </select>
                @if (form.get('ciClassId')?.hasError('required') && form.get('ciClassId')?.touched) {
                  <span class="error">CI class is required</span>
                }
              </div>
            } @else {
              <div class="form-group">
                <label>CI Class</label>
                <div class="readonly-value">{{ existingTemplate()?.ciClassName || '\u2014' }}</div>
              </div>
            }

            <!-- Version (read-only for edits) -->
            @if (isEditMode()) {
              <div class="form-group">
                <label>Version</label>
                <div class="readonly-value">v{{ existingTemplate()?.version }}</div>
              </div>
            }

            <!-- Active toggle -->
            @if (isEditMode()) {
              <div class="form-group toggle-group">
                <label class="toggle-label">
                  <input
                    type="checkbox"
                    formControlName="isActive"
                    class="toggle-checkbox"
                  />
                  <span class="toggle-track">
                    <span class="toggle-thumb"></span>
                  </span>
                  <span class="toggle-text">{{ form.get('isActive')?.value ? 'Active' : 'Inactive' }}</span>
                </label>
              </div>
            }

            <!-- Attributes (key-value editor) -->
            <fieldset class="fieldset">
              <legend>
                Attributes
                <button type="button" class="btn-link-inline" (click)="addAttribute()">+ Add Attribute</button>
              </legend>
              @for (attr of attributeEntries(); track $index) {
                <div class="kv-row">
                  <input
                    class="form-input kv-key-input"
                    [value]="attr.key"
                    (input)="updateAttributeKey($index, $event)"
                    placeholder="Key"
                  />
                  <input
                    class="form-input kv-value-input"
                    [value]="attr.value"
                    (input)="updateAttributeValue($index, $event)"
                    placeholder="Value"
                  />
                  <button
                    type="button"
                    class="btn-icon-remove"
                    (click)="removeAttribute($index)"
                    title="Remove attribute"
                  >
                    &times;
                  </button>
                </div>
              }
              @if (attributeEntries().length === 0) {
                <div class="empty-hint">No attributes defined. Click "+ Add Attribute" to add one.</div>
              }
            </fieldset>

            <!-- Tags (key-value editor) -->
            <fieldset class="fieldset">
              <legend>
                Tags
                <button type="button" class="btn-link-inline" (click)="addTag()">+ Add Tag</button>
              </legend>
              @for (tag of tagEntries(); track $index) {
                <div class="kv-row">
                  <input
                    class="form-input kv-key-input"
                    [value]="tag.key"
                    (input)="updateTagKey($index, $event)"
                    placeholder="Key"
                  />
                  <input
                    class="form-input kv-value-input"
                    [value]="tag.value"
                    (input)="updateTagValue($index, $event)"
                    placeholder="Value"
                  />
                  <button
                    type="button"
                    class="btn-icon-remove"
                    (click)="removeTag($index)"
                    title="Remove tag"
                  >
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
                {{ submitting() ? 'Saving...' : (isEditMode() ? 'Update' : 'Create') }}
              </button>
              <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
            </div>
          </form>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .template-editor-page { padding: 0; max-width: 780px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading {
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

    /* Toggle switch */
    .toggle-group { margin-bottom: 1.25rem; }
    .toggle-label {
      display: flex; align-items: center; gap: 0.75rem; cursor: pointer;
      font-size: 0.8125rem; font-weight: 600; color: #374151;
    }
    .toggle-checkbox {
      position: absolute; opacity: 0; width: 0; height: 0;
    }
    .toggle-track {
      position: relative; display: inline-block; width: 40px; height: 22px;
      background: #cbd5e1; border-radius: 11px; transition: background 0.2s;
      flex-shrink: 0;
    }
    .toggle-checkbox:checked + .toggle-track {
      background: #3b82f6;
    }
    .toggle-thumb {
      position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
      background: #fff; border-radius: 50%; transition: transform 0.2s;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
    }
    .toggle-checkbox:checked + .toggle-track .toggle-thumb {
      transform: translateX(18px);
    }
    .toggle-text {
      font-weight: 500; color: #1e293b;
    }

    /* Fieldsets */
    .fieldset {
      border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem;
      margin-bottom: 1.25rem; background: #fafbfc;
    }
    .fieldset legend {
      font-size: 0.875rem; font-weight: 600; color: #1e293b;
      padding: 0 0.5rem; display: flex; align-items: center; gap: 0.75rem;
    }

    /* Key-value rows */
    .kv-row {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem;
    }
    .kv-key-input { flex: 1; }
    .kv-value-input { flex: 2; }
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
export class TemplateEditorComponent implements OnInit {
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
  existingTemplate = signal<CITemplate | null>(null);
  attributeEntries = signal<{ key: string; value: string }[]>([]);
  tagEntries = signal<{ key: string; value: string }[]>([]);

  form: FormGroup = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
    ciClassId: ['', [Validators.required]],
    isActive: [true],
  });

  private templateId: string | null = null;

  ngOnInit(): void {
    this.templateId = this.route.snapshot.paramMap.get('id') ?? null;
    this.isEditMode.set(!!this.templateId);

    this.loadClasses();

    if (this.templateId) {
      this.loading.set(true);
      this.loadExistingTemplate(this.templateId);
    }
  }

  // ── Attribute key-value helpers ───────────────────────────────────

  addAttribute(): void {
    this.attributeEntries.update((entries) => [...entries, { key: '', value: '' }]);
  }

  removeAttribute(index: number): void {
    this.attributeEntries.update((entries) => entries.filter((_, i) => i !== index));
  }

  updateAttributeKey(index: number, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.attributeEntries.update((entries) =>
      entries.map((e, i) => (i === index ? { ...e, key: value } : e)),
    );
  }

  updateAttributeValue(index: number, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.attributeEntries.update((entries) =>
      entries.map((e, i) => (i === index ? { ...e, value: value } : e)),
    );
  }

  // ── Tag key-value helpers ─────────────────────────────────────────

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

  // ── Form submission ───────────────────────────────────────────────

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    if (this.isEditMode() && this.templateId) {
      this.submitUpdate(this.templateId);
    } else {
      this.submitCreate();
    }
  }

  cancel(): void {
    this.router.navigate(['/cmdb', 'templates']);
  }

  // ── Private helpers ───────────────────────────────────────────────

  private submitCreate(): void {
    const values = this.form.value;
    const attributes = this.collectKeyValues(this.attributeEntries());
    const tags = this.collectKeyValues(this.tagEntries());

    const input: CITemplateCreateInput = {
      name: values.name,
      ciClassId: values.ciClassId,
      description: values.description || null,
      attributes: Object.keys(attributes).length > 0 ? attributes : null,
      tags: Object.keys(tags).length > 0 ? tags : null,
    };

    this.cmdbService.createTemplate(input).subscribe({
      next: (tpl) => {
        this.toastService.success(`Template "${tpl.name}" created`);
        this.router.navigate(['/cmdb', 'templates', tpl.id, 'edit']);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to create template';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private submitUpdate(templateId: string): void {
    const values = this.form.value;
    const attributes = this.collectKeyValues(this.attributeEntries());
    const tags = this.collectKeyValues(this.tagEntries());

    const input: CITemplateUpdateInput = {
      name: values.name,
      description: values.description || null,
      attributes: Object.keys(attributes).length > 0 ? attributes : null,
      tags: Object.keys(tags).length > 0 ? tags : null,
      isActive: values.isActive,
    };

    this.cmdbService.updateTemplate(templateId, input).subscribe({
      next: (tpl) => {
        this.toastService.success(`Template "${tpl.name}" updated`);
        this.existingTemplate.set(tpl);
        this.submitting.set(false);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to update template';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private collectKeyValues(entries: { key: string; value: string }[]): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const entry of entries) {
      const key = entry.key.trim();
      if (key) {
        result[key] = entry.value;
      }
    }
    return result;
  }

  private loadClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => this.classes.set(classes),
    });
  }

  private loadExistingTemplate(templateId: string): void {
    // Load templates to find the one we need. The service does not expose
    // a getTemplate(id) method, so we load with a large limit and match by id.
    this.cmdbService.listTemplates({ limit: 500 }).subscribe({
      next: (result) => {
        const tpl = result.items.find((t) => t.id === templateId);
        if (!tpl) {
          this.loading.set(false);
          this.toastService.error('Template not found');
          this.router.navigate(['/cmdb', 'templates']);
          return;
        }

        this.existingTemplate.set(tpl);
        this.form.patchValue({
          name: tpl.name,
          description: tpl.description || '',
          isActive: tpl.isActive,
        });

        // Remove ciClassId required validator in edit mode
        this.form.get('ciClassId')?.clearValidators();
        this.form.get('ciClassId')?.updateValueAndValidity();

        // Populate attributes
        if (tpl.attributes && Object.keys(tpl.attributes).length > 0) {
          const entries = Object.entries(tpl.attributes).map(([key, val]) => ({
            key,
            value: String(val ?? ''),
          }));
          this.attributeEntries.set(entries);
        }

        // Populate tags
        if (tpl.tags && Object.keys(tpl.tags).length > 0) {
          const entries = Object.entries(tpl.tags).map(([key, val]) => ({
            key,
            value: String(val ?? ''),
          }));
          this.tagEntries.set(entries);
        }

        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load template');
        this.router.navigate(['/cmdb', 'templates']);
      },
    });
  }
}
