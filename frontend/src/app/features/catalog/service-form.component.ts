/**
 * Overview: Service offering create/edit form — manage service name, description,
 *     category (with autocomplete), service group association (with on-the-fly creation),
 *     service type, measuring unit (filtered by type),
 *     operating model, region picker (with add link), multi-select CI class chips,
 *     CI class ↔ activity associations, coverage model, active status, status badge
 *     with lifecycle actions (publish/archive/clone), base fee + fee period,
 *     and provider SKU composition for resource offerings.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/catalog.service,
 *     app/core/services/cmdb.service, app/core/services/delivery.service, app/core/services/semantic.service
 * Concepts: Service offering CRUD, type-filtered measuring units, multi-CI-class chip selector,
 *     category autocomplete, service group membership, CI class ↔ activity associations,
 *     region add link, offering lifecycle (draft/published/archived), read-only mode for
 *     published/archived, SKU composition
 */
import { Component, inject, signal, computed, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators, FormsModule } from '@angular/forms';
import { CatalogService } from '@core/services/catalog.service';
import { CmdbService } from '@core/services/cmdb.service';
import { DeliveryService } from '@core/services/delivery.service';
import { SemanticService } from '@core/services/semantic.service';
import {
  ServiceOffering, CIClass, CIClassActivityAssociation, MeasuringUnit,
  ProviderSku, ServiceOfferingSku, OfferingStatus,
} from '@shared/models/cmdb.model';
import { SemanticResourceType, SemanticProvider } from '@shared/models/semantic.model';
import { ActivityTemplate, DeliveryRegion, ServiceProcess, ServiceProcessAssignment } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const LABOR_UNITS: { value: MeasuringUnit; label: string }[] = [
  { value: 'hour', label: 'Hour' }, { value: 'day', label: 'Day' },
  { value: 'month', label: 'Month' }, { value: 'user', label: 'User' },
];
const RESOURCE_UNITS: { value: MeasuringUnit; label: string }[] = [
  { value: 'month', label: 'Month' }, { value: 'gb', label: 'GB' },
  { value: 'request', label: 'Request' }, { value: 'instance', label: 'Instance' },
];
const SERVICE_TYPES = [{ value: 'resource', label: 'Resource' }, { value: 'labor', label: 'Labor' }];
const OPERATING_MODELS = [{ value: 'regional', label: 'Regional' }, { value: 'follow_the_sun', label: 'Follow the Sun' }];
const COVERAGE_MODELS = [
  { value: '', label: 'None' }, { value: 'business_hours', label: 'Business Hours' },
  { value: 'extended', label: 'Extended' }, { value: '24x7', label: '24/7' },
];
const FEE_PERIODS = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual', label: 'Annual' },
];

@Component({
  selector: 'nimbus-service-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="service-form-page">
        <div class="page-header">
          <div class="page-header-left">
            <h1>{{ isEditMode() ? 'Edit Service Offering' : 'Create Service Offering' }}</h1>
            @if (isEditMode() && offeringStatus()) {
              <span class="badge-status" [class]="'badge-status-' + offeringStatus()">
                {{ offeringStatus() | titlecase }}
              </span>
            }
          </div>
          @if (isEditMode() && offeringStatus()) {
            <div class="page-header-actions">
              @if (offeringStatus() === 'draft') {
                <button type="button" class="btn btn-success" (click)="publishOffering()" [disabled]="lifecycleActionInProgress()">
                  {{ lifecycleActionInProgress() ? 'Publishing...' : 'Publish' }}
                </button>
              }
              @if (offeringStatus() === 'published') {
                <button type="button" class="btn btn-warning" (click)="archiveOffering()" [disabled]="lifecycleActionInProgress()">
                  {{ lifecycleActionInProgress() ? 'Archiving...' : 'Archive' }}
                </button>
                <button type="button" class="btn btn-secondary" (click)="cloneOffering()" [disabled]="lifecycleActionInProgress()">Clone</button>
              }
              @if (offeringStatus() === 'archived') {
                <button type="button" class="btn btn-secondary" (click)="cloneOffering()" [disabled]="lifecycleActionInProgress()">Clone</button>
              }
            </div>
          }
        </div>

        <!-- Read-only banner for published/archived offerings -->
        @if (isReadOnly()) {
          <div class="info-banner">
            <span class="info-banner-icon">&#9432;</span>
            <span>
              This offering is {{ offeringStatus() }}. To make changes, clone it first.
            </span>
            <button type="button" class="btn btn-primary btn-sm" (click)="cloneAndEdit()" [disabled]="lifecycleActionInProgress()">
              {{ lifecycleActionInProgress() ? 'Cloning...' : 'Clone & Edit' }}
            </button>
          </div>
        }

        @if (loading()) { <div class="loading">Loading...</div> }
        @if (!loading()) {
          <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
            <div class="form-group">
              <label for="name">Name *</label>
              <input id="name" formControlName="name" class="form-input" placeholder="Service offering name" />
              @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                <span class="error">Name is required</span>
              }
            </div>
            <div class="form-group">
              <label for="description">Description</label>
              <textarea id="description" formControlName="description" class="form-input form-textarea"
                placeholder="Optional description of the service offering" rows="3"></textarea>
            </div>
            <!-- Category autocomplete -->
            <div class="form-group autocomplete-wrapper">
              <label for="category">Category</label>
              <input id="category" formControlName="category" class="form-input"
                placeholder="e.g. Compute, Storage, Network" (input)="onCategoryInput()"
                (focus)="showCategoryDropdown.set(true)" (blur)="hideCategoryDropdownDelayed()" autocomplete="off" />
              @if (showCategoryDropdown() && filteredCategories().length > 0) {
                <div class="autocomplete-dropdown">
                  @for (cat of filteredCategories(); track cat) {
                    <div class="autocomplete-item" (mousedown)="selectCategory(cat)">{{ cat }}</div>
                  }
                </div>
              }
            </div>
            <div class="form-group">
              <label for="serviceType">Service Type *</label>
              <select id="serviceType" formControlName="serviceType" class="form-input form-select">
                @for (st of serviceTypes; track st.value) { <option [value]="st.value">{{ st.label }}</option> }
              </select>
              <span class="form-hint">Resource = cloud/infrastructure services. Labor = human-delivered services.</span>
            </div>
            <div class="form-group">
              <label for="measuringUnit">Measuring Unit *</label>
              <select id="measuringUnit" formControlName="measuringUnit" class="form-input form-select">
                @for (unit of filteredUnits(); track unit.value) { <option [value]="unit.value">{{ unit.label }}</option> }
              </select>
            </div>
            <div class="form-group">
              <label for="operatingModel">Operating Model *</label>
              <select id="operatingModel" formControlName="operatingModel" class="form-input form-select">
                @for (om of operatingModels; track om.value) { <option [value]="om.value">{{ om.label }}</option> }
              </select>
              <span class="form-hint">Regional = specific delivery regions. Follow the Sun = all regions, 24/7 coverage.</span>
            </div>
            @if (form.get('operatingModel')?.value === 'regional') {
              <div class="form-group">
                <label>Delivery Regions *</label>
                <div class="region-picker">
                  @for (region of deliveryRegions(); track region.id) {
                    <label class="region-checkbox">
                      <input type="checkbox" [checked]="selectedRegionIds().includes(region.id)" (change)="toggleRegion(region.id)" />
                      <span>{{ region.displayName }} ({{ region.code }})</span>
                    </label>
                  }
                  @if (deliveryRegions().length === 0) { <span class="form-hint">No delivery regions configured.</span> }
                </div>
                <a class="add-link" (click)="navigateToAddRegion()">+ Add Region</a>
                @if (selectedRegionIds().length === 0 && deliveryRegions().length > 0) {
                  <span class="error">Select at least one delivery region</span>
                }
              </div>
            }
            <div class="form-group">
              <label for="defaultCoverageModel">Default Coverage Model</label>
              <select id="defaultCoverageModel" formControlName="defaultCoverageModel" class="form-input form-select">
                @for (cm of coverageModels; track cm.value) { <option [value]="cm.value">{{ cm.label }}</option> }
              </select>
            </div>

            <!-- Base Fee + Fee Period -->
            <div class="form-group">
              <label for="baseFee">Base Fee</label>
              <input id="baseFee" type="number" formControlName="baseFee" class="form-input"
                placeholder="Fixed recurring charge (optional)" min="0" step="0.01" />
              <span class="form-hint">Optional fixed recurring charge applied to the offering.</span>
            </div>
            @if (form.get('baseFee')?.value != null && form.get('baseFee')?.value !== 0) {
              <div class="form-group">
                <label for="feePeriod">Fee Period</label>
                <select id="feePeriod" formControlName="feePeriod" class="form-input form-select">
                  <option value="">Select period...</option>
                  @for (fp of feePeriods; track fp.value) { <option [value]="fp.value">{{ fp.label }}</option> }
                </select>
                <span class="form-hint">Billing period for the base fee.</span>
              </div>
            }

            <!-- Minimum Charge -->
            <div class="form-group" style="margin-top: 0.5rem; padding-top: 1rem; border-top: 1px solid #f1f5f9;">
              <label for="minimumAmount">Minimum Charge</label>
              <input id="minimumAmount" type="number" formControlName="minimumAmount" class="form-input"
                placeholder="Minimum monthly/annual charge (optional)" min="0" step="0.01" />
              <span class="form-hint">Minimum billing threshold for this service.</span>
            </div>
            @if (minimumAmountValue() > 0) {
              <div class="form-row" style="display: flex; gap: 1rem;">
                <div class="form-group" style="flex: 1;">
                  <label for="minimumCurrency">Currency</label>
                  <select id="minimumCurrency" formControlName="minimumCurrency" class="form-input form-select">
                    <option value="EUR">EUR</option>
                    <option value="USD">USD</option>
                    <option value="GBP">GBP</option>
                    <option value="CHF">CHF</option>
                  </select>
                </div>
                <div class="form-group" style="flex: 1;">
                  <label for="minimumPeriod">Period</label>
                  <select id="minimumPeriod" formControlName="minimumPeriod" class="form-input form-select">
                    <option value="monthly">Monthly</option>
                    <option value="annual">Annual</option>
                  </select>
                </div>
              </div>
            }

            <!-- CI Classes multi-select chips -->
            <div class="form-group autocomplete-wrapper">
              <label>CI Classes</label>
              <div class="chip-container">
                @for (cls of selectedClassDetails(); track cls.id) {
                  <span class="chip">
                    @if (cls.categoryName) { <span class="chip-category">{{ cls.categoryName }}</span> }
                    <span>{{ cls.displayName }}</span>
                    @if (cls.semanticTypeId) {
                      <a class="chip-link" (click)="navigateToSemanticType(cls.semanticTypeId!)" title="View in Semantic Explorer">&#8599;</a>
                    }
                    @if (!isReadOnly()) {
                      <button type="button" class="chip-remove" (click)="removeCIClass(cls.id)">&times;</button>
                    }
                  </span>
                }
                @if (!isReadOnly()) {
                  <input type="text" class="chip-input" placeholder="Search CI classes..."
                    [(ngModel)]="ciClassSearchText" [ngModelOptions]="{standalone: true}"
                    (input)="onCIClassSearch()" (focus)="showClassDropdown.set(true)" (blur)="hideClassDropdownDelayed()" />
                }
              </div>
              @if (showClassDropdown() && filteredClasses().length > 0) {
                <div class="autocomplete-dropdown">
                  @for (cls of filteredClasses(); track cls.id) {
                    <div class="autocomplete-item" (mousedown)="addCIClass(cls.id)">
                      @if (getCategoryForClass(cls)) { <span class="chip-category">{{ getCategoryForClass(cls) }}</span> }
                      {{ cls.displayName }} ({{ cls.name }})
                    </div>
                  }
                </div>
              }
              <span class="form-hint">Link CI classes for consumption measurement. Available for both resource and labor services.</span>
            </div>
            @if (isEditMode()) {
              <div class="form-group">
                <label class="toggle-label">
                  <input type="checkbox" formControlName="isActive" />
                  <span>{{ form.get('isActive')?.value ? 'Active' : 'Inactive' }}</span>
                </label>
              </div>
            }

            <!-- CI Class ↔ Activity Associations -->
            @if (isEditMode() && selectedCIClassIds().length > 0) {
              <div class="assoc-section">
                <h3 class="process-title">CI Class ↔ Activity Associations</h3>
                @if (ciClassAssociations().length > 0) {
                  <table class="assign-table">
                    <thead><tr><th>CI Class</th><th>Relationship</th><th>Activity Template</th><th>Actions</th></tr></thead>
                    <tbody>
                      @for (a of ciClassAssociations(); track a.id) {
                        <tr><td>{{ a.ciClassDisplayName }}</td><td>{{ a.relationshipType || '\u2014' }}</td>
                          <td>{{ a.activityTemplateName }}</td>
                          <td>
                            @if (!isReadOnly()) {
                              <button type="button" class="btn-action btn-delete" (click)="removeAssociation(a.id)">Remove</button>
                            }
                          </td></tr>
                      }
                    </tbody>
                  </table>
                } @else { <div class="no-assignments">No associations defined.</div> }
                @if (!isReadOnly()) {
                  <div class="assoc-add-form">
                    <select class="form-input assign-field" [(ngModel)]="assocCIClassId" [ngModelOptions]="{standalone: true}">
                      <option value="">CI Class...</option>
                      @for (cls of selectedClassDetails(); track cls.id) { <option [value]="cls.id">{{ cls.displayName }}</option> }
                    </select>
                    <input type="text" class="form-input assign-field" placeholder="Relationship type"
                      [(ngModel)]="assocRelType" [ngModelOptions]="{standalone: true}" list="rel-type-suggestions" />
                    <datalist id="rel-type-suggestions">
                      @for (s of relationshipTypeSuggestions(); track s) { <option [value]="s"></option> }
                    </datalist>
                    <select class="form-input assign-field" [(ngModel)]="assocActivityTemplateId" [ngModelOptions]="{standalone: true}">
                      <option value="">Activity Template...</option>
                      @for (tmpl of activityTemplates(); track tmpl.id) { <option [value]="tmpl.id">{{ tmpl.name }}</option> }
                    </select>
                    <button type="button" class="btn btn-sm btn-primary" (click)="addAssociation()"
                      [disabled]="!assocCIClassId || !assocActivityTemplateId">Add</button>
                  </div>
                }
              </div>
            }

            <!-- Provider SKU Composition (resource offerings in edit mode) -->
            @if (isEditMode() && serviceTypeValue() === 'resource') {
              <div class="sku-section">
                <h3 class="process-title">Provider SKU Composition</h3>
                @if (offeringSkuRows().length > 0) {
                  <table class="assign-table">
                    <thead>
                      <tr>
                        <th>SKU Name</th>
                        <th>Provider</th>
                        <th>Quantity</th>
                        <th>Required?</th>
                        <th>Sort Order</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (row of offeringSkuRows(); track row.link.id) {
                        <tr>
                          <td>{{ row.skuName }}</td>
                          <td>{{ row.providerName }}</td>
                          <td>{{ row.link.defaultQuantity }}</td>
                          <td>{{ row.link.isRequired ? 'Yes' : 'No' }}</td>
                          <td>{{ row.link.sortOrder }}</td>
                          <td>
                            @if (!isReadOnly()) {
                              <button type="button" class="btn-action btn-delete" (click)="removeSkuFromOffering(row.link.id)">Remove</button>
                            }
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="no-assignments">No SKUs linked to this offering.</div>
                }

                @if (!isReadOnly()) {
                  <div class="sku-add-form">
                    <select class="form-input assign-field" [(ngModel)]="skuProviderFilter" [ngModelOptions]="{standalone: true}"
                      (ngModelChange)="onSkuProviderChange()">
                      <option value="">Select provider...</option>
                      @for (prov of semanticProviders(); track prov.id) {
                        <option [value]="prov.id">{{ prov.displayName }}</option>
                      }
                    </select>
                    <select class="form-input assign-field" [(ngModel)]="skuSelectedId" [ngModelOptions]="{standalone: true}"
                      [disabled]="!skuProviderFilter">
                      <option value="">Select SKU...</option>
                      @for (sku of availableSkus(); track sku.id) {
                        <option [value]="sku.id">{{ sku.displayName || sku.name }}</option>
                      }
                    </select>
                    <input type="number" class="form-input assign-field-sm" placeholder="Qty"
                      [(ngModel)]="skuQuantity" [ngModelOptions]="{standalone: true}" min="1" />
                    <label class="toggle-label">
                      <input type="checkbox" [(ngModel)]="skuIsRequired" [ngModelOptions]="{standalone: true}" />
                      <span>Required</span>
                    </label>
                    <button type="button" class="btn btn-sm btn-primary" (click)="addSkuToOffering()"
                      [disabled]="!skuSelectedId || !skuProviderFilter">Add</button>
                  </div>
                }
              </div>
            }

            <!-- Delivery Processes -->
            @if (isEditMode()) {
              <div class="process-section">
                <h3 class="process-title">Delivery Processes</h3>
                @if (!isReadOnly()) {
                  <div class="assign-form">
                    <select class="form-input assign-field" [(ngModel)]="assignProcessId" [ngModelOptions]="{standalone: true}">
                      <option value="">Select process...</option>
                      @for (proc of processes(); track proc.id) { <option [value]="proc.id">{{ proc.name }}</option> }
                    </select>
                    <select class="form-input assign-field-sm" [(ngModel)]="assignCoverage" [ngModelOptions]="{standalone: true}">
                      <option value="">No coverage</option><option value="business_hours">Business Hours</option>
                      <option value="extended">Extended</option><option value="24x7">24x7</option>
                    </select>
                    <label class="toggle-label">
                      <input type="checkbox" [(ngModel)]="assignIsDefault" [ngModelOptions]="{standalone: true}" /><span>Default</span>
                    </label>
                    <button type="button" class="btn btn-sm btn-primary" (click)="assignProcess()" [disabled]="!assignProcessId">Assign</button>
                  </div>
                }
                @if (assignments().length > 0) {
                  <table class="assign-table">
                    <thead><tr><th>Process</th><th>Coverage</th><th>Default?</th><th>Actions</th></tr></thead>
                    <tbody>
                      @for (a of assignments(); track a.id) {
                        <tr><td>{{ processNameForId(a.processId) }}</td><td>{{ a.coverageModel || '\u2014' }}</td>
                          <td>{{ a.isDefault ? 'Yes' : 'No' }}</td>
                          <td>
                            @if (!isReadOnly()) {
                              <button type="button" class="btn-action btn-delete" (click)="removeAssignment(a.id)">Remove</button>
                            }
                          </td></tr>
                      }
                    </tbody>
                  </table>
                } @else { <div class="no-assignments">No processes assigned.</div> }
              </div>
            }
            @if (errorMessage()) { <div class="form-error">{{ errorMessage() }}</div> }
            @if (!isReadOnly()) {
              <div class="form-actions">
                <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
                  {{ submitting() ? 'Saving...' : (isEditMode() ? 'Update' : 'Create') }}
                </button>
                <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
              </div>
            }
            @if (isReadOnly()) {
              <div class="form-actions">
                <button type="button" class="btn btn-secondary" (click)="cancel()">Back</button>
              </div>
            }
          </form>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .service-form-page { padding: 0; max-width: 680px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap; }
    .page-header-left { display: flex; align-items: center; gap: 0.75rem; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .page-header-actions { display: flex; gap: 0.5rem; }
    .loading { padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem; }

    /* Status badges */
    .badge-status { display: inline-flex; align-items: center; padding: 0.1875rem 0.625rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap; }
    .badge-status-draft { background: #fef3c7; color: #92400e; }
    .badge-status-published { background: #dcfce7; color: #166534; }
    .badge-status-archived { background: #f1f5f9; color: #64748b; }

    /* Info banner */
    .info-banner { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; margin-bottom: 1.25rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; font-size: 0.8125rem; color: #1e40af; }
    .info-banner-icon { font-size: 1.125rem; flex-shrink: 0; }

    .form { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem; }
    .form-group { margin-bottom: 1.25rem; }
    .form-group label { display: block; margin-bottom: 0.375rem; font-size: 0.8125rem; font-weight: 600; color: #374151; }
    .form-input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box; font-family: inherit; transition: border-color 0.15s; background: #fff; color: #1e293b; }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .form-textarea { resize: vertical; min-height: 60px; }
    .form-select { cursor: pointer; }
    .form-hint { display: block; font-size: 0.6875rem; color: #64748b; margin-top: 0.25rem; }
    .toggle-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: #374151; cursor: pointer; }
    .toggle-label input[type="checkbox"] { cursor: pointer; }
    .error { color: #dc2626; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error { background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem; border: 1px solid #fecaca; }
    .region-picker { max-height: 200px; overflow-y: auto; padding: 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; }
    .region-checkbox { display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0; font-size: 0.8125rem; color: #374151; cursor: pointer; font-weight: 400; }
    .region-checkbox input[type="checkbox"] { cursor: pointer; }
    .add-link { display: inline-block; margin-top: 0.375rem; font-size: 0.75rem; color: #3b82f6; cursor: pointer; text-decoration: none; }
    .add-link:hover { text-decoration: underline; }
    .autocomplete-wrapper { position: relative; }
    .autocomplete-dropdown { position: absolute; z-index: 10; width: 100%; max-height: 200px; overflow-y: auto; background: #fff; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 6px 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); }
    .autocomplete-item { padding: 0.5rem 0.75rem; font-size: 0.8125rem; color: #1e293b; cursor: pointer; }
    .autocomplete-item:hover { background: #f1f5f9; }
    .chip-container { display: flex; flex-wrap: wrap; gap: 0.375rem; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; min-height: 38px; align-items: center; }
    .chip { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.25rem 0.5rem; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 16px; font-size: 0.75rem; color: #1e293b; }
    .chip-category { display: inline-block; padding: 0.0625rem 0.375rem; background: #dbeafe; color: #1d4ed8; border-radius: 10px; font-size: 0.625rem; font-weight: 600; }
    .chip-link { cursor: pointer; color: #3b82f6; font-size: 0.75rem; text-decoration: none; }
    .chip-link:hover { color: #2563eb; }
    .chip-remove { cursor: pointer; background: none; border: none; color: #94a3b8; font-size: 0.875rem; padding: 0; line-height: 1; margin-left: 0.125rem; }
    .chip-remove:hover { color: #dc2626; }
    .chip-input { flex: 1; min-width: 120px; border: none; outline: none; font-size: 0.8125rem; padding: 0.25rem 0; background: transparent; color: #1e293b; font-family: inherit; }
    .chip-input::placeholder { color: #94a3b8; }
    .assoc-section { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #e2e8f0; }
    .assoc-add-form { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-top: 0.75rem; }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.5rem; transition: background 0.15s; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-success { background: #16a34a; color: #fff; border: none; }
    .btn-success:hover { background: #15803d; }
    .btn-success:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-warning { background: #f59e0b; color: #fff; border: none; }
    .btn-warning:hover { background: #d97706; }
    .btn-warning:disabled { opacity: 0.5; cursor: not-allowed; }
    .process-section { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #e2e8f0; }
    .process-title { font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem; }
    .assign-form { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem; }
    .assign-field { flex: 2; min-width: 180px; }
    .assign-field-sm { flex: 1; min-width: 120px; max-width: 160px; }
    .assign-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .assign-table th, .assign-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
    .assign-table th { font-weight: 600; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .btn-action { padding: 0.25rem 0.625rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; font-family: inherit; cursor: pointer; border: 1px solid transparent; }
    .btn-delete { background: #fff; color: #dc2626; border-color: #fecaca; }
    .btn-delete:hover { background: #fef2f2; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; border: none; }
    .no-assignments { color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* SKU composition section */
    .sku-section { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #e2e8f0; }
    .sku-add-form { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-top: 0.75rem; }

  `],
})
export class ServiceFormComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private cmdbService = inject(CmdbService);
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);
  private deliveryService = inject(DeliveryService);
  private semanticService = inject(SemanticService);

  isEditMode = signal(false);
  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');
  classes = signal<CIClass[]>([]);
  existingOffering = signal<ServiceOffering | null>(null);
  processes = signal<ServiceProcess[]>([]);
  assignments = signal<ServiceProcessAssignment[]>([]);
  deliveryRegions = signal<DeliveryRegion[]>([]);
  selectedRegionIds = signal<string[]>([]);
  serviceTypeValue = signal<string>('resource');
  minimumAmountValue = signal<number>(0);
  assignProcessId = '';
  assignCoverage = '';
  assignIsDefault = false;
  existingCategories = signal<string[]>([]);
  showCategoryDropdown = signal(false);
  filteredCategories = computed(() => {
    const input = (this.form.get('category')?.value || '').toLowerCase();
    if (!input) return this.existingCategories();
    return this.existingCategories().filter(c => c.toLowerCase().includes(input));
  });
  selectedCIClassIds = signal<string[]>([]);
  ciClassSearchText = '';
  showClassDropdown = signal(false);
  semanticTypes = signal<SemanticResourceType[]>([]);
  selectedClassDetails = computed(() => {
    const ids = this.selectedCIClassIds();
    const allClasses = this.classes();
    const stypes = this.semanticTypes();
    return ids.map(id => {
      const cls = allClasses.find(c => c.id === id);
      if (!cls) return { id, displayName: id.substring(0, 8), name: '', semanticTypeId: null, categoryName: '' };
      const st = cls.semanticTypeId ? stypes.find(t => t.id === cls.semanticTypeId) : null;
      return { id: cls.id, displayName: cls.displayName, name: cls.name, semanticTypeId: cls.semanticTypeId, categoryName: st?.category?.displayName || '' };
    });
  });
  filteredClasses = computed(() => {
    const search = this.ciClassSearchText.toLowerCase();
    const selected = this.selectedCIClassIds();
    return this.classes().filter(c => !selected.includes(c.id)).filter(c => !search || c.displayName.toLowerCase().includes(search) || c.name.toLowerCase().includes(search));
  });
  ciClassAssociations = signal<CIClassActivityAssociation[]>([]);
  activityTemplates = signal<ActivityTemplate[]>([]);
  relationshipTypeSuggestions = signal<string[]>([]);
  assocCIClassId = '';
  assocRelType = '';
  assocActivityTemplateId = '';
  filteredUnits = computed(() => this.serviceTypeValue() === 'labor' ? LABOR_UNITS : RESOURCE_UNITS);
  readonly serviceTypes = SERVICE_TYPES;
  readonly operatingModels = OPERATING_MODELS;
  readonly coverageModels = COVERAGE_MODELS;
  readonly feePeriods = FEE_PERIODS;

  // Lifecycle state
  offeringStatus = signal<OfferingStatus | null>(null);
  lifecycleActionInProgress = signal(false);
  isReadOnly = computed(() => {
    const status = this.offeringStatus();
    return status === 'published' || status === 'archived';
  });

  // SKU composition state
  offeringSkuLinks = signal<ServiceOfferingSku[]>([]);
  skuDetailsMap = signal<Record<string, ProviderSku>>({});
  semanticProviders = signal<SemanticProvider[]>([]);
  availableSkus = signal<ProviderSku[]>([]);
  skuProviderFilter = '';
  skuSelectedId = '';
  skuQuantity = 1;
  skuIsRequired = false;
  offeringSkuRows = computed(() => {
    const links = this.offeringSkuLinks();
    const skuMap = this.skuDetailsMap();
    const providers = this.semanticProviders();
    return links.map(link => {
      const sku = skuMap[link.providerSkuId];
      const provider = sku ? providers.find(p => p.id === sku.providerId) : null;
      return {
        link,
        skuName: sku ? (sku.displayName || sku.name) : link.providerSkuId.substring(0, 8) + '...',
        providerName: provider?.displayName || (sku?.providerId?.substring(0, 8) + '...' || '--'),
      };
    });
  });

  form = this.fb.group({
    name: ['', [Validators.required]], description: [''], category: [''],
    measuringUnit: ['month' as string, [Validators.required]],
    serviceType: ['resource' as string, [Validators.required]],
    operatingModel: ['regional' as string, [Validators.required]],
    defaultCoverageModel: [''], isActive: [true],
    baseFee: [null as number | null],
    feePeriod: ['' as string],
    minimumAmount: [null as number | null],
    minimumCurrency: ['EUR' as string],
    minimumPeriod: ['monthly' as string],
  });
  private offeringId: string | null = null;

  ngOnInit(): void {
    this.offeringId = this.route.snapshot.paramMap.get('id') ?? null;
    this.isEditMode.set(!!this.offeringId);
    this.loadClasses();
    this.loadProcesses();
    this.loadRegions();
    this.loadCategories();
    this.loadSemanticTypes();
    this.loadSemanticProviders();
    this.setupFormReactions();
    if (this.offeringId) {
      this.loading.set(true);
      this.loadExistingOffering(this.offeringId);
      this.loadActivityTemplates();
      this.loadRelationshipTypeSuggestions();
    }
  }

  onSubmit(): void {
    if (this.form.invalid || this.isReadOnly()) return;
    this.submitting.set(true);
    this.errorMessage.set('');
    if (this.isEditMode() && this.offeringId) { this.submitUpdate(this.offeringId); } else { this.submitCreate(); }
  }

  cancel(): void { this.router.navigate(['/catalog', 'services']); }
  onCategoryInput(): void { this.showCategoryDropdown.set(true); }
  selectCategory(cat: string): void { this.form.patchValue({ category: cat }); this.showCategoryDropdown.set(false); }
  hideCategoryDropdownDelayed(): void { setTimeout(() => this.showCategoryDropdown.set(false), 150); }

  toggleRegion(regionId: string): void {
    if (this.isReadOnly()) return;
    const current = this.selectedRegionIds();
    this.selectedRegionIds.set(current.includes(regionId) ? current.filter(id => id !== regionId) : [...current, regionId]);
  }
  navigateToAddRegion(): void { this.router.navigate(['/catalog', 'regions', 'create']); }

  onCIClassSearch(): void { this.showClassDropdown.set(true); }
  hideClassDropdownDelayed(): void { setTimeout(() => this.showClassDropdown.set(false), 150); }
  addCIClass(id: string): void {
    if (this.isReadOnly()) return;
    if (!this.selectedCIClassIds().includes(id)) { this.selectedCIClassIds.set([...this.selectedCIClassIds(), id]); }
    this.ciClassSearchText = '';
    this.showClassDropdown.set(false);
  }
  removeCIClass(id: string): void {
    if (this.isReadOnly()) return;
    this.selectedCIClassIds.set(this.selectedCIClassIds().filter(cid => cid !== id));
  }
  getCategoryForClass(cls: CIClass): string {
    if (!cls.semanticTypeId) return '';
    const st = this.semanticTypes().find(t => t.id === cls.semanticTypeId);
    return st?.category?.displayName || '';
  }
  navigateToSemanticType(semanticTypeId: string): void { this.router.navigate(['/semantic', 'types', semanticTypeId]); }

  addAssociation(): void {
    if (this.isReadOnly()) return;
    if (!this.assocCIClassId || !this.assocActivityTemplateId) return;
    this.catalogService.createCIClassActivityAssociation({
      ciClassId: this.assocCIClassId, activityTemplateId: this.assocActivityTemplateId,
      relationshipType: this.assocRelType || null,
    }).subscribe({
      next: (a) => { this.ciClassAssociations.update(list => [...list, a]); this.assocCIClassId = ''; this.assocRelType = ''; this.assocActivityTemplateId = ''; this.toastService.success('Association created'); },
      error: (err) => this.toastService.error(err.message || 'Failed to create association'),
    });
  }
  removeAssociation(id: string): void {
    if (this.isReadOnly()) return;
    this.catalogService.deleteCIClassActivityAssociation(id).subscribe({
      next: () => { this.ciClassAssociations.update(list => list.filter(a => a.id !== id)); this.toastService.success('Association removed'); },
      error: (err) => this.toastService.error(err.message || 'Failed to remove association'),
    });
  }

  assignProcess(): void {
    if (this.isReadOnly()) return;
    if (!this.offeringId || !this.assignProcessId) return;
    this.deliveryService.createAssignment({ serviceOfferingId: this.offeringId, processId: this.assignProcessId, coverageModel: this.assignCoverage || null, isDefault: this.assignIsDefault }).subscribe({
      next: (a) => { this.assignments.update(list => [...list, a]); this.assignProcessId = ''; this.assignCoverage = ''; this.assignIsDefault = false; this.toastService.success('Process assigned'); },
      error: (err) => this.toastService.error(err.message || 'Failed to assign process'),
    });
  }
  removeAssignment(id: string): void {
    if (this.isReadOnly()) return;
    this.deliveryService.deleteAssignment(id).subscribe({
      next: () => { this.assignments.update(list => list.filter(a => a.id !== id)); this.toastService.success('Assignment removed'); },
      error: (err) => this.toastService.error(err.message || 'Failed to remove assignment'),
    });
  }
  processNameForId(processId: string): string {
    const p = this.processes().find(proc => proc.id === processId);
    return p ? p.name : processId.substring(0, 8) + '...';
  }

  // ── Lifecycle actions ──────────────────────────────────────────────

  publishOffering(): void {
    if (!this.offeringId) return;
    this.lifecycleActionInProgress.set(true);
    this.catalogService.publishOffering(this.offeringId).subscribe({
      next: (updated) => {
        this.existingOffering.set(updated);
        this.offeringStatus.set(updated.status);
        this.applyReadOnlyState();
        this.lifecycleActionInProgress.set(false);
        this.toastService.success(`"${updated.name}" published`);
      },
      error: (err) => {
        this.lifecycleActionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to publish offering');
      },
    });
  }

  archiveOffering(): void {
    if (!this.offeringId) return;
    this.lifecycleActionInProgress.set(true);
    this.catalogService.archiveOffering(this.offeringId).subscribe({
      next: (updated) => {
        this.existingOffering.set(updated);
        this.offeringStatus.set(updated.status);
        this.applyReadOnlyState();
        this.lifecycleActionInProgress.set(false);
        this.toastService.success(`"${updated.name}" archived`);
      },
      error: (err) => {
        this.lifecycleActionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to archive offering');
      },
    });
  }

  cloneOffering(): void {
    if (!this.offeringId) return;
    this.lifecycleActionInProgress.set(true);
    this.catalogService.cloneOffering(this.offeringId).subscribe({
      next: (cloned) => {
        this.lifecycleActionInProgress.set(false);
        this.toastService.success(`Cloned as "${cloned.name}"`);
        this.router.navigate(['/catalog', 'services', cloned.id, 'edit']);
      },
      error: (err) => {
        this.lifecycleActionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to clone offering');
      },
    });
  }

  cloneAndEdit(): void {
    this.cloneOffering();
  }

  // ── SKU composition actions ────────────────────────────────────────

  onSkuProviderChange(): void {
    this.skuSelectedId = '';
    this.availableSkus.set([]);
    if (this.skuProviderFilter) {
      this.catalogService.listSkus({ providerId: this.skuProviderFilter, activeOnly: true, limit: 500 }).subscribe({
        next: (result) => this.availableSkus.set(result.items),
        error: () => this.availableSkus.set([]),
      });
    }
  }

  addSkuToOffering(): void {
    if (this.isReadOnly() || !this.offeringId || !this.skuSelectedId) return;
    const nextSortOrder = this.offeringSkuLinks().length;
    this.catalogService.addSkuToOffering(
      this.offeringId, this.skuSelectedId, this.skuQuantity, this.skuIsRequired, nextSortOrder,
    ).subscribe({
      next: (link) => {
        this.offeringSkuLinks.update(list => [...list, link]);
        this.loadSkuDetail(link.providerSkuId);
        this.skuSelectedId = '';
        this.skuQuantity = 1;
        this.skuIsRequired = false;
        this.toastService.success('SKU added to offering');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to add SKU'),
    });
  }

  removeSkuFromOffering(linkId: string): void {
    if (this.isReadOnly()) return;
    this.catalogService.removeSkuFromOffering(linkId).subscribe({
      next: () => {
        this.offeringSkuLinks.update(list => list.filter(l => l.id !== linkId));
        this.toastService.success('SKU removed from offering');
      },
      error: (err) => this.toastService.error(err.message || 'Failed to remove SKU'),
    });
  }

  // ── Private methods ────────────────────────────────────────────────

  private setupFormReactions(): void {
    this.form.get('serviceType')?.valueChanges.subscribe(value => {
      const type = value || 'resource';
      this.serviceTypeValue.set(type);
      const validUnits = type === 'labor' ? LABOR_UNITS.map(u => u.value) : RESOURCE_UNITS.map(u => u.value);
      const currentUnit = this.form.get('measuringUnit')?.value;
      if (currentUnit && !validUnits.includes(currentUnit as MeasuringUnit)) { this.form.patchValue({ measuringUnit: 'month' }); }
    });
    this.form.get('operatingModel')?.valueChanges.subscribe(value => { if (value === 'follow_the_sun') { this.selectedRegionIds.set([]); } });
    this.form.get('minimumAmount')?.valueChanges.subscribe(value => { this.minimumAmountValue.set(value || 0); });
  }

  private submitCreate(): void {
    const values = this.form.value;
    this.catalogService.createOffering({
      name: values.name!, description: values.description || null, category: values.category || null,
      measuringUnit: values.measuringUnit || 'month', ciClassIds: this.selectedCIClassIds().length > 0 ? this.selectedCIClassIds() : null,
      serviceType: values.serviceType || 'resource', operatingModel: values.operatingModel || null, defaultCoverageModel: values.defaultCoverageModel || null,
      baseFee: values.baseFee || null, feePeriod: values.feePeriod || null,
      minimumAmount: values.minimumAmount || null, minimumCurrency: values.minimumCurrency || null, minimumPeriod: values.minimumPeriod || null,
    }).subscribe({
      next: (offering) => {
        const regionIds = this.selectedRegionIds();
        if (values.operatingModel === 'regional' && regionIds.length > 0) {
          this.catalogService.setOfferingRegions(offering.id, regionIds).subscribe({
            next: () => { this.toastService.success(`"${offering.name}" created`); this.router.navigate(['/catalog', 'services']); },
            error: () => { this.toastService.success(`"${offering.name}" created (regions save failed)`); this.router.navigate(['/catalog', 'services']); },
          });
        } else { this.toastService.success(`"${offering.name}" created`); this.router.navigate(['/catalog', 'services']); }
      },
      error: (err) => { this.submitting.set(false); const msg = err.message || 'Failed to create service offering'; this.errorMessage.set(msg); this.toastService.error(msg); },
    });
  }

  private submitUpdate(id: string): void {
    const values = this.form.value;
    this.catalogService.updateOffering(id, {
      name: values.name || null, description: values.description || null, category: values.category || null,
      measuringUnit: values.measuringUnit || null, ciClassIds: this.selectedCIClassIds(),
      serviceType: values.serviceType || null, operatingModel: values.operatingModel || null,
      defaultCoverageModel: values.defaultCoverageModel || null, isActive: values.isActive,
      minimumAmount: values.minimumAmount || null, minimumCurrency: values.minimumCurrency || null, minimumPeriod: values.minimumPeriod || null,
    }).subscribe({
      next: (offering) => {
        const regionIds = this.selectedRegionIds();
        this.catalogService.setOfferingRegions(offering.id, regionIds).subscribe({
          next: () => { this.toastService.success(`"${offering.name}" updated`); this.router.navigate(['/catalog', 'services']); },
          error: () => { this.toastService.success(`"${offering.name}" updated (regions save failed)`); this.router.navigate(['/catalog', 'services']); },
        });
      },
      error: (err) => { this.submitting.set(false); const msg = err.message || 'Failed to update service offering'; this.errorMessage.set(msg); this.toastService.error(msg); },
    });
  }

  private loadClasses(): void { this.cmdbService.listClasses(true).subscribe({ next: (classes) => this.classes.set(classes) }); }
  private loadProcesses(): void { this.deliveryService.listProcesses({ limit: 500 }).subscribe({ next: (r) => this.processes.set(r.items) }); }
  private loadRegions(): void { this.deliveryService.listRegions({ isActive: true, limit: 500 }).subscribe({ next: (r) => this.deliveryRegions.set(r.items) }); }
  private loadCategories(): void { this.catalogService.listDistinctCategories().subscribe({ next: (cats) => this.existingCategories.set(cats) }); }
  private loadSemanticTypes(): void { this.semanticService.listTypes({ limit: 500 }).subscribe({ next: (r) => this.semanticTypes.set(r.items) }); }
  private loadActivityTemplates(): void { this.deliveryService.listActivityTemplates({ limit: 500 }).subscribe({ next: (r) => this.activityTemplates.set(r.items) }); }
  private loadRelationshipTypeSuggestions(): void { this.catalogService.listRelationshipTypeSuggestions().subscribe({ next: (s) => this.relationshipTypeSuggestions.set(s) }); }
  private loadSemanticProviders(): void { this.semanticService.listProviders().subscribe({ next: (providers) => this.semanticProviders.set(providers) }); }

  private loadExistingOffering(id: string): void {
    this.catalogService.getOffering(id).subscribe({
      next: (offering) => {
        if (!offering) { this.loading.set(false); this.toastService.error('Service offering not found'); this.router.navigate(['/catalog', 'services']); return; }
        this.existingOffering.set(offering);
        this.offeringStatus.set(offering.status);
        this.serviceTypeValue.set(offering.serviceType || 'resource');
        this.form.patchValue({
          name: offering.name, description: offering.description || '', category: offering.category || '',
          measuringUnit: offering.measuringUnit, serviceType: offering.serviceType || 'resource',
          operatingModel: offering.operatingModel || 'regional', defaultCoverageModel: offering.defaultCoverageModel || '', isActive: offering.isActive,
          baseFee: offering.baseFee, feePeriod: offering.feePeriod || '',
          minimumAmount: offering.minimumAmount, minimumCurrency: offering.minimumCurrency || 'EUR', minimumPeriod: offering.minimumPeriod || 'monthly',
        });
        if (offering.regionIds) { this.selectedRegionIds.set(offering.regionIds); }
        if (offering.ciClassIds) { this.selectedCIClassIds.set(offering.ciClassIds); this.loadAssociationsForOffering(); }
        this.applyReadOnlyState();
        this.loading.set(false);
        this.deliveryService.listAssignments(offering.id).subscribe({ next: (assignments) => this.assignments.set(assignments) });
        this.loadOfferingSkus(offering.id);
      },
      error: () => { this.loading.set(false); this.toastService.error('Failed to load service offering'); this.router.navigate(['/catalog', 'services']); },
    });
  }

  private applyReadOnlyState(): void {
    if (this.isReadOnly()) {
      this.form.disable();
    } else {
      this.form.enable();
    }
  }

  private loadOfferingSkus(offeringId: string): void {
    this.catalogService.listOfferingSkus(offeringId).subscribe({
      next: (links) => {
        this.offeringSkuLinks.set(links);
        for (const link of links) {
          this.loadSkuDetail(link.providerSkuId);
        }
      },
      error: () => { /* SKU loading is best-effort */ },
    });
  }

  private loadSkuDetail(skuId: string): void {
    if (this.skuDetailsMap()[skuId]) return;
    this.catalogService.getSku(skuId).subscribe({
      next: (sku) => {
        if (sku) {
          this.skuDetailsMap.update(map => ({ ...map, [skuId]: sku }));
        }
      },
    });
  }

  private loadAssociationsForOffering(): void {
    const ids = this.selectedCIClassIds();
    if (ids.length === 0) { this.ciClassAssociations.set([]); return; }
    const allAssocs: CIClassActivityAssociation[] = [];
    let pending = ids.length;
    for (const ciClassId of ids) {
      this.catalogService.listCIClassActivityAssociations({ ciClassId }).subscribe({
        next: (assocs) => { allAssocs.push(...assocs); pending--; if (pending === 0) this.ciClassAssociations.set(allAssocs); },
        error: () => { pending--; if (pending === 0) this.ciClassAssociations.set(allAssocs); },
      });
    }
  }
}
