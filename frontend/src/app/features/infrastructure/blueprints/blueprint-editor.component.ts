/**
 * Overview: Tabbed blueprint editor with Composition, Variables, Workflows, HA, DR,
 *     Reservations, and Governance tabs. Supports publishing and archiving blueprints.
 * Architecture: Infrastructure blueprint editor UI (Section 8)
 * Dependencies: @angular/core, @angular/router, cluster.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper,
 *     tabbed interface for multi-faceted blueprint editing, HA/DR JSON Schema editors,
 *     reservation template form.
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import {
  ServiceCluster,
  StackBlueprintGovernance,
  StackWorkflow,
  StackVariableBinding,
  VariableBindingInput,
  ServiceClusterSlotCreateInput,
  ComponentReservationTemplate,
  ComponentReservationTemplateInput,
} from '@shared/models/cluster.model';

interface CompResFormEntry {
  reservationType: 'HOT_STANDBY' | 'WARM_STANDBY' | 'COLD_STANDBY' | 'PILOT_LIGHT';
  resourcePercentage: number;
  rtoSeconds: number | null;
  rpoSeconds: number | null;
  targetEnvLabel: string;
  targetProviderId: string;
  autoCreate: boolean;
}

type EditorTab = 'composition' | 'variables' | 'workflows' | 'ha' | 'dr' | 'reservations' | 'governance';

interface SchemaProperty {
  name: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
}

interface EditableBinding {
  _idx: number;
  direction: 'INPUT' | 'OUTPUT';
  variableName: string;
  targetNodeId: string;
  targetParameter: string;
  expressionMode: boolean;
}

@Component({
  selector: 'nimbus-blueprint-editor',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (loading()) {
          <div class="loading-state">Loading blueprint...</div>
        } @else if (!blueprint()) {
          <div class="empty-state">Blueprint not found.</div>
        } @else {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/provider/infrastructure/blueprints" class="breadcrumb-link">Blueprint Catalog</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ blueprint()!.displayName || blueprint()!.name }}</span>
              </div>
              <h1 class="page-title">{{ blueprint()!.displayName || blueprint()!.name }}</h1>
              @if (blueprint()!.description) {
                <p class="page-subtitle">{{ blueprint()!.description }}</p>
              }
            </div>
            <div class="header-actions">
              <span class="badge" [ngClass]="blueprint()!.isPublished ? 'badge-published' : 'badge-draft'">
                {{ blueprint()!.isPublished ? 'Published' : 'Draft' }}
              </span>
              <span class="version-label">v{{ blueprint()!.version }}</span>
              <button class="btn btn-outline" (click)="onCancel()">Cancel</button>
              <button
                *nimbusHasPermission="'infrastructure:blueprint:manage'"
                class="btn btn-secondary"
                (click)="onSaveDraft()"
                [disabled]="draftSaving()"
              >{{ draftSaving() ? 'Saving...' : 'Save Draft' }}</button>
              <button
                *nimbusHasPermission="'infrastructure:blueprint:manage'"
                class="btn btn-primary"
                (click)="showPublishDialog.set(true)"
              >Publish</button>
            </div>
          </div>

          <!-- Info Summary -->
          <div class="info-row">
            <div class="info-card">
              <div class="info-label">Components</div>
              <div class="info-value">{{ blueprint()!.blueprintComponents.length || 0 }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Slots</div>
              <div class="info-value">{{ blueprint()!.slots.length || 0 }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Variables</div>
              <div class="info-value">{{ blueprint()!.variableBindings.length || 0 }}</div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="tabs-bar">
            <button
              *ngFor="let tab of tabs"
              class="tab-btn"
              [class.tab-active]="activeTab() === tab.key"
              (click)="activeTab.set(tab.key)"
            >{{ tab.label }}</button>
          </div>

          <div class="tab-content">
            <!-- Tab: Composition -->
            @if (activeTab() === 'composition') {
              <div class="tab-panel">
                <!-- Slots Section -->
                <div class="section-header-row">
                  <div>
                    <h2 class="section-title">Slots</h2>
                    <p class="section-desc">Typed placement slots that define where components can be inserted.</p>
                  </div>
                  <button
                    *nimbusHasPermission="'infrastructure:blueprint:manage'"
                    class="btn btn-xs btn-outline"
                    (click)="showSlotForm.set(!showSlotForm())"
                  >{{ showSlotForm() ? 'Cancel' : '+ Add Slot' }}</button>
                </div>

                @if (showSlotForm()) {
                  <div class="inline-form-card">
                    <div class="form-row">
                      <div class="form-group">
                        <label class="form-label">Name *</label>
                        <input type="text" class="form-input" [(ngModel)]="slotForm.name" placeholder="e.g. database" />
                      </div>
                      <div class="form-group">
                        <label class="form-label">Display Name</label>
                        <input type="text" class="form-input" [(ngModel)]="slotForm.displayName" placeholder="e.g. Database Server" />
                      </div>
                    </div>
                    <div class="form-row">
                      <div class="form-group" style="grid-column: 1 / -1;">
                        <label class="form-label">Description</label>
                        <input type="text" class="form-input" [(ngModel)]="slotForm.description" placeholder="What this slot is for" />
                      </div>
                    </div>
                    <div class="form-row">
                      <div class="form-group">
                        <label class="form-label">Min Count</label>
                        <input type="number" class="form-input" [(ngModel)]="slotForm.minCount" min="0" />
                      </div>
                      <div class="form-group">
                        <label class="form-label">Max Count</label>
                        <input type="number" class="form-input" [(ngModel)]="slotForm.maxCount" min="0" placeholder="Unlimited" />
                      </div>
                    </div>
                    <div class="form-row">
                      <div class="form-group">
                        <label class="form-label">Sort Order</label>
                        <input type="number" class="form-input" [(ngModel)]="slotForm.sortOrder" min="0" />
                      </div>
                      <div class="form-group form-group-toggle">
                        <label class="toggle-label">
                          <input type="checkbox" [(ngModel)]="slotForm.isRequired" />
                          <span>Required</span>
                        </label>
                      </div>
                    </div>
                    <div class="editor-actions">
                      <button
                        class="btn btn-primary btn-sm"
                        (click)="onAddSlot()"
                        [disabled]="slotSaving() || !slotForm.name.trim()"
                      >{{ slotSaving() ? 'Adding...' : 'Add Slot' }}</button>
                    </div>
                  </div>
                }

                @if (blueprint()!.slots.length) {
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Display Name</th>
                        <th>Required</th>
                        <th>Min / Max</th>
                        <th>Sort</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (slot of blueprint()!.slots; track slot.id) {
                        <tr>
                          <td class="text-bold">{{ slot.name }}</td>
                          <td class="text-muted">{{ slot.displayName || '--' }}</td>
                          <td>
                            <span class="badge" [ngClass]="slot.isRequired ? 'badge-required' : 'badge-draft'">
                              {{ slot.isRequired ? 'Required' : 'Optional' }}
                            </span>
                          </td>
                          <td class="text-muted">{{ slot.minCount }} / {{ slot.maxCount ?? '∞' }}</td>
                          <td class="text-muted">{{ slot.sortOrder }}</td>
                          <td>
                            <button
                              *nimbusHasPermission="'infrastructure:blueprint:manage'"
                              class="btn-remove"
                              title="Remove slot"
                              (click)="onRemoveSlot(slot.id)"
                            >&times;</button>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="empty-state-sm">No slots defined yet.</div>
                }

                <!-- Components Section -->
                <div class="section-header-row" style="margin-top: 32px;">
                  <div>
                    <h2 class="section-title">Components</h2>
                    <p class="section-desc">Blueprint components and their variable bindings.</p>
                  </div>
                </div>

                @if (blueprint()!.blueprintComponents.length) {
                  @for (comp of blueprint()!.blueprintComponents; track comp.id) {
                    <div class="component-binding-card">
                      <div class="component-binding-header" (click)="toggleComponentExpansion(comp.nodeId)">
                        <span class="component-expand-icon">{{ expandedComponents().has(comp.nodeId) ? '▼' : '▶' }}</span>
                        <span class="component-binding-label">
                          <a class="link-primary" [routerLink]="'/provider/components/' + comp.componentId + '/edit'" (click)="$event.stopPropagation()">
                            {{ comp.label }}
                          </a>
                        </span>
                        <code class="code-value">{{ comp.nodeId }}</code>
                        <span class="text-muted" style="font-size: 0.8rem;">{{ comp.componentVersion != null ? 'v' + comp.componentVersion : '' }}</span>
                        <span class="badge" [ngClass]="comp.isOptional ? 'badge-draft' : 'badge-required'" style="margin-left: auto;">
                          {{ comp.isOptional ? 'Optional' : 'Required' }}
                        </span>
                        <span class="text-muted" style="font-size: 0.8rem;">Order: {{ comp.sortOrder }}</span>
                      </div>
                      @if (expandedComponents().has(comp.nodeId)) {
                        <div class="component-binding-body">
                          <!-- Input Bindings -->
                          <div class="binding-section">
                            <div class="binding-section-header">
                              <span class="binding-section-label">Input Bindings</span>
                              <button class="btn btn-xs btn-outline" (click)="addBinding(comp.nodeId, 'INPUT')">+ Add</button>
                            </div>
                            @if (getComponentBindings(comp.nodeId, 'INPUT').length === 0) {
                              <div class="empty-schema">No input bindings for this component.</div>
                            } @else {
                              <table class="data-table binding-table">
                                <thead>
                                  <tr>
                                    <th>Stack Variable</th>
                                    <th>Component Parameter</th>
                                    <th></th>
                                  </tr>
                                </thead>
                                <tbody>
                                  @for (b of getComponentBindings(comp.nodeId, 'INPUT'); track b._idx) {
                                    <tr>
                                      <td>
                                        <select class="form-select form-select-sm" [(ngModel)]="b.variableName">
                                          <option value="">-- Select --</option>
                                          @for (p of inputProperties(); track p.name) {
                                            <option [value]="p.name">{{ p.name }}</option>
                                          }
                                        </select>
                                      </td>
                                      <td>
                                        <div class="param-cell">
                                          @if (b.expressionMode) {
                                            <input type="text" class="form-input form-input-sm" [(ngModel)]="b.targetParameter"
                                              placeholder="Python expr, e.g. value.split(':')[0]" title="Python expression — stack variable value available as 'value'" />
                                          } @else {
                                            <select class="form-select form-select-sm" [(ngModel)]="b.targetParameter">
                                              <option value="">-- Select --</option>
                                              @for (param of getComponentParameterNames(comp); track param) {
                                                <option [value]="param">{{ param }}</option>
                                              }
                                            </select>
                                          }
                                          <button class="btn-mode-toggle" (click)="toggleExpressionMode(b)"
                                            [title]="b.expressionMode ? 'Switch to parameter dropdown' : 'Switch to Python expression'">
                                            {{ b.expressionMode ? 'fx' : 'fx' }}
                                          </button>
                                        </div>
                                      </td>
                                      <td><button class="btn-remove" (click)="removeBinding(b._idx)">&times;</button></td>
                                    </tr>
                                  }
                                </tbody>
                              </table>
                            }
                          </div>
                          <!-- Output Bindings -->
                          <div class="binding-section" style="margin-top: 16px;">
                            <div class="binding-section-header">
                              <span class="binding-section-label">Output Bindings</span>
                              <button class="btn btn-xs btn-outline" (click)="addBinding(comp.nodeId, 'OUTPUT')">+ Add</button>
                            </div>
                            @if (getComponentBindings(comp.nodeId, 'OUTPUT').length === 0) {
                              <div class="empty-schema">No output bindings for this component.</div>
                            } @else {
                              <table class="data-table binding-table">
                                <thead>
                                  <tr>
                                    <th>Stack Variable</th>
                                    <th>Component Parameter</th>
                                    <th></th>
                                  </tr>
                                </thead>
                                <tbody>
                                  @for (b of getComponentBindings(comp.nodeId, 'OUTPUT'); track b._idx) {
                                    <tr>
                                      <td>
                                        <select class="form-select form-select-sm" [(ngModel)]="b.variableName">
                                          <option value="">-- Select --</option>
                                          @for (p of outputProperties(); track p.name) {
                                            <option [value]="p.name">{{ p.name }}</option>
                                          }
                                        </select>
                                      </td>
                                      <td>
                                        <div class="param-cell">
                                          @if (b.expressionMode) {
                                            <input type="text" class="form-input form-input-sm" [(ngModel)]="b.targetParameter"
                                              placeholder="Python expr, e.g. value.upper()" title="Python expression — stack variable value available as 'value'" />
                                          } @else {
                                            <select class="form-select form-select-sm" [(ngModel)]="b.targetParameter">
                                              <option value="">-- Select --</option>
                                              @for (param of getComponentParameterNames(comp); track param) {
                                                <option [value]="param">{{ param }}</option>
                                              }
                                            </select>
                                          }
                                          <button class="btn-mode-toggle" (click)="toggleExpressionMode(b)"
                                            [title]="b.expressionMode ? 'Switch to parameter dropdown' : 'Switch to Python expression'">
                                            {{ b.expressionMode ? 'fx' : 'fx' }}
                                          </button>
                                        </div>
                                      </td>
                                      <td><button class="btn-remove" (click)="removeBinding(b._idx)">&times;</button></td>
                                    </tr>
                                  }
                                </tbody>
                              </table>
                            }
                          </div>
                          <div class="editor-actions">
                            <button
                              *nimbusHasPermission="'infrastructure:blueprint:manage'"
                              class="btn btn-primary btn-sm"
                              (click)="onSaveBindings()"
                              [disabled]="bindingsSaving()"
                            >{{ bindingsSaving() ? 'Saving...' : 'Save Bindings' }}</button>
                            @if (bindingsSaveMsg()) {
                              <span class="save-msg" [class.save-error]="bindingsSaveError()">{{ bindingsSaveMsg() }}</span>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  }
                } @else {
                  <div class="empty-state-sm">No components defined yet. Add components to build the stack composition.</div>
                }
              </div>
            }

            <!-- Tab: Variables -->
            @if (activeTab() === 'variables') {
              <div class="tab-panel">
                <!-- Input Parameters Schema -->
                <div class="schema-builder">
                  <div class="schema-header">
                    <span class="schema-label">Input Parameters</span>
                    <button class="btn btn-xs btn-outline" (click)="addInputProperty()">+ Add</button>
                  </div>
                  @if (inputProperties().length === 0) {
                    <div class="empty-schema">No input parameters defined.</div>
                  }
                  @for (prop of inputProperties(); track prop; let i = $index) {
                    <div class="schema-row">
                      <div class="schema-row-top">
                        <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="param_name" (ngModelChange)="onInputSchemaChange()" />
                        <select class="schema-type" [(ngModel)]="prop.type" (ngModelChange)="onInputSchemaChange()">
                          <option value="string">String</option>
                          <option value="integer">Integer</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                          <option value="object">Object</option>
                          <option value="array">Array</option>
                        </select>
                        <label class="schema-req" title="Required">
                          <input type="checkbox" [(ngModel)]="prop.required" (ngModelChange)="onInputSchemaChange()" />
                        </label>
                        <button class="btn-remove" (click)="removeInputProperty(i)" title="Remove">&times;</button>
                      </div>
                      <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" (ngModelChange)="onInputSchemaChange()" />
                    </div>
                  }
                </div>

                <!-- Output Parameters Schema -->
                <div class="schema-builder" style="margin-top: 24px;">
                  <div class="schema-header">
                    <span class="schema-label">Output Parameters</span>
                    <button class="btn btn-xs btn-outline" (click)="addOutputProperty()">+ Add</button>
                  </div>
                  @if (outputProperties().length === 0) {
                    <div class="empty-schema">No output parameters defined.</div>
                  }
                  @for (prop of outputProperties(); track prop; let i = $index) {
                    <div class="schema-row">
                      <div class="schema-row-top">
                        <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="field_name" (ngModelChange)="onOutputSchemaChange()" />
                        <select class="schema-type" [(ngModel)]="prop.type" (ngModelChange)="onOutputSchemaChange()">
                          <option value="string">String</option>
                          <option value="integer">Integer</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                          <option value="object">Object</option>
                          <option value="array">Array</option>
                        </select>
                        <label class="schema-req" title="Required">
                          <input type="checkbox" [(ngModel)]="prop.required" (ngModelChange)="onOutputSchemaChange()" />
                        </label>
                        <button class="btn-remove" (click)="removeOutputProperty(i)" title="Remove">&times;</button>
                      </div>
                      <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" (ngModelChange)="onOutputSchemaChange()" />
                    </div>
                  }
                </div>

                <div class="editor-actions" style="margin-top: 16px;">
                  <button
                    *nimbusHasPermission="'infrastructure:blueprint:manage'"
                    class="btn btn-primary"
                    (click)="onSaveSchemas()"
                    [disabled]="schemaSaving()"
                  >{{ schemaSaving() ? 'Saving...' : 'Save Schemas' }}</button>
                  @if (schemaSaveMsg()) {
                    <span class="save-msg" [class.save-error]="schemaSaveError()">{{ schemaSaveMsg() }}</span>
                  }
                </div>

              </div>
            }

            <!-- Tab: Workflows -->
            @if (activeTab() === 'workflows') {
              <div class="tab-panel">
                <h2 class="section-title">Stack Workflows</h2>
                <p class="section-desc">Operational workflows bound to this blueprint for provisioning, scaling, backup, and more.</p>
                @if (workflowsLoading()) {
                  <div class="loading-state-sm">Loading workflows...</div>
                } @else if (workflows().length) {
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Kind</th>
                        <th>Required</th>
                        <th>Sort</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (wf of workflows(); track wf.id) {
                        <tr>
                          <td class="text-bold">{{ wf.displayName || wf.name }}</td>
                          <td>
                            <span class="badge badge-kind">{{ wf.workflowKind }}</span>
                          </td>
                          <td>
                            <span class="badge" [ngClass]="wf.isRequired ? 'badge-required' : 'badge-draft'">
                              {{ wf.isRequired ? 'Required' : 'Optional' }}
                            </span>
                          </td>
                          <td class="text-muted">{{ wf.sortOrder }}</td>
                          <td>
                            <button
                              class="btn btn-xs btn-outline"
                              (click)="onResetWorkflow(wf.id)"
                              [disabled]="workflowsSaving()"
                            >Reset to Default</button>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="empty-state-sm">No workflows bound to this blueprint.</div>
                }
              </div>
            }

            <!-- Tab: HA -->
            @if (activeTab() === 'ha') {
              <div class="tab-panel">
                <h2 class="section-title">High Availability</h2>
                <p class="section-desc">Define the HA configuration schema and default values for this blueprint.</p>

                <div class="schema-builder">
                  <div class="schema-header">
                    <span class="schema-label">HA Config Schema</span>
                    <button class="btn btn-xs btn-outline" (click)="addHaSchemaProperty()">+ Add</button>
                  </div>
                  @if (haSchemaProperties().length === 0) {
                    <div class="empty-schema">No HA configuration fields defined.</div>
                  }
                  @for (prop of haSchemaProperties(); track prop; let i = $index) {
                    <div class="schema-row">
                      <div class="schema-row-top">
                        <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="field_name" />
                        <select class="schema-type" [(ngModel)]="prop.type">
                          <option value="string">String</option>
                          <option value="integer">Integer</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                          <option value="object">Object</option>
                          <option value="array">Array</option>
                        </select>
                        <label class="schema-req" title="Required">
                          <input type="checkbox" [(ngModel)]="prop.required" />
                        </label>
                        <button class="btn-remove" (click)="removeHaSchemaProperty(i)" title="Remove">&times;</button>
                      </div>
                      <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" />
                    </div>
                  }
                </div>

                <div class="schema-builder" style="margin-top: 20px;">
                  <div class="schema-header">
                    <span class="schema-label">HA Default Values</span>
                  </div>
                  @if (haSchemaProperties().length === 0) {
                    <div class="empty-schema">Add schema fields above to configure defaults.</div>
                  } @else {
                    <div class="defaults-grid">
                      @for (prop of haSchemaProperties(); track prop.name) {
                        <div class="defaults-row">
                          <input type="text" class="defaults-key" [value]="prop.name" readonly />
                          <input type="text" class="defaults-value" [(ngModel)]="haDefaults()[prop.name]" [placeholder]="prop.type" />
                        </div>
                      }
                    </div>
                  }
                </div>

                <div class="editor-actions">
                  <button
                    *nimbusHasPermission="'infrastructure:blueprint:manage'"
                    class="btn btn-primary"
                    (click)="onSaveHaConfig()"
                    [disabled]="configSaving()"
                  >{{ configSaving() ? 'Saving...' : 'Save HA Configuration' }}</button>
                  @if (configSaveMsg()) {
                    <span class="save-msg" [class.save-error]="configSaveError()">{{ configSaveMsg() }}</span>
                  }
                </div>
              </div>
            }

            <!-- Tab: DR -->
            @if (activeTab() === 'dr') {
              <div class="tab-panel">
                <h2 class="section-title">Disaster Recovery</h2>
                <p class="section-desc">Define the DR configuration schema and default values for this blueprint.</p>

                <div class="schema-builder">
                  <div class="schema-header">
                    <span class="schema-label">DR Config Schema</span>
                    <button class="btn btn-xs btn-outline" (click)="addDrSchemaProperty()">+ Add</button>
                  </div>
                  @if (drSchemaProperties().length === 0) {
                    <div class="empty-schema">No DR configuration fields defined.</div>
                  }
                  @for (prop of drSchemaProperties(); track prop; let i = $index) {
                    <div class="schema-row">
                      <div class="schema-row-top">
                        <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="field_name" />
                        <select class="schema-type" [(ngModel)]="prop.type">
                          <option value="string">String</option>
                          <option value="integer">Integer</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                          <option value="object">Object</option>
                          <option value="array">Array</option>
                        </select>
                        <label class="schema-req" title="Required">
                          <input type="checkbox" [(ngModel)]="prop.required" />
                        </label>
                        <button class="btn-remove" (click)="removeDrSchemaProperty(i)" title="Remove">&times;</button>
                      </div>
                      <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" />
                    </div>
                  }
                </div>

                <div class="schema-builder" style="margin-top: 20px;">
                  <div class="schema-header">
                    <span class="schema-label">DR Default Values</span>
                  </div>
                  @if (drSchemaProperties().length === 0) {
                    <div class="empty-schema">Add schema fields above to configure defaults.</div>
                  } @else {
                    <div class="defaults-grid">
                      @for (prop of drSchemaProperties(); track prop.name) {
                        <div class="defaults-row">
                          <input type="text" class="defaults-key" [value]="prop.name" readonly />
                          <input type="text" class="defaults-value" [(ngModel)]="drDefaults()[prop.name]" [placeholder]="prop.type" />
                        </div>
                      }
                    </div>
                  }
                </div>

                <div class="editor-actions">
                  <button
                    *nimbusHasPermission="'infrastructure:blueprint:manage'"
                    class="btn btn-primary"
                    (click)="onSaveDrConfig()"
                    [disabled]="configSaving()"
                  >{{ configSaving() ? 'Saving...' : 'Save DR Configuration' }}</button>
                  @if (configSaveMsg()) {
                    <span class="save-msg" [class.save-error]="configSaveError()">{{ configSaveMsg() }}</span>
                  }
                </div>
              </div>
            }

            <!-- Tab: Reservations -->
            @if (activeTab() === 'reservations') {
              <div class="tab-panel">
                <h2 class="section-title">Per-Component Reservations</h2>
                <p class="section-desc">Configure DR reservation settings for each component in the blueprint.</p>
                @if (resSaveMsg()) {
                  <div class="save-msg-block" [class.save-error]="resSaveError()">{{ resSaveMsg() }}</div>
                }
                @if (blueprint()!.blueprintComponents.length === 0) {
                  <div class="empty-state-sm">No components in this blueprint. Add components in the Composition tab first.</div>
                } @else {
                  @for (comp of blueprint()!.blueprintComponents; track comp.id) {
                    <div class="component-res-card">
                      <div class="component-res-header" (click)="toggleComponentRes(comp.id)">
                        <span class="component-res-label">{{ comp.label }}</span>
                        <span class="component-res-status">
                          @if (getCompResTemplate(comp.id)) {
                            <span class="badge badge-published">Configured</span>
                          } @else {
                            <span class="badge badge-draft">Not configured</span>
                          }
                        </span>
                        <span class="component-res-toggle">{{ expandedComponentRes().has(comp.id) ? '−' : '+' }}</span>
                      </div>
                      @if (expandedComponentRes().has(comp.id)) {
                        <div class="component-res-body">
                          <div class="reservation-form">
                            <div class="form-row">
                              <div class="form-group">
                                <label class="form-label">Reservation Type</label>
                                <select class="form-select" [(ngModel)]="compResFormData()[comp.id].reservationType">
                                  <option value="HOT_STANDBY">Hot Standby</option>
                                  <option value="WARM_STANDBY">Warm Standby</option>
                                  <option value="COLD_STANDBY">Cold Standby</option>
                                  <option value="PILOT_LIGHT">Pilot Light</option>
                                </select>
                              </div>
                              <div class="form-group">
                                <label class="form-label">Resource Percentage</label>
                                <div class="slider-row">
                                  <input type="range" min="0" max="100" step="5" class="form-range" [(ngModel)]="compResFormData()[comp.id].resourcePercentage" />
                                  <span class="slider-value">{{ compResFormData()[comp.id].resourcePercentage }}%</span>
                                </div>
                              </div>
                            </div>
                            <div class="form-row">
                              <div class="form-group">
                                <label class="form-label">RTO (seconds)</label>
                                <input type="number" class="form-input" [(ngModel)]="compResFormData()[comp.id].rtoSeconds" placeholder="e.g. 300" />
                              </div>
                              <div class="form-group">
                                <label class="form-label">RPO (seconds)</label>
                                <input type="number" class="form-input" [(ngModel)]="compResFormData()[comp.id].rpoSeconds" placeholder="e.g. 60" />
                              </div>
                            </div>
                            <div class="form-row">
                              <div class="form-group">
                                <label class="form-label">Target Environment Label</label>
                                <input type="text" class="form-input" [(ngModel)]="compResFormData()[comp.id].targetEnvLabel" placeholder="e.g. dr-region-west" />
                              </div>
                              <div class="form-group">
                                <label class="form-label">Target Provider ID</label>
                                <input type="text" class="form-input" [(ngModel)]="compResFormData()[comp.id].targetProviderId" placeholder="UUID (optional)" />
                              </div>
                            </div>
                            <div class="form-row">
                              <div class="form-group form-group-toggle">
                                <label class="toggle-label">
                                  <input type="checkbox" [(ngModel)]="compResFormData()[comp.id].autoCreate" />
                                  <span>Auto-create reservation on deploy</span>
                                </label>
                              </div>
                            </div>
                            <div class="editor-actions">
                              <button
                                *nimbusHasPermission="'infrastructure:blueprint:manage'"
                                class="btn btn-primary btn-sm"
                                (click)="onSaveComponentRes(comp.id)"
                                [disabled]="resSaving()"
                              >Save</button>
                              @if (getCompResTemplate(comp.id)) {
                                <button
                                  *nimbusHasPermission="'infrastructure:blueprint:manage'"
                                  class="btn btn-outline btn-danger-outline btn-sm"
                                  (click)="onRemoveComponentRes(comp.id)"
                                  [disabled]="resSaving()"
                                >Remove</button>
                              }
                            </div>
                          </div>
                        </div>
                      }
                    </div>
                  }
                }
              </div>
            }

            <!-- Tab: Governance -->
            @if (activeTab() === 'governance') {
              <div class="tab-panel">
                <h2 class="section-title">Governance Rules</h2>
                <p class="section-desc">Tenant-level governance controls for blueprint usage, parameter constraints, and instance limits.</p>
                @if (governanceLoading()) {
                  <div class="loading-state-sm">Loading governance rules...</div>
                } @else if (governanceRules().length) {
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Tenant ID</th>
                        <th>Allowed</th>
                        <th>Max Instances</th>
                        <th>Constraints</th>
                        <th>Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (rule of governanceRules(); track rule.id) {
                        <tr>
                          <td class="text-muted">{{ rule.tenantId }}</td>
                          <td>
                            <span class="badge" [ngClass]="rule.isAllowed ? 'badge-published' : 'badge-denied'">
                              {{ rule.isAllowed ? 'Allowed' : 'Denied' }}
                            </span>
                          </td>
                          <td>{{ rule.maxInstances ?? 'Unlimited' }}</td>
                          <td class="text-muted">{{ rule.parameterConstraints ? 'Configured' : '--' }}</td>
                          <td class="text-muted">{{ rule.updatedAt | date:'mediumDate' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="empty-state-sm">No governance rules configured. All tenants can use this blueprint by default.</div>
                }
              </div>
            }
          </div>
        }

        @if (showPublishDialog()) {
          <div class="dialog-overlay" (click)="showPublishDialog.set(false)">
            <div class="dialog" (click)="$event.stopPropagation()">
              <h3>Publish Blueprint</h3>
              <p>This will create an immutable version snapshot (v{{ blueprint()!.version }}).</p>
              <label>Changelog</label>
              <textarea rows="4" [(ngModel)]="publishChangelog" placeholder="What changed in this version?"></textarea>
              <div class="dialog-actions">
                <button class="btn btn-secondary" (click)="showPublishDialog.set(false)">Cancel</button>
                <button class="btn btn-primary" (click)="onPublish()">Publish</button>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .breadcrumb { font-size: 0.8rem; color: #64748b; margin-bottom: 2px; }
    .breadcrumb-link { color: #3b82f6; text-decoration: none; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { margin: 0 4px; }
    .header-actions { display: flex; gap: 8px; align-items: center; }
    .version-label { font-size: 0.85rem; font-weight: 600; color: #475569; padding: 4px 10px; background: #f1f5f9; border-radius: 4px; }

    .info-row { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .info-card {
      flex: 1; min-width: 140px; padding: 16px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .info-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .info-value { font-size: 1.1rem; font-weight: 600; color: #1e293b; }

    .tabs-bar {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 0;
    }
    .tab-btn {
      padding: 10px 20px; font-size: 0.875rem; font-weight: 500; color: #64748b;
      background: none; border: none; border-bottom: 2px solid transparent;
      margin-bottom: -2px; cursor: pointer; transition: all 0.15s;
    }
    .tab-btn:hover { color: #1e293b; }
    .tab-active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { background: #fff; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px; }
    .tab-panel { padding: 24px; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0 0 4px; }
    .section-desc { font-size: 0.85rem; color: #64748b; margin: 0 0 16px; }
    .section-actions { margin-bottom: 16px; }

    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 10px 14px; font-size: 0.75rem; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.875rem; }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover { background: #f8fafc; }
    .text-bold { font-weight: 500; }
    .text-muted { color: #64748b; }
    .link-primary { color: #3b82f6; font-weight: 500; text-decoration: none; cursor: pointer; }
    .link-primary:hover { text-decoration: underline; }
    .code-value { font-size: 0.8rem; font-family: monospace; color: #0284c7; background: #f0f9ff; padding: 1px 5px; border-radius: 3px; }

    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
    }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-draft { background: #f1f5f9; color: #475569; }
    .badge-required { background: #fef3c7; color: #92400e; }
    .badge-denied { background: #fef2f2; color: #991b1b; }
    .badge-input { background: #eff6ff; color: #1d4ed8; }
    .badge-output { background: #f0fdf4; color: #166534; }
    .badge-kind { background: #f5f3ff; color: #5b21b6; }

    .placeholder-card {
      text-align: center; padding: 40px 24px; background: #f8fafc; border: 1px dashed #e2e8f0;
      border-radius: 8px; color: #64748b;
    }
    .placeholder-icon { font-size: 2rem; margin-bottom: 8px; }
    .placeholder-card p { margin: 0 0 16px; font-size: 0.875rem; }

    .empty-state-sm { padding: 32px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
    .loading-state-sm { padding: 24px; text-align: center; color: #64748b; font-size: 0.85rem; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }

    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn-xs { padding: 3px 8px; font-size: 0.75rem; }
    .btn-danger-outline { color: #dc2626; border-color: #fecaca; }
    .btn-danger-outline:hover { background: #fef2f2; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Schema editor grid */
    .schema-editor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    .schema-editor-col { min-width: 0; }
    .editor-label { font-size: 0.8rem; font-weight: 600; color: #475569; margin-bottom: 6px; }
    .editor-actions { display: flex; gap: 10px; align-items: center; margin-top: 16px; }
    .save-msg { font-size: 0.8rem; color: #16a34a; font-weight: 500; }
    .save-msg.save-error { color: #dc2626; }

    /* Reservation form */
    .reservation-form { max-width: 700px; }
    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    .form-group { display: flex; flex-direction: column; }
    .form-group-toggle { justify-content: flex-end; }
    .form-label { font-size: 0.8rem; font-weight: 600; color: #475569; margin-bottom: 6px; }
    .form-input, .form-select {
      padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff;
    }
    .form-input:focus, .form-select:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .form-range { flex: 1; }
    .slider-row { display: flex; align-items: center; gap: 10px; }
    .slider-value { font-size: 0.875rem; font-weight: 600; color: #1e293b; min-width: 40px; }
    .toggle-label { display: flex; align-items: center; gap: 8px; font-size: 0.875rem; color: #1e293b; cursor: pointer; }
    .toggle-label input[type="checkbox"] { width: 16px; height: 16px; accent-color: #3b82f6; }

    /* Schema builder */
    .schema-builder { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
    .schema-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .schema-label { font-size: 0.85rem; font-weight: 600; color: #1e293b; }
    .empty-schema { padding: 16px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
    .schema-row { background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
    .schema-row-top { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
    .schema-name {
      flex: 1; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; font-family: monospace;
    }
    .schema-type {
      width: 100px; padding: 5px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; background: #fff;
    }
    .schema-req { display: flex; align-items: center; cursor: pointer; }
    .schema-req input { width: 14px; height: 14px; accent-color: #3b82f6; }
    .schema-desc {
      width: 100%; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #64748b;
    }
    .btn-remove {
      background: none; border: none; color: #94a3b8; font-size: 1.1rem; cursor: pointer;
      padding: 0 4px; line-height: 1;
    }
    .btn-remove:hover { color: #dc2626; }

    /* Defaults editor */
    .defaults-grid { display: grid; gap: 8px; }
    .defaults-row { display: flex; gap: 8px; align-items: center; }
    .defaults-key {
      width: 180px; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; font-family: monospace; background: #f1f5f9;
    }
    .defaults-value {
      flex: 1; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b;
    }

    /* Per-component reservation cards */
    .component-res-card {
      border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 12px;
      background: #fff; overflow: hidden;
    }
    .component-res-header {
      display: flex; align-items: center; gap: 10px; padding: 12px 16px;
      cursor: pointer; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
      transition: background 0.15s;
    }
    .component-res-header:hover { background: #f1f5f9; }
    .component-res-label { flex: 1; font-weight: 500; color: #1e293b; font-size: 0.875rem; }
    .component-res-status { font-size: 0.75rem; }
    .component-res-toggle { font-size: 1.2rem; color: #64748b; font-weight: 600; width: 20px; text-align: center; }
    .component-res-body { padding: 16px; }
    .save-msg-block {
      padding: 8px 12px; margin-bottom: 12px; border-radius: 6px;
      font-size: 0.8rem; font-weight: 500;
      background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0;
    }
    .save-msg-block.save-error {
      background: #fef2f2; color: #dc2626; border-color: #fecaca;
    }

    .btn-secondary { background: #f1f5f9; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #e2e8f0; }

    /* Publish dialog */
    .dialog-overlay {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.4); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 12px; padding: 24px; width: 440px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }
    .dialog h3 { margin: 0 0 8px; font-size: 1.1rem; font-weight: 600; color: #1e293b; }
    .dialog p { margin: 0 0 16px; font-size: 0.875rem; color: #64748b; }
    .dialog label { font-size: 0.8rem; font-weight: 600; color: #475569; display: block; margin-bottom: 6px; }
    .dialog textarea {
      width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; resize: vertical; box-sizing: border-box;
    }
    .dialog textarea:focus { outline: none; border-color: #3b82f6; }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

    /* Section header with action button */
    .section-header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }

    /* Inline form card */
    .inline-form-card {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 16px; margin-bottom: 16px;
    }

    /* Expandable component binding cards */
    .component-binding-card {
      border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px;
      background: #fff; overflow: hidden;
    }
    .component-binding-header {
      display: flex; align-items: center; gap: 10px; padding: 10px 14px;
      cursor: pointer; transition: background 0.15s;
    }
    .component-binding-header:hover { background: #f8fafc; }
    .component-expand-icon { font-size: 0.7rem; color: #64748b; width: 14px; flex-shrink: 0; }
    .component-binding-label { font-weight: 500; color: #1e293b; font-size: 0.875rem; }
    .component-binding-body { padding: 0 16px 16px; border-top: 1px solid #f1f5f9; }

    /* Binding sub-sections */
    .binding-section {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 12px; margin-top: 12px;
    }
    .binding-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .binding-section-label { font-size: 0.8rem; font-weight: 600; color: #475569; }
    .binding-table { font-size: 0.8125rem; }
    .binding-table th { padding: 6px 10px; font-size: 0.7rem; }
    .binding-table td { padding: 6px 10px; }
    .form-select-sm, .form-input-sm {
      padding: 4px 8px; font-size: 0.8125rem; border: 1px solid #d1d5db;
      border-radius: 4px; color: #1e293b; background: #fff; width: 100%;
    }
    .form-select-sm:focus, .form-input-sm:focus { outline: none; border-color: #3b82f6; }

    /* Dual-mode parameter cell */
    .param-cell { display: flex; align-items: center; gap: 4px; }
    .param-cell select, .param-cell input { flex: 1; min-width: 0; }
    .btn-mode-toggle {
      background: none; border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 6px;
      font-size: 0.7rem; font-weight: 700; font-style: italic; color: #64748b;
      cursor: pointer; white-space: nowrap; line-height: 1.4;
    }
    .btn-mode-toggle:hover { background: #f1f5f9; color: #3b82f6; border-color: #3b82f6; }
  `],
})
export class BlueprintEditorComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clusterService = inject(ClusterService);

  blueprint = signal<ServiceCluster | null>(null);
  loading = signal(false);
  draftSaving = signal(false);
  showPublishDialog = signal(false);
  publishChangelog = '';
  activeTab = signal<EditorTab>('composition');
  workflows = signal<StackWorkflow[]>([]);
  workflowsLoading = signal(false);
  workflowsSaving = signal(false);
  governanceRules = signal<StackBlueprintGovernance[]>([]);
  governanceLoading = signal(false);

  // Schema builder state
  inputProperties = signal<SchemaProperty[]>([]);
  outputProperties = signal<SchemaProperty[]>([]);
  schemaSaving = signal(false);
  schemaSaveMsg = signal('');
  schemaSaveError = signal(false);

  // HA/DR config editor state
  haSchemaProperties = signal<SchemaProperty[]>([]);
  haDefaults = signal<Record<string, string>>({});
  drSchemaProperties = signal<SchemaProperty[]>([]);
  drDefaults = signal<Record<string, string>>({});
  configSaving = signal(false);
  configSaveMsg = signal('');
  configSaveError = signal(false);

  // Per-component reservation state
  expandedComponentRes = signal<Set<string>>(new Set());
  compResFormData = signal<Record<string, CompResFormEntry>>({});
  compResTemplates = signal<Record<string, ComponentReservationTemplate>>({});
  resSaving = signal(false);
  resSaveMsg = signal('');
  resSaveError = signal(false);

  // Slot form state
  showSlotForm = signal(false);
  slotSaving = signal(false);
  slotForm: ServiceClusterSlotCreateInput & { isRequired: boolean } = {
    name: '', displayName: '', description: '', minCount: 1, maxCount: undefined,
    isRequired: true, sortOrder: 0,
  };

  // Expandable component bindings state
  expandedComponents = signal<Set<string>>(new Set());
  editableBindings = signal<EditableBinding[]>([]);
  bindingsSaving = signal(false);
  bindingsSaveMsg = signal('');
  bindingsSaveError = signal(false);

  tabs: { key: EditorTab; label: string }[] = [
    { key: 'composition', label: 'Composition' },
    { key: 'variables', label: 'Variables' },
    { key: 'workflows', label: 'Workflows' },
    { key: 'ha', label: 'HA' },
    { key: 'dr', label: 'DR' },
    { key: 'reservations', label: 'Reservations' },
    { key: 'governance', label: 'Governance' },
  ];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadBlueprint(id);
    }
  }

  loadBlueprint(id: string): void {
    this.loading.set(true);
    this.clusterService.getCluster(id).subscribe({
      next: (bp) => {
        this.blueprint.set(bp);
        this.loading.set(false);
        if (bp) {
          this.loadGovernance(bp.id);
          this.loadWorkflows(bp.id);
          this.populateConfigEditors(bp);
          this.loadComponentReservationTemplates(bp.id, bp);
          this.inputProperties.set(this.schemaToProperties(bp.inputSchema));
          this.outputProperties.set(this.schemaToProperties(bp.outputSchema));
          this.initEditableBindings(bp.variableBindings);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  private populateConfigEditors(bp: ServiceCluster): void {
    this.haSchemaProperties.set(this.schemaToProperties(bp.haConfigSchema));
    this.haDefaults.set(this.flattenDefaults(bp.haConfigDefaults));
    this.drSchemaProperties.set(this.schemaToProperties(bp.drConfigSchema));
    this.drDefaults.set(this.flattenDefaults(bp.drConfigDefaults));
  }

  private flattenDefaults(defaults: Record<string, unknown> | null): Record<string, string> {
    if (!defaults) return {};
    const flat: Record<string, string> = {};
    for (const [key, value] of Object.entries(defaults)) {
      flat[key] = value != null ? String(value) : '';
    }
    return flat;
  }

  private unflattenDefaults(flat: Record<string, string>, properties: SchemaProperty[]): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const prop of properties) {
      if (!prop.name) continue;
      const val = flat[prop.name];
      if (val === undefined || val === '') continue;
      switch (prop.type) {
        case 'integer': result[prop.name] = parseInt(val, 10) || 0; break;
        case 'number': result[prop.name] = parseFloat(val) || 0; break;
        case 'boolean': result[prop.name] = val === 'true'; break;
        default: result[prop.name] = val;
      }
    }
    return result;
  }

  loadComponentReservationTemplates(blueprintId: string, bp: ServiceCluster): void {
    this.clusterService.listComponentReservationTemplates(blueprintId).subscribe({
      next: (templates) => {
        const templateMap: Record<string, ComponentReservationTemplate> = {};
        const formData: Record<string, CompResFormEntry> = {};
        for (const tmpl of templates) {
          templateMap[tmpl.blueprintComponentId] = tmpl;
        }
        for (const comp of bp.blueprintComponents) {
          const existing = templateMap[comp.id];
          formData[comp.id] = existing
            ? {
                reservationType: existing.reservationType,
                resourcePercentage: existing.resourcePercentage,
                rtoSeconds: existing.rtoSeconds,
                rpoSeconds: existing.rpoSeconds,
                targetEnvLabel: existing.targetEnvironmentLabel || '',
                targetProviderId: existing.targetProviderId || '',
                autoCreate: existing.autoCreateOnDeploy,
              }
            : {
                reservationType: 'WARM_STANDBY',
                resourcePercentage: 80,
                rtoSeconds: null,
                rpoSeconds: null,
                targetEnvLabel: '',
                targetProviderId: '',
                autoCreate: true,
              };
        }
        this.compResTemplates.set(templateMap);
        this.compResFormData.set(formData);
      },
    });
  }

  toggleComponentRes(componentId: string): void {
    this.expandedComponentRes.update(set => {
      const next = new Set(set);
      if (next.has(componentId)) {
        next.delete(componentId);
      } else {
        next.add(componentId);
      }
      return next;
    });
  }

  getCompResTemplate(componentId: string): ComponentReservationTemplate | null {
    return this.compResTemplates()[componentId] || null;
  }

  loadGovernance(blueprintId: string): void {
    this.governanceLoading.set(true);
    this.clusterService.listBlueprintGovernance(blueprintId).subscribe({
      next: (rules) => {
        this.governanceRules.set(rules);
        this.governanceLoading.set(false);
      },
      error: () => this.governanceLoading.set(false),
    });
  }

  loadWorkflows(blueprintId: string): void {
    this.workflowsLoading.set(true);
    this.clusterService.listBlueprintWorkflows(blueprintId).subscribe({
      next: (wfs) => {
        this.workflows.set(wfs);
        this.workflowsLoading.set(false);
      },
      error: () => this.workflowsLoading.set(false),
    });
  }

  onCancel(): void {
    this.router.navigate(['/provider/infrastructure/blueprints']);
  }

  onSaveDraft(): void {
    if (!this.blueprint()) return;
    this.draftSaving.set(true);
    this.clusterService.updateCluster(this.blueprint()!.id, {
      name: this.blueprint()!.name,
      description: this.blueprint()!.description || undefined,
    }).subscribe({
      next: (updated) => {
        this.blueprint.set(updated);
        this.draftSaving.set(false);
      },
      error: () => this.draftSaving.set(false),
    });
  }

  onPublish(): void {
    if (!this.blueprint()) return;
    const changelog = this.publishChangelog.trim() || undefined;
    this.clusterService.publishBlueprint(this.blueprint()!.id, changelog).subscribe({
      next: () => {
        this.showPublishDialog.set(false);
        this.publishChangelog = '';
        this.loadBlueprint(this.blueprint()!.id);
      },
    });
  }

  onResetWorkflow(workflowId: string): void {
    if (!this.blueprint()) return;
    this.workflowsSaving.set(true);
    this.clusterService.resetStackWorkflow(workflowId, this.blueprint()!.id).subscribe({
      next: (wf) => {
        this.workflows.update((wfs) => wfs.map((w) => (w.id === workflowId ? wf : w)));
        this.workflowsSaving.set(false);
      },
      error: () => this.workflowsSaving.set(false),
    });
  }

  onSaveHaConfig(): void {
    if (!this.blueprint()) return;
    this.configSaving.set(true);
    this.configSaveMsg.set('');
    const schema = this.propertiesToSchema(this.haSchemaProperties());
    const defaults = this.unflattenDefaults(this.haDefaults(), this.haSchemaProperties());
    this.clusterService.updateCluster(this.blueprint()!.id, {
      haConfigSchema: schema ?? undefined,
      haConfigDefaults: Object.keys(defaults).length ? defaults : undefined,
    }).subscribe({
      next: (updated) => {
        this.blueprint.set(updated);
        this.configSaving.set(false);
        this.configSaveError.set(false);
        this.configSaveMsg.set('HA configuration saved.');
      },
      error: () => {
        this.configSaving.set(false);
        this.configSaveError.set(true);
        this.configSaveMsg.set('Failed to save HA configuration.');
      },
    });
  }

  onSaveDrConfig(): void {
    if (!this.blueprint()) return;
    this.configSaving.set(true);
    this.configSaveMsg.set('');
    const schema = this.propertiesToSchema(this.drSchemaProperties());
    const defaults = this.unflattenDefaults(this.drDefaults(), this.drSchemaProperties());
    this.clusterService.updateCluster(this.blueprint()!.id, {
      drConfigSchema: schema ?? undefined,
      drConfigDefaults: Object.keys(defaults).length ? defaults : undefined,
    }).subscribe({
      next: (updated) => {
        this.blueprint.set(updated);
        this.configSaving.set(false);
        this.configSaveError.set(false);
        this.configSaveMsg.set('DR configuration saved.');
      },
      error: () => {
        this.configSaving.set(false);
        this.configSaveError.set(true);
        this.configSaveMsg.set('Failed to save DR configuration.');
      },
    });
  }

  addHaSchemaProperty(): void {
    this.haSchemaProperties.update(props => [...props, { name: '', type: 'string', description: '', required: false }]);
  }

  removeHaSchemaProperty(index: number): void {
    this.haSchemaProperties.update(props => props.filter((_, i) => i !== index));
  }

  addDrSchemaProperty(): void {
    this.drSchemaProperties.update(props => [...props, { name: '', type: 'string', description: '', required: false }]);
  }

  removeDrSchemaProperty(index: number): void {
    this.drSchemaProperties.update(props => props.filter((_, i) => i !== index));
  }

  onSaveComponentRes(componentId: string): void {
    if (!this.blueprint()) return;
    this.resSaving.set(true);
    this.resSaveMsg.set('');
    const form = this.compResFormData()[componentId];
    if (!form) return;
    const input: ComponentReservationTemplateInput = {
      reservationType: form.reservationType,
      resourcePercentage: form.resourcePercentage,
      rtoSeconds: form.rtoSeconds ?? undefined,
      rpoSeconds: form.rpoSeconds ?? undefined,
      targetEnvironmentLabel: form.targetEnvLabel || undefined,
      targetProviderId: form.targetProviderId || undefined,
      autoCreateOnDeploy: form.autoCreate,
    };
    this.clusterService.setComponentReservationTemplate(componentId, input).subscribe({
      next: (tmpl) => {
        this.compResTemplates.update(map => ({ ...map, [componentId]: tmpl }));
        this.resSaving.set(false);
        this.resSaveError.set(false);
        this.resSaveMsg.set('Reservation template saved.');
      },
      error: () => {
        this.resSaving.set(false);
        this.resSaveError.set(true);
        this.resSaveMsg.set('Failed to save reservation template.');
      },
    });
  }

  onRemoveComponentRes(componentId: string): void {
    if (!confirm('Remove this component\'s reservation template?')) return;
    this.resSaving.set(true);
    this.resSaveMsg.set('');
    this.clusterService.removeComponentReservationTemplate(componentId).subscribe({
      next: () => {
        this.compResTemplates.update(map => {
          const next = { ...map };
          delete next[componentId];
          return next;
        });
        this.compResFormData.update(data => ({
          ...data,
          [componentId]: {
            reservationType: 'WARM_STANDBY',
            resourcePercentage: 80,
            rtoSeconds: null,
            rpoSeconds: null,
            targetEnvLabel: '',
            targetProviderId: '',
            autoCreate: true,
          },
        }));
        this.resSaving.set(false);
        this.resSaveError.set(false);
        this.resSaveMsg.set('Reservation template removed.');
      },
      error: () => {
        this.resSaving.set(false);
        this.resSaveError.set(true);
        this.resSaveMsg.set('Failed to remove reservation template.');
      },
    });
  }

  // ── Slot management ────────────────────────────────────────────────

  onAddSlot(): void {
    if (!this.blueprint() || !this.slotForm.name.trim()) return;
    this.slotSaving.set(true);
    const input: ServiceClusterSlotCreateInput = {
      name: this.slotForm.name.trim(),
      displayName: this.slotForm.displayName?.trim() || undefined,
      description: this.slotForm.description?.trim() || undefined,
      minCount: this.slotForm.minCount ?? 1,
      maxCount: this.slotForm.maxCount ?? undefined,
      isRequired: this.slotForm.isRequired,
      sortOrder: this.slotForm.sortOrder ?? 0,
    };
    this.clusterService.addSlot(this.blueprint()!.id, input).subscribe({
      next: (updated) => {
        this.blueprint.set(updated);
        this.slotSaving.set(false);
        this.showSlotForm.set(false);
        this.slotForm = { name: '', displayName: '', description: '', minCount: 1, maxCount: undefined, isRequired: true, sortOrder: 0 };
      },
      error: () => this.slotSaving.set(false),
    });
  }

  onRemoveSlot(slotId: string): void {
    if (!this.blueprint() || !confirm('Remove this slot?')) return;
    this.clusterService.removeSlot(this.blueprint()!.id, slotId).subscribe({
      next: (updated) => this.blueprint.set(updated),
    });
  }

  // ── Component expansion & variable bindings ───────────────────────

  private initEditableBindings(bindings: StackVariableBinding[]): void {
    const bp = this.blueprint();
    this.editableBindings.set(bindings.map((b, i) => {
      const comp = bp?.blueprintComponents.find(c => c.nodeId === b.targetNodeId);
      const knownParams = comp?.defaultParameters ? Object.keys(comp.defaultParameters) : [];
      return {
        _idx: i,
        direction: b.direction,
        variableName: b.variableName,
        targetNodeId: b.targetNodeId,
        targetParameter: b.targetParameter,
        expressionMode: knownParams.length === 0 || !knownParams.includes(b.targetParameter),
      };
    }));
  }

  toggleComponentExpansion(nodeId: string): void {
    this.expandedComponents.update(set => {
      const next = new Set(set);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }

  getComponentBindings(nodeId: string, direction: 'INPUT' | 'OUTPUT'): EditableBinding[] {
    return this.editableBindings().filter(b => b.targetNodeId === nodeId && b.direction === direction);
  }

  getComponentParameterNames(comp: { defaultParameters: Record<string, unknown> | null }): string[] {
    if (!comp.defaultParameters) return [];
    return Object.keys(comp.defaultParameters);
  }

  addBinding(nodeId: string, direction: 'INPUT' | 'OUTPUT'): void {
    this.editableBindings.update(bindings => {
      const maxIdx = bindings.reduce((max, b) => Math.max(max, b._idx), -1);
      return [...bindings, {
        _idx: maxIdx + 1,
        direction,
        variableName: '',
        targetNodeId: nodeId,
        targetParameter: '',
        expressionMode: false,
      }];
    });
  }

  removeBinding(idx: number): void {
    this.editableBindings.update(bindings => bindings.filter(b => b._idx !== idx));
  }

  toggleExpressionMode(binding: EditableBinding): void {
    binding.expressionMode = !binding.expressionMode;
    binding.targetParameter = '';
  }

  onSaveBindings(): void {
    if (!this.blueprint()) return;
    this.bindingsSaving.set(true);
    this.bindingsSaveMsg.set('');
    const inputs: VariableBindingInput[] = this.editableBindings()
      .filter(b => b.variableName && b.targetParameter)
      .map(b => ({
        direction: b.direction,
        variableName: b.variableName,
        targetNodeId: b.targetNodeId,
        targetParameter: b.targetParameter,
      }));
    this.clusterService.setVariableBindings(this.blueprint()!.id, inputs).subscribe({
      next: (saved) => {
        this.initEditableBindings(saved);
        this.bindingsSaving.set(false);
        this.bindingsSaveError.set(false);
        this.bindingsSaveMsg.set('Bindings saved.');
      },
      error: () => {
        this.bindingsSaving.set(false);
        this.bindingsSaveError.set(true);
        this.bindingsSaveMsg.set('Failed to save bindings.');
      },
    });
  }

  // ── Schema builder helpers ──────────────────────────────────────────

  private schemaToProperties(schema: Record<string, unknown> | null): SchemaProperty[] {
    if (!schema) return [];
    const props = (schema['properties'] || {}) as Record<string, Record<string, unknown>>;
    const required = (schema['required'] || []) as string[];
    return Object.entries(props).map(([name, def]) => ({
      name,
      type: (def['type'] as SchemaProperty['type']) || 'string',
      description: (def['description'] as string) || '',
      required: required.includes(name),
    }));
  }

  private propertiesToSchema(properties: SchemaProperty[]): Record<string, unknown> | null {
    if (properties.length === 0) return null;
    const props: Record<string, Record<string, unknown>> = {};
    const required: string[] = [];
    for (const p of properties) {
      const def: Record<string, unknown> = { type: p.type };
      if (p.description) def['description'] = p.description;
      props[p.name || `field_${Object.keys(props).length}`] = def;
      if (p.required) required.push(p.name || `field_${required.length}`);
    }
    const schema: Record<string, unknown> = { type: 'object', properties: props };
    if (required.length > 0) schema['required'] = required;
    return schema;
  }

  addInputProperty(): void {
    this.inputProperties.update(props => [...props, { name: '', type: 'string', description: '', required: false }]);
  }

  removeInputProperty(index: number): void {
    this.inputProperties.update(props => props.filter((_, i) => i !== index));
  }

  addOutputProperty(): void {
    this.outputProperties.update(props => [...props, { name: '', type: 'string', description: '', required: false }]);
  }

  removeOutputProperty(index: number): void {
    this.outputProperties.update(props => props.filter((_, i) => i !== index));
  }

  onInputSchemaChange(): void {
    // Triggered on each field change — no-op, schema built on save
  }

  onOutputSchemaChange(): void {
    // Triggered on each field change — no-op, schema built on save
  }

  onSaveSchemas(): void {
    if (!this.blueprint()) return;
    this.schemaSaving.set(true);
    this.schemaSaveMsg.set('');
    const inputSchema = this.propertiesToSchema(this.inputProperties());
    const outputSchema = this.propertiesToSchema(this.outputProperties());
    this.clusterService.updateCluster(this.blueprint()!.id, {
      inputSchema: inputSchema ?? undefined,
      outputSchema: outputSchema ?? undefined,
    }).subscribe({
      next: (updated) => {
        this.blueprint.set(updated);
        this.schemaSaving.set(false);
        this.schemaSaveError.set(false);
        this.schemaSaveMsg.set('Schemas saved.');
      },
      error: () => {
        this.schemaSaving.set(false);
        this.schemaSaveError.set(true);
        this.schemaSaveMsg.set('Failed to save schemas.');
      },
    });
  }
}
