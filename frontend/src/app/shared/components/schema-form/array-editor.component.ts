/**
 * Overview: Reusable array editor that replaces comma-separated text inputs with a chip/tag UI for string arrays.
 * Architecture: Shared reusable form component (Section 3)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Chip-based array editing, add/remove items, Enter key support
 */
import { Component, ChangeDetectionStrategy, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'nimbus-array-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="array-editor">
      <div class="chips-container">
        @for (item of items; track $index) {
          <span class="chip">
            <span class="chip-text">{{ item }}</span>
            <button
              type="button"
              class="chip-remove"
              (click)="removeItem($index)"
              title="Remove"
            >&times;</button>
          </span>
        }
        @if (items.length === 0) {
          <span class="empty-hint">No items added</span>
        }
      </div>
      <div class="add-row">
        <input
          type="text"
          class="add-input"
          placeholder="Type and press Enter to add..."
          [(ngModel)]="newItem"
          (keydown.enter)="addItem()"
        />
        <button
          type="button"
          class="add-btn"
          [disabled]="!newItem().trim()"
          (click)="addItem()"
        >Add</button>
      </div>
    </div>
  `,
  styles: [`
    .array-editor {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fff;
      padding: 12px;
    }

    .chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 32px;
      margin-bottom: 10px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #eff6ff;
      color: #3b82f6;
      border-radius: 16px;
      padding: 4px 8px 4px 12px;
      font-size: 13px;
      font-weight: 500;
      line-height: 1.4;
    }

    .chip-text {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .chip-remove {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border: none;
      background: transparent;
      color: #94a3b8;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border-radius: 50%;
      padding: 0;
      line-height: 1;
    }

    .chip-remove:hover {
      background: #dbeafe;
      color: #3b82f6;
    }

    .empty-hint {
      color: #94a3b8;
      font-size: 13px;
      font-style: italic;
      padding: 4px 0;
    }

    .add-row {
      display: flex;
      gap: 8px;
    }

    .add-input {
      flex: 1;
      padding: 7px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 13px;
      background: #fff;
      color: #1e293b;
      outline: none;
      transition: border-color 0.15s;
    }

    .add-input:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    .add-input::placeholder {
      color: #94a3b8;
    }

    .add-btn {
      padding: 7px 16px;
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .add-btn:hover:not(:disabled) {
      background: #2563eb;
    }

    .add-btn:disabled {
      background: #cbd5e1;
      cursor: not-allowed;
    }
  `]
})
export class ArrayEditorComponent {
  @Input() items: string[] = [];
  @Output() itemsChange = new EventEmitter<string[]>();

  newItem = signal('');

  addItem(): void {
    const val = this.newItem().trim();
    if (!val) return;
    const updated = [...this.items, val];
    this.items = updated;
    this.itemsChange.emit(updated);
    this.newItem.set('');
  }

  removeItem(index: number): void {
    const updated = this.items.filter((_, i) => i !== index);
    this.items = updated;
    this.itemsChange.emit(updated);
  }
}
