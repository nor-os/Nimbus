/**
 * Overview: Key-value map editor — edits Record<string,string> as key-value pairs.
 * Architecture: Reusable sub-component for properties panel editors (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Object editing as pair list, Record<string,string> conversion
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface MapEntry {
  key: string;
  value: string;
}

@Component({
  selector: 'nimbus-key-value-map-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="kv-map-editor">
      <div class="kv-header">
        <span class="kv-label">{{ keyLabel }}</span>
        <span class="kv-label">{{ valueLabel }}</span>
        <span class="kv-spacer"></span>
      </div>
      @for (entry of entries(); track $index) {
        <div class="kv-row">
          <input
            type="text"
            class="kv-input"
            [ngModel]="entry.key"
            (ngModelChange)="updateKey($index, $event)"
            [placeholder]="keyLabel"
          />
          <input
            type="text"
            class="kv-input"
            [ngModel]="entry.value"
            (ngModelChange)="updateValue($index, $event)"
            [placeholder]="valueLabel"
          />
          <button class="remove-btn" (click)="removeEntry($index)" title="Remove">×</button>
        </div>
      }
      <button class="add-btn" (click)="addEntry()">+ Add</button>
    </div>
  `,
  styles: [`
    .kv-map-editor { display: flex; flex-direction: column; gap: 4px; }
    .kv-header { display: flex; gap: 4px; align-items: center; }
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
export class KeyValueMapEditorComponent {
  @Input() keyLabel = 'Key';
  @Input() valueLabel = 'Value';
  @Input() set value(val: Record<string, string>) {
    if (val && typeof val === 'object') {
      this.entries.set(Object.entries(val).map(([key, value]) => ({ key, value })));
    } else {
      this.entries.set([]);
    }
  }
  @Output() valueChange = new EventEmitter<Record<string, string>>();

  entries = signal<MapEntry[]>([]);

  private emit(): void {
    const obj: Record<string, string> = {};
    for (const entry of this.entries()) {
      if (entry.key) {
        obj[entry.key] = entry.value;
      }
    }
    this.valueChange.emit(obj);
  }

  updateKey(index: number, key: string): void {
    const updated = this.entries().map((e, i) => i === index ? { ...e, key } : e);
    this.entries.set(updated);
    this.emit();
  }

  updateValue(index: number, value: string): void {
    const updated = this.entries().map((e, i) => i === index ? { ...e, value } : e);
    this.entries.set(updated);
    this.emit();
  }

  addEntry(): void {
    const updated = [...this.entries(), { key: '', value: '' }];
    this.entries.set(updated);
    this.emit();
  }

  removeEntry(index: number): void {
    const updated = this.entries().filter((_, i) => i !== index);
    this.entries.set(updated);
    this.emit();
  }
}
