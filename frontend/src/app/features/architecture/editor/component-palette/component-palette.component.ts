/**
 * Overview: Component palette — semantic types grouped by category with search and click-to-add.
 * Architecture: Left sidebar panel for architecture editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Semantic resource types as palette items, category grouping, search filter, light theme
 */
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SemanticResourceType } from '@shared/models/semantic.model';
import { ServiceCluster } from '@shared/models/cluster.model';
import { iconNameToSymbol } from '@shared/utils/icon-map';

@Component({
  selector: 'nimbus-component-palette',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="component-palette">
      <div class="palette-header">
        <h3>Palette</h3>
        <input
          type="text"
          class="palette-search"
          placeholder="Search..."
          [ngModel]="searchQuery()"
          (ngModelChange)="searchQuery.set($event)"
        />
      </div>
      <div class="palette-categories">
        <!-- Compartments section -->
        <div class="category">
          <button class="category-header section-compartments" (click)="toggleCategory('__compartments__')">
            <span class="category-chevron" [class.expanded]="isCategoryExpanded('__compartments__')">&#9206;</span>
            <span>Compartments</span>
          </button>
          @if (isCategoryExpanded('__compartments__')) {
            <button class="palette-item" (click)="addCompartment.emit()" title="Add a container region">
              <span class="item-icon">&#9633;</span>
              <span class="item-label">Custom Compartment</span>
            </button>
            @for (type of compartmentTypes(); track type.id) {
              <button
                class="palette-item"
                (click)="addCompartmentFromType.emit(type.id)"
                [title]="type.description || type.displayName"
              >
                <span class="item-icon">{{ resolveIcon(type.icon, '\u25A1') }}</span>
                <span class="item-label">{{ type.displayName }}</span>
              </button>
            }
          }
        </div>

        <!-- Stacks section -->
        @if (blueprints().length > 0) {
          <div class="category">
            <button class="category-header section-stacks" (click)="toggleCategory('__stacks__')">
              <span class="category-chevron" [class.expanded]="isCategoryExpanded('__stacks__')">&#9206;</span>
              <span>Stacks</span>
            </button>
            @if (isCategoryExpanded('__stacks__')) {
              @for (bp of filteredBlueprints(); track bp.id) {
                <button
                  class="palette-item"
                  (click)="addStack.emit(bp.id)"
                  [title]="bp.description || bp.name"
                >
                  <span class="item-icon">&#9881;</span>
                  <span class="item-label">{{ bp.name }}</span>
                </button>
              }
              @if (filteredBlueprints().length === 0) {
                <div class="empty-state">No blueprints match</div>
              }
            }
          </div>
        }

        <!-- Components section -->
        @for (cat of categories(); track cat) {
          <div class="category">
            <button class="category-header" (click)="toggleCategory(cat)">
              <span class="category-chevron" [class.expanded]="isCategoryExpanded(cat)">&#9206;</span>
              <span>{{ cat }}</span>
            </button>
            @if (isCategoryExpanded(cat)) {
              @for (type of getTypesForCategory(cat); track type.id) {
                <button
                  class="palette-item"
                  (click)="addComponent.emit(type.id)"
                  [title]="type.description || type.displayName"
                >
                  <span class="item-icon">{{ resolveIcon(type.icon, '\u25A3') }}</span>
                  <span class="item-label">{{ type.displayName }}</span>
                </button>
              }
            }
          </div>
        }
        @if (categories().length === 0 && filteredBlueprints().length === 0) {
          <div class="empty-state">No items match your search</div>
        }
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; flex-shrink: 0; width: 240px; height: 100%; }
    .component-palette {
      width: 100%;
      height: 100%;
      background: #fff;
      border-right: 1px solid #e2e8f0;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }
    .palette-header {
      padding: 12px;
      border-bottom: 1px solid #e2e8f0;
    }
    .palette-header h3 {
      margin: 0 0 8px;
      font-size: 0.875rem;
      font-weight: 600;
      color: #1e293b;
    }
    .palette-search {
      width: 100%;
      padding: 6px 8px;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      color: #1e293b;
      font-size: 0.75rem;
      outline: none;
      font-family: inherit;
      box-sizing: border-box;
    }
    .palette-search:focus { border-color: #3b82f6; }
    .palette-categories { flex: 1; padding: 4px 0; }
    .category { margin-bottom: 2px; }
    .category-header {
      display: flex;
      align-items: center;
      gap: 6px;
      width: 100%;
      padding: 6px 12px;
      border: none;
      background: none;
      font-size: 0.6875rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #94a3b8;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
    }
    .category-header:hover { color: #64748b; }
    .category-chevron {
      font-size: 0.5rem;
      transition: transform 0.2s;
      transform: rotate(180deg);
    }
    .category-chevron.expanded { transform: rotate(0deg); }
    .palette-item {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 12px 6px 24px;
      border: none;
      background: none;
      color: #374151;
      font-size: 0.8125rem;
      cursor: pointer;
      text-align: left;
      transition: background 0.15s;
      font-family: inherit;
    }
    .palette-item:hover { background: #f8fafc; color: #1e293b; }
    .item-icon { font-size: 0.875rem; width: 18px; height: 18px; line-height: 18px; text-align: center; flex-shrink: 0; overflow: hidden; }
    .item-label {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .empty-state {
      padding: 24px 12px;
      text-align: center;
      font-size: 0.75rem;
      color: #94a3b8;
    }
    .section-compartments { color: #2563eb; }
    .section-stacks { color: #7c3aed; }
  `],
})
export class ComponentPaletteComponent {
  private _types = signal<SemanticResourceType[]>([]);
  private _blueprints = signal<ServiceCluster[]>([]);
  private expandedCategories = signal<Set<string>>(new Set());

  @Input() set semanticTypes(value: SemanticResourceType[]) {
    this._types.set(value);
    // Auto-expand all categories + built-in sections
    const cats = new Set(value.map(t => (t as any).category?.displayName || 'Uncategorized'));
    cats.add('__compartments__');
    cats.add('__stacks__');
    this.expandedCategories.set(cats);
  }

  @Input() set availableBlueprints(value: ServiceCluster[]) {
    this._blueprints.set(value || []);
  }

  @Output() addComponent = new EventEmitter<string>();
  @Output() addCompartment = new EventEmitter<void>();
  @Output() addCompartmentFromType = new EventEmitter<string>();
  @Output() addStack = new EventEmitter<string>();

  searchQuery = signal('');

  blueprints = computed(() => this._blueprints());

  compartmentTypes = computed(() => {
    const q = this.searchQuery().toLowerCase();
    // Semantic types that support containment (e.g., VPC, Subnet, Resource Group)
    const containment = this._types().filter(
      t => !t.isAbstract && (t as any).supportsContainment,
    );
    if (!q) return containment;
    return containment.filter(
      t => t.displayName.toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q),
    );
  });

  filteredBlueprints = computed(() => {
    const q = this.searchQuery().toLowerCase();
    const bps = this._blueprints();
    if (!q) return bps;
    return bps.filter(
      bp => bp.name.toLowerCase().includes(q) || (bp.description || '').toLowerCase().includes(q),
    );
  });

  filteredTypes = computed(() => {
    const q = this.searchQuery().toLowerCase();
    const types = this._types().filter(t => !t.isAbstract);
    if (!q) return types;
    return types.filter(
      t =>
        t.displayName.toLowerCase().includes(q) ||
        (t.description || '').toLowerCase().includes(q),
    );
  });

  categories = computed(() => {
    const types = this.filteredTypes();
    const cats = new Set(types.map(t => (t as any).category?.displayName || 'Uncategorized'));
    return Array.from(cats).sort();
  });

  getTypesForCategory(category: string): SemanticResourceType[] {
    return this.filteredTypes().filter(
      t => ((t as any).category?.displayName || 'Uncategorized') === category,
    );
  }

  toggleCategory(cat: string): void {
    const current = this.expandedCategories();
    const next = new Set(current);
    if (next.has(cat)) {
      next.delete(cat);
    } else {
      next.add(cat);
    }
    this.expandedCategories.set(next);
  }

  isCategoryExpanded(cat: string): boolean {
    return this.expandedCategories().has(cat);
  }

  resolveIcon(icon: string | null | undefined, fallback: string): string {
    return iconNameToSymbol(icon) || fallback;
  }
}
