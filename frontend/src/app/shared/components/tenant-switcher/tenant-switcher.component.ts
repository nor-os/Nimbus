/**
 * Overview: Hierarchical tenant switcher with search, tree display, and click-outside close.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/tenant-context.service
 * Concepts: Multi-tenancy, tenant switching, hierarchical tree, search filtering
 */
import { Component, inject, signal, computed, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TenantContextService } from '@core/services/tenant-context.service';
import { UserTenantInfo } from '@core/models/tenant.model';

interface TenantNode {
  id: string;
  name: string;
  level: number;
  children: TenantNode[];
}

@Component({
  selector: 'nimbus-tenant-switcher',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="tenant-switcher">
      <button class="trigger" (click)="toggle()">
        <span class="trigger-name">{{ tenantContext.currentTenant()?.tenant_name ?? 'Select tenant' }}</span>
        <span class="trigger-chevron" [class.open]="open()">&#9662;</span>
      </button>

      @if (open()) {
        <div class="dropdown">
          <div class="search-box">
            <input
              #searchInput
              type="text"
              class="search-input"
              placeholder="Search tenants..."
              [(ngModel)]="searchQuery"
              (ngModelChange)="onSearchChange()"
              (keydown.escape)="close()"
            />
          </div>
          <div class="tree-list">
            @if (flatFiltered().length === 0) {
              <div class="empty">No tenants found</div>
            }
            @for (node of flatFiltered(); track node.id) {
              <button
                class="tree-item"
                [class.active]="node.id === tenantContext.currentTenantId()"
                [style.padding-left.px]="12 + node.level * 16"
                (click)="selectTenant(node.id)"
              >
                @if (node.children.length > 0) {
                  <span class="node-icon">&#9656;</span>
                } @else {
                  <span class="node-icon leaf">&#8226;</span>
                }
                <span class="node-name">{{ node.name }}</span>
              </button>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .tenant-switcher { position: relative; }
    .trigger {
      display: flex; align-items: center; gap: 0.375rem;
      padding: 0.25rem 0.5rem; border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 4px; font-size: 0.8125rem; background: rgba(255, 255, 255, 0.06);
      color: #e0e0e0; cursor: pointer; font-family: inherit; white-space: nowrap;
      transition: border-color 0.15s, background 0.15s;
    }
    .trigger:hover { background: rgba(255, 255, 255, 0.1); }
    .trigger-chevron {
      font-size: 0.625rem; transition: transform 0.15s; color: #94a3b8;
    }
    .trigger-chevron.open { transform: rotate(180deg); }
    .dropdown {
      position: absolute; top: calc(100% + 4px); right: 0; z-index: 300;
      width: 280px; max-height: 380px; background: #1e2530; border: 1px solid #334155;
      border-radius: 8px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      display: flex; flex-direction: column; overflow: hidden;
    }
    .search-box { padding: 0.5rem; border-bottom: 1px solid #334155; }
    .search-input {
      width: 100%; padding: 0.375rem 0.625rem; border: 1px solid #475569;
      border-radius: 4px; font-size: 0.8125rem; background: #0f172a;
      color: #e2e8f0; font-family: inherit; box-sizing: border-box; outline: none;
    }
    .search-input:focus { border-color: #3b82f6; }
    .search-input::placeholder { color: #64748b; }
    .tree-list { overflow-y: auto; max-height: 300px; padding: 0.25rem 0; }
    .tree-item {
      display: flex; align-items: center; gap: 0.375rem; width: 100%;
      padding: 0.4375rem 0.75rem; border: none; background: none;
      color: #cbd5e1; font-size: 0.8125rem; font-family: inherit;
      cursor: pointer; text-align: left; transition: background 0.1s;
    }
    .tree-item:hover { background: rgba(255, 255, 255, 0.06); }
    .tree-item.active { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .node-icon { font-size: 0.625rem; color: #64748b; width: 0.75rem; text-align: center; flex-shrink: 0; }
    .node-icon.leaf { font-size: 0.875rem; }
    .node-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .empty { padding: 1rem; text-align: center; color: #64748b; font-size: 0.8125rem; }
  `],
})
export class TenantSwitcherComponent {
  tenantContext = inject(TenantContextService);
  private elRef = inject(ElementRef);

  open = signal(false);
  searchQuery = '';
  private searchTerm = signal('');

  private tree = computed<TenantNode[]>(() => {
    return this.buildTree(this.tenantContext.accessibleTenants());
  });

  flatFiltered = computed<TenantNode[]>(() => {
    const term = this.searchTerm().toLowerCase();
    const nodes = this.flattenTree(this.tree());
    if (!term) return nodes;
    return nodes.filter((n) => n.name.toLowerCase().includes(term));
  });

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.open() && !this.elRef.nativeElement.contains(event.target)) {
      this.close();
    }
  }

  toggle(): void {
    if (this.open()) {
      this.close();
    } else {
      this.open.set(true);
      this.searchQuery = '';
      this.searchTerm.set('');
    }
  }

  close(): void {
    this.open.set(false);
  }

  onSearchChange(): void {
    this.searchTerm.set(this.searchQuery);
  }

  selectTenant(tenantId: string): void {
    this.close();
    if (tenantId !== this.tenantContext.currentTenantId()) {
      this.tenantContext.switchTenant(tenantId);
    }
  }

  private buildTree(tenants: UserTenantInfo[]): TenantNode[] {
    const map = new Map<string, TenantNode>();
    const roots: TenantNode[] = [];

    for (const t of tenants) {
      map.set(t.tenant_id, { id: t.tenant_id, name: t.tenant_name, level: t.level, children: [] });
    }

    for (const t of tenants) {
      const node = map.get(t.tenant_id)!;
      if (t.parent_id && map.has(t.parent_id)) {
        map.get(t.parent_id)!.children.push(node);
      } else {
        roots.push(node);
      }
    }

    return roots;
  }

  private flattenTree(nodes: TenantNode[]): TenantNode[] {
    const result: TenantNode[] = [];
    const walk = (list: TenantNode[]) => {
      for (const node of list) {
        result.push(node);
        if (node.children.length > 0) {
          walk(node.children);
        }
      }
    };
    walk(nodes);
    return result;
  }
}
