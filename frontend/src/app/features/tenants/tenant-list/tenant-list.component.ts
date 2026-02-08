/**
 * Overview: Tenant list page with hierarchical tree display, search filtering, and CRUD actions.
 * Architecture: Feature component for tenant management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/tenant.service
 * Concepts: Multi-tenancy, tenant hierarchy, tree display, collapsible nodes, CRUD operations
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TenantService } from '@core/services/tenant.service';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { IconComponent } from '@shared/components/icon/icon.component';

interface TreeTenant extends Tenant {
  hasChildren: boolean;
}

@Component({
  selector: 'nimbus-tenant-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, IconComponent],
  template: `
    <nimbus-layout>
      <div class="tenant-list-page">
        <div class="page-header">
          <h1>Tenants</h1>
          <a routerLink="/tenants/create" class="btn btn-primary">Create Tenant</a>
        </div>

        <div class="filters">
          <input
            type="text"
            [(ngModel)]="searchTerm"
            (ngModelChange)="filterTenants()"
            placeholder="Search tenants..."
            class="search-input"
          />
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Level</th>
                <th>Contact</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (tenant of displayedTenants(); track tenant.id) {
                <tr [class.row-root]="tenant.is_root">
                  <td>
                    <div class="name-cell" [style.padding-left.rem]="tenant.level * 1.25">
                      @if (tenant.hasChildren) {
                        <button
                          class="tree-toggle"
                          (click)="toggleExpand(tenant.id)"
                          [attr.aria-expanded]="isExpanded(tenant.id)"
                          [title]="isExpanded(tenant.id) ? 'Collapse' : 'Expand'"
                        >
                          <span class="tree-chevron" [class.expanded]="isExpanded(tenant.id)">&#9654;</span>
                        </button>
                      } @else {
                        <span class="tree-spacer"></span>
                      }
                      @if (tenant.level > 0) {
                        <span class="tree-connector">&#9492;</span>
                      }
                      <a [routerLink]="['/tenants', tenant.id]" class="tenant-name" [class.tenant-root]="tenant.is_root">
                        {{ tenant.name }}
                      </a>
                    </div>
                  </td>
                  <td>
                    <span class="badge" [class]="'level-' + tenant.level">
                      {{ getLevelLabel(tenant.level) }}
                    </span>
                  </td>
                  <td class="contact-cell">{{ tenant.contact_email || '\u2014' }}</td>
                  <td class="date-cell">{{ tenant.created_at | date: 'mediumDate' }}</td>
                  <td class="actions">
                    <a [routerLink]="['/tenants', tenant.id]" class="icon-btn" title="View">
                      <nimbus-icon name="eye" />
                    </a>
                    <a [routerLink]="['/tenants', tenant.id, 'settings']" class="icon-btn" title="Settings">
                      <nimbus-icon name="gear" />
                    </a>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="empty-state">No tenants found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .tenant-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; border-radius: 6px; text-decoration: none; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .filters { margin-bottom: 1rem; }
    .search-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 300px; font-size: 0.8125rem; background: #fff; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th { font-weight: 600; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .table tbody tr:hover { background: #f8fafc; }
    .row-root { background: #fafbff; }
    .row-root:hover { background: #f0f4ff; }
    .name-cell {
      display: flex; align-items: center; gap: 0.25rem;
    }
    .tree-toggle {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1.25rem; height: 1.25rem; border: none; background: none;
      cursor: pointer; padding: 0; flex-shrink: 0; border-radius: 3px;
      transition: background 0.15s;
    }
    .tree-toggle:hover { background: #e2e8f0; }
    .tree-chevron {
      font-size: 0.5rem; color: #64748b; display: inline-block;
      transition: transform 0.15s;
    }
    .tree-chevron.expanded { transform: rotate(90deg); }
    .tree-spacer { display: inline-block; width: 1.25rem; flex-shrink: 0; }
    .tree-connector {
      color: #cbd5e1; font-size: 0.75rem; margin-right: 0.125rem; flex-shrink: 0;
    }
    .tenant-name {
      color: #1e293b; text-decoration: none; font-weight: 500;
      transition: color 0.15s;
    }
    .tenant-name:hover { color: #3b82f6; }
    .tenant-root { font-weight: 700; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .level-0 { background: #dbeafe; color: #1d4ed8; }
    .level-1 { background: #f3e8ff; color: #7c3aed; }
    .level-2 { background: #dcfce7; color: #16a34a; }
    .contact-cell { color: #64748b; }
    .date-cell { color: #64748b; }
    .actions { display: flex; gap: 0.25rem; align-items: center; }
    .icon-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border: none; background: none; border-radius: 4px;
      color: #64748b; cursor: pointer; transition: background 0.15s, color 0.15s;
      text-decoration: none;
    }
    .icon-btn:hover { background: #f1f5f9; color: #3b82f6; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class TenantListComponent implements OnInit {
  private tenantService = inject(TenantService);

  allTenants = signal<Tenant[]>([]);
  searchTerm = '';

  private expandedIds = signal<Set<string>>(new Set());

  displayedTenants = computed(() => {
    const all = this.allTenants();
    const term = this.searchTerm.toLowerCase().trim();

    // When searching, show flat filtered results
    if (term) {
      return this.toTreeTenants(
        all.filter(
          (t) =>
            t.name.toLowerCase().includes(term) ||
            (t.contact_email?.toLowerCase().includes(term) ?? false),
        ),
      );
    }

    // Build tree-ordered list with expand/collapse
    const expanded = this.expandedIds();
    const childMap = new Map<string | null, Tenant[]>();
    for (const t of all) {
      const key = t.parent_id ?? '__root__';
      if (!childMap.has(key)) childMap.set(key, []);
      childMap.get(key)!.push(t);
    }

    // Sort children alphabetically at each level
    for (const children of childMap.values()) {
      children.sort((a, b) => a.name.localeCompare(b.name));
    }

    const result: TreeTenant[] = [];
    const walk = (parentId: string | null) => {
      const key = parentId ?? '__root__';
      const children = childMap.get(key) ?? [];
      for (const child of children) {
        const hasChildren = childMap.has(child.id) && (childMap.get(child.id)!.length > 0);
        result.push({ ...child, hasChildren });
        if (hasChildren && expanded.has(child.id)) {
          walk(child.id);
        }
      }
    };
    walk(null);
    return result;
  });

  ngOnInit(): void {
    this.loadTenants();
  }

  loadTenants(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (tenants) => {
        this.allTenants.set(tenants);
        // Auto-expand all parents on first load
        const parentIds = new Set<string>();
        for (const t of tenants) {
          if (t.parent_id) parentIds.add(t.parent_id);
        }
        this.expandedIds.set(parentIds);
      },
    });
  }

  filterTenants(): void {
    // Triggers recomputation via displayedTenants computed
    this.allTenants.update((t) => [...t]);
  }

  toggleExpand(id: string): void {
    this.expandedIds.update((set) => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  isExpanded(id: string): boolean {
    return this.expandedIds().has(id);
  }

  getLevelLabel(level: number): string {
    return ['Provider', 'Tenant', 'Sub-tenant'][level] ?? `Level ${level}`;
  }

  private toTreeTenants(tenants: Tenant[]): TreeTenant[] {
    const allIds = new Set(this.allTenants().map((t) => t.id));
    return tenants.map((t) => ({
      ...t,
      hasChildren: this.allTenants().some((c) => c.parent_id === t.id),
    }));
  }
}
