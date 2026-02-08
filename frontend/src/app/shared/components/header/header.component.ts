/**
 * Overview: Application header with brand left, user/tenant info and actions right.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common
 * Concepts: Layout, navigation, user actions, tenant switching, sidebar toggle
 */
import { Component, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '@core/auth/auth.service';
import { ImpersonationService } from '@core/services/impersonation.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { NotificationBellComponent } from '../notification-bell/notification-bell.component';
import { TenantSwitcherComponent } from '../tenant-switcher/tenant-switcher.component';

@Component({
  selector: 'nimbus-header',
  standalone: true,
  imports: [CommonModule, RouterLink, NotificationBellComponent, TenantSwitcherComponent],
  template: `
    <header class="header" [class.impersonating]="impersonationService.isImpersonating()">
      <div class="header-left">
        <button class="sidebar-toggle" (click)="toggleSidebar.emit()" [attr.aria-label]="sidebarCollapsed() ? 'Open sidebar' : 'Close sidebar'">
          <span class="toggle-icon">&#9776;</span>
        </button>
        <a routerLink="/dashboard" class="brand-link">
          <span class="brand-mark">N</span>
          <span class="brand-text">Nimbus</span>
        </a>
      </div>

      <div class="header-right">
        @if (authService.currentUser(); as user) {
          <div class="user-badge">
            <span class="user-avatar">{{ getUserInitial(user.display_name ?? user.email) }}</span>
            <span class="user-name">{{ user.display_name ?? user.email }}</span>
            @if (impersonationService.isImpersonating()) {
              <span class="impersonation-label">(Impersonating)</span>
            }
          </div>
        }

        <nimbus-notification-bell />
        <nimbus-tenant-switcher />

        <button class="btn-icon" (click)="authService.logout()" title="Sign out">
          &#9211;
        </button>
      </div>
    </header>
  `,
  styles: [`
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 48px;
      padding: 0 1rem;
      background: #1a1f2b;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      z-index: 10;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .sidebar-toggle {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 2rem;
      height: 2rem;
      background: none;
      border: none;
      color: #9ca3af;
      cursor: pointer;
      border-radius: 4px;
      font-size: 1rem;
      transition: background 0.15s, color 0.15s;
    }
    .sidebar-toggle:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }

    .brand-link {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      color: #fff;
    }

    .brand-mark {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 1.625rem;
      height: 1.625rem;
      background: linear-gradient(135deg, #3b82f6, #2563eb);
      border-radius: 5px;
      font-size: 0.875rem;
      font-weight: 800;
      color: #fff;
    }

    .brand-text {
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .user-badge {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem 0.25rem 0.25rem;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 1rem;
    }

    .user-avatar {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 1.5rem;
      height: 1.5rem;
      border-radius: 50%;
      background: rgba(59, 130, 246, 0.25);
      color: #60a5fa;
      font-size: 0.6875rem;
      font-weight: 700;
    }

    .user-name {
      color: #e0e0e0;
      font-size: 0.75rem;
      font-weight: 500;
    }

    .btn-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 2rem;
      height: 2rem;
      background: none;
      border: none;
      color: #64748b;
      cursor: pointer;
      border-radius: 4px;
      font-size: 1.125rem;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #ef4444;
    }

    .header.impersonating {
      border-bottom: 2px solid #f59e0b;
    }

    .impersonation-label {
      color: #f59e0b;
      font-size: 0.625rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  `],
})
export class HeaderComponent {
  authService = inject(AuthService);
  impersonationService = inject(ImpersonationService);
  tenantContext = inject(TenantContextService);

  sidebarCollapsed = input(false);
  toggleSidebar = output();

  getUserInitial(name: string): string {
    return name.charAt(0).toUpperCase();
  }
}
