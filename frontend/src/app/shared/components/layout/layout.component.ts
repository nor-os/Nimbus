/**
 * Overview: Main layout shell with header, sidebar navigation, and content area.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Application layout, enterprise portal shell, sidebar navigation
 */
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HeaderComponent } from '../header/header.component';
import { ImpersonationBannerComponent } from '../impersonation-banner/impersonation-banner.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { BreadcrumbComponent } from '../breadcrumb/breadcrumb.component';

@Component({
  selector: 'nimbus-layout',
  standalone: true,
  imports: [CommonModule, HeaderComponent, ImpersonationBannerComponent, SidebarComponent, BreadcrumbComponent],
  template: `
    <div class="layout">
      <nimbus-header (toggleSidebar)="onToggleSidebar()" [sidebarCollapsed]="collapsed()" />
      <nimbus-impersonation-banner />
      <div class="layout-body">
        <aside class="layout-sidebar" [class.collapsed]="collapsed()">
          <nimbus-sidebar />
        </aside>
        <main class="layout-content">
          <nimbus-breadcrumb />
          <ng-content />
        </main>
      </div>
    </div>
  `,
  styles: [`
    .layout {
      display: flex;
      flex-direction: column;
      height: 100vh;
      background: #f5f6f8;
    }
    .layout-body {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    .layout-sidebar {
      width: 240px;
      min-width: 240px;
      background: #1e2530;
      border-right: 1px solid rgba(255, 255, 255, 0.06);
      transition: width 0.2s ease, min-width 0.2s ease;
      overflow: hidden;
    }
    .layout-sidebar.collapsed {
      width: 0;
      min-width: 0;
      border-right: none;
    }
    .layout-content {
      flex: 1;
      padding: 1.5rem 2rem;
      overflow-y: auto;
    }
  `],
})
export class LayoutComponent {
  collapsed = signal(false);

  onToggleSidebar(): void {
    this.collapsed.update((v) => !v);
  }
}
