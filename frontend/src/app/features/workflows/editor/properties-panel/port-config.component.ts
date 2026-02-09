/**
 * Overview: Port configuration component — editable port labels for Parallel/Switch nodes.
 * Architecture: Port editing component for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic ports, port labeling, parallel branches
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface PortConfig {
  name: string;
  label: string;
}

@Component({
  selector: 'nimbus-port-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="port-config">
      <label class="config-label">Output Ports</label>
      @for (port of ports; track port.name; let i = $index) {
        <div class="port-row">
          <input
            type="text"
            class="port-input"
            [ngModel]="port.label"
            (ngModelChange)="updatePort(i, $event)"
            [placeholder]="port.name"
          />
          @if (ports.length > 2) {
            <button class="port-remove" (click)="removePort(i)" title="Remove port">&#10005;</button>
          }
        </div>
      }
      <button class="add-port-btn" (click)="addPort()">+ Add Port</button>
    </div>
  `,
  styles: [`
    .port-config { display: flex; flex-direction: column; gap: 6px; }
    .config-label { font-size: 0.75rem; color: #64748b; }
    .port-row { display: flex; gap: 4px; }
    .port-input {
      flex: 1; padding: 4px 6px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-size: 0.75rem; outline: none;
    }
    .port-input:focus { border-color: #3b82f6; }
    .port-remove {
      padding: 2px 6px; background: none; border: 1px solid #fecaca;
      border-radius: 6px; color: #dc2626; cursor: pointer; font-size: 0.75rem;
    }
    .port-remove:hover { background: #fef2f2; }
    .add-port-btn {
      padding: 4px 8px; background: none; border: 1px dashed #e2e8f0;
      border-radius: 6px; color: #64748b; cursor: pointer; font-size: 0.75rem;
    }
    .add-port-btn:hover { border-color: #3b82f6; color: #3b82f6; }
  `],
})
export class PortConfigComponent {
  @Input() ports: PortConfig[] = [];
  @Output() portsChange = new EventEmitter<PortConfig[]>();

  updatePort(index: number, label: string): void {
    const updated = [...this.ports];
    updated[index] = { ...updated[index], label };
    this.portsChange.emit(updated);
  }

  addPort(): void {
    const name = `branch_${this.ports.length}`;
    this.portsChange.emit([...this.ports, { name, label: `Branch ${this.ports.length + 1}` }]);
  }

  removePort(index: number): void {
    const updated = this.ports.filter((_, i) => i !== index);
    this.portsChange.emit(updated);
  }
}
