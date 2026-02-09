/**
 * Overview: Key-value list editor — list of {key, value} pairs with configurable column labels.
 * Architecture: Reusable sub-component for properties panel editors (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Key-value pair editing, variable assignments, expression mapping
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface KeyValuePair {
  variable: string;
  expression: string;
}

@Component({
  selector: 'nimbus-key-value-list-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="kv-list-editor">
      <div class="kv-header">
        <span class="kv-label">{{ keyLabel }}</span>
        <span class="kv-label">{{ valueLabel }}</span>
        <span class="kv-spacer"></span>
      </div>
      @for (item of items(); track $index) {
        <div class="kv-row">
          <input
            type="text"
            class="kv-input"
            [ngModel]="item.variable"
            (ngModelChange)="updateKey($index, $event)"
            [placeholder]="keyLabel"
          />
          <input
            type="text"
            class="kv-input expression-font"
            [ngModel]="item.expression"
            (ngModelChange)="updateValue($index, $event)"
            [placeholder]="valueLabel"
          />
          <button class="remove-btn" (click)="removeItem($index)" title="Remove">×</button>
        </div>
      }
      <button class="add-btn" (click)="addItem()">+ Add</button>
    </div>
  `,
  styles: [`
    .kv-list-editor { display: flex; flex-direction: column; gap: 4px; }
    .kv-header {
      display: flex; gap: 4px; align-items: center;
    }
    .kv-label {
      flex: 1; font-size: 0.625rem; color: #94a3b8; text-transform: uppercase;
      letter-spacing: 0.05em; padding-left: 2px;
    }
    .kv-spacer { width: 24px; }
    .kv-row { display: flex; gap: 4px; align-items: center; }
    .kv-input {
      flex: 1; padding: 5px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 4px; color: #1e293b; font-size: 0.8125rem; outline: none;
    }
    .kv-input:focus { border-color: #3b82f6; }
    .expression-font { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
    .remove-btn {
      width: 24px; height: 24px; border: none; background: #fee2e2; color: #dc2626;
      border-radius: 4px; cursor: pointer; font-size: 1rem; line-height: 1;
      display: flex; align-items: center; justify-content: center;
    }
    .remove-btn:hover { background: #fecaca; }
    .add-btn {
      padding: 4px 8px; border: 1px dashed #cbd5e1; background: #f8fafc; color: #64748b;
      border-radius: 4px; cursor: pointer; font-size: 0.75rem; text-align: left;
    }
    .add-btn:hover { border-color: #3b82f6; color: #3b82f6; }
  `],
})
export class KeyValueListEditorComponent {
  @Input() keyLabel = 'Key';
  @Input() valueLabel = 'Value';
  @Input() set value(val: KeyValuePair[]) {
    this.items.set(val ? val.map(v => ({ ...v })) : []);
  }
  @Output() valueChange = new EventEmitter<KeyValuePair[]>();

  items = signal<KeyValuePair[]>([]);

  updateKey(index: number, key: string): void {
    const updated = this.items().map((item, i) =>
      i === index ? { ...item, variable: key } : item
    );
    this.items.set(updated);
    this.valueChange.emit(updated);
  }

  updateValue(index: number, val: string): void {
    const updated = this.items().map((item, i) =>
      i === index ? { ...item, expression: val } : item
    );
    this.items.set(updated);
    this.valueChange.emit(updated);
  }

  addItem(): void {
    const updated = [...this.items(), { variable: '', expression: '' }];
    this.items.set(updated);
    this.valueChange.emit(updated);
  }

  removeItem(index: number): void {
    const updated = this.items().filter((_, i) => i !== index);
    this.items.set(updated);
    this.valueChange.emit(updated);
  }
}
