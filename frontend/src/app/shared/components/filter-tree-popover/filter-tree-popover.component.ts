/**
 * Overview: Generic tree popover with tri-state checkboxes for hierarchical filtering.
 * Architecture: Reusable shared component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Tri-state checkboxes, tree filtering, popover positioning
 */
import {
  Component,
  ElementRef,
  HostListener,
  input,
  output,
  signal,
  computed,
  effect,
  viewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface TreeNode {
  key: string;
  label: string;
  children?: TreeNode[];
}

type CheckState = 'checked' | 'unchecked' | 'indeterminate';

@Component({
  selector: 'nimbus-filter-tree-popover',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="popover-anchor">
      <button
        class="trigger-btn"
        [class.has-selection]="selected().length > 0"
        (click)="toggle()"
      >
        {{ label() }}
        @if (selected().length > 0) {
          <span class="count-badge">{{ selected().length }}</span>
        }
        <span class="chevron" [class.open]="isOpen()">&#9662;</span>
      </button>

      @if (isOpen()) {
        <div class="popover-panel" #panel>
          <div class="search-box">
            <input
              type="text"
              [(ngModel)]="searchQuery"
              (ngModelChange)="onSearchChange()"
              placeholder="Search..."
              class="search-input"
              #searchInput
            />
          </div>
          <div class="tree-scroll">
            @for (node of filteredItems(); track node.key) {
              <div class="tree-parent">
                <label class="tree-label parent-label" (click)="toggleParent(node); $event.preventDefault()">
                  <span class="checkbox-wrap">
                    <input
                      type="checkbox"
                      [checked]="getParentState(node) === 'checked'"
                      [indeterminate]="getParentState(node) === 'indeterminate'"
                      (click)="$event.preventDefault()"
                    />
                  </span>
                  <span class="label-text">{{ node.label }}</span>
                </label>
                @if (node.children && node.children.length > 0) {
                  @for (child of node.children; track child.key) {
                    <label class="tree-label child-label" (click)="toggleLeaf(child.key); $event.preventDefault()">
                      <span class="checkbox-wrap">
                        <input
                          type="checkbox"
                          [checked]="isSelected(child.key)"
                          (click)="$event.preventDefault()"
                        />
                      </span>
                      <span class="label-text">{{ child.label }}</span>
                    </label>
                  }
                }
              </div>
            } @empty {
              <div class="empty-state">No matching items</div>
            }
          </div>
          <div class="popover-footer">
            <button class="footer-btn" (click)="clearAll()">Clear</button>
            <button class="footer-btn primary" (click)="close()">Done</button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .popover-anchor { position: relative; display: inline-block; }
    .trigger-btn {
      display: flex; align-items: center; gap: 0.375rem;
      padding: 0.375rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 6px;
      background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; color: #475569; transition: border-color 0.15s;
    }
    .trigger-btn:hover { border-color: #cbd5e1; }
    .trigger-btn.has-selection { border-color: #3b82f6; background: #eff6ff; color: #1d4ed8; }
    .count-badge {
      background: #3b82f6; color: #fff; border-radius: 999px;
      padding: 0 0.375rem; font-size: 0.6875rem; font-weight: 600;
      min-width: 1.125rem; text-align: center; line-height: 1.25rem;
    }
    .chevron { font-size: 0.625rem; transition: transform 0.15s; color: #94a3b8; }
    .chevron.open { transform: rotate(180deg); }
    .popover-panel {
      position: absolute; top: calc(100% + 4px); left: 0; z-index: 50;
      width: 280px; max-height: 400px; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12); display: flex; flex-direction: column;
    }
    .search-box { padding: 0.5rem; border-bottom: 1px solid #f1f5f9; }
    .search-input {
      width: 100%; box-sizing: border-box; padding: 0.375rem 0.5rem;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .tree-scroll {
      flex: 1; overflow-y: auto; padding: 0.25rem 0;
      max-height: 280px;
    }
    .tree-parent { padding: 0; }
    .tree-label {
      display: flex; align-items: center; gap: 0.375rem;
      padding: 0.25rem 0.5rem; cursor: pointer; user-select: none;
      font-size: 0.8125rem; color: #334155;
    }
    .tree-label:hover { background: #f8fafc; }
    .parent-label { font-weight: 600; color: #1e293b; padding-top: 0.375rem; }
    .child-label { padding-left: 1.5rem; font-weight: 400; }
    .checkbox-wrap { display: flex; align-items: center; }
    .checkbox-wrap input[type="checkbox"] { cursor: pointer; accent-color: #3b82f6; }
    .label-text { flex: 1; }
    .empty-state { padding: 1rem; text-align: center; color: #94a3b8; font-size: 0.8125rem; }
    .popover-footer {
      display: flex; justify-content: space-between; padding: 0.5rem;
      border-top: 1px solid #f1f5f9;
    }
    .footer-btn {
      padding: 0.25rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px;
      background: #fff; cursor: pointer; font-size: 0.75rem; font-family: inherit;
      color: #475569;
    }
    .footer-btn:hover { background: #f8fafc; }
    .footer-btn.primary { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .footer-btn.primary:hover { background: #2563eb; }
  `],
})
export class FilterTreePopoverComponent {
  items = input<TreeNode[]>([]);
  selected = input<string[]>([]);
  label = input<string>('Filter');

  selectionChange = output<string[]>();

  isOpen = signal(false);
  searchQuery = '';

  private selectedSet = signal<Set<string>>(new Set());

  panel = viewChild<ElementRef>('panel');

  constructor(private elRef: ElementRef) {
    effect(() => {
      this.selectedSet.set(new Set(this.selected()));
    }, { allowSignalWrites: true });
  }

  filteredItems = computed(() => {
    const q = this.searchQuery.toLowerCase().trim();
    if (!q) return this.items();
    return this.items()
      .map((parent): TreeNode | null => {
        const children = parent.children?.filter(c =>
          c.label.toLowerCase().includes(q) || c.key.toLowerCase().includes(q)
        ) ?? [];
        const parentMatch = parent.label.toLowerCase().includes(q);
        if (parentMatch || children.length > 0) {
          return { ...parent, children: parentMatch ? parent.children : children } as TreeNode;
        }
        return null;
      })
      .filter((n): n is TreeNode => n !== null);
  });

  toggle(): void {
    this.isOpen.update(v => !v);
    if (this.isOpen()) {
      this.searchQuery = '';
    }
  }

  close(): void {
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (this.isOpen() && !this.elRef.nativeElement.contains(event.target)) {
      this.close();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen()) this.close();
  }

  onSearchChange(): void {
    // search is reactive via computed
  }

  isSelected(key: string): boolean {
    return this.selectedSet().has(key);
  }

  getParentState(node: TreeNode): CheckState {
    const children = node.children ?? [];
    if (children.length === 0) {
      return this.isSelected(node.key) ? 'checked' : 'unchecked';
    }
    const selected = children.filter(c => this.selectedSet().has(c.key)).length;
    if (selected === 0) return 'unchecked';
    if (selected === children.length) return 'checked';
    return 'indeterminate';
  }

  toggleParent(node: TreeNode): void {
    const children = node.children ?? [];
    if (children.length === 0) {
      this.toggleLeaf(node.key);
      return;
    }
    const state = this.getParentState(node);
    const newSet = new Set(this.selectedSet());
    if (state === 'checked') {
      children.forEach(c => newSet.delete(c.key));
    } else {
      children.forEach(c => newSet.add(c.key));
    }
    this.selectedSet.set(newSet);
    this.emitSelection();
  }

  toggleLeaf(key: string): void {
    const newSet = new Set(this.selectedSet());
    if (newSet.has(key)) {
      newSet.delete(key);
    } else {
      newSet.add(key);
    }
    this.selectedSet.set(newSet);
    this.emitSelection();
  }

  clearAll(): void {
    this.selectedSet.set(new Set());
    this.emitSelection();
  }

  private emitSelection(): void {
    this.selectionChange.emit([...this.selectedSet()]);
  }
}
