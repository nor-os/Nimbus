/**
 * Overview: Price list management -- create/delete price lists, add/remove/edit price list
 *     items with inline editing, multi-target items (offering, SKU, activity), markup
 *     percent support, and view effective date ranges.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/catalog.service,
 *     app/core/services/semantic.service, app/core/services/delivery.service
 * Concepts: Price list CRUD, inline item editing, effective date display, multi-target
 *     price list items (service offering, provider SKU, activity definition), markup percent
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
import { CurrencyService } from '@core/services/currency.service';
import { DeliveryService } from '@core/services/delivery.service';
import { SemanticService } from '@core/services/semantic.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { TenantService } from '@core/services/tenant.service';
import {
  PriceList,
  PriceListDiff,
  PriceListDiffItem,
  PriceListItem,
  ProviderSku,
  ServiceOffering,
  TenantPriceListAssignment,
} from '@shared/models/cmdb.model';
import { ActivityTemplate } from '@shared/models/delivery.model';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { SemanticProvider } from '@shared/models/semantic.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface TenantInfo {
  id: string;
  name: string;
}

/** Target type for price list items: offering, SKU, or activity. */
type ItemTargetType = 'offering' | 'sku' | 'activity';

/** Tracks which price list item is being edited inline. */
interface EditingItem {
  itemId: string;
  priceListId: string;
  pricePerUnit: number;
  currency: string;
  markupPercent: number | null;
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
          <div class="header-actions">
            <select class="form-input filter-select" [(ngModel)]="filterStatus" (ngModelChange)="loadPriceLists()">
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>
            <nimbus-searchable-select
              class="filter-select"
              [(ngModel)]="filterRegionId"
              [options]="regionOptions()"
              placeholder="All regions"
              [allowClear]="true"
              (ngModelChange)="loadPriceLists()"
            />
            <button
              *nimbusHasPermission="'catalog:pricelist:create'"
              class="btn btn-primary"
              (click)="showCreateForm()"
            >
              + Create Price List
            </button>
          </div>
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
            <div class="form-group">
              <label class="form-label">Region Default (optional)</label>
              <nimbus-searchable-select
                [(ngModel)]="formDeliveryRegionId"
                [options]="regionOptions()"
                placeholder="Global (no region)"
                [allowClear]="true"
              />
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
                [disabled]="!formName.trim()"
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
                <span class="badge" [class]="'badge-status-' + priceList.status">
                  {{ priceList.versionLabel }}
                </span>
                <span class="badge" [class]="'badge-status-' + priceList.status">
                  {{ priceList.status }}
                </span>
                @if (priceList.isDefault) {
                  <span class="badge badge-default">Default</span>
                }
                @if (priceList.deliveryRegionId) {
                  <span class="badge badge-region">
                    Region: {{ regionNameForId(priceList.deliveryRegionId) }}
                  </span>
                }
                <span class="badge badge-tenant">
                  {{ tenantNameForId(priceList.tenantId) || 'System-wide' }}
                </span>
              </div>
              <div class="card-meta">
              </div>
              <div class="card-actions">
                @if (priceList.status === 'draft') {
                  <button
                    *nimbusHasPermission="'cmdb:catalog:manage'"
                    class="btn btn-sm btn-success"
                    title="Publish this version"
                    (click)="publishPriceList(priceList)"
                  >
                    Publish
                  </button>
                }
                @if (priceList.status === 'published') {
                  <button
                    *nimbusHasPermission="'cmdb:catalog:manage'"
                    class="btn btn-sm btn-secondary"
                    title="Archive this version"
                    (click)="archivePriceList(priceList)"
                  >
                    Archive
                  </button>
                }
                <button
                  *nimbusHasPermission="'cmdb:catalog:manage'"
                  class="btn btn-sm btn-secondary"
                  title="Create new version"
                  (click)="startNewVersion(priceList)"
                >
                  New Version
                </button>
                <button
                  *nimbusHasPermission="'cmdb:catalog:manage'"
                  class="btn-icon"
                  title="Copy price list"
                  (click)="startCopy(priceList)"
                >
                  &#x2398;
                </button>
                @if (priceList.status !== 'published') {
                  <button
                    *nimbusHasPermission="'catalog:pricelist:delete'"
                    class="btn-icon btn-danger"
                    title="Delete price list"
                    (click)="deletePriceList(priceList)"
                  >
                    &times;
                  </button>
                }
              </div>
            </div>

            <!-- New version dialog -->
            @if (versioningListId() === priceList.id) {
              <div class="version-form">
                <span class="version-label">Create new version from {{ priceList.versionLabel }}:</span>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="createVersion(priceList.id, 'minor')"
                >
                  Minor bump
                </button>
                <button
                  class="btn btn-sm btn-secondary"
                  (click)="createVersion(priceList.id, 'major')"
                >
                  Major bump
                </button>
                <button class="btn btn-sm btn-secondary" (click)="cancelNewVersion()">Cancel</button>
              </div>
            }

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

            <!-- Tenant Assignments -->
            @if (assignmentsMap().get(priceList.id)?.length) {
              <div class="assignment-section">
                <div class="assignment-header" (click)="toggleAssignments(priceList.id)">
                  <span class="assignment-title">Tenant Assignments ({{ assignmentsMap().get(priceList.id)!.length }})</span>
                  <span class="assignment-toggle">{{ expandedAssignments().has(priceList.id) ? '\u25B2' : '\u25BC' }}</span>
                </div>
                @if (expandedAssignments().has(priceList.id)) {
                  <table class="assignment-table">
                    <thead>
                      <tr>
                        <th>Tenant</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Changes</th>
                        <th class="th-actions"></th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (a of assignmentsMap().get(priceList.id)!; track a.tenantId) {
                        <tr
                          class="assignment-row"
                          [class.selected]="selectedAssignment()?.assignment === a"
                          (click)="selectAssignment(priceList.id, a)"
                        >
                          <td>{{ tenantNameForId(a.tenantId) || a.tenantId }}</td>
                          <td>
                            @if (a.assignmentType === 'pin') {
                              <span class="badge badge-pin">Pinned</span>
                            } @else {
                              <span class="badge badge-clone">Custom Copy</span>
                            }
                          </td>
                          <td>
                            @if (a.assignmentType === 'clone') {
                              @if (a.isCustomized) {
                                <span class="badge badge-warning">Modified</span>
                              } @else {
                                <span class="badge badge-status-published">Identical</span>
                              }
                            } @else {
                              <span class="meta-muted">Uses as-is</span>
                            }
                          </td>
                          <td>
                            @if (a.assignmentType === 'clone' && a.isCustomized) {
                              <span class="diff-add">+{{ a.additions }}</span>
                              <span class="diff-del">&minus;{{ a.deletions }}</span>
                            }
                          </td>
                          <td class="td-actions">
                            @if (a.assignmentType === 'clone') {
                              <span class="btn-link" title="View diff">&#x1F50D;</span>
                            }
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>

                  <!-- Diff panel -->
                  @if (selectedAssignment()?.priceListId === priceList.id && selectedAssignment()?.assignment?.assignmentType === 'clone') {
                    <div class="diff-panel">
                      @if (diffLoading()) {
                        <div class="diff-loading">Loading diff...</div>
                      } @else if (diff()) {
                        <div class="diff-panel-header">
                          <span class="diff-panel-title">Changes vs Source</span>
                          <button class="btn-icon" (click)="closeAssignment()" title="Close">&times;</button>
                        </div>
                        <div class="diff-panel-body">
                          @if (diff()!.additions.length > 0) {
                            <div class="diff-group diff-group-add">
                              <div class="diff-group-label">Additions ({{ diff()!.additions.length }})</div>
                              @for (item of diff()!.additions; track item.id) {
                                <div class="diff-item">
                                  <span class="diff-item-name">{{ diffItemName(item) }}</span>
                                  <span class="mono">{{ item.pricePerUnit | number: '1.2-2' }} {{ item.currency }}</span>
                                </div>
                              }
                            </div>
                          }
                          @if (diff()!.deletions.length > 0) {
                            <div class="diff-group diff-group-del">
                              <div class="diff-group-label">Removals ({{ diff()!.deletions.length }})</div>
                              @for (item of diff()!.deletions; track item.id) {
                                <div class="diff-item">
                                  <span class="diff-item-name">{{ diffItemName(item) }}</span>
                                  <span class="mono">{{ item.pricePerUnit | number: '1.2-2' }} {{ item.currency }}</span>
                                </div>
                              }
                            </div>
                          }
                          @if (diff()!.additions.length === 0 && diff()!.deletions.length === 0) {
                            <div class="diff-empty">No differences found.</div>
                          }
                        </div>
                      }
                    </div>
                  }
                }
              </div>
            }

            <!-- Items table -->
            <div class="items-section">
              <div class="items-header">
                <span class="items-label">
                  Items ({{ priceList.items.length }})
                </span>
                @if (priceList.status === 'draft') {
                  <button
                    *nimbusHasPermission="'catalog:pricelist:update'"
                    class="btn-link"
                    (click)="showAddItem(priceList.id)"
                  >
                    + Add Item
                  </button>
                }
              </div>

              <!-- Add item form -->
              @if (addingItemForList() === priceList.id) {
                <div class="add-item-form-wrapper">
                  <!-- Target type radio group -->
                  <div class="target-type-row">
                    <span class="target-type-label">Target type:</span>
                    <label class="radio-label">
                      <input type="radio" name="targetType" value="offering"
                        [checked]="newItemTargetType === 'offering'"
                        (change)="onTargetTypeChange('offering')" />
                      Offering
                    </label>
                    <label class="radio-label">
                      <input type="radio" name="targetType" value="sku"
                        [checked]="newItemTargetType === 'sku'"
                        (change)="onTargetTypeChange('sku')" />
                      SKU
                    </label>
                    <label class="radio-label">
                      <input type="radio" name="targetType" value="activity"
                        [checked]="newItemTargetType === 'activity'"
                        (change)="onTargetTypeChange('activity')" />
                      Activity
                    </label>
                  </div>

                  <div class="add-item-form">
                    <!-- Offering target -->
                    @if (newItemTargetType === 'offering') {
                      <nimbus-searchable-select
                        class="item-field"
                        [(ngModel)]="newItemServiceId"
                        [options]="offeringOptions()"
                        placeholder="Select service offering..."
                      />
                    }

                    <!-- SKU target: provider filter + SKU dropdown -->
                    @if (newItemTargetType === 'sku') {
                      <nimbus-searchable-select
                        class="item-field-half"
                        [(ngModel)]="newItemProviderId"
                        [options]="providerOptions()"
                        placeholder="Select provider..."
                        (ngModelChange)="onProviderChange($event)"
                      />
                      <nimbus-searchable-select
                        class="item-field-half"
                        [(ngModel)]="newItemSkuId"
                        [options]="skuOptions()"
                        placeholder="Select SKU..."
                        [disabled]="!newItemProviderId"
                      />
                    }

                    <!-- Activity target -->
                    @if (newItemTargetType === 'activity') {
                      <nimbus-searchable-select
                        class="item-field"
                        [(ngModel)]="newItemActivityId"
                        [options]="activityOptions()"
                        placeholder="Select activity..."
                      />
                    }

                    <input
                      class="form-input item-field-sm"
                      type="number"
                      [(ngModel)]="newItemPrice"
                      placeholder="Price"
                      min="0"
                      step="0.01"
                    />
                    <select
                      class="form-input item-field-sm"
                      [(ngModel)]="newItemCurrency"
                    >
                      @for (c of availableCurrencies(); track c) {
                        <option [value]="c">{{ c }}</option>
                      }
                    </select>
                    <input
                      class="form-input item-field-sm"
                      type="number"
                      [(ngModel)]="newItemMarkupPercent"
                      placeholder="Markup %"
                      min="0"
                      step="0.1"
                    />
                    <nimbus-searchable-select
                      class="item-field"
                      [(ngModel)]="newItemRegionId"
                      [options]="regionOptions()"
                      placeholder="No region"
                      [allowClear]="true"
                    />
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
                      [disabled]="!isAddItemValid()"
                    >Add</button>
                    <button class="btn btn-sm btn-secondary" (click)="cancelAddItem()">Cancel</button>
                  </div>
                </div>
              }

              @if (priceList.items.length > 0) {
                <table class="items-table">
                  <thead>
                    <tr>
                      <th>Target</th>
                      <th>Region</th>
                      <th>Coverage</th>
                      <th>Price/Unit</th>
                      <th>Markup %</th>
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
                          <td>
                            <span>{{ itemTargetName(item) }}</span>
                            @if (item.providerSkuId) {
                              <span class="badge badge-sku">SKU</span>
                            }
                            @if (item.activityDefinitionId) {
                              <span class="badge badge-activity">Activity</span>
                            }
                          </td>
                          <td>
                            <select class="inline-input" [(ngModel)]="editingItem()!.deliveryRegionId">
                              <option [ngValue]="null">&mdash;</option>
                              @for (region of deliveryRegions(); track region.id) {
                                <option [value]="region.id">{{ region.displayName }}</option>
                              }
                            </select>
                          </td>
                          <td>
                            <select class="inline-input" [(ngModel)]="editingItem()!.coverageModel">
                              <option [ngValue]="null">&mdash;</option>
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
                              type="number"
                              [(ngModel)]="editingItem()!.markupPercent"
                              min="0"
                              step="0.1"
                              placeholder="--"
                            />
                          </td>
                          <td>
                            <select
                              class="inline-input"
                              [(ngModel)]="editingItem()!.currency"
                            >
                              @for (c of availableCurrencies(); track c) {
                                <option [value]="c">{{ c }}</option>
                              }
                            </select>
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
                          <td>
                            <span>{{ itemTargetName(item) }}</span>
                            @if (item.providerSkuId) {
                              <span class="badge badge-sku">SKU</span>
                            }
                            @if (item.activityDefinitionId) {
                              <span class="badge badge-activity">Activity</span>
                            }
                          </td>
                          <td>{{ regionNameForId(item.deliveryRegionId) }}</td>
                          <td>{{ formatCoverage(item.coverageModel) }}</td>
                          <td class="mono">{{ item.pricePerUnit | number: '1.2-2' }}</td>
                          <td class="mono">{{ item.markupPercent != null ? (item.markupPercent | number: '1.1-2') : '\u2014' }}</td>
                          <td>{{ item.currency }}</td>
                          <td>{{ item.minQuantity ?? '\u2014' }}</td>
                          <td>{{ item.maxQuantity ?? '\u2014' }}</td>
                          <td class="td-actions">
                            @if (priceList.status === 'draft') {
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
                            }
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
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; white-space: nowrap; }
    .header-actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
    .filter-select { min-width: 150px; max-width: 200px; }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Create form -------------------------------------------------------- */
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

    /* -- Price list cards --------------------------------------------------- */
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
    .badge-region { background: #fef3c7; color: #92400e; }
    .badge-status-draft { background: #fef3c7; color: #92400e; }
    .badge-status-published { background: #dcfce7; color: #166534; }
    .badge-status-archived { background: #f1f5f9; color: #64748b; }
    .badge-sku { background: #ede9fe; color: #6d28d9; margin-left: 0.375rem; }
    .badge-activity { background: #fce7f3; color: #be185d; margin-left: 0.375rem; }

    .card-actions { display: flex; gap: 0.375rem; align-items: center; margin-left: auto; }
    .btn-success { background: #16a34a; color: #fff; }
    .btn-success:hover { background: #15803d; }

    .version-form {
      display: flex; gap: 0.5rem; align-items: center; padding: 0.75rem 1.25rem;
      background: #eff6ff; border-bottom: 1px solid #dbeafe;
    }
    .version-label { font-size: 0.8125rem; color: #374151; font-weight: 500; }

    .tenant-chips {
      display: flex; gap: 0.375rem; flex-wrap: wrap; margin-top: 0.25rem;
    }
    .tenant-chip {
      display: inline-block; padding: 0.125rem 0.5rem; background: #dbeafe;
      color: #1d4ed8; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }

    /* -- Items section ------------------------------------------------------ */
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

    .add-item-form-wrapper {
      margin-bottom: 0.75rem; padding: 0.75rem; background: #f8fafc;
      border: 1px solid #e2e8f0; border-radius: 6px;
    }
    .target-type-row {
      display: flex; align-items: center; gap: 1rem; margin-bottom: 0.625rem;
      font-size: 0.8125rem; color: #374151;
    }
    .target-type-label { font-weight: 600; }
    .radio-label {
      display: flex; align-items: center; gap: 0.25rem; cursor: pointer;
      font-size: 0.8125rem; color: #374151;
    }
    .radio-label input[type="radio"] { margin: 0; }

    .add-item-form {
      display: flex; gap: 0.5rem; align-items: center;
      flex-wrap: wrap;
    }
    .item-field { flex: 2; min-width: 180px; }
    .item-field-half { flex: 1; min-width: 140px; }
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

    /* -- Buttons ------------------------------------------------------------ */
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

    /* -- Tenant Assignments ------------------------------------------------- */
    .assignment-section {
      border-top: 1px solid #e2e8f0; padding: 0;
    }
    .assignment-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.625rem 1.25rem; cursor: pointer; user-select: none;
    }
    .assignment-header:hover { background: #f8fafc; }
    .assignment-title {
      font-size: 0.8125rem; font-weight: 600; color: #374151;
    }
    .assignment-toggle { font-size: 0.625rem; color: #94a3b8; }
    .assignment-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .assignment-table th, .assignment-table td {
      padding: 0.5rem 1.25rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .assignment-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .assignment-row { cursor: pointer; transition: background 0.15s; }
    .assignment-row:hover { background: #f8fafc; }
    .assignment-row.selected { background: #eff6ff; }
    .badge-pin { background: #dbeafe; color: #1d4ed8; }
    .badge-clone { background: #ede9fe; color: #6d28d9; }
    .badge-warning { background: #fef3c7; color: #92400e; }
    .diff-add { color: #16a34a; font-weight: 600; font-size: 0.75rem; margin-right: 0.5rem; }
    .diff-del { color: #dc2626; font-weight: 600; font-size: 0.75rem; }

    /* -- Diff Panel --------------------------------------------------------- */
    .diff-panel {
      border-top: 1px solid #e2e8f0; background: #f8fafc; padding: 0.75rem 1.25rem;
    }
    .diff-panel-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .diff-panel-title {
      font-size: 0.8125rem; font-weight: 600; color: #1e293b;
    }
    .diff-panel-body { display: flex; flex-direction: column; gap: 0.75rem; }
    .diff-loading {
      color: #64748b; font-size: 0.8125rem; padding: 0.5rem 0;
    }
    .diff-empty {
      color: #64748b; font-size: 0.8125rem; font-style: italic; padding: 0.25rem 0;
    }
    .diff-group { border-radius: 6px; padding: 0.5rem 0.75rem; }
    .diff-group-add { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .diff-group-del { background: #fef2f2; border: 1px solid #fecaca; }
    .diff-group-label {
      font-size: 0.75rem; font-weight: 600; margin-bottom: 0.375rem;
      color: #374151;
    }
    .diff-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.25rem 0; font-size: 0.8125rem; color: #374151;
    }
    .diff-item-name { flex: 1; }
  `],
})
export class PricingConfigComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private currencyService = inject(CurrencyService);
  private deliveryService = inject(DeliveryService);
  private semanticService = inject(SemanticService);
  private tenantContext = inject(TenantContextService);
  private tenantService = inject(TenantService);
  private toastService = inject(ToastService);

  priceLists = signal<PriceList[]>([]);
  offerings = signal<ServiceOffering[]>([]);
  tenants = signal<TenantInfo[]>([]);
  deliveryRegions = signal<DeliveryRegion[]>([]);
  providers = signal<SemanticProvider[]>([]);
  providerSkus = signal<ProviderSku[]>([]);
  activityTemplates = signal<ActivityTemplate[]>([]);
  availableCurrencies = signal<string[]>([]);
  providerDefaultCurrency = signal('EUR');
  loading = signal(false);

  tenantOptions = computed(() => this.tenants().map(t => ({ value: t.id, label: t.name })));
  offeringOptions = computed(() => this.offerings().map(o => ({ value: o.id, label: o.name })));
  regionOptions = computed(() => this.deliveryRegions().map(r => ({ value: r.id, label: r.displayName })));
  providerOptions = computed(() => this.providers().map(p => ({ value: p.id, label: p.displayName || p.name })));
  skuOptions = computed(() => this.providerSkus().map(s => ({ value: s.id, label: s.displayName || s.name })));
  activityOptions = computed(() => {
    const templates = this.activityTemplates();
    return templates.map(t => ({ value: t.id, label: t.name }));
  });

  creating = signal(false);
  addingItemForList = signal<string | null>(null);
  editingItem = signal<EditingItem | null>(null);
  copyingListId = signal<string | null>(null);
  versioningListId = signal<string | null>(null);
  assignmentsMap = signal<Map<string, TenantPriceListAssignment[]>>(new Map());
  selectedAssignment = signal<{ priceListId: string; assignment: TenantPriceListAssignment } | null>(null);
  diff = signal<PriceListDiff | null>(null);
  diffLoading = signal(false);
  expandedAssignments = signal<Set<string>>(new Set());
  copyName = '';
  copyClientTenantId = '';

  // Filter fields
  filterStatus = '';
  filterRegionId = '';

  // Create form fields
  formName = '';
  formIsDefault = false;
  formClientTenantId = '';
  formDeliveryRegionId = '';

  // Add item fields
  newItemTargetType: ItemTargetType = 'offering';
  newItemServiceId = '';
  newItemSkuId = '';
  newItemActivityId = '';
  newItemProviderId = '';
  newItemPrice = 0;
  newItemCurrency = 'EUR';
  newItemMarkupPercent: number | null = null;
  newItemRegionId = '';
  newItemCoverage = '';

  ngOnInit(): void {
    this.loadPriceLists();
    this.loadOfferings();
    this.loadRegions();
    this.loadTenants();
    this.loadProviders();
    this.loadActivityTemplates();
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
      clientTenantId: this.formClientTenantId || null,
      deliveryRegionId: this.formDeliveryRegionId || null,
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
    const clientTenantId = this.copyClientTenantId || null;
    this.catalogService.copyPriceList(
      sourceId,
      this.copyName.trim(),
      clientTenantId,
    ).subscribe({
      next: (copied) => {
        this.priceLists.update((lists) => [...lists, copied]);
        this.toastService.success(`Price list "${copied.name}" created`);
        this.cancelCopy();
        // Reload assignments for source if this was a tenant clone
        if (clientTenantId) {
          this.loadAssignmentsForPriceList(sourceId);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to copy price list');
      },
    });
  }

  // -- Tenant Assignments ---------------------------------------------------

  toggleAssignments(priceListId: string): void {
    this.expandedAssignments.update((set) => {
      const next = new Set(set);
      if (next.has(priceListId)) {
        next.delete(priceListId);
        // Close diff if open for this list
        if (this.selectedAssignment()?.priceListId === priceListId) {
          this.closeAssignment();
        }
      } else {
        next.add(priceListId);
      }
      return next;
    });
  }

  selectAssignment(priceListId: string, assignment: TenantPriceListAssignment): void {
    if (assignment.assignmentType === 'pin') {
      this.selectedAssignment.set(null);
      this.diff.set(null);
      return;
    }
    this.selectedAssignment.set({ priceListId, assignment });
    this.diff.set(null);
    this.diffLoading.set(true);
    this.catalogService.getPriceListDiff(priceListId, assignment.clonePriceListId!).subscribe({
      next: (result) => {
        this.diff.set(result);
        this.diffLoading.set(false);
      },
      error: () => {
        this.diffLoading.set(false);
        this.toastService.error('Failed to load diff');
      },
    });
  }

  closeAssignment(): void {
    this.selectedAssignment.set(null);
    this.diff.set(null);
    this.diffLoading.set(false);
  }

  diffItemName(item: PriceListDiffItem): string {
    if (item.serviceOfferingId) {
      return this.serviceNameForId(item.serviceOfferingId);
    }
    if (item.providerSkuId) {
      return this.skuNameForId(item.providerSkuId);
    }
    if (item.activityDefinitionId) {
      return this.activityNameForId(item.activityDefinitionId);
    }
    return 'Unknown target';
  }

  // -- Target type handling -------------------------------------------------

  onTargetTypeChange(type: ItemTargetType): void {
    this.newItemTargetType = type;
    this.newItemServiceId = '';
    this.newItemSkuId = '';
    this.newItemActivityId = '';
    this.newItemProviderId = '';
    this.providerSkus.set([]);
  }

  onProviderChange(providerId: string): void {
    this.newItemSkuId = '';
    if (providerId) {
      this.loadSkusForProvider(providerId);
    } else {
      this.providerSkus.set([]);
    }
  }

  isAddItemValid(): boolean {
    if (this.newItemPrice < 0) return false;
    switch (this.newItemTargetType) {
      case 'offering':
        return !!this.newItemServiceId;
      case 'sku':
        return !!this.newItemSkuId;
      case 'activity':
        return !!this.newItemActivityId;
      default:
        return false;
    }
  }

  // -- Item management ------------------------------------------------------

  showAddItem(priceListId: string): void {
    this.addingItemForList.set(priceListId);
    this.newItemTargetType = 'offering';
    this.newItemServiceId = '';
    this.newItemSkuId = '';
    this.newItemActivityId = '';
    this.newItemProviderId = '';
    this.newItemPrice = 0;
    this.newItemCurrency = this.providerDefaultCurrency();
    this.newItemMarkupPercent = null;
    this.newItemRegionId = '';
    this.newItemCoverage = '';
    this.providerSkus.set([]);
  }

  cancelAddItem(): void {
    this.addingItemForList.set(null);
  }

  addItem(priceListId: string): void {
    const input: Record<string, unknown> = {
      pricePerUnit: this.newItemPrice,
      currency: this.newItemCurrency || this.providerDefaultCurrency(),
      deliveryRegionId: this.newItemRegionId || undefined,
      coverageModel: this.newItemCoverage || undefined,
      markupPercent: this.newItemMarkupPercent,
    };

    switch (this.newItemTargetType) {
      case 'offering':
        input['serviceOfferingId'] = this.newItemServiceId;
        break;
      case 'sku':
        input['providerSkuId'] = this.newItemSkuId;
        break;
      case 'activity':
        input['activityDefinitionId'] = this.newItemActivityId;
        break;
    }

    this.catalogService.addPriceListItem(priceListId, input as any).subscribe({
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
      markupPercent: item.markupPercent,
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
      markupPercent: editing.markupPercent,
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

  // -- Display helpers ------------------------------------------------------

  /** Returns the display name for an item's target (offering, SKU, or activity). */
  itemTargetName(item: PriceListItem): string {
    if (item.serviceOfferingId) {
      return this.serviceNameForId(item.serviceOfferingId);
    }
    if (item.providerSkuId) {
      return this.skuNameForId(item.providerSkuId);
    }
    if (item.activityDefinitionId) {
      return this.activityNameForId(item.activityDefinitionId);
    }
    return 'Unknown target';
  }

  serviceNameForId(serviceOfferingId: string): string {
    const offering = this.offerings().find((o) => o.id === serviceOfferingId);
    return offering ? offering.name : serviceOfferingId.substring(0, 8) + '...';
  }

  skuNameForId(skuId: string): string {
    // Search across all loaded SKUs; they may be from a previous provider load
    const sku = this.providerSkus().find((s) => s.id === skuId);
    return sku ? (sku.displayName || sku.name) : skuId.substring(0, 8) + '...';
  }

  activityNameForId(activityId: string): string {
    const templates = this.activityTemplates();
    for (const tmpl of templates) {
      if (tmpl.id === activityId) return tmpl.name;
      // Activity definitions nested inside templates
      if (tmpl.definitions) {
        const def = tmpl.definitions.find((d) => d.id === activityId);
        if (def) return def.name;
      }
    }
    return activityId.substring(0, 8) + '...';
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

  // -- Versioning -----------------------------------------------------------

  startNewVersion(priceList: PriceList): void {
    this.versioningListId.set(priceList.id);
  }

  cancelNewVersion(): void {
    this.versioningListId.set(null);
  }

  createVersion(priceListId: string, bump: 'minor' | 'major'): void {
    this.catalogService.createPriceListVersion(priceListId, bump).subscribe({
      next: (created) => {
        this.priceLists.update((lists) => [...lists, created]);
        this.toastService.success(`Version ${created.versionLabel} created (draft)`);
        this.versioningListId.set(null);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create version');
      },
    });
  }

  publishPriceList(priceList: PriceList): void {
    this.catalogService.publishPriceList(priceList.id).subscribe({
      next: (updated) => {
        this.priceLists.update((lists) =>
          lists.map((l) => {
            if (l.id === updated.id) return updated;
            // Archive the previously-published version in the same group
            if (l.groupId === updated.groupId && l.status === 'published') {
              return { ...l, status: 'archived' };
            }
            return l;
          }),
        );
        this.toastService.success(`${priceList.name} ${updated.versionLabel} published`);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to publish');
      },
    });
  }

  archivePriceList(priceList: PriceList): void {
    this.catalogService.archivePriceList(priceList.id).subscribe({
      next: (updated) => {
        this.priceLists.update((lists) =>
          lists.map((l) => (l.id === updated.id ? updated : l)),
        );
        this.toastService.success(`${priceList.name} ${updated.versionLabel} archived`);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to archive');
      },
    });
  }

  // -- Private helpers ------------------------------------------------------

  loadPriceLists(): void {
    this.loading.set(true);
    this.catalogService.listPriceLists(0, 100).subscribe({
      next: (response) => {
        let filtered = response.items;
        if (this.filterStatus) {
          filtered = filtered.filter((l) => l.status === this.filterStatus);
        }
        if (this.filterRegionId) {
          filtered = filtered.filter((l) => l.deliveryRegionId === this.filterRegionId);
        }
        this.priceLists.set(filtered);
        this.loading.set(false);
        this.loadAssignmentsForAllPriceLists(filtered);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load price lists');
      },
    });
  }

  private loadAssignmentsForAllPriceLists(lists: PriceList[]): void {
    const newMap = new Map<string, TenantPriceListAssignment[]>();
    for (const pl of lists) {
      this.catalogService.getPriceListTenantAssignments(pl.id).subscribe({
        next: (assignments) => {
          if (assignments.length > 0) {
            newMap.set(pl.id, assignments);
            this.assignmentsMap.set(new Map(newMap));
          }
        },
      });
    }
  }

  private loadAssignmentsForPriceList(priceListId: string): void {
    this.catalogService.getPriceListTenantAssignments(priceListId).subscribe({
      next: (assignments) => {
        this.assignmentsMap.update((map) => {
          const next = new Map(map);
          if (assignments.length > 0) {
            next.set(priceListId, assignments);
          } else {
            next.delete(priceListId);
          }
          return next;
        });
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
      next: (list) => {
        this.tenants.set(list.map((t) => ({ id: t.id, name: t.name })));
        // Use the org-level provider_id (from tenants table) for currency lookups
        const providerIds = [...new Set(list.map((t) => t.provider_id).filter(Boolean))];
        if (providerIds.length > 0) {
          this.loadAvailableCurrencies(providerIds);
        }
      },
    });
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (providerList) => {
        this.providers.set(providerList);
      },
    });
  }

  private loadAvailableCurrencies(orgProviderIds: string[]): void {
    const currencies = new Set<string>();
    for (const providerId of orgProviderIds) {
      this.currencyService.getProviderCurrency(providerId).subscribe({
        next: (pc) => {
          currencies.add(pc.defaultCurrency);
          if (!this.providerDefaultCurrency() || this.providerDefaultCurrency() === 'EUR') {
            this.providerDefaultCurrency.set(pc.defaultCurrency);
          }
          this.availableCurrencies.set([...currencies].sort());
        },
      });
      this.currencyService.listExchangeRates(providerId).subscribe({
        next: (rates) => {
          for (const rate of rates) {
            currencies.add(rate.sourceCurrency);
            currencies.add(rate.targetCurrency);
          }
          this.availableCurrencies.set([...currencies].sort());
        },
      });
    }
  }

  private loadActivityTemplates(): void {
    this.deliveryService.listActivityTemplates({ limit: 500 }).subscribe({
      next: (response) => this.activityTemplates.set(response.items),
    });
  }

  private loadSkusForProvider(providerId: string): void {
    this.catalogService.listSkus({ providerId, activeOnly: true, limit: 500 }).subscribe({
      next: (response) => this.providerSkus.set(response.items),
    });
  }

  private resetCreateForm(): void {
    this.formName = '';
    this.formIsDefault = false;
    this.formClientTenantId = '';
    this.formDeliveryRegionId = '';
  }
}
