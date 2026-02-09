/**
 * Overview: Webhook delivery history with retry for dead-lettered deliveries.
 * Architecture: Feature component at /settings/webhooks/:id (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/notification.service
 * Concepts: Webhook deliveries, delivery status, dead letter retry, pagination
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ActivatedRoute, Router } from '@angular/router';
import { NotificationService } from '@core/services/notification.service';
import { WebhookDelivery } from '@shared/models/notification.model';

type DeliveryStatus = '' | 'PENDING' | 'DELIVERED' | 'FAILED' | 'DEAD_LETTER';

@Component({
  selector: 'nimbus-webhook-detail',
  standalone: true,
  imports: [CommonModule, LayoutComponent],
  template: `
    <nimbus-layout>
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
    </nimbus-layout>
  `,
  styles: [`
    .page { max-width: 56rem; }
    .page-header {
      display: flex; justify-content: space-between;
      align-items: center; margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 0.75rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .filters {
      display: flex; gap: 0.5rem; margin-bottom: 1rem; padding: 0.75rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .filter-select {
      padding: 0.375rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8125rem;
      font-family: inherit;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }
    .delivery-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .delivery-row {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 0.75rem 1rem; background: #fff; border-radius: 8px;
      border: 1px solid #e2e8f0;
    }
    .delivery-row:hover { background: #f8fafc; }
    .delivery-info { flex: 1; min-width: 0; }
    .delivery-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
    .status-badge {
      display: inline-block; padding: 0.125rem 0.5rem;
      font-size: 0.6875rem; font-weight: 600; border-radius: 12px;
      text-transform: uppercase;
    }
    .status-pending { background: #fef9c3; color: #a16207; }
    .status-delivered { background: #dcfce7; color: #16a34a; }
    .status-failed { background: #fef2f2; color: #dc2626; }
    .status-dead_letter { background: #f3e8ff; color: #7c3aed; }
    .delivery-time { font-size: 0.6875rem; color: #64748b; }
    .delivery-meta { display: flex; gap: 0.75rem; }
    .meta-item { font-size: 0.6875rem; color: #94a3b8; }
    .delivery-error {
      margin-top: 0.25rem; font-size: 0.6875rem; color: #dc2626;
      font-family: monospace; word-break: break-all;
    }
    .delivery-actions { flex-shrink: 0; margin-left: 0.75rem; }
    .btn {
      padding: 0.5rem 1.5rem; border-radius: 6px;
      font-size: 0.8125rem; font-weight: 500; cursor: pointer; border: none;
      font-family: inherit; transition: background 0.15s;
    }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; padding: 0.75rem; margin-top: 1rem;
    }
    .page-info { font-size: 0.8125rem; color: #64748b; }
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
