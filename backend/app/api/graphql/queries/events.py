"""
Overview: GraphQL queries for event types, subscriptions, and event log.
Architecture: Query resolvers for event system (Section 11.6)
Dependencies: strawberry, app.services.events.event_service, app.api.graphql.auth
Concepts: Event queries, subscription listing, event log search
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.events import (
    EventLogGQL,
    EventSubscriptionGQL,
    EventTypeGQL,
    event_log_to_gql,
    event_type_to_gql,
    subscription_to_gql,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class EventQuery:

    @strawberry.field
    async def event_types(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
        search: str | None = None,
    ) -> list[EventTypeGQL]:
        """List event types — system + tenant custom."""
        await check_graphql_permission(info, "events:type:read", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        types = await svc.list_event_types(
            tenant_id=str(tenant_id), category=category, search=search
        )
        return [event_type_to_gql(et) for et in types]

    @strawberry.field
    async def event_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> EventTypeGQL | None:
        """Get a single event type by ID."""
        await check_graphql_permission(info, "events:type:read", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        et = await svc.get_event_type(str(id))
        return event_type_to_gql(et) if et else None

    @strawberry.field
    async def event_subscriptions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        event_type_id: uuid.UUID | None = None,
    ) -> list[EventSubscriptionGQL]:
        """List event subscriptions for a tenant."""
        await check_graphql_permission(info, "events:subscription:read", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        subs = await svc.list_subscriptions(
            tenant_id=str(tenant_id),
            event_type_id=str(event_type_id) if event_type_id else None,
        )
        return [subscription_to_gql(s) for s in subs]

    @strawberry.field
    async def event_log(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        event_type_name: str | None = None,
        source: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[EventLogGQL]:
        """List event log entries for a tenant."""
        await check_graphql_permission(info, "events:log:read", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        entries = await svc.list_event_log(
            tenant_id=str(tenant_id),
            event_type_name=event_type_name,
            source=source,
            offset=offset,
            limit=limit,
        )
        return [event_log_to_gql(e) for e in entries]

    @strawberry.field
    async def event_log_entry(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> EventLogGQL | None:
        """Get a single event log entry with deliveries."""
        await check_graphql_permission(info, "events:log:read", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        entry = await svc.get_event_log_entry(str(id))
        return event_log_to_gql(entry, include_deliveries=True) if entry else None
