/**
 * Overview: Horizontal chip bar showing active filters with remove and clear-all actions.
 * Architecture: Reusable shared component (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Filter chips, active filters display
 */
import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ActiveFilter {
  key: string;
  label: string;
  value: string;
  displayValue: string;
}

@Component({
  selector: 'nimbus-active-filters-bar',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (filters().length > 0) {
      <div class="filters-bar">
        <span class="bar-label">Filters:</span>
        @for (filter of filters(); track filter.key + ':' + filter.value) {
          <span class="filter-chip">
            <span class="chip-label">{{ filter.label }}:</span>
            <span class="chip-value">{{ filter.displayValue }}</span>
            <button class="chip-remove" (click)="removeFilter.emit(filter)">&times;</button>
          </span>
        }
        <button class="clear-btn" (click)="clearAll.emit()">Clear all</button>
      </div>
    }
  `,
  styles: [`
    .filters-bar {
      display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem;
      padding: 0.5rem 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .bar-label {
      font-size: 0.75rem; color: #64748b; font-weight: 500; margin-right: 0.25rem;
    }
    .filter-chip {
      display: inline-flex; align-items: center; gap: 0.25rem;
      padding: 0.1875rem 0.5rem; background: #eff6ff; border: 1px solid #bfdbfe;
      border-radius: 999px; font-size: 0.6875rem;
    }
    .chip-label { color: #64748b; font-weight: 500; }
    .chip-value { color: #1d4ed8; font-weight: 600; }
    .chip-remove {
      background: none; border: none; cursor: pointer; font-size: 0.875rem;
      color: #94a3b8; padding: 0 0.125rem; line-height: 1;
      font-family: inherit;
    }
    .chip-remove:hover { color: #dc2626; }
    .clear-btn {
      background: none; border: none; cursor: pointer; font-size: 0.6875rem;
      color: #64748b; font-family: inherit; padding: 0.1875rem 0.375rem;
      border-radius: 4px;
    }
    .clear-btn:hover { color: #dc2626; background: #fef2f2; }
  `],
})
export class ActiveFiltersBarComponent {
  filters = input<ActiveFilter[]>([]);
  removeFilter = output<ActiveFilter>();
  clearAll = output<void>();
}
