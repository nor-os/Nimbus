"""
Overview: GraphQL queries for automated activities, versions, executions, and config changes.
Architecture: Query resolvers for activity catalog (Section 11.5)
Dependencies: strawberry, app.services.automation.*, app.api.graphql.auth
Concepts: Activity queries, version listing, execution monitoring, config change history
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.automation import (
    ActivityExecutionType,
    AutomatedActivityType,
    AutomatedActivityVersionType,
    ConfigurationChangeType,
    activity_summary_to_type,
    activity_to_type,
    config_change_to_type,
    execution_to_type,
    version_to_type,
)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class AutomationQuery:

    @strawberry.field
    async def automated_activities(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        category: str | None = None,
        operation_kind: str | None = None,
        provider_id: uuid.UUID | None = None,
        scope: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AutomatedActivityType]:
        """List automated activities for a tenant."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        activities = await svc.list(
            str(tenant_id),
            category=category,
            operation_kind=operation_kind,
            provider_id=str(provider_id) if provider_id else None,
            scope=scope,
            search=search,
            offset=offset,
            limit=limit,
        )
        return [activity_summary_to_type(a) for a in activities]

    @strawberry.field
    async def automated_activity(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID
    ) -> AutomatedActivityType | None:
        """Get an automated activity by ID with versions."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        a = await svc.get(str(tenant_id), str(activity_id))
        return activity_to_type(a) if a else None

    @strawberry.field
    async def automated_activity_versions(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID
    ) -> list[AutomatedActivityVersionType]:
        """List all versions of an activity."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        versions = await svc.list_versions(str(activity_id))
        return [version_to_type(v) for v in versions]

    @strawberry.field
    async def activity_executions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        activity_id: uuid.UUID | None = None,
        status: str | None = None,
        deployment_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ActivityExecutionType]:
        """List activity executions."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.services.automation.execution_service import ExecutionService

        db = await _get_session(info)
        svc = ExecutionService(db)
        executions = await svc.list(
            str(tenant_id),
            activity_id=str(activity_id) if activity_id else None,
            status=status,
            deployment_id=str(deployment_id) if deployment_id else None,
            offset=offset,
            limit=limit,
        )
        return [execution_to_type(e) for e in executions]

    @strawberry.field
    async def activity_execution(
        self, info: Info, tenant_id: uuid.UUID, execution_id: uuid.UUID
    ) -> ActivityExecutionType | None:
        """Get a single activity execution with config changes."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.services.automation.execution_service import ExecutionService

        db = await _get_session(info)
        svc = ExecutionService(db)
        e = await svc.get(str(tenant_id), str(execution_id))
        return execution_to_type(e) if e else None

    @strawberry.field
    async def configuration_changes(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        deployment_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ConfigurationChangeType]:
        """List configuration changes for a deployment."""
        await check_graphql_permission(info, "automation:activity:read", str(tenant_id))

        from app.models.automated_activity import ConfigurationChange
        from sqlalchemy import select

        db = await _get_session(info)
        result = await db.execute(
            select(ConfigurationChange)
            .where(
                ConfigurationChange.tenant_id == str(tenant_id),
                ConfigurationChange.deployment_id == str(deployment_id),
            )
            .order_by(ConfigurationChange.version.desc())
            .offset(offset)
            .limit(limit)
        )
        return [config_change_to_type(c) for c in result.scalars().all()]
