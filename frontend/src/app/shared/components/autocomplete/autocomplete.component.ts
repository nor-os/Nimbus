/**
 * Overview: Reusable typeahead autocomplete with keyboard navigation and client-side filtering.
 * Architecture: Shared UI component for entity selection (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Typeahead, keyboard navigation, dropdown overlay, client-side search
 */
import {
  Component,
  ElementRef,
  HostListener,
  input,
  output,
  signal,
  computed,
  viewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface AutocompleteOption {
  id: string;
  label: string;
  sublabel?: string;
}

@Component({
  selector: 'nimbus-autocomplete',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="autocomplete-wrapper">
      <input
        #inputEl
        type="text"
        class="autocomplete-input"
        [placeholder]="placeholder()"
        [(ngModel)]="query"
        (ngModelChange)="onQueryChange($event)"
        (focus)="onFocus()"
        (keydown)="onKeydown($event)"
        autocomplete="off"
      />
      @if (isOpen() && filteredOptions().length > 0) {
        <div class="autocomplete-dropdown" #dropdown>
          @for (option of filteredOptions(); track option.id; let i = $index) {
            <div
              class="autocomplete-option"
              [class.highlighted]="highlightIndex() === i"
              (mousedown)="selectOption(option)"
              (mouseenter)="highlightIndex.set(i)"
            >
              <span class="option-label">{{ option.label }}</span>
              @if (option.sublabel) {
                <span class="option-sublabel">{{ option.sublabel }}</span>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .autocomplete-wrapper { position: relative; width: 100%; }
    .autocomplete-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .autocomplete-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .autocomplete-dropdown {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); margin-top: 2px;
      max-height: 240px; overflow-y: auto;
    }
    .autocomplete-option {
      padding: 0.5rem 0.75rem; cursor: pointer; transition: background 0.1s;
      display: flex; flex-direction: column; gap: 0.125rem;
    }
    .autocomplete-option:hover,
    .autocomplete-option.highlighted { background: #f1f5f9; }
    .option-label { font-size: 0.8125rem; color: #1e293b; font-weight: 500; }
    .option-sublabel { font-size: 0.6875rem; color: #94a3b8; }
  `],
})
export class AutocompleteComponent {
  options = input.required<AutocompleteOption[]>();
  placeholder = input<string>('Search...');
  minChars = input<number>(0);
  maxResults = input<number>(50);

  selected = output<AutocompleteOption>();
  queryChanged = output<string>();

  query = '';
  isOpen = signal(false);
  highlightIndex = signal(-1);

  inputEl = viewChild<ElementRef<HTMLInputElement>>('inputEl');

  filteredOptions = computed(() => {
    const q = this.query.toLowerCase().trim();
    const min = this.minChars();
    if (q.length < min) return [];
    const opts = this.options().filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        (o.sublabel?.toLowerCase().includes(q) ?? false),
    );
    return opts.slice(0, this.maxResults());
  });

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const el = this.inputEl()?.nativeElement;
    if (el && !el.closest('.autocomplete-wrapper')?.contains(event.target as Node)) {
      this.isOpen.set(false);
    }
  }

  onFocus(): void {
    if (this.filteredOptions().length > 0 || this.query.length >= this.minChars()) {
      this.isOpen.set(true);
    }
  }

  onQueryChange(value: string): void {
    this.isOpen.set(true);
    this.highlightIndex.set(-1);
    this.queryChanged.emit(value);
  }

  onKeydown(event: KeyboardEvent): void {
    const opts = this.filteredOptions();
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.isOpen.set(true);
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
        if (this.highlightIndex() >= 0 && this.highlightIndex() < opts.length) {
          this.selectOption(opts[this.highlightIndex()]);
        }
        break;
      case 'Escape':
        this.isOpen.set(false);
        break;
    }
  }

  selectOption(option: AutocompleteOption): void {
    this.query = option.label;
    this.isOpen.set(false);
    this.highlightIndex.set(-1);
    this.selected.emit(option);
  }

  private scrollToHighlighted(): void {
    setTimeout(() => {
      const dropdown = this.inputEl()?.nativeElement
        .closest('.autocomplete-wrapper')
        ?.querySelector('.autocomplete-dropdown');
      const highlighted = dropdown?.querySelector('.highlighted');
      if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
      }
    });
  }
}
