/**
 * Overview: Parameter binding editor — configure parameterOverrides for a stack instance.
 * Architecture: Properties sub-panel for stack parameter bindings (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Parameter override types (explicit, tag_ref), binding to blueprint parameters
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ParameterOverride, TopologyStackInstance } from '@shared/models/architecture.model';
import { StackBlueprintParameter } from '@shared/models/cluster.model';

interface BindingRow {
  paramName: string;
  displayName: string;
  isRequired: boolean;
  override: ParameterOverride | null;
  defaultValue: unknown;
}

@Component({
  selector: 'nimbus-parameter-binding-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="binding-editor">
      <div class="section-title">Parameter Bindings</div>
      @for (row of bindings; track row.paramName) {
        <div class="binding-row">
          <div class="param-name">
            {{ row.displayName }}
            @if (row.isRequired) { <span class="required-mark">*</span> }
          </div>
          <div class="binding-controls">
            <select
              class="binding-type"
              [ngModel]="getBindingType(row)"
              (ngModelChange)="onTypeChange(row.paramName, $event)"
              [disabled]="readOnly"
            >
              <option value="default">Default</option>
              <option value="explicit">Explicit</option>
              <option value="tag_ref">Tag Reference</option>
            </select>
            @if (getBindingType(row) === 'explicit') {
              <input
                type="text"
                class="binding-value"
                [ngModel]="getExplicitValue(row)"
                (ngModelChange)="onExplicitChange(row.paramName, $event)"
                [disabled]="readOnly"
                placeholder="Value..."
              />
            }
            @if (getBindingType(row) === 'tag_ref') {
              <input
                type="text"
                class="binding-value"
                [ngModel]="getTagKey(row)"
                (ngModelChange)="onTagKeyChange(row.paramName, $event)"
                [disabled]="readOnly"
                placeholder="Tag key..."
              />
            }
            @if (getBindingType(row) === 'default') {
              <span class="default-value">{{ formatDefault(row.defaultValue) }}</span>
            }
          </div>
        </div>
      }
      @if (bindings.length === 0) {
        <div class="empty-hint">No parameters defined for this blueprint</div>
      }
    </div>
  `,
  styles: [`
    .binding-editor { display: flex; flex-direction: column; gap: 8px; }
    .section-title {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
      margin-bottom: 2px;
    }
    .binding-row {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 6px 8px;
      background: #f8fafc;
      border-radius: 6px;
      border: 1px solid #f1f5f9;
    }
    .param-name {
      font-size: 0.75rem;
      font-weight: 600;
      color: #374151;
    }
    .required-mark { color: #dc2626; }
    .binding-controls {
      display: flex;
      gap: 4px;
      align-items: center;
    }
    .binding-type {
      padding: 3px 6px;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 0.6875rem;
      color: #374151;
      background: #fff;
      font-family: inherit;
      outline: none;
      min-width: 80px;
    }
    .binding-type:focus { border-color: #3b82f6; }
    .binding-type:disabled { background: #f8fafc; }
    .binding-value {
      flex: 1;
      padding: 3px 6px;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 0.75rem;
      color: #1e293b;
      background: #fff;
      font-family: inherit;
      outline: none;
    }
    .binding-value:focus { border-color: #3b82f6; }
    .binding-value:disabled { background: #f8fafc; }
    .default-value {
      flex: 1;
      font-size: 0.75rem;
      color: #94a3b8;
      font-style: italic;
    }
    .empty-hint {
      font-size: 0.75rem;
      color: #94a3b8;
      padding: 6px 0;
    }
  `],
})
export class ParameterBindingEditorComponent {
  @Input() stack!: TopologyStackInstance;
  @Input() blueprintParameters: StackBlueprintParameter[] = [];
  @Input() readOnly = false;

  @Output() overridesChange = new EventEmitter<Record<string, ParameterOverride>>();

  get bindings(): BindingRow[] {
    return this.blueprintParameters.map(p => ({
      paramName: p.name,
      displayName: p.displayName || p.name,
      isRequired: p.isRequired,
      override: this.stack.parameterOverrides?.[p.name] || null,
      defaultValue: p.defaultValue,
    }));
  }

  getBindingType(row: BindingRow): string {
    if (!row.override) return 'default';
    return row.override.type;
  }

  getExplicitValue(row: BindingRow): string {
    return row.override?.type === 'explicit' ? String(row.override.value ?? '') : '';
  }

  getTagKey(row: BindingRow): string {
    return row.override?.type === 'tag_ref' ? (row.override.tagKey ?? '') : '';
  }

  formatDefault(value: unknown): string {
    if (value === null || value === undefined) return '(none)';
    return String(value);
  }

  onTypeChange(paramName: string, type: string): void {
    const overrides = { ...(this.stack.parameterOverrides || {}) };
    if (type === 'default') {
      delete overrides[paramName];
    } else if (type === 'explicit') {
      overrides[paramName] = { type: 'explicit', value: '' };
    } else if (type === 'tag_ref') {
      overrides[paramName] = { type: 'tag_ref', tagKey: '' };
    }
    this.overridesChange.emit(overrides);
  }

  onExplicitChange(paramName: string, value: string): void {
    const overrides = { ...(this.stack.parameterOverrides || {}) };
    overrides[paramName] = { type: 'explicit', value };
    this.overridesChange.emit(overrides);
  }

  onTagKeyChange(paramName: string, tagKey: string): void {
    const overrides = { ...(this.stack.parameterOverrides || {}) };
    overrides[paramName] = { type: 'tag_ref', tagKey };
    this.overridesChange.emit(overrides);
  }
}
