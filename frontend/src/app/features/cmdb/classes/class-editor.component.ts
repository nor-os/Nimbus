/**
 * Overview: CI class schema editor — visual editor for CI class details and attribute definitions.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router,
 *     app/core/services/cmdb.service, app/shared/services/toast.service
 * Concepts: Inline editing of attribute definitions, process-editor-style two-section card layout.
 *     System classes are read-only. Custom classes support full CRUD on attribute definitions.
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
import { ActivatedRoute, Router } from '@angular/router';
import { CmdbService } from '@core/services/cmdb.service';
import { CIClassDetail, CIAttributeDefinition } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const DATA_TYPES = [
  'string', 'integer', 'float', 'boolean', 'date', 'datetime',
  'json', 'text', 'url', 'email', 'ip_address', 'enum',
];

@Component({
  selector: 'nimbus-class-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="class-editor-page">
        @if (loading()) {
          <div class="loading">Loading class...</div>
        }

        @if (!loading() && !ciClass()) {
          <div class="empty-state">Class not found.</div>
        }

        @if (!loading() && ciClass(); as cls) {
          <!-- Page header -->
          <div class="page-header">
            <div class="header-left">
              <button class="btn btn-secondary btn-sm" (click)="goBack()">
                &#8592; Back to Classes
              </button>
              <h1>{{ cls.displayName }}</h1>
              @if (cls.isSystem) {
                <span class="badge badge-system">System</span>
              }
            </div>
          </div>

          <!-- Details section -->
          <div class="section-card">
            <h2>Details</h2>
            <div class="detail-form">
              <div class="form-row">
                <div class="form-group">
                  <label>Identifier</label>
                  <input class="form-input mono" [value]="cls.name" disabled />
                </div>
                <div class="form-group">
                  <label>Display Name</label>
                  <input
                    class="form-input"
                    [(ngModel)]="editDisplayName"
                    [disabled]="cls.isSystem"
                    placeholder="Display name"
                  />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>Icon</label>
                  <input
                    class="form-input"
                    [(ngModel)]="editIcon"
                    [disabled]="cls.isSystem"
                    placeholder="e.g. server, database"
                  />
                </div>
                <div class="form-group">
                  <label>Active</label>
                  <label class="toggle-label">
                    <input
                      type="checkbox"
                      [(ngModel)]="editIsActive"
                      [disabled]="cls.isSystem"
                    />
                    <span>{{ editIsActive ? 'Active' : 'Inactive' }}</span>
                  </label>
                </div>
              </div>
              @if (!cls.isSystem) {
                <div class="form-actions">
                  <button
                    class="btn btn-primary"
                    [disabled]="savingDetails()"
                    (click)="saveDetails()"
                    *nimbusHasPermission="'cmdb:class:manage'"
                  >
                    {{ savingDetails() ? 'Saving...' : 'Save Changes' }}
                  </button>
                </div>
              }
            </div>
          </div>

          <!-- Attribute Definitions section -->
          <div class="section-card">
            <div class="section-header">
              <h2>Attribute Definitions ({{ sortedAttrs().length }})</h2>
              @if (!cls.isSystem) {
                <button
                  class="btn btn-link"
                  (click)="showAddAttr.set(!showAddAttr())"
                  *nimbusHasPermission="'cmdb:class:manage'"
                >
                  {{ showAddAttr() ? 'Cancel' : '+ Add Attribute' }}
                </button>
              }
            </div>

            <!-- Add attribute form -->
            @if (showAddAttr()) {
              <div class="add-attr-form">
                <div class="form-row">
                  <div class="form-group add-field">
                    <label>Name *</label>
                    <input
                      class="form-input mono"
                      [(ngModel)]="newAttrName"
                      placeholder="snake_case"
                    />
                  </div>
                  <div class="form-group add-field">
                    <label>Display Name *</label>
                    <input
                      class="form-input"
                      [(ngModel)]="newAttrDisplayName"
                      placeholder="Human-readable"
                    />
                  </div>
                  <div class="form-group add-field-sm">
                    <label>Data Type *</label>
                    <select class="form-input form-select" [(ngModel)]="newAttrDataType">
                      @for (dt of dataTypes; track dt) {
                        <option [value]="dt">{{ dt }}</option>
                      }
                    </select>
                  </div>
                  <div class="form-group add-field-sm">
                    <label>Required</label>
                    <label class="toggle-label">
                      <input type="checkbox" [(ngModel)]="newAttrRequired" />
                      <span>{{ newAttrRequired ? 'Yes' : 'No' }}</span>
                    </label>
                  </div>
                  <div class="form-group add-field-sm">
                    <label>Sort Order</label>
                    <input
                      type="number"
                      class="form-input"
                      [(ngModel)]="newAttrSortOrder"
                    />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group add-field">
                    <label>Default Value (JSON)</label>
                    <input
                      class="form-input mono"
                      [(ngModel)]="newAttrDefault"
                      placeholder='e.g. "value" or 42 or null'
                    />
                  </div>
                  <div class="form-group add-field">
                    <label>Validation Rules (JSON)</label>
                    <input
                      class="form-input mono"
                      [(ngModel)]="newAttrValidation"
                      placeholder='e.g. {"min": 0, "max": 100}'
                    />
                  </div>
                </div>
                @if (addAttrError()) {
                  <div class="form-error">{{ addAttrError() }}</div>
                }
                <div class="form-actions">
                  <button
                    class="btn btn-primary"
                    [disabled]="addingAttr() || !newAttrName || !newAttrDisplayName"
                    (click)="addAttribute()"
                  >
                    {{ addingAttr() ? 'Adding...' : 'Add Attribute' }}
                  </button>
                  <button
                    class="btn btn-secondary"
                    (click)="cancelAddAttr()"
                  >Cancel</button>
                </div>
              </div>
            }

            <!-- Attribute table -->
            @if (sortedAttrs().length > 0) {
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th class="col-order">#</th>
                      <th>Name</th>
                      <th>Display Name</th>
                      <th>Data Type</th>
                      <th>Required</th>
                      <th>Default</th>
                      <th>Validation</th>
                      @if (!cls.isSystem) {
                        <th class="col-actions">Actions</th>
                      }
                    </tr>
                  </thead>
                  <tbody>
                    @for (attr of sortedAttrs(); track attr.id) {
                      @if (editingAttrId() === attr.id) {
                        <!-- Inline edit row -->
                        <tr class="edit-row">
                          <td>
                            <input
                              type="number"
                              class="form-input form-input-sm"
                              [(ngModel)]="editAttrSortOrder"
                            />
                          </td>
                          <td class="mono">{{ attr.name }}</td>
                          <td>
                            <input
                              class="form-input form-input-sm"
                              [(ngModel)]="editAttrDisplayName"
                            />
                          </td>
                          <td>
                            <select class="form-input form-input-sm form-select" [(ngModel)]="editAttrDataType">
                              @for (dt of dataTypes; track dt) {
                                <option [value]="dt">{{ dt }}</option>
                              }
                            </select>
                          </td>
                          <td>
                            <label class="toggle-label">
                              <input type="checkbox" [(ngModel)]="editAttrRequired" />
                            </label>
                          </td>
                          <td>
                            <input
                              class="form-input form-input-sm mono"
                              [(ngModel)]="editAttrDefault"
                            />
                          </td>
                          <td>
                            <input
                              class="form-input form-input-sm mono"
                              [(ngModel)]="editAttrValidation"
                            />
                          </td>
                          <td class="col-actions">
                            <button
                              class="btn btn-primary btn-xs"
                              [disabled]="savingAttr()"
                              (click)="saveAttribute(attr)"
                            >Save</button>
                            <button
                              class="btn btn-secondary btn-xs"
                              (click)="cancelEditAttr()"
                            >Cancel</button>
                          </td>
                        </tr>
                      } @else {
                        <!-- Display row -->
                        <tr>
                          <td class="col-order">{{ attr.sortOrder }}</td>
                          <td class="mono">{{ attr.name }}</td>
                          <td>{{ attr.displayName }}</td>
                          <td><span class="badge badge-type">{{ attr.dataType }}</span></td>
                          <td>
                            <span [class]="attr.isRequired ? 'badge badge-required' : 'badge badge-optional'">
                              {{ attr.isRequired ? 'Required' : 'Optional' }}
                            </span>
                          </td>
                          <td class="mono cell-truncate">{{ formatJson(attr.defaultValue) }}</td>
                          <td class="mono cell-truncate">{{ formatJson(attr.validationRules) }}</td>
                          @if (!cls.isSystem) {
                            <td class="col-actions">
                              <button
                                class="btn btn-secondary btn-xs"
                                (click)="startEditAttr(attr)"
                                *nimbusHasPermission="'cmdb:class:manage'"
                              >Edit</button>
                              <button
                                class="btn btn-delete btn-xs"
                                (click)="confirmRemoveAttr(attr)"
                                *nimbusHasPermission="'cmdb:class:manage'"
                              >Remove</button>
                            </td>
                          }
                        </tr>
                      }
                    }
                  </tbody>
                </table>
              </div>
            } @else if (!showAddAttr()) {
              <div class="empty-attrs">
                No attribute definitions yet.
                @if (!cls.isSystem) {
                  Click "+ Add Attribute" to define custom fields.
                }
              </div>
            }
          </div>

          <!-- Delete confirmation overlay -->
          @if (confirmDeleteAttr()) {
            <div class="confirm-overlay" (click)="confirmDeleteAttr.set(null)">
              <div class="confirm-dialog" (click)="$event.stopPropagation()">
                <h3>Remove Attribute</h3>
                <p>
                  Are you sure you want to remove the attribute
                  <strong>{{ confirmDeleteAttr()!.name }}</strong>?
                  This will soft-delete it.
                </p>
                <div class="confirm-actions">
                  <button
                    class="btn btn-delete"
                    [disabled]="removingAttr()"
                    (click)="removeAttribute()"
                  >
                    {{ removingAttr() ? 'Removing...' : 'Remove' }}
                  </button>
                  <button
                    class="btn btn-secondary"
                    (click)="confirmDeleteAttr.set(null)"
                  >Cancel</button>
                </div>
              </div>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .class-editor-page { padding: 0; }

    .loading, .empty-state {
      padding: 3rem; text-align: center; color: #64748b; font-size: 0.875rem;
    }

    /* ── Page header ─────────────────────────────────────────────── */
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 0.75rem; }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    /* ── Section cards ───────────────────────────────────────────── */
    .section-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .section-card h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
    }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-header h2 { margin-bottom: 0; }

    /* ── Form layout ─────────────────────────────────────────────── */
    .form-row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .form-row .form-group { flex: 1; min-width: 200px; }
    .form-group { margin-bottom: 0.75rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.75rem;
      font-weight: 600; color: #64748b; text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s; background: #fff;
      color: #1e293b;
    }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .form-input-sm { padding: 0.375rem 0.5rem; font-size: 0.75rem; }
    .form-select { cursor: pointer; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .toggle-label {
      display: inline-flex; align-items: center; gap: 0.5rem;
      font-size: 0.8125rem; color: #1e293b; cursor: pointer;
      padding-top: 0.25rem;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.5rem 0.75rem;
      border-radius: 6px; margin-bottom: 0.75rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }

    /* ── Add attr form fields ────────────────────────────────────── */
    .add-attr-form {
      background: #fafbfc; border: 1px solid #f1f5f9; border-radius: 6px;
      padding: 1rem; margin-bottom: 1rem;
    }
    .add-field { min-width: 180px; }
    .add-field-sm { min-width: 100px; max-width: 140px; flex: 0 0 auto; }

    /* ── Buttons ─────────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none; white-space: nowrap;
    }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-xs { padding: 0.25rem 0.5rem; font-size: 0.6875rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-link {
      background: none; color: #3b82f6; padding: 0.25rem 0.5rem;
      font-weight: 500; border: none;
    }
    .btn-link:hover { text-decoration: underline; }
    .btn-delete { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .btn-delete:hover { background: #fee2e2; }
    .btn-delete:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Table ────────────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em; background: #fafbfc;
    }
    .table tbody tr:last-child td { border-bottom: none; }
    .table tbody tr:hover { background: #f8fafc; }
    .table tbody tr.edit-row { background: #eff6ff; }
    .col-order { width: 50px; text-align: center; }
    .col-actions { width: 140px; }
    .col-actions .btn + .btn { margin-left: 0.375rem; }
    .cell-truncate { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .empty-attrs {
      padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* ── Badges ───────────────────────────────────────────────────── */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; line-height: 1.5;
    }
    .badge-system { background: #dbeafe; color: #1d4ed8; }
    .badge-type { background: #f1f5f9; color: #64748b; }
    .badge-required { background: #fef2f2; color: #dc2626; }
    .badge-optional { background: #f1f5f9; color: #64748b; }

    /* ── Confirm dialog overlay ──────────────────────────────────── */
    .confirm-overlay {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.3);
      display: flex; justify-content: center; align-items: center; z-index: 1000;
    }
    .confirm-dialog {
      background: #fff; border-radius: 8px; padding: 1.5rem;
      max-width: 400px; width: 90%; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
    }
    .confirm-dialog h3 {
      font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem;
    }
    .confirm-dialog p {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 1.25rem; line-height: 1.5;
    }
    .confirm-actions { display: flex; gap: 0.75rem; }
  `],
})
export class ClassEditorComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  loading = signal(false);
  ciClass = signal<CIClassDetail | null>(null);
  savingDetails = signal(false);
  showAddAttr = signal(false);
  addingAttr = signal(false);
  addAttrError = signal('');
  editingAttrId = signal<string | null>(null);
  savingAttr = signal(false);
  confirmDeleteAttr = signal<CIAttributeDefinition | null>(null);
  removingAttr = signal(false);

  dataTypes = DATA_TYPES;

  // Detail editing fields
  editDisplayName = '';
  editIcon = '';
  editIsActive = true;

  // Add attribute fields
  newAttrName = '';
  newAttrDisplayName = '';
  newAttrDataType = 'string';
  newAttrRequired = false;
  newAttrSortOrder = 0;
  newAttrDefault = '';
  newAttrValidation = '';

  // Inline edit attribute fields
  editAttrDisplayName = '';
  editAttrDataType = 'string';
  editAttrRequired = false;
  editAttrSortOrder = 0;
  editAttrDefault = '';
  editAttrValidation = '';

  sortedAttrs = computed(() => {
    const cls = this.ciClass();
    if (!cls) return [];
    return [...cls.attributeDefinitions].sort((a, b) => a.sortOrder - b.sortOrder);
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadClass(id);
    }
  }

  goBack(): void {
    this.router.navigate(['/cmdb/classes']);
  }

  saveDetails(): void {
    const cls = this.ciClass();
    if (!cls) return;
    this.savingDetails.set(true);
    this.cmdbService.updateClass(cls.id, {
      displayName: this.editDisplayName,
      icon: this.editIcon || null,
      isActive: this.editIsActive,
    }).subscribe({
      next: (updated) => {
        this.savingDetails.set(false);
        this.ciClass.set(updated);
        this.toastService.success('Class details saved');
      },
      error: (err) => {
        this.savingDetails.set(false);
        this.toastService.error(err.message || 'Failed to save');
      },
    });
  }

  // ── Add attribute ──────────────────────────────────────────────

  addAttribute(): void {
    const cls = this.ciClass();
    if (!cls || !this.newAttrName || !this.newAttrDisplayName) return;

    // Validate name format
    if (!/^[a-z][a-z0-9_]*$/.test(this.newAttrName)) {
      this.addAttrError.set('Name must be lowercase snake_case (a-z, 0-9, underscores)');
      return;
    }

    const defaultValue = this.parseJsonField(this.newAttrDefault);
    if (defaultValue === undefined) {
      this.addAttrError.set('Invalid JSON in Default Value');
      return;
    }
    const validationRules = this.parseJsonField(this.newAttrValidation);
    if (validationRules === undefined) {
      this.addAttrError.set('Invalid JSON in Validation Rules');
      return;
    }

    this.addingAttr.set(true);
    this.addAttrError.set('');

    this.cmdbService.addAttributeDefinition(cls.id, {
      name: this.newAttrName,
      displayName: this.newAttrDisplayName,
      dataType: this.newAttrDataType,
      isRequired: this.newAttrRequired,
      defaultValue: defaultValue,
      validationRules: validationRules as Record<string, unknown> | null,
      sortOrder: this.newAttrSortOrder,
    }).subscribe({
      next: (updated) => {
        this.addingAttr.set(false);
        this.ciClass.set(updated);
        this.resetAddForm();
        this.showAddAttr.set(false);
        this.toastService.success('Attribute added');
      },
      error: (err) => {
        this.addingAttr.set(false);
        this.addAttrError.set(err.message || 'Failed to add attribute');
      },
    });
  }

  cancelAddAttr(): void {
    this.showAddAttr.set(false);
    this.resetAddForm();
  }

  // ── Inline edit attribute ──────────────────────────────────────

  startEditAttr(attr: CIAttributeDefinition): void {
    this.editingAttrId.set(attr.id);
    this.editAttrDisplayName = attr.displayName;
    this.editAttrDataType = attr.dataType;
    this.editAttrRequired = attr.isRequired;
    this.editAttrSortOrder = attr.sortOrder;
    this.editAttrDefault = attr.defaultValue != null ? JSON.stringify(attr.defaultValue) : '';
    this.editAttrValidation = attr.validationRules != null ? JSON.stringify(attr.validationRules) : '';
  }

  cancelEditAttr(): void {
    this.editingAttrId.set(null);
  }

  saveAttribute(attr: CIAttributeDefinition): void {
    const cls = this.ciClass();
    if (!cls) return;

    const defaultValue = this.parseJsonField(this.editAttrDefault);
    if (defaultValue === undefined) {
      this.toastService.error('Invalid JSON in Default Value');
      return;
    }
    const validationRules = this.parseJsonField(this.editAttrValidation);
    if (validationRules === undefined) {
      this.toastService.error('Invalid JSON in Validation Rules');
      return;
    }

    this.savingAttr.set(true);
    this.cmdbService.updateAttributeDefinition(cls.id, attr.id, {
      displayName: this.editAttrDisplayName,
      dataType: this.editAttrDataType,
      isRequired: this.editAttrRequired,
      defaultValue: defaultValue,
      validationRules: validationRules as Record<string, unknown> | null,
      sortOrder: this.editAttrSortOrder,
    }).subscribe({
      next: (updated) => {
        this.savingAttr.set(false);
        this.ciClass.set(updated);
        this.editingAttrId.set(null);
        this.toastService.success('Attribute updated');
      },
      error: (err) => {
        this.savingAttr.set(false);
        this.toastService.error(err.message || 'Failed to update attribute');
      },
    });
  }

  // ── Remove attribute ───────────────────────────────────────────

  confirmRemoveAttr(attr: CIAttributeDefinition): void {
    this.confirmDeleteAttr.set(attr);
  }

  removeAttribute(): void {
    const cls = this.ciClass();
    const attr = this.confirmDeleteAttr();
    if (!cls || !attr) return;

    this.removingAttr.set(true);
    this.cmdbService.removeAttributeDefinition(cls.id, attr.id).subscribe({
      next: (updated) => {
        this.removingAttr.set(false);
        this.ciClass.set(updated);
        this.confirmDeleteAttr.set(null);
        this.toastService.success('Attribute removed');
      },
      error: (err) => {
        this.removingAttr.set(false);
        this.toastService.error(err.message || 'Failed to remove attribute');
      },
    });
  }

  // ── Helpers ────────────────────────────────────────────────────

  formatJson(value: unknown): string {
    if (value == null) return '\u2014';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  private loadClass(id: string): void {
    this.loading.set(true);
    this.cmdbService.getClass(id).subscribe({
      next: (cls) => {
        this.loading.set(false);
        this.ciClass.set(cls);
        if (cls) {
          this.editDisplayName = cls.displayName;
          this.editIcon = cls.icon || '';
          this.editIsActive = cls.isActive;
          // Set next sort order for new attrs
          const maxOrder = cls.attributeDefinitions.reduce(
            (max, a) => Math.max(max, a.sortOrder), -1
          );
          this.newAttrSortOrder = maxOrder + 1;
        }
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load class');
      },
    });
  }

  private resetAddForm(): void {
    this.newAttrName = '';
    this.newAttrDisplayName = '';
    this.newAttrDataType = 'string';
    this.newAttrRequired = false;
    this.newAttrDefault = '';
    this.newAttrValidation = '';
    this.addAttrError.set('');
    // Auto-increment sort order
    const cls = this.ciClass();
    if (cls) {
      const maxOrder = cls.attributeDefinitions.reduce(
        (max, a) => Math.max(max, a.sortOrder), -1
      );
      this.newAttrSortOrder = maxOrder + 1;
    }
  }

  /**
   * Parse a JSON string from an input field.
   * Returns null for empty string, parsed value for valid JSON,
   * or undefined to indicate a parse error.
   */
  private parseJsonField(raw: string): unknown | undefined {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed);
    } catch {
      return undefined;
    }
  }
}
