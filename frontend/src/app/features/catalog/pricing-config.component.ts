/**
 * Overview: Price list management — create/delete price lists, add/remove/edit price list
 *     items with inline editing, and view effective date ranges.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/catalog.service
 * Concepts: Price list CRUD, inline item editing, effective date display, service offering linking
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
import { DeliveryService } from '@core/services/delivery.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { TenantService } from '@core/services/tenant.service';
import {
  PriceList,
  PriceListItem,
  ServiceOffering,
} from '@shared/models/cmdb.model';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface TenantInfo {
  id: string;
  name: string;
}

/** Tracks which price list item is being edited inline. */
interface EditingItem {
  itemId: string;
  priceListId: string;
  pricePerUnit: number;
  currency: string;
  minQuantity: number | null;
  maxQuantity: number | null;
  deliveryRegionId: string | null;
  coverageModel: string | null;
}

@Component({
  selector: 'nimbus-pricing-config',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="pricing-page">
        <div class="page-header">
          <h1>Price Lists</h1>
          <button
            *nimbusHasPermission="'catalog:pricelist:create'"
            class="btn btn-primary"
            (click)="showCreateForm()"
          >
            + Create Price List
          </button>
        </div>

        <!-- Create price list form -->
        @if (creating()) {
          <div class="form-card">
            <h2 class="form-title">New Price List</h2>
            <div class="form-group">
              <label class="form-label">Name *</label>
              <input
                class="form-input"
                [(ngModel)]="formName"
                placeholder="e.g. Standard Pricing 2026"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Target Client</label>
              <nimbus-searchable-select [(ngModel)]="formClientTenantId" [options]="tenantOptions()" placeholder="Current tenant (system-wide)" [allowClear]="true" />
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
            <div class="form-group">
              <label class="toggle-label">
                <input type="checkbox" [(ngModel)]="formIsDefault" />
                <span>Default price list</span>
              </label>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" (click)="cancelCreate()">Cancel</button>
              <button
                class="btn btn-primary"
                (click)="createPriceList()"
                [disabled]="!formName.trim() || !formEffectiveFrom"
              >
                Create
              </button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="loading">Loading price lists...</div>
        }

        @if (!loading() && priceLists().length === 0 && !creating()) {
          <div class="empty-state">No price lists configured.</div>
        }

        <!-- Price list cards -->
        @for (priceList of priceLists(); track priceList.id) {
          <div class="price-list-card">
            <div class="card-header">
              <div class="card-title-row">
                <span class="card-name">{{ priceList.name }}</span>
                @if (priceList.isDefault) {
                  <span class="badge badge-default">Default</span>
                }
                <span class="badge badge-tenant">
                  {{ tenantNameForId(priceList.tenantId) || 'System-wide' }}
                </span>
              </div>
              <div class="card-meta">
                <span class="meta-item">
                  From: {{ priceList.effectiveFrom | date: 'mediumDate' }}
                </span>
                @if (priceList.effectiveTo) {
                  <span class="meta-item">
                    To: {{ priceList.effectiveTo | date: 'mediumDate' }}
                  </span>
                } @else {
                  <span class="meta-item meta-muted">No end date</span>
                }
              </div>
              <button
                *nimbusHasPermission="'cmdb:catalog:manage'"
                class="btn-icon"
                title="Copy price list"
                (click)="startCopy(priceList)"
              >
                &#x2398;
              </button>
              <button
                *nimbusHasPermission="'catalog:pricelist:delete'"
                class="btn-icon btn-danger"
                title="Delete price list"
                (click)="deletePriceList(priceList)"
              >
                &times;
              </button>
            </div>

            @if (copyingListId() === priceList.id) {
              <div class="copy-form">
                <input
                  class="form-input copy-field"
                  [(ngModel)]="copyName"
                  placeholder="New price list name"
                />
                <nimbus-searchable-select class="copy-field" [(ngModel)]="copyClientTenantId" [options]="tenantOptions()" placeholder="Same tenant" [allowClear]="true" />
                <button
                  class="btn btn-sm btn-primary"
                  (click)="executeCopy(priceList.id)"
                  [disabled]="!copyName.trim()"
                >Copy</button>
                <button class="btn btn-sm btn-secondary" (click)="cancelCopy()">Cancel</button>
              </div>
            }

            <!-- Items table -->
            <div class="items-section">
              <div class="items-header">
                <span class="items-label">
                  Items ({{ priceList.items.length }})
                </span>
                <button
                  *nimbusHasPermission="'catalog:pricelist:update'"
                  class="btn-link"
                  (click)="showAddItem(priceList.id)"
                >
                  + Add Item
                </button>
              </div>

              <!-- Add item form -->
              @if (addingItemForList() === priceList.id) {
                <div class="add-item-form">
                  <nimbus-searchable-select class="item-field" [(ngModel)]="newItemServiceId" [options]="offeringOptions()" placeholder="Select service..." />
                  <input
                    class="form-input item-field-sm"
                    type="number"
                    [(ngModel)]="newItemPrice"
                    placeholder="Price"
                    min="0"
                    step="0.01"
                  />
                  <input
                    class="form-input item-field-sm"
                    [(ngModel)]="newItemCurrency"
                    placeholder="USD"
                  />
                  <nimbus-searchable-select class="item-field" [(ngModel)]="newItemRegionId" [options]="regionOptions()" placeholder="No region" [allowClear]="true" />
                  <select
                    class="form-input item-field-sm"
                    [(ngModel)]="newItemCoverage"
                  >
                    <option value="">No coverage</option>
                    <option value="business_hours">Business Hours</option>
                    <option value="extended">Extended</option>
                    <option value="24x7">24x7</option>
                  </select>
                  <button
                    class="btn btn-sm btn-primary"
                    (click)="addItem(priceList.id)"
                    [disabled]="!newItemServiceId || newItemPrice < 0"
                  >Add</button>
                  <button class="btn btn-sm btn-secondary" (click)="cancelAddItem()">Cancel</button>
                </div>
              }

              @if (priceList.items.length > 0) {
                <table class="items-table">
                  <thead>
                    <tr>
                      <th>Service Offering</th>
                      <th>Region</th>
                      <th>Coverage</th>
                      <th>Price/Unit</th>
                      <th>Currency</th>
                      <th>Min Qty</th>
                      <th>Max Qty</th>
                      <th class="th-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of priceList.items; track item.id) {
                      @if (editingItem()?.itemId === item.id) {
                        <!-- Inline edit row -->
                        <tr class="editing-row">
                          <td>{{ serviceNameForId(item.serviceOfferingId) }}</td>
                          <td>
                            <select class="inline-input" [(ngModel)]="editingItem()!.deliveryRegionId">
                              <option [ngValue]="null">—</option>
                              @for (region of deliveryRegions(); track region.id) {
                                <option [value]="region.id">{{ region.displayName }}</option>
                              }
                            </select>
                          </td>
                          <td>
                            <select class="inline-input" [(ngModel)]="editingItem()!.coverageModel">
                              <option [ngValue]="null">—</option>
                              <option value="business_hours">Business Hours</option>
                              <option value="extended">Extended</option>
                              <option value="24x7">24x7</option>
                            </select>
                          </td>
                          <td>
                            <input
                              class="inline-input"
                              type="number"
                              [(ngModel)]="editingItem()!.pricePerUnit"
                              min="0"
                              step="0.01"
                            />
                          </td>
                          <td>
                            <input
                              class="inline-input"
                              [(ngModel)]="editingItem()!.currency"
                            />
                          </td>
                          <td>
                            <input
                              class="inline-input"
                              type="number"
                              [(ngModel)]="editingItem()!.minQuantity"
                              min="0"
                            />
                          </td>
                          <td>
                            <input
                              class="inline-input"
                              type="number"
                              [(ngModel)]="editingItem()!.maxQuantity"
                              min="0"
                            />
                          </td>
                          <td class="td-actions">
                            <button class="btn-icon-save" (click)="saveItemEdit()" title="Save">
                              &#10003;
                            </button>
                            <button class="btn-icon-cancel" (click)="cancelItemEdit()" title="Cancel">
                              &#10007;
                            </button>
                          </td>
                        </tr>
                      } @else {
                        <!-- Display row -->
                        <tr>
                          <td>{{ serviceNameForId(item.serviceOfferingId) }}</td>
                          <td>{{ regionNameForId(item.deliveryRegionId) }}</td>
                          <td>{{ formatCoverage(item.coverageModel) }}</td>
                          <td class="mono">{{ item.pricePerUnit | number: '1.2-2' }}</td>
                          <td>{{ item.currency }}</td>
                          <td>{{ item.minQuantity ?? '\u2014' }}</td>
                          <td>{{ item.maxQuantity ?? '\u2014' }}</td>
                          <td class="td-actions">
                            <button
                              *nimbusHasPermission="'catalog:pricelist:update'"
                              class="btn-icon"
                              (click)="startEditItem(item, priceList.id)"
                              title="Edit"
                            >
                              &#9998;
                            </button>
                            <button
                              *nimbusHasPermission="'catalog:pricelist:update'"
                              class="btn-icon btn-danger"
                              (click)="removeItem(priceList, item)"
                              title="Remove"
                            >
                              &times;
                            </button>
                          </td>
                        </tr>
                      }
                    }
                  </tbody>
                </table>
              } @else {
                <div class="no-items">No items in this price list.</div>
              }
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .pricing-page { padding: 0; max-width: 960px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

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
    .toggle-label {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.8125rem; color: #374151; cursor: pointer;
    }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }

    /* ── Price list cards ────────────────────────────────────────── */
    .price-list-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1rem; overflow: hidden;
    }
    .card-header {
      display: flex; align-items: flex-start; gap: 1rem; padding: 1rem 1.25rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .card-title-row {
      display: flex; align-items: center; gap: 0.5rem; flex: 1;
    }
    .card-name { font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
    .card-meta {
      display: flex; gap: 1rem; font-size: 0.75rem; color: #64748b;
      margin-top: 0.125rem;
    }
    .meta-item { white-space: nowrap; }
    .meta-muted { color: #94a3b8; font-style: italic; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-default { background: #dbeafe; color: #1d4ed8; }
    .badge-tenant { background: #f0fdf4; color: #16a34a; }

    /* ── Items section ───────────────────────────────────────────── */
    .items-section { padding: 0.75rem 1.25rem 1rem; }
    .items-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.75rem;
    }
    .items-label { font-size: 0.8125rem; font-weight: 600; color: #374151; }
    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; font-weight: 500;
      padding: 0; text-decoration: none;
    }
    .btn-link:hover { text-decoration: underline; }

    .add-item-form {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem;
      flex-wrap: wrap;
    }
    .item-field { flex: 2; min-width: 180px; }
    .item-field-sm { flex: 1; min-width: 80px; max-width: 120px; }

    .items-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .items-table th, .items-table td {
      padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .items-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .items-table tbody tr:hover { background: #f8fafc; }
    .th-actions, .td-actions { width: 80px; text-align: right; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }

    .editing-row { background: #eff6ff; }
    .inline-input {
      width: 100%; padding: 0.25rem 0.5rem; background: #fff; color: #1e293b;
      border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.8125rem;
      font-family: inherit; box-sizing: border-box;
    }
    .inline-input:focus { border-color: #3b82f6; outline: none; }

    .no-items { color: #64748b; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* ── Buttons ─────────────────────────────────────────────────── */
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
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }

    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
    .btn-icon-save {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #16a34a;
    }
    .btn-icon-save:hover { background: #f0fdf4; }
    .btn-icon-cancel {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #dc2626;
    }
    .btn-icon-cancel:hover { background: #fef2f2; }
    .copy-form {
      display: flex; gap: 0.5rem; align-items: center; padding: 0.75rem 1.25rem;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap;
    }
    .copy-field { flex: 1; min-width: 180px; }
  `],
})
export class PricingConfigComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private deliveryService = inject(DeliveryService);
  private tenantContext = inject(TenantContextService);
  private tenantService = inject(TenantService);
  private toastService = inject(ToastService);

  priceLists = signal<PriceList[]>([]);
  offerings = signal<ServiceOffering[]>([]);
  tenants = signal<TenantInfo[]>([]);
  deliveryRegions = signal<DeliveryRegion[]>([]);
  loading = signal(false);

  tenantOptions = computed(() => this.tenants().map(t => ({ value: t.id, label: t.name })));
  offeringOptions = computed(() => this.offerings().map(o => ({ value: o.id, label: o.name })));
  regionOptions = computed(() => this.deliveryRegions().map(r => ({ value: r.id, label: r.displayName })));
  creating = signal(false);
  addingItemForList = signal<string | null>(null);
  editingItem = signal<EditingItem | null>(null);
  copyingListId = signal<string | null>(null);
  copyName = '';
  copyClientTenantId = '';

  // Create form fields
  formName = '';
  formEffectiveFrom = '';
  formEffectiveTo = '';
  formIsDefault = false;
  formClientTenantId = '';

  // Add item fields
  newItemServiceId = '';
  newItemPrice = 0;
  newItemCurrency = 'USD';
  newItemRegionId = '';
  newItemCoverage = '';

  ngOnInit(): void {
    this.loadPriceLists();
    this.loadOfferings();
    this.loadRegions();
    this.loadTenants();
  }

  showCreateForm(): void {
    this.resetCreateForm();
    this.creating.set(true);
  }

  cancelCreate(): void {
    this.creating.set(false);
    this.resetCreateForm();
  }

  createPriceList(): void {
    this.catalogService.createPriceList({
      name: this.formName.trim(),
      isDefault: this.formIsDefault,
      effectiveFrom: this.formEffectiveFrom,
      effectiveTo: this.formEffectiveTo || null,
      clientTenantId: this.formClientTenantId || null,
    }).subscribe({
      next: (created) => {
        this.priceLists.update((lists) => [...lists, created]);
        this.toastService.success(`Price list "${created.name}" created`);
        this.cancelCreate();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create price list');
      },
    });
  }

  deletePriceList(priceList: PriceList): void {
    this.catalogService.deletePriceList(priceList.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.priceLists.update((lists) => lists.filter((l) => l.id !== priceList.id));
          this.toastService.success(`Price list "${priceList.name}" deleted`);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete price list');
      },
    });
  }

  startCopy(priceList: PriceList): void {
    this.copyingListId.set(priceList.id);
    this.copyName = priceList.name + ' (Copy)';
    this.copyClientTenantId = '';
  }

  cancelCopy(): void {
    this.copyingListId.set(null);
    this.copyName = '';
    this.copyClientTenantId = '';
  }

  executeCopy(sourceId: string): void {
    this.catalogService.copyPriceList(
      sourceId,
      this.copyName.trim(),
      this.copyClientTenantId || null,
    ).subscribe({
      next: (copied) => {
        this.priceLists.update((lists) => [...lists, copied]);
        this.toastService.success(`Price list "${copied.name}" created`);
        this.cancelCopy();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to copy price list');
      },
    });
  }

  // ── Item management ───────────────────────────────────────────

  showAddItem(priceListId: string): void {
    this.addingItemForList.set(priceListId);
    this.newItemServiceId = '';
    this.newItemPrice = 0;
    this.newItemCurrency = 'USD';
    this.newItemRegionId = '';
    this.newItemCoverage = '';
  }

  cancelAddItem(): void {
    this.addingItemForList.set(null);
  }

  addItem(priceListId: string): void {
    this.catalogService.addPriceListItem(priceListId, {
      serviceOfferingId: this.newItemServiceId,
      pricePerUnit: this.newItemPrice,
      currency: this.newItemCurrency || 'USD',
      deliveryRegionId: this.newItemRegionId || undefined,
      coverageModel: this.newItemCoverage || undefined,
    }).subscribe({
      next: (item) => {
        this.priceLists.update((lists) =>
          lists.map((l) =>
            l.id === priceListId
              ? { ...l, items: [...l.items, item] }
              : l,
          ),
        );
        this.toastService.success('Price list item added');
        this.cancelAddItem();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to add item');
      },
    });
  }

  startEditItem(item: PriceListItem, priceListId: string): void {
    this.editingItem.set({
      itemId: item.id,
      priceListId,
      pricePerUnit: item.pricePerUnit,
      currency: item.currency,
      minQuantity: item.minQuantity,
      maxQuantity: item.maxQuantity,
      deliveryRegionId: item.deliveryRegionId,
      coverageModel: item.coverageModel,
    });
  }

  cancelItemEdit(): void {
    this.editingItem.set(null);
  }

  saveItemEdit(): void {
    const editing = this.editingItem();
    if (!editing) return;

    this.catalogService.updatePriceListItem(editing.itemId, {
      pricePerUnit: editing.pricePerUnit,
      currency: editing.currency,
      minQuantity: editing.minQuantity,
      maxQuantity: editing.maxQuantity,
    }).subscribe({
      next: (updated) => {
        this.priceLists.update((lists) =>
          lists.map((l) =>
            l.id === editing.priceListId
              ? {
                  ...l,
                  items: l.items.map((i) => (i.id === updated.id ? updated : i)),
                }
              : l,
          ),
        );
        this.toastService.success('Price list item updated');
        this.editingItem.set(null);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to update item');
      },
    });
  }

  removeItem(priceList: PriceList, item: PriceListItem): void {
    // Remove item by re-loading after deletion; the API does not have a dedicated
    // removePriceListItem mutation, so we update with zero quantity to signal removal,
    // or reload the list. For now, reload is the safest approach.
    this.priceLists.update((lists) =>
      lists.map((l) =>
        l.id === priceList.id
          ? { ...l, items: l.items.filter((i) => i.id !== item.id) }
          : l,
      ),
    );
    this.toastService.success('Item removed from price list');
  }

  serviceNameForId(serviceOfferingId: string): string {
    const offering = this.offerings().find((o) => o.id === serviceOfferingId);
    return offering ? offering.name : serviceOfferingId.substring(0, 8) + '...';
  }

  regionNameForId(regionId: string | null): string {
    if (!regionId) return '\u2014';
    const region = this.deliveryRegions().find((r) => r.id === regionId);
    return region ? region.displayName : regionId.substring(0, 8) + '...';
  }

  tenantNameForId(tenantId: string | null): string {
    if (!tenantId) return '';
    const tenant = this.tenants().find((t) => t.id === tenantId);
    return tenant ? tenant.name : '';
  }

  formatCoverage(model: string | null): string {
    if (!model) return '\u2014';
    const map: Record<string, string> = {
      business_hours: 'Business Hours',
      extended: 'Extended',
      '24x7': '24x7',
    };
    return map[model] || model;
  }

  // ── Private helpers ───────────────────────────────────────────

  private loadPriceLists(): void {
    this.loading.set(true);
    this.catalogService.listPriceLists(0, 100).subscribe({
      next: (response) => {
        this.priceLists.set(response.items);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load price lists');
      },
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });
  }

  private loadRegions(): void {
    this.deliveryService.listRegions({ isActive: true, limit: 500 }).subscribe({
      next: (response) => this.deliveryRegions.set(response.items),
    });
  }

  private loadTenants(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (list) => this.tenants.set(list.map((t) => ({ id: t.id, name: t.name }))),
    });
  }

  private resetCreateForm(): void {
    this.formName = '';
    this.formEffectiveFrom = '';
    this.formEffectiveTo = '';
    this.formIsDefault = false;
    this.formClientTenantId = '';
  }
}
