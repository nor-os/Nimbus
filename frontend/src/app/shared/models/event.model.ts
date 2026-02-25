/**
 * Overview: Event system TypeScript interfaces and types.
 * Architecture: Frontend data models for event bus (Section 11.6)
 * Dependencies: None
 * Concepts: Event types, subscriptions, event log, delivery tracking
 */

export type EventHandlerType = 'INTERNAL' | 'WORKFLOW' | 'NOTIFICATION' | 'ACTIVITY' | 'WEBHOOK';
export type EventDeliveryStatus = 'PENDING' | 'PROCESSING' | 'DELIVERED' | 'FAILED';
export type EventCategory =
  | 'AUTHENTICATION'
  | 'APPROVAL'
  | 'DEPLOYMENT'
  | 'ENVIRONMENT'
  | 'CMDB'
  | 'AUTOMATION'
  | 'WORKFLOW'
  | 'CUSTOM';

export interface EventType {
  id: string;
  tenantId: string | null;
  name: string;
  description: string | null;
  category: string;
  payloadSchema: Record<string, unknown> | null;
  sourceValidators: string[] | null;
  isSystem: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface EventSubscription {
  id: string;
  tenantId: string;
  eventTypeId: string;
  name: string;
  handlerType: EventHandlerType;
  handlerConfig: Record<string, unknown>;
  filterExpression: string | null;
  priority: number;
  isActive: boolean;
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface EventDelivery {
  id: string;
  eventLogId: string;
  subscriptionId: string;
  status: EventDeliveryStatus;
  handlerOutput: Record<string, unknown> | null;
  error: string | null;
  attempts: number;
  startedAt: string | null;
  deliveredAt: string | null;
  createdAt: string;
}

export interface EventLogEntry {
  id: string;
  tenantId: string;
  eventTypeId: string | null;
  eventTypeName: string;
  source: string;
  payload: Record<string, unknown>;
  emittedAt: string;
  emittedBy: string | null;
  traceId: string | null;
  deliveries: EventDelivery[];
}

export interface EventTypeCreateInput {
  name: string;
  description?: string;
  category?: string;
  payloadSchema?: Record<string, unknown>;
  sourceValidators?: string[];
}

export interface EventTypeUpdateInput {
  name?: string;
  description?: string;
  category?: string;
  payloadSchema?: Record<string, unknown>;
  sourceValidators?: string[];
  isActive?: boolean;
}

export interface EventSubscriptionCreateInput {
  eventTypeId: string;
  name: string;
  handlerType: EventHandlerType;
  handlerConfig: Record<string, unknown>;
  filterExpression?: string;
  priority?: number;
  isActive?: boolean;
}

export interface EventSubscriptionUpdateInput {
  name?: string;
  handlerType?: string;
  handlerConfig?: Record<string, unknown>;
  filterExpression?: string;
  priority?: number;
  isActive?: boolean;
}
