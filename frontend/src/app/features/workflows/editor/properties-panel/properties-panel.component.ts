/**
 * Overview: Properties panel — right sidebar with dynamic form from JSON Schema for selected node.
 * Architecture: Right sidebar panel for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic forms, JSON Schema, node configuration, property editing, x-ui-widget dispatch
 */
import { Component, EventEmitter, Input, Output, computed, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NodeTypeInfo } from '@shared/models/workflow.model';
import { ExpressionEditorComponent } from './expression-editor.component';
import { StringListEditorComponent } from './editors/string-list-editor.component';
import { KeyValueListEditorComponent } from './editors/key-value-list-editor.component';
import { KeyValueMapEditorComponent } from './editors/key-value-map-editor.component';
import { SwitchCasesEditorComponent } from './editors/switch-cases-editor.component';
import { WorkflowPickerComponent } from './editors/workflow-picker.component';

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
  `],
})
export class PropertiesPanelComponent {
  private _nodeTypes = signal<NodeTypeInfo[]>([]);
  @Input() set nodeTypes(value: NodeTypeInfo[]) { this._nodeTypes.set(value); }
  @Input() set selectedNode(value: { id: string; type: string; config: Record<string, unknown> } | null) {
    this.selectedNodeId.set(value?.id ?? null);
    this._selectedType.set(value?.type ?? null);
    this._config.set(value?.config ? { ...value.config } : {});
  }

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
}
