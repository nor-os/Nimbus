/**
 * Overview: Policy library browser — list, filter, create, edit, and delete policy library entries.
 * Architecture: Feature component for governance policy library (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router, app/core/services/policy.service
 * Concepts: Policy library management, category/severity filtering, system policy indicator,
 *     statement editing, variable schema editing
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PolicyService } from '@core/services/policy.service';
import { PermissionCheckService } from '@core/services/permission-check.service';
import {
  PolicyLibraryEntry,
  PolicyCategory,
  PolicySeverity,
  PolicyStatement,
  PolicyVariable,
} from '@shared/models/policy.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-policy-library',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="policy-library-page">
        <div class="page-header">
          <h1>Policy Library</h1>
          @if (canManage()) {
            <button class="btn btn-primary" (click)="openEditor()">Create Policy</button>
          }
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
            placeholder="Search policies..."
            class="search-input"
          />
          <select [(ngModel)]="categoryFilter" (ngModelChange)="loadPolicies()" class="filter-select">
            <option value="">All Categories</option>
            @for (cat of categories; track cat) {
              <option [value]="cat">{{ cat }}</option>
            }
          </select>
          <select [(ngModel)]="severityFilter" (ngModelChange)="loadPolicies()" class="filter-select">
            <option value="">All Severities</option>
            @for (sev of severities; track sev) {
              <option [value]="sev">{{ sev }}</option>
            }
          </select>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Statements</th>
                <th>Tags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (policy of filteredPolicies(); track policy.id) {
                <tr>
                  <td>
                    <div class="policy-name-cell">
                      @if (policy.isSystem) {
                        <span class="system-badge" title="System policy (read-only)">S</span>
                      }
                      <div>
                        <span class="policy-name">{{ policy.displayName }}</span>
                        <span class="policy-slug">{{ policy.name }}</span>
                      </div>
                    </div>
                  </td>
                  <td><span class="badge badge-category">{{ policy.category }}</span></td>
                  <td><span class="badge" [class]="'badge-' + policy.severity.toLowerCase()">{{ policy.severity }}</span></td>
                  <td>{{ policy.statements.length || 0 }}</td>
                  <td>
                    @if (policy.tags?.length) {
                      <div class="tag-list">
                        @for (tag of policy.tags!.slice(0, 3); track tag) {
                          <span class="tag">{{ tag }}</span>
                        }
                        @if (policy.tags!.length > 3) {
                          <span class="tag tag-more">+{{ policy.tags!.length - 3 }}</span>
                        }
                      </div>
                    } @else {
                      <span class="text-muted">-</span>
                    }
                  </td>
                  <td>
                    <div class="action-btns">
                      <button class="btn-icon" (click)="openEditor(policy)" title="Edit">&#9998;</button>
                      @if (canManage() && !policy.isSystem) {
                        <button class="btn-icon btn-icon-danger" (click)="deletePolicy(policy)" title="Delete">&times;</button>
                      }
                    </div>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="6" class="empty-row">
                    @if (loading()) {
                      Loading policies...
                    } @else {
                      No policies found
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Editor Modal -->
        @if (editorOpen()) {
          <div class="modal-overlay" (click)="closeEditor()">
            <div class="modal-panel" (click)="$event.stopPropagation()">
              <div class="modal-header">
                <h2>{{ editingPolicy() ? 'Edit Policy' : 'Create Policy' }}</h2>
                <button class="btn-close" (click)="closeEditor()">&times;</button>
              </div>

              <div class="modal-tabs">
                <button class="tab" [class.active]="activeTab() === 'general'" (click)="activeTab.set('general')">General</button>
                <button class="tab" [class.active]="activeTab() === 'statements'" (click)="activeTab.set('statements')">Statements</button>
                <button class="tab" [class.active]="activeTab() === 'variables'" (click)="activeTab.set('variables')">Variables</button>
              </div>

              <div class="modal-body">
                @if (activeTab() === 'general') {
                  <div class="form-group">
                    <label class="form-label">Name (slug)</label>
                    <input type="text" class="form-input" [(ngModel)]="formName" [disabled]="formIsSystem" placeholder="e.g. require-encryption" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Display Name</label>
                    <input type="text" class="form-input" [(ngModel)]="formDisplayName" [disabled]="formIsSystem" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Description</label>
                    <textarea class="form-input form-textarea" [(ngModel)]="formDescription" [disabled]="formIsSystem"></textarea>
                  </div>
                  <div class="form-row">
                    <div class="form-group flex-1">
                      <label class="form-label">Category</label>
                      <select class="form-input" [(ngModel)]="formCategory" [disabled]="formIsSystem">
                        @for (cat of categories; track cat) {
                          <option [value]="cat">{{ cat }}</option>
                        }
                      </select>
                    </div>
                    <div class="form-group flex-1">
                      <label class="form-label">Severity</label>
                      <select class="form-input" [(ngModel)]="formSeverity" [disabled]="formIsSystem">
                        @for (sev of severities; track sev) {
                          <option [value]="sev">{{ sev }}</option>
                        }
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Tags (comma-separated)</label>
                    <input type="text" class="form-input" [(ngModel)]="formTagsStr" [disabled]="formIsSystem" placeholder="security, compliance" />
                  </div>
                }

                @if (activeTab() === 'statements') {
                  <div class="statements-editor">
                    @for (stmt of formStatements; track $index) {
                      <div class="statement-card">
                        <div class="statement-header">
                          <span class="statement-sid">{{ stmt.sid || 'Statement ' + ($index + 1) }}</span>
                          @if (!formIsSystem) {
                            <button class="btn-icon btn-icon-danger" (click)="removeStatement($index)">&times;</button>
                          }
                        </div>
                        <div class="form-row">
                          <div class="form-group flex-1">
                            <label class="form-label">SID</label>
                            <input type="text" class="form-input" [(ngModel)]="stmt.sid" [disabled]="formIsSystem" />
                          </div>
                          <div class="form-group">
                            <label class="form-label">Effect</label>
                            <select class="form-input" [(ngModel)]="stmt.effect" [disabled]="formIsSystem">
                              <option value="allow">Allow</option>
                              <option value="deny">Deny</option>
                            </select>
                          </div>
                        </div>
                        <div class="form-group">
                          <label class="form-label">Actions (comma-separated)</label>
                          <input type="text" class="form-input" [ngModel]="stmt.actions.join(', ')" (ngModelChange)="stmt.actions = splitTags($event)" [disabled]="formIsSystem" placeholder="compute:create, storage:*" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Resources (comma-separated)</label>
                          <input type="text" class="form-input" [ngModel]="stmt.resources.join(', ')" (ngModelChange)="stmt.resources = splitTags($event)" [disabled]="formIsSystem" placeholder="VirtualMachine, BlockStorage" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Principals (comma-separated)</label>
                          <input type="text" class="form-input" [ngModel]="stmt.principals.join(', ')" (ngModelChange)="stmt.principals = splitTags($event)" [disabled]="formIsSystem" placeholder="*, role:Member" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Condition (ABAC expression, optional)</label>
                          <input type="text" class="form-input" [(ngModel)]="stmt.condition" [disabled]="formIsSystem" placeholder="resource.environment == 'production'" />
                        </div>
                      </div>
                    }
                    @if (!formIsSystem) {
                      <button class="btn btn-secondary" (click)="addStatement()">+ Add Statement</button>
                    }
                  </div>
                }

                @if (activeTab() === 'variables') {
                  <div class="variables-editor">
                    @for (v of formVariableEntries; track $index) {
                      <div class="variable-row">
                        <div class="form-group flex-1">
                          <label class="form-label">Name</label>
                          <input type="text" class="form-input" [(ngModel)]="v.key" [disabled]="formIsSystem" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Type</label>
                          <select class="form-input" [(ngModel)]="v.type" [disabled]="formIsSystem">
                            <option value="string">String</option>
                            <option value="integer">Integer</option>
                            <option value="float">Float</option>
                            <option value="boolean">Boolean</option>
                            <option value="array">Array</option>
                          </select>
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">Default</label>
                          <input type="text" class="form-input" [(ngModel)]="v.default" [disabled]="formIsSystem" />
                        </div>
                        @if (!formIsSystem) {
                          <button class="btn-icon btn-icon-danger var-remove" (click)="removeVariable($index)">&times;</button>
                        }
                      </div>
                    }
                    @if (!formIsSystem) {
                      <button class="btn btn-secondary" (click)="addVariable()">+ Add Variable</button>
                    }
                  </div>
                }
              </div>

              @if (!formIsSystem) {
                <div class="modal-footer">
                  <button class="btn btn-secondary" (click)="closeEditor()">Cancel</button>
                  <button class="btn btn-primary" (click)="savePolicy()" [disabled]="saving()">
                    {{ saving() ? 'Saving...' : (editingPolicy() ? 'Update' : 'Create') }}
                  </button>
                </div>
              } @else {
                <div class="modal-footer">
                  <button class="btn btn-secondary" (click)="closeEditor()">Close</button>
                </div>
              }
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .policy-library-page { padding: 0; }
    .page-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0;
    }
    .filters {
      display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
    }
    .search-input {
      flex: 1; min-width: 200px; padding: 8px 12px;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff;
      outline: none; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; }
    .filter-select {
      padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff;
      outline: none; font-family: inherit; cursor: pointer;
    }
    .table-container {
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
      overflow: hidden;
    }
    .table {
      width: 100%; border-collapse: collapse;
    }
    .table th {
      padding: 10px 14px; text-align: left;
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.04em; color: #64748b;
      border-bottom: 1px solid #e2e8f0; background: #f8fafc;
    }
    .table td {
      padding: 10px 14px; font-size: 0.8125rem; color: #1e293b;
      border-bottom: 1px solid #f1f5f9;
    }
    .table tr:last-child td { border-bottom: none; }
    .table tr:hover td { background: #f8fafc; }
    .policy-name-cell {
      display: flex; align-items: center; gap: 8px;
    }
    .system-badge {
      display: inline-flex; align-items: center; justify-content: center;
      width: 20px; height: 20px; border-radius: 4px;
      background: #dbeafe; color: #3b82f6; font-size: 0.6875rem;
      font-weight: 700; flex-shrink: 0;
    }
    .policy-name { display: block; font-weight: 500; color: #1e293b; }
    .policy-slug { display: block; font-size: 0.6875rem; color: #94a3b8; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 10px;
      font-size: 0.6875rem; font-weight: 600;
    }
    .badge-category { background: #f1f5f9; color: #475569; }
    .badge-critical { background: #fef2f2; color: #dc2626; }
    .badge-high { background: #fff7ed; color: #ea580c; }
    .badge-medium { background: #fefce8; color: #ca8a04; }
    .badge-low { background: #f0fdf4; color: #16a34a; }
    .badge-info { background: #eff6ff; color: #3b82f6; }
    .tag-list { display: flex; gap: 4px; flex-wrap: wrap; }
    .tag {
      padding: 1px 6px; border-radius: 4px; font-size: 0.6875rem;
      background: #f1f5f9; color: #64748b;
    }
    .tag-more { background: #e2e8f0; }
    .text-muted { color: #94a3b8; }
    .action-btns { display: flex; gap: 4px; }
    .btn-icon {
      width: 28px; height: 28px; border: 1px solid #e2e8f0;
      border-radius: 4px; background: #fff; color: #64748b;
      cursor: pointer; display: flex; align-items: center;
      justify-content: center; font-size: 0.875rem;
    }
    .btn-icon:hover { background: #f8fafc; color: #1e293b; }
    .btn-icon-danger:hover { background: #fef2f2; color: #dc2626; border-color: #fca5a5; }
    .empty-row { text-align: center; color: #94a3b8; padding: 32px 14px !important; }
    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; border: none; font-family: inherit;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: default; }
    .btn-secondary {
      background: #fff; color: #1e293b; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }

    /* Modal */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.4);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .modal-panel {
      background: #fff; border-radius: 12px; width: 680px;
      max-height: 85vh; display: flex; flex-direction: column;
      box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }
    .modal-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 20px 24px 0;
    }
    .modal-header h2 { font-size: 1.125rem; font-weight: 700; color: #1e293b; margin: 0; }
    .btn-close {
      width: 28px; height: 28px; border: none; background: none;
      color: #94a3b8; cursor: pointer; font-size: 1.25rem;
    }
    .btn-close:hover { color: #1e293b; }
    .modal-tabs {
      display: flex; gap: 0; padding: 16px 24px 0; border-bottom: 1px solid #e2e8f0;
    }
    .tab {
      padding: 8px 16px; border: none; background: none;
      color: #64748b; font-size: 0.8125rem; font-weight: 500;
      cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -1px; font-family: inherit;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .modal-body { padding: 20px 24px; overflow-y: auto; flex: 1; }
    .modal-footer {
      display: flex; gap: 8px; justify-content: flex-end;
      padding: 16px 24px; border-top: 1px solid #e2e8f0;
    }
    .form-group { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
    .form-label {
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.04em; color: #64748b;
    }
    .form-input {
      padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; color: #1e293b; background: #fff;
      font-family: inherit; outline: none;
    }
    .form-input:focus { border-color: #3b82f6; }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; }
    .form-textarea { min-height: 64px; resize: vertical; }
    .form-row { display: flex; gap: 12px; }
    .flex-1 { flex: 1; }

    /* Statement cards */
    .statement-card {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 14px; margin-bottom: 12px;
    }
    .statement-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 10px;
    }
    .statement-sid { font-weight: 600; font-size: 0.8125rem; color: #1e293b; }

    /* Variable rows */
    .variable-row {
      display: flex; gap: 8px; align-items: flex-end; margin-bottom: 8px;
    }
    .var-remove { align-self: flex-end; margin-bottom: 12px; }
  `],
})
export class PolicyLibraryComponent implements OnInit {
  private policySvc = inject(PolicyService);
  private permissionCheck = inject(PermissionCheckService);
  private toast = inject(ToastService);

  policies = signal<PolicyLibraryEntry[]>([]);
  loading = signal(false);
  saving = signal(false);
  editorOpen = signal(false);
  editingPolicy = signal<PolicyLibraryEntry | null>(null);
  activeTab = signal<'general' | 'statements' | 'variables'>('general');

  searchTerm = '';
  categoryFilter = '';
  severityFilter = '';

  categories: PolicyCategory[] = ['IAM', 'NETWORK', 'ENCRYPTION', 'TAGGING', 'COST'];
  severities: PolicySeverity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];

  // Form fields
  formName = '';
  formDisplayName = '';
  formDescription = '';
  formCategory: PolicyCategory = 'IAM';
  formSeverity: PolicySeverity = 'MEDIUM';
  formTagsStr = '';
  formIsSystem = false;
  formStatements: PolicyStatement[] = [];
  formVariableEntries: { key: string; type: string; default: string; description: string }[] = [];

  canManage = computed(() => {
    this.permissionCheck.permissions();
    return this.permissionCheck.hasPermission('policy:library:manage');
  });

  filteredPolicies = computed(() => {
    let list = this.policies();
    if (this.severityFilter) {
      list = list.filter(p => p.severity === this.severityFilter);
    }
    return list;
  });

  ngOnInit(): void {
    this.loadPolicies();
  }

  loadPolicies(): void {
    this.loading.set(true);
    this.policySvc.list({
      category: this.categoryFilter || undefined,
      search: this.searchTerm || undefined,
    }).subscribe({
      next: (entries) => {
        this.policies.set(entries);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toast.error('Failed to load policies');
      },
    });
  }

  onSearch(): void {
    this.loadPolicies();
  }

  openEditor(policy?: PolicyLibraryEntry): void {
    if (policy) {
      this.editingPolicy.set(policy);
      this.formName = policy.name;
      this.formDisplayName = policy.displayName;
      this.formDescription = policy.description || '';
      this.formCategory = policy.category;
      this.formSeverity = policy.severity;
      this.formTagsStr = policy.tags?.join(', ') || '';
      this.formIsSystem = policy.isSystem;
      this.formStatements = (policy.statements || []).map(s => ({ ...s }));
      this.formVariableEntries = policy.variables
        ? Object.entries(policy.variables).map(([key, v]) => ({
            key,
            type: v.type || 'string',
            default: v.default != null ? String(v.default) : '',
            description: v.description || '',
          }))
        : [];
    } else {
      this.editingPolicy.set(null);
      this.formName = '';
      this.formDisplayName = '';
      this.formDescription = '';
      this.formCategory = 'IAM';
      this.formSeverity = 'MEDIUM';
      this.formTagsStr = '';
      this.formIsSystem = false;
      this.formStatements = [this.emptyStatement()];
      this.formVariableEntries = [];
    }
    this.activeTab.set('general');
    this.editorOpen.set(true);
  }

  closeEditor(): void {
    this.editorOpen.set(false);
    this.editingPolicy.set(null);
  }

  addStatement(): void {
    this.formStatements = [...this.formStatements, this.emptyStatement()];
  }

  removeStatement(index: number): void {
    this.formStatements = this.formStatements.filter((_, i) => i !== index);
  }

  addVariable(): void {
    this.formVariableEntries = [...this.formVariableEntries, { key: '', type: 'string', default: '', description: '' }];
  }

  removeVariable(index: number): void {
    this.formVariableEntries = this.formVariableEntries.filter((_, i) => i !== index);
  }

  splitTags(val: string): string[] {
    return val.split(',').map(s => s.trim()).filter(Boolean);
  }

  savePolicy(): void {
    const tags = this.formTagsStr ? this.splitTags(this.formTagsStr) : null;
    const variables = this.formVariableEntries.length > 0
      ? Object.fromEntries(this.formVariableEntries.map(v => [v.key, {
          type: v.type,
          default: v.default || undefined,
          description: v.description || undefined,
        }]))
      : null;

    this.saving.set(true);

    if (this.editingPolicy()) {
      this.policySvc.update(this.editingPolicy()!.id, {
        name: this.formName,
        displayName: this.formDisplayName,
        description: this.formDescription || null,
        category: this.formCategory,
        statements: this.formStatements,
        variables,
        severity: this.formSeverity,
        tags,
      }).subscribe({
        next: () => {
          this.saving.set(false);
          this.closeEditor();
          this.loadPolicies();
          this.toast.success('Policy updated');
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error(err.message || 'Failed to update policy');
        },
      });
    } else {
      this.policySvc.create({
        name: this.formName,
        displayName: this.formDisplayName,
        description: this.formDescription || null,
        category: this.formCategory,
        statements: this.formStatements,
        variables,
        severity: this.formSeverity,
        tags,
      }).subscribe({
        next: () => {
          this.saving.set(false);
          this.closeEditor();
          this.loadPolicies();
          this.toast.success('Policy created');
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error(err.message || 'Failed to create policy');
        },
      });
    }
  }

  deletePolicy(policy: PolicyLibraryEntry): void {
    if (!confirm(`Delete policy "${policy.displayName}"?`)) return;
    this.policySvc.delete(policy.id).subscribe({
      next: () => {
        this.loadPolicies();
        this.toast.success('Policy deleted');
      },
      error: () => this.toast.error('Failed to delete policy'),
    });
  }

  private emptyStatement(): PolicyStatement {
    return {
      sid: '',
      effect: 'deny',
      actions: [],
      resources: ['*'],
      principals: ['*'],
      condition: null,
    };
  }
}
