/**
 * Overview: Enterprise sidebar navigation with collapsible groups and role-aware visibility.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common
 * Concepts: Navigation, sidebar, enterprise portal, route-aware menu, root-tenant gating, provider section
 */
import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationEnd, RouterLink, RouterLinkActive } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';
import { TenantContextService } from '@core/services/tenant-context.service';
import { PermissionCheckService } from '@core/services/permission-check.service';

interface NavItem {
  label: string;
  icon: string;
  route?: string;
  children?: NavItem[];
  disabled?: boolean;
  rootOnly?: boolean;
  exact?: boolean;
  permission?: string;
}

@Component({
  selector: 'nimbus-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <nav class="sidebar-nav" role="navigation" aria-label="Main navigation">

      <!-- Provider section — only visible for root tenant -->
      @if (showProviderSection()) {
        <div class="provider-section">
          <div class="section-label">Provider</div>
          @for (item of providerItems; track item.label) {
            <a
              class="nav-item nav-top-item"
              [routerLink]="item.route"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{ exact: !!item.exact }"
            >
              <span class="nav-icon" [innerHTML]="item.icon"></span>
              <span class="nav-label">{{ item.label }}</span>
            </a>
          }
        </div>
      }

      <!-- Main navigation -->
      @for (group of visibleNavGroups(); track group.label) {
        @if (!group.disabled) {
          <div class="nav-group">
            @if (group.children) {
              <button
                class="nav-group-header"
                [class.locked]="isActiveGroup(group.label)"
                (click)="toggleGroup(group.label)"
                [attr.aria-expanded]="isExpanded(group.label)"
              >
                <span class="nav-icon" [innerHTML]="group.icon"></span>
                <span class="nav-label">{{ group.label }}</span>
                <span class="nav-chevron" [class.expanded]="isExpanded(group.label)">&#9206;</span>
              </button>
              @if (isExpanded(group.label)) {
                <div class="nav-children">
                  @for (child of visibleChildren(group); track child.label) {
                    @if (child.route && !child.disabled) {
                      <a
                        class="nav-item nav-child"
                        [routerLink]="child.route"
                        routerLinkActive="active"
                        [routerLinkActiveOptions]="{ exact: !!child.exact }"
                      >
                        <span class="nav-label">{{ child.label }}</span>
                      </a>
                    }
                    @if (child.disabled) {
                      <span class="nav-item nav-child disabled">
                        <span class="nav-label">{{ child.label }}</span>
                      </span>
                    }
                  }
                </div>
              }
            } @else if (group.route) {
              <a
                class="nav-item nav-top-item"
                [routerLink]="group.route"
                routerLinkActive="active"
                [routerLinkActiveOptions]="{ exact: !!group.exact }"
              >
                <span class="nav-icon" [innerHTML]="group.icon"></span>
                <span class="nav-label">{{ group.label }}</span>
              </a>
            }
          </div>
        }

        @if (group.disabled) {
          <div class="nav-group">
            <span class="nav-group-header disabled">
              <span class="nav-icon" [innerHTML]="group.icon"></span>
              <span class="nav-label">{{ group.label }}</span>
            </span>
          </div>
        }
      }
    </nav>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .sidebar-nav {
      display: flex;
      flex-direction: column;
      flex: 1;
      padding: 0.5rem 0;
      overflow-y: auto;
    }

    /* ── Provider section ─────────────────────────────── */

    .provider-section {
      margin: 0 0.5rem 0.25rem;
      padding: 0.5rem 0;
      background: rgba(59, 130, 246, 0.08);
      border-radius: 6px;
      border: 1px solid rgba(59, 130, 246, 0.12);
    }

    .section-label {
      padding: 0 0.75rem 0.375rem;
      font-size: 0.625rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #60a5fa;
    }

    .provider-section .nav-item {
      padding: 0.4375rem 0.75rem;
      margin: 0;
      border-radius: 4px;
    }

    .provider-section .nav-item:hover:not(.disabled) {
      background: rgba(59, 130, 246, 0.12);
    }

    .provider-section .nav-item.active {
      background: rgba(59, 130, 246, 0.18);
      color: #60a5fa;
      border-right: none;
    }

    /* ── Standard navigation ──────────────────────────── */

    .nav-group {
      margin-bottom: 0.125rem;
    }

    .nav-group-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      width: 100%;
      padding: 0.625rem 1rem;
      border: none;
      background: none;
      color: #c8ccd0;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      text-align: left;
      transition: background 0.15s, color 0.15s;
      font-family: inherit;
    }
    .nav-group-header:hover:not(.disabled) {
      background: rgba(255, 255, 255, 0.06);
      color: #fff;
    }
    .nav-group-header.disabled {
      opacity: 0.35;
      cursor: default;
    }
    .nav-group-header.locked {
      cursor: default;
    }
    .nav-group-header.locked .nav-chevron {
      opacity: 0.3;
    }

    .nav-chevron {
      margin-left: auto;
      font-size: 0.625rem;
      transition: transform 0.2s;
      transform: rotate(180deg);
    }
    .nav-chevron.expanded {
      transform: rotate(0deg);
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem 1rem;
      color: #c8ccd0;
      text-decoration: none;
      font-size: 0.8125rem;
      transition: background 0.15s, color 0.15s;
      cursor: pointer;
    }
    .nav-item:hover:not(.disabled) {
      background: rgba(255, 255, 255, 0.06);
      color: #fff;
    }
    .nav-item.active {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border-right: 2px solid #3b82f6;
    }
    .nav-item.disabled {
      opacity: 0.35;
      cursor: default;
    }

    .nav-top-item {
      font-weight: 500;
    }

    .nav-child {
      padding-left: 2.75rem;
    }

    .nav-children {
      overflow: hidden;
    }

    .nav-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 1.25rem;
      font-size: 1rem;
      flex-shrink: 0;
    }

    .nav-label {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  `],
})
export class SidebarComponent {
  tenantContext = inject(TenantContextService);
  private permissionCheck = inject(PermissionCheckService);
  private router = inject(Router);

  private expandedGroups = signal<Set<string>>(new Set(['Users & Roles', 'Settings', 'Workflows', 'CMDB', 'Services']));
  private activeGroup = signal<string | null>(null);

  constructor() {
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      takeUntilDestroyed(),
    ).subscribe(() => this.updateActiveGroup());
    this.updateActiveGroup();
  }

  showProviderSection = computed(() => this.tenantContext.canManageClients());

  providerItems: NavItem[] = [
    { label: 'Tenants', icon: '&#9636;', route: '/tenants', permission: 'settings:tenant:read' },
  ];

  private allNavGroups: NavItem[] = [
    {
      label: 'Dashboard',
      icon: '&#9673;',
      route: '/dashboard',
      exact: true,
    },
    {
      label: 'CMDB',
      icon: '&#9634;',
      permission: 'cmdb:ci:read',
      children: [
        { label: 'Dashboard', icon: '', route: '/cmdb/dashboard', permission: 'cmdb:ci:read' },
        { label: 'Configuration Items', icon: '', route: '/cmdb', exact: true, permission: 'cmdb:ci:read' },
        { label: 'Classes', icon: '', route: '/cmdb/classes', permission: 'cmdb:class:read' },
      ],
    },
    {
      label: 'Services',
      icon: '&#9881;',
      permission: 'cmdb:catalog:read',
      children: [
        { label: 'Catalog', icon: '', route: '/catalog/services', permission: 'cmdb:catalog:read' },
        { label: 'Pricing', icon: '', route: '/catalog/pricing', permission: 'cmdb:catalog:manage' },
        { label: 'Processes', icon: '', route: '/catalog/processes', permission: 'catalog:process:read' },
        { label: 'Estimations', icon: '', route: '/catalog/estimations', permission: 'catalog:estimation:read' },
        { label: 'Regions', icon: '', route: '/catalog/regions', permission: 'catalog:region:read' },
        { label: 'Rate Cards', icon: '', route: '/catalog/rate-cards', permission: 'catalog:staff:read' },
        { label: 'Profitability', icon: '', route: '/catalog/profitability', permission: 'catalog:profitability:read' },
      ],
    },
    {
      label: 'Architecture',
      icon: '&#9783;',
      disabled: true,
      route: '/architecture',
    },
    {
      label: 'Semantic Explorer',
      icon: '&#9670;',
      route: '/semantic',
      exact: true,
      permission: 'semantic:type:read',
    },
    {
      label: 'Users & Roles',
      icon: '&#9823;',
      permission: 'users:user:list',
      children: [
        { label: 'Users', icon: '', route: '/users', exact: true, permission: 'users:user:list' },
        { label: 'Roles', icon: '', route: '/users/roles', permission: 'users:role:list' },
        { label: 'Groups', icon: '', route: '/users/groups', permission: 'users:group:list' },
        { label: 'Impersonate', icon: '', route: '/users/impersonate', permission: 'impersonation:session:read' },
        { label: 'ABAC Policies', icon: '', route: '/permissions/abac', exact: true, permission: 'permissions:abac:list' },
        { label: 'Overrides', icon: '', route: '/permissions/overrides', permission: 'permissions:abac:list' },
        { label: 'Simulator', icon: '', route: '/permissions/simulator', permission: 'permissions:permission:simulate' },
      ],
    },
    {
      label: 'Workflows',
      icon: '&#8644;',
      permission: 'approval:decision:submit',
      children: [
        { label: 'Definitions', icon: '', route: '/workflows/definitions', exact: true, permission: 'workflow:definition:read' },
        { label: 'Executions', icon: '', route: '/workflows/executions', exact: true, permission: 'workflow:execution:read' },
        { label: 'Approvals', icon: '', route: '/workflows/approvals', permission: 'approval:decision:submit' },
        { label: 'Manage', icon: '', route: '/workflows/manage', permission: 'approval:policy:manage' },
      ],
    },
    {
      label: 'Audit Log',
      icon: '&#9112;',
      permission: 'audit:log:read',
      children: [
        { label: 'Explorer', icon: '', route: '/audit', exact: true, permission: 'audit:log:read' },
        { label: 'Configuration', icon: '', route: '/audit/config', permission: 'audit:retention:read' },
      ],
    },
    {
      label: 'Cost',
      icon: '&#9733;',
      disabled: true,
      route: '/cost',
    },
    {
      label: 'Settings',
      icon: '&#9881;',
      permission: 'settings:idp:list',
      children: [
        { label: 'General', icon: '', route: '/settings', disabled: true },
        { label: 'Authentication', icon: '', route: '/settings/auth', exact: true, permission: 'settings:idp:list' },
        { label: 'Impersonation', icon: '', route: '/settings/impersonation', permission: 'impersonation:config:manage' },
        { label: 'Notifications', icon: '', route: '/settings/notifications', permission: 'notification:preference:manage' },
        { label: 'Webhooks', icon: '', route: '/settings/webhooks', permission: 'notification:webhook:manage' },
      ],
    },
  ];

  visibleNavGroups = computed(() => {
    const canManage = this.tenantContext.canManageClients();
    // Re-evaluate when permissions change
    this.permissionCheck.permissions();
    return this.allNavGroups.filter((group) => {
      if (group.rootOnly && !canManage) return false;
      if (group.permission && !this.hasPermission(group.permission)) return false;
      return true;
    });
  });

  visibleChildren(group: NavItem): NavItem[] {
    const canManage = this.tenantContext.canManageClients();
    return (group.children ?? []).filter((child) => {
      if (child.rootOnly && !canManage) return false;
      if (child.permission && !this.hasPermission(child.permission)) return false;
      return true;
    });
  }

  private hasPermission(key: string): boolean {
    // While loading, show all items to avoid flash of missing nav
    if (this.permissionCheck.isLoading()) return true;
    return this.permissionCheck.hasPermission(key);
  }

  toggleGroup(label: string): void {
    if (this.activeGroup() === label) return;
    const current = this.expandedGroups();
    const next = new Set(current);
    if (next.has(label)) {
      next.delete(label);
    } else {
      next.add(label);
    }
    this.expandedGroups.set(next);
  }

  isExpanded(label: string): boolean {
    return this.expandedGroups().has(label);
  }

  isActiveGroup(label: string): boolean {
    return this.activeGroup() === label;
  }

  private updateActiveGroup(): void {
    const url = this.router.url.split('?')[0].split('#')[0];
    for (const group of this.allNavGroups) {
      if (group.children) {
        for (const child of group.children) {
          if (child.route && this.isRouteMatch(url, child.route, !!child.exact)) {
            this.activeGroup.set(group.label);
            const current = this.expandedGroups();
            if (!current.has(group.label)) {
              const next = new Set(current);
              next.add(group.label);
              this.expandedGroups.set(next);
            }
            return;
          }
        }
      } else if (group.route && this.isRouteMatch(url, group.route, !!group.exact)) {
        this.activeGroup.set(group.label);
        return;
      }
    }
    this.activeGroup.set(null);
  }

  private isRouteMatch(url: string, route: string, exact: boolean): boolean {
    if (exact) return url === route;
    return url === route || url.startsWith(route + '/');
  }
}
