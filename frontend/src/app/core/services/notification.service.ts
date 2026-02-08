/**
 * Overview: Notification service with signals, polling, and GraphQL API methods.
 * Architecture: Core service layer for notifications (Section 3.2)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Notifications, GraphQL queries, signals, polling, unread count
 */
import { Injectable, inject, signal, OnDestroy } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  Notification,
  NotificationListResponse,
  NotificationPreference,
  NotificationPreferenceUpdate,
  NotificationTemplate,
  NotificationTemplateCreate,
  NotificationTemplateUpdate,
  WebhookConfig,
  WebhookConfigCreate,
  WebhookConfigUpdate,
  WebhookDelivery,
  WebhookDeliveryListResponse,
  WebhookTestResult,
  NotificationCategory,
} from '@shared/models/notification.model';

const POLL_INTERVAL = 30_000; // 30 seconds

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly unreadCount = signal(0);
  readonly notifications = signal<Notification[]>([]);

  startPolling(): void {
    this.stopPolling();
    this.refreshUnreadCount();
    this.pollTimer = setInterval(() => this.refreshUnreadCount(), POLL_INTERVAL);
  }

  stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  refreshUnreadCount(): void {
    const tenantId = this.tenantContext.currentTenantId();
    if (!tenantId) return;

    this.gql<{ unreadNotificationCount: number }>(`
      query UnreadCount($tenantId: UUID!) {
        unreadNotificationCount(tenantId: $tenantId)
      }
    `, { tenantId }).subscribe({
      next: (data) => this.unreadCount.set(data.unreadNotificationCount),
      error: () => {},
    });
  }

  // -- Notification queries --

  listNotifications(
    params: {
      isRead?: boolean;
      category?: NotificationCategory;
      offset?: number;
      limit?: number;
    } = {},
  ): Observable<NotificationListResponse> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ notifications: NotificationListResponse }>(`
      query Notifications(
        $tenantId: UUID!
        $isRead: Boolean
        $category: NotificationCategoryGQL
        $offset: Int
        $limit: Int
      ) {
        notifications(
          tenantId: $tenantId
          isRead: $isRead
          category: $category
          offset: $offset
          limit: $limit
        ) {
          items {
            id tenantId userId category eventType title body
            relatedResourceType relatedResourceId isRead readAt createdAt
          }
          total unreadCount offset limit
        }
      }
    `, { tenantId, ...params }).pipe(
      tap((data) => {
        this.notifications.set(data.notifications.items);
        this.unreadCount.set(data.notifications.unreadCount);
      }),
      map((data) => data.notifications),
    );
  }

  // -- Notification mutations --

  markRead(notificationId: string): Observable<Notification | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ markNotificationRead: Notification | null }>(`
      mutation MarkRead($tenantId: UUID!, $notificationId: UUID!) {
        markNotificationRead(tenantId: $tenantId, notificationId: $notificationId) {
          id isRead readAt
        }
      }
    `, { tenantId, notificationId }).pipe(
      tap(() => this.refreshUnreadCount()),
      map((data) => data.markNotificationRead),
    );
  }

  markAllRead(): Observable<number> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ markAllNotificationsRead: number }>(`
      mutation MarkAllRead($tenantId: UUID!) {
        markAllNotificationsRead(tenantId: $tenantId)
      }
    `, { tenantId }).pipe(
      tap(() => this.unreadCount.set(0)),
      map((data) => data.markAllNotificationsRead),
    );
  }

  deleteNotification(notificationId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteNotification: boolean }>(`
      mutation DeleteNotification($tenantId: UUID!, $notificationId: UUID!) {
        deleteNotification(tenantId: $tenantId, notificationId: $notificationId)
      }
    `, { tenantId, notificationId }).pipe(
      map((data) => data.deleteNotification),
    );
  }

  // -- Preferences --

  getPreferences(): Observable<NotificationPreference[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ notificationPreferences: NotificationPreference[] }>(`
      query Preferences($tenantId: UUID!) {
        notificationPreferences(tenantId: $tenantId) {
          id tenantId userId category channel enabled createdAt updatedAt
        }
      }
    `, { tenantId }).pipe(map((d) => d.notificationPreferences));
  }

  updatePreferences(
    updates: NotificationPreferenceUpdate[],
  ): Observable<NotificationPreference[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateNotificationPreferences: NotificationPreference[] }>(`
      mutation UpdatePreferences(
        $tenantId: UUID!
        $updates: [NotificationPreferenceUpdateInput!]!
      ) {
        updateNotificationPreferences(tenantId: $tenantId, updates: $updates) {
          id tenantId userId category channel enabled createdAt updatedAt
        }
      }
    `, { tenantId, updates }).pipe(map((d) => d.updateNotificationPreferences));
  }

  // -- Templates --

  getTemplates(): Observable<NotificationTemplate[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ notificationTemplates: NotificationTemplate[] }>(`
      query Templates($tenantId: UUID!) {
        notificationTemplates(tenantId: $tenantId) {
          id tenantId category eventType channel
          subjectTemplate bodyTemplate isActive createdAt updatedAt
        }
      }
    `, { tenantId }).pipe(map((d) => d.notificationTemplates));
  }

  createTemplate(input: NotificationTemplateCreate): Observable<NotificationTemplate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createNotificationTemplate: NotificationTemplate }>(`
      mutation CreateTemplate(
        $tenantId: UUID!
        $input: NotificationTemplateCreateInput!
      ) {
        createNotificationTemplate(tenantId: $tenantId, input: $input) {
          id tenantId category eventType channel
          subjectTemplate bodyTemplate isActive createdAt updatedAt
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createNotificationTemplate));
  }

  updateTemplate(
    templateId: string,
    input: NotificationTemplateUpdate,
  ): Observable<NotificationTemplate | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateNotificationTemplate: NotificationTemplate | null }>(`
      mutation UpdateTemplate(
        $tenantId: UUID!
        $templateId: UUID!
        $input: NotificationTemplateUpdateInput!
      ) {
        updateNotificationTemplate(
          tenantId: $tenantId
          templateId: $templateId
          input: $input
        ) {
          id tenantId category eventType channel
          subjectTemplate bodyTemplate isActive createdAt updatedAt
        }
      }
    `, { tenantId, templateId, input }).pipe(map((d) => d.updateNotificationTemplate));
  }

  deleteTemplate(templateId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteNotificationTemplate: boolean }>(`
      mutation DeleteTemplate($tenantId: UUID!, $templateId: UUID!) {
        deleteNotificationTemplate(tenantId: $tenantId, templateId: $templateId)
      }
    `, { tenantId, templateId }).pipe(map((d) => d.deleteNotificationTemplate));
  }

  // -- Webhooks --

  getWebhookConfigs(): Observable<WebhookConfig[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ webhookConfigs: WebhookConfig[] }>(`
      query WebhookConfigs($tenantId: UUID!) {
        webhookConfigs(tenantId: $tenantId) {
          id tenantId name url authType eventFilter
          batchSize batchIntervalSeconds isActive createdAt updatedAt
        }
      }
    `, { tenantId }).pipe(map((d) => d.webhookConfigs));
  }

  createWebhookConfig(input: WebhookConfigCreate): Observable<WebhookConfig> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createWebhookConfig: WebhookConfig }>(`
      mutation CreateWebhook($tenantId: UUID!, $input: WebhookConfigCreateInput!) {
        createWebhookConfig(tenantId: $tenantId, input: $input) {
          id tenantId name url authType eventFilter
          batchSize batchIntervalSeconds isActive createdAt updatedAt
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createWebhookConfig));
  }

  updateWebhookConfig(
    configId: string,
    input: WebhookConfigUpdate,
  ): Observable<WebhookConfig | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateWebhookConfig: WebhookConfig | null }>(`
      mutation UpdateWebhook(
        $tenantId: UUID!
        $configId: UUID!
        $input: WebhookConfigUpdateInput!
      ) {
        updateWebhookConfig(tenantId: $tenantId, configId: $configId, input: $input) {
          id tenantId name url authType eventFilter
          batchSize batchIntervalSeconds isActive createdAt updatedAt
        }
      }
    `, { tenantId, configId, input }).pipe(map((d) => d.updateWebhookConfig));
  }

  deleteWebhookConfig(configId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteWebhookConfig: boolean }>(`
      mutation DeleteWebhook($tenantId: UUID!, $configId: UUID!) {
        deleteWebhookConfig(tenantId: $tenantId, configId: $configId)
      }
    `, { tenantId, configId }).pipe(map((d) => d.deleteWebhookConfig));
  }

  testWebhook(configId: string): Observable<WebhookTestResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ testWebhook: WebhookTestResult }>(`
      mutation TestWebhook($tenantId: UUID!, $configId: UUID!) {
        testWebhook(tenantId: $tenantId, configId: $configId) {
          success message error
        }
      }
    `, { tenantId, configId }).pipe(map((d) => d.testWebhook));
  }

  // -- Webhook deliveries --

  getDeliveries(
    configId?: string,
    status?: string,
    offset = 0,
    limit = 50,
  ): Observable<WebhookDeliveryListResponse> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ webhookDeliveries: WebhookDeliveryListResponse }>(`
      query Deliveries(
        $tenantId: UUID!
        $configId: UUID
        $status: WebhookDeliveryStatusGQL
        $offset: Int
        $limit: Int
      ) {
        webhookDeliveries(
          tenantId: $tenantId
          configId: $configId
          status: $status
          offset: $offset
          limit: $limit
        ) {
          items {
            id tenantId webhookConfigId payload status attempts maxAttempts
            lastAttemptAt lastError nextRetryAt createdAt
          }
          total offset limit
        }
      }
    `, { tenantId, configId, status, offset, limit }).pipe(
      map((d) => d.webhookDeliveries),
    );
  }

  retryDelivery(deliveryId: string): Observable<WebhookDelivery | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ retryWebhookDelivery: WebhookDelivery | null }>(`
      mutation RetryDelivery($tenantId: UUID!, $deliveryId: UUID!) {
        retryWebhookDelivery(tenantId: $tenantId, deliveryId: $deliveryId) {
          id status attempts nextRetryAt
        }
      }
    `, { tenantId, deliveryId }).pipe(map((d) => d.retryWebhookDelivery));
  }

  // -- GraphQL helper --

  private gql<T>(
    query: string,
    variables: Record<string, unknown> = {},
  ): Observable<T> {
    return this.api
      .post<{ data: T; errors?: Array<{ message: string }> }>(this.gqlUrl, {
        query,
        variables,
      })
      .pipe(
        map((response) => {
          if (response.errors?.length) {
            throw new Error(response.errors[0].message);
          }
          return response.data;
        }),
      );
  }
}
