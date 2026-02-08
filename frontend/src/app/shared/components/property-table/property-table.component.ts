/**
 * Overview: Reusable typed property editor with support for text, number, email, textarea, select, toggle, and readonly fields.
 * Architecture: Shared UI component for structured property editing (Section 3.2)
 * Dependencies: @angular/core, @angular/forms
 * Concepts: Property-based editing, batch save vs per-field emit, inline extras
 */
import { Component, input, output, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export type PropertyControlType = 'text' | 'number' | 'email' | 'textarea' | 'select' | 'toggle' | 'readonly';

export interface SelectOption {
  label: string;
  value: string | number;
}

export interface PropertyExtra {
  key: string;
  label: string;
  controlType: PropertyControlType;
  options?: SelectOption[];
  width?: string;
}

export interface PropertyField {
  key: string;
  label: string;
  controlType: PropertyControlType;
  placeholder?: string;
  required?: boolean;
  min?: number;
  max?: number;
  options?: SelectOption[];
  disabled?: boolean;
  suffix?: string;
  hint?: string;
  extras?: PropertyExtra[];
}

export interface PropertyChangeEvent {
  key: string;
  value: unknown;
  extraKey?: string;
}

@Component({
  selector: 'nimbus-property-table',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="property-table">
      @for (field of fields(); track field.key) {
        <div class="property-row">
          <label class="property-label">
            {{ field.label }}
            @if (field.required) { <span class="required">*</span> }
          </label>
          <div class="property-value">
            <div class="input-group">
              @switch (field.controlType) {
                @case ('readonly') {
                  <span class="readonly-value">{{ formatValue(field.key) }}</span>
                }
                @case ('text') {
                  <input
                    type="text"
                    class="form-input"
                    [placeholder]="field.placeholder ?? ''"
                    [disabled]="field.disabled ?? false"
                    [value]="getStringValue(field.key)"
                    (input)="onInput(field.key, $event)"
                    (blur)="onBlur(field.key)"
                  />
                }
                @case ('number') {
                  <input
                    type="number"
                    class="form-input"
                    [placeholder]="field.placeholder ?? ''"
                    [disabled]="field.disabled ?? false"
                    [min]="field.min ?? ''"
                    [max]="field.max ?? ''"
                    [value]="getNumberValue(field.key)"
                    (input)="onNumberInput(field.key, $event)"
                    (blur)="onBlur(field.key)"
                  />
                }
                @case ('email') {
                  <input
                    type="email"
                    class="form-input"
                    [placeholder]="field.placeholder ?? ''"
                    [disabled]="field.disabled ?? false"
                    [value]="getStringValue(field.key)"
                    (input)="onInput(field.key, $event)"
                    (blur)="onBlur(field.key)"
                  />
                }
                @case ('textarea') {
                  <textarea
                    class="form-input textarea"
                    rows="3"
                    [placeholder]="field.placeholder ?? ''"
                    [disabled]="field.disabled ?? false"
                    [value]="getStringValue(field.key)"
                    (input)="onInput(field.key, $event)"
                    (blur)="onBlur(field.key)"
                  ></textarea>
                }
                @case ('select') {
                  <select
                    class="form-input"
                    [disabled]="field.disabled ?? false"
                    [value]="getStringValue(field.key)"
                    (change)="onSelectChange(field.key, $event)"
                  >
                    @for (opt of field.options ?? []; track opt.value) {
                      <option [value]="opt.value" [selected]="getStringValue(field.key) === '' + opt.value">
                        {{ opt.label }}
                      </option>
                    }
                  </select>
                }
                @case ('toggle') {
                  <label class="toggle-wrapper">
                    <input
                      type="checkbox"
                      class="toggle-input"
                      [checked]="getBoolValue(field.key)"
                      [disabled]="field.disabled ?? false"
                      (change)="onToggleChange(field.key, $event)"
                    />
                    <span class="toggle-track"><span class="toggle-thumb"></span></span>
                  </label>
                }
              }
              @if (field.suffix) {
                <span class="suffix">{{ field.suffix }}</span>
              }
              @if (field.extras) {
                @for (extra of field.extras; track extra.key) {
                  @if (extra.label) {
                    <span class="extra-label">{{ extra.label }}</span>
                  }
                  @switch (extra.controlType) {
                    @case ('select') {
                      <select
                        class="form-input extra-input"
                        [style.width]="extra.width ?? '120px'"
                        [value]="getExtraValue(field.key, extra.key)"
                        (change)="onExtraSelectChange(field.key, extra.key, $event)"
                      >
                        @for (opt of extra.options ?? []; track opt.value) {
                          <option [value]="opt.value" [selected]="getExtraValue(field.key, extra.key) === '' + opt.value">
                            {{ opt.label }}
                          </option>
                        }
                      </select>
                    }
                    @case ('text') {
                      <input
                        type="text"
                        class="form-input extra-input"
                        [style.width]="extra.width ?? '120px'"
                        [value]="getExtraValue(field.key, extra.key)"
                        (input)="onExtraInput(field.key, extra.key, $event)"
                        (blur)="onExtraBlur(field.key, extra.key)"
                      />
                    }
                  }
                }
              }
            </div>
            @if (field.hint) {
              <span class="hint">{{ field.hint }}</span>
            }
          </div>
        </div>
      }

      @if (showSave()) {
        <div class="property-footer">
          <button class="btn btn-primary" [disabled]="saving() || !isDirty()" (click)="onSave()">
            {{ saving() ? 'Saving...' : 'Save Changes' }}
          </button>
          <button class="btn btn-secondary" [disabled]="saving() || !isDirty()" (click)="onReset()">
            Reset
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .property-table {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    }
    .property-row {
      display: flex; align-items: flex-start; padding: 0.75rem 1.25rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .property-row:last-of-type { border-bottom: none; }
    .property-label {
      min-width: 160px; width: 160px; font-size: 0.8125rem; font-weight: 600;
      color: #64748b; padding-top: 0.4375rem;
    }
    .required { color: #ef4444; }
    .property-value { flex: 1; min-width: 0; }
    .input-group { display: flex; align-items: center; gap: 0.5rem; }
    .form-input {
      flex: 1; padding: 0.4375rem 0.625rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit;
      box-sizing: border-box; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .form-input.textarea { resize: vertical; min-height: 60px; }
    select.form-input { cursor: pointer; }
    .extra-input { flex: none; }
    .extra-label { font-size: 0.75rem; color: #64748b; white-space: nowrap; }
    .readonly-value { font-size: 0.8125rem; color: #1e293b; padding: 0.4375rem 0; display: block; }
    .suffix { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; }
    .hint { display: block; font-size: 0.6875rem; color: #94a3b8; margin-top: 0.25rem; }
    .toggle-wrapper { display: flex; align-items: center; cursor: pointer; padding: 0.25rem 0; }
    .toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
    .toggle-track {
      position: relative; width: 36px; height: 20px; background: #cbd5e1;
      border-radius: 10px; transition: background 0.2s;
    }
    .toggle-input:checked + .toggle-track { background: #3b82f6; }
    .toggle-thumb {
      position: absolute; top: 2px; left: 2px; width: 16px; height: 16px;
      background: #fff; border-radius: 50%; transition: transform 0.2s;
    }
    .toggle-input:checked + .toggle-track .toggle-thumb { transform: translateX(16px); }
    .toggle-input:disabled + .toggle-track { opacity: 0.5; cursor: not-allowed; }
    .property-footer {
      display: flex; gap: 0.5rem; padding: 1rem 1.25rem;
      border-top: 1px solid #e2e8f0; background: #f8fafc;
    }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: background 0.15s; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover:not(:disabled) { background: #f1f5f9; }
  `],
})
export class PropertyTableComponent {
  fields = input.required<PropertyField[]>();
  data = input.required<Record<string, unknown>>();
  showSave = input(false);
  saving = input(false);

  valueChange = output<PropertyChangeEvent>();
  save = output<Record<string, unknown>>();

  private editBuffer = signal<Record<string, unknown>>({});
  private originalSnapshot = signal<Record<string, unknown>>({});
  private initialized = false;

  constructor() {
    effect(() => {
      const d = this.data();
      if (d) {
        this.editBuffer.set({ ...d });
        this.originalSnapshot.set({ ...d });
        this.initialized = true;
      }
    }, { allowSignalWrites: true });
  }

  isDirty = computed(() => {
    const current = this.editBuffer();
    const original = this.originalSnapshot();
    return Object.keys(current).some((k) => current[k] !== original[k]);
  });

  getStringValue(key: string): string {
    const val = this.editBuffer()[key];
    return val != null ? String(val) : '';
  }

  getNumberValue(key: string): number | string {
    const val = this.editBuffer()[key];
    return typeof val === 'number' ? val : '';
  }

  getBoolValue(key: string): boolean {
    return !!this.editBuffer()[key];
  }

  formatValue(key: string): string {
    const val = this.editBuffer()[key];
    return val != null ? String(val) : '—';
  }

  getExtraValue(fieldKey: string, extraKey: string): string {
    const compositeKey = `${fieldKey}__${extraKey}`;
    const val = this.editBuffer()[compositeKey];
    return val != null ? String(val) : '';
  }

  onInput(key: string, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.editBuffer.update((b) => ({ ...b, [key]: value }));
  }

  onNumberInput(key: string, event: Event): void {
    const raw = (event.target as HTMLInputElement).value;
    const value = raw === '' ? null : Number(raw);
    this.editBuffer.update((b) => ({ ...b, [key]: value }));
  }

  onBlur(key: string): void {
    if (!this.showSave()) {
      this.valueChange.emit({ key, value: this.editBuffer()[key] });
    }
  }

  onSelectChange(key: string, event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.editBuffer.update((b) => ({ ...b, [key]: value }));
    if (!this.showSave()) {
      this.valueChange.emit({ key, value });
    }
  }

  onToggleChange(key: string, event: Event): void {
    const value = (event.target as HTMLInputElement).checked;
    this.editBuffer.update((b) => ({ ...b, [key]: value }));
    if (!this.showSave()) {
      this.valueChange.emit({ key, value });
    }
  }

  onExtraInput(fieldKey: string, extraKey: string, event: Event): void {
    const compositeKey = `${fieldKey}__${extraKey}`;
    const value = (event.target as HTMLInputElement).value;
    this.editBuffer.update((b) => ({ ...b, [compositeKey]: value }));
  }

  onExtraBlur(fieldKey: string, extraKey: string): void {
    if (!this.showSave()) {
      const compositeKey = `${fieldKey}__${extraKey}`;
      this.valueChange.emit({ key: fieldKey, value: this.editBuffer()[compositeKey], extraKey });
    }
  }

  onExtraSelectChange(fieldKey: string, extraKey: string, event: Event): void {
    const compositeKey = `${fieldKey}__${extraKey}`;
    const value = (event.target as HTMLSelectElement).value;
    this.editBuffer.update((b) => ({ ...b, [compositeKey]: value }));
    if (!this.showSave()) {
      this.valueChange.emit({ key: fieldKey, value, extraKey });
    }
  }

  onSave(): void {
    const current = this.editBuffer();
    this.save.emit({ ...current });
    this.originalSnapshot.set({ ...current });
  }

  onReset(): void {
    this.editBuffer.set({ ...this.originalSnapshot() });
  }
}
