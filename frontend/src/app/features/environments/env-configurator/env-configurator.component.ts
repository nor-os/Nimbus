/**
 * Overview: Guided environment configurator — tile-based option catalog with detail panels, category filtering, and advanced mode toggle.
 * Architecture: Feature component for guided environment configuration (Section 7.2)
 * Dependencies: @angular/core, @angular/common, landing-zone.service, toast.service, SchemaFormRendererComponent
 * Concepts: Options displayed as selectable tiles grouped by category. Conflict/prerequisite handling with auto-deselect.
 *   Advanced mode toggles to raw JSON Schema form. Selected options' config_values are deep-merged and emitted.
 *   Detail panel pins on click and stays visible until another tile is clicked or explicitly dismissed.
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  OnChanges,
  SimpleChanges,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { inject } from '@angular/core';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { ToastService } from '@shared/services/toast.service';
import { SchemaFormRendererComponent } from '@shared/components/schema-form/schema-form-renderer.component';
import { ConfigOption, ConfigOptionCategory } from '@shared/models/env-config-option.model';

@Component({
  selector: 'nimbus-env-configurator',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, SchemaFormRendererComponent],
  template: `
    <div class="configurator">
      <!-- Mode toggle + filter -->
      <div class="toolbar">
        <div class="mode-toggle">
          <button
            class="toggle-btn"
            [class.active]="!advancedMode()"
            (click)="advancedMode.set(false)"
          >Guided</button>
          <button
            class="toggle-btn"
            [class.active]="advancedMode()"
            (click)="advancedMode.set(true)"
          >Advanced</button>
        </div>
        @if (!advancedMode()) {
          <div class="filter-box">
            <input
              type="text"
              class="filter-input"
              placeholder="Filter options..."
              [ngModel]="filterText()"
              (ngModelChange)="filterText.set($event)"
            />
          </div>
        }
      </div>

      @if (advancedMode()) {
        <!-- Advanced: raw schema form -->
        @if (schema) {
          <nimbus-schema-form-renderer
            [schema]="schema"
            [values]="currentValues"
            (valuesChange)="onAdvancedValuesChange($event)"
          />
        } @else {
          <p class="empty-hint">No schema available for this domain.</p>
        }
      } @else {
        <!-- Category pills -->
        @if (categories().length > 1) {
          <div class="category-pills">
            <button
              class="pill"
              [class.active]="activeCategory() === ''"
              (click)="activeCategory.set('')"
            >All</button>
            @for (cat of categories(); track cat.name) {
              <button
                class="pill"
                [class.active]="activeCategory() === cat.name"
                (click)="activeCategory.set(cat.name)"
              >{{ cat.displayName }}</button>
            }
          </div>
        }

        <!-- Tile grid grouped by category -->
        @for (group of groupedOptions(); track group.category) {
          <div class="category-group">
            <h3 class="category-title">{{ group.displayName }}</h3>
            <div class="tile-grid">
              @for (opt of group.options; track opt.id) {
                <div
                  class="tile"
                  [class.selected]="isSelected(opt.id)"
                  [class.conflicted]="isConflicted(opt.id)"
                  [class.focused]="focusedOption()?.id === opt.id"
                  (click)="onTileClick(opt, $event)"
                  tabindex="0"
                  (keydown.enter)="toggleOption(opt)"
                  (keydown.space)="onTileClick(opt, $event)"
                >
                  <div class="tile-header">
                    <span class="tile-icon">{{ getIconChar(opt.icon) }}</span>
                    @if (isSelected(opt.id)) {
                      <span class="check-mark">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                          <circle cx="8" cy="8" r="7" fill="#3b82f6"/>
                          <path d="M5 8l2 2 4-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </span>
                    }
                  </div>
                  <div class="tile-name">{{ opt.displayName }}</div>
                  <div class="tile-desc">{{ opt.description }}</div>
                  @if (opt.tags.length > 0) {
                    <div class="tile-tags">
                      @for (tag of opt.tags; track tag) {
                        <span class="tag" [class]="'tag-' + tag">{{ tag }}</span>
                      }
                    </div>
                  }
                </div>
              }
            </div>

            <!-- Inline detail panel for focused option in this category -->
            @if (focusedOption() && focusedOptionCategory() === group.category) {
              <div class="detail-panel" (click)="$event.stopPropagation()">
                <div class="detail-header">
                  <span class="detail-icon">{{ getIconChar(focusedOption()!.icon) }}</span>
                  <h3 class="detail-title">{{ focusedOption()!.displayName }}</h3>
                  @if (focusedOption()!.isDefault) {
                    <span class="tag tag-default">default</span>
                  }
                  <button class="detail-close" (click)="focusedOption.set(null)" title="Close">&times;</button>
                </div>
                <p class="detail-text">{{ focusedOption()!.detail }}</p>

                @if (focusedOption()!.implications.length > 0) {
                  <div class="detail-section">
                    <h4 class="detail-label">Implications</h4>
                    <ul class="implication-list">
                      @for (imp of focusedOption()!.implications; track imp) {
                        <li>{{ imp }}</li>
                      }
                    </ul>
                  </div>
                }

                @if (focusedOption()!.relatedResolverTypes.length > 0 || focusedOption()!.relatedComponentNames.length > 0) {
                  <div class="detail-section">
                    <h4 class="detail-label">Related</h4>
                    <div class="related-links">
                      @for (r of focusedOption()!.relatedResolverTypes; track r) {
                        <span class="related-chip resolver">{{ r }} resolver</span>
                      }
                      @for (c of focusedOption()!.relatedComponentNames; track c) {
                        <span class="related-chip component">{{ c }}</span>
                      }
                    </div>
                  </div>
                }

                @if (focusedOption()!.conflictsWith.length > 0) {
                  <div class="detail-section">
                    <h4 class="detail-label">Conflicts with</h4>
                    <div class="related-links">
                      @for (cId of focusedOption()!.conflictsWith; track cId) {
                        <span class="related-chip conflict">{{ getOptionName(cId) }}</span>
                      }
                    </div>
                  </div>
                }

                <div class="detail-actions">
                  <button
                    class="btn btn-sm"
                    [class.btn-primary]="!isSelected(focusedOption()!.id)"
                    [class.btn-outline]="isSelected(focusedOption()!.id)"
                    (click)="toggleOption(focusedOption()!)"
                  >{{ isSelected(focusedOption()!.id) ? 'Deselect' : 'Select' }}</button>
                </div>
              </div>
            }
          </div>
        }

        @if (options().length === 0 && !loadingOptions()) {
          <p class="empty-hint">No configuration options available for this provider and domain.</p>
        }
        @if (loadingOptions()) {
          <p class="empty-hint">Loading options...</p>
        }
      }
    </div>
  `,
  styles: [`
    .configurator { }

    /* Toolbar */
    .toolbar {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; gap: 12px;
    }
    .mode-toggle {
      display: flex; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;
    }
    .toggle-btn {
      padding: 6px 14px; font-size: 0.8125rem; font-weight: 500; border: none;
      background: #fff; color: #64748b; cursor: pointer; font-family: inherit;
      transition: background 0.15s, color 0.15s;
    }
    .toggle-btn.active {
      background: #3b82f6; color: #fff;
    }
    .toggle-btn:not(.active):hover { background: #f8fafc; color: #1e293b; }
    .filter-box { flex: 1; max-width: 240px; }
    .filter-input {
      width: 100%; padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; color: #1e293b; background: #fff; outline: none;
      font-family: inherit;
    }
    .filter-input:focus { border-color: #3b82f6; }
    .filter-input::placeholder { color: #94a3b8; }

    /* Category pills */
    .category-pills {
      display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px;
    }
    .pill {
      padding: 4px 12px; border-radius: 16px; font-size: 0.75rem; font-weight: 500;
      border: 1px solid #e2e8f0; background: #fff; color: #64748b; cursor: pointer;
      font-family: inherit; transition: all 0.15s;
    }
    .pill:hover { border-color: #3b82f6; color: #3b82f6; }
    .pill.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }

    /* Category groups */
    .category-group { margin-bottom: 20px; }
    .category-title {
      font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase;
      letter-spacing: 0.04em; margin: 0 0 10px; padding-bottom: 6px;
      border-bottom: 1px solid #f1f5f9;
    }

    /* Tile grid */
    .tile-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;
    }
    .tile {
      position: relative; padding: 14px; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer;
      transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
      display: flex; flex-direction: column; gap: 6px;
    }
    .tile:hover {
      border-color: #93c5fd; box-shadow: 0 1px 4px rgba(59, 130, 246, 0.08);
    }
    .tile:focus { outline: 2px solid #3b82f6; outline-offset: 2px; }
    .tile.selected {
      background: #eff6ff; border-color: #3b82f6;
    }
    .tile.focused {
      border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
    }
    .tile.conflicted {
      background: #fffbeb; border-color: #fbbf24; opacity: 0.65;
    }

    .tile-header {
      display: flex; justify-content: space-between; align-items: flex-start;
    }
    .tile-icon {
      font-size: 1.125rem; line-height: 1; color: #64748b;
    }
    .check-mark {
      flex-shrink: 0; line-height: 0;
    }

    .tile-name { font-size: 0.8125rem; font-weight: 600; color: #1e293b; }
    .tile-desc { font-size: 0.6875rem; color: #64748b; line-height: 1.4; }
    .tile-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 2px; }
    .tag {
      font-size: 0.5625rem; padding: 1px 6px; border-radius: 3px;
      text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em;
    }
    .tag-basic { background: #f1f5f9; color: #475569; }
    .tag-standard { background: #f0fdf4; color: #166534; }
    .tag-enterprise { background: #fefce8; color: #854d0e; }
    .tag-default { background: #eff6ff; color: #1d4ed8; }
    .tag-advanced { background: #faf5ff; color: #7c3aed; }

    /* Detail panel — inline below tile grid within category */
    .detail-panel {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 16px 20px; margin-top: 12px;
      animation: slideDown 0.15s ease-out;
    }
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .detail-header {
      display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
    }
    .detail-icon { font-size: 1.125rem; color: #64748b; }
    .detail-title { font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0; flex: 1; }
    .detail-close {
      background: none; border: none; font-size: 1.25rem; color: #94a3b8;
      cursor: pointer; padding: 0 4px; line-height: 1; font-family: inherit;
    }
    .detail-close:hover { color: #475569; }
    .detail-text { font-size: 0.8125rem; color: #374151; line-height: 1.5; margin: 0 0 12px; }
    .detail-section { margin-bottom: 10px; }
    .detail-label {
      font-size: 0.6875rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
    }
    .implication-list {
      margin: 0; padding: 0 0 0 16px; font-size: 0.8125rem; color: #374151;
      line-height: 1.6;
    }
    .related-links { display: flex; gap: 6px; flex-wrap: wrap; }
    .related-chip {
      font-size: 0.6875rem; padding: 2px 8px; border-radius: 4px; font-weight: 500;
    }
    .related-chip.resolver { background: #f1f5f9; color: #475569; }
    .related-chip.component { background: #f5f3ff; color: #6d28d9; }
    .related-chip.conflict { background: #fef2f2; color: #dc2626; }

    .detail-actions { margin-top: 12px; }

    /* Shared buttons */
    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
      cursor: pointer; border: none; display: inline-flex; align-items: center;
      font-family: inherit; transition: background 0.15s;
    }
    .btn-sm { padding: 6px 12px; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #64748b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { border-color: #94a3b8; color: #1e293b; }
    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 16px 0; }
  `],
})
export class EnvConfiguratorComponent implements OnChanges {
  @Input() domain = '';
  @Input() providerName = '';
  @Input() currentValues: Record<string, unknown> = {};
  @Input() schema: Record<string, unknown> | null = null;
  @Input() excludeCategories: string[] = [];
  @Input() catalogSource: 'env' | 'lz' = 'env';

  @Output() valuesChange = new EventEmitter<Record<string, unknown>>();

  private lzService = inject(LandingZoneService);
  private toast = inject(ToastService);

  /** State */
  advancedMode = signal(false);
  options = signal<ConfigOption[]>([]);
  categories = signal<ConfigOptionCategory[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  focusedOption = signal<ConfigOption | null>(null);
  activeCategory = signal('');
  filterText = signal('');
  loadingOptions = signal(false);

  /** Derived: category of the focused option (for inline placement) */
  focusedOptionCategory = computed(() => this.focusedOption()?.category ?? '');

  /** Monochrome icon map — simple text symbols, no colorful emoji */
  private iconMap: Record<string, string> = {
    globe: '\u25CE',         // ◎
    layers: '\u2261',        // ≡
    zap: '\u21AF',           // ↯
    square: '\u25A1',        // □
    cloud: '\u2601',         // ☁
    link: '\u2194',          // ↔
    'at-sign': '@',
    'shield-off': '\u25CB',  // ○
    shield: '\u25C6',        // ◆
    lock: '\u2302',          // ⌂
    filter: '\u25B7',        // ▷
    key: '\u2217',           // ∗
    user: '\u2206',          // ∆
    users: '\u2206',         // ∆
    database: '\u2395',      // ⎕
    cpu: '\u2699',           // ⚙
    box: '\u25A0',           // ■
    grid: '\u2637',          // ☷
    settings: '\u2699',      // ⚙
    sliders: '\u2630',       // ☰
    activity: '\u223F',      // ∿
    bell: '\u25B3',          // △
    'file-text': '\u2263',   // ≣
    eye: '\u25C9',           // ◉
    'dollar-sign': '$',
    'trending-up': '\u2197', // ↗
    'bar-chart-2': '\u2502', // │
    'map-pin': '\u25BD',     // ▽
    'arrow-up-right': '\u2197',
    'git-merge': '\u2325',   // ⌥
    'check-circle': '\u2713',// ✓
    'shield-check': '\u25C6',
    network: '\u25CE',       // ◎
    subnet: '\u2261',        // ≡
    firewall: '\u25C6',      // ◆
    monitor: '\u25C9',       // ◉
    'hard-drive': '\u2395',  // ⎕
    server: '\u2395',        // ⎕
    terminal: '\u2502',      // │
    wifi: '\u223F',          // ∿
    crosshair: '\u2295',     // ⊕
    folder: '\u25A1',        // □
    tag: '\u2302',           // ⌂
    hash: '#',
    percent: '%',
    alert: '\u25B3',         // △
    target: '\u25CE',        // ◎
  };

  /** Map option IDs to display names for conflict labels */
  private optionNameMap = new Map<string, string>();

  /** Filtered + grouped options for rendering */
  groupedOptions = computed(() => {
    const opts = this.options();
    const cat = this.activeCategory();
    const filter = this.filterText().toLowerCase();
    const excluded = this.excludeCategories;

    let filtered = opts;
    if (excluded.length > 0) {
      filtered = filtered.filter(o => !excluded.includes(o.category));
    }
    if (cat) {
      filtered = filtered.filter(o => o.category === cat);
    }
    if (filter) {
      filtered = filtered.filter(o =>
        o.displayName.toLowerCase().includes(filter) ||
        o.description.toLowerCase().includes(filter) ||
        o.tags.some(t => t.includes(filter))
      );
    }

    // Group by category
    const groups = new Map<string, { category: string; displayName: string; options: ConfigOption[] }>();
    const cats = this.categories();
    for (const o of filtered) {
      if (!groups.has(o.category)) {
        const catInfo = cats.find(c => c.name === o.category);
        groups.set(o.category, {
          category: o.category,
          displayName: catInfo?.displayName ?? o.category,
          options: [],
        });
      }
      groups.get(o.category)!.options.push(o);
    }
    return Array.from(groups.values());
  });

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['domain'] || changes['providerName'] || changes['catalogSource']) && this.domain && this.providerName) {
      this.loadCatalog();
    }
  }

  private loadCatalog(): void {
    this.loadingOptions.set(true);
    this.focusedOption.set(null);
    const optionsObs = this.catalogSource === 'lz'
      ? this.lzService.getLzConfigOptions(this.providerName, this.domain)
      : this.lzService.getEnvConfigOptions(this.providerName, this.domain);
    const categoriesObs = this.catalogSource === 'lz'
      ? this.lzService.getLzConfigCategories(this.providerName, this.domain)
      : this.lzService.getEnvConfigCategories(this.providerName, this.domain);
    optionsObs.subscribe({
      next: (opts) => {
        this.options.set(opts);
        this.optionNameMap.clear();
        for (const o of opts) {
          this.optionNameMap.set(o.id, o.displayName);
        }
        this.initSelections(opts);
        this.loadingOptions.set(false);
      },
      error: () => {
        this.loadingOptions.set(false);
      },
    });
    categoriesObs.subscribe({
      next: (cats) => this.categories.set(cats),
    });
  }

  private initSelections(opts: ConfigOption[]): void {
    const selected = new Set<string>();
    const hasValues = this.currentValues && Object.keys(this.currentValues).length > 0;

    if (hasValues) {
      for (const opt of opts) {
        if (this.optionMatchesValues(opt)) {
          selected.add(opt.id);
        }
      }
    }

    if (selected.size === 0) {
      for (const opt of opts) {
        if (opt.isDefault) {
          selected.add(opt.id);
        }
      }
    }
    this.selectedIds.set(selected);
  }

  private optionMatchesValues(opt: ConfigOption): boolean {
    for (const [key, val] of Object.entries(opt.configValues)) {
      if (this.currentValues[key] === undefined) return false;
      if (JSON.stringify(this.currentValues[key]) !== JSON.stringify(val)) return false;
    }
    return Object.keys(opt.configValues).length > 0;
  }

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
  }

  isConflicted(id: string): boolean {
    const selected = this.selectedIds();
    if (selected.has(id)) return false;
    const opt = this.options().find(o => o.id === id);
    if (!opt) return false;
    return opt.conflictsWith.some(cId => selected.has(cId));
  }

  /** Click on tile: toggle selection AND pin detail panel */
  onTileClick(opt: ConfigOption, event: Event): void {
    event.preventDefault();
    // Pin the detail panel to show this option's details
    if (this.focusedOption()?.id === opt.id) {
      // Clicking the already-focused tile: toggle selection only
      this.toggleOption(opt);
    } else {
      // Focus this tile to show its detail panel
      this.focusedOption.set(opt);
    }
  }

  toggleOption(opt: ConfigOption): void {
    const current = new Set(this.selectedIds());

    if (current.has(opt.id)) {
      current.delete(opt.id);
    } else {
      // Auto-deselect conflicting options
      for (const conflictId of opt.conflictsWith) {
        if (current.has(conflictId)) {
          const conflictOpt = this.options().find(o => o.id === conflictId);
          current.delete(conflictId);
          if (conflictOpt) {
            this.toast.info(`Deselected "${conflictOpt.displayName}" (conflicts with "${opt.displayName}")`);
          }
        }
      }

      // Auto-select prerequisites
      for (const reqId of opt.requires) {
        if (!current.has(reqId)) {
          current.add(reqId);
          const reqOpt = this.options().find(o => o.id === reqId);
          if (reqOpt) {
            this.toast.info(`Auto-selected "${reqOpt.displayName}" (required by "${opt.displayName}")`);
          }
        }
      }

      current.add(opt.id);
    }

    this.selectedIds.set(current);
    this.emitMergedValues(current);
  }

  private emitMergedValues(selected: Set<string>): void {
    const merged: Record<string, unknown> = {};
    const opts = this.options();

    for (const opt of opts) {
      if (selected.has(opt.id)) {
        this.deepMerge(merged, opt.configValues);
      }
    }

    this.valuesChange.emit(merged);
  }

  private deepMerge(target: Record<string, unknown>, source: Record<string, unknown>): void {
    for (const [key, val] of Object.entries(source)) {
      if (val && typeof val === 'object' && !Array.isArray(val) &&
          target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])) {
        this.deepMerge(target[key] as Record<string, unknown>, val as Record<string, unknown>);
      } else {
        target[key] = val;
      }
    }
  }

  onAdvancedValuesChange(values: Record<string, unknown>): void {
    this.valuesChange.emit(values);
  }

  getIconChar(icon: string): string {
    return this.iconMap[icon] ?? '\u25CF'; // ● as fallback
  }

  getOptionName(id: string): string {
    return this.optionNameMap.get(id) ?? id;
  }
}
