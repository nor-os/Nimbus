"""
Overview: GraphQL mutations for audit retention, redaction rules, saved queries, and exports.
Architecture: GraphQL mutation resolvers (Section 7.2)
Dependencies: strawberry, app.services.audit
Concepts: Audit configuration, data lifecycle, export management
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.audit import (
    CategoryRetentionOverrideInput,
    CategoryRetentionOverrideType,
    EventCategoryGQL,
    ExportRequestInput,
    ExportStatusType,
    RedactionRuleCreateInput,
    RedactionRuleType,
    RedactionRuleUpdateInput,
    RetentionPolicyInput,
    RetentionPolicyType,
    SavedQueryCreateInput,
    SavedQueryType,
)

logger = logging.getLogger(__name__)


@strawberry.type
class AuditMutation:
    @strawberry.mutation
    async def update_retention_policy(
        self, info: Info, tenant_id: uuid.UUID, input: RetentionPolicyInput
    ) -> RetentionPolicyType:
        """Update the retention policy for a tenant."""
        await check_graphql_permission(info, "audit:retention:update", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.retention import RetentionService

        async with async_session_factory() as db:
            service = RetentionService(db)
            policy = await service.update_policy(
                str(tenant_id),
                hot_days=input.hot_days,
                cold_days=input.cold_days,
                archive_enabled=input.archive_enabled,
            )
            overrides = await service.list_category_overrides(str(tenant_id))
            await db.commit()
            return RetentionPolicyType(
                id=policy.id,
                tenant_id=policy.tenant_id,
                hot_days=policy.hot_days,
                cold_days=policy.cold_days,
                archive_enabled=policy.archive_enabled,
                category_overrides=[
                    CategoryRetentionOverrideType(
                        id=ov.id,
                        tenant_id=ov.tenant_id,
                        event_category=EventCategoryGQL(ov.event_category.value),
                        hot_days=ov.hot_days,
                        cold_days=ov.cold_days,
                        created_at=ov.created_at,
                        updated_at=ov.updated_at,
                    )
                    for ov in overrides
                ],
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )

    @strawberry.mutation
    async def upsert_category_retention_override(
        self, info: Info, tenant_id: uuid.UUID, input: CategoryRetentionOverrideInput
    ) -> CategoryRetentionOverrideType:
        """Create or update a per-category retention override."""
        await check_graphql_permission(info, "audit:retention:update", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.retention import RetentionService

        async with async_session_factory() as db:
            service = RetentionService(db)
            override = await service.upsert_category_override(
                str(tenant_id),
                event_category=input.event_category.value,
                hot_days=input.hot_days,
                cold_days=input.cold_days,
            )
            await db.commit()
            return CategoryRetentionOverrideType(
                id=override.id,
                tenant_id=override.tenant_id,
                event_category=EventCategoryGQL(override.event_category.value),
                hot_days=override.hot_days,
                cold_days=override.cold_days,
                created_at=override.created_at,
                updated_at=override.updated_at,
            )

    @strawberry.mutation
    async def delete_category_retention_override(
        self, info: Info, tenant_id: uuid.UUID, event_category: EventCategoryGQL
    ) -> bool:
        """Delete a per-category retention override (reverts to global default)."""
        await check_graphql_permission(info, "audit:retention:update", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.retention import RetentionService

        async with async_session_factory() as db:
            service = RetentionService(db)
            deleted = await service.delete_category_override(
                str(tenant_id), event_category.value
            )
            await db.commit()
            return deleted

    @strawberry.mutation
    async def create_redaction_rule(
        self, info: Info, tenant_id: uuid.UUID, input: RedactionRuleCreateInput
    ) -> RedactionRuleType:
        """Create a new redaction rule."""
        await check_graphql_permission(info, "audit:redaction:create", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.redaction import RedactionService

        async with async_session_factory() as db:
            service = RedactionService(db)
            rule = await service.create_rule(
                str(tenant_id),
                field_pattern=input.field_pattern,
                replacement=input.replacement,
                is_active=input.is_active,
                priority=input.priority,
            )
            await db.commit()
            return RedactionRuleType(
                id=rule.id,
                tenant_id=rule.tenant_id,
                field_pattern=rule.field_pattern,
                replacement=rule.replacement,
                is_active=rule.is_active,
                priority=rule.priority,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )

    @strawberry.mutation
    async def update_redaction_rule(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        input: RedactionRuleUpdateInput,
    ) -> RedactionRuleType | None:
        """Update a redaction rule."""
        await check_graphql_permission(info, "audit:redaction:update", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.redaction import RedactionService

        async with async_session_factory() as db:
            service = RedactionService(db)
            kwargs = {}
            if input.field_pattern is not None:
                kwargs["field_pattern"] = input.field_pattern
            if input.replacement is not None:
                kwargs["replacement"] = input.replacement
            if input.is_active is not None:
                kwargs["is_active"] = input.is_active
            if input.priority is not None:
                kwargs["priority"] = input.priority

            rule = await service.update_rule(str(rule_id), str(tenant_id), **kwargs)
            if not rule:
                return None
            await db.commit()
            return RedactionRuleType(
                id=rule.id,
                tenant_id=rule.tenant_id,
                field_pattern=rule.field_pattern,
                replacement=rule.replacement,
                is_active=rule.is_active,
                priority=rule.priority,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )

    @strawberry.mutation
    async def delete_redaction_rule(
        self, info: Info, tenant_id: uuid.UUID, rule_id: uuid.UUID
    ) -> bool:
        """Delete a redaction rule (soft delete)."""
        await check_graphql_permission(info, "audit:redaction:delete", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.redaction import RedactionService

        async with async_session_factory() as db:
            service = RedactionService(db)
            deleted = await service.delete_rule(str(rule_id), str(tenant_id))
            await db.commit()
            return deleted

    @strawberry.mutation
    async def create_saved_query(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        input: SavedQueryCreateInput,
    ) -> SavedQueryType:
        """Create a saved audit query."""
        await check_graphql_permission(info, "audit:query:create", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            query = await service.create_saved_query(
                str(tenant_id),
                str(user_id),
                name=input.name,
                query_params=input.query_params,
                is_shared=input.is_shared,
            )
            await db.commit()
            return SavedQueryType(
                id=query.id,
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                name=query.name,
                query_params=query.query_params,
                is_shared=query.is_shared,
                created_at=query.created_at,
                updated_at=query.updated_at,
            )

    @strawberry.mutation
    async def delete_saved_query(
        self, info: Info, tenant_id: uuid.UUID, query_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a saved audit query (soft delete)."""
        await check_graphql_permission(info, "audit:query:delete", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            deleted = await service.delete_saved_query(
                str(query_id), str(tenant_id), str(user_id)
            )
            await db.commit()
            return deleted

    @strawberry.mutation
    async def start_audit_export(
        self, info: Info, tenant_id: uuid.UUID, input: ExportRequestInput
    ) -> ExportStatusType:
        """Start an async audit log export."""
        await check_graphql_permission(info, "audit:export:create", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.export import AuditExportService

        async with async_session_factory() as db:
            service = AuditExportService(db)
            filters = {}
            if input.date_from:
                filters["date_from"] = input.date_from
            if input.date_to:
                filters["date_to"] = input.date_to
            if input.action:
                filters["action"] = input.action.value
            if input.resource_type:
                filters["resource_type"] = input.resource_type
            if input.priority:
                filters["priority"] = input.priority.value

            export_id = await service.start_export(
                str(tenant_id), format=input.format, filters=filters
            )

        # Start Temporal workflow
        warnings: list[str] = []
        try:
            from app.core.config import get_settings
            from app.core.temporal import get_temporal_client
            from app.workflows.audit_export import AuditExportParams

            settings = get_settings()
            client = await get_temporal_client()
            await client.start_workflow(
                "AuditExportWorkflow",
                AuditExportParams(
                    tenant_id=str(tenant_id),
                    export_id=export_id,
                    format=input.format,
                    filters=filters,
                ),
                id=f"audit-export-{export_id}",
                task_queue=settings.temporal_task_queue,
            )
        except Exception:
            logger.warning(
                "Failed to start audit export workflow for export %s",
                export_id,
                exc_info=True,
            )
            warnings.append(
                "Workflow engine unavailable — export will need to be retried"
            )

        return ExportStatusType(
            export_id=export_id, status="pending", warnings=warnings or None
        )
