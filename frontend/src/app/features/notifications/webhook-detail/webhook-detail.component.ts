/**
 * Overview: Webhook delivery history with retry for dead-lettered deliveries.
 * Architecture: Feature component at /settings/webhooks/:id (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/notification.service
 * Concepts: Webhook deliveries, delivery status, dead letter retry, pagination
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { NotificationService } from '@core/services/notification.service';
import { WebhookDelivery } from '@shared/models/notification.model';

type DeliveryStatus = '' | 'PENDING' | 'DELIVERED' | 'FAILED' | 'DEAD_LETTER';

@Component({
  selector: 'nimbus-webhook-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="page-header">
        <div class="header-left">
          <button class="btn btn-secondary" (click)="goBack()">
            &larr; Webhooks
          </button>
          <h1 class="page-title">Delivery History</h1>
        </div>
      </div>

      <div class="filters">
        <select class="filter-select" (change)="onStatusChange($event)">
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="DELIVERED">Delivered</option>
          <option value="FAILED">Failed</option>
          <option value="DEAD_LETTER">Dead Letter</option>
        </select>
      </div>

      <div class="delivery-list">
        @if (loading()) {
          <div class="loading">Loading deliveries...</div>
        }
        @if (!loading() && deliveries().length === 0) {
          <div class="empty">No deliveries found.</div>
        }
        @for (d of deliveries(); track d.id) {
          <div class="delivery-row">
            <div class="delivery-info">
              <div class="delivery-header">
                <span class="status-badge" [class]="'status-' + d.status.toLowerCase()">
                  {{ d.status }}
                </span>
                <span class="delivery-time">{{ formatTime(d.createdAt) }}</span>
              </div>
              <div class="delivery-meta">
                <span class="meta-item">
                  Attempts: {{ d.attempts }}/{{ d.maxAttempts }}
                </span>
                @if (d.lastAttemptAt) {
                  <span class="meta-item">
                    Last attempt: {{ formatTime(d.lastAttemptAt) }}
                  </span>
                }
                @if (d.nextRetryAt) {
                  <span class="meta-item">
                    Next retry: {{ formatTime(d.nextRetryAt) }}
                  </span>
                }
              </div>
              @if (d.lastError) {
                <div class="delivery-error">{{ d.lastError }}</div>
              }
            </div>
            <div class="delivery-actions">
              @if (d.status === 'DEAD_LETTER' || d.status === 'FAILED') {
                <button
                  class="btn btn-secondary btn-sm"
                  (click)="retryDelivery(d)"
                  [disabled]="retrying() === d.id"
                >
                  {{ retrying() === d.id ? 'Retrying...' : 'Retry' }}
                </button>
              }
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
            {{ offset() + 1 }}&ndash;{{ Math.min(offset() + limit, total()) }}
            of {{ total() }}
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
    .page-header {
      display: flex; justify-content: space-between;
      align-items: center; margin-bottom: 1rem;
    }
    .header-left { display: flex; align-items: center; gap: 0.75rem; }
    .page-title { font-size: 1.25rem; font-weight: 700; color: #e0e0e0; margin: 0; }
    .filters { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .filter-select {
      padding: 0.375rem 0.75rem; background: #1e2433; color: #e0e0e0;
      border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; font-size: 0.75rem;
    }
    .delivery-list { display: flex; flex-direction: column; gap: 0.25rem; }
    .delivery-row {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 0.75rem 1rem; background: #1e2433; border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .delivery-info { flex: 1; min-width: 0; }
    .delivery-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
    .status-badge {
      display: inline-block; padding: 0.125rem 0.5rem;
      font-size: 0.625rem; font-weight: 700; border-radius: 3px;
      text-transform: uppercase;
    }
    .status-pending { background: rgba(234,179,8,0.15); color: #facc15; }
    .status-delivered { background: rgba(34,197,94,0.15); color: #22c55e; }
    .status-failed { background: rgba(239,68,68,0.15); color: #f87171; }
    .status-dead_letter { background: rgba(168,85,247,0.15); color: #c084fc; }
    .delivery-time { font-size: 0.6875rem; color: #64748b; }
    .delivery-meta { display: flex; gap: 0.75rem; }
    .meta-item { font-size: 0.6875rem; color: #9ca3af; }
    .delivery-error {
      margin-top: 0.25rem; font-size: 0.6875rem; color: #f87171;
      font-family: monospace; word-break: break-all;
    }
    .delivery-actions { flex-shrink: 0; margin-left: 0.75rem; }
    .btn {
      padding: 0.375rem 0.75rem; border-radius: 4px;
      font-size: 0.75rem; cursor: pointer; border: none;
    }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.6875rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-secondary { background: rgba(255,255,255,0.08); color: #e0e0e0; }
    .btn-secondary:hover { background: rgba(255,255,255,0.12); }
    .btn-secondary:disabled { opacity: 0.4; cursor: default; }
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .page-info { font-size: 0.75rem; color: #9ca3af; }
    .loading, .empty {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }
  `],
})
export class WebhookDetailComponent implements OnInit {
  private notificationService = inject(NotificationService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  Math = Math;

  deliveries = signal<WebhookDelivery[]>([]);
  total = signal(0);
  offset = signal(0);
  loading = signal(false);
  retrying = signal<string | null>(null);
  limit = 20;

  private configId = '';
  private statusFilter: DeliveryStatus = '';

  ngOnInit(): void {
    this.configId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();
  }

  onStatusChange(event: Event): void {
    this.statusFilter = (event.target as HTMLSelectElement).value as DeliveryStatus;
    this.offset.set(0);
    this.load();
  }

  retryDelivery(d: WebhookDelivery): void {
    this.retrying.set(d.id);
    this.notificationService.retryDelivery(d.id).subscribe({
      next: (updated) => {
        if (updated) {
          this.deliveries.update((items) =>
            items.map((item) =>
              item.id === d.id
                ? { ...item, status: updated.status, attempts: updated.attempts }
                : item,
            ),
          );
        }
        this.retrying.set(null);
      },
      error: () => this.retrying.set(null),
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

  goBack(): void {
    this.router.navigate(['/settings/webhooks']);
  }

  formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  private load(): void {
    this.loading.set(true);
    this.notificationService
      .getDeliveries(
        this.configId,
        this.statusFilter || undefined,
        this.offset(),
        this.limit,
      )
      .subscribe({
        next: (res) => {
          this.deliveries.set(res.items);
          this.total.set(res.total);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }
}
