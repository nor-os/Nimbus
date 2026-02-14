/**
 * Overview: Dynamic node properties form — generates fields from semantic type properties_schema.
 * Architecture: Properties form for selected node in architecture editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, property-field.component
 * Concepts: Dynamic form generation from JSON Schema, property binding, validation display
 */
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PropertyFieldComponent, PropertyFieldDef } from './property-field.component';

@Component({
  selector: 'nimbus-node-properties-form',
  standalone: true,
  imports: [CommonModule, FormsModule, PropertyFieldComponent],
  template: `
    <div class="node-properties-form">
      <div class="form-section">
        <label class="section-label">Label</label>
        <input
          type="text"
          class="field-input"
          [ngModel]="label"
          (ngModelChange)="labelChange.emit($event)"
          [disabled]="readOnly"
          placeholder="Node label..."
        />
      </div>

      @if (fields().length > 0) {
        <div class="form-section">
          <div class="section-label">Properties</div>
          @for (field of fields(); track field.name) {
            <nimbus-property-field
              [field]="field"
              [value]="getPropertyValue(field.name)"
              [readOnly]="readOnly"
              (valueChange)="onPropertyChange(field.name, $event)"
            />
          }
        </div>
      } @else {
        <div class="no-properties">No configurable properties</div>
      }
    </div>
  `,
  styles: [`
    .node-properties-form { padding: 0; }
    .form-section { margin-bottom: 16px; }
    .section-label {
      font-size: 0.6875rem;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 6px;
    }
    .field-input {
      width: 100%;
      padding: 6px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      outline: none;
      font-family: inherit;
      box-sizing: border-box;
    }
    .field-input:focus { border-color: #3b82f6; }
    .field-input:disabled { background: #f8fafc; color: #94a3b8; }
    .no-properties {
      padding: 16px 0;
      font-size: 0.75rem;
      color: #94a3b8;
      text-align: center;
    }
  `],
})
export class NodePropertiesFormComponent {
  private _schema = signal<Record<string, unknown> | null>(null);

  @Input() set propertiesSchema(value: Record<string, unknown> | null) {
    this._schema.set(value);
  }
  @Input() properties: Record<string, unknown> = {};
  @Input() label = '';
  @Input() readOnly = false;

  @Output() labelChange = new EventEmitter<string>();
  @Output() propertyChange = new EventEmitter<{ name: string; value: unknown }>();

  fields = computed<PropertyFieldDef[]>(() => {
    const schema = this._schema();
    if (!schema) return [];

    // Handle PropertyDef[] array format (from semantic types)
    if (Array.isArray(schema)) {
      return (schema as Array<Record<string, unknown>>).map(def => {
        const unit = def['unit'] as string | null;
        const displayName = (def['display_name'] as string) || (def['name'] as string) || '';
        return {
          name: (def['name'] as string) || '',
          type: (def['data_type'] as string) || 'string',
          label: unit ? `${displayName} (${unit})` : displayName,
          description: (def['description'] as string) || undefined,
          required: (def['required'] as boolean) || false,
          enum: (def['allowed_values'] as string[]) || undefined,
          default: def['default_value'],
        };
      });
    }

    // Handle JSON Schema { properties: {...}, required: [...] } format
    if (!schema['properties']) return [];

    const props = schema['properties'] as Record<string, Record<string, unknown>>;
    const required = (schema['required'] as string[]) || [];

    return Object.entries(props).map(([name, def]) => ({
      name,
      type: (def['type'] as string) || 'string',
      label: (def['title'] as string) || name,
      description: (def['description'] as string) || undefined,
      required: required.includes(name),
      enum: (def['enum'] as string[]) || undefined,
      default: def['default'],
    }));
  });

  getPropertyValue(name: string): unknown {
    return this.properties[name] ?? null;
  }

  onPropertyChange(name: string, value: unknown): void {
    this.propertyChange.emit({ name, value });
  }
}
