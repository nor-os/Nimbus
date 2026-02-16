/**
 * Overview: Multi-step wizard for creating tenants — Basic Info, Cloud Provider, Currency & Region.
 * Architecture: Feature component for tenant creation (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/tenant.service,
 *     app/core/services/semantic.service, app/core/services/delivery.service,
 *     app/core/services/cloud-backend.service
 * Concepts: Multi-tenancy, reactive forms, 3-level hierarchy limit, wizard pattern
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { TenantService } from '@core/services/tenant.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { SemanticService } from '@core/services/semantic.service';
import { DeliveryService } from '@core/services/delivery.service';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { Tenant } from '@core/models/tenant.model';
import { SemanticProvider } from '@shared/models/semantic.model';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

const CURRENCIES = [
  'EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'SEK', 'NOK', 'DKK',
  'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'INR', 'BRL', 'CNY', 'SGD',
];

@Component({
  selector: 'nimbus-tenant-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="wizard-page">
        <h1>Create Tenant</h1>

        <!-- Step indicator -->
        <div class="step-indicator">
          @for (s of steps; track s.num; let i = $index) {
            <div class="step" [class.active]="step() === s.num" [class.completed]="step() > s.num">
              <div class="step-circle">{{ step() > s.num ? '&#10003;' : s.num }}</div>
              <span class="step-label">{{ s.label }}</span>
            </div>
            @if (i < steps.length - 1) {
              <div class="step-line" [class.completed]="step() > s.num"></div>
            }
          }
        </div>

        <div class="wizard-card">
          <!-- Step 1: Basic Info -->
          @if (step() === 1) {
            <h2>Basic Information</h2>
            <form [formGroup]="basicForm" class="wizard-form">
              <div class="form-group">
                <label for="name">Name *</label>
                <input id="name" formControlName="name" class="form-input" placeholder="Tenant name" />
                @if (basicForm.get('name')?.hasError('required') && basicForm.get('name')?.touched) {
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
                <input id="contactEmail" formControlName="contactEmail" type="email" class="form-input" placeholder="contact@example.com" />
                @if (basicForm.get('contactEmail')?.hasError('email') && basicForm.get('contactEmail')?.touched) {
                  <span class="error">Invalid email format</span>
                }
              </div>

              <div class="form-group">
                <label for="description">Description</label>
                <textarea id="description" formControlName="description" class="form-input" rows="3" placeholder="Optional description"></textarea>
              </div>
            </form>
          }

          <!-- Step 2: Cloud Provider -->
          @if (step() === 2) {
            <h2>Cloud Provider</h2>
            <p class="step-hint">Select a cloud provider to auto-create a backend for this tenant. You can skip this and configure it later.</p>

            @if (providersLoading()) {
              <p class="loading-text">Loading providers...</p>
            } @else {
              <div class="provider-grid">
                @for (p of providers(); track p.id) {
                  <button
                    class="provider-card"
                    [class.selected]="selectedProviderId() === p.id"
                    (click)="selectProvider(p)"
                  >
                    <div class="provider-icon">{{ p.icon || p.name.charAt(0).toUpperCase() }}</div>
                    <div class="provider-name">{{ p.displayName }}</div>
                    <div class="provider-type">{{ p.providerType }}</div>
                  </button>
                }
              </div>
              @if (selectedProviderId()) {
                <button class="btn-link" (click)="clearProvider()">Clear selection</button>
              }
            }
          }

          <!-- Step 3: Currency & Region -->
          @if (step() === 3) {
            <h2>Currency & Region</h2>
            <p class="step-hint">Set the default invoice currency and primary delivery region. Both are optional and can be changed later.</p>

            <form [formGroup]="configForm" class="wizard-form">
              <div class="form-group">
                <label for="currency">Invoice Currency</label>
                <select id="currency" formControlName="invoiceCurrency" class="form-input">
                  <option value="">None (inherit default)</option>
                  @for (c of currencies; track c) {
                    <option [value]="c">{{ c }}</option>
                  }
                </select>
              </div>

              <div class="form-group">
                <label for="region">Primary Delivery Region</label>
                <select id="region" formControlName="primaryRegionId" class="form-input">
                  <option value="">None</option>
                  @for (r of regions(); track r.id) {
                    <option [value]="r.id">{{ r.displayName }} ({{ r.code }})</option>
                  }
                </select>
                <span class="hint">Regions are managed in Settings &gt; Delivery Regions.</span>
              </div>
            </form>
          }

          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <!-- Wizard actions -->
          <div class="wizard-actions">
            <div class="left-actions">
              @if (step() > 1) {
                <button class="btn btn-secondary" (click)="prevStep()">Back</button>
              }
            </div>
            <div class="right-actions">
              <button class="btn btn-secondary" (click)="cancel()">Cancel</button>
              @if (step() < 3) {
                @if (step() > 1) {
                  <button class="btn btn-secondary" (click)="skipToEnd()">Skip to Create</button>
                }
                <button class="btn btn-primary" (click)="nextStep()" [disabled]="!canProceed()">Next</button>
              } @else {
                <button class="btn btn-primary" (click)="onSubmit()" [disabled]="!canProceed() || submitting()">
                  {{ submitting() ? 'Creating...' : 'Create Tenant' }}
                </button>
              }
            </div>
          </div>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .wizard-page { padding: 0; max-width: 700px; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; }
    h2 { font-size: 1.125rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem; }

    /* Step indicator */
    .step-indicator { display: flex; align-items: center; margin-bottom: 1.5rem; gap: 0; }
    .step { display: flex; align-items: center; gap: 0.5rem; }
    .step-circle {
      width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
      justify-content: center; font-size: 0.75rem; font-weight: 600;
      background: #e2e8f0; color: #64748b; transition: all 0.2s;
    }
    .step.active .step-circle { background: #3b82f6; color: #fff; }
    .step.completed .step-circle { background: #10b981; color: #fff; }
    .step-label { font-size: 0.8125rem; color: #64748b; font-weight: 500; }
    .step.active .step-label { color: #1e293b; font-weight: 600; }
    .step.completed .step-label { color: #10b981; }
    .step-line {
      flex: 1; height: 2px; background: #e2e8f0; margin: 0 0.75rem; transition: background 0.2s;
    }
    .step-line.completed { background: #10b981; }

    /* Wizard card */
    .wizard-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .wizard-form { margin-top: 0.5rem; }
    .step-hint { font-size: 0.8125rem; color: #64748b; margin: -0.5rem 0 1.25rem; }

    /* Form groups */
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
    .hint { font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin: 1rem 0 0; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .loading-text { font-size: 0.8125rem; color: #64748b; }

    /* Provider cards */
    .provider-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 0.75rem; margin-bottom: 1rem;
    }
    .provider-card {
      display: flex; flex-direction: column; align-items: center; gap: 0.375rem;
      padding: 1rem 0.5rem; border: 2px solid #e2e8f0; border-radius: 8px;
      background: #fff; cursor: pointer; transition: all 0.15s;
      font-family: inherit;
    }
    .provider-card:hover { border-color: #93c5fd; background: #f0f9ff; }
    .provider-card.selected { border-color: #3b82f6; background: #eff6ff; }
    .provider-icon {
      width: 40px; height: 40px; border-radius: 8px; background: #f1f5f9;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.25rem; font-weight: 700; color: #3b82f6;
    }
    .provider-card.selected .provider-icon { background: #dbeafe; }
    .provider-name { font-size: 0.8125rem; font-weight: 600; color: #1e293b; text-align: center; }
    .provider-type { font-size: 0.6875rem; color: #94a3b8; text-transform: capitalize; }
    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; padding: 0; font-family: inherit;
    }
    .btn-link:hover { text-decoration: underline; }

    /* Actions */
    .wizard-actions {
      display: flex; justify-content: space-between; align-items: center;
      margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #f1f5f9;
    }
    .left-actions, .right-actions { display: flex; gap: 0.75rem; }
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
  private semanticService = inject(SemanticService);
  private deliveryService = inject(DeliveryService);
  private cloudBackendService = inject(CloudBackendService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toastService = inject(ToastService);

  step = signal(1);
  submitting = signal(false);
  errorMessage = signal('');
  availableParents = signal<Tenant[]>([]);
  providers = signal<SemanticProvider[]>([]);
  providersLoading = signal(false);
  regions = signal<DeliveryRegion[]>([]);
  selectedProviderId = signal<string | null>(null);

  currencies = CURRENCIES;
  steps = [
    { num: 1, label: 'Basic Info' },
    { num: 2, label: 'Provider' },
    { num: 3, label: 'Currency & Region' },
  ];

  basicForm = this.fb.group({
    name: ['', Validators.required],
    parentId: [''],
    contactEmail: ['', Validators.email],
    description: [''],
  });

  configForm = this.fb.group({
    invoiceCurrency: [''],
    primaryRegionId: [''],
  });

  canProceed = computed(() => {
    if (this.step() === 1) return this.basicForm.valid;
    return true;
  });

  ngOnInit(): void {
    const parentId = this.route.snapshot.queryParams['parent'] || '';
    if (parentId) {
      this.basicForm.patchValue({ parentId });
    }

    this.tenantService.listTenants(0, 200).subscribe({
      next: (tenants) => {
        this.availableParents.set(tenants.filter((t) => t.level < 2));
      },
    });

    // Load providers for step 2
    this.providersLoading.set(true);
    this.semanticService.listProviders().subscribe({
      next: (providers) => {
        this.providers.set(providers);
        this.providersLoading.set(false);
      },
      error: () => this.providersLoading.set(false),
    });

    // Load delivery regions for step 3
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (result) => this.regions.set(result.items),
      error: () => {},
    });
  }

  selectProvider(p: SemanticProvider): void {
    this.selectedProviderId.set(
      this.selectedProviderId() === p.id ? null : p.id
    );
  }

  clearProvider(): void {
    this.selectedProviderId.set(null);
  }

  nextStep(): void {
    if (this.step() === 1 && this.basicForm.invalid) {
      this.basicForm.markAllAsTouched();
      return;
    }
    this.step.update((s) => Math.min(s + 1, 3));
  }

  prevStep(): void {
    this.step.update((s) => Math.max(s - 1, 1));
  }

  skipToEnd(): void {
    this.step.set(3);
  }

  onSubmit(): void {
    if (this.basicForm.invalid) {
      this.step.set(1);
      this.basicForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    const basic = this.basicForm.value;
    const config = this.configForm.value;

    this.tenantService
      .createTenant({
        name: basic.name!,
        parent_id: basic.parentId || null,
        contact_email: basic.contactEmail || null,
        description: basic.description || null,
        invoice_currency: config.invoiceCurrency || null,
        primary_region_id: config.primaryRegionId || null,
        provider_id_for_backend: this.selectedProviderId() || null,
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
