/**
 * Overview: Notification bell icon with unread badge and dropdown for recent notifications.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router
 * Concepts: Notification bell, unread count badge, dropdown, polling lifecycle
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  OnDestroy,
  HostListener,
  ElementRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { NotificationService } from '@core/services/notification.service';
import { Notification } from '@shared/models/notification.model';

@Component({
  selector: 'nimbus-notification-bell',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="bell-wrapper">
      <button
        class="bell-btn"
        (click)="toggleDropdown()"
        title="Notifications"
        aria-label="Notifications"
      >
        <svg class="bell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        @if (notificationService.unreadCount() > 0) {
          <span class="badge">{{ notificationService.unreadCount() }}</span>
        }
      </button>

      @if (dropdownOpen()) {
        <div class="dropdown">
          <div class="dropdown-header">
            <span class="dropdown-title">Notifications</span>
            @if (notificationService.unreadCount() > 0) {
              <button class="mark-all-btn" (click)="markAllRead()">
                Mark all read
              </button>
            }
          </div>

          <div class="dropdown-list">
            @if (recentNotifications().length === 0) {
              <div class="empty-state">No notifications</div>
            }
            @for (n of recentNotifications(); track n.id) {
              <div
                class="notification-item"
                [class.unread]="!n.isRead"
                (click)="onNotificationClick(n)"
              >
                <div class="notification-title">{{ n.title }}</div>
                <div class="notification-body">{{ n.body | slice: 0 : 80 }}</div>
                <div class="notification-time">{{ formatTime(n.createdAt) }}</div>
              </div>
            }
          </div>

          <a class="view-all" routerLink="/notifications" (click)="dropdownOpen.set(false)">
            View all notifications
          </a>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .bell-wrapper {
        position: relative;
      }

      .bell-btn {
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
        position: relative;
        transition: background 0.15s, color 0.15s;
      }
      .bell-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
      }

      .bell-icon {
        width: 1.125rem;
        height: 1.125rem;
      }

      .badge {
        position: absolute;
        top: 0;
        right: 0;
        min-width: 1rem;
        height: 1rem;
        padding: 0 0.25rem;
        background: #ef4444;
        color: #fff;
        font-size: 0.625rem;
        font-weight: 700;
        border-radius: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
      }

      .dropdown {
        position: absolute;
        top: calc(100% + 0.5rem);
        right: 0;
        width: 22rem;
        background: #1e2433;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        z-index: 100;
        overflow: hidden;
      }

      .dropdown-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      }

      .dropdown-title {
        font-size: 0.8125rem;
        font-weight: 600;
        color: #e0e0e0;
      }

      .mark-all-btn {
        background: none;
        border: none;
        color: #60a5fa;
        font-size: 0.6875rem;
        cursor: pointer;
        padding: 0;
        font-family: inherit;
      }
      .mark-all-btn:hover {
        text-decoration: underline;
      }

      .dropdown-list {
        max-height: 20rem;
        overflow-y: auto;
      }

      .notification-item {
        padding: 0.625rem 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        cursor: pointer;
        transition: background 0.15s;
      }
      .notification-item:hover {
        background: rgba(255, 255, 255, 0.04);
      }
      .notification-item.unread {
        border-left: 2px solid #3b82f6;
      }

      .notification-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #e0e0e0;
        margin-bottom: 0.125rem;
      }

      .notification-body {
        font-size: 0.6875rem;
        color: #9ca3af;
        line-height: 1.3;
      }

      .notification-time {
        font-size: 0.625rem;
        color: #64748b;
        margin-top: 0.25rem;
      }

      .empty-state {
        padding: 2rem 1rem;
        text-align: center;
        color: #64748b;
        font-size: 0.75rem;
      }

      .view-all {
        display: block;
        padding: 0.625rem 1rem;
        text-align: center;
        color: #60a5fa;
        font-size: 0.75rem;
        text-decoration: none;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
      }
      .view-all:hover {
        background: rgba(255, 255, 255, 0.04);
      }
    `,
  ],
})
export class NotificationBellComponent implements OnInit, OnDestroy {
  notificationService = inject(NotificationService);
  private elementRef = inject(ElementRef);
  private router = inject(Router);

  dropdownOpen = signal(false);
  recentNotifications = signal<Notification[]>([]);

  ngOnInit(): void {
    this.notificationService.startPolling();
  }

  ngOnDestroy(): void {
    this.notificationService.stopPolling();
  }

  toggleDropdown(): void {
    const isOpen = !this.dropdownOpen();
    this.dropdownOpen.set(isOpen);
    if (isOpen) {
      this.loadRecent();
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.dropdownOpen.set(false);
    }
  }

  markAllRead(): void {
    this.notificationService.markAllRead().subscribe(() => {
      this.recentNotifications.update((items) =>
        items.map((n) => ({ ...n, isRead: true })),
      );
    });
  }

  onNotificationClick(n: Notification): void {
    if (!n.isRead) {
      this.notificationService.markRead(n.id).subscribe(() => {
        this.recentNotifications.update((items) =>
          items.map((item) =>
            item.id === n.id ? { ...item, isRead: true } : item,
          ),
        );
      });
    }

    // Navigate to approvals page for APPROVAL notifications
    if (n.category === 'APPROVAL') {
      this.dropdownOpen.set(false);
      this.router.navigate(['/workflows/approvals']);
    }
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  private loadRecent(): void {
    this.notificationService
      .listNotifications({ limit: 8 })
      .subscribe((res) => {
        this.recentNotifications.set(res.items);
      });
  }
}
