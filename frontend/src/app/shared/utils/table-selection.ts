/**
 * Overview: Signal-based table selection utility for checkbox-driven bulk operations.
 * Architecture: Shared utility for list component selection state (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Bulk selection, select-all, indeterminate state, pure signals
 */
import { Signal, signal, computed } from '@angular/core';

export interface TableSelection<T> {
  selectedIds: Signal<Set<string>>;
  allSelected: Signal<boolean>;
  someSelected: Signal<boolean>;
  selectedCount: Signal<number>;
  toggle: (id: string) => void;
  toggleAll: () => void;
  clear: () => void;
  isSelected: (id: string) => boolean;
}

export function createTableSelection<T>(
  items: Signal<T[]>,
  idFn: (item: T) => string,
): TableSelection<T> {
  const selectedIds = signal<Set<string>>(new Set());

  const selectedCount = computed(() => selectedIds().size);

  const allSelected = computed(() => {
    const ids = selectedIds();
    const all = items();
    return all.length > 0 && ids.size === all.length;
  });

  const someSelected = computed(() => {
    const count = selectedIds().size;
    return count > 0 && count < items().length;
  });

  function toggle(id: string): void {
    selectedIds.update((set) => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleAll(): void {
    if (allSelected()) {
      selectedIds.set(new Set());
    } else {
      selectedIds.set(new Set(items().map(idFn)));
    }
  }

  function clear(): void {
    selectedIds.set(new Set());
  }

  function isSelected(id: string): boolean {
    return selectedIds().has(id);
  }

  return { selectedIds, allSelected, someSelected, selectedCount, toggle, toggleAll, clear, isSelected };
}
