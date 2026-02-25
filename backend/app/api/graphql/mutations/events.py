"""
Overview: GraphQL mutations for event type and subscription CRUD, plus test emit.
Architecture: Mutation resolvers for event system (Section 11.6)
Dependencies: strawberry, app.services.events.*, app.api.graphql.auth
Concepts: Event type management, subscription lifecycle, test emission
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.events import (
    EventLogGQL,
    EventSubscriptionCreateInput,
    EventSubscriptionGQL,
    EventSubscriptionUpdateInput,
    EventTypeCreateInput,
    EventTypeGQL,
    EventTypeUpdateInput,
    event_log_to_gql,
    event_type_to_gql,
    subscription_to_gql,
)

logger = logging.getLogger(__name__)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class EventMutation:

    @strawberry.mutation
    async def create_event_type(
        self, info: Info, tenant_id: uuid.UUID, input: EventTypeCreateInput
    ) -> EventTypeGQL:
        """Create a custom event type."""
        await check_graphql_permission(info, "events:type:create", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        et = await svc.create_event_type(str(tenant_id), {
            "name": input.name,
            "description": input.description,
            "category": input.category,
            "payload_schema": input.payload_schema,
            "source_validators": input.source_validators,
        })
        await db.commit()
        await db.refresh(et)
        return event_type_to_gql(et)

    @strawberry.mutation
    async def update_event_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID, input: EventTypeUpdateInput
    ) -> EventTypeGQL:
        """Update a custom event type."""
        await check_graphql_permission(info, "events:type:update", str(tenant_id))

        from app.services.events.event_service import EventService

        data = {}
        for field in ("name", "description", "category", "payload_schema",
                       "source_validators", "is_active"):
            val = getattr(input, field, None)
            if val is not None:
                data[field] = val

        db = await _get_session(info)
        svc = EventService(db)
        et = await svc.update_event_type(str(id), data)
        await db.commit()
        await db.refresh(et)
        return event_type_to_gql(et)

    @strawberry.mutation
    async def delete_event_type(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete a custom event type."""
        await check_graphql_permission(info, "events:type:delete", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        result = await svc.delete_event_type(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def create_event_subscription(
        self, info: Info, tenant_id: uuid.UUID, input: EventSubscriptionCreateInput
    ) -> EventSubscriptionGQL:
        """Create an event subscription."""
        await check_graphql_permission(info, "events:subscription:create", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        sub = await svc.create_subscription(str(tenant_id), {
            "event_type_id": str(input.event_type_id),
            "name": input.name,
            "handler_type": input.handler_type,
            "handler_config": input.handler_config,
            "filter_expression": input.filter_expression,
            "priority": input.priority,
            "is_active": input.is_active,
        })
        await db.commit()
        await db.refresh(sub)
        return subscription_to_gql(sub)

    @strawberry.mutation
    async def update_event_subscription(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID, input: EventSubscriptionUpdateInput
    ) -> EventSubscriptionGQL:
        """Update an event subscription."""
        await check_graphql_permission(info, "events:subscription:update", str(tenant_id))

        from app.services.events.event_service import EventService

        data = {}
        for field in ("name", "handler_type", "handler_config", "filter_expression",
                       "priority", "is_active"):
            val = getattr(input, field, None)
            if val is not None:
                data[field] = val

        db = await _get_session(info)
        svc = EventService(db)
        sub = await svc.update_subscription(str(id), data)
        await db.commit()
        await db.refresh(sub)
        return subscription_to_gql(sub)

    @strawberry.mutation
    async def delete_event_subscription(
        self, info: Info, tenant_id: uuid.UUID, id: uuid.UUID
    ) -> bool:
        """Soft-delete an event subscription."""
        await check_graphql_permission(info, "events:subscription:delete", str(tenant_id))

        from app.services.events.event_service import EventService

        db = await _get_session(info)
        svc = EventService(db)
        result = await svc.delete_subscription(str(id))
        await db.commit()
        return result

    @strawberry.mutation
    async def test_emit_event(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        event_type_name: str,
        payload: strawberry.scalars.JSON,
    ) -> EventLogGQL:
        """Emit a test event for debugging subscriptions."""
        user_id = await check_graphql_permission(info, "events:type:create", str(tenant_id))

        from app.services.events.event_bus import EventBus

        db = await _get_session(info)
        bus = EventBus(db)
        event_log = await bus.emit(
            event_type_name=event_type_name,
            payload=payload,
            tenant_id=str(tenant_id),
            source="test_emit",
            emitted_by=user_id,
        )
        await db.commit()
        await db.refresh(event_log)
        return event_log_to_gql(event_log)
