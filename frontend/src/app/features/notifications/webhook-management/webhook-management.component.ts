/**
 * Overview: Webhook configuration CRUD with test functionality.
 * Architecture: Feature component at /settings/webhooks (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/notification.service
 * Concepts: Webhook management, CRUD, config testing, event filtering
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { NotificationService } from '@core/services/notification.service';
import {
  WebhookConfig,
  WebhookConfigCreate,
  WebhookAuthType,
  WebhookTestResult,
} from '@shared/models/notification.model';

const AUTH_TYPES: WebhookAuthType[] = ['NONE', 'API_KEY', 'BASIC', 'BEARER'];

@Component({
  selector: 'nimbus-webhook-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">Webhooks</h1>
        <button class="btn btn-primary" (click)="showCreateForm()">
          + Add Webhook
        </button>
      </div>
      <p class="page-description">
        Configure webhook endpoints to receive notification events via HTTP POST.
      </p>

      @if (creating()) {
        <div class="form-card">
          <h2 class="form-title">
            {{ editing() ? 'Edit Webhook' : 'New Webhook' }}
          </h2>
          <div class="form-group">
            <label class="form-label">Name</label>
            <input
              class="form-input"
              [(ngModel)]="formName"
              placeholder="e.g. Slack alerts"
            />
          </div>
          <div class="form-group">
            <label class="form-label">URL</label>
            <input
              class="form-input"
              [(ngModel)]="formUrl"
              placeholder="https://..."
            />
          </div>
          <div class="form-group">
            <label class="form-label">Auth Type</label>
            <select class="form-select" [(ngModel)]="formAuthType">
              @for (t of authTypes; track t) {
                <option [value]="t">{{ t }}</option>
              }
            </select>
          </div>

          @if (formAuthType === 'API_KEY') {
            <div class="form-group">
              <label class="form-label">API Key Header</label>
              <input
                class="form-input"
                [(ngModel)]="formAuthHeader"
                placeholder="X-API-Key"
              />
            </div>
            <div class="form-group">
              <label class="form-label">API Key Value</label>
              <input
                class="form-input"
                type="password"
                [(ngModel)]="formAuthValue"
                placeholder="secret"
              />
            </div>
          }
          @if (formAuthType === 'BASIC') {
            <div class="form-group">
              <label class="form-label">Username</label>
              <input
                class="form-input"
                [(ngModel)]="formAuthHeader"
                placeholder="username"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Password</label>
              <input
                class="form-input"
                type="password"
                [(ngModel)]="formAuthValue"
                placeholder="password"
              />
            </div>
          }
          @if (formAuthType === 'BEARER') {
            <div class="form-group">
              <label class="form-label">Bearer Token</label>
              <input
                class="form-input"
                type="password"
                [(ngModel)]="formAuthValue"
                placeholder="token"
              />
            </div>
          }

          <div class="form-group">
            <label class="form-label">Event Filter (optional, comma-separated categories)</label>
            <input
              class="form-input"
              [(ngModel)]="formEventFilter"
              placeholder="APPROVAL,SECURITY"
            />
          </div>
          <div class="form-row">
            <div class="form-group half">
              <label class="form-label">Batch Size</label>
              <input
                class="form-input"
                type="number"
                [(ngModel)]="formBatchSize"
                min="1"
                max="100"
              />
            </div>
            <div class="form-group half">
              <label class="form-label">Batch Interval (seconds)</label>
              <input
                class="form-input"
                type="number"
                [(ngModel)]="formBatchInterval"
                min="0"
              />
            </div>
          </div>

          <div class="form-actions">
            <button class="btn btn-secondary" (click)="cancelForm()">Cancel</button>
            <button class="btn btn-primary" (click)="saveWebhook()">
              {{ editing() ? 'Update' : 'Create' }}
            </button>
          </div>
        </div>
      }

      <div class="webhook-list">
        @if (loading()) {
          <div class="loading">Loading...</div>
        }
        @if (!loading() && webhooks().length === 0 && !creating()) {
          <div class="empty">No webhooks configured.</div>
        }
        @for (wh of webhooks(); track wh.id) {
          <div class="webhook-card" [class.inactive]="!wh.isActive">
            <div class="webhook-info">
              <div class="webhook-name">
                {{ wh.name }}
                @if (!wh.isActive) {
                  <span class="badge-inactive">Inactive</span>
                }
              </div>
              <div class="webhook-url">{{ wh.url }}</div>
              <div class="webhook-meta">
                <span class="meta-item">Auth: {{ wh.authType }}</span>
                @if (wh.batchSize > 1) {
                  <span class="meta-item">Batch: {{ wh.batchSize }}</span>
                }
              </div>
            </div>
            <div class="webhook-actions">
              <button class="btn-small" (click)="testWebhook(wh)" title="Test">
                &#9889;
              </button>
              <button class="btn-small" (click)="viewDeliveries(wh)" title="Deliveries">
                &#9776;
              </button>
              <button class="btn-small" (click)="editWebhook(wh)" title="Edit">
                &#9998;
              </button>
              <button
                class="btn-small"
                (click)="toggleActive(wh)"
                [title]="wh.isActive ? 'Deactivate' : 'Activate'"
              >
                {{ wh.isActive ? '&#10006;' : '&#10004;' }}
              </button>
              <button
                class="btn-small btn-danger"
                (click)="deleteWebhook(wh)"
                title="Delete"
              >
                &#128465;
              </button>
            </div>
          </div>
        }
      </div>

      @if (testResult()) {
        <div class="test-result" [class.success]="testResult()!.success">
          <strong>Test {{ testResult()!.success ? 'passed' : 'failed' }}:</strong>
          {{ testResult()!.message || testResult()!.error }}
        </div>
      }
    </div>
  `,
  styles: [`
    .page { padding: 1.5rem; max-width: 56rem; }
    .page-header {
      display: flex; justify-content: space-between;
      align-items: center; margin-bottom: 0.5rem;
    }
    .page-title { font-size: 1.25rem; font-weight: 700; color: #e0e0e0; margin: 0; }
    .page-description { font-size: 0.75rem; color: #9ca3af; margin-bottom: 1rem; }
    .form-card {
      background: #1e2433; border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;
    }
    .form-title { font-size: 0.9375rem; font-weight: 600; color: #e0e0e0; margin: 0 0 1rem; }
    .form-group { margin-bottom: 0.75rem; }
    .form-label { display: block; font-size: 0.6875rem; color: #9ca3af; margin-bottom: 0.25rem; }
    .form-input, .form-select {
      width: 100%; padding: 0.5rem 0.75rem; background: #161b26; color: #e0e0e0;
      border: 1px solid rgba(255,255,255,0.1); border-radius: 4px;
      font-size: 0.8125rem; box-sizing: border-box;
    }
    .form-row { display: flex; gap: 0.75rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; }
    .webhook-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .webhook-card {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 1rem; background: #1e2433; border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .webhook-card.inactive { opacity: 0.6; }
    .webhook-info { flex: 1; min-width: 0; }
    .webhook-name { font-size: 0.875rem; font-weight: 600; color: #e0e0e0; }
    .badge-inactive {
      margin-left: 0.5rem; padding: 0.0625rem 0.375rem;
      background: rgba(239,68,68,0.15); color: #f87171;
      font-size: 0.625rem; font-weight: 600; border-radius: 3px;
    }
    .webhook-url {
      font-size: 0.75rem; color: #9ca3af; margin-top: 0.125rem;
      word-break: break-all;
    }
    .webhook-meta { display: flex; gap: 0.75rem; margin-top: 0.375rem; }
    .meta-item { font-size: 0.6875rem; color: #64748b; }
    .webhook-actions { display: flex; gap: 0.25rem; flex-shrink: 0; margin-left: 0.75rem; }
    .btn-small {
      width: 1.75rem; height: 1.75rem; display: flex;
      align-items: center; justify-content: center;
      background: none; border: 1px solid rgba(255,255,255,0.1);
      color: #9ca3af; border-radius: 3px; cursor: pointer; font-size: 0.75rem;
    }
    .btn-small:hover { background: rgba(255,255,255,0.06); color: #e0e0e0; }
    .btn-small.btn-danger:hover { color: #ef4444; }
    .btn {
      padding: 0.375rem 0.75rem; border-radius: 4px;
      font-size: 0.75rem; cursor: pointer; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: rgba(255,255,255,0.08); color: #e0e0e0; }
    .btn-secondary:hover { background: rgba(255,255,255,0.12); }
    .loading, .empty {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }
    .test-result {
      margin-top: 0.75rem; padding: 0.625rem 1rem;
      border-radius: 4px; font-size: 0.75rem;
      background: rgba(239,68,68,0.1); color: #f87171;
      border: 1px solid rgba(239,68,68,0.2);
    }
    .test-result.success {
      background: rgba(34,197,94,0.1); color: #22c55e;
      border-color: rgba(34,197,94,0.2);
    }
  `],
})
export class WebhookManagementComponent implements OnInit {
  private notificationService = inject(NotificationService);
  private router = inject(Router);

  webhooks = signal<WebhookConfig[]>([]);
  loading = signal(false);
  creating = signal(false);
  editing = signal(false);
  testResult = signal<WebhookTestResult | null>(null);

  authTypes = AUTH_TYPES;

  formName = '';
  formUrl = '';
  formAuthType: WebhookAuthType = 'NONE';
  formAuthHeader = '';
  formAuthValue = '';
  formEventFilter = '';
  formBatchSize = 1;
  formBatchInterval = 0;
  private editingId: string | null = null;

  ngOnInit(): void {
    this.loadWebhooks();
  }

  showCreateForm(): void {
    this.resetForm();
    this.creating.set(true);
    this.editing.set(false);
  }

  editWebhook(wh: WebhookConfig): void {
    this.editingId = wh.id;
    this.formName = wh.name;
    this.formUrl = wh.url;
    this.formAuthType = wh.authType;
    this.formAuthHeader = '';
    this.formAuthValue = '';
    this.formEventFilter = wh.eventFilter ? wh.eventFilter.join(',') : '';
    this.formBatchSize = wh.batchSize;
    this.formBatchInterval = wh.batchIntervalSeconds;
    this.creating.set(true);
    this.editing.set(true);
  }

  cancelForm(): void {
    this.creating.set(false);
    this.editing.set(false);
    this.resetForm();
  }

  saveWebhook(): void {
    const authConfig = this.buildAuthConfig();
    const eventFilter = this.formEventFilter.trim()
      ? this.formEventFilter.split(',').map((s) => s.trim().toUpperCase())
      : undefined;

    if (this.editing() && this.editingId) {
      this.notificationService
        .updateWebhookConfig(this.editingId, {
          name: this.formName,
          url: this.formUrl,
          authType: this.formAuthType,
          authConfig,
          eventFilter,
          batchSize: this.formBatchSize,
          batchIntervalSeconds: this.formBatchInterval,
        })
        .subscribe((updated) => {
          if (updated) {
            this.webhooks.update((items) =>
              items.map((w) => (w.id === updated.id ? updated : w)),
            );
          }
          this.cancelForm();
        });
    } else {
      const input: WebhookConfigCreate = {
        name: this.formName,
        url: this.formUrl,
        authType: this.formAuthType,
        authConfig,
        eventFilter,
        batchSize: this.formBatchSize,
        batchIntervalSeconds: this.formBatchInterval,
      };
      this.notificationService.createWebhookConfig(input).subscribe((wh) => {
        this.webhooks.update((items) => [...items, wh]);
        this.cancelForm();
      });
    }
  }

  deleteWebhook(wh: WebhookConfig): void {
    this.notificationService.deleteWebhookConfig(wh.id).subscribe((deleted) => {
      if (deleted) {
        this.webhooks.update((items) => items.filter((w) => w.id !== wh.id));
      }
    });
  }

  toggleActive(wh: WebhookConfig): void {
    this.notificationService
      .updateWebhookConfig(wh.id, { isActive: !wh.isActive })
      .subscribe((updated) => {
        if (updated) {
          this.webhooks.update((items) =>
            items.map((w) => (w.id === updated.id ? updated : w)),
          );
        }
      });
  }

  testWebhook(wh: WebhookConfig): void {
    this.testResult.set(null);
    this.notificationService.testWebhook(wh.id).subscribe({
      next: (result) => this.testResult.set(result),
      error: () =>
        this.testResult.set({ success: false, message: null, error: 'Test request failed' }),
    });
  }

  viewDeliveries(wh: WebhookConfig): void {
    this.router.navigate(['/settings/webhooks', wh.id]);
  }

  private loadWebhooks(): void {
    this.loading.set(true);
    this.notificationService.getWebhookConfigs().subscribe({
      next: (configs) => {
        this.webhooks.set(configs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private resetForm(): void {
    this.editingId = null;
    this.formName = '';
    this.formUrl = '';
    this.formAuthType = 'NONE';
    this.formAuthHeader = '';
    this.formAuthValue = '';
    this.formEventFilter = '';
    this.formBatchSize = 1;
    this.formBatchInterval = 0;
  }

  private buildAuthConfig(): Record<string, string> | undefined {
    switch (this.formAuthType) {
      case 'API_KEY':
        return { header: this.formAuthHeader, value: this.formAuthValue };
      case 'BASIC':
        return { username: this.formAuthHeader, password: this.formAuthValue };
      case 'BEARER':
        return { token: this.formAuthValue };
      default:
        return undefined;
    }
  }
}
