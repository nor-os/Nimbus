/**
 * Overview: Component catalog — browsable list of typed Pulumi scripts with filters, search, and provider grouping.
 * Architecture: Feature component for component browsing (Section 11)
 * Dependencies: @angular/core, @angular/router, ComponentService, SemanticService, LayoutComponent
 * Concepts: Mode-aware catalog — provider mode shows shared components (tenant_id=null),
 *     tenant mode shows published provider components + tenant's own. Groups by provider with filter support.
 */
import { Component as NgComponent, OnInit, inject, signal, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ComponentService } from '@core/services/component.service';
import { SemanticService } from '@core/services/semantic.service';
import { Component as ComponentModel } from '@shared/models/component.model';

interface ProviderGroup {
  providerName: string;
  components: ComponentModel[];
}

@NgComponent({
  selector: 'nimbus-component-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div class="header-left">
            <h1>{{ isProviderMode() ? 'Provider Components' : 'Components' }}</h1>
            <span class="subtitle">{{
              isProviderMode()
                ? 'Define and publish shared components for all tenants'
                : 'Browse and use provider components, or define your own'
            }}</span>
          </div>
          <div class="header-right">
            <button
              *nimbusHasPermission="'component:definition:create'"
              class="btn btn-primary"
              (click)="router.navigate([basePath() + '/new'])"
            >+ New Component</button>
          </div>
        </div>

        <!-- Filters -->
        <div class="filter-bar">
          <input
            type="text"
            class="search-input"
            placeholder="Search components..."
            [ngModel]="searchQuery()"
            (ngModelChange)="searchQuery.set($event); loadComponents()"
          />
          <select class="filter-select" [ngModel]="providerFilter()" (ngModelChange)="providerFilter.set($event)">
            <option value="">All Providers</option>
            @for (p of providerNames(); track p) {
              <option [value]="p">{{ p }}</option>
            }
          </select>
          <select class="filter-select" [ngModel]="statusFilter()" (ngModelChange)="statusFilter.set($event)">
            <option value="">All Statuses</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
          </select>
        </div>

        <!-- Component Grid grouped by provider -->
        @if (loading()) {
          <div class="loading-state">Loading components...</div>
        } @else if (groupedComponents().length === 0) {
          <div class="empty-state">
            <div class="empty-icon">&#9783;</div>
            <div class="empty-title">No components found</div>
            <div class="empty-text">{{
              isProviderMode()
                ? 'Create a provider-level component to share with all tenants.'
                : 'Create a component or browse published provider components.'
            }}</div>
          </div>
        } @else {
          @for (group of groupedComponents(); track group.providerName) {
            <div class="provider-group">
              <div class="provider-group-header">
                <span class="provider-icon">&#9878;</span>
                <span class="provider-label">{{ group.providerName }}</span>
                <span class="provider-count">{{ group.components.length }}</span>
              </div>
              <div class="component-grid">
                @for (comp of group.components; track comp.id) {
                  <div class="component-card" (click)="openComponent(comp)">
                    <div class="card-header">
                      <span class="card-language" [class]="'lang-' + comp.language">{{ comp.language }}</span>
                      <div class="card-badges">
                        @if (!isProviderMode() && !comp.tenantId) {
                          <span class="card-scope scope-provider">Provider</span>
                        }
                        <span class="card-status" [class.published]="comp.isPublished" [class.draft]="!comp.isPublished">
                          {{ comp.isPublished ? 'Published' : 'Draft' }}
                        </span>
                      </div>
                    </div>
                    <h3 class="card-title">{{ comp.displayName }}</h3>
                    <p class="card-description">{{ comp.description || 'No description' }}</p>
                    <div class="card-meta">
                      <span class="meta-item" title="Semantic Type">{{ comp.semanticTypeName || 'Unknown' }}</span>
                      <span class="meta-sep">&middot;</span>
                      <span class="meta-item">v{{ comp.version }}</span>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .header-left h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .subtitle { font-size: 0.875rem; color: #64748b; }
    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: none; font-weight: 500; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }

    .filter-bar {
      display: flex; gap: 0.75rem; margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }
    .search-input {
      flex: 1; min-width: 200px; padding: 0.5rem 0.75rem;
      border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem;
      background: #fff; color: #1e293b;
    }
    .search-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; background: #fff; color: #1e293b; min-width: 140px;
    }

    .loading-state, .empty-state {
      text-align: center; padding: 3rem; color: #64748b;
    }
    .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
    .empty-title { font-size: 1.125rem; font-weight: 600; color: #1e293b; margin-bottom: 0.5rem; }
    .empty-text { font-size: 0.875rem; }

    /* ── Provider groups ──────────────────────── */
    .provider-group { margin-bottom: 1.5rem; }
    .provider-group-header {
      display: flex; align-items: center; gap: 0.5rem;
      margin-bottom: 0.75rem; padding-bottom: 0.5rem;
      border-bottom: 1px solid #e2e8f0;
    }
    .provider-icon { font-size: 1rem; color: #3b82f6; }
    .provider-label { font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
    .provider-count {
      background: #f1f5f9; color: #64748b; padding: 1px 8px; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 600;
    }

    .component-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }
    .component-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s;
    }
    .component-card:hover {
      border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59,130,246,0.08);
    }
    .card-header { display: flex; justify-content: space-between; margin-bottom: 0.75rem; }
    .card-badges { display: flex; gap: 0.375rem; }
    .card-language {
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      padding: 0.125rem 0.5rem; border-radius: 4px;
    }
    .lang-typescript { background: #eff6ff; color: #2563eb; }
    .lang-python { background: #fef3c7; color: #92400e; }
    .card-status {
      font-size: 0.6875rem; font-weight: 500; padding: 0.125rem 0.5rem; border-radius: 4px;
    }
    .card-status.published { background: #dcfce7; color: #166534; }
    .card-status.draft { background: #f1f5f9; color: #64748b; }
    .card-scope { font-size: 0.6875rem; font-weight: 500; padding: 0.125rem 0.5rem; border-radius: 4px; }
    .scope-provider { background: #ede9fe; color: #6d28d9; }
    .card-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 0.5rem; }
    .card-description {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 0.75rem;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .card-meta { display: flex; gap: 0.375rem; font-size: 0.75rem; color: #94a3b8; }
    .meta-sep { color: #cbd5e1; }
  `],
})
export class ComponentCatalogComponent implements OnInit {
  router = inject(Router);
  private route = inject(ActivatedRoute);
  private componentService = inject(ComponentService);
  private semanticService = inject(SemanticService);

  components = signal<ComponentModel[]>([]);
  loading = signal(false);
  searchQuery = signal('');
  providerFilter = signal('');
  statusFilter = signal('');

  isProviderMode = computed(() => this.route.snapshot.data['mode'] === 'provider');
  basePath = computed(() => this.isProviderMode() ? '/provider/components' : '/components');

  providerNames = computed(() => {
    const names = new Set<string>();
    for (const c of this.components()) {
      if (c.providerName) names.add(c.providerName);
    }
    return Array.from(names).sort();
  });

  filteredComponents = computed(() => {
    let items = this.components();
    const provider = this.providerFilter();
    const status = this.statusFilter();

    if (provider) {
      items = items.filter(c => c.providerName === provider);
    }
    if (status === 'published') {
      items = items.filter(c => c.isPublished);
    } else if (status === 'draft') {
      items = items.filter(c => !c.isPublished);
    }
    return items;
  });

  groupedComponents = computed((): ProviderGroup[] => {
    const items = this.filteredComponents();
    const groups = new Map<string, ComponentModel[]>();
    for (const c of items) {
      const name = c.providerName || 'Unknown';
      if (!groups.has(name)) groups.set(name, []);
      groups.get(name)!.push(c);
    }
    return Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([providerName, components]) => ({ providerName, components }));
  });

  ngOnInit(): void {
    this.loadComponents();
  }

  loadComponents(): void {
    this.loading.set(true);
    const search = this.searchQuery() || undefined;
    const providerMode = this.isProviderMode();
    this.componentService.listComponents({ search, providerMode }).subscribe({
      next: (items) => {
        this.components.set(items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openComponent(comp: ComponentModel): void {
    const isProviderComp = !comp.tenantId;
    const base = isProviderComp ? '/provider/components' : '/components';
    this.router.navigate([base, comp.id, 'edit']);
  }
}
