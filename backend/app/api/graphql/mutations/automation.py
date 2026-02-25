"""
Overview: GraphQL mutations for automated activity CRUD, versioning, and execution.
Architecture: Mutation resolvers for activity catalog (Section 11.5)
Dependencies: strawberry, app.services.automation.*, app.api.graphql.auth
Concepts: Activity lifecycle, version publish, execution orchestration
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.automation import (
    ActivityExecutionType,
    ActivityVersionCreateInput,
    AutomatedActivityCreateInput,
    AutomatedActivityType,
    AutomatedActivityUpdateInput,
    AutomatedActivityVersionType,
    activity_to_type,
    execution_to_type,
    version_to_type,
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
class AutomationMutation:

    @strawberry.mutation
    async def create_automated_activity(
        self, info: Info, tenant_id: uuid.UUID, input: AutomatedActivityCreateInput
    ) -> AutomatedActivityType:
        """Create a new automated activity."""
        user_id = await check_graphql_permission(info, "automation:activity:create", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        activity = await svc.create(
            str(tenant_id),
            user_id,
            {
                "name": input.name,
                "slug": input.slug,
                "description": input.description,
                "category": input.category,
                "semantic_activity_type_id": str(input.semantic_activity_type_id) if input.semantic_activity_type_id else None,
                "semantic_type_id": str(input.semantic_type_id) if input.semantic_type_id else None,
                "provider_id": str(input.provider_id) if input.provider_id else None,
                "operation_kind": input.operation_kind,
                "implementation_type": input.implementation_type,
                "scope": input.scope,
                "idempotent": input.idempotent,
                "timeout_seconds": input.timeout_seconds,
            },
        )
        await db.commit()
        await db.refresh(activity, ["versions"])
        return activity_to_type(activity)

    @strawberry.mutation
    async def update_automated_activity(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID, input: AutomatedActivityUpdateInput
    ) -> AutomatedActivityType:
        """Update an automated activity's metadata."""
        await check_graphql_permission(info, "automation:activity:update", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        data = {}
        for field in ("name", "slug", "description", "category", "operation_kind",
                       "implementation_type", "scope", "idempotent", "timeout_seconds"):
            val = getattr(input, field, None)
            if val is not None:
                data[field] = val
        for fk_field in ("semantic_activity_type_id", "semantic_type_id", "provider_id"):
            val = getattr(input, fk_field, None)
            if val is not None:
                data[fk_field] = str(val)

        db = await _get_session(info)
        svc = ActivityService(db)
        activity = await svc.update(str(tenant_id), str(activity_id), data)
        await db.commit()
        await db.refresh(activity, ["versions"])
        return activity_to_type(activity)

    @strawberry.mutation
    async def delete_automated_activity(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID
    ) -> bool:
        """Soft-delete an automated activity."""
        await check_graphql_permission(info, "automation:activity:delete", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        result = await svc.delete(str(tenant_id), str(activity_id))
        await db.commit()
        return result

    @strawberry.mutation
    async def create_activity_version(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID, input: ActivityVersionCreateInput
    ) -> AutomatedActivityVersionType:
        """Create a new draft version of an activity."""
        await check_graphql_permission(info, "automation:activity:update", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        version = await svc.create_version(
            str(tenant_id),
            str(activity_id),
            {
                "source_code": input.source_code,
                "input_schema": input.input_schema,
                "output_schema": input.output_schema,
                "config_mutations": input.config_mutations,
                "rollback_mutations": input.rollback_mutations,
                "changelog": input.changelog,
                "runtime_config": input.runtime_config,
            },
        )
        await db.commit()
        await db.refresh(version)
        return version_to_type(version)

    @strawberry.mutation
    async def publish_activity_version(
        self, info: Info, tenant_id: uuid.UUID, activity_id: uuid.UUID, version_id: uuid.UUID
    ) -> AutomatedActivityVersionType:
        """Publish a version, making it immutable and available for use."""
        user_id = await check_graphql_permission(info, "automation:activity:publish", str(tenant_id))

        from app.services.automation.activity_service import ActivityService

        db = await _get_session(info)
        svc = ActivityService(db)
        version = await svc.publish_version(
            str(tenant_id), str(activity_id), str(version_id), user_id
        )
        await db.commit()
        await db.refresh(version)
        return version_to_type(version)

    @strawberry.mutation
    async def start_activity_execution(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        activity_id: uuid.UUID,
        version_id: uuid.UUID | None = None,
        ci_id: uuid.UUID | None = None,
        deployment_id: uuid.UUID | None = None,
        input_data: strawberry.scalars.JSON | None = None,
    ) -> ActivityExecutionType:
        """Start executing an activity."""
        user_id = await check_graphql_permission(info, "automation:activity:execute", str(tenant_id))

        from app.services.automation.execution_service import ExecutionService

        db = await _get_session(info)
        svc = ExecutionService(db)
        execution = await svc.start_execution(
            tenant_id=str(tenant_id),
            activity_id=str(activity_id),
            version_id=str(version_id) if version_id else None,
            started_by=user_id,
            input_data=input_data,
            ci_id=str(ci_id) if ci_id else None,
            deployment_id=str(deployment_id) if deployment_id else None,
        )
        await db.commit()
        await db.refresh(execution, ["activity_version", "config_changes"])
        return execution_to_type(execution)

    @strawberry.mutation
    async def cancel_activity_execution(
        self, info: Info, tenant_id: uuid.UUID, execution_id: uuid.UUID
    ) -> ActivityExecutionType:
        """Cancel a running execution."""
        await check_graphql_permission(info, "automation:activity:execute", str(tenant_id))

        from app.services.automation.execution_service import ExecutionService

        db = await _get_session(info)
        svc = ExecutionService(db)
        execution = await svc.cancel_execution(str(tenant_id), str(execution_id))
        await db.commit()
        await db.refresh(execution, ["activity_version", "config_changes"])
        return execution_to_type(execution)

    @strawberry.mutation
    async def rollback_activity_execution(
        self, info: Info, tenant_id: uuid.UUID, execution_id: uuid.UUID
    ) -> ActivityExecutionType:
        """Rollback config mutations from a successful execution."""
        user_id = await check_graphql_permission(info, "automation:activity:execute", str(tenant_id))

        from app.services.automation.execution_service import ExecutionService

        db = await _get_session(info)
        svc = ExecutionService(db)
        execution = await svc.rollback_execution(
            str(tenant_id), str(execution_id), user_id
        )
        await db.commit()
        await db.refresh(execution, ["activity_version", "config_changes"])
        return execution_to_type(execution)

    @strawberry.mutation
    async def link_activity_template(
        self, info: Info, tenant_id: uuid.UUID, template_id: uuid.UUID, activity_id: uuid.UUID
    ) -> bool:
        """Link a CMDB ActivityTemplate to an AutomatedActivity."""
        await check_graphql_permission(info, "automation:activity:update", str(tenant_id))

        from app.models.cmdb import ActivityTemplate
        from sqlalchemy import select

        db = await _get_session(info)
        result = await db.execute(
            select(ActivityTemplate).where(ActivityTemplate.id == str(template_id))
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("ActivityTemplate not found")
        template.automated_activity_id = str(activity_id)
        await db.commit()
        return True

    @strawberry.mutation
    async def unlink_activity_template(
        self, info: Info, tenant_id: uuid.UUID, template_id: uuid.UUID
    ) -> bool:
        """Unlink a CMDB ActivityTemplate from its AutomatedActivity."""
        await check_graphql_permission(info, "automation:activity:update", str(tenant_id))

        from app.models.cmdb import ActivityTemplate
        from sqlalchemy import select

        db = await _get_session(info)
        result = await db.execute(
            select(ActivityTemplate).where(ActivityTemplate.id == str(template_id))
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("ActivityTemplate not found")
        template.automated_activity_id = None
        await db.commit()
        return True
