/**
 * Overview: Estimation builder — create and edit service delivery estimations with line items.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/delivery.service
 * Concepts: Service estimations, line items, profitability calculation, cost vs sell price
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
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { DeliveryService } from '@core/services/delivery.service';
import { CatalogService } from '@core/services/catalog.service';
import { TenantService } from '@core/services/tenant.service';
import {
  ServiceEstimation,
  DeliveryRegion,
  StaffProfile,
  ServiceProcessAssignment,
  ServiceProcess,
} from '@shared/models/delivery.model';
import { ServiceOffering } from '@shared/models/cmdb.model';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface LineItemForm {
  name: string;
  staffProfileId: string;
  deliveryRegionId: string;
  estimatedHours: number;
  hourlyRate: number;
  rateCurrency: string;
  rateCardId: string | null;
}

const COVERAGE_MODELS: { value: string; label: string }[] = [
  { value: 'business_hours', label: 'Business Hours' },
  { value: 'extended', label: 'Extended' },
  { value: '24x7', label: '24x7' },
];

@Component({
  selector: 'nimbus-estimation-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="builder-page">
        <div class="page-header">
          <h1>{{ isEditMode() ? 'Edit Estimation' : 'Create Estimation' }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading...</div>
        }

        @if (!loading()) {
          <!-- Top section: Estimation details -->
          <div class="form-card">
            <h2 class="section-title">Estimation Details</h2>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Client Tenant *</label>
                <nimbus-searchable-select [(ngModel)]="formClientTenantId" [disabled]="isEditMode()" [options]="tenantOptions()" placeholder="Select client..." />
              </div>
              <div class="form-group">
                <label class="form-label">Service Offering *</label>
                <nimbus-searchable-select [(ngModel)]="formServiceOfferingId" [disabled]="isEditMode()" [options]="offeringOptions()" placeholder="Select service..." />
              </div>
              <div class="form-group">
                <label class="form-label">Delivery Region</label>
                <nimbus-searchable-select [(ngModel)]="formDeliveryRegionId" [options]="regionOptions()" placeholder="Select region..." [allowClear]="true" />
              </div>
              <div class="form-group">
                <label class="form-label">Coverage Model</label>
                <select class="form-input" [(ngModel)]="formCoverageModel">
                  <option value="">Select coverage...</option>
                  @for (model of coverageModels; track model.value) {
                    <option [value]="model.value">{{ model.label }}</option>
                  }
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Quantity</label>
                <input
                  class="form-input"
                  type="number"
                  [(ngModel)]="formQuantity"
                  min="1"
                  step="1"
                  placeholder="1"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Sell Price per Unit</label>
                <input
                  class="form-input"
                  type="number"
                  [(ngModel)]="formSellPricePerUnit"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                />
              </div>
            </div>
          </div>

          <!-- Middle section: Line items -->
          <div class="form-card">
            <div class="section-header">
              <h2 class="section-title">Line Items</h2>
              <div class="section-actions">
                @if (isEditMode() && assignedProcesses().length > 0) {
                  <select class="form-input form-input-sm" [(ngModel)]="importProcessId">
                    <option value="">Import from process...</option>
                    @for (a of assignedProcesses(); track a.id) {
                      <option [value]="a.processId">{{ processNameForId(a.processId) }}</option>
                    }
                  </select>
                  <button
                    class="btn btn-sm"
                    (click)="importFromProcess()"
                    [disabled]="!importProcessId"
                  >Import</button>
                }
                @if (isEditMode()) {
                  <button class="btn btn-sm" (click)="refreshRates()">Refresh Rates</button>
                }
                <button class="btn btn-sm" (click)="addLineItem()">+ Add Line Item</button>
              </div>
            </div>

            @if (lineItems().length > 0) {
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Staff Profile</th>
                      <th>Region</th>
                      <th class="th-right">Est. Hours</th>
                      <th class="th-right">Hourly Rate</th>
                      <th class="th-right">Line Cost</th>
                      <th class="th-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of lineItems(); track item) {
                      <tr>
                        <td>
                          <input
                            class="inline-input"
                            [(ngModel)]="item.name"
                            placeholder="Activity name"
                          />
                        </td>
                        <td>
                          <select class="inline-input" [(ngModel)]="item.staffProfileId">
                            <option value="">Select...</option>
                            @for (profile of staffProfiles(); track profile.id) {
                              <option [value]="profile.id">{{ profile.displayName }}</option>
                            }
                          </select>
                        </td>
                        <td>
                          <select class="inline-input" [(ngModel)]="item.deliveryRegionId">
                            <option value="">Select...</option>
                            @for (region of regions(); track region.id) {
                              <option [value]="region.id">{{ region.displayName }}</option>
                            }
                          </select>
                        </td>
                        <td>
                          <input
                            class="inline-input inline-number"
                            type="number"
                            [(ngModel)]="item.estimatedHours"
                            min="0"
                            step="0.5"
                          />
                        </td>
                        <td>
                          <span class="inline-rate mono" [class.rate-missing]="!item.rateCardId">
                            {{ item.hourlyRate | number: '1.2-2' }}
                          </span>
                        </td>
                        <td class="td-right mono">
                          {{ (item.estimatedHours * item.hourlyRate) | number: '1.2-2' }}
                        </td>
                        <td class="td-actions">
                          <button
                            class="btn-icon btn-danger"
                            (click)="removeLineItem($index)"
                            title="Remove line item"
                          >
                            &times;
                          </button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="empty-lines">No line items added yet. Click "Add Line Item" to begin.</div>
            }
          </div>

          <!-- Bottom section: Summary -->
          <div class="summary-card">
            <h2 class="section-title">Profitability Summary</h2>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">Total Estimated Cost</span>
                <span class="summary-value mono">{{ totalCost() | number: '1.2-2' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Total Sell Price</span>
                <span class="summary-value mono">{{ totalSell() | number: '1.2-2' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Margin Amount</span>
                <span
                  class="summary-value mono"
                  [class.margin-positive]="marginAmount() >= 0"
                  [class.margin-negative]="marginAmount() < 0"
                >
                  {{ marginAmount() | number: '1.2-2' }}
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Margin %</span>
                <span
                  class="summary-value"
                  [class.margin-positive]="marginPercent() >= 0"
                  [class.margin-negative]="marginPercent() < 0"
                >
                  {{ marginPercent() | number: '1.1-1' }}%
                </span>
              </div>
            </div>
          </div>

          <!-- Error -->
          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <!-- Actions -->
          <div class="form-actions">
            <button class="btn btn-secondary" (click)="cancel()">Cancel</button>
            <button
              class="btn btn-outline"
              (click)="saveAsDraft()"
              [disabled]="!canSave() || submitting()"
            >
              {{ submitting() ? 'Saving...' : 'Save as Draft' }}
            </button>
            <button
              class="btn btn-primary"
              (click)="submitEstimation()"
              [disabled]="!canSave() || submitting()"
            >
              {{ submitting() ? 'Submitting...' : 'Submit' }}
            </button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .builder-page { padding: 0; max-width: 1100px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading {
      padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* ── Cards ──────────────────────────────────────────────────────── */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.25rem;
    }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-title {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
    }
    .section-header .section-title { margin: 0; }

    /* ── Form grid ─────────────────────────────────────────────────── */
    .form-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
    }
    .form-group { display: flex; flex-direction: column; }
    .form-label {
      font-size: 0.8125rem; font-weight: 600; color: #475569;
      margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }

    /* ── Inline table inputs ───────────────────────────────────────── */
    .inline-input {
      width: 100%; padding: 0.375rem 0.5rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.75rem; box-sizing: border-box; font-family: inherit;
    }
    .inline-input:focus { border-color: #3b82f6; outline: none; }
    .inline-number { text-align: right; width: 90px; }

    /* ── Table ──────────────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
    }
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
    .th-right, .td-right { text-align: right; }
    .th-actions, .td-actions { width: 50px; text-align: center; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }

    .empty-lines {
      text-align: center; color: #94a3b8; padding: 1.5rem; font-size: 0.8125rem;
    }

    /* ── Summary ───────────────────────────────────────────────────── */
    .summary-card {
      background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.25rem;
    }
    .summary-card .section-title { margin-bottom: 1rem; }
    .summary-grid {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;
    }
    .summary-item { display: flex; flex-direction: column; gap: 0.25rem; }
    .summary-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .summary-value { font-size: 1.25rem; font-weight: 700; color: #1e293b; }
    .margin-positive { color: #16a34a; }
    .margin-negative { color: #dc2626; }

    /* ── Error ──────────────────────────────────────────────────────── */
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }

    /* ── Actions ─────────────────────────────────────────────────────── */
    .form-actions {
      display: flex; gap: 0.75rem; justify-content: flex-end;
      margin-top: 0.5rem; margin-bottom: 2rem;
    }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1.5rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-outline {
      background: #fff; color: #3b82f6; border: 1px solid #3b82f6;
    }
    .btn-outline:hover { background: #eff6ff; }
    .btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #475569; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; color: #475569; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .section-actions { display: flex; gap: 0.5rem; align-items: center; }
    .form-input-sm {
      padding: 0.375rem 0.5rem; font-size: 0.75rem; min-width: 180px;
      border: 1px solid #e2e8f0; border-radius: 6px; background: #fff;
      color: #1e293b; font-family: inherit;
    }
    .inline-rate { display: inline-block; padding: 0.375rem 0.5rem; font-size: 0.75rem; }
    .rate-missing { color: #dc2626; font-style: italic; }

    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 1rem; border-radius: 4px; color: #94a3b8;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class EstimationBuilderComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');

  tenants = signal<Tenant[]>([]);
  offerings = signal<ServiceOffering[]>([]);
  regions = signal<DeliveryRegion[]>([]);
  staffProfiles = signal<StaffProfile[]>([]);
  lineItems = signal<LineItemForm[]>([]);
  assignedProcesses = signal<ServiceProcessAssignment[]>([]);
  availableProcesses = signal<ServiceProcess[]>([]);

  readonly coverageModels = COVERAGE_MODELS;

  tenantOptions = computed(() => this.tenants().map(t => ({ value: t.id, label: t.name })));
  offeringOptions = computed(() => this.offerings().map(o => ({ value: o.id, label: o.name })));
  regionOptions = computed(() => this.regions().map(r => ({ value: r.id, label: r.displayName })));

  // Form fields
  formClientTenantId = '';
  formServiceOfferingId = '';
  formDeliveryRegionId = '';
  formCoverageModel = '';
  formQuantity = 1;
  formSellPricePerUnit = 0;
  importProcessId = '';

  private estimationId: string | null = null;
  private existingEstimation = signal<ServiceEstimation | null>(null);

  // Computed summary values
  totalCost = computed(() => {
    return this.lineItems().reduce(
      (sum, item) => sum + item.estimatedHours * item.hourlyRate,
      0,
    );
  });

  totalSell = computed(() => {
    return this.formQuantity * this.formSellPricePerUnit;
  });

  marginAmount = computed(() => {
    return this.totalSell() - this.totalCost();
  });

  marginPercent = computed(() => {
    const sell = this.totalSell();
    if (sell === 0) return 0;
    return (this.marginAmount() / sell) * 100;
  });

  canSave = computed(() => {
    return !!this.formClientTenantId && !!this.formServiceOfferingId;
  });

  ngOnInit(): void {
    this.estimationId = this.route.snapshot.paramMap.get('id') ?? null;
    this.isEditMode.set(!!this.estimationId);

    this.loadLookups();

    if (this.estimationId) {
      this.loading.set(true);
      this.loadExistingEstimation(this.estimationId);
    }
  }

  addLineItem(): void {
    this.lineItems.update((items) => [
      ...items,
      {
        name: '',
        staffProfileId: '',
        deliveryRegionId: this.formDeliveryRegionId || '',
        estimatedHours: 0,
        hourlyRate: 0,
        rateCurrency: 'EUR',
        rateCardId: null,
      },
    ]);
  }

  removeLineItem(index: number): void {
    this.lineItems.update((items) => items.filter((_, i) => i !== index));
  }

  saveAsDraft(): void {
    this.save(false);
  }

  submitEstimation(): void {
    this.save(true);
  }

  cancel(): void {
    this.router.navigate(['/catalog', 'estimations']);
  }

  importFromProcess(): void {
    if (!this.estimationId || !this.importProcessId) return;
    this.submitting.set(true);
    this.deliveryService.importProcessToEstimation(
      this.estimationId,
      this.importProcessId,
      this.formDeliveryRegionId || null,
    ).subscribe({
      next: (estimation) => {
        this.mapEstimationToForm(estimation);
        this.submitting.set(false);
        this.importProcessId = '';
        this.toastService.success('Process line items imported');
      },
      error: (err) => {
        this.submitting.set(false);
        this.toastService.error(err.message || 'Failed to import process');
      },
    });
  }

  refreshRates(): void {
    if (!this.estimationId) return;
    this.submitting.set(true);
    this.deliveryService.refreshEstimationRates(this.estimationId).subscribe({
      next: (estimation) => {
        this.mapEstimationToForm(estimation);
        this.submitting.set(false);
        this.toastService.success('Rates refreshed from current rate cards');
      },
      error: (err) => {
        this.submitting.set(false);
        this.toastService.error(err.message || 'Failed to refresh rates');
      },
    });
  }

  processNameForId(processId: string): string {
    const p = this.availableProcesses().find((proc) => proc.id === processId);
    return p ? p.name : processId.substring(0, 8) + '...';
  }

  // ── Private helpers ─────────────────────────────────────────────

  private save(submitAfterSave: boolean): void {
    this.submitting.set(true);
    this.errorMessage.set('');

    if (this.isEditMode() && this.estimationId) {
      this.deliveryService.updateEstimation(this.estimationId, {
        quantity: this.formQuantity,
        sellPricePerUnit: this.formSellPricePerUnit,
        deliveryRegionId: this.formDeliveryRegionId || null,
        coverageModel: this.formCoverageModel || null,
      }).subscribe({
        next: (estimation) => {
          this.syncLineItems(estimation.id, submitAfterSave);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.message || 'Failed to update estimation';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    } else {
      this.deliveryService.createEstimation({
        clientTenantId: this.formClientTenantId,
        serviceOfferingId: this.formServiceOfferingId,
        deliveryRegionId: this.formDeliveryRegionId || null,
        coverageModel: this.formCoverageModel || null,
        quantity: this.formQuantity,
        sellPricePerUnit: this.formSellPricePerUnit,
      }).subscribe({
        next: (estimation) => {
          this.syncLineItems(estimation.id, submitAfterSave);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.message || 'Failed to create estimation';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    }
  }

  private syncLineItems(estimationId: string, submitAfterSave: boolean): void {
    const items = this.lineItems().filter(
      (item) => item.name && item.staffProfileId && item.deliveryRegionId,
    );

    if (items.length === 0) {
      this.finalize(estimationId, submitAfterSave);
      return;
    }

    // Delete existing line items from the loaded estimation, then add new ones
    const existing = this.existingEstimation();
    const deleteOps = existing
      ? existing.lineItems.map((li) => this.deliveryService.deleteLineItem(li.id))
      : [];

    const afterDelete = deleteOps.length > 0 ? forkJoin(deleteOps) : forkJoin([]);

    const doAdd = (): void => {
      const addOps = items.map((item) =>
        this.deliveryService.addLineItem(estimationId, {
          name: item.name,
          staffProfileId: item.staffProfileId,
          deliveryRegionId: item.deliveryRegionId,
          estimatedHours: item.estimatedHours,
          hourlyRate: item.hourlyRate,
          rateCurrency: item.rateCurrency,
        }),
      );

      if (addOps.length === 0) {
        this.finalize(estimationId, submitAfterSave);
        return;
      }

      forkJoin(addOps).subscribe({
        next: () => this.finalize(estimationId, submitAfterSave),
        error: (err) => {
          this.submitting.set(false);
          this.toastService.error(err.message || 'Failed to save line items');
        },
      });
    };

    if (deleteOps.length > 0) {
      afterDelete.subscribe({
        next: () => doAdd(),
        error: (err) => {
          this.submitting.set(false);
          this.toastService.error(err.message || 'Failed to remove old line items');
        },
      });
    } else {
      doAdd();
    }
  }

  private finalize(estimationId: string, submit: boolean): void {
    if (submit) {
      this.deliveryService.submitEstimation(estimationId).subscribe({
        next: () => {
          this.submitting.set(false);
          this.toastService.success('Estimation submitted');
          this.router.navigate(['/catalog', 'estimations', estimationId]);
        },
        error: (err) => {
          this.submitting.set(false);
          this.toastService.error(err.message || 'Failed to submit estimation');
        },
      });
    } else {
      this.submitting.set(false);
      this.toastService.success(this.isEditMode() ? 'Estimation updated' : 'Estimation saved as draft');
      this.router.navigate(['/catalog', 'estimations', estimationId]);
    }
  }

  private mapEstimationToForm(estimation: ServiceEstimation): void {
    this.existingEstimation.set(estimation);
    this.formClientTenantId = estimation.clientTenantId;
    this.formServiceOfferingId = estimation.serviceOfferingId;
    this.formDeliveryRegionId = estimation.deliveryRegionId || '';
    this.formCoverageModel = estimation.coverageModel || '';
    this.formQuantity = estimation.quantity;
    this.formSellPricePerUnit = estimation.sellPricePerUnit;

    const formItems: LineItemForm[] = estimation.lineItems.map((li) => ({
      name: li.name,
      staffProfileId: li.staffProfileId,
      deliveryRegionId: li.deliveryRegionId,
      estimatedHours: li.estimatedHours,
      hourlyRate: li.hourlyRate,
      rateCurrency: li.rateCurrency,
      rateCardId: li.rateCardId,
    }));
    this.lineItems.set(formItems);
  }

  private loadLookups(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (tenants) => this.tenants.set(tenants),
    });

    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });

    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (response) => this.regions.set(response.items),
    });

    this.deliveryService.listStaffProfiles().subscribe({
      next: (profiles) => this.staffProfiles.set(profiles),
    });

    this.deliveryService.listProcesses({ limit: 500 }).subscribe({
      next: (response) => this.availableProcesses.set(response.items),
    });
  }

  private loadExistingEstimation(id: string): void {
    this.deliveryService.getEstimation(id).subscribe({
      next: (estimation) => {
        if (!estimation) {
          this.loading.set(false);
          this.toastService.error('Estimation not found');
          this.router.navigate(['/catalog', 'estimations']);
          return;
        }

        this.existingEstimation.set(estimation);
        this.formClientTenantId = estimation.clientTenantId;
        this.formServiceOfferingId = estimation.serviceOfferingId;
        this.formDeliveryRegionId = estimation.deliveryRegionId || '';
        this.formCoverageModel = estimation.coverageModel || '';
        this.formQuantity = estimation.quantity;
        this.formSellPricePerUnit = estimation.sellPricePerUnit;

        // Load process assignments for this offering
        this.deliveryService.listAssignments(estimation.serviceOfferingId).subscribe({
          next: (assignments) => this.assignedProcesses.set(assignments),
        });

        // Map existing line items into form
        const formItems: LineItemForm[] = estimation.lineItems.map((li) => ({
          name: li.name,
          staffProfileId: li.staffProfileId,
          deliveryRegionId: li.deliveryRegionId,
          estimatedHours: li.estimatedHours,
          hourlyRate: li.hourlyRate,
          rateCurrency: li.rateCurrency,
          rateCardId: li.rateCardId,
        }));
        this.lineItems.set(formItems);

        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load estimation');
        this.router.navigate(['/catalog', 'estimations']);
      },
    });
  }
}
