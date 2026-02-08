/**
 * Overview: ABAC policy create/edit form with DSL expression editor and validation.
 * Architecture: Feature component for ABAC policy authoring (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/permission.service, app/shared/components/autocomplete
 * Concepts: ABAC, attribute-based access control, DSL expression editing, policy validation, permission autocomplete
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { PermissionService } from '@core/services/permission.service';
import { Permission } from '@core/models/permission.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { AutocompleteComponent, AutocompleteOption } from '@shared/components/autocomplete/autocomplete.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-abac-editor',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, AutocompleteComponent],
  template: `
    <nimbus-layout>
      <div class="abac-editor-page">
        <h1>{{ isEditMode() ? 'Edit ABAC Policy' : 'Create ABAC Policy' }}</h1>

        <div class="editor-layout">
          <div class="editor-main">
            <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
              <div class="form-group">
                <label for="name">Name *</label>
                <input id="name" formControlName="name" class="form-input" placeholder="Policy name" />
                @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                  <span class="error">Name is required</span>
                }
              </div>

              <div class="form-row">
                <div class="form-group form-group-half">
                  <label for="effect">Effect *</label>
                  <select id="effect" formControlName="effect" class="form-input">
                    <option value="allow">Allow</option>
                    <option value="deny">Deny</option>
                  </select>
                </div>

                <div class="form-group form-group-half">
                  <label for="priority">Priority</label>
                  <input id="priority" formControlName="priority" type="number" class="form-input" min="0" placeholder="0" />
                </div>
              </div>

              <div class="form-group">
                <label>Target Permission</label>
                @if (selectedPermissionLabel()) {
                  <div class="selected-permission">
                    <span class="selected-label">{{ selectedPermissionLabel() }}</span>
                    <button type="button" class="clear-btn" (click)="clearTargetPermission()">&times;</button>
                  </div>
                } @else {
                  <nimbus-autocomplete
                    [options]="permissionOptions()"
                    placeholder="Search permissions... (leave empty for all)"
                    (selected)="onPermissionSelected($event)"
                  />
                }
              </div>

              <div class="form-group">
                <label for="expression">Expression *</label>
                <textarea
                  id="expression"
                  formControlName="expression"
                  class="form-input expression-input"
                  rows="8"
                  placeholder="Enter ABAC expression..."
                ></textarea>
                @if (form.get('expression')?.hasError('required') && form.get('expression')?.touched) {
                  <span class="error">Expression is required</span>
                }

                <div class="expression-actions">
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    (click)="validateExpression()"
                    [disabled]="!form.get('expression')?.value || validating()"
                  >
                    {{ validating() ? 'Validating...' : 'Validate Expression' }}
                  </button>

                  @if (validationResult()) {
                    <span class="validation-result" [class.valid]="validationResult()!.valid" [class.invalid]="!validationResult()!.valid">
                      @if (validationResult()!.valid) {
                        &#10003; Expression is valid
                      } @else {
                        &#10007; {{ validationResult()!.error }}
                      }
                    </span>
                  }
                </div>
              </div>

              <div class="form-group">
                <label class="toggle-label">
                  <input type="checkbox" formControlName="isEnabled" />
                  <span>Enabled</span>
                </label>
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

          <aside class="syntax-help">
            <h3>Expression Syntax</h3>
            <div class="help-section">
              <h4>Operators</h4>
              <code>AND, OR, NOT, ==, !=, IN, CONTAINS</code>
            </div>
            <div class="help-section">
              <h4>User Attributes</h4>
              <code>user.department</code><br/>
              <code>user.role</code><br/>
              <code>user.level</code>
            </div>
            <div class="help-section">
              <h4>Resource Attributes</h4>
              <code>resource.type</code><br/>
              <code>resource.owner</code><br/>
              <code>resource.classification</code>
            </div>
            <div class="help-section">
              <h4>Context</h4>
              <code>context.mfa_verified</code><br/>
              <code>context.ip</code><br/>
              <code>context.time</code>
            </div>
            <div class="help-section">
              <h4>Examples</h4>
              <pre>user.department == "engineering"
AND resource.classification != "secret"</pre>
              <pre>context.mfa_verified == true
OR user.level >= 3</pre>
            </div>
          </aside>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .abac-editor-page { padding: 0; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; }
    .editor-layout { display: flex; gap: 1.5rem; align-items: flex-start; }
    .editor-main { flex: 1; min-width: 0; }
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
    .expression-input {
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.8125rem; line-height: 1.6; resize: vertical; min-height: 160px;
    }
    .expression-actions { display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; }
    .validation-result { font-size: 0.8125rem; font-weight: 500; }
    .validation-result.valid { color: #16a34a; }
    .validation-result.invalid { color: #dc2626; }
    .toggle-label {
      display: flex; align-items: center; gap: 0.5rem; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #374151;
    }
    .toggle-label input[type="checkbox"] { accent-color: #3b82f6; }
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
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1.5rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover:not(:disabled) { background: #f8fafc; }
    .btn-sm { padding: 0.375rem 0.75rem; }
    .selected-permission {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      background: #f8fafc; font-size: 0.8125rem;
    }
    .selected-label { flex: 1; color: #1e293b; font-weight: 500; }
    .clear-btn {
      background: none; border: none; cursor: pointer; font-size: 1.125rem;
      color: #94a3b8; line-height: 1; padding: 0 0.25rem;
    }
    .clear-btn:hover { color: #dc2626; }
    .syntax-help {
      width: 260px; flex-shrink: 0; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.25rem; position: sticky; top: 1.5rem;
    }
    .syntax-help h3 {
      font-size: 0.875rem; font-weight: 700; color: #1e293b;
      margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;
    }
    .help-section { margin-bottom: 1rem; }
    .help-section h4 {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 0.375rem 0;
    }
    .help-section code {
      font-size: 0.75rem; color: #1e293b; background: #f8fafc;
      padding: 0.125rem 0.25rem; border-radius: 3px;
    }
    .help-section pre {
      font-size: 0.6875rem; color: #374151; background: #f8fafc;
      padding: 0.5rem; border-radius: 4px; margin: 0.375rem 0 0;
      white-space: pre-wrap; line-height: 1.5; border: 1px solid #f1f5f9;
    }
  `],
})
export class ABACEditorComponent implements OnInit {
  private fb = inject(FormBuilder);
  private permissionService = inject(PermissionService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  submitting = signal(false);
  validating = signal(false);
  errorMessage = signal('');
  validationResult = signal<{ valid: boolean; error: string | null } | null>(null);
  permissionOptions = signal<AutocompleteOption[]>([]);
  selectedPermissionLabel = signal('');
  private allPermissions: Permission[] = [];

  private policyId = '';

  form = this.fb.group({
    name: ['', Validators.required],
    effect: ['allow' as 'allow' | 'deny', Validators.required],
    priority: [0],
    targetPermission: [''],
    expression: ['', Validators.required],
    isEnabled: [true],
  });

  ngOnInit(): void {
    this.policyId = this.route.snapshot.params['id'] || '';
    this.loadPermissions();
    if (this.policyId) {
      this.isEditMode.set(true);
      this.loadPolicy();
    }
  }

  onPermissionSelected(option: AutocompleteOption): void {
    this.form.patchValue({ targetPermission: option.id });
    this.selectedPermissionLabel.set(option.label);
  }

  clearTargetPermission(): void {
    this.form.patchValue({ targetPermission: '' });
    this.selectedPermissionLabel.set('');
  }

  validateExpression(): void {
    const expr = this.form.get('expression')?.value;
    if (!expr) return;

    this.validating.set(true);
    this.validationResult.set(null);

    this.permissionService.validateABACExpression(expr).subscribe({
      next: (result) => {
        this.validationResult.set(result);
        this.validating.set(false);
      },
      error: () => {
        this.validationResult.set({ valid: false, error: 'Validation request failed' });
        this.validating.set(false);
      },
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;
    const payload = {
      name: values.name!,
      expression: values.expression!,
      effect: values.effect as 'allow' | 'deny',
      priority: values.priority ?? 0,
      is_enabled: values.isEnabled ?? true,
      target_permission_id: values.targetPermission || null,
    };

    if (this.isEditMode()) {
      this.permissionService.updateABACPolicy(this.policyId, payload).subscribe({
        next: () => {
          this.toastService.success('ABAC policy updated');
          this.router.navigate(['/permissions/abac']);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to update policy';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    } else {
      this.permissionService.createABACPolicy(payload).subscribe({
        next: () => {
          this.toastService.success('ABAC policy created');
          this.router.navigate(['/permissions/abac']);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to create policy';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    }
  }

  cancel(): void {
    this.router.navigate(['/permissions/abac']);
  }

  private loadPermissions(): void {
    this.permissionService.listPermissions().subscribe({
      next: (permissions) => {
        this.allPermissions = permissions;
        this.permissionOptions.set(
          permissions.map((p) => ({
            id: p.id,
            label: p.key,
            sublabel: p.description || undefined,
          })),
        );
        // If editing, resolve the label now that permissions are loaded
        const currentId = this.form.get('targetPermission')?.value;
        if (currentId) {
          this.resolvePermissionLabel(currentId);
        }
      },
    });
  }

  private loadPolicy(): void {
    this.permissionService.getABACPolicy(this.policyId).subscribe({
      next: (policy) => {
        this.form.patchValue({
          name: policy.name,
          effect: policy.effect,
          priority: policy.priority,
          targetPermission: policy.target_permission_id || '',
          expression: policy.expression,
          isEnabled: policy.is_enabled,
        });
        if (policy.target_permission_id) {
          this.resolvePermissionLabel(policy.target_permission_id);
        }
      },
    });
  }

  private resolvePermissionLabel(permissionId: string): void {
    const perm = this.allPermissions.find((p) => p.id === permissionId);
    if (perm) {
      this.selectedPermissionLabel.set(perm.key);
    }
  }
}
