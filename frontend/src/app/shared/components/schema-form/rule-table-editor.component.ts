/**
 * Overview: Editable table for arrays of objects (security group rules, IAM roles, subnets) with inline editing per column.
 * Architecture: Shared reusable form component (Section 3)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Dynamic table rendering, column definitions, inline editing, row add/remove
 */
import { Component, ChangeDetectionStrategy, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface ColumnDef {
  key: string;
  title: string;
  type: string;
  options?: string[];
}

@Component({
  selector: 'nimbus-rule-table-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="rule-table-wrapper">
      <div class="table-scroll">
        <table class="rule-table">
          <thead>
            <tr>
              @for (col of columns; track col.key) {
                <th>{{ col.title }}</th>
              }
              <th class="action-col"></th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows; track $index) {
              <tr>
                @for (col of columns; track col.key) {
                  <td>
                    @switch (col.type) {
                      @case ('select') {
                        <select
                          class="cell-select"
                          [ngModel]="row[col.key]"
                          (ngModelChange)="onCellChange($index, col.key, $event)"
                        >
                          <option value="" disabled>Select...</option>
                          @for (opt of col.options || []; track opt) {
                            <option [value]="opt">{{ opt }}</option>
                          }
                        </select>
                      }
                      @case ('number') {
                        <input
                          type="number"
                          class="cell-input"
                          [ngModel]="row[col.key]"
                          (ngModelChange)="onCellChange($index, col.key, $event)"
                        />
                      }
                      @case ('array') {
                        <input
                          type="text"
                          class="cell-input"
                          [ngModel]="asCommaSeparated(row[col.key])"
                          (ngModelChange)="onCellChange($index, col.key, splitComma($event))"
                          placeholder="comma, separated, values"
                        />
                      }
                      @default {
                        <input
                          type="text"
                          class="cell-input"
                          [ngModel]="row[col.key]"
                          (ngModelChange)="onCellChange($index, col.key, $event)"
                        />
                      }
                    }
                  </td>
                }
                <td class="action-col">
                  <button
                    type="button"
                    class="remove-btn"
                    title="Remove row"
                    (click)="removeRow($index)"
                  >&times;</button>
                </td>
              </tr>
            }
            @if (rows.length === 0) {
              <tr>
                <td [attr.colspan]="columns.length + 1" class="empty-cell">
                  No rows. Click "Add Row" to begin.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <button type="button" class="add-row-btn" (click)="addRow()">
        + Add Row
      </button>
    </div>
  `,
  styles: [`
    .rule-table-wrapper {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }

    .table-scroll {
      overflow-x: auto;
    }

    .rule-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .rule-table th {
      background: #fafbfc;
      border-bottom: 1px solid #e2e8f0;
      padding: 8px 10px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      color: #475569;
      white-space: nowrap;
    }

    .rule-table td {
      border-bottom: 1px solid #e2e8f0;
      padding: 4px 6px;
      background: #fff;
      vertical-align: middle;
    }

    .rule-table tbody tr:last-child td {
      border-bottom: none;
    }

    .cell-input, .cell-select {
      width: 100%;
      padding: 5px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 13px;
      background: #fff;
      color: #1e293b;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.15s;
    }

    .cell-input:focus, .cell-select:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    .action-col {
      width: 36px;
      text-align: center;
    }

    .remove-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border: none;
      background: transparent;
      color: #94a3b8;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      border-radius: 4px;
      padding: 0;
      line-height: 1;
    }

    .remove-btn:hover {
      background: #fee2e2;
      color: #ef4444;
    }

    .empty-cell {
      text-align: center;
      color: #94a3b8;
      font-style: italic;
      padding: 16px !important;
    }

    .add-row-btn {
      display: block;
      width: 100%;
      padding: 8px;
      border: none;
      border-top: 1px solid #e2e8f0;
      background: #f8fafc;
      color: #3b82f6;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .add-row-btn:hover {
      background: #eff6ff;
    }
  `]
})
export class RuleTableEditorComponent {
  @Input() columns: ColumnDef[] = [];
  @Input() rows: Record<string, unknown>[] = [];
  @Output() rowsChange = new EventEmitter<Record<string, unknown>[]>();

  onCellChange(rowIndex: number, key: string, value: unknown): void {
    const updated = this.rows.map((row, i) =>
      i === rowIndex ? { ...row, [key]: value } : row
    );
    this.rows = updated;
    this.rowsChange.emit(updated);
  }

  asCommaSeparated(val: unknown): string {
    if (Array.isArray(val)) return (val as string[]).join(', ');
    return '';
  }

  splitComma(csv: string): string[] {
    if (!csv.trim()) return [];
    return csv.split(',').map(s => s.trim()).filter(s => s.length > 0);
  }

  addRow(): void {
    const newRow: Record<string, unknown> = {};
    for (const col of this.columns) {
      if (col.type === 'number') {
        newRow[col.key] = 0;
      } else if (col.type === 'select' && col.options?.length) {
        newRow[col.key] = col.options[0];
      } else if (col.type === 'array') {
        newRow[col.key] = [];
      } else {
        newRow[col.key] = '';
      }
    }
    const updated = [...this.rows, newRow];
    this.rows = updated;
    this.rowsChange.emit(updated);
  }

  removeRow(index: number): void {
    const updated = this.rows.filter((_, i) => i !== index);
    this.rows = updated;
    this.rowsChange.emit(updated);
  }
}
