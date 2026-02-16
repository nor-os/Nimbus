/**
 * Overview: Properties panel — right sidebar with dynamic form from JSON Schema for selected node.
 * Architecture: Right sidebar panel for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic forms, JSON Schema, node configuration, property editing, x-ui-widget dispatch,
 *   variable context panel showing available expressions from upstream nodes
 */
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NodeTypeInfo, WorkflowNode, WorkflowConnection } from '@shared/models/workflow.model';
import { ExpressionEditorComponent } from './expression-editor.component';
import { StringListEditorComponent } from './editors/string-list-editor.component';
import { KeyValueListEditorComponent } from './editors/key-value-list-editor.component';
import { KeyValueMapEditorComponent } from './editors/key-value-map-editor.component';
import { SwitchCasesEditorComponent } from './editors/switch-cases-editor.component';
import { WorkflowPickerComponent } from './editors/workflow-picker.component';

interface GraphContext {
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
}

interface VariableGroup {
  label: string;
  prefix: string;
  variables: string[];
}

@Component({
  selector: 'nimbus-properties-panel',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ExpressionEditorComponent,
    StringListEditorComponent,
    KeyValueListEditorComponent,
    KeyValueMapEditorComponent,
    SwitchCasesEditorComponent,
    WorkflowPickerComponent,
  ],
  template: `
    <div class="properties-panel">
      @if (selectedNodeId()) {
        <div class="panel-header">
          <span class="node-icon" [innerHTML]="selectedNodeType()?.icon"></span>
          <h3>{{ selectedNodeType()?.label || 'Node' }}</h3>
        </div>
        <div class="panel-body">
          @if (selectedNodeType()?.configSchema?.['properties']) {
            @for (field of configFields(); track field.key) {
              <div class="form-field">
                <label>{{ field.label }}</label>

                <!-- Widget-based dispatch -->
                @if (field.widget === 'expression') {
                  <nimbus-expression-editor
                    [value]="getConfigValue(field.key)"
                    (valueChange)="setConfigValue(field.key, $event)"
                    [placeholder]="field.description || 'Enter expression...'"
                  ></nimbus-expression-editor>
                } @else if (field.widget === 'json-body') {
                  <nimbus-expression-editor
                    [value]="getConfigValue(field.key)"
                    (valueChange)="setConfigValue(field.key, $event)"
                    [placeholder]="field.description || 'Enter JSON body...'"
                    language="json"
                    height="160px"
                  ></nimbus-expression-editor>
                } @else if (field.widget === 'command') {
                  <nimbus-expression-editor
                    [value]="getConfigValue(field.key)"
                    (valueChange)="setConfigValue(field.key, $event)"
                    [placeholder]="field.description || 'Enter command...'"
                    language="shell"
                    height="120px"
                  ></nimbus-expression-editor>
                } @else if (field.widget === 'string-list') {
                  <nimbus-string-list-editor
                    [value]="getConfigValue(field.key) || []"
                    (valueChange)="setConfigValue(field.key, $event)"
                    [placeholder]="field.description || ''"
                  ></nimbus-string-list-editor>
                } @else if (field.widget === 'key-value-list') {
                  <nimbus-key-value-list-editor
                    [value]="getConfigValue(field.key) || []"
                    (valueChange)="setConfigValue(field.key, $event)"
                    [keyLabel]="field.uiKeyLabel || 'Key'"
                    [valueLabel]="field.uiValueLabel || 'Value'"
                  ></nimbus-key-value-list-editor>
                } @else if (field.widget === 'key-value-map') {
                  <nimbus-key-value-map-editor
                    [value]="getConfigValue(field.key) || {}"
                    (valueChange)="setConfigValue(field.key, $event)"
                  ></nimbus-key-value-map-editor>
                } @else if (field.widget === 'switch-cases') {
                  <nimbus-switch-cases-editor
                    [value]="getConfigValue(field.key) || []"
                    (valueChange)="setConfigValue(field.key, $event)"
                  ></nimbus-switch-cases-editor>
                } @else if (field.widget === 'workflow-picker') {
                  <nimbus-workflow-picker
                    [value]="getConfigValue(field.key) || ''"
                    (valueChange)="setConfigValue(field.key, $event)"
                  ></nimbus-workflow-picker>
                } @else if (field.type === 'string') {
                  @if (field.enum) {
                    <select
                      class="field-input"
                      [ngModel]="getConfigValue(field.key)"
                      (ngModelChange)="setConfigValue(field.key, $event)"
                    >
                      @for (opt of field.enum; track opt) {
                        <option [value]="opt">{{ opt }}</option>
                      }
                    </select>
                  } @else {
                    <input
                      type="text"
                      class="field-input"
                      [ngModel]="getConfigValue(field.key)"
                      (ngModelChange)="setConfigValue(field.key, $event)"
                      [placeholder]="field.description || ''"
                    />
                  }
                } @else if (field.type === 'number' || field.type === 'integer') {
                  <input
                    type="number"
                    class="field-input"
                    [ngModel]="getConfigValue(field.key)"
                    (ngModelChange)="setConfigValue(field.key, +$event)"
                  />
                } @else if (field.type === 'boolean') {
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      [ngModel]="getConfigValue(field.key)"
                      (ngModelChange)="setConfigValue(field.key, $event)"
                    />
                    {{ field.label }}
                  </label>
                } @else {
                  <textarea
                    class="field-input"
                    [ngModel]="getConfigValueJson(field.key)"
                    (ngModelChange)="setConfigValueJson(field.key, $event)"
                    rows="3"
                  ></textarea>
                }

                @if (field.description && !field.widget) {
                  <span class="field-hint">{{ field.description }}</span>
                }
              </div>
            }
          } @else {
            <p class="no-config">No configurable properties</p>
          }

          <!-- Variable Context Panel -->
          @if (variableGroups().length > 0) {
            <div class="variable-context">
              <button class="context-toggle" (click)="variablesExpanded = !variablesExpanded">
                <span class="toggle-icon">{{ variablesExpanded ? '&#9660;' : '&#9654;' }}</span>
                Available Variables
              </button>
              @if (variablesExpanded) {
                <div class="context-body">
                  @for (group of variableGroups(); track group.prefix) {
                    <div class="var-group">
                      <div class="var-group-label">{{ group.label }}</div>
                      @for (v of group.variables; track v) {
                        <code class="var-item" (click)="copyVariable(v)" title="Click to copy">{{ v }}</code>
                      }
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      } @else {
        <div class="panel-header">
          <h3>Workflow Properties</h3>
        </div>
        <div class="panel-body">
          <div class="form-field">
            <label>Name</label>
            <input type="text" class="field-input" [ngModel]="workflowName()" (ngModelChange)="workflowNameChange.emit($event)" />
          </div>
          <div class="form-field">
            <label>Description</label>
            <textarea class="field-input" rows="3" [ngModel]="workflowDescription()" (ngModelChange)="workflowDescriptionChange.emit($event)"></textarea>
          </div>
          <div class="form-field">
            <label>Timeout (seconds)</label>
            <input type="number" class="field-input" [ngModel]="timeoutSeconds()" (ngModelChange)="timeoutChange.emit(+$event)" />
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .properties-panel {
      width: 280px; height: 100%; background: #fff;
      border-left: 1px solid #e2e8f0; overflow-y: auto;
      display: flex; flex-direction: column;
    }
    .panel-header {
      display: flex; align-items: center; gap: 8px;
      padding: 12px; border-bottom: 1px solid #e2e8f0;
    }
    .panel-header h3 { margin: 0; font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .node-icon { font-size: 1rem; }
    .panel-body { padding: 12px; flex: 1; }
    .form-field { margin-bottom: 12px; }
    .form-field label { display: block; font-size: 0.75rem; color: #64748b; margin-bottom: 4px; }
    .field-input {
      width: 100%; padding: 6px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-size: 0.8125rem; outline: none;
      font-family: inherit;
    }
    .field-input:focus { border-color: #3b82f6; }
    textarea.field-input { resize: vertical; }
    .expression-input { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
    .field-hint { display: block; font-size: 0.625rem; color: #94a3b8; margin-top: 2px; }
    .checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 0.8125rem; color: #374151; }
    select.field-input { appearance: auto; }
    .no-config { color: #94a3b8; font-size: 0.8125rem; text-align: center; padding: 1.5rem 0; }

    /* Variable Context Panel */
    .variable-context {
      margin-top: 16px; border-top: 1px solid #e2e8f0; padding-top: 8px;
    }
    .context-toggle {
      display: flex; align-items: center; gap: 6px;
      background: none; border: none; cursor: pointer;
      font-size: 0.75rem; font-weight: 600; color: #475569;
      padding: 4px 0; width: 100%; text-align: left;
    }
    .context-toggle:hover { color: #1e293b; }
    .toggle-icon { font-size: 0.625rem; width: 12px; }
    .context-body { padding-top: 8px; }
    .var-group { margin-bottom: 8px; }
    .var-group-label {
      font-size: 0.625rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;
    }
    .var-item {
      display: block; padding: 2px 6px; margin: 2px 0;
      font-size: 0.6875rem; font-family: 'JetBrains Mono', monospace;
      color: #334155; background: #f1f5f9; border-radius: 3px;
      cursor: pointer; border: 1px solid transparent;
    }
    .var-item:hover { border-color: #3b82f6; background: #eff6ff; }
  `],
})
export class PropertiesPanelComponent {
  private _nodeTypes = signal<NodeTypeInfo[]>([]);
  private _graphContext = signal<GraphContext | null>(null);

  @Input() set nodeTypes(value: NodeTypeInfo[]) { this._nodeTypes.set(value); }
  @Input() set selectedNode(value: { id: string; type: string; config: Record<string, unknown> } | null) {
    this.selectedNodeId.set(value?.id ?? null);
    this._selectedType.set(value?.type ?? null);
    this._config.set(value?.config ? { ...value.config } : {});
  }
  @Input() set graphContext(value: GraphContext | null) { this._graphContext.set(value); }

  @Input() set workflowProps(value: { name: string; description: string; timeoutSeconds: number } | null) {
    if (value) {
      this.workflowName.set(value.name);
      this.workflowDescription.set(value.description);
      this.timeoutSeconds.set(value.timeoutSeconds);
    }
  }

  @Output() configChange = new EventEmitter<Record<string, unknown>>();
  @Output() workflowNameChange = new EventEmitter<string>();
  @Output() workflowDescriptionChange = new EventEmitter<string>();
  @Output() timeoutChange = new EventEmitter<number>();

  selectedNodeId = signal<string | null>(null);
  workflowName = signal('');
  workflowDescription = signal('');
  timeoutSeconds = signal(3600);
  variablesExpanded = false;

  private _selectedType = signal<string | null>(null);
  private _config = signal<Record<string, unknown>>({});

  selectedNodeType = computed(() => {
    const typeId = this._selectedType();
    return typeId ? this._nodeTypes().find(t => t.typeId === typeId) : null;
  });

  configFields = computed(() => {
    const schema = this.selectedNodeType()?.configSchema as any;
    if (!schema?.properties) return [];

    const required = new Set(schema.required || []);

    return Object.entries(schema.properties).map(([key, prop]: [string, any]) => ({
      key,
      label: key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ').replace(/^./, s => s.toUpperCase()),
      type: prop.type || 'string',
      description: prop.description || '',
      required: required.has(key),
      enum: prop.enum,
      widget: prop['x-ui-widget'] as string | undefined,
      uiKeyLabel: prop['x-ui-key-label'] as string | undefined,
      uiValueLabel: prop['x-ui-value-label'] as string | undefined,
      default: prop.default,
    }));
  });

  /** Compute variable groups from graph context for the selected node. */
  variableGroups = computed((): VariableGroup[] => {
    const ctx = this._graphContext();
    const nodeId = this.selectedNodeId();
    if (!ctx || !nodeId) return [];

    const groups: VariableGroup[] = [];

    // $input.* — always available
    groups.push({
      label: 'Workflow Input',
      prefix: '$input',
      variables: ['$input.*'],
    });

    // $nodes.<id>.* — from upstream nodes
    const upstreamIds = this.getUpstreamNodeIds(nodeId, ctx);
    if (upstreamIds.length > 0) {
      const nodeVars: string[] = [];
      for (const uid of upstreamIds) {
        const node = ctx.nodes.find(n => n.id === uid);
        const nodeLabel = node?.label || node?.id || uid;
        const nodeType = node?.type || '';

        // Provide known output fields for specific node types
        const outputFields = this.getOutputFieldsForType(nodeType);
        if (outputFields.length > 0) {
          for (const field of outputFields) {
            nodeVars.push(`$nodes.${nodeLabel}.${field}`);
          }
        } else {
          nodeVars.push(`$nodes.${nodeLabel}.*`);
        }
      }
      groups.push({
        label: 'Previous Nodes',
        prefix: '$nodes',
        variables: nodeVars,
      });
    }

    // $loop.* — always show for reference
    groups.push({
      label: 'Loop (if inside loop)',
      prefix: '$loop',
      variables: ['$loop.index', '$loop.item', '$loop.total'],
    });

    return groups;
  });

  getConfigValue(key: string): any {
    return this._config()[key] ?? '';
  }

  getConfigValueJson(key: string): string {
    const val = this._config()[key];
    return val != null ? JSON.stringify(val, null, 2) : '';
  }

  setConfigValue(key: string, value: any): void {
    const config = { ...this._config(), [key]: value };
    this._config.set(config);
    this.configChange.emit(config);
  }

  setConfigValueJson(key: string, json: string): void {
    try {
      const parsed = JSON.parse(json);
      this.setConfigValue(key, parsed);
    } catch {
      // Ignore invalid JSON while typing
    }
  }

  copyVariable(variable: string): void {
    navigator.clipboard.writeText('${' + variable + '}').catch(() => {
      // Fallback: just log
      console.log('Copy to clipboard:', variable);
    });
  }

  /** Walk connections backward to find all upstream nodes. */
  private getUpstreamNodeIds(nodeId: string, ctx: GraphContext): string[] {
    const visited = new Set<string>();
    const queue = [nodeId];

    while (queue.length > 0) {
      const current = queue.shift()!;
      for (const conn of ctx.connections) {
        if (conn.target === current && !visited.has(conn.source)) {
          visited.add(conn.source);
          queue.push(conn.source);
        }
      }
    }

    return Array.from(visited);
  }

  /** Return known output fields for a given node type. */
  private getOutputFieldsForType(typeId: string): string[] {
    switch (typeId) {
      case 'cloud_api':
        return ['status_code', 'body', 'headers'];
      case 'ssh_exec':
        return ['stdout', 'stderr', 'exit_code'];
      case 'approval':
        return ['approved', 'approver', 'comment'];
      case 'http_request':
        return ['status_code', 'body', 'headers'];
      default:
        return [];
    }
  }
}
