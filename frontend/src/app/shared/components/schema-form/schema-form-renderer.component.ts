/**
 * Overview: Orchestrator component that renders a full JSON Schema form by routing field types to specialized child components.
 * Architecture: Shared reusable form component (Section 3)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: JSON Schema rendering, dynamic form generation, type-based component routing, schema-driven UI
 */
import { Component, ChangeDetectionStrategy, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ArrayEditorComponent } from './array-editor.component';
import { ObjectEditorComponent } from './object-editor.component';
import { CidrInputComponent } from './cidr-input.component';
import { RuleTableEditorComponent, ColumnDef } from './rule-table-editor.component';

interface FieldDef {
  key: string;
  title: string;
  description?: string;
  type: string;
  format?: string;
  enumValues?: string[];
  items?: Record<string, unknown>;
  properties?: Record<string, unknown>;
  schema: Record<string, unknown>;
}

@Component({
  selector: 'nimbus-schema-form-renderer',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ArrayEditorComponent,
    ObjectEditorComponent,
    CidrInputComponent,
    RuleTableEditorComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="schema-form">
      @for (field of getFields(); track field.key) {
        <div class="form-field">
          @if (getFieldType(field) !== 'object') {
            <label class="form-label">{{ field.title }}</label>
          }

          @switch (getFieldType(field)) {
            @case ('boolean') {
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  [checked]="getVal(field.key) === true"
                  (change)="onFieldChange(field.key, $any($event.target).checked)"
                />
                <span class="toggle-slider"></span>
                <span class="toggle-text">{{ getVal(field.key) === true ? 'Enabled' : 'Disabled' }}</span>
              </label>
            }
            @case ('cidr') {
              <nimbus-cidr-input
                [value]="asString(getVal(field.key))"
                (valueChange)="onFieldChange(field.key, $event)"
              ></nimbus-cidr-input>
            }
            @case ('string-array') {
              <nimbus-array-editor
                [items]="asStringArray(getVal(field.key))"
                (itemsChange)="onFieldChange(field.key, $event)"
              ></nimbus-array-editor>
            }
            @case ('object-array') {
              <nimbus-rule-table-editor
                [columns]="deriveColumns(field)"
                [rows]="asObjectArray(getVal(field.key))"
                (rowsChange)="onFieldChange(field.key, $event)"
              ></nimbus-rule-table-editor>
            }
            @case ('object') {
              <nimbus-object-editor
                [schema]="field.schema"
                [value]="asObject(getVal(field.key))"
                (valueChange)="onFieldChange(field.key, $event)"
              ></nimbus-object-editor>
            }
            @case ('enum') {
              <select
                class="form-select"
                [ngModel]="getVal(field.key) ?? ''"
                (ngModelChange)="onFieldChange(field.key, $event)"
              >
                <option value="" disabled>Select...</option>
                @for (opt of field.enumValues || []; track opt) {
                  <option [value]="opt">{{ opt }}</option>
                }
              </select>
            }
            @case ('integer') {
              <input
                type="number"
                class="form-input"
                step="1"
                [ngModel]="getVal(field.key) ?? ''"
                (ngModelChange)="onFieldChange(field.key, toNumber($event))"
              />
            }
            @case ('number') {
              <input
                type="number"
                class="form-input"
                [ngModel]="getVal(field.key) ?? ''"
                (ngModelChange)="onFieldChange(field.key, toFloat($event))"
              />
            }
            @default {
              <input
                type="text"
                class="form-input"
                [ngModel]="getVal(field.key) ?? ''"
                (ngModelChange)="onFieldChange(field.key, $event)"
              />
            }
          }

          @if (field.description) {
            <span class="form-hint">{{ field.description }}</span>
          }
        </div>
      }
      @if (getFields().length === 0) {
        <div class="empty-state">No schema properties defined.</div>
      }
    </div>
  `,
  styles: [`
    .schema-form {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .form-label {
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
    }

    .form-hint {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
    }

    .form-input, .form-select {
      padding: 7px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 13px;
      background: #fff;
      color: #1e293b;
      outline: none;
      transition: border-color 0.15s;
    }

    .form-input:focus, .form-select:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    .toggle-switch {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      user-select: none;
    }

    .toggle-switch input[type="checkbox"] {
      position: relative;
      width: 36px;
      height: 20px;
      appearance: none;
      -webkit-appearance: none;
      background: #cbd5e1;
      border-radius: 10px;
      outline: none;
      cursor: pointer;
      transition: background 0.2s;
    }

    .toggle-switch input[type="checkbox"]::after {
      content: '';
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;
      height: 16px;
      background: #fff;
      border-radius: 50%;
      transition: transform 0.2s;
      box-shadow: 0 1px 2px rgba(0,0,0,0.15);
    }

    .toggle-switch input[type="checkbox"]:checked {
      background: #3b82f6;
    }

    .toggle-switch input[type="checkbox"]:checked::after {
      transform: translateX(16px);
    }

    .toggle-slider {
      display: none;
    }

    .toggle-text {
      font-size: 13px;
      color: #475569;
    }

    .empty-state {
      color: #94a3b8;
      font-size: 13px;
      font-style: italic;
      padding: 12px 0;
    }
  `]
})
export class SchemaFormRendererComponent {
  @Input() schema: Record<string, unknown> = {};
  @Input() values: Record<string, unknown> = {};
  @Output() valuesChange = new EventEmitter<Record<string, unknown>>();

  getFields(): FieldDef[] {
    const props = (this.schema?.['properties'] as Record<string, Record<string, unknown>>) || {};
    return Object.entries(props).map(([key, def]) => ({
      key,
      title: (def['title'] as string) || key,
      description: def['description'] as string | undefined,
      type: (def['type'] as string) || 'string',
      format: def['format'] as string | undefined,
      enumValues: def['enum'] as string[] | undefined,
      items: def['items'] as Record<string, unknown> | undefined,
      properties: def['properties'] as Record<string, unknown> | undefined,
      schema: def,
    }));
  }

  getFieldType(field: FieldDef): string {
    if (field.type === 'boolean') return 'boolean';
    if (field.type === 'string' && field.format === 'cidr') return 'cidr';
    if (field.type === 'string' && field.enumValues?.length) return 'enum';
    if (field.type === 'array') {
      const itemsType = (field.items?.['type'] as string) || 'string';
      if (itemsType === 'object') return 'object-array';
      return 'string-array';
    }
    if (field.type === 'object') return 'object';
    if (field.type === 'integer') return 'integer';
    if (field.type === 'number') return 'number';
    return 'string';
  }

  getVal(key: string): unknown {
    return this.values?.[key];
  }

  onFieldChange(key: string, val: unknown): void {
    const updated = { ...this.values, [key]: val };
    this.values = updated;
    this.valuesChange.emit(updated);
  }

  deriveColumns(field: FieldDef): ColumnDef[] {
    const itemProps = (field.items?.['properties'] as Record<string, Record<string, unknown>>) || {};
    return Object.entries(itemProps).map(([key, def]) => {
      const col: ColumnDef = {
        key,
        title: (def['title'] as string) || key,
        type: (def['type'] as string) || 'text',
      };
      if (def['enum']) {
        col.type = 'select';
        col.options = def['enum'] as string[];
      } else if ((def['type'] as string) === 'array') {
        const items = def['items'] as Record<string, unknown> | undefined;
        if (items && (items['type'] as string) === 'string') {
          col.type = 'array';
        }
      }
      return col;
    });
  }

  asString(val: unknown): string {
    return (val as string) || '';
  }

  asStringArray(val: unknown): string[] {
    return Array.isArray(val) ? val as string[] : [];
  }

  asObjectArray(val: unknown): Record<string, unknown>[] {
    return Array.isArray(val) ? val as Record<string, unknown>[] : [];
  }

  asObject(val: unknown): Record<string, unknown> {
    return (val as Record<string, unknown>) || {};
  }

  toNumber(val: unknown): number | null {
    const n = parseInt(String(val), 10);
    return isNaN(n) ? null : n;
  }

  toFloat(val: unknown): number | null {
    const n = parseFloat(String(val));
    return isNaN(n) ? null : n;
  }
}
