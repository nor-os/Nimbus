/**
 * Overview: Switch cases editor — editable list of switch cases with value, label, and port.
 * Architecture: Reusable sub-component for properties panel editors (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Switch/case editing, port assignment, multi-way branching configuration
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface SwitchCase {
  value: string;
  label: string;
  port: string;
}

@Component({
  selector: 'nimbus-switch-cases-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="switch-cases-editor">
      <div class="sc-header">
        <span class="sc-label">Value</span>
        <span class="sc-label">Label</span>
        <span class="sc-label sc-port-label">Port</span>
        <span class="sc-spacer"></span>
      </div>
      @for (c of cases(); track $index) {
        <div class="sc-row">
          <input
            type="text"
            class="sc-input"
            [ngModel]="c.value"
            (ngModelChange)="updateField($index, 'value', $event)"
            placeholder="Value"
          />
          <input
            type="text"
            class="sc-input"
            [ngModel]="c.label"
            (ngModelChange)="updateField($index, 'label', $event)"
            placeholder="Label"
          />
          <input
            type="text"
            class="sc-input sc-port-input"
            [ngModel]="c.port"
            (ngModelChange)="updateField($index, 'port', $event)"
            [placeholder]="derivePort(c.label)"
          />
          <button class="remove-btn" (click)="removeCase($index)" title="Remove">×</button>
        </div>
      }
      <button class="add-btn" (click)="addCase()">+ Add Case</button>
    </div>
  `,
  styles: [`
    .switch-cases-editor { display: flex; flex-direction: column; gap: 4px; }
    .sc-header { display: flex; gap: 4px; align-items: center; }
    .sc-label {
      flex: 1; font-size: 0.625rem; color: #94a3b8; text-transform: uppercase;
      letter-spacing: 0.05em; padding-left: 2px;
    }
    .sc-port-label { max-width: 60px; }
    .sc-spacer { width: 24px; }
    .sc-row { display: flex; gap: 4px; align-items: center; }
    .sc-input {
      flex: 1; padding: 5px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 4px; color: #1e293b; font-size: 0.8125rem; outline: none;
    }
    .sc-input:focus { border-color: #3b82f6; }
    .sc-port-input { max-width: 60px; font-size: 0.75rem; }
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
export class SwitchCasesEditorComponent {
  @Input() set value(val: SwitchCase[]) {
    this.cases.set(val ? val.map(c => ({ ...c })) : []);
  }
  @Output() valueChange = new EventEmitter<SwitchCase[]>();

  cases = signal<SwitchCase[]>([]);

  derivePort(label: string): string {
    return label ? label.toLowerCase().replace(/\s+/g, '_') : 'case';
  }

  updateField(index: number, field: keyof SwitchCase, val: string): void {
    const updated = this.cases().map((c, i) => {
      if (i !== index) return c;
      const patched = { ...c, [field]: val };
      // Auto-derive port from label if port is empty and label changed
      if (field === 'label' && !c.port) {
        patched.port = this.derivePort(val);
      }
      return patched;
    });
    this.cases.set(updated);
    this.valueChange.emit(updated);
  }

  addCase(): void {
    const updated = [...this.cases(), { value: '', label: '', port: '' }];
    this.cases.set(updated);
    this.valueChange.emit(updated);
  }

  removeCase(index: number): void {
    const updated = this.cases().filter((_, i) => i !== index);
    this.cases.set(updated);
    this.valueChange.emit(updated);
  }
}
