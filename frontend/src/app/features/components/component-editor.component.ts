/**
 * Overview: Component editor — create/edit Pulumi Python scripts with Monaco, schema builders, and resolver bindings.
 * Architecture: Feature component for component authoring (Section 11)
 * Dependencies: @angular/core, @angular/router, ComponentService, SemanticService, MonacoEditorComponent, SearchableSelectComponent
 * Concepts: Full component editor with code, structured input/output schema builder, visual resolver bindings,
 *     version history with restore, publish workflow. Language locked to Python. Provider auto-selected.
 */
import { Component as NgComponent, OnInit, inject, signal, computed, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { MonacoEditorComponent } from '@shared/components/monaco-editor/monaco-editor.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { ComponentService } from '@core/services/component.service';
import { SemanticService } from '@core/services/semantic.service';
import { WorkflowService } from '@core/services/workflow.service';
import {
  Component as ComponentModel,
  ComponentCreateInput,
  ComponentOperation,
  ComponentOperationCreateInput,
  ComponentVersion,
  EstimatedDowntime,
  Resolver,
} from '@shared/models/component.model';
import { WorkflowDefinition } from '@shared/models/workflow.model';
import { ToastService } from '@shared/services/toast.service';

type EditorTab = 'codeConfig' | 'operations' | 'versions';
type ConfigTab = 'inputs' | 'outputs';
type ComponentMode = 'provider' | 'tenant';

interface SchemaProperty {
  name: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  defaultValue: string;
  enumValues: string;
}

interface ResolverBinding {
  paramName: string;
  resolverType: string;
  resolverParams: Record<string, string>;
  targetField: string;
}

const EXAMPLE_CODE = `"""
Example Pulumi component for provisioning a virtual machine.
Modify this template to define your infrastructure resource.
"""

import pulumi
from pulumi import Input, Output

# Component inputs are injected as variables:
#   name: str           - resolved resource name
#   ip_address: str     - resolved IP from IPAM
#   image_id: str       - resolved OS image reference

def create_resource(args: dict) -> dict:
    """Create the infrastructure resource.

    Args:
        args: Resolved input parameters (after resolver pre-processing)

    Returns:
        Dictionary of output values to store in CMDB
    """
    resource_name = args.get("name", "unnamed")

    # TODO: Replace with actual Pulumi resource creation
    # Example:
    # vm = compute.VirtualMachine(
    #     resource_name,
    #     name=args["name"],
    #     image=args["image_id"],
    #     ip_address=args["ip_address"],
    #     ...
    # )

    return {
        "resource_id": f"placeholder-{resource_name}",
        "status": "created",
    }
`;

@NgComponent({
  selector: 'nimbus-component-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, MonacoEditorComponent, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <!-- Header -->
        <div class="page-header">
          <button class="back-btn" (click)="router.navigate([basePath()])">&larr; {{ isProviderMode() ? 'Provider Components' : 'Components' }}</button>
          <div class="header-main">
            <h1>{{ isNew() ? 'New Component' : component()?.displayName || 'Component' }}</h1>
            @if (component(); as c) {
              <div class="header-badges">
                <span class="badge lang-python">Python</span>
                <span class="badge" [class.published]="c.isPublished" [class.draft]="!c.isPublished">
                  {{ c.isPublished ? 'Published v' + (c.version - 1) : 'Draft' }}
                </span>
              </div>
            }
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" (click)="save()" [disabled]="saving()">
              {{ saving() ? 'Saving...' : 'Save Draft' }}
            </button>
            @if (!isNew() && component()) {
              <button class="btn btn-primary" (click)="showPublishDialog.set(true)">Publish</button>
              <button class="btn btn-danger" (click)="confirmDelete()">Delete</button>
            }
          </div>
        </div>

        <!-- Form Fields -->
        <div class="form-section">
          <div class="form-row">
            <div class="form-group">
              <label>Name (slug)</label>
              <input type="text" [(ngModel)]="form.name" placeholder="my-component" />
            </div>
            <div class="form-group">
              <label>Display Name</label>
              <input type="text" [(ngModel)]="form.displayName" placeholder="My Component" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Provider</label>
              <nimbus-searchable-select
                [options]="providerOptions()"
                [(ngModel)]="providerId"
                placeholder="Select provider..."
              />
            </div>
            <div class="form-group">
              <label>Semantic Type</label>
              <nimbus-searchable-select
                [options]="semanticTypeOptions()"
                [(ngModel)]="form.semanticTypeId"
                placeholder="Select semantic type..."
              />
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>Description</label>
            <input type="text" [(ngModel)]="form.description" placeholder="Brief description" />
          </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
          <button class="tab" [class.active]="activeTab() === 'codeConfig'" (click)="activeTab.set('codeConfig')">Code &amp; Config</button>
          @if (!isNew()) {
            <button class="tab" [class.active]="activeTab() === 'operations'" (click)="activeTab.set('operations'); loadOperations()">
              Operations ({{ operations().length }})
            </button>
            <button class="tab" [class.active]="activeTab() === 'versions'" (click)="activeTab.set('versions'); loadVersions()">
              Versions ({{ versions().length }})
            </button>
          }
        </div>

        <!-- Tab Content -->
        <div class="tab-content" [class.no-padding]="activeTab() === 'codeConfig'">
          <!-- ── Code & Config Tab ───────────────────────── -->
          @if (activeTab() === 'codeConfig') {
            <div class="split-pane">
              <!-- Left: Monaco Editor -->
              <div class="editor-pane">
                @if (editorVisible()) {
                  <nimbus-monaco-editor
                    [code]="form.code"
                    [language]="'python'"
                    [height]="'calc(100vh - 320px)'"
                    (codeChange)="form.code = $event"
                  />
                }
              </div>

              <!-- Right: Config Panel -->
              <div class="config-pane">
                <div class="config-tabs">
                  <button class="config-tab" [class.active]="configTab() === 'inputs'" (click)="configTab.set('inputs')">Inputs</button>
                  <button class="config-tab" [class.active]="configTab() === 'outputs'" (click)="configTab.set('outputs')">Outputs</button>
                </div>
                <div class="config-body">
                  <!-- Inputs sub-tab -->
                  @if (configTab() === 'inputs') {
                    <div class="schema-builder">
                      <div class="schema-header">
                        <h3>Input Parameters</h3>
                        <div style="display:flex;gap:6px">
                          <button class="btn btn-sm" (click)="addInputProperty()">+ Add</button>
                          @if (!isNew() && inputProperties().length > 0) {
                            <button class="btn btn-sm" (click)="validateBindings()">Validate</button>
                          }
                        </div>
                      </div>
                      @if (bindingWarnings().length > 0) {
                        <div class="binding-warnings">
                          @for (w of bindingWarnings(); track w) {
                            <div class="warning-item">&#9888; {{ w }}</div>
                          }
                        </div>
                      }
                      @if (inputProperties().length === 0) {
                        <div class="empty-schema">No input parameters defined.</div>
                      }
                      @for (prop of inputProperties(); track prop.name; let i = $index) {
                        <div class="input-card" [class.resolver-bound]="hasBinding(prop.name)">
                          <div class="schema-row-top">
                            <div class="schema-field">
                              <label>Name</label>
                              <input type="text" [(ngModel)]="prop.name" placeholder="param_name" />
                            </div>
                            <div class="schema-field type-field">
                              <label>Type</label>
                              <select [(ngModel)]="prop.type">
                                <option value="string">String</option>
                                <option value="integer">Integer</option>
                                <option value="number">Number</option>
                                <option value="boolean">Boolean</option>
                                <option value="object">Object</option>
                                <option value="array">Array</option>
                              </select>
                            </div>
                            <div class="schema-field check-field">
                              <label>
                                <input type="checkbox" [(ngModel)]="prop.required" /> Req
                              </label>
                            </div>
                            <button class="btn-icon btn-remove" (click)="removeInputProperty(i)" title="Remove">&times;</button>
                          </div>
                          <div class="schema-field">
                            <label>Description</label>
                            <input type="text" [(ngModel)]="prop.description" placeholder="Description" />
                          </div>

                          <!-- Source toggle: Manual vs Resolver -->
                          <div class="source-row">
                            <label class="source-label">Source</label>
                            <div class="source-toggle">
                              <button class="source-btn" [class.active]="!hasBinding(prop.name)" (click)="removeBinding(prop.name)">Manual</button>
                              <button class="source-btn" [class.active]="hasBinding(prop.name)" (click)="enableBinding(prop.name, prop.type)">Resolver</button>
                            </div>
                          </div>

                          @if (!hasBinding(prop.name)) {
                            <!-- Manual: default value + enum -->
                            <div class="schema-row-top">
                              <div class="schema-field">
                                <label>Default</label>
                                <input type="text" [(ngModel)]="prop.defaultValue" placeholder="Default value" />
                              </div>
                              <div class="schema-field">
                                <label>Enum (comma-sep)</label>
                                <input type="text" [(ngModel)]="prop.enumValues" placeholder="a, b, c" />
                              </div>
                            </div>
                          } @else {
                            <!-- Resolver binding config -->
                            @if (getBinding(prop.name); as binding) {
                              @if (getSuggestions(prop.name).length > 0 && !binding.resolverType) {
                                <div class="suggestions">
                                  <span class="suggestions-label">Suggested:</span>
                                  @for (s of getSuggestions(prop.name); track s.resolver_type) {
                                    <button class="suggestion-chip" (click)="applySuggestion(binding, s)">
                                      {{ s.display_name }}
                                      @if (s.matching_fields.length) {
                                        <span class="match-hint">&rarr; {{ s.matching_fields[0] }}</span>
                                      }
                                    </button>
                                  }
                                </div>
                              }
                              <div class="binding-row">
                                <div class="schema-field">
                                  <label>Resolver</label>
                                  <select [(ngModel)]="binding.resolverType" (ngModelChange)="onBindingResolverChange(binding)">
                                    <option value="">-- Select --</option>
                                    @for (r of resolvers(); track r.id) {
                                      <option [value]="r.resolverType">{{ r.displayName }}</option>
                                    }
                                  </select>
                                </div>
                                <div class="schema-field">
                                  <label>Output Field</label>
                                  <input type="text" [(ngModel)]="binding.targetField" placeholder="e.g. cidr, name" />
                                </div>
                              </div>
                              @if (binding.resolverType) {
                                @if (getResolverByType(binding.resolverType); as r) {
                                  <span class="resolver-hint">{{ r.description }}</span>
                                }
                              }
                            }
                          }
                        </div>
                      }
                    </div>
                  }

                  <!-- Outputs sub-tab -->
                  @if (configTab() === 'outputs') {
                    <div class="schema-builder">
                      <div class="schema-header">
                        <h3>Output Values</h3>
                        <button class="btn btn-sm" (click)="addOutputProperty()">+ Add</button>
                      </div>
                      @if (outputProperties().length === 0) {
                        <div class="empty-schema">No outputs defined.</div>
                      }
                      @for (prop of outputProperties(); track prop.name; let i = $index) {
                        <div class="schema-row stacked">
                          <div class="schema-row-top">
                            <div class="schema-field">
                              <label>Name</label>
                              <input type="text" [(ngModel)]="prop.name" placeholder="output_name" />
                            </div>
                            <div class="schema-field type-field">
                              <label>Type</label>
                              <select [(ngModel)]="prop.type">
                                <option value="string">String</option>
                                <option value="integer">Integer</option>
                                <option value="number">Number</option>
                                <option value="boolean">Boolean</option>
                                <option value="object">Object</option>
                                <option value="array">Array</option>
                              </select>
                            </div>
                            <button class="btn-icon btn-remove" (click)="removeOutputProperty(i)" title="Remove">&times;</button>
                          </div>
                          <div class="schema-field">
                            <label>Description</label>
                            <input type="text" [(ngModel)]="prop.description" placeholder="Description" />
                          </div>
                        </div>
                      }
                    </div>
                  }

                </div>
              </div>
            </div>
          }

          <!-- ── Operations Tab ─────────────────────────── -->
          @if (activeTab() === 'operations') {
            <div class="operations-builder">
              <div class="schema-header">
                <h3>Day-2 Operations</h3>
                <button class="btn btn-sm" (click)="showOpForm.set(true); resetOpForm()">+ Add Operation</button>
              </div>
              <p class="section-info">Define workflow-backed actions available on deployed resources (e.g. extend disk, snapshot, restart).</p>

              @if (operations().length === 0 && !showOpForm()) {
                <div class="empty-schema">No operations defined. Add day-2 operations that users can trigger on deployed resources.</div>
              }

              @for (op of operations(); track op.id) {
                <!-- Collapsed card (shown when NOT editing this op) -->
                @if (editingOpId() !== op.id) {
                  <div class="operation-card" [class.expanded]="expandedOpId() === op.id">
                    <div class="operation-header" (click)="toggleOperationExpand(op)">
                      <div class="operation-title">
                        <span class="expand-icon">{{ expandedOpId() === op.id ? '&#9660;' : '&#9654;' }}</span>
                        <span class="operation-name">{{ op.displayName }}</span>
                        @if (op.estimatedDowntime && op.estimatedDowntime !== 'NONE') {
                          <span class="badge badge-downtime">~{{ parseDowntimeMinutes(op.estimatedDowntime) }} min downtime</span>
                        }
                      </div>
                      <div class="operation-actions" (click)="$event.stopPropagation()">
                        <button class="btn btn-sm btn-secondary" (click)="editOperation(op)">Edit</button>
                        <button class="btn btn-sm btn-danger" (click)="deleteOperation(op)">Delete</button>
                      </div>
                    </div>
                    @if (op.description) {
                      <div class="operation-desc">{{ op.description }}</div>
                    }

                    <!-- Expanded workflow detail -->
                    @if (expandedOpId() === op.id) {
                      <div class="workflow-detail">
                        @if (workflowLoading()) {
                          <div class="workflow-loading">Loading workflow...</div>
                        } @else if (expandedWorkflow()) {
                          <div class="workflow-detail-header">
                            <h4>{{ expandedWorkflow()!.name }}</h4>
                            <div class="workflow-detail-actions">
                              <button class="btn btn-sm btn-secondary" (click)="editWorkflow(expandedWorkflow()!.id)">Open in Editor</button>
                            </div>
                          </div>
                          @if (expandedWorkflow()!.description) {
                            <p class="workflow-detail-desc">{{ expandedWorkflow()!.description }}</p>
                          }
                          <div class="workflow-detail-meta">
                            <div class="meta-item">
                              <span class="meta-label">Status</span>
                              <span class="badge" [class.published]="expandedWorkflow()!.status === 'ACTIVE'" [class.draft]="expandedWorkflow()!.status === 'DRAFT'">{{ expandedWorkflow()!.status }}</span>
                            </div>
                            <div class="meta-item">
                              <span class="meta-label">Type</span>
                              <span>{{ expandedWorkflow()!.workflowType }}</span>
                            </div>
                            <div class="meta-item">
                              <span class="meta-label">Version</span>
                              <span>v{{ expandedWorkflow()!.version }}</span>
                            </div>
                            @if (expandedWorkflow()!.graph) {
                              <div class="meta-item">
                                <span class="meta-label">Nodes</span>
                                <span>{{ expandedWorkflow()!.graph!.nodes.length || 0 }}</span>
                              </div>
                            }
                            <div class="meta-item">
                              <span class="meta-label">Timeout</span>
                              <span>{{ expandedWorkflow()!.timeoutSeconds }}s</span>
                            </div>
                          </div>
                          @if (expandedWorkflow()?.graph?.nodes?.length) {
                            <div class="workflow-node-list">
                              <span class="meta-label">Node Pipeline</span>
                              <div class="node-pipeline">
                                @for (node of expandedWorkflow()!.graph!.nodes; track node.id; let last = $last) {
                                  <span class="pipeline-node">{{ node.label || node.type }}</span>
                                  @if (!last) {
                                    <span class="pipeline-arrow">&rarr;</span>
                                  }
                                }
                              </div>
                            </div>
                          }
                        } @else {
                          <div class="workflow-loading">No workflow linked.</div>
                        }
                      </div>
                    } @else {
                      <div class="operation-meta">
                        <span>Workflow: <strong>{{ op.workflowDefinitionName || '—' }}</strong></span>
                        @if (op.inputSchema) {
                          <span>Inputs: {{ getSchemaFieldCount(op.inputSchema) }} fields</span>
                        }
                      </div>
                    }
                  </div>
                }

                <!-- Inline edit form (shown when editing this op) -->
                @if (editingOpId() === op.id) {
                  <ng-container *ngTemplateOutlet="opFormTpl; context: { isEdit: true }"></ng-container>
                }
              }

              <!-- New operation form (at bottom, only for new) -->
              @if (showOpForm() && !editingOpId()) {
                <ng-container *ngTemplateOutlet="opFormTpl; context: { isEdit: false }"></ng-container>
              }

              <!-- Shared form template -->
              <ng-template #opFormTpl let-isEdit="isEdit">
                <div class="operation-form">
                  <h4>{{ isEdit ? 'Edit Operation' : 'New Operation' }}</h4>
                  <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" [(ngModel)]="opForm.displayName" placeholder="Extend Disk" />
                  </div>
                  <div class="form-group">
                    <label>Description</label>
                    <input type="text" [(ngModel)]="opForm.description" placeholder="What this operation does" />
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>Workflow Definition</label>
                      @if (isEdit) {
                        <input type="text" [value]="getWorkflowName(opForm.workflowDefinitionId)" disabled />
                      } @else {
                        <select [(ngModel)]="opForm.workflowDefinitionId">
                          <option value="">-- Select workflow --</option>
                          @for (wf of workflowDefinitions(); track wf.id) {
                            <option [value]="wf.id">{{ wf.name }}</option>
                          }
                        </select>
                      }
                    </div>
                    <div class="form-group">
                      <label>Estimated Downtime (minutes)</label>
                      <input type="number" [(ngModel)]="opForm.downtimeMinutes" min="0" placeholder="0" />
                    </div>
                  </div>
                  <div class="form-actions">
                    <button class="btn btn-secondary" (click)="cancelOpForm()">Cancel</button>
                    <button class="btn btn-primary" (click)="saveOperation()" [disabled]="opSaving()">
                      {{ opSaving() ? 'Saving...' : (isEdit ? 'Update' : 'Create') }}
                    </button>
                  </div>
                </div>
              </ng-template>
            </div>
          }

          <!-- ── Versions Tab ────────────────────────────── -->
          @if (activeTab() === 'versions') {
            <div class="version-list">
              @if (versions().length === 0) {
                <p class="empty-msg">No published versions yet. Publish this component to create a version snapshot.</p>
              }
              @for (v of versions(); track v.id) {
                <div class="version-card">
                  <div class="version-header">
                    <span class="version-number">v{{ v.version }}</span>
                    <span class="version-date">{{ v.publishedAt | date:'medium' }}</span>
                    <button class="btn btn-sm btn-secondary" (click)="restoreVersion(v)">Restore</button>
                  </div>
                  @if (v.changelog) {
                    <div class="version-changelog">{{ v.changelog }}</div>
                  }
                </div>
              }
            </div>
          }
        </div>

        <!-- Publish Dialog -->
        @if (showPublishDialog()) {
          <div class="dialog-overlay" (click)="showPublishDialog.set(false)">
            <div class="dialog" (click)="$event.stopPropagation()">
              <h3>Publish Component</h3>
              <p>This will create an immutable version snapshot (v{{ component()?.version }}).</p>
              <label>Changelog</label>
              <textarea rows="4" [(ngModel)]="publishChangelog" placeholder="What changed in this version?"></textarea>
              <div class="dialog-actions">
                <button class="btn btn-secondary" (click)="showPublishDialog.set(false)">Cancel</button>
                <button class="btn btn-primary" (click)="publish()">Publish</button>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem; }
    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.875rem; padding: 0; text-align: left;
    }
    .back-btn:hover { text-decoration: underline; }
    .header-main { display: flex; align-items: center; gap: 0.75rem; }
    .header-main h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-badges { display: flex; gap: 0.5rem; }
    .badge {
      font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.5rem; border-radius: 4px;
      text-transform: uppercase;
    }
    .lang-python { background: #fef3c7; color: #92400e; }
    .badge.published { background: #dcfce7; color: #166534; }
    .badge.draft { background: #f1f5f9; color: #64748b; }
    .header-actions { display: flex; gap: 0.5rem; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: none; font-weight: 500; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #f1f5f9; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-danger { background: #fee2e2; color: #991b1b; }
    .btn-danger:hover { background: #fecaca; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .form-section { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }
    .form-row { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .form-group { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; }
    .form-group.flex-2 { flex: 2; }
    .form-group label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .form-group input, .form-group select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff;
    }
    .form-group input:focus, .form-group select:focus {
      outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }

    .tabs { display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.875rem; color: #64748b; font-weight: 500; border-bottom: 2px solid transparent;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; min-height: 300px; }
    .tab-content.no-padding { padding: 0; overflow: hidden; }

    /* ── Split pane layout ────────────────────── */
    .split-pane { display: flex; gap: 0; min-height: calc(100vh - 320px); }
    .editor-pane { flex: 3; min-width: 0; }
    .config-pane {
      flex: 2; min-width: 300px; display: flex; flex-direction: column;
      border-left: 1px solid #e2e8f0;
    }
    .config-tabs {
      display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; background: #f8fafc;
    }
    .config-tab {
      padding: 0.5rem 0.875rem; border: none; border-bottom: 2px solid transparent;
      background: none; cursor: pointer; font-size: 0.8125rem; font-weight: 500; color: #64748b;
    }
    .config-tab:hover { color: #1e293b; }
    .config-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .config-body { flex: 1; overflow-y: auto; max-height: calc(100vh - 380px); padding: 0.75rem; }

    /* ── Schema builder ──────────────────────── */
    .schema-builder { display: flex; flex-direction: column; gap: 0.75rem; }
    .schema-header { display: flex; justify-content: space-between; align-items: center; }
    .schema-header h3 { font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0; }
    .empty-schema { color: #94a3b8; font-size: 0.875rem; padding: 1.5rem; text-align: center; }

    .schema-row, .binding-row {
      display: flex; gap: 0.5rem; align-items: flex-end;
      padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
    }
    .schema-row.stacked {
      flex-direction: column; align-items: stretch; gap: 0.5rem;
    }
    .schema-row-top {
      display: flex; gap: 0.5rem; align-items: flex-end;
    }
    .schema-field { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; }
    .schema-field.name-field { flex: 1.2; }
    .schema-field.type-field { flex: 0.8; }
    .schema-field.desc-field { flex: 2; }
    .schema-field.default-field { flex: 1; }
    .schema-field.enum-field { flex: 1.2; }
    .schema-field.check-field { flex: 0 0 auto; align-self: center; }
    .schema-field.flex-2 { flex: 2; }
    .schema-field label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .schema-field input, .schema-field select {
      padding: 0.375rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; background: #fff;
    }
    .schema-field input:focus, .schema-field select:focus {
      outline: none; border-color: #3b82f6;
    }
    .schema-field input[type="checkbox"] { width: auto; margin-right: 0.25rem; }

    .btn-icon { background: none; border: none; cursor: pointer; font-size: 1.25rem; padding: 0.25rem; line-height: 1; color: #94a3b8; }
    .btn-remove:hover { color: #dc2626; }

    .resolver-hint { font-size: 0.75rem; color: #64748b; font-style: italic; display: block; margin-top: 0.25rem; }
    .section-info { font-size: 0.875rem; color: #64748b; margin: 0; }
    .binding-warnings { margin: 8px 0; padding: 8px 12px; background: #fef3c7; border: 1px solid #fbbf24; border-radius: 6px; }
    .warning-item { font-size: 0.8125rem; color: #92400e; padding: 2px 0; }

    /* ── Input card with integrated source toggle ── */
    .input-card {
      padding: 0.75rem; background: #f8fafc; border-radius: 6px;
      border: 1px solid #e2e8f0; margin-bottom: 0.5rem;
      display: flex; flex-direction: column; gap: 0.5rem; transition: border-color 0.15s;
    }
    .input-card.resolver-bound { border-color: #93c5fd; background: #f0f7ff; }
    .source-row { display: flex; align-items: center; gap: 0.5rem; }
    .source-label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .source-toggle { display: flex; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; }
    .source-btn {
      padding: 0.25rem 0.625rem; font-size: 0.6875rem; font-weight: 500; border: none;
      background: #fff; color: #64748b; cursor: pointer; font-family: inherit;
    }
    .source-btn:first-child { border-right: 1px solid #e2e8f0; }
    .source-btn.active { background: #3b82f6; color: #fff; }
    .source-btn:hover:not(.active) { background: #f1f5f9; }
    .binding-row { display: flex; gap: 0.5rem; }
    .binding-row .schema-field { flex: 1; }
    .suggestions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; }
    .suggestions-label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .suggestion-chip {
      padding: 3px 10px; border-radius: 12px; border: 1px solid #93c5fd; background: #eff6ff;
      color: #1e40af; font-size: 0.6875rem; font-weight: 500; cursor: pointer; font-family: inherit;
    }
    .suggestion-chip:hover { background: #dbeafe; border-color: #3b82f6; }
    .match-hint { color: #64748b; font-weight: 400; }

    /* ── Version list ────────────────────────── */
    .version-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .empty-msg { color: #64748b; font-size: 0.875rem; }
    .version-card { padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0; }
    .version-header { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; }
    .version-number { font-weight: 600; color: #1e293b; }
    .version-date { font-size: 0.75rem; color: #94a3b8; flex: 1; }
    .version-changelog { font-size: 0.8125rem; color: #374151; margin-top: 0.375rem; }

    /* ── Operations ──────────────────────────── */
    .operations-builder { display: flex; flex-direction: column; gap: 0.75rem; }
    .operation-card {
      padding: 0.75rem 1rem; background: #f8fafc; border-radius: 6px;
      border: 1px solid #e2e8f0;
    }
    .operation-card { cursor: pointer; transition: border-color 0.15s; }
    .operation-card:hover { border-color: #cbd5e1; }
    .operation-card.expanded { border-color: #3b82f6; cursor: default; }
    .operation-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
    .operation-title { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .expand-icon { font-size: 0.625rem; color: #94a3b8; width: 0.75rem; flex-shrink: 0; }
    .operation-name { font-weight: 600; color: #1e293b; font-size: 0.9375rem; }
    .op-name-badge { background: #f1f5f9; color: #64748b; font-family: monospace; font-size: 0.75rem; }
    .badge-destructive { background: #fef2f2; color: #dc2626; }
    .badge-approval { background: #eff6ff; color: #2563eb; }
    .badge-downtime { background: #fffbeb; color: #d97706; }
    .operation-actions { display: flex; gap: 0.375rem; align-items: center; }
    .btn-link { background: none; border: none; color: #3b82f6; cursor: pointer; font-size: 0.8125rem; padding: 0.375rem 0.5rem; }
    .btn-link:hover { text-decoration: underline; }
    .operation-desc { font-size: 0.8125rem; color: #64748b; margin-top: 0.375rem; }
    .operation-meta { display: flex; gap: 1.5rem; font-size: 0.75rem; color: #94a3b8; margin-top: 0.375rem; }
    .operation-meta strong { color: #475569; }
    .operation-form {
      background: #fff; border: 1px solid #3b82f6; border-radius: 8px;
      padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
    }
    .operation-form h4 { margin: 0; font-size: 1rem; color: #1e293b; }
    .form-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.25rem; }

    /* ── Workflow detail (expanded operation) ── */
    .workflow-detail {
      margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #e2e8f0;
    }
    .workflow-loading { font-size: 0.8125rem; color: #94a3b8; padding: 0.5rem 0; }
    .workflow-detail-header { display: flex; justify-content: space-between; align-items: center; }
    .workflow-detail-header h4 { margin: 0; font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
    .workflow-detail-actions { display: flex; gap: 0.375rem; }
    .workflow-detail-desc { font-size: 0.8125rem; color: #64748b; margin: 0.25rem 0 0.5rem; }
    .workflow-detail-meta { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.5rem; }
    .meta-item { display: flex; flex-direction: column; gap: 0.125rem; }
    .meta-label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .meta-item span:not(.meta-label):not(.badge) { font-size: 0.8125rem; color: #1e293b; }
    .workflow-node-list { margin-top: 0.75rem; }
    .node-pipeline {
      display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; margin-top: 0.375rem;
    }
    .pipeline-node {
      display: inline-block; padding: 0.25rem 0.625rem; background: #eff6ff; color: #1e40af;
      border-radius: 4px; font-size: 0.75rem; font-weight: 500;
    }
    .pipeline-arrow { color: #94a3b8; font-size: 0.75rem; }

    /* ── Dialog ──────────────────────────────── */
    .dialog-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex;
      align-items: center; justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 8px; padding: 1.5rem; max-width: 480px; width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.2);
    }
    .dialog h3 { font-size: 1.125rem; color: #1e293b; margin: 0 0 0.5rem; }
    .dialog p { font-size: 0.875rem; color: #64748b; margin: 0 0 1rem; }
    .dialog label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; display: block; margin-bottom: 0.25rem; }
    .dialog textarea {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.875rem; resize: vertical; box-sizing: border-box;
    }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
  `],
})
export class ComponentEditorComponent implements OnInit {
  router = inject(Router);
  private route = inject(ActivatedRoute);
  private componentService = inject(ComponentService);
  private semanticService = inject(SemanticService);
  private workflowService = inject(WorkflowService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  component = signal<ComponentModel | null>(null);
  loading = signal(false);
  saving = signal(false);
  activeTab = signal<EditorTab>('codeConfig');
  configTab = signal<ConfigTab>('inputs');
  showPublishDialog = signal(false);
  publishChangelog = '';
  versions = signal<ComponentVersion[]>([]);
  resolvers = signal<Resolver[]>([]);
  operations = signal<ComponentOperation[]>([]);
  workflowDefinitions = signal<{ id: string; name: string }[]>([]);
  showOpForm = signal(false);
  editingOpId = signal<string | null>(null);
  opSaving = signal(false);
  expandedOpId = signal<string | null>(null);
  expandedWorkflow = signal<WorkflowDefinition | null>(null);
  workflowLoading = signal(false);
  editorVisible = signal(false);

  // Dropdown options
  semanticTypeOptions = signal<SelectOption[]>([]);
  providerOptions = signal<SelectOption[]>([]);
  providerId = '';

  isProviderMode = computed(() => (this.route.snapshot.data['mode'] as ComponentMode) === 'provider');
  basePath = computed(() => this.isProviderMode() ? '/provider/components' : '/components');

  form = {
    name: '',
    displayName: '',
    description: '',
    semanticTypeId: '',
    code: EXAMPLE_CODE,
    inputSchema: null as Record<string, unknown> | null,
    outputSchema: null as Record<string, unknown> | null,
    resolverBindings: null as Record<string, unknown> | null,
  };

  opForm = {
    displayName: '',
    description: '',
    workflowDefinitionId: '',
    downtimeMinutes: 0,
  };

  // Structured schema editing
  inputProperties = signal<SchemaProperty[]>([]);
  outputProperties = signal<SchemaProperty[]>([]);
  resolverBindings = signal<ResolverBinding[]>([]);
  bindingWarnings = signal<string[]>([]);

  isNew = computed(() => !this.route.snapshot.params['id']);

  ngOnInit(): void {
    const id = this.route.snapshot.params['id'];
    this.loadSemanticTypes();
    this.loadProvider();
    this.loadResolvers();

    if (id) {
      this.loadComponent(id);
    } else {
      // Trigger editor visibility after a tick so Monaco gets a real DOM size
      setTimeout(() => {
        this.editorVisible.set(true);
        this.cdr.markForCheck();
      }, 50);
    }
  }

  private loadSemanticTypes(): void {
    this.semanticService.listTypes({ limit: 500, infrastructureOnly: true }).subscribe({
      next: (result) => {
        this.semanticTypeOptions.set(
          result.items.map(t => ({ value: t.id, label: `${t.displayName} (${t.category?.name || t.name})` }))
        );
        this.cdr.markForCheck();
      },
    });
  }

  private loadProvider(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => {
        this.providerOptions.set(
          providers.map(p => ({ value: p.id, label: p.displayName || p.name }))
        );
        // Auto-select first provider for new components if only one exists
        if (this.isNew() && providers.length === 1) {
          this.providerId = providers[0].id;
        }
        this.cdr.markForCheck();
      },
    });
  }

  private loadComponent(id: string): void {
    this.loading.set(true);
    this.componentService.getComponent(id, this.isProviderMode()).subscribe({
      next: (c) => {
        this.component.set(c);
        this.form.name = c.name;
        this.form.displayName = c.displayName;
        this.form.description = c.description || '';
        this.form.semanticTypeId = c.semanticTypeId;
        this.form.code = c.code || EXAMPLE_CODE;
        this.form.inputSchema = c.inputSchema;
        this.form.outputSchema = c.outputSchema;
        this.form.resolverBindings = c.resolverBindings;
        this.providerId = c.providerId;
        this.versions.set(c.versions || []);
        this.operations.set(c.operations || []);

        // Parse schema into structured format
        this.inputProperties.set(this.schemaToProperties(c.inputSchema));
        this.outputProperties.set(this.schemaToProperties(c.outputSchema));
        this.resolverBindings.set(this.parseResolverBindings(c.resolverBindings));

        this.loading.set(false);
        // Show editor after data loads
        setTimeout(() => {
          this.editorVisible.set(true);
          this.cdr.markForCheck();
        }, 50);
        this.cdr.markForCheck();
      },
      error: () => this.loading.set(false),
    });
  }

  private loadResolvers(): void {
    this.componentService.listResolvers().subscribe({
      next: (r) => {
        this.resolvers.set(r);
        this.cdr.markForCheck();
      },
    });
  }

  loadVersions(): void {
    const comp = this.component();
    if (!comp) return;
    this.componentService.getVersionHistory(comp.id).subscribe({
      next: (v) => {
        this.versions.set(v);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Schema ↔ Properties conversion ────────────────────────────────

  private schemaToProperties(schema: Record<string, unknown> | null): SchemaProperty[] {
    if (!schema) return [];
    const props = (schema['properties'] || {}) as Record<string, Record<string, unknown>>;
    const required = ((schema['required'] || []) as string[]);
    return Object.entries(props).map(([name, def]) => ({
      name,
      type: (def['type'] as SchemaProperty['type']) || 'string',
      description: (def['description'] as string) || '',
      required: required.includes(name),
      defaultValue: def['default'] !== undefined ? String(def['default']) : '',
      enumValues: Array.isArray(def['enum']) ? (def['enum'] as string[]).join(', ') : '',
    }));
  }

  private propertiesToSchema(properties: SchemaProperty[]): Record<string, unknown> | null {
    if (properties.length === 0) return null;
    const props: Record<string, Record<string, unknown>> = {};
    const required: string[] = [];

    for (const p of properties) {
      if (!p.name.trim()) continue;
      const def: Record<string, unknown> = { type: p.type };
      if (p.description) def['description'] = p.description;
      if (p.defaultValue) {
        if (p.type === 'integer' || p.type === 'number') {
          def['default'] = Number(p.defaultValue);
        } else if (p.type === 'boolean') {
          def['default'] = p.defaultValue === 'true';
        } else {
          def['default'] = p.defaultValue;
        }
      }
      if (p.enumValues.trim()) {
        def['enum'] = p.enumValues.split(',').map(v => v.trim()).filter(Boolean);
      }
      props[p.name] = def;
      if (p.required) required.push(p.name);
    }

    const schema: Record<string, unknown> = { type: 'object', properties: props };
    if (required.length > 0) schema['required'] = required;
    return schema;
  }

  private parseResolverBindings(bindings: Record<string, unknown> | null): ResolverBinding[] {
    if (!bindings) return [];
    return Object.entries(bindings).map(([paramName, def]) => {
      const d = def as Record<string, unknown>;
      return {
        paramName,
        resolverType: (d['resolver_type'] as string) || '',
        resolverParams: (d['params'] as Record<string, string>) || {},
        targetField: (d['target'] as string) || paramName,
      };
    });
  }

  private resolverBindingsToJson(bindings: ResolverBinding[]): Record<string, unknown> | null {
    if (bindings.length === 0) return null;
    const result: Record<string, unknown> = {};
    for (const b of bindings) {
      if (!b.paramName || !b.resolverType) continue;
      result[b.paramName] = {
        resolver_type: b.resolverType,
        params: b.resolverParams,
        target: b.targetField || b.paramName,
      };
    }
    return Object.keys(result).length > 0 ? result : null;
  }

  // ── Schema builders ───────────────────────────────────────────────

  addInputProperty(): void {
    this.inputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false, defaultValue: '', enumValues: '' },
    ]);
  }

  removeInputProperty(index: number): void {
    const name = this.inputProperties()[index]?.name;
    this.inputProperties.update(props => props.filter((_, i) => i !== index));
    if (name) {
      this.resolverBindings.update(bindings => bindings.filter(b => b.paramName !== name));
    }
  }

  addOutputProperty(): void {
    this.outputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false, defaultValue: '', enumValues: '' },
    ]);
  }

  removeOutputProperty(index: number): void {
    this.outputProperties.update(props => props.filter((_, i) => i !== index));
  }

  // ── Per-parameter binding helpers ────────────────────────────────

  private suggestionsCache = signal<Record<string, Array<{ resolver_id: string; resolver_type: string; display_name: string; matching_fields: string[] }>>>({});

  hasBinding(paramName: string): boolean {
    return this.resolverBindings().some(b => b.paramName === paramName);
  }

  getBinding(paramName: string): ResolverBinding | undefined {
    return this.resolverBindings().find(b => b.paramName === paramName);
  }

  enableBinding(paramName: string, fieldType: string): void {
    if (this.hasBinding(paramName)) return;
    this.resolverBindings.update(bindings => [
      ...bindings,
      { paramName, resolverType: '', resolverParams: {}, targetField: paramName },
    ]);
    this.loadSuggestions(paramName, fieldType);
  }

  removeBinding(paramName: string): void {
    if (!this.hasBinding(paramName)) return;
    this.resolverBindings.update(bindings => bindings.filter(b => b.paramName !== paramName));
  }

  loadSuggestions(paramName: string, fieldType: string): void {
    const pid = this.providerId || undefined;
    this.componentService.suggestResolversForField(fieldType, pid).subscribe({
      next: (suggestions) => {
        this.suggestionsCache.update(cache => ({ ...cache, [paramName]: suggestions }));
        this.cdr.markForCheck();
      },
    });
  }

  getSuggestions(paramName: string): Array<{ resolver_id: string; resolver_type: string; display_name: string; matching_fields: string[] }> {
    return this.suggestionsCache()[paramName] || [];
  }

  applySuggestion(binding: ResolverBinding, suggestion: { resolver_type: string; matching_fields: string[] }): void {
    binding.resolverType = suggestion.resolver_type;
    binding.resolverParams = {};
    if (suggestion.matching_fields.length > 0) {
      binding.targetField = suggestion.matching_fields[0];
    }
  }

  getResolverByType(type: string): Resolver | undefined {
    return this.resolvers().find(r => r.resolverType === type);
  }

  onBindingResolverChange(binding: ResolverBinding): void {
    binding.resolverParams = {};
  }

  validateBindings(): void {
    const comp = this.component();
    if (!comp) return;
    this.componentService.validateResolverBindings(comp.id).subscribe({
      next: (warnings) => {
        this.bindingWarnings.set(warnings);
        if (warnings.length === 0) {
          this.toastService.success('All bindings are valid');
        }
      },
      error: () => this.toastService.error('Failed to validate bindings'),
    });
  }

  // ── Operations ───────────────────────────────────────────────────

  loadOperations(): void {
    const comp = this.component();
    if (!comp) return;
    // Load operations from the component's embedded list first
    this.operations.set(comp.operations || []);
    // Load workflow definitions filtered by applicability (semantic type + provider)
    this.loadApplicableWorkflows();
  }

  resetOpForm(): void {
    this.editingOpId.set(null);
    this.opForm = { displayName: '', description: '', workflowDefinitionId: '', downtimeMinutes: 0 };
    if (this.workflowDefinitions().length === 0) {
      this.loadApplicableWorkflows();
    }
  }

  editOperation(op: ComponentOperation): void {
    this.showOpForm.set(false);
    this.editingOpId.set(op.id);
    this.opForm = {
      displayName: op.displayName,
      description: op.description || '',
      workflowDefinitionId: op.workflowDefinitionId,
      downtimeMinutes: this.parseDowntimeMinutes(op.estimatedDowntime),
    };
    if (this.workflowDefinitions().length === 0) {
      this.loadApplicableWorkflows();
    }
  }

  getWorkflowName(id: string): string {
    const wf = this.workflowDefinitions().find(w => w.id === id);
    return wf?.name || '(linked workflow)';
  }

  parseDowntimeMinutes(downtime: EstimatedDowntime | string): number {
    if (!downtime || downtime === 'NONE') return 0;
    if (downtime === 'BRIEF') return 5;
    if (downtime === 'EXTENDED') return 30;
    const n = parseInt(downtime as string, 10);
    return isNaN(n) ? 0 : n;
  }

  private minutesToDowntime(minutes: number): EstimatedDowntime {
    if (minutes <= 0) return 'NONE';
    if (minutes <= 5) return 'BRIEF';
    return 'EXTENDED';
  }

  private toSlug(displayName: string): string {
    return displayName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  }

  private loadApplicableWorkflows(): void {
    const comp = this.component();
    if (comp?.semanticTypeId && comp?.providerId) {
      this.workflowService.listOperationWorkflows(comp.semanticTypeId, comp.providerId).subscribe({
        next: (defs) => {
          this.workflowDefinitions.set(defs.map(d => ({ id: d.id, name: d.name })));
          this.cdr.markForCheck();
        },
      });
    } else {
      // Fallback: load all active workflows
      this.workflowService.listDefinitions({ status: 'ACTIVE', limit: 500 }).subscribe({
        next: (defs) => {
          this.workflowDefinitions.set(defs.map(d => ({ id: d.id, name: d.name })));
          this.cdr.markForCheck();
        },
      });
    }
  }

  cancelOpForm(): void {
    this.showOpForm.set(false);
    this.editingOpId.set(null);
  }

  toggleOperationExpand(op: ComponentOperation): void {
    if (this.expandedOpId() === op.id) {
      this.expandedOpId.set(null);
      this.expandedWorkflow.set(null);
      return;
    }
    this.expandedOpId.set(op.id);
    this.expandedWorkflow.set(null);
    if (op.workflowDefinitionId) {
      this.workflowLoading.set(true);
      this.workflowService.getDefinition(op.workflowDefinitionId).subscribe({
        next: (wf) => {
          this.expandedWorkflow.set(wf);
          this.workflowLoading.set(false);
          this.cdr.markForCheck();
        },
        error: () => {
          this.workflowLoading.set(false);
          this.cdr.markForCheck();
        },
      });
    }
  }

  editWorkflow(workflowDefinitionId: string): void {
    this.router.navigate(['/workflows', 'definitions', workflowDefinitionId, 'edit']);
  }

  saveOperation(): void {
    const comp = this.component();
    if (!comp) return;
    if (!this.opForm.displayName || !this.opForm.workflowDefinitionId) {
      this.toastService.error('Display name and workflow are required');
      return;
    }

    this.opSaving.set(true);
    const providerMode = this.isProviderMode();
    const downtime = this.minutesToDowntime(this.opForm.downtimeMinutes);

    if (this.editingOpId()) {
      this.componentService.updateOperation(this.editingOpId()!, {
        displayName: this.opForm.displayName,
        name: this.toSlug(this.opForm.displayName),
        description: this.opForm.description || undefined,
        estimatedDowntime: downtime,
      }, providerMode).subscribe({
        next: (updated) => {
          this.operations.update(ops => ops.map(o => o.id === updated.id ? updated : o));
          this.editingOpId.set(null);
          this.opSaving.set(false);
          this.toastService.success('Operation updated');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.opSaving.set(false);
          this.toastService.error('Failed: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    } else {
      const input: ComponentOperationCreateInput = {
        name: this.toSlug(this.opForm.displayName),
        displayName: this.opForm.displayName,
        workflowDefinitionId: this.opForm.workflowDefinitionId,
        description: this.opForm.description || undefined,
        estimatedDowntime: downtime,
      };
      this.componentService.createOperation(comp.id, input, providerMode).subscribe({
        next: (created) => {
          this.operations.update(ops => [...ops, created]);
          this.showOpForm.set(false);
          this.opSaving.set(false);
          this.toastService.success('Operation created');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.opSaving.set(false);
          this.toastService.error('Failed: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    }
  }

  deleteOperation(op: ComponentOperation): void {
    if (!confirm(`Delete operation "${op.displayName}"?`)) return;
    this.componentService.deleteOperation(op.id, this.isProviderMode()).subscribe({
      next: () => {
        this.operations.update(ops => ops.filter(o => o.id !== op.id));
        this.toastService.success('Operation deleted');
        this.cdr.markForCheck();
      },
      error: (err) => this.toastService.error('Failed: ' + err.message),
    });
  }

  getSchemaFieldCount(schema: Record<string, unknown>): number {
    const props = schema['properties'] as Record<string, unknown> | undefined;
    return props ? Object.keys(props).length : 0;
  }

  // ── Version restore ───────────────────────────────────────────────

  restoreVersion(v: ComponentVersion): void {
    if (!confirm(`Restore code and schemas from v${v.version}? Current draft will be overwritten.`)) return;
    this.form.code = v.code;
    this.form.inputSchema = v.inputSchema;
    this.form.outputSchema = v.outputSchema;
    this.form.resolverBindings = v.resolverBindings;
    this.inputProperties.set(this.schemaToProperties(v.inputSchema));
    this.outputProperties.set(this.schemaToProperties(v.outputSchema));
    this.resolverBindings.set(this.parseResolverBindings(v.resolverBindings));

    // Force Monaco to re-render with new code
    this.editorVisible.set(false);
    setTimeout(() => {
      this.editorVisible.set(true);
      this.cdr.markForCheck();
    }, 50);

    this.activeTab.set('codeConfig');
    this.toastService.success(`Restored from v${v.version}. Save to persist.`);
    this.cdr.markForCheck();
  }

  // ── Save / Publish / Delete ───────────────────────────────────────

  save(): void {
    this.saving.set(true);
    const comp = this.component();
    const providerMode = this.isProviderMode();

    // Build schemas from structured editors
    const inputSchema = this.propertiesToSchema(this.inputProperties()) || undefined;
    const outputSchema = this.propertiesToSchema(this.outputProperties()) || undefined;
    const resolverBindings = this.resolverBindingsToJson(this.resolverBindings()) || undefined;

    if (comp) {
      this.componentService.updateComponent(comp.id, {
        name: this.form.name,
        displayName: this.form.displayName,
        description: this.form.description || undefined,
        code: this.form.code,
        language: 'python',
        inputSchema,
        outputSchema,
        resolverBindings,
      }, providerMode).subscribe({
        next: (updated) => {
          this.component.set(updated);
          this.saving.set(false);
          this.toastService.success('Component saved');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error('Failed to save: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    } else {
      if (!this.providerId) {
        this.saving.set(false);
        this.toastService.error('No provider available. Create a provider first.');
        return;
      }
      const input: ComponentCreateInput = {
        name: this.form.name,
        displayName: this.form.displayName,
        providerId: this.providerId,
        semanticTypeId: this.form.semanticTypeId,
        language: 'python',
        description: this.form.description || undefined,
        code: this.form.code,
        inputSchema,
        outputSchema,
        resolverBindings,
      };
      this.componentService.createComponent(input, providerMode).subscribe({
        next: (created) => {
          this.component.set(created);
          this.saving.set(false);
          this.toastService.success('Component created');
          this.router.navigate([this.basePath(), created.id, 'edit']);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error('Failed to create: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    }
  }

  publish(): void {
    const comp = this.component();
    if (!comp) return;

    this.componentService.publishComponent(comp.id, this.publishChangelog, this.isProviderMode()).subscribe({
      next: (updated) => {
        this.component.set(updated);
        this.versions.set(updated.versions || []);
        this.showPublishDialog.set(false);
        this.publishChangelog = '';
        this.toastService.success('Component published');
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.toastService.error('Failed to publish: ' + err.message);
      },
    });
  }

  confirmDelete(): void {
    const comp = this.component();
    if (!comp) return;
    if (!confirm('Are you sure you want to delete this component?')) return;

    this.componentService.deleteComponent(comp.id, this.isProviderMode()).subscribe({
      next: () => {
        this.toastService.success('Component deleted');
        this.router.navigate([this.basePath()]);
      },
    });
  }
}
