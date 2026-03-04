/**
 * Overview: Properties panel — right sidebar with dynamic form from JSON Schema for selected node.
 * Architecture: Right sidebar panel for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic forms, JSON Schema, node configuration, property editing, x-ui-widget dispatch,
 *   variable context panel showing available expressions from upstream nodes,
 *   definition/inputs/outputs tabs with field-list schema builders
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

interface SchemaProperty {
  name: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
}

type DefTab = 'definition' | 'inputs' | 'outputs';

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
        @if (isActivityNode()) {
          <div class="activity-link-bar">
            <button class="btn-edit-activity" (click)="onEditActivity()">
              &#9998; Edit Activity Definition
            </button>
          </div>
        }
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
        <!-- Workflow Definition Tabs -->
        <div class="def-tabs">
          <button class="def-tab" [class.active]="activeDefTab() === 'definition'" (click)="activeDefTab.set('definition')">Definition</button>
          <button class="def-tab" [class.active]="activeDefTab() === 'inputs'" (click)="activeDefTab.set('inputs')">Inputs ({{ inputProperties().length }})</button>
          <button class="def-tab" [class.active]="activeDefTab() === 'outputs'" (click)="activeDefTab.set('outputs')">Outputs ({{ outputProperties().length }})</button>
        </div>

        <div class="panel-body">
          <!-- Definition Tab -->
          @if (activeDefTab() === 'definition') {
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
            @if (workflowVersion() !== null) {
              <div class="form-field">
                <label>Version</label>
                <input type="text" class="field-input read-only" [value]="'v' + workflowVersion()" readonly />
              </div>
            }
          }

          <!-- Inputs Tab -->
          @if (activeDefTab() === 'inputs') {
            <div class="schema-builder">
              <div class="schema-header">
                <span class="schema-label">Input Parameters</span>
                <button class="btn-add" (click)="addInputProperty()">+ Add</button>
              </div>
              @if (inputProperties().length === 0) {
                <div class="empty-schema">No input parameters defined.</div>
              }
              @for (prop of inputProperties(); track prop; let i = $index) {
                <div class="schema-row">
                  <div class="schema-row-top">
                    <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="param_name" (ngModelChange)="emitInputSchema()" />
                    <select class="schema-type" [(ngModel)]="prop.type" (ngModelChange)="emitInputSchema()">
                      <option value="string">String</option>
                      <option value="integer">Integer</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="object">Object</option>
                      <option value="array">Array</option>
                    </select>
                    <label class="schema-req" title="Required">
                      <input type="checkbox" [(ngModel)]="prop.required" (ngModelChange)="emitInputSchema()" />
                    </label>
                    <button class="btn-remove" (click)="removeInputProperty(i)" title="Remove">&times;</button>
                  </div>
                  <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" (ngModelChange)="emitInputSchema()" />
                </div>
              }
            </div>
          }

          <!-- Outputs Tab -->
          @if (activeDefTab() === 'outputs') {
            <div class="schema-builder">
              <div class="schema-header">
                <span class="schema-label">Output Values</span>
                <button class="btn-add" (click)="addOutputProperty()">+ Add</button>
              </div>
              @if (outputProperties().length === 0) {
                <div class="empty-schema">No output values defined.</div>
              }
              @for (prop of outputProperties(); track prop; let i = $index) {
                <div class="schema-row">
                  <div class="schema-row-top">
                    <input type="text" class="schema-name" [(ngModel)]="prop.name" placeholder="field_name" (ngModelChange)="emitOutputSchema()" />
                    <select class="schema-type" [(ngModel)]="prop.type" (ngModelChange)="emitOutputSchema()">
                      <option value="string">String</option>
                      <option value="integer">Integer</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="object">Object</option>
                      <option value="array">Array</option>
                    </select>
                    <label class="schema-req" title="Required">
                      <input type="checkbox" [(ngModel)]="prop.required" (ngModelChange)="emitOutputSchema()" />
                    </label>
                    <button class="btn-remove" (click)="removeOutputProperty(i)" title="Remove">&times;</button>
                  </div>
                  <input type="text" class="schema-desc" [(ngModel)]="prop.description" placeholder="Description" (ngModelChange)="emitOutputSchema()" />
                </div>
              }
            </div>
          }
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
    .field-input.read-only { background: #f8fafc; color: #64748b; cursor: default; }
    textarea.field-input { resize: vertical; }
    .expression-input { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
    .field-hint { display: block; font-size: 0.625rem; color: #94a3b8; margin-top: 2px; }
    .checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 0.8125rem; color: #374151; }
    select.field-input { appearance: auto; }
    .no-config { color: #94a3b8; font-size: 0.8125rem; text-align: center; padding: 1.5rem 0; }

    /* Definition Tabs */
    .def-tabs {
      display: flex; border-bottom: 1px solid #e2e8f0;
    }
    .def-tab {
      flex: 1; padding: 10px 4px; background: none; border: none;
      border-bottom: 2px solid transparent;
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      cursor: pointer; text-align: center; font-family: inherit;
      transition: color 0.15s, border-color 0.15s;
    }
    .def-tab:hover { color: #1e293b; }
    .def-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    /* Schema Builder */
    .schema-builder { display: flex; flex-direction: column; gap: 8px; }
    .schema-header {
      display: flex; justify-content: space-between; align-items: center;
    }
    .schema-label { font-size: 0.75rem; font-weight: 600; color: #475569; }
    .btn-add {
      padding: 3px 10px; background: #f0f9ff; border: 1px solid #bae6fd;
      color: #0284c7; border-radius: 4px; cursor: pointer;
      font-size: 0.6875rem; font-weight: 600; font-family: inherit;
    }
    .btn-add:hover { background: #e0f2fe; }
    .empty-schema {
      color: #94a3b8; font-size: 0.8125rem; text-align: center; padding: 1.5rem 0;
    }
    .schema-row {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 8px; display: flex; flex-direction: column; gap: 6px;
    }
    .schema-row-top {
      display: flex; gap: 4px; align-items: center;
    }
    .schema-name {
      flex: 1; padding: 4px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;
      color: #1e293b; background: #fff; outline: none;
    }
    .schema-name:focus { border-color: #3b82f6; }
    .schema-type {
      width: 72px; padding: 4px 2px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.6875rem; color: #1e293b; background: #fff; outline: none;
    }
    .schema-type:focus { border-color: #3b82f6; }
    .schema-req {
      display: flex; align-items: center; cursor: pointer;
    }
    .schema-req input[type="checkbox"] { margin: 0; cursor: pointer; }
    .btn-remove {
      background: none; border: none; cursor: pointer; color: #94a3b8;
      font-size: 1rem; line-height: 1; padding: 0 2px; font-family: inherit;
    }
    .btn-remove:hover { color: #dc2626; }
    .schema-desc {
      width: 100%; padding: 4px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.6875rem; color: #475569; background: #fff; outline: none;
    }
    .schema-desc:focus { border-color: #3b82f6; }

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

    /* Activity link bar */
    .activity-link-bar {
      padding: 8px 12px; border-bottom: 1px solid #e2e8f0;
      background: #f0fdf4;
    }
    .btn-edit-activity {
      width: 100%; padding: 6px 10px; background: #fff; border: 1px solid #16a34a;
      color: #16a34a; border-radius: 6px; cursor: pointer; font-size: 0.75rem;
      font-weight: 600; font-family: inherit; transition: all 0.15s;
    }
    .btn-edit-activity:hover { background: #16a34a; color: #fff; }
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

  @Input() set workflowProps(value: {
    name: string; description: string; timeoutSeconds: number;
    inputSchema: Record<string, unknown> | null;
    outputSchema: Record<string, unknown> | null;
    version?: number;
  } | null) {
    if (value) {
      this.workflowName.set(value.name);
      this.workflowDescription.set(value.description);
      this.timeoutSeconds.set(value.timeoutSeconds);
      this.workflowVersion.set(value.version ?? null);
      this.inputProperties.set(this.schemaToProperties(value.inputSchema));
      this.outputProperties.set(this.schemaToProperties(value.outputSchema));
    }
  }

  @Output() configChange = new EventEmitter<Record<string, unknown>>();
  @Output() editActivity = new EventEmitter<string>();
  @Output() workflowNameChange = new EventEmitter<string>();
  @Output() workflowDescriptionChange = new EventEmitter<string>();
  @Output() timeoutChange = new EventEmitter<number>();
  @Output() inputSchemaChange = new EventEmitter<Record<string, unknown> | null>();
  @Output() outputSchemaChange = new EventEmitter<Record<string, unknown> | null>();

  selectedNodeId = signal<string | null>(null);
  workflowName = signal('');
  workflowDescription = signal('');
  timeoutSeconds = signal(3600);
  workflowVersion = signal<number | null>(null);
  variablesExpanded = false;

  activeDefTab = signal<DefTab>('definition');
  inputProperties = signal<SchemaProperty[]>([]);
  outputProperties = signal<SchemaProperty[]>([]);

  private _selectedType = signal<string | null>(null);
  private _config = signal<Record<string, unknown>>({});

  selectedNodeType = computed(() => {
    const typeId = this._selectedType();
    return typeId ? this._nodeTypes().find(t => t.typeId === typeId) : null;
  });

  /** True when the selected node is an activity with an activity_id that can be edited */
  isActivityNode = computed(() => {
    const type = this._selectedType();
    if (!type) return false;
    if (type !== 'activity' && !type.startsWith('activity:')) return false;
    const config = this._config();
    return !!config['activity_id'];
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

    // $input.* — named fields if available, else wildcard
    const inputProps = this.inputProperties();
    if (inputProps.length > 0) {
      groups.push({
        label: 'Workflow Input',
        prefix: '$input',
        variables: inputProps.map(p => `$input.${p.name}`),
      });
    } else {
      groups.push({
        label: 'Workflow Input',
        prefix: '$input',
        variables: ['$input.*'],
      });
    }

    // $nodes.<id>.* — from upstream nodes
    const upstreamIds = this.getUpstreamNodeIds(nodeId, ctx);
    if (upstreamIds.length > 0) {
      const nodeVars: string[] = [];
      for (const uid of upstreamIds) {
        const node = ctx.nodes.find(n => n.id === uid);
        const nodeLabel = node?.label || node?.id || uid;
        const nodeType = node?.type || '';

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

  // ── Schema <-> Properties conversion ──────────────────────────────

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

  // ── Schema field operations ───────────────────────────────────────

  addInputProperty(): void {
    this.inputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false },
    ]);
  }

  removeInputProperty(index: number): void {
    this.inputProperties.update(props => props.filter((_, i) => i !== index));
    this.emitInputSchema();
  }

  addOutputProperty(): void {
    this.outputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false },
    ]);
  }

  removeOutputProperty(index: number): void {
    this.outputProperties.update(props => props.filter((_, i) => i !== index));
    this.emitOutputSchema();
  }

  emitInputSchema(): void {
    this.inputSchemaChange.emit(this.propertiesToSchema(this.inputProperties()));
  }

  emitOutputSchema(): void {
    this.outputSchemaChange.emit(this.propertiesToSchema(this.outputProperties()));
  }

  // ── Config helpers ────────────────────────────────────────────────

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

  onEditActivity(): void {
    const config = this._config();
    const activityId = config['activity_id'] as string;
    if (activityId) {
      this.editActivity.emit(activityId);
    }
  }

  copyVariable(variable: string): void {
    navigator.clipboard.writeText('${' + variable + '}').catch(() => {
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
