/**
 * Overview: Visual editor for semantic type property schemas (list of PropertyDef).
 * Architecture: Shared form component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Property definition editing, add/remove/reorder rows, replaces raw JSON textarea
 */
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface PropertyDefRow {
  name: string;
  display_name: string;
  data_type: string;
  required: boolean;
  default_value: string;
  unit: string;
  description: string;
}

const DATA_TYPES = ['string', 'integer', 'float', 'boolean', 'json'];

@Component({
  selector: 'nimbus-property-schema-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="schema-editor">
      @if (rows.length === 0) {
        <div class="empty">No properties defined.</div>
      }
      @for (row of rows; track $index) {
        <div class="prop-row">
          <div class="prop-header">
            <span class="prop-num">{{ $index + 1 }}</span>
            <div class="prop-actions">
              @if ($index > 0) {
                <button type="button" class="icon-btn" (click)="moveUp($index)" title="Move up">&#9650;</button>
              }
              @if ($index < rows.length - 1) {
                <button type="button" class="icon-btn" (click)="moveDown($index)" title="Move down">&#9660;</button>
              }
              <button type="button" class="icon-btn danger" (click)="removeRow($index)" title="Remove">&times;</button>
            </div>
          </div>
          <div class="prop-fields">
            <div class="field-row">
              <div class="field third">
                <label>Name</label>
                <input type="text" [(ngModel)]="row.name" (ngModelChange)="emitChange()" placeholder="e.g. cpu_count" />
              </div>
              <div class="field third">
                <label>Display Name</label>
                <input type="text" [(ngModel)]="row.display_name" (ngModelChange)="emitChange()" placeholder="e.g. CPU Count" />
              </div>
              <div class="field sixth">
                <label>Type</label>
                <select [(ngModel)]="row.data_type" (ngModelChange)="emitChange()">
                  @for (dt of dataTypes; track dt) {
                    <option [value]="dt">{{ dt }}</option>
                  }
                </select>
              </div>
              <div class="field sixth">
                <label>Required</label>
                <label class="toggle">
                  <input type="checkbox" [(ngModel)]="row.required" (ngModelChange)="emitChange()" />
                  <span>{{ row.required ? 'Yes' : 'No' }}</span>
                </label>
              </div>
            </div>
            <div class="field-row">
              <div class="field third">
                <label>Default</label>
                <input type="text" [(ngModel)]="row.default_value" (ngModelChange)="emitChange()" placeholder="Optional" />
              </div>
              <div class="field sixth">
                <label>Unit</label>
                <input type="text" [(ngModel)]="row.unit" (ngModelChange)="emitChange()" placeholder="e.g. GB" />
              </div>
              <div class="field half">
                <label>Description</label>
                <input type="text" [(ngModel)]="row.description" (ngModelChange)="emitChange()" placeholder="Optional" />
              </div>
            </div>
          </div>
        </div>
      }
      <button type="button" class="add-btn" (click)="addRow()">+ Add Property</button>
    </div>
  `,
  styles: [`
    .schema-editor { display: flex; flex-direction: column; gap: 0.5rem; }
    .empty { font-size: 0.75rem; color: #94a3b8; padding: 0.5rem 0; }
    .prop-row {
      border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.625rem;
      background: #fafbfc;
    }
    .prop-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 0.5rem;
    }
    .prop-num {
      font-size: 0.625rem; font-weight: 700; color: #94a3b8;
      background: #e2e8f0; border-radius: 4px; padding: 0.125rem 0.375rem;
    }
    .prop-actions { display: flex; gap: 0.25rem; }
    .icon-btn {
      background: none; border: none; cursor: pointer; font-size: 0.75rem;
      color: #64748b; padding: 0.125rem 0.25rem; border-radius: 3px;
    }
    .icon-btn:hover { background: #e2e8f0; }
    .icon-btn.danger:hover { color: #dc2626; background: rgba(220,38,38,0.08); }
    .prop-fields { display: flex; flex-direction: column; gap: 0.375rem; }
    .field-row { display: flex; gap: 0.5rem; }
    .field { display: flex; flex-direction: column; }
    .field label {
      font-size: 0.625rem; font-weight: 600; color: #94a3b8;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.125rem;
    }
    .third { flex: 2; }
    .sixth { flex: 1; }
    .half { flex: 3; }
    input, select {
      width: 100%; box-sizing: border-box; padding: 0.3125rem 0.5rem;
      border: 1px solid #e2e8f0; border-radius: 4px; font-size: 0.75rem;
      font-family: inherit; color: #374151; background: #fff; outline: none;
    }
    input:focus, select:focus { border-color: #3b82f6; }
    .toggle {
      display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem;
      color: #374151; cursor: pointer; padding-top: 0.1875rem;
      text-transform: none; font-weight: 400; letter-spacing: 0;
    }
    .toggle input { width: auto; }
    .add-btn {
      display: inline-flex; align-items: center; gap: 0.25rem; align-self: flex-start;
      background: none; border: 1px dashed #cbd5e1; border-radius: 6px;
      padding: 0.375rem 0.75rem; font-size: 0.75rem; font-family: inherit;
      color: #64748b; cursor: pointer;
    }
    .add-btn:hover { border-color: #3b82f6; color: #3b82f6; }
  `],
})
export class PropertySchemaEditorComponent {
  dataTypes = DATA_TYPES;
  rows: PropertyDefRow[] = [];

  @Input()
  set value(val: PropertyDefRow[] | null) {
    if (val) {
      this.rows = val.map((p) => ({ ...p }));
    } else {
      this.rows = [];
    }
  }

  @Output() valueChange = new EventEmitter<PropertyDefRow[]>();

  addRow(): void {
    this.rows.push({
      name: '',
      display_name: '',
      data_type: 'string',
      required: false,
      default_value: '',
      unit: '',
      description: '',
    });
    this.emitChange();
  }

  removeRow(index: number): void {
    this.rows.splice(index, 1);
    this.emitChange();
  }

  moveUp(index: number): void {
    if (index <= 0) return;
    [this.rows[index - 1], this.rows[index]] = [this.rows[index], this.rows[index - 1]];
    this.emitChange();
  }

  moveDown(index: number): void {
    if (index >= this.rows.length - 1) return;
    [this.rows[index], this.rows[index + 1]] = [this.rows[index + 1], this.rows[index]];
    this.emitChange();
  }

  emitChange(): void {
    const clean = this.rows.map((r) => ({
      name: r.name,
      display_name: r.display_name,
      data_type: r.data_type,
      required: r.required,
      default_value: r.default_value || null,
      unit: r.unit || null,
      description: r.description || '',
    }));
    this.valueChange.emit(clean as any);
  }
}
