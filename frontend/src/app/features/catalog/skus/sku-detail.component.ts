/**
 * Overview: Provider SKU detail page — view and edit a single SKU with inline editing,
 *     attributes JSON editor, and active/deactivate toggle.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/catalog.service
 * Concepts: Provider SKU detail view, inline edit form, JSONB attributes editor, lifecycle toggle
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
import { CatalogService } from '@core/services/catalog.service';
import { CmdbService } from '@core/services/cmdb.service';
import { SemanticService } from '@core/services/semantic.service';
import {
  ProviderSku,
  MeasuringUnit,
  CIClass,
} from '@shared/models/cmdb.model';
import { SemanticProvider } from '@shared/models/semantic.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const MEASURING_UNIT_LABELS: Record<MeasuringUnit, string> = {
  hour: 'Hour',
  day: 'Day',
  month: 'Month',
  gb: 'GB',
  request: 'Request',
  user: 'User',
  instance: 'Instance',
};

const MEASURING_UNIT_OPTIONS: { value: MeasuringUnit; label: string }[] = [
  { value: 'hour', label: 'Hour' },
  { value: 'day', label: 'Day' },
  { value: 'month', label: 'Month' },
  { value: 'gb', label: 'GB' },
  { value: 'request', label: 'Request' },
  { value: 'user', label: 'User' },
  { value: 'instance', label: 'Instance' },
];

@Component({
  selector: 'nimbus-sku-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="sku-detail-page">
        @if (loading()) {
          <div class="loading">Loading...</div>
        }
        @if (!loading() && !sku()) {
          <div class="not-found">
            <p>Provider SKU not found.</p>
            <button class="btn btn-secondary" (click)="goBack()">Back to SKUs</button>
          </div>
        }
        @if (!loading() && sku()) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <button class="btn btn-back" (click)="goBack()">&larr; Back</button>
              <div class="header-info">
                <h1>
                  {{ sku()!.name }}
                  @if (sku()!.displayName) {
                    <span class="display-name">{{ sku()!.displayName }}</span>
                  }
                </h1>
                <div class="header-meta">
                  <span class="meta-item">{{ providerDisplayName() }}</span>
                  <code class="code-badge">{{ sku()!.externalSkuId }}</code>
                  <span
                    class="badge"
                    [class.badge-active]="sku()!.isActive"
                    [class.badge-inactive]="!sku()!.isActive"
                  >
                    {{ sku()!.isActive ? 'Active' : 'Inactive' }}
                  </span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button
                *nimbusHasPermission="'catalog:sku:manage'"
                class="btn btn-secondary"
                (click)="editing = !editing"
              >
                {{ editing ? 'Cancel Edit' : 'Edit' }}
              </button>
              <button
                *nimbusHasPermission="'catalog:sku:manage'"
                class="btn"
                [class.btn-danger]="sku()!.isActive"
                [class.btn-success]="!sku()!.isActive"
                (click)="toggleActive()"
                [disabled]="toggling()"
              >
                {{ sku()!.isActive ? 'Deactivate' : 'Reactivate' }}
              </button>
            </div>
          </div>

          <!-- Edit Form -->
          @if (editing) {
            <div class="detail-card">
              <h2 class="section-title">Edit SKU</h2>
              <div class="edit-form">
                <div class="form-row">
                  <div class="form-group">
                    <label for="editName">Name *</label>
                    <input
                      id="editName"
                      [(ngModel)]="editForm.name"
                      class="form-input"
                    />
                  </div>
                  <div class="form-group">
                    <label for="editDisplayName">Display Name</label>
                    <input
                      id="editDisplayName"
                      [(ngModel)]="editForm.displayName"
                      class="form-input"
                    />
                  </div>
                </div>
                <div class="form-group">
                  <label for="editDescription">Description</label>
                  <textarea
                    id="editDescription"
                    [(ngModel)]="editForm.description"
                    class="form-input form-textarea"
                    rows="2"
                  ></textarea>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label for="editCiClass">CI Class</label>
                    <select
                      id="editCiClass"
                      [(ngModel)]="editForm.ciClassId"
                      class="form-input form-select"
                    >
                      <option value="">None</option>
                      @for (cls of ciClasses(); track cls.id) {
                        <option [value]="cls.id">{{ cls.displayName }}</option>
                      }
                    </select>
                  </div>
                  <div class="form-group">
                    <label for="editMeasuringUnit">Measuring Unit</label>
                    <select
                      id="editMeasuringUnit"
                      [(ngModel)]="editForm.measuringUnit"
                      class="form-input form-select"
                    >
                      @for (u of measuringUnitOptions; track u.value) {
                        <option [value]="u.value">{{ u.label }}</option>
                      }
                    </select>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label for="editCategory">Category</label>
                    <input
                      id="editCategory"
                      [(ngModel)]="editForm.category"
                      class="form-input"
                    />
                  </div>
                  <div class="form-group">
                    <label for="editUnitCost">Unit Cost</label>
                    <input
                      id="editUnitCost"
                      type="number"
                      [(ngModel)]="editForm.unitCost"
                      class="form-input"
                      step="0.01"
                    />
                  </div>
                  <div class="form-group">
                    <label for="editCurrency">Currency</label>
                    <input
                      id="editCurrency"
                      [(ngModel)]="editForm.costCurrency"
                      class="form-input"
                    />
                  </div>
                </div>
                @if (editError()) {
                  <div class="form-error">{{ editError() }}</div>
                }
                <div class="form-actions">
                  <button
                    class="btn btn-primary"
                    [disabled]="!editForm.name || saving()"
                    (click)="submitEdit()"
                  >
                    {{ saving() ? 'Saving...' : 'Save Changes' }}
                  </button>
                  <button class="btn btn-secondary" (click)="editing = false">Cancel</button>
                </div>
              </div>
            </div>
          }

          <!-- Detail Card -->
          @if (!editing) {
            <div class="detail-card">
              <h2 class="section-title">Details</h2>
              <div class="detail-grid">
                <div class="detail-field">
                  <span class="field-label">Provider</span>
                  <span class="field-value">{{ providerDisplayName() }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">External SKU ID</span>
                  <span class="field-value"><code class="code-badge">{{ sku()!.externalSkuId }}</code></span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Name</span>
                  <span class="field-value">{{ sku()!.name }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Display Name</span>
                  <span class="field-value">{{ sku()!.displayName || '\u2014' }}</span>
                </div>
                <div class="detail-field detail-field-full">
                  <span class="field-label">Description</span>
                  <span class="field-value">{{ sku()!.description || '\u2014' }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">CI Class</span>
                  <span class="field-value">
                    @if (sku()!.ciClassId) {
                      <a class="link" (click)="goToCIClass(sku()!.ciClassId!)">{{ ciClassName() }}</a>
                    } @else {
                      \u2014
                    }
                  </span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Measuring Unit</span>
                  <span class="field-value">{{ unitLabel(sku()!.measuringUnit) }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Category</span>
                  <span class="field-value">{{ sku()!.category || '\u2014' }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Unit Cost</span>
                  <span class="field-value">
                    {{ sku()!.unitCost !== null ? (sku()!.unitCost! | number:'1.2-2') + ' ' + sku()!.costCurrency : '\u2014' }}
                  </span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Cost Currency</span>
                  <span class="field-value">{{ sku()!.costCurrency }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Semantic Type</span>
                  <span class="field-value">{{ sku()!.semanticTypeName || '\u2014' }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Resource Type</span>
                  <span class="field-value">
                    @if (sku()!.resourceType) {
                      <code class="code-badge">{{ sku()!.resourceType }}</code>
                    } @else {
                      \u2014
                    }
                  </span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Status</span>
                  <span class="field-value">
                    <span
                      class="badge"
                      [class.badge-active]="sku()!.isActive"
                      [class.badge-inactive]="!sku()!.isActive"
                    >
                      {{ sku()!.isActive ? 'Active' : 'Inactive' }}
                    </span>
                  </span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Created</span>
                  <span class="field-value">{{ sku()!.createdAt | date:'medium' }}</span>
                </div>
                <div class="detail-field">
                  <span class="field-label">Updated</span>
                  <span class="field-value">{{ sku()!.updatedAt | date:'medium' }}</span>
                </div>
              </div>
            </div>
          }

          <!-- Attributes Section -->
          <div class="detail-card">
            <div class="section-header">
              <h2 class="section-title">Attributes (JSON)</h2>
              <button
                *nimbusHasPermission="'catalog:sku:manage'"
                class="btn btn-sm"
                (click)="editingAttributes = !editingAttributes"
              >
                {{ editingAttributes ? 'Cancel' : 'Edit' }}
              </button>
            </div>
            @if (!editingAttributes) {
              <pre class="json-view">{{ attributesJson() }}</pre>
            }
            @if (editingAttributes) {
              <textarea
                class="form-input json-editor"
                [(ngModel)]="attributesText"
                rows="10"
                placeholder='{ "key": "value" }'
              ></textarea>
              @if (attributesError()) {
                <div class="form-error attr-error">{{ attributesError() }}</div>
              }
              <div class="form-actions">
                <button
                  class="btn btn-primary"
                  [disabled]="savingAttributes()"
                  (click)="saveAttributes()"
                >
                  {{ savingAttributes() ? 'Saving...' : 'Save Attributes' }}
                </button>
                <button class="btn btn-secondary" (click)="editingAttributes = false">Cancel</button>
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .sku-detail-page { padding: 0; max-width: 900px; }
    .loading { padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem; }
    .not-found { padding: 2rem; text-align: center; color: #64748b; }
    .not-found p { margin-bottom: 1rem; }

    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap;
    }
    .header-left { display: flex; align-items: flex-start; gap: 1rem; }
    .header-info { display: flex; flex-direction: column; gap: 0.375rem; }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .display-name {
      font-size: 0.875rem; font-weight: 400; color: #64748b; margin-left: 0.5rem;
    }
    .header-meta {
      display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
    }
    .meta-item { font-size: 0.8125rem; color: #64748b; font-weight: 500; }
    .header-actions { display: flex; gap: 0.5rem; align-items: center; }

    .detail-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.25rem;
    }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-title { margin: 0 0 1rem; font-size: 1rem; font-weight: 600; color: #1e293b; }
    .section-header .section-title { margin-bottom: 0; }

    .detail-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
    }
    .detail-field { display: flex; flex-direction: column; gap: 0.25rem; }
    .detail-field-full { grid-column: 1 / -1; }
    .field-label {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .field-value { font-size: 0.8125rem; color: #1e293b; }

    .link { color: #3b82f6; cursor: pointer; text-decoration: none; }
    .link:hover { text-decoration: underline; }

    .code-badge {
      padding: 0.125rem 0.375rem; background: #f1f5f9; border: 1px solid #e2e8f0;
      border-radius: 4px; font-size: 0.75rem; color: #475569; font-family: monospace;
    }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fee2e2; color: #dc2626; }

    .json-view {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1rem; font-size: 0.75rem; font-family: monospace;
      color: #374151; overflow-x: auto; white-space: pre-wrap;
      word-break: break-word; margin: 0;
    }
    .json-editor {
      width: 100%; font-family: monospace; font-size: 0.75rem;
      resize: vertical; min-height: 120px;
    }
    .attr-error { margin-top: 0.5rem; }

    .edit-form { display: flex; flex-direction: column; gap: 0; }
    .form-row { display: flex; gap: 0.75rem; }
    .form-row .form-group { flex: 1; }
    .form-group { margin-bottom: 1rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
    .form-textarea { resize: vertical; min-height: 48px; }
    .form-select { cursor: pointer; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-back {
      background: none; border: 1px solid #e2e8f0; color: #374151;
      padding: 0.375rem 0.75rem; font-size: 0.8125rem; white-space: nowrap;
    }
    .btn-back:hover { background: #f8fafc; }
    .btn-danger {
      background: #fff; color: #dc2626; padding: 0.5rem 1rem;
      border: 1px solid #fecaca;
    }
    .btn-danger:hover { background: #fef2f2; }
    .btn-success {
      background: #fff; color: #16a34a; padding: 0.5rem 1rem;
      border: 1px solid #bbf7d0;
    }
    .btn-success:hover { background: #f0fdf4; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; color: #374151; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
  `],
})
export class SkuDetailComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private cmdbService = inject(CmdbService);
  private semanticService = inject(SemanticService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  sku = signal<ProviderSku | null>(null);
  loading = signal(true);
  saving = signal(false);
  toggling = signal(false);
  editError = signal('');
  editing = false;
  providers = signal<SemanticProvider[]>([]);
  ciClasses = signal<CIClass[]>([]);

  editForm = {
    name: '',
    displayName: '',
    description: '',
    ciClassId: '',
    measuringUnit: 'month' as string,
    category: '',
    unitCost: null as number | null,
    costCurrency: 'EUR',
  };

  editingAttributes = false;
  attributesText = '';
  attributesError = signal('');
  savingAttributes = signal(false);

  readonly measuringUnitOptions = MEASURING_UNIT_OPTIONS;

  providerDisplayName = computed(() => {
    const s = this.sku();
    if (!s) return '';
    const p = this.providers().find((prov) => prov.id === s.providerId);
    return p ? p.displayName : s.providerId.substring(0, 8) + '...';
  });

  ciClassName = computed(() => {
    const s = this.sku();
    if (!s || !s.ciClassId) return '';
    const cls = this.ciClasses().find((c) => c.id === s.ciClassId);
    return cls ? cls.displayName : s.ciClassId.substring(0, 8) + '...';
  });

  attributesJson = computed(() => {
    const s = this.sku();
    if (!s || !s.attributes) return '{}';
    return JSON.stringify(s.attributes, null, 2);
  });

  private skuId: string | null = null;

  ngOnInit(): void {
    this.skuId = this.route.snapshot.paramMap.get('id') ?? null;
    this.loadProviders();
    this.loadCIClasses();
    if (this.skuId) {
      this.loadSku(this.skuId);
    } else {
      this.loading.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(['/catalog', 'skus']);
  }

  goToCIClass(ciClassId: string): void {
    this.router.navigate(['/cmdb', 'classes', ciClassId]);
  }

  unitLabel(unit: string): string {
    return MEASURING_UNIT_LABELS[unit as MeasuringUnit] || unit;
  }

  submitEdit(): void {
    if (!this.editForm.name || !this.skuId) return;
    this.saving.set(true);
    this.editError.set('');

    const input: Record<string, unknown> = {
      name: this.editForm.name,
      displayName: this.editForm.displayName || null,
      description: this.editForm.description || null,
      ciClassId: this.editForm.ciClassId || null,
      measuringUnit: this.editForm.measuringUnit,
      category: this.editForm.category || null,
      unitCost: this.editForm.unitCost,
      costCurrency: this.editForm.costCurrency || 'EUR',
    };

    this.catalogService.updateSku(this.skuId, input).subscribe({
      next: (updated) => {
        this.saving.set(false);
        this.sku.set(updated);
        this.editing = false;
        this.toastService.success(`SKU "${updated.name}" updated`);
      },
      error: (err) => {
        this.saving.set(false);
        const msg = err.message || 'Failed to update SKU';
        this.editError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  toggleActive(): void {
    if (!this.skuId || !this.sku()) return;
    this.toggling.set(true);

    if (this.sku()!.isActive) {
      this.catalogService.deactivateSku(this.skuId).subscribe({
        next: (updated) => {
          this.toggling.set(false);
          this.sku.set(updated);
          this.toastService.success('SKU deactivated');
        },
        error: (err) => {
          this.toggling.set(false);
          this.toastService.error(err.message || 'Failed to deactivate SKU');
        },
      });
    } else {
      // Reactivate by updating isActive to true
      this.catalogService.updateSku(this.skuId, { isActive: true }).subscribe({
        next: (updated) => {
          this.toggling.set(false);
          this.sku.set(updated);
          this.toastService.success('SKU reactivated');
        },
        error: (err) => {
          this.toggling.set(false);
          this.toastService.error(err.message || 'Failed to reactivate SKU');
        },
      });
    }
  }

  saveAttributes(): void {
    if (!this.skuId) return;
    this.savingAttributes.set(true);
    this.attributesError.set('');

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(this.attributesText);
    } catch {
      this.attributesError.set('Invalid JSON. Please check the syntax.');
      this.savingAttributes.set(false);
      return;
    }

    this.catalogService.updateSku(this.skuId, { attributes: parsed }).subscribe({
      next: (updated) => {
        this.savingAttributes.set(false);
        this.sku.set(updated);
        this.editingAttributes = false;
        this.toastService.success('Attributes saved');
      },
      error: (err) => {
        this.savingAttributes.set(false);
        const msg = err.message || 'Failed to save attributes';
        this.attributesError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private loadSku(id: string): void {
    this.catalogService.getSku(id).subscribe({
      next: (sku) => {
        this.loading.set(false);
        if (!sku) {
          this.toastService.error('Provider SKU not found');
          return;
        }
        this.sku.set(sku);
        this.populateEditForm(sku);
        this.attributesText = sku.attributes ? JSON.stringify(sku.attributes, null, 2) : '{}';
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load provider SKU');
      },
    });
  }

  private populateEditForm(sku: ProviderSku): void {
    this.editForm = {
      name: sku.name,
      displayName: sku.displayName || '',
      description: sku.description || '',
      ciClassId: sku.ciClassId || '',
      measuringUnit: sku.measuringUnit,
      category: sku.category || '',
      unitCost: sku.unitCost,
      costCurrency: sku.costCurrency,
    };
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => this.providers.set(providers),
    });
  }

  private loadCIClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => this.ciClasses.set(classes),
    });
  }
}
