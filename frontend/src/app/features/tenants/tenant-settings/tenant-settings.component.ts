/**
 * Overview: Tenant settings page with General, Quotas, Domains, Data Export, Catalogs,
 *     Price Lists, and Tags tabs. Catalog and Price List pins have expandable overlay sections.
 * Architecture: Feature component for tenant configuration (Section 3.2)
 * Dependencies: @angular/core, @angular/router, app/core/services/tenant.service,
 *     app/core/services/catalog.service, app/shared/components/property-table,
 *     app/shared/components/searchable-select
 * Concepts: Multi-tenancy, tenant settings, quota management, property editing, data export,
 *     catalog/price list pins with overlay items and minimum charges
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TenantService } from '@core/services/tenant.service';
import { CatalogService } from '@core/services/catalog.service';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { DeliveryService } from '@core/services/delivery.service';
import { TenantDetail, TenantQuota } from '@core/models/tenant.model';
import { CloudBackend } from '@shared/models/cloud-backend.model';
import { DeliveryRegion } from '@shared/models/delivery.model';
import { TenantTag, TenantTagCreateInput } from '@shared/models/tenant-tag.model';
import { DomainMapping, DomainMappingService } from '@core/services/domain-mapping.service';
import {
  TenantCatalogPin,
  TenantPriceListPin,
  ServiceCatalog,
  ServiceCatalogItem,
  PriceList,
  PriceListItem,
  ServiceOffering,
  ServiceGroup,
  PriceListOverlayItem,
  PriceListOverlayItemCreateInput,
  PinMinimumCharge,
  PinMinimumChargeCreateInput,
  CatalogOverlayItem,
  CatalogOverlayItemCreateInput,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import {
  PropertyTableComponent,
  PropertyField,
  PropertyChangeEvent,
} from '@shared/components/property-table/property-table.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';
import { ComponentService } from '@core/services/component.service';
import { Component as ComponentModel, ComponentGovernance } from '@shared/models/component.model';

type TabName = 'general' | 'quotas' | 'domains' | 'export' | 'catalogs' | 'priceLists' | 'tags' | 'governance';

@Component({
  selector: 'nimbus-tenant-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterLink, LayoutComponent, PropertyTableComponent, SearchableSelectComponent, HasPermissionDirective],
  template: `
    <nimbus-layout>
      <div class="settings-page">
        <h1>Settings: {{ tenant()?.name }}</h1>

        <div class="tabs">
          <button class="tab" [class.active]="activeTab() === 'general'" (click)="setTab('general')">General</button>
          <button class="tab" [class.active]="activeTab() === 'quotas'" (click)="setTab('quotas')">Quotas</button>
          <button class="tab" [class.active]="activeTab() === 'domains'" (click)="setTab('domains')">Domains</button>
          <button class="tab" [class.active]="activeTab() === 'export'" (click)="setTab('export')">Data Export</button>
          <button class="tab" [class.active]="activeTab() === 'catalogs'" (click)="setTab('catalogs')">Catalogs</button>
          <button class="tab" [class.active]="activeTab() === 'priceLists'" (click)="setTab('priceLists')">Price Lists</button>
          <button class="tab" [class.active]="activeTab() === 'tags'" (click)="setTab('tags')">Tags</button>
          <button class="tab" [class.active]="activeTab() === 'governance'" (click)="setTab('governance')">Governance</button>
        </div>

        <div class="tab-content">
          <!-- ── General Tab ───────────────────────────────────────── -->
          @if (activeTab() === 'general') {
            <div class="section">
              <h2>General Information</h2>
              @if (generalData()) {
                <nimbus-property-table
                  [fields]="generalFields()"
                  [data]="generalData()!"
                  [showSave]="true"
                  [saving]="generalSaving()"
                  (save)="onGeneralSave($event)"
                />
              }

              <!-- Cloud Backend Info -->
              <div class="backend-card">
                <h3>Cloud Backend</h3>
                @if (tenantBackend(); as b) {
                  <div class="backend-info">
                    <div class="backend-row">
                      <span class="backend-label">Provider</span>
                      <span class="backend-value">
                        {{ b.providerDisplayName }}
                      </span>
                    </div>
                    <div class="backend-row">
                      <span class="backend-label">Backend</span>
                      <a class="backend-link" [routerLink]="['/backends', b.id]">{{ b.name }}</a>
                    </div>
                    <div class="backend-row">
                      <span class="backend-label">Status</span>
                      <span class="status-pill" [class]="'status-' + b.status">{{ b.status }}</span>
                    </div>
                    <div class="backend-row">
                      <span class="backend-label">Credentials</span>
                      <span>{{ b.hasCredentials ? 'Configured' : 'Not set' }}</span>
                    </div>
                    @if (b.endpointUrl) {
                      <div class="backend-row">
                        <span class="backend-label">Endpoint</span>
                        <span class="backend-value mono">{{ b.endpointUrl }}</span>
                      </div>
                    }
                  </div>
                } @else {
                  <p class="backend-empty">No cloud backend configured. <a routerLink="/backends">Set up a backend</a> to enable infrastructure management.</p>
                }
              </div>

              <div class="danger-zone">
                <h3>Danger Zone</h3>
                <p>Deleting this tenant will soft-delete it and all its data.</p>
                <button class="btn btn-danger" (click)="confirmDelete()">Delete Tenant</button>
              </div>
            </div>
          }

          <!-- ── Quotas Tab ────────────────────────────────────────── -->
          @if (activeTab() === 'quotas') {
            <div class="section">
              <h2>Quota Management</h2>
              @if (quotaData()) {
                <nimbus-property-table
                  [fields]="quotaFields()"
                  [data]="quotaData()!"
                  [showSave]="false"
                  (valueChange)="onQuotaChange($event)"
                />
              }
              @if (!quotas().length) {
                <p class="empty">No quotas configured for this tenant.</p>
              }
            </div>
          }

          <!-- ── Domains Tab ───────────────────────────────────────── -->
          @if (activeTab() === 'domains') {
            <div class="section">
              <h2>Domain Mappings</h2>
              <p class="section-hint">Map email domains to this tenant so users are automatically routed here during login.</p>

              @if (domainError()) {
                <div class="domain-alert">{{ domainError() }}</div>
              }

              @if (showDomainForm()) {
                <div class="domain-form-card">
                  <form [formGroup]="domainForm" (ngSubmit)="onCreateDomain()">
                    <div class="domain-form-row">
                      <input formControlName="domain" type="text" placeholder="example.com" class="domain-input" />
                      <button type="submit" class="btn btn-primary" [disabled]="domainForm.invalid || domainSaving()">
                        {{ domainSaving() ? 'Adding...' : 'Add' }}
                      </button>
                      <button type="button" class="btn btn-secondary" (click)="showDomainForm.set(false)">Cancel</button>
                    </div>
                  </form>
                </div>
              } @else {
                <button class="btn btn-primary" (click)="showDomainForm.set(true)" style="margin-bottom: 1rem;">
                  + Add Domain
                </button>
              }

              @if (domainsLoading()) {
                <p class="empty">Loading...</p>
              } @else if (!domains().length) {
                <p class="empty">No domain mappings configured yet.</p>
              } @else {
                <table class="domain-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Added</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (d of domains(); track d.id) {
                      <tr>
                        <td class="domain-name">{{ d.domain }}</td>
                        <td class="date-col">{{ d.created_at | date: 'mediumDate' }}</td>
                        <td><button class="btn-icon-del" (click)="onDeleteDomain(d)" title="Remove">&#10005;</button></td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            </div>
          }

          <!-- ── Data Export Tab ────────────────────────────────────── -->
          @if (activeTab() === 'export') {
            <div class="section">
              <h2>Data Export</h2>
              <p>Export all tenant data as a ZIP archive.</p>
              <button class="btn btn-primary" (click)="startExport()" [disabled]="exporting()">
                {{ exporting() ? 'Exporting...' : 'Start Export' }}
              </button>
              @if (exportJobId()) {
                <div class="export-status">
                  <p>Export started. Job ID: {{ exportJobId() }}</p>
                  <button class="btn btn-secondary" (click)="downloadExport()">Download</button>
                </div>
              }
            </div>
          }

          <!-- ── Catalogs Tab ──────────────────────────────────────── -->
          @if (activeTab() === 'catalogs') {
            <div class="section">
              <div class="section-header">
                <h2>Pinned Service Catalogs</h2>
                <span class="section-count">{{ catalogPins().length }}</span>
              </div>

              @if (catalogPins().length === 0) {
                <div class="empty-hint">No catalog pinned. Default catalog applies.</div>
              }

              @if (catalogPins().length > 0) {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Catalog</th>
                        <th>Version</th>
                        <th>Status</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Active</th>
                        <th class="th-actions">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (pin of catalogPins(); track pin.id) {
                        <tr class="pin-row-clickable" (click)="toggleCatalogPinExpand(pin.id)">
                          <td class="name-cell">{{ pin.catalog?.name || 'Unknown' }}</td>
                          <td>
                            @if (pin.catalog) {
                              <span class="badge badge-version">v{{ pin.catalog.versionMajor }}.{{ pin.catalog.versionMinor }}</span>
                            }
                          </td>
                          <td>
                            @if (pin.catalog) {
                              <span class="badge" [class.badge-published]="pin.catalog.status === 'published'"
                                    [class.badge-draft]="pin.catalog.status === 'draft'"
                                    [class.badge-archived]="pin.catalog.status === 'archived'">
                                {{ pin.catalog.status }}
                              </span>
                            }
                          </td>
                          <td>{{ pin.effectiveFrom | date: 'mediumDate' }}</td>
                          <td>{{ pin.effectiveTo | date: 'mediumDate' }}</td>
                          <td>
                            <span class="badge" [class.badge-active]="pinStatus(pin) === 'active'"
                                  [class.badge-upcoming]="pinStatus(pin) === 'upcoming'"
                                  [class.badge-expired]="pinStatus(pin) === 'expired'">
                              {{ pinStatus(pin) | titlecase }}
                            </span>
                          </td>
                          <td class="td-actions">
                            <button
                              *nimbusHasPermission="'cmdb:catalog:manage'"
                              class="btn-icon-del"
                              (click)="unpinCatalog(pin); $event.stopPropagation()"
                              title="Unpin catalog"
                            >&times;</button>
                          </td>
                        </tr>
                        @if (expandedCatalogPinId() === pin.id) {
                          <tr class="expand-row">
                            <td colspan="7">
                              <div class="expand-content">
                                <div class="expand-section-header">
                                  <h4>Overlay Items</h4>
                                  <button
                                    *nimbusHasPermission="'cmdb:catalog:manage'"
                                    class="btn btn-primary btn-xs"
                                    (click)="showCatalogOverlayForm(pin.id); $event.stopPropagation()"
                                  >+ Add Overlay</button>
                                </div>
                                @if (pin.overlayItems.length === 0 && catalogOverlayFormPinId() !== pin.id) {
                                  <p class="empty-hint">No overlay items.</p>
                                }
                                @if (pin.overlayItems.length > 0) {
                                  <table class="sub-table">
                                    <thead>
                                      <tr>
                                        <th>Action</th>
                                        <th>Offering / Group</th>
                                        <th>Sort Order</th>
                                        <th></th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      @for (overlay of pin.overlayItems; track overlay.id) {
                                        <tr>
                                          <td>
                                            <span class="badge"
                                              [class.badge-include]="overlay.overlayAction === 'include'"
                                              [class.badge-exclude]="overlay.overlayAction === 'exclude'">
                                              {{ overlay.overlayAction | titlecase }}
                                            </span>
                                          </td>
                                          <td>{{ overlay.serviceOfferingId ? serviceNameForId(overlay.serviceOfferingId) : (overlay.serviceGroupId ? groupNameForId(overlay.serviceGroupId) : 'N/A') }}</td>
                                          <td>{{ overlay.sortOrder }}</td>
                                          <td>
                                            <button class="btn-icon-del" (click)="deleteCatalogOverlay(pin, overlay); $event.stopPropagation()" title="Remove">&times;</button>
                                          </td>
                                        </tr>
                                      }
                                    </tbody>
                                  </table>
                                }

                                @if (catalogOverlayFormPinId() === pin.id) {
                                  <div class="inline-form" (click)="$event.stopPropagation()">
                                    <div class="form-row">
                                      <div class="form-group third">
                                        <label class="form-label">Action *</label>
                                        <select class="form-input" [(ngModel)]="catalogOverlayAction" (ngModelChange)="onCatalogOverlayActionChange()">
                                          <option value="include">Include</option>
                                          <option value="exclude">Exclude</option>
                                        </select>
                                      </div>
                                      @if (catalogOverlayAction === 'exclude') {
                                        <div class="form-group two-thirds">
                                          <label class="form-label">Base Item *</label>
                                          <select class="form-input" [(ngModel)]="catalogOverlayBaseItemId">
                                            <option value="">Select base item...</option>
                                            @for (item of catalogBaseItems(pin); track item.id) {
                                              <option [value]="item.id">{{ catalogBaseItemLabel(item) }}</option>
                                            }
                                          </select>
                                        </div>
                                      }
                                      @if (catalogOverlayAction === 'include') {
                                        <div class="form-group two-thirds">
                                          <label class="form-label">Offering</label>
                                          <select class="form-input" [(ngModel)]="catalogOverlayOfferingId">
                                            <option value="">Select offering...</option>
                                            @for (off of offerings(); track off.id) {
                                              <option [value]="off.id">{{ off.name }}</option>
                                            }
                                          </select>
                                        </div>
                                      }
                                    </div>
                                    @if (catalogOverlayAction === 'include') {
                                      <div class="form-row">
                                        <div class="form-group third">
                                          <label class="form-label">Service Group</label>
                                          <select class="form-input" [(ngModel)]="catalogOverlayGroupId">
                                            <option value="">Select group...</option>
                                            @for (g of serviceGroups(); track g.id) {
                                              <option [value]="g.id">{{ g.displayName || g.name }}</option>
                                            }
                                          </select>
                                        </div>
                                        <div class="form-group third">
                                          <label class="form-label">Sort Order</label>
                                          <input class="form-input" type="number" step="1" [(ngModel)]="catalogOverlaySortOrder" placeholder="0" />
                                        </div>
                                      </div>
                                    }
                                    @if (catalogOverlayAction === 'exclude') {
                                      <div class="form-row">
                                        <div class="form-group third">
                                          <label class="form-label">Sort Order</label>
                                          <input class="form-input" type="number" step="1" [(ngModel)]="catalogOverlaySortOrder" placeholder="0" />
                                        </div>
                                      </div>
                                    }
                                    <div class="form-actions">
                                      <button class="btn btn-secondary btn-sm" (click)="cancelCatalogOverlayForm(); $event.stopPropagation()">Cancel</button>
                                      <button
                                        class="btn btn-primary btn-sm"
                                        [disabled]="!canSaveCatalogOverlay() || catalogOverlaySaving()"
                                        (click)="saveCatalogOverlay(pin); $event.stopPropagation()"
                                      >{{ catalogOverlaySaving() ? 'Saving...' : 'Add Overlay' }}</button>
                                    </div>
                                  </div>
                                }
                              </div>
                            </td>
                          </tr>
                        }
                      }
                    </tbody>
                  </table>
                </div>
              }

              <div *nimbusHasPermission="'cmdb:catalog:manage'" class="pin-action pin-action-dates">
                <nimbus-searchable-select
                  [(ngModel)]="newCatalogId"
                  [options]="availableCatalogOptions()"
                  placeholder="Pin a catalog..."
                />
                <input type="date" class="form-input date-input" [(ngModel)]="newCatalogEffectiveFrom" placeholder="From" />
                <input type="date" class="form-input date-input" [(ngModel)]="newCatalogEffectiveTo" placeholder="To (optional)" />
                <button
                  class="btn btn-primary btn-sm"
                  [disabled]="!newCatalogId || !newCatalogEffectiveFrom"
                  (click)="pinCatalog()"
                >Pin</button>
              </div>
            </div>
          }

          <!-- ── Price Lists Tab ───────────────────────────────────── -->
          @if (activeTab() === 'priceLists') {
            <div class="section">
              <div class="section-header">
                <h2>Pinned Price Lists</h2>
                <span class="section-count">{{ priceListPins().length }}</span>
              </div>

              @if (priceListPins().length === 0) {
                <div class="empty-hint">No price lists pinned. Default price list applies.</div>
              }

              @if (priceListPins().length > 0) {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Price List</th>
                        <th>Version</th>
                        <th>Status</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Active</th>
                        <th class="th-actions">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (pin of priceListPins(); track pin.id) {
                        <tr class="pin-row-clickable" (click)="togglePriceListPinExpand(pin.id)">
                          <td class="name-cell">{{ pin.priceList?.name || 'Unknown' }}</td>
                          <td>
                            @if (pin.priceList) {
                              <span class="badge badge-version">v{{ pin.priceList.versionMajor }}.{{ pin.priceList.versionMinor }}</span>
                            }
                          </td>
                          <td>
                            @if (pin.priceList) {
                              <span class="badge" [class.badge-published]="pin.priceList.status === 'published'"
                                    [class.badge-draft]="pin.priceList.status === 'draft'"
                                    [class.badge-archived]="pin.priceList.status === 'archived'">
                                {{ pin.priceList.status }}
                              </span>
                            }
                          </td>
                          <td>{{ pin.effectiveFrom | date: 'mediumDate' }}</td>
                          <td>{{ pin.effectiveTo | date: 'mediumDate' }}</td>
                          <td>
                            <span class="badge" [class.badge-active]="pinStatus(pin) === 'active'"
                                  [class.badge-upcoming]="pinStatus(pin) === 'upcoming'"
                                  [class.badge-expired]="pinStatus(pin) === 'expired'">
                              {{ pinStatus(pin) | titlecase }}
                            </span>
                          </td>
                          <td class="td-actions">
                            <button
                              *nimbusHasPermission="'cmdb:catalog:manage'"
                              class="btn-icon-del"
                              (click)="unpinPriceList(pin); $event.stopPropagation()"
                              title="Unpin price list"
                            >&times;</button>
                          </td>
                        </tr>
                        @if (expandedPriceListPinId() === pin.id) {
                          <tr class="expand-row">
                            <td colspan="7">
                              <div class="expand-content">
                                <div class="expand-section-header">
                                  <h4>Overlay Items</h4>
                                  <button
                                    *nimbusHasPermission="'cmdb:catalog:manage'"
                                    class="btn btn-primary btn-xs"
                                    (click)="showOverlayForm(pin.id); $event.stopPropagation()"
                                  >+ Add Overlay</button>
                                </div>
                                @if (pin.overlayItems.length === 0 && overlayFormPinId() !== pin.id) {
                                  <p class="empty-hint">No overlay items.</p>
                                }
                                @if (pin.overlayItems.length > 0) {
                                  <table class="sub-table">
                                    <thead>
                                      <tr>
                                        <th>Action</th>
                                        <th>Description</th>
                                        <th>Price</th>
                                        <th>Markup</th>
                                        <th>Discount</th>
                                        <th>Coverage</th>
                                        <th></th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      @for (overlay of pin.overlayItems; track overlay.id) {
                                        <tr>
                                          <td>
                                            <span class="badge"
                                              [class.badge-modify]="overlay.overlayAction === 'modify'"
                                              [class.badge-add]="overlay.overlayAction === 'add'"
                                              [class.badge-exclude]="overlay.overlayAction === 'exclude'">
                                              {{ overlay.overlayAction | titlecase }}
                                            </span>
                                          </td>
                                          <td>{{ overlayDescription(overlay) }}</td>
                                          <td class="mono">{{ overlay.pricePerUnit != null ? (overlay.pricePerUnit | number: '1.2-2') : '—' }} {{ overlay.currency || '' }}</td>
                                          <td class="mono">{{ overlay.markupPercent != null ? (overlay.markupPercent | number: '1.1-1') + '%' : '—' }}</td>
                                          <td class="mono">{{ overlay.discountPercent != null ? (overlay.discountPercent | number: '1.1-1') + '%' : '—' }}</td>
                                          <td>{{ overlay.coverageModel || '—' }}</td>
                                          <td>
                                            <button class="btn-icon-del" (click)="deletePriceListOverlay(pin, overlay); $event.stopPropagation()" title="Remove">&times;</button>
                                          </td>
                                        </tr>
                                      }
                                    </tbody>
                                  </table>
                                }

                                @if (overlayFormPinId() === pin.id) {
                                  <div class="inline-form" (click)="$event.stopPropagation()">
                                    <div class="form-row">
                                      <div class="form-group third">
                                        <label class="form-label">Action *</label>
                                        <select class="form-input" [(ngModel)]="overlayAction" (ngModelChange)="onOverlayActionChange()">
                                          <option value="modify">Modify</option>
                                          <option value="add">Add</option>
                                          <option value="exclude">Exclude</option>
                                        </select>
                                      </div>
                                      @if (overlayAction === 'modify' || overlayAction === 'exclude') {
                                        <div class="form-group two-thirds">
                                          <label class="form-label">Base Item *</label>
                                          <select class="form-input" [(ngModel)]="overlayBaseItemId">
                                            <option value="">Select base item...</option>
                                            @for (item of baseItemsForPin(pin); track item.id) {
                                              <option [value]="item.id">{{ baseItemLabel(item) }}</option>
                                            }
                                          </select>
                                        </div>
                                      }
                                      @if (overlayAction === 'add') {
                                        <div class="form-group two-thirds">
                                          <label class="form-label">Service Offering *</label>
                                          <select class="form-input" [(ngModel)]="overlayOfferingId">
                                            <option value="">Select offering...</option>
                                            @for (off of offerings(); track off.id) {
                                              <option [value]="off.id">{{ off.name }}</option>
                                            }
                                          </select>
                                        </div>
                                      }
                                    </div>
                                    @if (overlayAction !== 'exclude') {
                                      <div class="form-row">
                                        <div class="form-group quarter">
                                          <label class="form-label">Price</label>
                                          <input class="form-input" type="number" step="0.01" [(ngModel)]="overlayPrice" placeholder="0.00" />
                                        </div>
                                        <div class="form-group quarter">
                                          <label class="form-label">Currency</label>
                                          <select class="form-input" [(ngModel)]="overlayCurrency">
                                            <option value="">—</option>
                                            @for (c of currencyCodes; track c) {
                                              <option [value]="c">{{ c }}</option>
                                            }
                                          </select>
                                        </div>
                                        <div class="form-group quarter">
                                          <label class="form-label">Markup %</label>
                                          <input class="form-input" type="number" step="0.1" [(ngModel)]="overlayMarkup" placeholder="0" />
                                        </div>
                                        <div class="form-group quarter">
                                          <label class="form-label">Discount %</label>
                                          <input class="form-input" type="number" step="0.1" [(ngModel)]="overlayDiscount" placeholder="0" />
                                        </div>
                                      </div>
                                      <div class="form-row">
                                        <div class="form-group third">
                                          <label class="form-label">Coverage Model</label>
                                          <select class="form-input" [(ngModel)]="overlayCoverage">
                                            <option value="">—</option>
                                            <option value="business_hours">Business Hours</option>
                                            <option value="extended">Extended</option>
                                            <option value="24x7">24x7</option>
                                          </select>
                                        </div>
                                        <div class="form-group third">
                                          <label class="form-label">Min Qty</label>
                                          <input class="form-input" type="number" step="1" [(ngModel)]="overlayMinQty" placeholder="—" />
                                        </div>
                                        <div class="form-group third">
                                          <label class="form-label">Max Qty</label>
                                          <input class="form-input" type="number" step="1" [(ngModel)]="overlayMaxQty" placeholder="—" />
                                        </div>
                                      </div>
                                    }
                                    <div class="form-actions">
                                      <button class="btn btn-secondary btn-sm" (click)="cancelOverlayForm(); $event.stopPropagation()">Cancel</button>
                                      <button
                                        class="btn btn-primary btn-sm"
                                        [disabled]="!canSaveOverlay() || overlaySaving()"
                                        (click)="saveOverlay(pin); $event.stopPropagation()"
                                      >{{ overlaySaving() ? 'Saving...' : 'Add Overlay' }}</button>
                                    </div>
                                  </div>
                                }

                                <div class="expand-section-header" style="margin-top: 1rem;">
                                  <h4>Minimum Charges</h4>
                                  <button
                                    *nimbusHasPermission="'cmdb:catalog:manage'"
                                    class="btn btn-primary btn-xs"
                                    (click)="showMinChargeForm(pin.id); $event.stopPropagation()"
                                  >+ Add Minimum</button>
                                </div>
                                @if (pin.minimumCharges.length === 0 && minChargeFormPinId() !== pin.id) {
                                  <p class="empty-hint">No minimum charges.</p>
                                }
                                @if (pin.minimumCharges.length > 0) {
                                  <table class="sub-table">
                                    <thead>
                                      <tr>
                                        <th>Category</th>
                                        <th>Amount</th>
                                        <th>Currency</th>
                                        <th>Period</th>
                                        <th>From</th>
                                        <th>To</th>
                                        <th></th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      @for (charge of pin.minimumCharges; track charge.id) {
                                        <tr>
                                          <td>{{ charge.category || '—' }}</td>
                                          <td class="mono">{{ charge.minimumAmount | number: '1.2-2' }}</td>
                                          <td>{{ charge.currency }}</td>
                                          <td>{{ charge.period }}</td>
                                          <td>{{ charge.effectiveFrom | date: 'mediumDate' }}</td>
                                          <td>{{ charge.effectiveTo ? (charge.effectiveTo | date: 'mediumDate') : '—' }}</td>
                                          <td>
                                            <button class="btn-icon-del" (click)="deletePinMinimumCharge(pin, charge); $event.stopPropagation()" title="Remove">&times;</button>
                                          </td>
                                        </tr>
                                      }
                                    </tbody>
                                  </table>
                                }

                                @if (minChargeFormPinId() === pin.id) {
                                  <div class="inline-form" (click)="$event.stopPropagation()">
                                    <div class="form-row">
                                      <div class="form-group third">
                                        <label class="form-label">Category</label>
                                        <input class="form-input" type="text" [(ngModel)]="minCategory" placeholder="e.g. compute, storage" />
                                      </div>
                                      <div class="form-group third">
                                        <label class="form-label">Amount *</label>
                                        <input class="form-input" type="number" step="0.01" [(ngModel)]="minAmount" placeholder="0.00" />
                                      </div>
                                      <div class="form-group third">
                                        <label class="form-label">Currency</label>
                                        <select class="form-input" [(ngModel)]="minCurrency">
                                          @for (c of currencyCodes; track c) {
                                            <option [value]="c">{{ c }}</option>
                                          }
                                        </select>
                                      </div>
                                    </div>
                                    <div class="form-row">
                                      <div class="form-group third">
                                        <label class="form-label">Period</label>
                                        <select class="form-input" [(ngModel)]="minPeriod">
                                          <option value="monthly">Monthly</option>
                                          <option value="quarterly">Quarterly</option>
                                          <option value="annually">Annually</option>
                                        </select>
                                      </div>
                                      <div class="form-group third">
                                        <label class="form-label">From *</label>
                                        <input class="form-input date-input" type="date" [(ngModel)]="minEffectiveFrom" />
                                      </div>
                                      <div class="form-group third">
                                        <label class="form-label">To</label>
                                        <input class="form-input date-input" type="date" [(ngModel)]="minEffectiveTo" />
                                      </div>
                                    </div>
                                    <div class="form-actions">
                                      <button class="btn btn-secondary btn-sm" (click)="cancelMinChargeForm(); $event.stopPropagation()">Cancel</button>
                                      <button
                                        class="btn btn-primary btn-sm"
                                        [disabled]="!canSaveMinCharge() || minChargeSaving()"
                                        (click)="saveMinCharge(pin); $event.stopPropagation()"
                                      >{{ minChargeSaving() ? 'Saving...' : 'Add Minimum Charge' }}</button>
                                    </div>
                                  </div>
                                }
                              </div>
                            </td>
                          </tr>
                        }
                      }
                    </tbody>
                  </table>
                </div>
              }

              <div *nimbusHasPermission="'cmdb:catalog:manage'" class="pin-action pin-action-dates">
                <nimbus-searchable-select
                  [(ngModel)]="newPriceListId"
                  [options]="availablePriceListOptions()"
                  placeholder="Pin a price list..."
                />
                <input type="date" class="form-input date-input" [(ngModel)]="newPriceListEffectiveFrom" placeholder="From" />
                <input type="date" class="form-input date-input" [(ngModel)]="newPriceListEffectiveTo" placeholder="To (optional)" />
                <button
                  class="btn btn-primary btn-sm"
                  [disabled]="!newPriceListId || !newPriceListEffectiveFrom"
                  (click)="pinPriceList()"
                >Pin</button>
              </div>
            </div>
          }

          <!-- ── Tags Tab ──────────────────────────────────────────── -->
          @if (activeTab() === 'tags') {
            <div class="section">
              <div class="section-header">
                <h2>Configuration Tags</h2>
                <button
                  *nimbusHasPermission="'settings:tag:create'"
                  class="btn btn-primary btn-sm"
                  (click)="showTagForm()"
                >
                  + Add Tag
                </button>
              </div>
              <p class="section-hint">
                Tags provide typed key-value configuration that blueprints and topologies can reference.
              </p>

              @if (editingTag()) {
                <div class="form-card">
                  <h3 class="form-title">{{ editingTagId() ? 'Edit Tag' : 'New Tag' }}</h3>
                  <div class="form-row">
                    <div class="form-group half">
                      <label class="form-label">Key *</label>
                      <input class="form-input" type="text" [(ngModel)]="tagFormKey"
                        [disabled]="!!editingTagId()" placeholder="e.g. env, region" />
                    </div>
                    <div class="form-group half">
                      <label class="form-label">Display Name</label>
                      <input class="form-input" type="text" [(ngModel)]="tagFormDisplayName"
                        placeholder="Environment" />
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Description</label>
                    <input class="form-input" type="text" [(ngModel)]="tagFormDescription"
                      placeholder="Optional description..." />
                  </div>
                  <div class="form-row">
                    <div class="form-group half">
                      <label class="form-label">Value Type</label>
                      <select class="form-input" [(ngModel)]="tagFormValueType" (ngModelChange)="onTagTypeChange()">
                        <option value="string">String</option>
                        <option value="number">Number</option>
                        <option value="integer">Integer</option>
                        <option value="boolean">Boolean</option>
                      </select>
                    </div>
                    <div class="form-group half">
                      <label class="form-label">Value</label>
                      @if (tagFormValueType === 'boolean') {
                        <select class="form-input" [(ngModel)]="tagFormValue">
                          <option value="">Not set</option>
                          <option value="true">true</option>
                          <option value="false">false</option>
                        </select>
                      } @else if (tagFormValueType === 'number' || tagFormValueType === 'integer') {
                        <input class="form-input" type="number" [(ngModel)]="tagFormValue" placeholder="0" />
                      } @else {
                        <input class="form-input" type="text" [(ngModel)]="tagFormValue" placeholder="Value..." />
                      }
                    </div>
                  </div>
                  <div class="form-group form-group-check">
                    <label class="check-label">
                      <input type="checkbox" [(ngModel)]="tagFormIsSecret" />
                      Secret (mask value in UI)
                    </label>
                  </div>
                  <div class="form-actions">
                    <button class="btn btn-secondary" (click)="cancelTagForm()">Cancel</button>
                    <button class="btn btn-primary" (click)="saveTag()"
                      [disabled]="!tagFormKey || tagSaving()">
                      {{ tagSaving() ? 'Saving...' : (editingTagId() ? 'Update' : 'Create') }}
                    </button>
                  </div>
                </div>
              }

              @if (!tags().length && !editingTag()) {
                <div class="empty-hint">No configuration tags defined yet.</div>
              }

              @if (tags().length > 0) {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Key</th>
                        <th>Display Name</th>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Secret</th>
                        <th class="th-actions">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (tag of tags(); track tag.id) {
                        <tr>
                          <td class="mono">{{ tag.key }}</td>
                          <td>{{ tag.displayName }}</td>
                          <td>{{ getTagSchemaType(tag) }}</td>
                          <td class="mono">{{ tag.isSecret ? '***' : formatTagValue(tag) }}</td>
                          <td>
                            @if (tag.isSecret) {
                              <span class="badge badge-override">Yes</span>
                            }
                          </td>
                          <td class="td-actions">
                            <button
                              *nimbusHasPermission="'settings:tag:update'"
                              class="btn-icon-edit"
                              (click)="editTag(tag)"
                              title="Edit"
                            >&#9998;</button>
                            <button
                              *nimbusHasPermission="'settings:tag:delete'"
                              class="btn-icon-del"
                              (click)="deleteTag(tag)"
                              title="Delete"
                            >&times;</button>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            </div>
          }

          <!-- ── Governance Tab ─────────────────────────────────────── -->
          @if (activeTab() === 'governance') {
            <div class="section">
              <div class="section-header">
                <h2>Component Governance</h2>
                <button
                  *nimbusHasPermission="'component:governance:manage'"
                  class="btn btn-primary btn-sm"
                  (click)="showGovernanceForm.set(true)"
                >
                  + Add Rule
                </button>
              </div>
              <p class="section-hint">
                Control which provider components are available to this tenant, enforce parameter constraints, and limit instance counts.
              </p>

              @if (showGovernanceForm()) {
                <div class="form-card">
                  <h3 class="form-title">{{ editingGovernanceId() ? 'Edit Rule' : 'New Governance Rule' }}</h3>
                  <div class="form-group">
                    <label class="form-label">Component</label>
                    <select class="form-input" [(ngModel)]="govFormComponentId" [disabled]="!!editingGovernanceId()">
                      <option value="">Select a component...</option>
                      @for (c of providerComponents(); track c.id) {
                        <option [value]="c.id">{{ c.displayName }} ({{ c.providerName }})</option>
                      }
                    </select>
                  </div>
                  <div class="form-group form-group-check">
                    <label class="check-label">
                      <input type="checkbox" [(ngModel)]="govFormIsAllowed" />
                      Allow this component for the tenant
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Max Instances (optional)</label>
                    <input class="form-input" type="number" [(ngModel)]="govFormMaxInstances" min="0" placeholder="Unlimited" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Parameter Constraints (JSON, optional)</label>
                    <textarea class="form-input" rows="3" [(ngModel)]="govFormConstraints"
                      placeholder='e.g. {"cpu_count": {"max": 8}}'></textarea>
                  </div>
                  <div class="form-actions">
                    <button class="btn btn-secondary" (click)="cancelGovernanceForm()">Cancel</button>
                    <button class="btn btn-primary" (click)="saveGovernance()"
                      [disabled]="!govFormComponentId || govSaving()">
                      {{ govSaving() ? 'Saving...' : (editingGovernanceId() ? 'Update' : 'Create') }}
                    </button>
                  </div>
                </div>
              }

              @if (!governanceRules().length && !showGovernanceForm()) {
                <div class="empty-hint">No governance rules defined. All published provider components are available by default.</div>
              }

              @if (governanceRules().length > 0) {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Component</th>
                        <th>Status</th>
                        <th>Max Instances</th>
                        <th>Constraints</th>
                        <th class="th-actions">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (rule of governanceRules(); track rule.id) {
                        <tr>
                          <td>{{ getComponentName(rule.componentId) }}</td>
                          <td>
                            <span class="badge" [class.badge-allowed]="rule.isAllowed" [class.badge-denied]="!rule.isAllowed">
                              {{ rule.isAllowed ? 'Allowed' : 'Denied' }}
                            </span>
                          </td>
                          <td>{{ rule.maxInstances ?? 'Unlimited' }}</td>
                          <td class="mono">{{ rule.parameterConstraints ? 'Yes' : '-' }}</td>
                          <td class="td-actions">
                            <button
                              *nimbusHasPermission="'component:governance:manage'"
                              class="btn-icon-edit"
                              (click)="editGovernance(rule)"
                              title="Edit"
                            >&#9998;</button>
                            <button
                              *nimbusHasPermission="'component:governance:manage'"
                              class="btn-icon-del"
                              (click)="deleteGovernance(rule)"
                              title="Delete"
                            >&times;</button>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            </div>
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .settings-page { padding: 0; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; }
    .tabs {
      display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.5rem; gap: 0.25rem;
      flex-wrap: wrap;
    }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; font-family: inherit;
      transition: color 0.15s; white-space: nowrap;
    }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab:hover { color: #3b82f6; }
    .section { margin-bottom: 2rem; }
    .section h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin-bottom: 1rem; }
    .empty { color: #94a3b8; font-size: 0.8125rem; padding: 1rem; }
    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* ── Section header ─────────────────────────────────────────── */
    .section-header {
      display: flex; align-items: center; gap: 0.5rem;
      margin-bottom: 0.75rem; padding-bottom: 0.5rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .section-header h2 { margin: 0; }
    .section-count {
      background: #f1f5f9; color: #64748b; padding: 0.125rem 0.5rem;
      border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }

    /* ── Pin cards ─────────────────────────────────────────────── */
    .pin-card {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.625rem 0; border-bottom: 1px solid #f8fafc;
    }
    .pin-card:last-of-type { border-bottom: none; }
    .pin-info {
      display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
    }
    .pin-name { font-weight: 500; color: #1e293b; font-size: 0.875rem; }
    .pin-action {
      display: flex; gap: 0.5rem; align-items: center; margin-top: 0.75rem;
      padding-top: 0.75rem; border-top: 1px solid #f1f5f9;
    }
    .pin-action nimbus-searchable-select { flex: 1; }
    .pin-action-dates { flex-wrap: wrap; }
    .date-input { width: 140px; flex: 0 0 140px; }

    /* ── Badges ────────────────────────────────────────────────── */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-version { background: #eff6ff; color: #3b82f6; }
    .badge-published { background: #dcfce7; color: #16a34a; }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .badge-override { background: #fef3c7; color: #92400e; }
    .badge-discount { background: #dcfce7; color: #16a34a; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-upcoming { background: #eff6ff; color: #3b82f6; }
    .badge-expired { background: #f1f5f9; color: #64748b; }
    .badge-allowed { background: #dcfce7; color: #166534; }
    .badge-denied { background: #fef2f2; color: #dc2626; }

    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
      color: #374151;
    }
    .text-muted { color: #94a3b8; font-size: 0.8125rem; }
    .name-cell { font-weight: 500; color: #1e293b; }

    /* ── Forms ──────────────────────────────────────────────────── */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;
    }
    .form-title {
      font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
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

    /* ── Table ──────────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .data-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .data-table th, .data-table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .data-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .data-table tbody tr:hover { background: #f8fafc; }
    .th-actions, .td-actions { width: 60px; text-align: right; }

    /* ── Danger zone ────────────────────────────────────────────── */
    /* ── Cloud Backend Card ──────────────────────────────────── */
    .backend-card {
      margin-top: 1.5rem; padding: 1.25rem; border: 1px solid #e2e8f0;
      border-radius: 8px; background: #fff;
    }
    .backend-card h3 { font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem; }
    .backend-info { display: flex; flex-direction: column; gap: 8px; }
    .backend-row { display: flex; align-items: center; gap: 12px; font-size: 0.8125rem; }
    .backend-label { font-weight: 600; color: #64748b; min-width: 90px; }
    .backend-value { color: #374151; }
    .backend-link { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .backend-link:hover { text-decoration: underline; }
    .backend-empty { font-size: 0.8125rem; color: #94a3b8; margin: 0; }
    .backend-empty a { color: #3b82f6; text-decoration: none; }
    .backend-empty a:hover { text-decoration: underline; }
    .mono { font-family: monospace; font-size: 0.75rem; }
    .status-pill {
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
    }
    .status-active { background: #d1fae5; color: #065f46; }
    .status-disabled { background: #f1f5f9; color: #64748b; }
    .status-error { background: #fee2e2; color: #991b1b; }

    .danger-zone {
      margin-top: 2rem; padding: 1.25rem; border: 1px solid #fecaca;
      border-radius: 8px; background: #fff;
    }
    .danger-zone h3 { color: #dc2626; font-size: 0.9375rem; font-weight: 600; margin-bottom: 0.5rem; }
    .danger-zone p { font-size: 0.8125rem; color: #64748b; margin-bottom: 0.75rem; }

    /* ── Buttons ────────────────────────────────────────────────── */
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: background 0.15s; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover:not(:disabled) { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; border: none; }
    .btn-danger:hover { background: #b91c1c; }
    .export-status {
      margin-top: 1rem; padding: 0.75rem 1rem; background: #f0fdf4;
      border: 1px solid #bbf7d0; border-radius: 8px;
    }
    .export-status p { font-size: 0.8125rem; margin-bottom: 0.5rem; color: #166534; }
    .section-hint { font-size: 0.8125rem; color: #64748b; margin: -0.5rem 0 1rem; }
    .domain-alert {
      padding: 0.625rem 0.875rem; margin-bottom: 0.75rem; font-size: 0.8125rem;
      color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
    }
    .domain-form-card { margin-bottom: 1rem; }
    .domain-form-row { display: flex; gap: 0.5rem; align-items: center; }
    .domain-input {
      flex: 1; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit;
    }
    .domain-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .domain-table { width: 100%; border-collapse: collapse; }
    .domain-table th, .domain-table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 0.8125rem;
    }
    .domain-table th { color: #64748b; font-weight: 600; text-transform: uppercase; font-size: 0.6875rem; letter-spacing: 0.05em; }
    .domain-name { font-weight: 500; color: #1e293b; }
    .date-col { color: #64748b; }
    .btn-icon-del {
      padding: 0.2rem 0.4rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; cursor: pointer; font-size: 0.75rem; color: #dc2626;
    }
    .btn-icon-del:hover { background: #fef2f2; border-color: #fecaca; }
    .btn-icon-edit {
      padding: 0.2rem 0.4rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; cursor: pointer; font-size: 0.75rem; color: #3b82f6;
      margin-right: 4px;
    }
    .btn-icon-edit:hover { background: #eff6ff; border-color: #bfdbfe; }
    .check-label {
      font-size: 0.85rem; color: #475569; display: flex; align-items: center; gap: 6px; white-space: nowrap;
    }
    .form-group-check { display: flex; align-items: center; margin-bottom: 14px; }

    /* ── Expandable pin overlay sections ─────────────────────────── */
    .expand-row td { padding: 0; border-bottom: 1px solid #e2e8f0; }
    .expand-content { padding: 1rem 1.5rem; background: #f8fafc; }
    .expand-content h4 { font-size: 0.8125rem; font-weight: 600; color: #475569; margin: 0 0 0.5rem; }
    .sub-table { width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-bottom: 0.75rem; }
    .sub-table th, .sub-table td { padding: 0.375rem 0.5rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
    .sub-table th { color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.625rem; letter-spacing: 0.05em; }
    .badge-modify { background: #fef3c7; color: #92400e; }
    .badge-add { background: #dcfce7; color: #16a34a; }
    .badge-exclude { background: #fee2e2; color: #dc2626; }
    .badge-include { background: #dcfce7; color: #16a34a; }
    .pin-row-clickable { cursor: pointer; }
    .pin-row-clickable:hover { background: #eff6ff; }

    /* ── Inline overlay/minimum forms ──────────────────────────────── */
    .expand-section-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 0.5rem;
    }
    .expand-section-header h4 { margin: 0; }
    .btn-xs { padding: 0.25rem 0.5rem; font-size: 0.6875rem; }
    .inline-form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 0.75rem; margin: 0.5rem 0 0.75rem;
    }
    .inline-form .form-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
    .inline-form .form-group { margin-bottom: 0; }
    .inline-form .form-group.third { flex: 1; }
    .inline-form .form-group.two-thirds { flex: 2; }
    .inline-form .form-group.quarter { flex: 1; }
    .inline-form .form-label { font-size: 0.6875rem; margin-bottom: 0.25rem; }
    .inline-form .form-input { font-size: 0.75rem; padding: 0.375rem 0.5rem; }
    .inline-form .form-actions { margin-top: 0.5rem; }
  `],
})
export class TenantSettingsComponent implements OnInit {
  private tenantService = inject(TenantService);
  private catalogService = inject(CatalogService);
  private domainMappingService = inject(DomainMappingService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private backendService = inject(CloudBackendService);
  private deliveryService = inject(DeliveryService);
  private componentService = inject(ComponentService);
  private datePipe = new DatePipe('en-US');

  tenant = signal<TenantDetail | null>(null);
  quotas = signal<TenantQuota[]>([]);
  activeTab = signal<TabName>('general');
  generalSaving = signal(false);

  // Cloud backend & regions for General tab
  tenantBackend = signal<CloudBackend | null>(null);
  deliveryRegions = signal<DeliveryRegion[]>([]);
  exporting = signal(false);
  exportJobId = signal('');

  // Domain mappings
  domains = signal<DomainMapping[]>([]);
  domainsLoading = signal(false);
  domainSaving = signal(false);
  domainError = signal<string | null>(null);
  showDomainForm = signal(false);
  domainForm = new FormGroup({
    domain: new FormControl('', [
      Validators.required,
      Validators.pattern(/^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*\.[a-zA-Z]{2,}$/),
    ]),
  });

  // Catalogs tab
  catalogPins = signal<TenantCatalogPin[]>([]);
  publishedCatalogs = signal<ServiceCatalog[]>([]);
  newCatalogId = '';
  newCatalogEffectiveFrom = '';
  newCatalogEffectiveTo = '';
  private catalogsLoaded = false;

  availableCatalogOptions = computed(() => {
    const pinnedIds = new Set(this.catalogPins().map(p => p.catalogId));
    return this.publishedCatalogs()
      .filter(c => !pinnedIds.has(c.id))
      .map(c => ({
        value: c.id,
        label: `${c.name} (v${c.versionMajor}.${c.versionMinor})`,
      }));
  });

  // Price Lists tab
  priceListPins = signal<TenantPriceListPin[]>([]);
  publishedPriceLists = signal<PriceList[]>([]);
  newPriceListId = '';
  newPriceListEffectiveFrom = '';
  newPriceListEffectiveTo = '';
  private priceListsLoaded = false;

  availablePriceListOptions = computed(() => {
    const pinnedIds = new Set(this.priceListPins().map(p => p.priceListId));
    return this.publishedPriceLists()
      .filter(pl => !pinnedIds.has(pl.id))
      .map(pl => ({
        value: pl.id,
        label: `${pl.name} (v${pl.versionMajor}.${pl.versionMinor})`,
      }));
  });

  // Expandable pin overlays
  offerings = signal<ServiceOffering[]>([]);
  expandedPriceListPinId = signal<string | null>(null);
  expandedCatalogPinId = signal<string | null>(null);
  private offeringsLoaded = false;

  // Catalog overlay create form state
  catalogOverlayFormPinId = signal<string | null>(null);
  catalogOverlaySaving = signal(false);
  catalogOverlayAction = 'include';
  catalogOverlayBaseItemId = '';
  catalogOverlayOfferingId = '';
  catalogOverlayGroupId = '';
  catalogOverlaySortOrder: number | null = null;
  serviceGroups = signal<ServiceGroup[]>([]);
  private serviceGroupsLoaded = false;

  // Overlay create form state
  overlayFormPinId = signal<string | null>(null);
  overlaySaving = signal(false);
  overlayAction = 'modify';
  overlayBaseItemId = '';
  overlayOfferingId = '';
  overlayPrice: number | null = null;
  overlayCurrency = '';
  overlayMarkup: number | null = null;
  overlayDiscount: number | null = null;
  overlayCoverage = '';
  overlayMinQty: number | null = null;
  overlayMaxQty: number | null = null;

  // Minimum charge create form state
  minChargeFormPinId = signal<string | null>(null);
  minChargeSaving = signal(false);
  minCategory = '';
  minAmount: number | null = null;
  minCurrency = 'EUR';
  minPeriod = 'monthly';
  minEffectiveFrom = '';
  minEffectiveTo = '';

  readonly currencyCodes = [
    'EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CNY', 'AUD', 'CAD',
    'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
    'BRL', 'INR', 'KRW', 'MXN', 'SGD', 'HKD', 'NZD', 'ZAR',
  ];

  // Tags tab
  tags = signal<TenantTag[]>([]);
  editingTag = signal(false);
  editingTagId = signal<string | null>(null);
  tagSaving = signal(false);
  tagFormKey = '';
  tagFormDisplayName = '';
  tagFormDescription = '';
  tagFormValueType = 'string';
  tagFormValue: string = '';
  tagFormIsSecret = false;
  private tagsLoaded = false;

  // Governance tab
  governanceRules = signal<ComponentGovernance[]>([]);
  providerComponents = signal<ComponentModel[]>([]);
  showGovernanceForm = signal(false);
  editingGovernanceId = signal<string | null>(null);
  govSaving = signal(false);
  govFormComponentId = '';
  govFormIsAllowed = true;
  govFormMaxInstances: number | null = null;
  govFormConstraints = '';
  private governanceLoaded = false;
  private componentNameMap = new Map<string, string>();

  private tenantId = '';

  private readonly CURRENCY_OPTIONS = [
    { label: '(Inherit from provider)', value: '' },
    ...['EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CNY', 'AUD', 'CAD',
      'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
      'BRL', 'INR', 'KRW', 'MXN', 'SGD', 'HKD', 'NZD', 'ZAR',
    ].map(c => ({ label: c, value: c })),
  ];

  regionOptions = computed(() => {
    const regions = this.deliveryRegions();
    return [
      { label: '(None)', value: '' },
      ...regions.map(r => ({
        label: `${r.displayName} (${r.code})`,
        value: r.id,
      })),
    ];
  });

  generalFields = computed<PropertyField[]>(() => {
    return [
      { key: 'name', label: 'Name', controlType: 'text', required: true, placeholder: 'Tenant name' },
      { key: 'contact_email', label: 'Contact Email', controlType: 'email', placeholder: 'contact@example.com' },
      { key: 'description', label: 'Description', controlType: 'textarea', placeholder: 'Optional description' },
      {
        key: 'invoice_currency',
        label: 'Invoice Currency',
        controlType: 'select',
        options: this.CURRENCY_OPTIONS,
        hint: 'Leave empty to inherit from provider default',
      },
      {
        key: 'primary_region_id',
        label: 'Primary Region',
        controlType: 'select',
        options: this.regionOptions(),
        hint: 'Regions are managed in Settings > Delivery Regions',
      },
      { key: 'level', label: 'Level', controlType: 'readonly' },
      { key: 'created_at', label: 'Created', controlType: 'readonly' },
    ];
  });

  generalData = computed<Record<string, unknown> | null>(() => {
    const t = this.tenant();
    if (!t) return null;
    return {
      name: t.name,
      contact_email: t.contact_email ?? '',
      description: t.description ?? '',
      invoice_currency: t.invoice_currency ?? '',
      primary_region_id: t.primary_region_id ?? '',
      level: this.getLevelLabel(t.level),
      created_at: this.datePipe.transform(t.created_at, 'medium') ?? t.created_at,
    };
  });

  quotaFields = computed<PropertyField[]>(() => {
    return this.quotas().map((q) => {
      const label = this.formatQuotaLabel(q.quota_type);
      const suffix = this.getQuotaSuffix(q.quota_type);
      return {
        key: q.quota_type,
        label,
        controlType: 'number' as const,
        min: 0,
        suffix,
        hint: `Currently using ${q.current_usage} of ${q.limit_value}`,
        extras: [{
          key: 'enforcement',
          label: 'Enforcement',
          controlType: 'select' as const,
          options: [
            { label: 'Hard', value: 'hard' },
            { label: 'Soft', value: 'soft' },
          ],
          width: '100px',
        }],
      };
    });
  });

  quotaData = computed<Record<string, unknown> | null>(() => {
    const qs = this.quotas();
    if (!qs.length) return null;
    const data: Record<string, unknown> = {};
    for (const q of qs) {
      data[q.quota_type] = q.limit_value;
      data[`${q.quota_type}__enforcement`] = q.enforcement;
    }
    return data;
  });

  ngOnInit(): void {
    this.tenantId = this.route.snapshot.params['id'];

    const tabParam = this.route.snapshot.queryParams['tab'] as TabName | undefined;
    const validTabs: TabName[] = ['general', 'quotas', 'domains', 'export', 'catalogs', 'priceLists', 'tags', 'governance'];
    if (tabParam && validTabs.includes(tabParam)) {
      this.activeTab.set(tabParam);
    }

    this.loadTenant();
    this.loadStats();
    this.loadTenantBackend();
    this.loadDeliveryRegions();

    // Load data for the initially active tab if needed
    this.ensureTabDataLoaded(this.activeTab());
  }

  setTab(tab: TabName): void {
    this.activeTab.set(tab);
    this.ensureTabDataLoaded(tab);
  }

  // ── General tab ─────────────────────────────────────────────────

  onGeneralSave(data: Record<string, unknown>): void {
    this.generalSaving.set(true);
    const invoiceCurrency = (data['invoice_currency'] as string) || null;
    const primaryRegionId = (data['primary_region_id'] as string) || null;
    this.tenantService.updateTenant(this.tenantId, {
      name: data['name'] as string || undefined,
      contact_email: (data['contact_email'] as string) || null,
      description: (data['description'] as string) || null,
      invoice_currency: invoiceCurrency,
      primary_region_id: primaryRegionId,
    }).subscribe({
      next: (updated) => {
        this.tenant.update((t) => t ? { ...t, name: updated.name, contact_email: updated.contact_email, description: updated.description, invoice_currency: updated.invoice_currency, primary_region_id: updated.primary_region_id } : t);
        this.generalSaving.set(false);
        this.toastService.success('Settings saved');
      },
      error: (err) => {
        this.generalSaving.set(false);
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to save settings');
      },
    });
  }

  // ── Quotas tab ──────────────────────────────────────────────────

  onQuotaChange(event: PropertyChangeEvent): void {
    const quotaType = event.key;
    if (event.extraKey === 'enforcement') {
      this.tenantService.updateQuota(this.tenantId, quotaType, {
        enforcement: event.value as string,
      }).subscribe({
        next: (updated) => {
          this.updateQuotaInList(updated);
          this.toastService.success('Quota updated');
        },
        error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to update quota'),
      });
    } else {
      const numValue = typeof event.value === 'number' ? event.value : Number(event.value);
      if (isNaN(numValue)) return;
      this.tenantService.updateQuota(this.tenantId, quotaType, {
        limit_value: numValue,
      }).subscribe({
        next: (updated) => {
          this.updateQuotaInList(updated);
          this.toastService.success('Quota updated');
        },
        error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to update quota'),
      });
    }
  }

  // ── Export tab ──────────────────────────────────────────────────

  startExport(): void {
    this.exporting.set(true);
    this.tenantService.startExport(this.tenantId).subscribe({
      next: (res) => {
        this.exportJobId.set(res.job_id);
        this.exporting.set(false);
        this.toastService.success('Export started');
      },
      error: (err) => {
        this.exporting.set(false);
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to start export');
      },
    });
  }

  downloadExport(): void {
    this.tenantService.getExportDownload(this.tenantId, this.exportJobId()).subscribe({
      next: (res) => window.open(res.download_url, '_blank'),
    });
  }

  async confirmDelete(): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Tenant',
      message: `Are you sure you want to delete "${this.tenant()?.name}"? This action will soft-delete the tenant and all its data.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.tenantService.deleteTenant(this.tenantId).subscribe({
      next: () => {
        this.toastService.success('Tenant deleted');
        this.router.navigate(['/tenants']);
      },
      error: (err) => this.toastService.error(err.error?.detail?.error?.message || 'Failed to delete tenant'),
    });
  }

  // ── Domain mapping methods ──────────────────────────────────────

  loadDomains(): void {
    this.domainsLoading.set(true);
    this.domainMappingService.listForTenant(this.tenantId).subscribe({
      next: (data) => { this.domains.set(data); this.domainsLoading.set(false); },
      error: () => { this.domainError.set('Failed to load domain mappings.'); this.domainsLoading.set(false); },
    });
  }

  onCreateDomain(): void {
    if (this.domainForm.invalid) return;
    this.domainSaving.set(true);
    this.domainError.set(null);
    this.domainMappingService.createForTenant(this.tenantId, { domain: this.domainForm.value.domain! }).subscribe({
      next: () => {
        this.domainSaving.set(false);
        this.showDomainForm.set(false);
        this.domainForm.reset();
        this.loadDomains();
        this.toastService.success('Domain added');
      },
      error: (err) => {
        this.domainSaving.set(false);
        this.domainError.set(err.error?.error?.message ?? 'Failed to add domain.');
      },
    });
  }

  onDeleteDomain(d: DomainMapping): void {
    this.domainError.set(null);
    this.domainMappingService.deleteForTenant(this.tenantId, d.id).subscribe({
      next: () => { this.loadDomains(); this.toastService.success('Domain removed'); },
      error: (err) => this.domainError.set(err.error?.error?.message ?? 'Failed to remove domain.'),
    });
  }

  // ── Catalogs tab ────────────────────────────────────────────────

  pinCatalog(): void {
    if (!this.newCatalogId || !this.newCatalogEffectiveFrom) return;
    this.catalogService.pinTenantToCatalog(
      this.tenantId,
      this.newCatalogId,
      this.newCatalogEffectiveFrom,
      this.newCatalogEffectiveTo || undefined,
    ).subscribe({
      next: (pin) => {
        this.catalogPins.update(pins => [...pins, pin]);
        this.newCatalogId = '';
        this.newCatalogEffectiveFrom = '';
        this.newCatalogEffectiveTo = '';
        this.toastService.success('Catalog pinned');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to pin catalog'),
    });
  }

  unpinCatalog(pin: TenantCatalogPin): void {
    this.catalogService.unpinTenantFromCatalog(this.tenantId, pin.catalogId).subscribe({
      next: () => {
        this.catalogPins.update(pins => pins.filter(p => p.id !== pin.id));
        this.toastService.success('Catalog unpinned');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to unpin catalog'),
    });
  }

  // ── Price Lists tab ─────────────────────────────────────────────

  pinPriceList(): void {
    if (!this.newPriceListId || !this.newPriceListEffectiveFrom) return;
    this.catalogService.pinTenantToPriceList(
      this.tenantId,
      this.newPriceListId,
      this.newPriceListEffectiveFrom,
      this.newPriceListEffectiveTo || undefined,
    ).subscribe({
      next: (pin) => {
        this.priceListPins.update(pins => [...pins, pin]);
        this.newPriceListId = '';
        this.newPriceListEffectiveFrom = '';
        this.newPriceListEffectiveTo = '';
        this.toastService.success('Price list pinned');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to pin price list'),
    });
  }

  unpinPriceList(pin: TenantPriceListPin): void {
    this.catalogService.unpinTenantFromPriceList(this.tenantId, pin.priceListId).subscribe({
      next: () => {
        this.priceListPins.update(pins => pins.filter(p => p.id !== pin.id));
        this.toastService.success('Price list unpinned');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to unpin price list'),
    });
  }

  // ── Expandable pin overlays ────────────────────────────────────

  togglePriceListPinExpand(pinId: string): void {
    this.expandedPriceListPinId.update(id => id === pinId ? null : pinId);
  }

  deletePriceListOverlay(pin: TenantPriceListPin, overlay: PriceListOverlayItem): void {
    this.catalogService.deletePriceListOverlay(this.tenantId, overlay.id).subscribe({
      next: () => {
        this.priceListPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, overlayItems: p.overlayItems.filter(o => o.id !== overlay.id) } : p
        ));
        this.toastService.success('Overlay item removed');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to remove overlay'),
    });
  }

  deletePinMinimumCharge(pin: TenantPriceListPin, charge: PinMinimumCharge): void {
    this.catalogService.deletePinMinimumCharge(this.tenantId, charge.id).subscribe({
      next: () => {
        this.priceListPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, minimumCharges: p.minimumCharges.filter(c => c.id !== charge.id) } : p
        ));
        this.toastService.success('Minimum charge removed');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to remove minimum charge'),
    });
  }

  // ── Overlay create form ────────────────────────────────────────

  showOverlayForm(pinId: string): void {
    this.overlayFormPinId.set(pinId);
    this.resetOverlayForm();
  }

  cancelOverlayForm(): void {
    this.overlayFormPinId.set(null);
  }

  onOverlayActionChange(): void {
    this.overlayBaseItemId = '';
    this.overlayOfferingId = '';
  }

  canSaveOverlay(): boolean {
    if (this.overlayAction === 'modify' || this.overlayAction === 'exclude') {
      return !!this.overlayBaseItemId;
    }
    if (this.overlayAction === 'add') {
      return !!this.overlayOfferingId;
    }
    return false;
  }

  baseItemsForPin(pin: TenantPriceListPin): PriceListItem[] {
    return pin.priceList?.items ?? [];
  }

  baseItemLabel(item: PriceListItem): string {
    if (item.serviceOfferingId) {
      const name = this.serviceNameForId(item.serviceOfferingId);
      return `${name} — ${item.pricePerUnit ?? '?'} ${item.currency ?? ''}`;
    }
    if (item.providerSkuId) return `SKU: ${item.providerSkuId.substring(0, 8)}...`;
    if (item.activityDefinitionId) return `Activity: ${item.activityDefinitionId.substring(0, 8)}...`;
    return item.id.substring(0, 12);
  }

  overlayDescription(overlay: PriceListOverlayItem): string {
    if (overlay.serviceOfferingId) return this.serviceNameForId(overlay.serviceOfferingId);
    if (overlay.providerSkuId) return `SKU: ${overlay.providerSkuId.substring(0, 8)}...`;
    if (overlay.activityDefinitionId) return `Activity: ${overlay.activityDefinitionId.substring(0, 8)}...`;
    if (overlay.baseItemId) return `Base: ${overlay.baseItemId.substring(0, 8)}...`;
    return 'N/A';
  }

  saveOverlay(pin: TenantPriceListPin): void {
    this.overlaySaving.set(true);
    const input: PriceListOverlayItemCreateInput = {
      overlayAction: this.overlayAction,
    };
    if (this.overlayAction === 'modify' || this.overlayAction === 'exclude') {
      input.baseItemId = this.overlayBaseItemId;
    }
    if (this.overlayAction === 'add') {
      input.serviceOfferingId = this.overlayOfferingId;
    }
    if (this.overlayAction !== 'exclude') {
      if (this.overlayPrice != null) input.pricePerUnit = this.overlayPrice;
      if (this.overlayCurrency) input.currency = this.overlayCurrency;
      if (this.overlayMarkup != null) input.markupPercent = this.overlayMarkup;
      if (this.overlayDiscount != null) input.discountPercent = this.overlayDiscount;
      if (this.overlayCoverage) input.coverageModel = this.overlayCoverage;
      if (this.overlayMinQty != null) input.minQuantity = this.overlayMinQty;
      if (this.overlayMaxQty != null) input.maxQuantity = this.overlayMaxQty;
    }
    this.catalogService.createPriceListOverlay(this.tenantId, pin.id, input).subscribe({
      next: (created) => {
        this.priceListPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, overlayItems: [...p.overlayItems, created] } : p
        ));
        this.overlaySaving.set(false);
        this.overlayFormPinId.set(null);
        this.toastService.success('Overlay item added');
      },
      error: (err) => {
        this.overlaySaving.set(false);
        this.toastService.error(err.message || 'Failed to create overlay');
      },
    });
  }

  // ── Minimum charge create form ───────────────────────────────

  showMinChargeForm(pinId: string): void {
    this.minChargeFormPinId.set(pinId);
    this.resetMinChargeForm();
  }

  cancelMinChargeForm(): void {
    this.minChargeFormPinId.set(null);
  }

  canSaveMinCharge(): boolean {
    return this.minAmount != null && this.minAmount > 0 && !!this.minEffectiveFrom;
  }

  saveMinCharge(pin: TenantPriceListPin): void {
    if (!this.canSaveMinCharge()) return;
    this.minChargeSaving.set(true);
    const input: PinMinimumChargeCreateInput = {
      minimumAmount: this.minAmount!,
      effectiveFrom: this.minEffectiveFrom,
      currency: this.minCurrency,
      period: this.minPeriod,
    };
    if (this.minCategory) input.category = this.minCategory;
    if (this.minEffectiveTo) input.effectiveTo = this.minEffectiveTo;
    this.catalogService.createPinMinimumCharge(this.tenantId, pin.id, input).subscribe({
      next: (created) => {
        this.priceListPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, minimumCharges: [...p.minimumCharges, created] } : p
        ));
        this.minChargeSaving.set(false);
        this.minChargeFormPinId.set(null);
        this.toastService.success('Minimum charge added');
      },
      error: (err) => {
        this.minChargeSaving.set(false);
        this.toastService.error(err.message || 'Failed to create minimum charge');
      },
    });
  }

  toggleCatalogPinExpand(pinId: string): void {
    this.expandedCatalogPinId.update(id => id === pinId ? null : pinId);
  }

  deleteCatalogOverlay(pin: TenantCatalogPin, overlay: CatalogOverlayItem): void {
    this.catalogService.deleteCatalogOverlay(this.tenantId, overlay.id).subscribe({
      next: () => {
        this.catalogPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, overlayItems: p.overlayItems.filter(o => o.id !== overlay.id) } : p
        ));
        this.toastService.success('Overlay item removed');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to remove overlay'),
    });
  }

  // ── Catalog overlay create form ──────────────────────────────

  showCatalogOverlayForm(pinId: string): void {
    this.catalogOverlayFormPinId.set(pinId);
    this.resetCatalogOverlayForm();
  }

  cancelCatalogOverlayForm(): void {
    this.catalogOverlayFormPinId.set(null);
  }

  onCatalogOverlayActionChange(): void {
    this.catalogOverlayBaseItemId = '';
    this.catalogOverlayOfferingId = '';
    this.catalogOverlayGroupId = '';
  }

  canSaveCatalogOverlay(): boolean {
    if (this.catalogOverlayAction === 'exclude') {
      return !!this.catalogOverlayBaseItemId;
    }
    // include: need at least an offering or a group
    return !!this.catalogOverlayOfferingId || !!this.catalogOverlayGroupId;
  }

  catalogBaseItems(pin: TenantCatalogPin): ServiceCatalogItem[] {
    return pin.catalog?.items ?? [];
  }

  catalogBaseItemLabel(item: ServiceCatalogItem): string {
    if (item.serviceOfferingId) {
      return this.serviceNameForId(item.serviceOfferingId);
    }
    if (item.serviceGroupId) {
      return this.groupNameForId(item.serviceGroupId);
    }
    return item.id.substring(0, 12);
  }

  groupNameForId(groupId: string): string {
    const group = this.serviceGroups().find(g => g.id === groupId);
    return group ? (group.displayName || group.name) : groupId.substring(0, 8) + '...';
  }

  saveCatalogOverlay(pin: TenantCatalogPin): void {
    this.catalogOverlaySaving.set(true);
    const input: CatalogOverlayItemCreateInput = {
      overlayAction: this.catalogOverlayAction,
    };
    if (this.catalogOverlayAction === 'exclude') {
      input.baseItemId = this.catalogOverlayBaseItemId;
    }
    if (this.catalogOverlayAction === 'include') {
      if (this.catalogOverlayOfferingId) input.serviceOfferingId = this.catalogOverlayOfferingId;
      if (this.catalogOverlayGroupId) input.serviceGroupId = this.catalogOverlayGroupId;
    }
    if (this.catalogOverlaySortOrder != null) input.sortOrder = this.catalogOverlaySortOrder;
    this.catalogService.createCatalogOverlay(this.tenantId, pin.id, input).subscribe({
      next: (created) => {
        this.catalogPins.update(pins => pins.map(p =>
          p.id === pin.id ? { ...p, overlayItems: [...p.overlayItems, created] } : p
        ));
        this.catalogOverlaySaving.set(false);
        this.catalogOverlayFormPinId.set(null);
        this.toastService.success('Overlay item added');
      },
      error: (err) => {
        this.catalogOverlaySaving.set(false);
        this.toastService.error(err.message || 'Failed to create overlay');
      },
    });
  }

  serviceNameForId(serviceOfferingId: string): string {
    const offering = this.offerings().find(o => o.id === serviceOfferingId);
    return offering ? offering.name : serviceOfferingId.substring(0, 8) + '...';
  }

  pinStatus(pin: { effectiveFrom: string; effectiveTo: string }): 'active' | 'upcoming' | 'expired' {
    const today = new Date().toISOString().split('T')[0];
    if (pin.effectiveFrom > today) return 'upcoming';
    if (pin.effectiveTo < today) return 'expired';
    return 'active';
  }

  // ── Tags tab ───────────────────────────────────────────────────

  showTagForm(): void {
    this.resetTagForm();
    this.editingTag.set(true);
    this.editingTagId.set(null);
  }

  cancelTagForm(): void {
    this.editingTag.set(false);
    this.resetTagForm();
  }

  editTag(tag: TenantTag): void {
    this.editingTag.set(true);
    this.editingTagId.set(tag.id);
    this.tagFormKey = tag.key;
    this.tagFormDisplayName = tag.displayName;
    this.tagFormDescription = tag.description || '';
    this.tagFormValueType = this.getTagSchemaType(tag);
    this.tagFormValue = tag.value != null ? String(tag.value) : '';
    this.tagFormIsSecret = tag.isSecret;
  }

  saveTag(): void {
    if (!this.tagFormKey) return;
    this.tagSaving.set(true);

    const schema = { type: this.tagFormValueType };
    const value = this.parseTagValue(this.tagFormValue, this.tagFormValueType);

    if (this.editingTagId()) {
      this.tenantService.updateTag(this.tenantId, this.editingTagId()!, {
        displayName: this.tagFormDisplayName || this.tagFormKey,
        description: this.tagFormDescription || null,
        valueSchema: schema,
        value: value,
        isSecret: this.tagFormIsSecret,
      }).subscribe({
        next: (updated) => {
          this.tags.update(tags => tags.map(t => t.id === updated.id ? updated : t));
          this.tagSaving.set(false);
          this.cancelTagForm();
          this.toastService.success('Tag updated');
        },
        error: (err) => {
          this.tagSaving.set(false);
          this.toastService.error(err.message || 'Failed to update tag');
        },
      });
    } else {
      this.tenantService.createTag(this.tenantId, {
        key: this.tagFormKey,
        displayName: this.tagFormDisplayName || this.tagFormKey,
        description: this.tagFormDescription || undefined,
        valueSchema: schema,
        value: value,
        isSecret: this.tagFormIsSecret,
      }).subscribe({
        next: (created) => {
          this.tags.update(tags => [...tags, created]);
          this.tagSaving.set(false);
          this.cancelTagForm();
          this.toastService.success('Tag created');
        },
        error: (err) => {
          this.tagSaving.set(false);
          this.toastService.error(err.message || 'Failed to create tag');
        },
      });
    }
  }

  deleteTag(tag: TenantTag): void {
    this.tenantService.deleteTag(this.tenantId, tag.id).subscribe({
      next: () => {
        this.tags.update(tags => tags.filter(t => t.id !== tag.id));
        this.toastService.success('Tag deleted');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to delete tag'),
    });
  }

  onTagTypeChange(): void {
    this.tagFormValue = '';
  }

  getTagSchemaType(tag: TenantTag): string {
    return (tag.valueSchema as Record<string, string>)?.['type'] || 'string';
  }

  formatTagValue(tag: TenantTag): string {
    if (tag.value == null) return '';
    if (typeof tag.value === 'object') return JSON.stringify(tag.value);
    return String(tag.value);
  }

  // ── Private helpers ─────────────────────────────────────────────

  private ensureTabDataLoaded(tab: TabName): void {
    switch (tab) {
      case 'domains':
        if (!this.domains().length && !this.domainsLoading()) {
          this.loadDomains();
        }
        break;
      case 'catalogs':
        if (!this.catalogsLoaded) {
          this.catalogsLoaded = true;
          this.loadCatalogPins();
          this.loadPublishedCatalogs();
        }
        if (!this.offeringsLoaded) {
          this.offeringsLoaded = true;
          this.loadOfferings();
        }
        if (!this.serviceGroupsLoaded) {
          this.serviceGroupsLoaded = true;
          this.loadServiceGroups();
        }
        break;
      case 'priceLists':
        if (!this.priceListsLoaded) {
          this.priceListsLoaded = true;
          this.loadPriceListPins();
          this.loadPublishedPriceLists();
        }
        if (!this.offeringsLoaded) {
          this.offeringsLoaded = true;
          this.loadOfferings();
        }
        break;
      case 'tags':
        if (!this.tagsLoaded) {
          this.tagsLoaded = true;
          this.loadTags();
        }
        break;
      case 'governance':
        if (!this.governanceLoaded) {
          this.governanceLoaded = true;
          this.loadGovernanceData();
        }
        break;
    }
  }

  private loadTenant(): void {
    this.tenantService.getTenant(this.tenantId).subscribe({
      next: (t) => this.tenant.set(t),
    });
  }

  private loadStats(): void {
    this.tenantService.getTenantStats(this.tenantId).subscribe({
      next: (s) => this.quotas.set(s.quotas),
    });
  }

  private loadTenantBackend(): void {
    this.backendService.getTenantBackend().subscribe({
      next: (b) => this.tenantBackend.set(b),
      error: () => {},
    });
  }

  private loadDeliveryRegions(): void {
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (result) => this.deliveryRegions.set(result.items),
      error: () => {},
    });
  }

  private loadCatalogPins(): void {
    this.catalogService.listCatalogPinsForTenant(this.tenantId).subscribe({
      next: (pins) => this.catalogPins.set(pins),
      error: () => this.catalogPins.set([]),
    });
  }

  private loadPublishedCatalogs(): void {
    this.catalogService.listCatalogs({ status: 'published', limit: 200 }).subscribe({
      next: (result) => this.publishedCatalogs.set(result.items),
    });
  }

  private loadPriceListPins(): void {
    this.catalogService.listTenantPins(this.tenantId).subscribe({
      next: (pins) => this.priceListPins.set(pins),
      error: () => this.priceListPins.set([]),
    });
  }

  private loadPublishedPriceLists(): void {
    this.catalogService.listPriceLists(0, 200).subscribe({
      next: (result) => {
        this.publishedPriceLists.set(result.items.filter(pl => pl.status === 'published'));
      },
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });
  }

  private loadServiceGroups(): void {
    this.catalogService.listGroups(0, 500).subscribe({
      next: (result) => this.serviceGroups.set(result.items),
      error: () => this.serviceGroups.set([]),
    });
  }

  private loadTags(): void {
    this.tenantService.listTags(this.tenantId).subscribe({
      next: (result) => this.tags.set(result.items),
      error: () => this.tags.set([]),
    });
  }

  private resetOverlayForm(): void {
    this.overlayAction = 'modify';
    this.overlayBaseItemId = '';
    this.overlayOfferingId = '';
    this.overlayPrice = null;
    this.overlayCurrency = '';
    this.overlayMarkup = null;
    this.overlayDiscount = null;
    this.overlayCoverage = '';
    this.overlayMinQty = null;
    this.overlayMaxQty = null;
  }

  private resetCatalogOverlayForm(): void {
    this.catalogOverlayAction = 'include';
    this.catalogOverlayBaseItemId = '';
    this.catalogOverlayOfferingId = '';
    this.catalogOverlayGroupId = '';
    this.catalogOverlaySortOrder = null;
  }

  private resetMinChargeForm(): void {
    this.minCategory = '';
    this.minAmount = null;
    this.minCurrency = 'EUR';
    this.minPeriod = 'monthly';
    this.minEffectiveFrom = '';
    this.minEffectiveTo = '';
  }

  private resetTagForm(): void {
    this.tagFormKey = '';
    this.tagFormDisplayName = '';
    this.tagFormDescription = '';
    this.tagFormValueType = 'string';
    this.tagFormValue = '';
    this.tagFormIsSecret = false;
  }

  private parseTagValue(raw: string, type: string): unknown {
    if (!raw && raw !== '0') return null;
    switch (type) {
      case 'number': return parseFloat(raw);
      case 'integer': return parseInt(raw, 10);
      case 'boolean': return raw === 'true';
      default: return raw;
    }
  }

  private getLevelLabel(level: number): string {
    return ['Provider', 'Tenant', 'Sub-tenant'][level] ?? `Level ${level}`;
  }

  private formatQuotaLabel(quotaType: string): string {
    return quotaType.replace(/_/g, ' ').replace(/\bmax\b/i, 'Max').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  private getQuotaSuffix(quotaType: string): string {
    const suffixMap: Record<string, string> = {
      max_users: 'users',
      max_compartments: 'compartments',
      max_children: 'children',
      max_storage_gb: 'GB',
      max_resources: 'resources',
    };
    return suffixMap[quotaType] ?? '';
  }

  private updateQuotaInList(updated: TenantQuota): void {
    this.quotas.update((qs) =>
      qs.map((q) => q.quota_type === updated.quota_type ? updated : q),
    );
  }

  // ── Governance Tab ─────────────────────────────────────────────

  private loadGovernanceData(): void {
    this.componentService.listGovernance().subscribe({
      next: rules => this.governanceRules.set(rules),
      error: () => this.governanceRules.set([]),
    });
    this.componentService.listComponents({ providerMode: true, publishedOnly: true }).subscribe({
      next: components => {
        this.providerComponents.set(components);
        this.componentNameMap.clear();
        for (const c of components) {
          this.componentNameMap.set(c.id, c.displayName);
        }
      },
    });
  }

  getComponentName(componentId: string): string {
    return this.componentNameMap.get(componentId) || componentId.slice(0, 8) + '...';
  }

  editGovernance(rule: ComponentGovernance): void {
    this.editingGovernanceId.set(rule.id);
    this.govFormComponentId = rule.componentId;
    this.govFormIsAllowed = rule.isAllowed;
    this.govFormMaxInstances = rule.maxInstances;
    this.govFormConstraints = rule.parameterConstraints
      ? JSON.stringify(rule.parameterConstraints, null, 2)
      : '';
    this.showGovernanceForm.set(true);
  }

  cancelGovernanceForm(): void {
    this.showGovernanceForm.set(false);
    this.editingGovernanceId.set(null);
    this.govFormComponentId = '';
    this.govFormIsAllowed = true;
    this.govFormMaxInstances = null;
    this.govFormConstraints = '';
  }

  saveGovernance(): void {
    if (!this.govFormComponentId) return;
    this.govSaving.set(true);

    let constraints: Record<string, unknown> | undefined;
    if (this.govFormConstraints.trim()) {
      try {
        constraints = JSON.parse(this.govFormConstraints);
      } catch {
        this.toastService.error('Invalid JSON in parameter constraints');
        this.govSaving.set(false);
        return;
      }
    }

    this.componentService.setGovernance({
      componentId: this.govFormComponentId,
      tenantId: this.tenantId,
      isAllowed: this.govFormIsAllowed,
      parameterConstraints: constraints,
      maxInstances: this.govFormMaxInstances ?? undefined,
    }).subscribe({
      next: () => {
        this.govSaving.set(false);
        this.cancelGovernanceForm();
        this.governanceLoaded = false;
        this.loadGovernanceData();
        this.toastService.success('Governance rule saved');
      },
      error: err => {
        this.govSaving.set(false);
        this.toastService.error(err.message || 'Failed to save governance rule');
      },
    });
  }

  deleteGovernance(rule: ComponentGovernance): void {
    this.componentService.deleteGovernance(rule.componentId, rule.tenantId).subscribe({
      next: () => {
        this.governanceRules.update(rules => rules.filter(r => r.id !== rule.id));
        this.toastService.success('Governance rule deleted');
      },
      error: err => this.toastService.error(err.message || 'Failed to delete governance rule'),
    });
  }
}
