/**
 * Overview: Searchable select dropdown — drop-in replacement for <select> with type-to-filter,
 *           keyboard navigation, and ControlValueAccessor support for ngModel and formControlName.
 * Architecture: Shared UI component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: ControlValueAccessor, keyboard navigation, dropdown overlay, client-side filtering
 */
import {
  Component,
  ElementRef,
  HostListener,
  Input,
  computed,
  forwardRef,
  signal,
  viewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';

export interface SelectOption {
  value: string;
  label: string;
}

@Component({
  selector: 'nimbus-searchable-select',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SearchableSelectComponent),
      multi: true,
    },
  ],
  template: `
    <div class="ss-wrapper" [class.ss-disabled]="isDisabled()">
      <button
        type="button"
        class="ss-trigger"
        [class.ss-open]="isOpen()"
        [class.ss-placeholder]="!selectedLabel()"
        [disabled]="isDisabled()"
        (click)="toggleDropdown()"
        (keydown)="onTriggerKeydown($event)"
        #triggerEl
      >
        <span class="ss-trigger-text">{{ selectedLabel() || placeholder }}</span>
        @if (allowClear && currentValue() && !isDisabled()) {
          <span class="ss-clear" (click)="clearValue($event)" title="Clear">&times;</span>
        }
        <span class="ss-arrow">&#9662;</span>
      </button>

      @if (isOpen()) {
        <div class="ss-dropdown" #dropdown>
          <input
            #searchEl
            type="text"
            class="ss-search"
            placeholder="Type to filter..."
            [ngModel]="searchTerm()"
            (ngModelChange)="onSearchChange($event)"
            (keydown)="onSearchKeydown($event)"
            autocomplete="off"
          />
          <div class="ss-options" #optionsList>
            @if (filteredOptions().length === 0) {
              <div class="ss-no-results">No matches found</div>
            }
            @for (opt of filteredOptions(); track opt.value; let i = $index) {
              <div
                class="ss-option"
                [class.ss-highlighted]="highlightIndex() === i"
                [class.ss-selected]="currentValue() === opt.value"
                (mousedown)="selectOption(opt)"
                (mouseenter)="highlightIndex.set(i)"
              >
                {{ opt.label }}
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .ss-wrapper { position: relative; width: 100%; }
    .ss-trigger {
      width: 100%; padding: 0.5rem 0.75rem; padding-right: 2.5rem;
      border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8125rem;
      box-sizing: border-box; font-family: inherit; background: #fff;
      cursor: pointer; text-align: left; transition: border-color 0.15s;
      display: flex; align-items: center; min-height: 2.25rem;
      color: #1e293b; position: relative;
    }
    .ss-trigger:hover:not(:disabled) { border-color: #cbd5e1; }
    .ss-trigger:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .ss-trigger.ss-open { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .ss-trigger.ss-placeholder .ss-trigger-text { color: #94a3b8; }
    .ss-trigger:disabled { background: #f8fafc; cursor: not-allowed; opacity: 0.7; }
    .ss-trigger-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ss-arrow {
      position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
      font-size: 0.625rem; color: #94a3b8; pointer-events: none;
    }
    .ss-clear {
      position: absolute; right: 1.75rem; top: 50%; transform: translateY(-50%);
      font-size: 0.875rem; color: #94a3b8; cursor: pointer; line-height: 1;
      padding: 0 0.25rem; z-index: 1;
    }
    .ss-clear:hover { color: #475569; }
    .ss-disabled { pointer-events: none; }
    .ss-dropdown {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); margin-top: 2px;
      overflow: hidden;
    }
    .ss-search {
      width: 100%; padding: 0.5rem 0.75rem; border: none;
      border-bottom: 1px solid #e2e8f0; font-size: 0.8125rem;
      font-family: inherit; box-sizing: border-box; outline: none;
    }
    .ss-search:focus { background: #fafbfc; }
    .ss-options { max-height: 200px; overflow-y: auto; }
    .ss-option {
      padding: 0.5rem 0.75rem; cursor: pointer; transition: background 0.1s;
      font-size: 0.8125rem; color: #1e293b;
    }
    .ss-option:hover, .ss-option.ss-highlighted { background: #f1f5f9; }
    .ss-option.ss-selected { font-weight: 600; color: #3b82f6; }
    .ss-no-results { padding: 0.5rem 0.75rem; color: #94a3b8; font-size: 0.8125rem; font-style: italic; }
  `],
})
export class SearchableSelectComponent implements ControlValueAccessor {
  @Input() options: SelectOption[] = [];
  @Input() placeholder = 'Select...';
  @Input() disabled = false;
  @Input() allowClear = false;

  isOpen = signal(false);
  searchTerm = signal('');
  highlightIndex = signal(0);
  currentValue = signal<string | null>(null);
  isDisabled = signal(false);

  triggerEl = viewChild<ElementRef<HTMLButtonElement>>('triggerEl');
  searchEl = viewChild<ElementRef<HTMLInputElement>>('searchEl');
  optionsList = viewChild<ElementRef<HTMLDivElement>>('optionsList');

  private onChange: (value: string | null) => void = () => {};
  private onTouched: () => void = () => {};

  selectedLabel = computed(() => {
    const val = this.currentValue();
    if (val == null) return '';
    const opt = this.options.find((o) => o.value === val);
    return opt?.label ?? '';
  });

  filteredOptions = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    if (!term) return this.options;
    return this.options.filter((o) => o.label.toLowerCase().includes(term));
  });

  // --- ControlValueAccessor ---

  writeValue(value: string | null): void {
    this.currentValue.set(value);
  }

  registerOnChange(fn: (value: string | null) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.isDisabled.set(isDisabled);
  }

  // --- Dropdown lifecycle ---

  toggleDropdown(): void {
    if (this.isOpen()) {
      this.close();
    } else {
      this.open();
    }
  }

  open(): void {
    this.isOpen.set(true);
    this.searchTerm.set('');
    this.highlightIndex.set(this.getSelectedIndex());
    setTimeout(() => this.searchEl()?.nativeElement.focus());
  }

  close(): void {
    this.isOpen.set(false);
    this.onTouched();
  }

  // --- Selection ---

  selectOption(option: SelectOption): void {
    this.currentValue.set(option.value);
    this.onChange(option.value);
    this.close();
    setTimeout(() => this.triggerEl()?.nativeElement.focus());
  }

  clearValue(event: MouseEvent): void {
    event.stopPropagation();
    this.currentValue.set(null);
    this.onChange(null);
  }

  // --- Keyboard ---

  onTriggerKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (!this.isOpen()) {
        this.open();
      }
    }
  }

  onSearchKeydown(event: KeyboardEvent): void {
    const opts = this.filteredOptions();
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.highlightIndex.update((i) => Math.min(i + 1, opts.length - 1));
        this.scrollToHighlighted();
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.highlightIndex.update((i) => Math.max(i - 1, 0));
        this.scrollToHighlighted();
        break;
      case 'Enter':
        event.preventDefault();
        if (opts.length > 0 && this.highlightIndex() >= 0 && this.highlightIndex() < opts.length) {
          this.selectOption(opts[this.highlightIndex()]);
        }
        break;
      case 'Escape':
        event.preventDefault();
        this.close();
        this.triggerEl()?.nativeElement.focus();
        break;
      case 'Tab':
        this.close();
        break;
    }
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
    this.highlightIndex.set(0);
  }

  // --- Click outside ---

  @HostListener('document:mousedown', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.isOpen()) return;
    const wrapper = this.triggerEl()?.nativeElement.closest('.ss-wrapper');
    if (wrapper && !wrapper.contains(event.target as Node)) {
      this.close();
    }
  }

  // --- Helpers ---

  private getSelectedIndex(): number {
    const val = this.currentValue();
    if (val == null) return 0;
    const idx = this.options.findIndex((o) => o.value === val);
    return idx >= 0 ? idx : 0;
  }

  private scrollToHighlighted(): void {
    setTimeout(() => {
      const list = this.optionsList()?.nativeElement;
      const highlighted = list?.querySelector('.ss-highlighted');
      if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
      }
    });
  }
}
