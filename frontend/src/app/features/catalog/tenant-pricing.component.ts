/**
 * Overview: Tenant price override management — list, create, and delete per-tenant
 *     price overrides with service selection, custom pricing, discounts, and date ranges.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/catalog.service
 * Concepts: Tenant-scoped price overrides, effective pricing display, discount configuration
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
import { CatalogService } from '@core/services/catalog.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import {
  TenantPriceOverride,
  ServiceOffering,
  EffectivePrice,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-tenant-pricing',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="tenant-pricing-page">
        <div class="page-header">
          <h1>Tenant Price Overrides</h1>
          <button
            *nimbusHasPermission="'catalog:override:create'"
            class="btn btn-primary"
            (click)="showCreateForm()"
          >
            + Create Override
          </button>
        </div>
        <p class="page-description">
          Configure per-tenant pricing overrides. Overrides take precedence over the
          default price list for the current tenant.
        </p>

        <!-- Create override form -->
        @if (creating()) {
          <div class="form-card">
            <h2 class="form-title">New Price Override</h2>
            <div class="form-group">
              <label class="form-label">Service Offering *</label>
              <nimbus-searchable-select [(ngModel)]="formServiceId" (ngModelChange)="onServiceChange()" [options]="offeringOptions()" placeholder="Select a service..." />
            </div>

            @if (effectivePrice()) {
              <div class="effective-card">
                <span class="effective-label">Current effective price:</span>
                <span class="effective-value mono">
                  {{ effectivePrice()!.pricePerUnit | number: '1.2-2' }}
                  {{ effectivePrice()!.currency }}/{{ effectivePrice()!.measuringUnit }}
                </span>
                @if (effectivePrice()!.hasOverride) {
                  <span class="badge badge-override">Override active</span>
                }
              </div>
            }

            <div class="form-row">
              <div class="form-group half">
                <label class="form-label">Price per Unit *</label>
                <input
                  class="form-input"
                  type="number"
                  [(ngModel)]="formPrice"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                />
              </div>
              <div class="form-group half">
                <label class="form-label">Discount %</label>
                <input
                  class="form-input"
                  type="number"
                  [(ngModel)]="formDiscount"
                  min="0"
                  max="100"
                  step="0.1"
                  placeholder="Optional"
                />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group half">
                <label class="form-label">Effective From *</label>
                <input
                  class="form-input"
                  type="date"
                  [(ngModel)]="formEffectiveFrom"
                />
              </div>
              <div class="form-group half">
                <label class="form-label">Effective To</label>
                <input
                  class="form-input"
                  type="date"
                  [(ngModel)]="formEffectiveTo"
                />
              </div>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" (click)="cancelCreate()">Cancel</button>
              <button
                class="btn btn-primary"
                (click)="createOverride()"
                [disabled]="!formServiceId || formPrice < 0 || !formEffectiveFrom"
              >
                Create Override
              </button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="loading">Loading overrides...</div>
        }

        @if (!loading() && overrides().length === 0 && !creating()) {
          <div class="empty-state">
            No tenant price overrides configured. Default price list pricing applies.
          </div>
        }

        <!-- Override list -->
        @if (!loading() && overrides().length > 0) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Price/Unit</th>
                  <th>Discount</th>
                  <th>Effective From</th>
                  <th>Effective To</th>
                  <th>Created</th>
                  <th class="th-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (override of overrides(); track override.id) {
                  <tr>
                    <td class="name-cell">{{ serviceNameForId(override.serviceOfferingId) }}</td>
                    <td class="mono">{{ override.pricePerUnit | number: '1.2-2' }}</td>
                    <td>
                      @if (override.discountPercent != null) {
                        <span class="badge badge-discount">
                          {{ override.discountPercent | number: '1.0-1' }}%
                        </span>
                      } @else {
                        <span class="text-muted">\u2014</span>
                      }
                    </td>
                    <td>{{ override.effectiveFrom | date: 'mediumDate' }}</td>
                    <td>
                      @if (override.effectiveTo) {
                        {{ override.effectiveTo | date: 'mediumDate' }}
                      } @else {
                        <span class="text-muted">No end date</span>
                      }
                    </td>
                    <td>{{ override.createdAt | date: 'medium' }}</td>
                    <td class="td-actions">
                      <button
                        *nimbusHasPermission="'catalog:override:delete'"
                        class="btn-icon btn-danger"
                        (click)="deleteOverride(override)"
                        title="Delete override"
                      >
                        &times;
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .tenant-pricing-page { padding: 0; max-width: 960px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .page-description {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 1.5rem;
    }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* ── Create form ─────────────────────────────────────────────── */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .form-title {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
      padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;
    }
    .form-group { margin-bottom: 1rem; }
    .form-label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
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
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }

    .effective-card {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0.75rem 1rem; background: #eff6ff;
      border: 1px solid #bfdbfe; border-radius: 6px;
      margin-bottom: 1rem; font-size: 0.8125rem;
    }
    .effective-label { color: #64748b; }
    .effective-value { color: #1e293b; font-weight: 600; }

    /* ── Table ────────────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .th-actions, .td-actions { width: 60px; text-align: right; }
    .text-muted { color: #94a3b8; }

    /* ── Badges ───────────────────────────────────────────────────── */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-override { background: #fef3c7; color: #92400e; }
    .badge-discount { background: #dcfce7; color: #16a34a; }

    /* ── Buttons ──────────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }

    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 1rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class TenantPricingComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private tenantContext = inject(TenantContextService);
  private toastService = inject(ToastService);

  overrides = signal<TenantPriceOverride[]>([]);
  offerings = signal<ServiceOffering[]>([]);
  loading = signal(false);

  offeringOptions = computed(() => this.offerings().map(o => ({ value: o.id, label: o.name })));
  creating = signal(false);
  effectivePrice = signal<EffectivePrice | null>(null);

  // Create form fields
  formServiceId = '';
  formPrice = 0;
  formDiscount: number | null = null;
  formEffectiveFrom = '';
  formEffectiveTo = '';

  ngOnInit(): void {
    this.loadOverrides();
    this.loadOfferings();
  }

  showCreateForm(): void {
    this.resetForm();
    this.creating.set(true);
  }

  cancelCreate(): void {
    this.creating.set(false);
    this.resetForm();
  }

  onServiceChange(): void {
    this.effectivePrice.set(null);
    if (!this.formServiceId) return;

    this.catalogService.getEffectivePrice(this.formServiceId).subscribe({
      next: (price) => this.effectivePrice.set(price),
    });
  }

  createOverride(): void {
    this.catalogService.createTenantOverride({
      serviceOfferingId: this.formServiceId,
      pricePerUnit: this.formPrice,
      discountPercent: this.formDiscount,
      effectiveFrom: this.formEffectiveFrom,
      effectiveTo: this.formEffectiveTo || null,
    }).subscribe({
      next: (created) => {
        this.overrides.update((items) => [...items, created]);
        this.toastService.success('Price override created');
        this.cancelCreate();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create override');
      },
    });
  }

  deleteOverride(override: TenantPriceOverride): void {
    this.catalogService.deleteTenantOverride(override.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.overrides.update((items) => items.filter((o) => o.id !== override.id));
          this.toastService.success('Price override deleted');
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete override');
      },
    });
  }

  serviceNameForId(serviceOfferingId: string): string {
    const offering = this.offerings().find((o) => o.id === serviceOfferingId);
    return offering ? offering.name : serviceOfferingId.substring(0, 8) + '...';
  }

  // ── Private helpers ───────────────────────────────────────────

  private loadOverrides(): void {
    this.loading.set(true);
    this.catalogService.listTenantOverrides().subscribe({
      next: (overrides) => {
        this.overrides.set(overrides);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load tenant price overrides');
      },
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });
  }

  private resetForm(): void {
    this.formServiceId = '';
    this.formPrice = 0;
    this.formDiscount = null;
    this.formEffectiveFrom = '';
    this.formEffectiveTo = '';
    this.effectivePrice.set(null);
  }
}
