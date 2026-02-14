/**
 * Overview: Interactive cost calculator — select offerings to see effective pricing and
 *     detailed cost breakdowns (SKU components, activity costs, base fees) using the
 *     16-level pricing engine. Provider-mode controls allow target tenant + price list
 *     selection. All users can filter by delivery region and coverage model.
 * Architecture: Cost feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router,
 *     app/core/services/catalog.service, app/core/services/delivery.service,
 *     app/core/services/tenant.service
 * Concepts: Effective pricing, cost breakdown, pricing engine, tenant-scoped pricing,
 *     pricing context, service estimations
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
import { Router } from '@angular/router';
import { CatalogService } from '@core/services/catalog.service';
import { DeliveryService } from '@core/services/delivery.service';
import { TenantService } from '@core/services/tenant.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import {
  ServiceOffering,
  EffectivePrice,
  OfferingCostBreakdown,
  PriceList,
} from '@shared/models/cmdb.model';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { ToastService } from '@shared/services/toast.service';

interface CalculatorLine {
  offering: ServiceOffering;
  effectivePrice: EffectivePrice | null;
  breakdown: OfferingCostBreakdown[];
  quantity: number;
  loading: boolean;
  expanded: boolean;
  saving: boolean;
}

@Component({
  selector: 'nimbus-cost-calculator',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="calculator-page">
        <div class="page-header">
          <h1>Cost Calculator</h1>
        </div>
        <p class="page-description">
          Estimate costs for service offerings using the pricing engine. Add offerings
          to see effective prices, cost breakdowns, and running totals.
        </p>

        <!-- Pricing context -->
        <div class="context-section">
          <div class="context-section-title">Pricing Context</div>
          <div class="context-grid">
            @if (canManageClients()) {
              <div class="context-field">
                <label class="context-field-label">Target Tenant</label>
                <nimbus-searchable-select
                  [(ngModel)]="selectedTenantId"
                  [options]="tenantOptions()"
                  placeholder="Current tenant"
                />
              </div>
              <div class="context-field">
                <label class="context-field-label">Price List</label>
                <nimbus-searchable-select
                  [(ngModel)]="selectedPriceListId"
                  [options]="priceListOptions()"
                  placeholder="Default (auto-resolve)"
                />
              </div>
            }
            <div class="context-field">
              <label class="context-field-label">Delivery Region</label>
              <nimbus-searchable-select
                [(ngModel)]="selectedRegionId"
                [options]="regionOptions()"
                placeholder="Any region"
              />
            </div>
            <div class="context-field">
              <label class="context-field-label">Coverage Model</label>
              <nimbus-searchable-select
                [(ngModel)]="selectedCoverageModel"
                [options]="coverageModelOptions"
                placeholder="Any coverage"
              />
            </div>
            <div class="context-field context-field-action">
              <button
                class="btn btn-secondary"
                [disabled]="lines().length === 0 || refreshing()"
                (click)="refreshAll()"
                title="Re-resolve all lines with current context"
              >
                @if (refreshing()) {
                  Refreshing...
                } @else {
                  Refresh All
                }
              </button>
            </div>
          </div>
        </div>

        <!-- Tenant context info bar -->
        <div class="context-bar">
          <span class="context-label">Tenant:</span>
          <span class="context-value">{{ effectiveTenantLabel() }}</span>
          @if (selectedPriceListId) {
            <span class="context-separator">|</span>
            <span class="context-label">Price List:</span>
            <span class="context-value">{{ selectedPriceListLabel() }}</span>
          }
          @if (selectedRegionId) {
            <span class="context-separator">|</span>
            <span class="context-label">Region:</span>
            <span class="context-value">{{ selectedRegionLabel() }}</span>
          }
          @if (selectedCoverageModel) {
            <span class="context-separator">|</span>
            <span class="context-label">Coverage:</span>
            <span class="context-value">{{ selectedCoverageModel }}</span>
          }
        </div>

        <!-- Add offering -->
        <div class="add-section">
          <nimbus-searchable-select
            [(ngModel)]="selectedOfferingId"
            [options]="offeringOptions()"
            placeholder="Add an offering..."
          />
          <button
            class="btn btn-primary"
            [disabled]="!selectedOfferingId"
            (click)="addOffering()"
          >+ Add</button>
        </div>

        @if (lines().length === 0) {
          <div class="empty-state">
            Add offerings above to calculate costs.
          </div>
        }

        <!-- Calculator lines -->
        @for (line of lines(); track line.offering.id; let i = $index) {
          <div class="line-card">
            <div class="line-header">
              <div class="line-info">
                <span class="line-name">{{ line.offering.name }}</span>
                @if (line.offering.category) {
                  <span class="badge badge-category">{{ line.offering.category }}</span>
                }
                @if (line.effectivePrice?.hasOverride) {
                  <span class="badge badge-override">Override</span>
                }
                @if (line.effectivePrice?.sourceType) {
                  <span class="badge badge-source">{{ line.effectivePrice!.sourceType }}</span>
                }
              </div>
              <div class="line-actions">
                <button
                  class="btn-icon btn-save"
                  (click)="saveAsEstimation(i)"
                  [disabled]="line.saving || !line.effectivePrice"
                  [title]="line.saving ? 'Saving...' : 'Save as estimation'"
                >
                  @if (line.saving) {
                    <span class="spinner-sm"></span>
                  } @else {
                    &#128190;
                  }
                </button>
                <button
                  class="btn-icon"
                  (click)="toggleExpand(i)"
                  [title]="line.expanded ? 'Collapse' : 'Expand breakdown'"
                >{{ line.expanded ? '&#9650;' : '&#9660;' }}</button>
                <button
                  class="btn-icon btn-danger"
                  (click)="removeLine(i)"
                  title="Remove"
                >&times;</button>
              </div>
            </div>

            @if (line.loading) {
              <div class="line-loading">Loading pricing...</div>
            }

            @if (!line.loading && line.effectivePrice) {
              <div class="line-price-row">
                <div class="price-cell">
                  <span class="price-label">Price/Unit</span>
                  <span class="price-value mono">
                    {{ line.effectivePrice.pricePerUnit | number: '1.2-4' }}
                    {{ line.effectivePrice.currency }}/{{ line.effectivePrice.measuringUnit }}
                  </span>
                </div>
                @if (line.effectivePrice.markupPercent) {
                  <div class="price-cell">
                    <span class="price-label">Markup</span>
                    <span class="price-value">{{ line.effectivePrice.markupPercent | number: '1.0-1' }}%</span>
                  </div>
                }
                @if (line.effectivePrice.discountPercent) {
                  <div class="price-cell">
                    <span class="price-label">Discount</span>
                    <span class="price-value text-green">-{{ line.effectivePrice.discountPercent | number: '1.0-1' }}%</span>
                  </div>
                }
                <div class="price-cell">
                  <span class="price-label">Qty</span>
                  <input
                    class="qty-input"
                    type="number"
                    [ngModel]="line.quantity"
                    (ngModelChange)="updateQuantity(i, $event)"
                    min="1"
                    step="1"
                  />
                </div>
                <div class="price-cell price-total">
                  <span class="price-label">Subtotal</span>
                  <span class="price-value mono">
                    {{ lineSubtotal(line) | number: '1.2-2' }}
                    {{ line.effectivePrice.currency }}
                  </span>
                </div>
              </div>
            }

            @if (!line.loading && !line.effectivePrice) {
              <div class="line-no-price">No effective price found for this offering.</div>
            }

            <!-- Expanded breakdown -->
            @if (line.expanded && line.breakdown.length > 0) {
              <div class="breakdown-section">
                <div class="breakdown-title">Cost Breakdown</div>
                <table class="breakdown-table">
                  <thead>
                    <tr>
                      <th>Component</th>
                      <th>Type</th>
                      <th>Qty</th>
                      <th>Price/Unit</th>
                      <th>Required</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of line.breakdown; track item.sourceId) {
                      <tr>
                        <td class="name-cell">{{ item.sourceName }}</td>
                        <td>
                          <span class="badge badge-type">{{ item.sourceType }}</span>
                        </td>
                        <td class="mono">{{ item.quantity }}</td>
                        <td class="mono">{{ item.pricePerUnit | number: '1.2-4' }} {{ item.currency }}/{{ item.measuringUnit }}</td>
                        <td>
                          @if (item.isRequired) {
                            <span class="text-green">Yes</span>
                          } @else {
                            <span class="text-muted">Optional</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }

            @if (line.expanded && line.breakdown.length === 0 && !line.loading) {
              <div class="breakdown-section">
                <div class="empty-hint">No breakdown components available.</div>
              </div>
            }
          </div>
        }

        <!-- Running total -->
        @if (lines().length > 0) {
          <div class="total-bar">
            <span class="total-label">Estimated Total</span>
            <span class="total-value mono">{{ grandTotal() | number: '1.2-2' }}</span>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .calculator-page { padding: 0; max-width: 960px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .page-description {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 1.5rem;
    }

    /* ── Pricing context section ───────────────────────────────── */
    .context-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .context-section-title {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;
    }
    .context-grid {
      display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end;
    }
    .context-field { display: flex; flex-direction: column; gap: 0.25rem; min-width: 180px; flex: 1; }
    .context-field-label {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .context-field-action { flex: 0 0 auto; min-width: auto; align-self: flex-end; }

    .context-bar {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.5rem 0.75rem; background: #eff6ff; border: 1px solid #bfdbfe;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      flex-wrap: wrap;
    }
    .context-label { color: #64748b; font-weight: 500; }
    .context-value { color: #1e293b; font-weight: 600; }
    .context-separator { color: #cbd5e1; }

    .add-section {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1.5rem;
    }
    .add-section nimbus-searchable-select { flex: 1; }

    .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* ── Line cards ────────────────────────────────────────────── */
    .line-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem;
    }
    .line-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .line-info { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .line-name { font-weight: 600; color: #1e293b; font-size: 0.9375rem; }
    .line-actions { display: flex; gap: 0.25rem; }

    .line-loading, .line-no-price {
      font-size: 0.8125rem; color: #94a3b8; padding: 0.25rem 0;
    }

    .line-price-row {
      display: flex; align-items: flex-end; gap: 1.5rem; flex-wrap: wrap;
    }
    .price-cell { display: flex; flex-direction: column; gap: 0.125rem; }
    .price-label { font-size: 0.6875rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; }
    .price-value { font-size: 0.875rem; color: #1e293b; font-weight: 500; }
    .price-total { margin-left: auto; }
    .price-total .price-value { font-weight: 700; font-size: 1rem; }

    .qty-input {
      width: 72px; padding: 0.375rem 0.5rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8125rem;
      font-family: 'JetBrains Mono', 'Fira Code', monospace; box-sizing: border-box;
    }
    .qty-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }

    /* ── Breakdown ─────────────────────────────────────────────── */
    .breakdown-section {
      margin-top: 0.75rem; padding-top: 0.75rem;
      border-top: 1px solid #f1f5f9;
    }
    .breakdown-title {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;
    }
    .breakdown-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .breakdown-table th, .breakdown-table td {
      padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f8fafc;
      color: #374151;
    }
    .breakdown-table th {
      font-weight: 600; color: #64748b; font-size: 0.6875rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .name-cell { font-weight: 500; color: #1e293b; }

    .empty-hint {
      color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0;
    }

    /* ── Total bar ─────────────────────────────────────────────── */
    .total-bar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem 1.25rem; background: #fff; border: 2px solid #3b82f6;
      border-radius: 8px; margin-top: 0.5rem;
    }
    .total-label {
      font-size: 1rem; font-weight: 600; color: #1e293b;
    }
    .total-value {
      font-size: 1.25rem; font-weight: 700; color: #1e293b;
    }

    /* ── Badges ────────────────────────────────────────────────── */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-category { background: #f1f5f9; color: #475569; }
    .badge-override { background: #fef3c7; color: #92400e; }
    .badge-source { background: #eff6ff; color: #3b82f6; }
    .badge-type { background: #f0fdf4; color: #15803d; }
    .badge-status { padding: 0.0625rem 0.375rem; border-radius: 8px; font-size: 0.625rem; font-weight: 600; }
    .badge-status-published { background: #dcfce7; color: #15803d; }
    .badge-status-draft { background: #fef3c7; color: #92400e; }
    .badge-status-archived { background: #f1f5f9; color: #64748b; }

    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .text-muted { color: #94a3b8; }
    .text-green { color: #16a34a; font-weight: 500; }

    /* ── Buttons ───────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #e2e8f0; color: #1e293b; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 1rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-icon:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-icon:disabled:hover { background: none; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
    .btn-save { color: #3b82f6; font-size: 0.875rem; }
    .btn-save:hover { background: #eff6ff; color: #2563eb; }

    /* ── Spinner ───────────────────────────────────────────────── */
    .spinner-sm {
      display: inline-block; width: 14px; height: 14px;
      border: 2px solid #e2e8f0; border-top-color: #3b82f6;
      border-radius: 50%; animation: spin 0.6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class CostCalculatorComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private deliveryService = inject(DeliveryService);
  private tenantService = inject(TenantService);
  private tenantContext = inject(TenantContextService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  // ── Reference data ──────────────────────────────────────────────
  offerings = signal<ServiceOffering[]>([]);
  tenants = signal<Tenant[]>([]);
  priceLists = signal<PriceList[]>([]);
  regions = signal<DeliveryRegion[]>([]);

  // ── Calculator state ────────────────────────────────────────────
  lines = signal<CalculatorLine[]>([]);
  selectedOfferingId = '';
  refreshing = signal(false);

  // ── Pricing context selections ──────────────────────────────────
  selectedTenantId = '';
  selectedPriceListId = '';
  selectedRegionId = '';
  selectedCoverageModel = '';

  // ── Provider mode ───────────────────────────────────────────────
  canManageClients = computed(() => this.tenantContext.canManageClients());

  // ── Coverage model options (static) ─────────────────────────────
  coverageModelOptions = [
    { value: 'business_hours', label: 'Business Hours' },
    { value: 'extended', label: 'Extended' },
    { value: '24x7', label: '24x7' },
  ];

  // ── Computed option lists ───────────────────────────────────────

  tenantOptions = computed(() =>
    this.tenants().map(t => ({ value: t.id, label: t.name })),
  );

  priceListOptions = computed(() =>
    this.priceLists().map(pl => ({
      value: pl.id,
      label: `${pl.name} v${pl.versionMajor}.${pl.versionMinor}${pl.versionLabel ? ' (' + pl.versionLabel + ')' : ''} [${pl.status}]`,
    })),
  );

  regionOptions = computed(() =>
    this.regions().map(r => ({ value: r.id, label: r.displayName || r.name })),
  );

  tenantName = computed(() => {
    const tenant = this.tenantContext.currentTenant();
    return tenant?.tenant_name || this.tenantContext.currentTenantId() || 'Current Tenant';
  });

  effectiveTenantLabel = computed(() => {
    if (this.selectedTenantId) {
      const t = this.tenants().find(t => t.id === this.selectedTenantId);
      return t?.name || this.selectedTenantId;
    }
    return this.tenantName();
  });

  selectedPriceListLabel = computed(() => {
    const pl = this.priceLists().find(p => p.id === this.selectedPriceListId);
    return pl ? `${pl.name} v${pl.versionMajor}.${pl.versionMinor}` : this.selectedPriceListId;
  });

  selectedRegionLabel = computed(() => {
    const r = this.regions().find(r => r.id === this.selectedRegionId);
    return r ? (r.displayName || r.name) : this.selectedRegionId;
  });

  offeringOptions = computed(() => {
    const addedIds = new Set(this.lines().map(l => l.offering.id));
    return this.offerings()
      .filter(o => !addedIds.has(o.id))
      .map(o => ({
        value: o.id,
        label: o.category ? `${o.name} (${o.category})` : o.name,
      }));
  });

  grandTotal = computed(() => {
    return this.lines().reduce((sum, line) => sum + this.lineSubtotal(line), 0);
  });

  // ── Lifecycle ───────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadOfferings();
    this.loadRegions();
    if (this.canManageClients()) {
      this.loadTenants();
      this.loadPriceLists();
    }
  }

  // ── Public actions ──────────────────────────────────────────────

  addOffering(): void {
    if (!this.selectedOfferingId) return;
    const offering = this.offerings().find(o => o.id === this.selectedOfferingId);
    if (!offering) return;

    const newLine: CalculatorLine = {
      offering,
      effectivePrice: null,
      breakdown: [],
      quantity: 1,
      loading: true,
      expanded: false,
      saving: false,
    };

    this.lines.update(lines => [...lines, newLine]);
    this.selectedOfferingId = '';

    const idx = this.lines().length - 1;
    this.loadLineData(idx, offering.id);
  }

  removeLine(index: number): void {
    this.lines.update(lines => lines.filter((_, i) => i !== index));
  }

  toggleExpand(index: number): void {
    this.lines.update(lines => lines.map((line, i) =>
      i === index ? { ...line, expanded: !line.expanded } : line,
    ));
  }

  updateQuantity(index: number, qty: number): void {
    this.lines.update(lines => lines.map((line, i) =>
      i === index ? { ...line, quantity: Math.max(1, qty || 1) } : line,
    ));
  }

  lineSubtotal(line: CalculatorLine): number {
    if (!line.effectivePrice) return 0;
    return line.effectivePrice.pricePerUnit * line.quantity;
  }

  refreshAll(): void {
    const currentLines = this.lines();
    if (currentLines.length === 0) return;

    this.refreshing.set(true);

    // Mark all lines as loading
    this.lines.update(lines => lines.map(line => ({
      ...line,
      loading: true,
      effectivePrice: null,
      breakdown: [],
    })));

    let pendingCount = currentLines.length;
    const checkAllDone = () => {
      pendingCount--;
      if (pendingCount <= 0) {
        this.refreshing.set(false);
      }
    };

    currentLines.forEach((line, idx) => {
      this.loadLineData(idx, line.offering.id, checkAllDone);
    });
  }

  saveAsEstimation(index: number): void {
    const line = this.lines()[index];
    if (!line || !line.effectivePrice) return;

    // Mark line as saving
    this.lines.update(lines => lines.map((l, i) =>
      i === index ? { ...l, saving: true } : l,
    ));

    const clientTenantId = this.selectedTenantId || this.tenantContext.currentTenantId() || '';

    this.deliveryService.createEstimation({
      clientTenantId,
      serviceOfferingId: line.offering.id,
      deliveryRegionId: this.selectedRegionId || null,
      coverageModel: this.selectedCoverageModel || null,
      priceListId: this.selectedPriceListId || null,
      quantity: line.quantity,
      sellPricePerUnit: line.effectivePrice.pricePerUnit,
      sellCurrency: line.effectivePrice.currency,
    }).subscribe({
      next: (estimation) => {
        this.lines.update(lines => lines.map((l, i) =>
          i === index ? { ...l, saving: false } : l,
        ));
        this.toastService.success('Estimation created successfully');
        this.router.navigate(['/catalog/estimations', estimation.id]);
      },
      error: () => {
        this.lines.update(lines => lines.map((l, i) =>
          i === index ? { ...l, saving: false } : l,
        ));
        this.toastService.error('Failed to create estimation');
      },
    });
  }

  // ── Private helpers ─────────────────────────────────────────────

  private getPricingContext(): {
    tenantId?: string;
    priceListId?: string;
    deliveryRegionId?: string;
    coverageModel?: string;
  } {
    return {
      tenantId: this.selectedTenantId || undefined,
      priceListId: this.selectedPriceListId || undefined,
      deliveryRegionId: this.selectedRegionId || undefined,
      coverageModel: this.selectedCoverageModel || undefined,
    };
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (result) => this.offerings.set(result.items),
      error: () => this.toastService.error('Failed to load offerings'),
    });
  }

  private loadTenants(): void {
    this.tenantService.listTenants(0, 200).subscribe({
      next: (tenants) => this.tenants.set(tenants),
      error: () => this.toastService.error('Failed to load tenants'),
    });
  }

  private loadPriceLists(): void {
    this.catalogService.listPriceLists(0, 200).subscribe({
      next: (result) => this.priceLists.set(result.items),
      error: () => this.toastService.error('Failed to load price lists'),
    });
  }

  private loadRegions(): void {
    this.deliveryService.listRegions({ isActive: true, limit: 200 }).subscribe({
      next: (result) => this.regions.set(result.items),
      error: () => this.toastService.error('Failed to load delivery regions'),
    });
  }

  private loadLineData(index: number, offeringId: string, onComplete?: () => void): void {
    let completed = 0;
    const ctx = this.getPricingContext();

    const checkDone = () => {
      completed++;
      if (completed >= 2) {
        this.lines.update(lines => lines.map((line, i) =>
          i === index ? { ...line, loading: false } : line,
        ));
        onComplete?.();
      }
    };

    this.catalogService.getEffectivePrice(offeringId, ctx).subscribe({
      next: (price) => {
        this.lines.update(lines => lines.map((line, i) =>
          i === index ? { ...line, effectivePrice: price } : line,
        ));
        checkDone();
      },
      error: () => checkDone(),
    });

    this.catalogService.getOfferingCostBreakdown(offeringId, ctx).subscribe({
      next: (breakdown) => {
        this.lines.update(lines => lines.map((line, i) =>
          i === index ? { ...line, breakdown } : line,
        ));
        checkDone();
      },
      error: () => checkDone(),
    });
  }
}
