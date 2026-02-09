/**
 * Overview: String list editor — editable list of strings with add/remove buttons.
 * Architecture: Reusable sub-component for properties panel editors (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic list editing, string arrays, form array management
 */
import { Component, EventEmitter, Input, Output, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'nimbus-string-list-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="string-list-editor">
      @for (item of items(); track $index) {
        <div class="list-row">
          <input
            type="text"
            class="list-input"
            [ngModel]="item"
            (ngModelChange)="updateItem($index, $event)"
            [placeholder]="placeholder"
          />
          <button class="remove-btn" (click)="removeItem($index)" title="Remove">×</button>
        </div>
      }
      <button class="add-btn" (click)="addItem()">+ Add</button>
    </div>
  `,
  styles: [`
    .string-list-editor { display: flex; flex-direction: column; gap: 4px; }
    .list-row { display: flex; gap: 4px; align-items: center; }
    .list-input {
      flex: 1; padding: 5px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 4px; color: #1e293b; font-size: 0.8125rem; outline: none;
    }
    .list-input:focus { border-color: #3b82f6; }
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
export class StringListEditorComponent {
  @Input() placeholder = '';
  @Input() set value(val: string[]) {
    this.items.set(val ? [...val] : []);
  }
  @Output() valueChange = new EventEmitter<string[]>();

  items = signal<string[]>([]);

  updateItem(index: number, val: string): void {
    const updated = [...this.items()];
    updated[index] = val;
    this.items.set(updated);
    this.valueChange.emit(updated);
  }

  addItem(): void {
    const updated = [...this.items(), ''];
    this.items.set(updated);
    this.valueChange.emit(updated);
  }

  removeItem(index: number): void {
    const updated = this.items().filter((_, i) => i !== index);
    this.items.set(updated);
    this.valueChange.emit(updated);
  }
}
