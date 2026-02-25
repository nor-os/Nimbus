/**
 * Overview: Inline editable table for security rules (inbound/outbound) with provider-specific columns.
 * Architecture: Shared component for subnet-level security rule editing (Section 7.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Provider-aware rule columns, inline add/remove, two-way binding via rulesChange
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface ColumnDef {
  key: string;
  label: string;
  type: 'text' | 'select' | 'number';
  options?: string[];
  placeholder?: string;
  width?: string;
}

@Component({
  selector: 'nimbus-security-rule-table',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="rule-table-container">
      <div class="rule-table-header">
        <span class="rule-direction">{{ direction === 'inbound' ? 'Inbound Rules' : 'Outbound Rules' }}</span>
        <button class="add-rule-btn" (click)="addRule()">+ Add Rule</button>
      </div>
      @if (rules.length === 0) {
        <p class="no-rules">No {{ direction }} rules defined.</p>
      } @else {
        <div class="table-scroll">
          <table class="rule-table">
            <thead>
              <tr>
                @for (col of columns; track col.key) {
                  <th [style.width]="col.width || 'auto'">{{ col.label }}</th>
                }
                <th class="action-col"></th>
              </tr>
            </thead>
            <tbody>
              @for (rule of rules; let i = $index; track i) {
                <tr>
                  @for (col of columns; track col.key) {
                    <td>
                      @if (col.type === 'select') {
                        <select
                          class="cell-input"
                          [ngModel]="rule[col.key]"
                          (ngModelChange)="onCellChange(i, col.key, $event)"
                        >
                          <option value="">—</option>
                          @for (opt of col.options; track opt) {
                            <option [value]="opt">{{ opt }}</option>
                          }
                        </select>
                      } @else if (col.type === 'number') {
                        <input
                          type="number"
                          class="cell-input"
                          [ngModel]="rule[col.key]"
                          (ngModelChange)="onCellChange(i, col.key, $event)"
                          [placeholder]="col.placeholder || ''"
                        />
                      } @else {
                        <input
                          type="text"
                          class="cell-input"
                          [ngModel]="rule[col.key]"
                          (ngModelChange)="onCellChange(i, col.key, $event)"
                          [placeholder]="col.placeholder || ''"
                        />
                      }
                    </td>
                  }
                  <td class="action-col">
                    <button class="remove-btn" (click)="removeRule(i)" title="Remove">&times;</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
  styles: [`
    .rule-table-container { margin-bottom: 8px; }
    .rule-table-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 6px;
    }
    .rule-direction {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.04em;
    }
    .add-rule-btn {
      padding: 3px 10px; font-size: 0.6875rem; font-weight: 500;
      color: #3b82f6; background: none; border: 1px solid #3b82f6;
      border-radius: 4px; cursor: pointer; font-family: inherit;
    }
    .add-rule-btn:hover { background: #eff6ff; }
    .no-rules { font-size: 0.75rem; color: #94a3b8; margin: 4px 0; }
    .table-scroll { overflow-x: auto; }
    .rule-table {
      width: 100%; border-collapse: collapse;
      border: 1px solid #e2e8f0; border-radius: 4px;
    }
    .rule-table th {
      padding: 4px 6px; text-align: left; font-size: 0.625rem;
      font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
      color: #64748b; border-bottom: 1px solid #e2e8f0; background: #fafbfc;
    }
    .rule-table td {
      padding: 2px 4px; border-bottom: 1px solid #f1f5f9;
    }
    .rule-table tr:last-child td { border-bottom: none; }
    .cell-input {
      width: 100%; padding: 4px 6px; border: 1px solid #e2e8f0;
      border-radius: 4px; font-size: 0.75rem; color: #1e293b;
      background: #fff; outline: none; font-family: inherit;
      box-sizing: border-box;
    }
    .cell-input:focus { border-color: #3b82f6; }
    select.cell-input { padding: 3px 4px; }
    .action-col { width: 30px; text-align: center; }
    .remove-btn {
      background: none; border: none; color: #ef4444; font-size: 1rem;
      cursor: pointer; padding: 2px 4px; line-height: 1; font-family: inherit;
    }
    .remove-btn:hover { color: #dc2626; }
  `],
})
export class SecurityRuleTableComponent {
  @Input() rules: Record<string, unknown>[] = [];
  @Input() providerName = '';
  @Input() direction: 'inbound' | 'outbound' = 'inbound';
  @Output() rulesChange = new EventEmitter<Record<string, unknown>[]>();

  get columns(): ColumnDef[] {
    return this.getColumnsForProvider(this.providerName, this.direction);
  }

  private getColumnsForProvider(provider: string, dir: string): ColumnDef[] {
    switch (provider) {
      case 'aws':
        return [
          { key: 'protocol', label: 'Protocol', type: 'select', options: ['tcp', 'udp', 'icmp', '-1'], width: '90px' },
          { key: 'port_range', label: 'Port', type: 'text', placeholder: '443', width: '70px' },
          { key: dir === 'inbound' ? 'source' : 'destination', label: dir === 'inbound' ? 'Source' : 'Dest', type: 'text', placeholder: '0.0.0.0/0' },
          { key: 'description', label: 'Description', type: 'text', placeholder: '' },
        ];
      case 'azure':
        return [
          { key: 'priority', label: 'Priority', type: 'number', placeholder: '100', width: '70px' },
          { key: 'access', label: 'Access', type: 'select', options: ['Allow', 'Deny'], width: '80px' },
          { key: 'protocol', label: 'Protocol', type: 'select', options: ['Tcp', 'Udp', 'Icmp', '*'], width: '80px' },
          { key: 'source_range', label: 'Source', type: 'text', placeholder: '*' },
          { key: 'dest_port_range', label: 'Dest Port', type: 'text', placeholder: '443', width: '80px' },
          { key: 'description', label: 'Description', type: 'text' },
        ];
      case 'gcp':
        return [
          { key: 'protocol', label: 'Protocol', type: 'text', placeholder: 'tcp', width: '80px' },
          { key: 'ports', label: 'Ports', type: 'text', placeholder: '443,8080' },
          { key: 'source_ranges', label: 'Source Ranges', type: 'text', placeholder: '0.0.0.0/0' },
        ];
      case 'oci':
        return [
          { key: 'protocol', label: 'Protocol', type: 'text', placeholder: '6', width: '70px' },
          { key: dir === 'inbound' ? 'source' : 'destination', label: dir === 'inbound' ? 'Source' : 'Dest', type: 'text', placeholder: '0.0.0.0/0' },
          { key: 'tcp_options', label: 'TCP Options', type: 'text', placeholder: '' },
        ];
      case 'proxmox':
        return [
          { key: 'direction', label: 'Dir', type: 'select', options: ['IN', 'OUT'], width: '65px' },
          { key: 'action', label: 'Action', type: 'select', options: ['ACCEPT', 'DROP', 'REJECT'], width: '80px' },
          { key: 'source', label: 'Source', type: 'text', placeholder: '' },
          { key: 'dest', label: 'Dest', type: 'text', placeholder: '' },
          { key: 'proto', label: 'Proto', type: 'text', placeholder: 'tcp', width: '60px' },
          { key: 'dport', label: 'Port', type: 'text', placeholder: '443', width: '60px' },
        ];
      default:
        return [
          { key: 'protocol', label: 'Protocol', type: 'text', width: '80px' },
          { key: 'port', label: 'Port', type: 'text', width: '70px' },
          { key: 'source', label: 'Source', type: 'text' },
          { key: 'description', label: 'Description', type: 'text' },
        ];
    }
  }

  onCellChange(index: number, key: string, value: unknown): void {
    const updated = this.rules.map((r, i) =>
      i === index ? { ...r, [key]: value } : { ...r }
    );
    this.rulesChange.emit(updated);
  }

  addRule(): void {
    const newRule: Record<string, unknown> = {};
    for (const col of this.columns) {
      newRule[col.key] = col.type === 'number' ? null : '';
    }
    this.rulesChange.emit([...this.rules, newRule]);
  }

  removeRule(index: number): void {
    const updated = this.rules.filter((_, i) => i !== index);
    this.rulesChange.emit(updated);
  }
}
