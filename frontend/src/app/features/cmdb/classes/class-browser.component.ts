/**
 * Overview: CI class browser — view and manage CI class hierarchy.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, app/core/services/cmdb.service
 * Concepts: CI class hierarchy, system vs custom classes, schema viewer
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
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CmdbService } from '@core/services/cmdb.service';
import { CIClass, CIClassDetail } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { PropertySchemaEditorComponent, PropertyDefRow } from '@shared/components/property-schema-editor/property-schema-editor.component';

/** Internal tree node for hierarchy rendering. */
interface ClassTreeNode {
  cls: CIClass;
  children: ClassTreeNode[];
  depth: number;
}

@Component({
  selector: 'nimbus-class-browser',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent, HasPermissionDirective, PropertySchemaEditorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="class-browser-page">
        <div class="page-header">
          <h1>CI Class Hierarchy</h1>
          <button
            *nimbusHasPermission="'cmdb:class:create'"
            class="btn btn-primary"
            (click)="showCreateForm.set(!showCreateForm())"
          >
            {{ showCreateForm() ? 'Cancel' : 'Create Custom Class' }}
          </button>
        </div>

        <!-- Create class form -->
        @if (showCreateForm()) {
          <div class="create-form-card">
            <h2>New Custom Class</h2>
            <form [formGroup]="createForm" (ngSubmit)="onCreateSubmit()" class="create-form">
              <div class="form-row">
                <div class="form-group">
                  <label for="className">Name *</label>
                  <input
                    id="className"
                    formControlName="name"
                    class="form-input"
                    placeholder="snake_case identifier"
                  />
                  @if (createForm.get('name')?.hasError('required') && createForm.get('name')?.touched) {
                    <span class="error">Name is required</span>
                  }
                  @if (createForm.get('name')?.hasError('pattern') && createForm.get('name')?.touched) {
                    <span class="error">Must be lowercase snake_case (a-z, 0-9, underscores)</span>
                  }
                </div>
                <div class="form-group">
                  <label for="classDisplayName">Display Name *</label>
                  <input
                    id="classDisplayName"
                    formControlName="displayName"
                    class="form-input"
                    placeholder="Human-readable name"
                  />
                  @if (createForm.get('displayName')?.hasError('required') && createForm.get('displayName')?.touched) {
                    <span class="error">Display name is required</span>
                  }
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label for="parentClassId">Parent Class</label>
                  <select
                    id="parentClassId"
                    formControlName="parentClassId"
                    class="form-input form-select"
                  >
                    <option value="">None (root class)</option>
                    @for (cls of allClasses(); track cls.id) {
                      <option [value]="cls.id">{{ cls.displayName }}</option>
                    }
                  </select>
                </div>
                <div class="form-group">
                  <label for="classIcon">Icon</label>
                  <input
                    id="classIcon"
                    formControlName="icon"
                    class="form-input"
                    placeholder="e.g. server, database, network"
                  />
                </div>
              </div>
              <div class="form-group">
                <label>Schema</label>
                <nimbus-property-schema-editor
                  [value]="schemaEditorRows"
                  (valueChange)="onSchemaEditorChange($event)"
                  [showValidation]="true"
                />
                @if (schemaError()) {
                  <span class="error">{{ schemaError() }}</span>
                }
              </div>
              @if (createError()) {
                <div class="form-error">{{ createError() }}</div>
              }
              <div class="form-actions">
                <button
                  type="submit"
                  class="btn btn-primary"
                  [disabled]="createForm.invalid || creating()"
                >
                  {{ creating() ? 'Creating...' : 'Create Class' }}
                </button>
                <button
                  type="button"
                  class="btn btn-secondary"
                  (click)="showCreateForm.set(false)"
                >Cancel</button>
              </div>
            </form>
          </div>
        }

        <!-- Class tree -->
        @if (loading()) {
          <div class="loading">Loading classes...</div>
        }

        @if (!loading() && classTree().length === 0) {
          <div class="empty-state">No CI classes found.</div>
        }

        @if (!loading() && classTree().length > 0) {
          <div class="class-tree">
            @for (node of flatTree(); track node.cls.id) {
              <div
                class="class-node"
                [class.selected]="selectedClassId() === node.cls.id"
                [style.padding-left]="(node.depth * 1.5 + 1) + 'rem'"
                (click)="selectClass(node.cls)"
              >
                <span class="node-icon">
                  @if (node.children.length > 0) {
                    <span class="has-children-indicator">&#9656;</span>
                  }
                  @if (node.cls.icon) {
                    <span class="class-icon-label">{{ node.cls.icon }}</span>
                  }
                </span>
                <span class="node-name">{{ node.cls.displayName }}</span>
                <span class="node-identifier">({{ node.cls.name }})</span>
                @if (node.cls.isSystem) {
                  <span class="badge badge-system">System</span>
                }
                @if (!node.cls.isActive) {
                  <span class="badge badge-inactive">Inactive</span>
                }
                @if (!node.cls.isSystem) {
                  <span class="node-spacer"></span>
                  <button
                    class="btn-icon btn-icon-delete"
                    title="Delete class"
                    (click)="confirmDeleteClass($event, node.cls)"
                    *nimbusHasPermission="'cmdb:class:manage'"
                  >&#10005;</button>
                }
              </div>
            }
          </div>
        }

        <!-- Delete class confirmation overlay -->
        @if (classToDelete()) {
          <div class="confirm-overlay" (click)="classToDelete.set(null)">
            <div class="confirm-dialog" (click)="$event.stopPropagation()">
              <h3>Delete Class</h3>
              <p>
                Are you sure you want to delete the class
                <strong>{{ classToDelete()!.displayName }}</strong>?
                This will soft-delete it and all its attribute definitions.
              </p>
              <div class="confirm-actions">
                <button
                  class="btn btn-delete"
                  [disabled]="deleting()"
                  (click)="deleteClass()"
                >
                  {{ deleting() ? 'Deleting...' : 'Delete' }}
                </button>
                <button
                  class="btn btn-secondary"
                  (click)="classToDelete.set(null)"
                >Cancel</button>
              </div>
            </div>
          </div>
        }

        <!-- Schema viewer panel -->
        @if (selectedDetail(); as detail) {
          <div class="detail-panel">
            <div class="detail-header">
              <h2>{{ detail.displayName }}</h2>
              @if (detail.isSystem) {
                <span class="badge badge-system">System</span>
              }
            </div>

            <div class="detail-meta">
              <div class="meta-row">
                <span class="meta-label">Identifier</span>
                <span class="meta-value mono">{{ detail.name }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">Parent</span>
                <span class="meta-value">{{ parentClassName(detail.parentClassId) }}</span>
              </div>
              @if (detail.icon) {
                <div class="meta-row">
                  <span class="meta-label">Icon</span>
                  <span class="meta-value">{{ detail.icon }}</span>
                </div>
              }
              @if (detail.semanticTypeId) {
                <div class="meta-row">
                  <span class="meta-label">Semantic Type ID</span>
                  <span class="meta-value mono">{{ detail.semanticTypeId }}</span>
                </div>
              }
              <div class="meta-row">
                <span class="meta-label">Active</span>
                <span class="meta-value">{{ detail.isActive ? 'Yes' : 'No' }}</span>
              </div>
            </div>

            @if (detail.attributeDefinitions.length > 0) {
              <h3>Attribute Definitions ({{ detail.attributeDefinitions.length }})</h3>
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Display Name</th>
                      <th>Data Type</th>
                      <th>Required</th>
                      <th>Default</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (attr of detail.attributeDefinitions; track attr.id) {
                      <tr>
                        <td class="mono">{{ attr.name }}</td>
                        <td>{{ attr.displayName }}</td>
                        <td>
                          <span class="badge badge-type">{{ attr.dataType }}</span>
                        </td>
                        <td>{{ attr.isRequired ? 'Yes' : 'No' }}</td>
                        <td class="mono">{{ attr.defaultValue != null ? attr.defaultValue : '\u2014' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }

            @if (detail.schemaDef) {
              <h3>Schema Definition</h3>
              <div class="schema-viewer">
                @if (schemaDefEntries(detail.schemaDef); as entries) {
                  @if (entries.length > 0) {
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Property</th>
                          <th>Type</th>
                          <th>Required</th>
                          <th>Default</th>
                          <th>Unit</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (entry of entries; track entry.name) {
                          <tr>
                            <td class="mono">{{ entry.name }}</td>
                            <td><span class="badge badge-type">{{ entry.type }}</span></td>
                            <td>{{ entry.required ? 'Yes' : 'No' }}</td>
                            <td class="mono">{{ entry.defaultVal ?? '\u2014' }}</td>
                            <td>{{ entry.unit ?? '\u2014' }}</td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else {
                    <pre class="schema-json">{{ detail.schemaDef | json }}</pre>
                  }
                }
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .class-browser-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading, .empty-state {
      padding: 3rem; text-align: center; color: #64748b; font-size: 0.875rem;
    }

    /* ── Create form ─────────────────────────────────────────────── */
    .create-form-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .create-form-card h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
    }
    .form-row {
      display: flex; gap: 1rem; flex-wrap: wrap;
    }
    .form-row .form-group { flex: 1; min-width: 240px; }
    .form-group { margin-bottom: 1rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }
    .form-textarea { resize: vertical; min-height: 80px; }
    .form-select { cursor: pointer; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }

    /* ── Class tree ──────────────────────────────────────────────── */
    .class-tree {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      overflow: hidden; margin-bottom: 1.5rem;
    }
    .class-node {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.625rem 1rem; cursor: pointer; font-size: 0.8125rem;
      border-bottom: 1px solid #f1f5f9; transition: background 0.1s;
    }
    .class-node:last-child { border-bottom: none; }
    .class-node:hover { background: #f8fafc; }
    .class-node.selected { background: #eff6ff; border-left: 3px solid #3b82f6; }
    .node-icon {
      display: flex; align-items: center; gap: 0.25rem; min-width: 40px;
      color: #94a3b8; flex-shrink: 0;
    }
    .has-children-indicator { font-size: 0.625rem; color: #94a3b8; }
    .class-icon-label { font-size: 0.6875rem; color: #64748b; }
    .node-name { font-weight: 500; color: #1e293b; }
    .node-identifier { color: #94a3b8; font-size: 0.75rem; }

    .badge {
      padding: 0.0625rem 0.375rem; border-radius: 12px; font-size: 0.625rem;
      font-weight: 600; display: inline-block; line-height: 1.5;
    }
    .badge-system { background: #dbeafe; color: #1d4ed8; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }
    .badge-type { background: #f1f5f9; color: #64748b; }
    .node-spacer { flex: 1; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.125rem 0.375rem;
      border-radius: 4px; font-size: 0.75rem; line-height: 1; transition: background 0.15s;
    }
    .btn-icon-delete { color: #dc2626; }
    .btn-icon-delete:hover { background: #fef2f2; }
    .btn-delete {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
    }
    .btn-delete:hover { background: #fee2e2; }
    .btn-delete:disabled { opacity: 0.5; cursor: not-allowed; }

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

    /* ── Detail panel ────────────────────────────────────────────── */
    .detail-panel {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; margin-bottom: 1.5rem;
    }
    .detail-header {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;
    }
    .detail-header h2 {
      font-size: 1.125rem; font-weight: 600; color: #1e293b; margin: 0;
    }
    .detail-meta {
      background: #fafbfc; border: 1px solid #f1f5f9; border-radius: 6px;
      padding: 1rem; margin-bottom: 1.25rem;
    }
    .meta-row {
      display: flex; gap: 1rem; padding: 0.25rem 0; font-size: 0.8125rem;
    }
    .meta-label { font-weight: 600; color: #64748b; min-width: 130px; flex-shrink: 0; }
    .meta-value { color: #1e293b; word-break: break-all; }

    .detail-panel h3 {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b;
      margin: 1.25rem 0 0.75rem; padding-bottom: 0.375rem;
      border-bottom: 1px solid #e2e8f0;
    }

    .table-container {
      overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1rem;
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

    .schema-viewer {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem;
      overflow-x: auto;
    }
    .schema-json {
      color: #374151; font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 0.75rem; line-height: 1.6; margin: 0; white-space: pre-wrap;
      word-break: break-word;
    }
  `],
})
export class ClassBrowserComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private toastService = inject(ToastService);

  allClasses = signal<CIClass[]>([]);
  loading = signal(false);
  selectedClassId = signal<string | null>(null);
  selectedDetail = signal<CIClassDetail | null>(null);
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal('');
  schemaError = signal('');
  classToDelete = signal<CIClass | null>(null);
  deleting = signal(false);

  /** Build hierarchical tree from flat class list. */
  classTree = computed<ClassTreeNode[]>(() => {
    const classes = this.allClasses();
    const map = new Map<string, ClassTreeNode>();
    const roots: ClassTreeNode[] = [];

    // Create nodes
    for (const cls of classes) {
      map.set(cls.id, { cls, children: [], depth: 0 });
    }

    // Link parents
    for (const cls of classes) {
      const node = map.get(cls.id)!;
      if (cls.parentClassId && map.has(cls.parentClassId)) {
        map.get(cls.parentClassId)!.children.push(node);
      } else {
        roots.push(node);
      }
    }

    // Sort children by displayName
    const sortChildren = (nodes: ClassTreeNode[]): void => {
      nodes.sort((a, b) => a.cls.displayName.localeCompare(b.cls.displayName));
      for (const node of nodes) {
        sortChildren(node.children);
      }
    };
    sortChildren(roots);

    return roots;
  });

  /** Flatten the tree for rendering, assigning depth. */
  flatTree = computed<ClassTreeNode[]>(() => {
    const result: ClassTreeNode[] = [];
    const walk = (nodes: ClassTreeNode[], depth: number): void => {
      for (const node of nodes) {
        result.push({ ...node, depth });
        walk(node.children, depth + 1);
      }
    };
    walk(this.classTree(), 0);
    return result;
  });

  schemaEditorRows: PropertyDefRow[] = [];

  createForm = this.fb.group({
    name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9_]*$/)]],
    displayName: ['', [Validators.required]],
    parentClassId: [''],
    icon: [''],
  });

  ngOnInit(): void {
    this.loadClasses();
  }

  selectClass(cls: CIClass): void {
    // Custom classes → navigate to class editor
    if (!cls.isSystem) {
      this.router.navigate(['/cmdb/classes', cls.id]);
      return;
    }

    // System classes → inline detail panel
    if (this.selectedClassId() === cls.id) {
      this.selectedClassId.set(null);
      this.selectedDetail.set(null);
      return;
    }
    this.selectedClassId.set(cls.id);
    this.selectedDetail.set(null);
    this.cmdbService.getClass(cls.id).subscribe({
      next: (detail) => this.selectedDetail.set(detail),
      error: () => this.toastService.error('Failed to load class detail'),
    });
  }

  parentClassName(parentId: string | null): string {
    if (!parentId) return '\u2014 (root)';
    const found = this.allClasses().find((c) => c.id === parentId);
    return found ? found.displayName : parentId;
  }

  onSchemaEditorChange(rows: PropertyDefRow[]): void {
    this.schemaEditorRows = rows;
  }

  /** Convert a schema definition to a flat table of entries for display. */
  schemaDefEntries(schemaDef: Record<string, unknown>): Array<{ name: string; type: string; required: boolean; defaultVal: string | null; unit: string | null }> {
    if (!schemaDef) return [];
    // Handle dict format: { "cpu": { "type": "integer" }, ... }
    if (typeof schemaDef === 'object' && !Array.isArray(schemaDef)) {
      // Check if it has a "properties" key (JSON Schema-style)
      const props = (schemaDef['properties'] ?? schemaDef) as Record<string, unknown>;
      return Object.entries(props).map(([key, val]) => {
        const v = (val && typeof val === 'object' ? val : {}) as Record<string, unknown>;
        return {
          name: key,
          type: String(v['type'] || v['data_type'] || 'string'),
          required: Boolean(v['required']),
          defaultVal: v['default'] != null ? String(v['default']) : (v['default_value'] != null ? String(v['default_value']) : null),
          unit: v['unit'] ? String(v['unit']) : null,
        };
      });
    }
    return [];
  }

  onCreateSubmit(): void {
    if (this.createForm.invalid) return;

    // Build schema from visual editor rows
    let schemaDef: Record<string, unknown> | null = null;
    if (this.schemaEditorRows.length > 0) {
      const properties: Record<string, unknown> = {};
      for (const row of this.schemaEditorRows) {
        if (!row.name) continue;
        const entry: Record<string, unknown> = { type: row.data_type };
        if (row.required) entry['required'] = true;
        if (row.default_value) entry['default'] = row.default_value;
        if (row.unit) entry['unit'] = row.unit;
        if (row.description) entry['description'] = row.description;
        properties[row.name] = entry;
      }
      schemaDef = { properties };
    }

    this.creating.set(true);
    this.createError.set('');
    this.schemaError.set('');

    const values = this.createForm.value;

    this.cmdbService.createClass({
      name: values.name!,
      displayName: values.displayName!,
      parentClassId: values.parentClassId || null,
      icon: values.icon || null,
      schemaDef,
    }).subscribe({
      next: (created) => {
        this.creating.set(false);
        this.toastService.success(`Class "${created.displayName}" created`);
        this.showCreateForm.set(false);
        this.createForm.reset();
        this.loadClasses();
      },
      error: (err) => {
        this.creating.set(false);
        const msg = err.message || 'Failed to create class';
        this.createError.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  confirmDeleteClass(event: Event, cls: CIClass): void {
    event.stopPropagation();
    this.classToDelete.set(cls);
  }

  deleteClass(): void {
    const cls = this.classToDelete();
    if (!cls) return;

    this.deleting.set(true);
    this.cmdbService.deleteClass(cls.id).subscribe({
      next: () => {
        this.deleting.set(false);
        this.classToDelete.set(null);
        this.toastService.success(`Class "${cls.displayName}" deleted`);
        // Clear selection if it was this class
        if (this.selectedClassId() === cls.id) {
          this.selectedClassId.set(null);
          this.selectedDetail.set(null);
        }
        this.loadClasses();
      },
      error: (err) => {
        this.deleting.set(false);
        this.toastService.error(err.message || 'Failed to delete class');
      },
    });
  }

  private loadClasses(): void {
    this.loading.set(true);
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => {
        this.allClasses.set(classes);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load CI classes');
      },
    });
  }
}
