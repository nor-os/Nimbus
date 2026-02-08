/**
 * Overview: TypeScript interfaces for notification data structures.
 * Architecture: Shared notification type definitions (Section 4)
 * Dependencies: none
 * Concepts: Notifications, preferences, templates, webhooks, delivery status
 */

export type NotificationCategory =
  | 'APPROVAL'
  | 'SECURITY'
  | 'SYSTEM'
  | 'AUDIT'
  | 'DRIFT'
  | 'WORKFLOW'
  | 'USER';

export type NotificationChannel = 'EMAIL' | 'IN_APP' | 'WEBHOOK';

export type WebhookAuthType = 'NONE' | 'API_KEY' | 'BASIC' | 'BEARER';

export type WebhookDeliveryStatus = 'PENDING' | 'DELIVERED' | 'FAILED' | 'DEAD_LETTER';

export interface Notification {
  id: string;
  tenantId: string;
  userId: string;
  category: NotificationCategory;
  eventType: string;
  title: string;
  body: string;
  relatedResourceType: string | null;
  relatedResourceId: string | null;
  isRead: boolean;
  readAt: string | null;
  createdAt: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unreadCount: number;
  offset: number;
  limit: number;
}

export interface NotificationPreference {
  id: string;
  tenantId: string;
  userId: string;
  category: NotificationCategory;
  channel: NotificationChannel;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface NotificationPreferenceUpdate {
  category: NotificationCategory;
  channel: NotificationChannel;
  enabled: boolean;
}

export interface NotificationTemplate {
  id: string;
  tenantId: string | null;
  category: NotificationCategory;
  eventType: string;
  channel: NotificationChannel;
  subjectTemplate: string | null;
  bodyTemplate: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface NotificationTemplateCreate {
  category: NotificationCategory;
  eventType: string;
  channel: NotificationChannel;
  bodyTemplate: string;
  subjectTemplate?: string;
  isActive?: boolean;
}

export interface NotificationTemplateUpdate {
  subjectTemplate?: string;
  bodyTemplate?: string;
  isActive?: boolean;
}

export interface WebhookConfig {
  id: string;
  tenantId: string;
  name: string;
  url: string;
  authType: WebhookAuthType;
  eventFilter: string[] | null;
  batchSize: number;
  batchIntervalSeconds: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface WebhookConfigCreate {
  name: string;
  url: string;
  authType?: WebhookAuthType;
  authConfig?: Record<string, string>;
  eventFilter?: string[];
  batchSize?: number;
  batchIntervalSeconds?: number;
  secret?: string;
  isActive?: boolean;
}

export interface WebhookConfigUpdate {
  name?: string;
  url?: string;
  authType?: WebhookAuthType;
  authConfig?: Record<string, string>;
  eventFilter?: string[];
  batchSize?: number;
  batchIntervalSeconds?: number;
  secret?: string;
  isActive?: boolean;
}

export interface WebhookDelivery {
  id: string;
  tenantId: string;
  webhookConfigId: string;
  payload: Record<string, unknown>;
  status: WebhookDeliveryStatus;
  attempts: number;
  maxAttempts: number;
  lastAttemptAt: string | null;
  lastError: string | null;
  nextRetryAt: string | null;
  createdAt: string;
}

export interface WebhookDeliveryListResponse {
  items: WebhookDelivery[];
  total: number;
  offset: number;
  limit: number;
}

export interface WebhookTestResult {
  success: boolean;
  message: string | null;
  error: string | null;
}
