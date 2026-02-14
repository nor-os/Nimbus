/**
 * Overview: Compartment properties editor — label, defaults key-value editor, parent selection.
 * Architecture: Properties sub-panel for compartment editing (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Compartment label editing, defaults propagation, nested compartment hierarchy
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TopologyCompartment } from '@shared/models/architecture.model';
import { CompartmentPolicyPanelComponent } from './compartment-policy-panel.component';

@Component({
  selector: 'nimbus-compartment-properties',
  standalone: true,
  imports: [CommonModule, FormsModule, CompartmentPolicyPanelComponent],
  template: `
    <div class="compartment-props">
      <div class="form-group">
        <label class="form-label">Label</label>
        <input
          type="text"
          class="form-input"
          [ngModel]="compartment.label"
          (ngModelChange)="onLabelChange($event)"
          [disabled]="readOnly"
        />
      </div>

      <div class="form-group" *ngIf="parentOptions.length > 0">
        <label class="form-label">Parent Compartment</label>
        <select
          class="form-input"
          [ngModel]="compartment.parentCompartmentId || ''"
          (ngModelChange)="onParentChange($event)"
          [disabled]="readOnly"
        >
          <option value="">None (top-level)</option>
          <option *ngFor="let opt of parentOptions" [value]="opt.id">{{ opt.label }}</option>
        </select>
      </div>

      <div class="defaults-section">
        <div class="section-header">
          <span class="section-title">Defaults</span>
          @if (!readOnly) {
            <button class="btn-add" (click)="addDefault()">+ Add</button>
          }
        </div>
        @for (entry of defaultEntries; track entry.key) {
          <div class="default-row">
            <input
              type="text"
              class="default-key"
              [value]="entry.key"
              (change)="onDefaultKeyChange($index, $any($event.target).value)"
              [disabled]="readOnly"
              placeholder="Key"
            />
            <input
              type="text"
              class="default-value"
              [value]="entry.value"
              (change)="onDefaultValueChange(entry.key, $any($event.target).value)"
              [disabled]="readOnly"
              placeholder="Value"
            />
            @if (!readOnly) {
              <button class="btn-remove" (click)="removeDefault(entry.key)">&times;</button>
            }
          </div>
        }
        @if (defaultEntries.length === 0) {
          <div class="empty-hint">No defaults configured</div>
        }
      </div>

      <nimbus-compartment-policy-panel
        [compartment]="compartment"
        [topologyId]="topologyId"
        [readOnly]="readOnly"
        (update)="update.emit($event)"
      />
    </div>
  `,
  styles: [`
    .compartment-props { display: flex; flex-direction: column; gap: 12px; }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    .form-label {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
    }
    .form-input {
      padding: 6px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      font-family: inherit;
      outline: none;
    }
    .form-input:focus { border-color: #3b82f6; }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; }
    .defaults-section { margin-top: 4px; }
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .section-title {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
    }
    .btn-add {
      font-size: 0.6875rem;
      color: #3b82f6;
      background: none;
      border: none;
      cursor: pointer;
      font-weight: 500;
      font-family: inherit;
    }
    .btn-add:hover { text-decoration: underline; }
    .default-row {
      display: flex;
      gap: 4px;
      margin-bottom: 4px;
    }
    .default-key, .default-value {
      flex: 1;
      padding: 4px 6px;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 0.75rem;
      color: #1e293b;
      background: #fff;
      font-family: inherit;
      outline: none;
    }
    .default-key:focus, .default-value:focus { border-color: #3b82f6; }
    .default-key:disabled, .default-value:disabled { background: #f8fafc; }
    .btn-remove {
      width: 22px;
      height: 22px;
      border: none;
      background: none;
      color: #94a3b8;
      cursor: pointer;
      font-size: 0.875rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .btn-remove:hover { color: #dc2626; }
    .empty-hint {
      font-size: 0.75rem;
      color: #94a3b8;
      padding: 6px 0;
    }
  `],
})
export class CompartmentPropertiesComponent {
  @Input() compartment!: TopologyCompartment;
  @Input() parentOptions: { id: string; label: string }[] = [];
  @Input() topologyId: string = '';
  @Input() readOnly = false;

  @Output() update = new EventEmitter<Partial<TopologyCompartment>>();

  get defaultEntries(): { key: string; value: string }[] {
    const defaults = this.compartment.defaults || {};
    return Object.entries(defaults).map(([key, value]) => ({
      key,
      value: String(value),
    }));
  }

  onLabelChange(label: string): void {
    this.update.emit({ label });
  }

  onParentChange(parentId: string): void {
    this.update.emit({ parentCompartmentId: parentId || null });
  }

  addDefault(): void {
    const defaults = { ...(this.compartment.defaults || {}) };
    const key = `key_${Date.now().toString(36)}`;
    defaults[key] = '';
    this.update.emit({ defaults });
  }

  onDefaultKeyChange(index: number, newKey: string): void {
    const entries = this.defaultEntries;
    if (index >= entries.length) return;
    const oldKey = entries[index].key;
    const defaults = { ...(this.compartment.defaults || {}) };
    const value = defaults[oldKey];
    delete defaults[oldKey];
    defaults[newKey] = value;
    this.update.emit({ defaults });
  }

  onDefaultValueChange(key: string, value: string): void {
    const defaults = { ...(this.compartment.defaults || {}) };
    defaults[key] = value;
    this.update.emit({ defaults });
  }

  removeDefault(key: string): void {
    const defaults = { ...(this.compartment.defaults || {}) };
    delete defaults[key];
    this.update.emit({ defaults });
  }
}
