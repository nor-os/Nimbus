/**
 * Overview: Full notification center with filtering, pagination, mark-read, and delete.
 * Architecture: Feature component at /notifications (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/core/services/notification.service
 * Concepts: Notification list, category filtering, read/unread filter, pagination
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService } from '@core/services/notification.service';
import {
  Notification,
  NotificationCategory,
} from '@shared/models/notification.model';

const CATEGORIES: NotificationCategory[] = [
  'APPROVAL',
  'SECURITY',
  'SYSTEM',
  'AUDIT',
  'DRIFT',
  'WORKFLOW',
  'USER',
];

@Component({
  selector: 'nimbus-notification-center',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">Notifications</h1>
        <div class="header-actions">
          @if (unreadCount() > 0) {
            <button class="btn btn-secondary" (click)="markAllRead()">
              Mark all read ({{ unreadCount() }})
            </button>
          }
        </div>
      </div>

      <div class="filters">
        <select class="filter-select" (change)="onCategoryChange($event)">
          <option value="">All categories</option>
          @for (cat of categories; track cat) {
            <option [value]="cat">{{ cat }}</option>
          }
        </select>
        <select class="filter-select" (change)="onReadFilterChange($event)">
          <option value="">All</option>
          <option value="false">Unread</option>
          <option value="true">Read</option>
        </select>
      </div>

      <div class="notification-list">
        @if (loading()) {
          <div class="loading">Loading...</div>
        }
        @if (!loading() && notifications().length === 0) {
          <div class="empty">No notifications found.</div>
        }
        @for (n of notifications(); track n.id) {
          <div class="notification-row" [class.unread]="!n.isRead">
            <div class="notification-content">
              <div class="notification-meta">
                <span class="category-badge">{{ n.category }}</span>
                <span class="time">{{ formatTime(n.createdAt) }}</span>
              </div>
              <div class="notification-title">{{ n.title }}</div>
              <div class="notification-body">{{ n.body }}</div>
            </div>
            <div class="notification-actions">
              @if (!n.isRead) {
                <button class="btn-small" (click)="markRead(n)" title="Mark read">
                  &#10003;
                </button>
              }
              <button class="btn-small btn-danger" (click)="deleteNotification(n)" title="Delete">
                &#10005;
              </button>
            </div>
          </div>
        }
      </div>

      @if (total() > limit) {
        <div class="pagination">
          <button
            class="btn btn-secondary"
            [disabled]="offset() === 0"
            (click)="prevPage()"
          >
            Previous
          </button>
          <span class="page-info">
            {{ offset() + 1 }}–{{ Math.min(offset() + limit, total()) }} of {{ total() }}
          </span>
          <button
            class="btn btn-secondary"
            [disabled]="offset() + limit >= total()"
            (click)="nextPage()"
          >
            Next
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .page { padding: 1.5rem; max-width: 56rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .page-title { font-size: 1.25rem; font-weight: 700; color: #e0e0e0; margin: 0; }
    .filters { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .filter-select {
      padding: 0.375rem 0.75rem; background: #1e2433; color: #e0e0e0;
      border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; font-size: 0.75rem;
    }
    .notification-list { display: flex; flex-direction: column; gap: 0.25rem; }
    .notification-row {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 0.75rem 1rem; background: #1e2433; border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .notification-row.unread { border-left: 3px solid #3b82f6; }
    .notification-content { flex: 1; min-width: 0; }
    .notification-meta { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.25rem; }
    .category-badge {
      padding: 0.125rem 0.375rem; background: rgba(59,130,246,0.15);
      color: #60a5fa; font-size: 0.625rem; font-weight: 600; border-radius: 3px;
      text-transform: uppercase;
    }
    .time { font-size: 0.625rem; color: #64748b; }
    .notification-title { font-size: 0.8125rem; font-weight: 600; color: #e0e0e0; }
    .notification-body { font-size: 0.75rem; color: #9ca3af; margin-top: 0.125rem; }
    .notification-actions { display: flex; gap: 0.25rem; flex-shrink: 0; margin-left: 0.5rem; }
    .btn-small {
      width: 1.5rem; height: 1.5rem; display: flex; align-items: center; justify-content: center;
      background: none; border: 1px solid rgba(255,255,255,0.1); color: #9ca3af;
      border-radius: 3px; cursor: pointer; font-size: 0.6875rem;
    }
    .btn-small:hover { background: rgba(255,255,255,0.06); color: #e0e0e0; }
    .btn-small.btn-danger:hover { color: #ef4444; }
    .btn { padding: 0.375rem 0.75rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; border: none; }
    .btn-secondary { background: rgba(255,255,255,0.08); color: #e0e0e0; }
    .btn-secondary:hover { background: rgba(255,255,255,0.12); }
    .btn-secondary:disabled { opacity: 0.4; cursor: default; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1rem; }
    .page-info { font-size: 0.75rem; color: #9ca3af; }
    .loading, .empty { padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem; }
    .header-actions { display: flex; gap: 0.5rem; }
  `],
})
export class NotificationCenterComponent implements OnInit {
  private notificationService = inject(NotificationService);
  Math = Math;

  notifications = signal<Notification[]>([]);
  total = signal(0);
  unreadCount = signal(0);
  offset = signal(0);
  loading = signal(false);
  limit = 20;

  categories = CATEGORIES;
  private categoryFilter: NotificationCategory | undefined;
  private readFilter: boolean | undefined;

  ngOnInit(): void {
    this.load();
  }

  onCategoryChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.categoryFilter = value ? (value as NotificationCategory) : undefined;
    this.offset.set(0);
    this.load();
  }

  onReadFilterChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.readFilter = value === '' ? undefined : value === 'true';
    this.offset.set(0);
    this.load();
  }

  markAllRead(): void {
    this.notificationService.markAllRead().subscribe(() => {
      this.notifications.update((items) =>
        items.map((n) => ({ ...n, isRead: true })),
      );
      this.unreadCount.set(0);
    });
  }

  markRead(n: Notification): void {
    this.notificationService.markRead(n.id).subscribe(() => {
      this.notifications.update((items) =>
        items.map((item) =>
          item.id === n.id ? { ...item, isRead: true } : item,
        ),
      );
      this.unreadCount.update((c) => Math.max(0, c - 1));
    });
  }

  deleteNotification(n: Notification): void {
    this.notificationService.deleteNotification(n.id).subscribe((deleted) => {
      if (deleted) {
        this.notifications.update((items) => items.filter((i) => i.id !== n.id));
        this.total.update((t) => t - 1);
        if (!n.isRead) this.unreadCount.update((c) => Math.max(0, c - 1));
      }
    });
  }

  prevPage(): void {
    this.offset.update((o) => Math.max(0, o - this.limit));
    this.load();
  }

  nextPage(): void {
    this.offset.update((o) => o + this.limit);
    this.load();
  }

  formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  private load(): void {
    this.loading.set(true);
    this.notificationService
      .listNotifications({
        category: this.categoryFilter,
        isRead: this.readFilter,
        offset: this.offset(),
        limit: this.limit,
      })
      .subscribe({
        next: (res) => {
          this.notifications.set(res.items);
          this.total.set(res.total);
          this.unreadCount.set(res.unreadCount);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }
}
