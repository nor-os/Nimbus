/**
 * Overview: Reactive form for creating tenants with hierarchy validation.
 * Architecture: Feature component for tenant creation (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/tenant.service
 * Concepts: Multi-tenancy, reactive forms, 3-level hierarchy limit
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TenantService } from '@core/services/tenant.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-tenant-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="tenant-form-page">
        <h1>Create Tenant</h1>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
          <div class="form-group">
            <label for="name">Name *</label>
            <input id="name" formControlName="name" class="form-input" />
            @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
              <span class="error">Name is required</span>
            }
          </div>

          <div class="form-group">
            <label for="parentId">Parent Tenant</label>
            <select id="parentId" formControlName="parentId" class="form-input">
              <option value="">None (root tenant)</option>
              @for (tenant of availableParents(); track tenant.id) {
                <option [value]="tenant.id">
                  {{ '  '.repeat(tenant.level) }}{{ tenant.name }}
                </option>
              }
            </select>
          </div>

          <div class="form-group">
            <label for="contactEmail">Contact Email</label>
            <input id="contactEmail" formControlName="contactEmail" type="email" class="form-input" />
            @if (form.get('contactEmail')?.hasError('email') && form.get('contactEmail')?.touched) {
              <span class="error">Invalid email format</span>
            }
          </div>

          <div class="form-group">
            <label for="description">Description</label>
            <textarea id="description" formControlName="description" class="form-input" rows="3"></textarea>
          </div>

          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
              {{ submitting() ? 'Saving...' : 'Create' }}
            </button>
            <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
          </div>
        </form>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .tenant-form-page { padding: 0; max-width: 640px; }
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
export class TenantFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private tenantService = inject(TenantService);
  private tenantContext = inject(TenantContextService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toastService = inject(ToastService);

  submitting = signal(false);
  errorMessage = signal('');
  availableParents = signal<Tenant[]>([]);

  form = this.fb.group({
    name: ['', Validators.required],
    parentId: [''],
    contactEmail: ['', Validators.email],
    description: [''],
  });

  ngOnInit(): void {
    // Pre-select parent from query param if provided
    const parentId = this.route.snapshot.queryParams['parent'] || '';
    if (parentId) {
      this.form.patchValue({ parentId });
    }

    // Load available parents (max level 1 to enforce 3-level limit)
    this.tenantService.listTenants(0, 200).subscribe({
      next: (tenants) => {
        this.availableParents.set(tenants.filter((t) => t.level < 2));
      },
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;

    this.tenantService
      .createTenant({
        name: values.name!,
        parent_id: values.parentId || null,
        contact_email: values.contactEmail || null,
        description: values.description || null,
      })
      .subscribe({
        next: (tenant) => {
          this.toastService.success('Tenant created');
          this.tenantContext.loadAccessibleTenants();
          this.router.navigate(['/tenants', tenant.id]);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to create tenant';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
  }

  cancel(): void {
    this.router.navigate(['/tenants']);
  }
}
