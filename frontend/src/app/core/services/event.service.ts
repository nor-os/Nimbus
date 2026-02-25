/**
 * Overview: Event service — GraphQL queries and mutations for event types, subscriptions, and log.
 * Architecture: Core service layer for event system (Section 11.6)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Event CRUD, subscription management, event log querying, test emission
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  EventType,
  EventSubscription,
  EventLogEntry,
  EventTypeCreateInput,
  EventTypeUpdateInput,
  EventSubscriptionCreateInput,
  EventSubscriptionUpdateInput,
} from '@shared/models/event.model';

const EVENT_TYPE_FIELDS = `
  id tenantId name description category
  payloadSchema sourceValidators isSystem isActive
  createdAt updatedAt
`;

const SUBSCRIPTION_FIELDS = `
  id tenantId eventTypeId name handlerType handlerConfig
  filterExpression priority isActive isSystem
  createdAt updatedAt
`;

const DELIVERY_FIELDS = `
  id eventLogId subscriptionId status handlerOutput
  error attempts startedAt deliveredAt createdAt
`;

const EVENT_LOG_FIELDS = `
  id tenantId eventTypeId eventTypeName source payload
  emittedAt emittedBy traceId
`;

@Injectable({ providedIn: 'root' })
export class EventService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // -- Event Type queries/mutations ------------------------------------------

  listEventTypes(options?: {
    category?: string;
    search?: string;
  }): Observable<EventType[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ eventTypes: EventType[] }>(`
      query EventTypes($tenantId: UUID!, $category: String, $search: String) {
        eventTypes(tenantId: $tenantId, category: $category, search: $search) {
          ${EVENT_TYPE_FIELDS}
        }
      }
    `, { tenantId, ...options }).pipe(
      map((data) => data.eventTypes),
    );
  }

  getEventType(id: string): Observable<EventType | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ eventType: EventType | null }>(`
      query EventType($tenantId: UUID!, $id: UUID!) {
        eventType(tenantId: $tenantId, id: $id) {
          ${EVENT_TYPE_FIELDS}
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.eventType),
    );
  }

  createEventType(input: EventTypeCreateInput): Observable<EventType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEventType: EventType }>(`
      mutation CreateEventType($tenantId: UUID!, $input: EventTypeCreateInput!) {
        createEventType(tenantId: $tenantId, input: $input) {
          ${EVENT_TYPE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((data) => data.createEventType),
    );
  }

  updateEventType(id: string, input: EventTypeUpdateInput): Observable<EventType> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateEventType: EventType }>(`
      mutation UpdateEventType($tenantId: UUID!, $id: UUID!, $input: EventTypeUpdateInput!) {
        updateEventType(tenantId: $tenantId, id: $id, input: $input) {
          ${EVENT_TYPE_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(
      map((data) => data.updateEventType),
    );
  }

  deleteEventType(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEventType: boolean }>(`
      mutation DeleteEventType($tenantId: UUID!, $id: UUID!) {
        deleteEventType(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(
      map((data) => data.deleteEventType),
    );
  }

  // -- Subscription queries/mutations ----------------------------------------

  listSubscriptions(eventTypeId?: string): Observable<EventSubscription[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ eventSubscriptions: EventSubscription[] }>(`
      query EventSubscriptions($tenantId: UUID!, $eventTypeId: UUID) {
        eventSubscriptions(tenantId: $tenantId, eventTypeId: $eventTypeId) {
          ${SUBSCRIPTION_FIELDS}
        }
      }
    `, { tenantId, eventTypeId }).pipe(
      map((data) => data.eventSubscriptions),
    );
  }

  createSubscription(input: EventSubscriptionCreateInput): Observable<EventSubscription> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createEventSubscription: EventSubscription }>(`
      mutation CreateEventSubscription($tenantId: UUID!, $input: EventSubscriptionCreateInput!) {
        createEventSubscription(tenantId: $tenantId, input: $input) {
          ${SUBSCRIPTION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((data) => data.createEventSubscription),
    );
  }

  updateSubscription(id: string, input: EventSubscriptionUpdateInput): Observable<EventSubscription> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateEventSubscription: EventSubscription }>(`
      mutation UpdateEventSubscription($tenantId: UUID!, $id: UUID!, $input: EventSubscriptionUpdateInput!) {
        updateEventSubscription(tenantId: $tenantId, id: $id, input: $input) {
          ${SUBSCRIPTION_FIELDS}
        }
      }
    `, { tenantId, id, input }).pipe(
      map((data) => data.updateEventSubscription),
    );
  }

  deleteSubscription(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteEventSubscription: boolean }>(`
      mutation DeleteEventSubscription($tenantId: UUID!, $id: UUID!) {
        deleteEventSubscription(tenantId: $tenantId, id: $id)
      }
    `, { tenantId, id }).pipe(
      map((data) => data.deleteEventSubscription),
    );
  }

  // -- Event Log queries -----------------------------------------------------

  listEventLog(options?: {
    eventTypeName?: string;
    source?: string;
    offset?: number;
    limit?: number;
  }): Observable<EventLogEntry[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ eventLog: EventLogEntry[] }>(`
      query EventLog(
        $tenantId: UUID!
        $eventTypeName: String
        $source: String
        $offset: Int
        $limit: Int
      ) {
        eventLog(
          tenantId: $tenantId
          eventTypeName: $eventTypeName
          source: $source
          offset: $offset
          limit: $limit
        ) {
          ${EVENT_LOG_FIELDS}
        }
      }
    `, { tenantId, ...options }).pipe(
      map((data) => data.eventLog),
    );
  }

  getEventLogEntry(id: string): Observable<EventLogEntry | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ eventLogEntry: EventLogEntry | null }>(`
      query EventLogEntry($tenantId: UUID!, $id: UUID!) {
        eventLogEntry(tenantId: $tenantId, id: $id) {
          ${EVENT_LOG_FIELDS}
          deliveries { ${DELIVERY_FIELDS} }
        }
      }
    `, { tenantId, id }).pipe(
      map((data) => data.eventLogEntry),
    );
  }

  // -- Test emit -------------------------------------------------------------

  testEmitEvent(eventTypeName: string, payload: Record<string, unknown>): Observable<EventLogEntry> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ testEmitEvent: EventLogEntry }>(`
      mutation TestEmitEvent($tenantId: UUID!, $eventTypeName: String!, $payload: JSON!) {
        testEmitEvent(tenantId: $tenantId, eventTypeName: $eventTypeName, payload: $payload) {
          ${EVENT_LOG_FIELDS}
        }
      }
    `, { tenantId, eventTypeName, payload }).pipe(
      map((data) => data.testEmitEvent),
    );
  }

  // -- GraphQL helper --------------------------------------------------------

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
