"""
Overview: GraphQL queries for audit logs, saved queries, retention, redaction rules, and taxonomy.
Architecture: GraphQL query resolvers (Section 7.2)
Dependencies: strawberry, app.services.audit
Concepts: Audit logging, GraphQL queries, event taxonomy
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.audit import (
    AuditLogListType,
    AuditLogType,
    AuditSearchInput,
    CategoryRetentionOverrideType,
    EventCategoryGQL,
    RedactionRuleType,
    RetentionPolicyType,
    SavedQueryType,
    TaxonomyCategoryGQL,
    TaxonomyEventTypeGQL,
    TaxonomyResponseGQL,
    VerifyChainResultType,
)


@strawberry.type
class AuditQuery:
    @strawberry.field
    async def audit_logs(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        search: AuditSearchInput | None = None,
    ) -> AuditLogListType:
        """Search audit logs with optional filters."""
        await check_graphql_permission(info, "audit:log:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        params = search or AuditSearchInput()

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            logs, total = await service.search(
                str(tenant_id),
                date_from=params.date_from,
                date_to=params.date_to,
                actor_id=str(params.actor_id) if params.actor_id else None,
                action=params.action,
                event_categories=[c.value for c in params.event_categories] if params.event_categories else None,
                event_types=params.event_types,
                resource_type=params.resource_type,
                resource_id=params.resource_id,
                priority=params.priority,
                trace_id=params.trace_id,
                full_text=params.full_text,
                offset=params.offset,
                limit=params.limit,
            )
            return AuditLogListType(
                items=[_to_audit_log_type(log) for log in logs],
                total=total,
                offset=params.offset,
                limit=params.limit,
            )

    @strawberry.field
    async def audit_log(
        self, info: Info, tenant_id: uuid.UUID, log_id: uuid.UUID
    ) -> AuditLogType | None:
        """Get a single audit log entry."""
        await check_graphql_permission(info, "audit:log:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            log = await service.get_by_id(str(log_id), str(tenant_id))
            if not log:
                return None
            return _to_audit_log_type(log)

    @strawberry.field
    async def audit_logs_by_trace(
        self, info: Info, tenant_id: uuid.UUID, trace_id: str
    ) -> list[AuditLogType]:
        """Get all audit log entries for a trace ID."""
        await check_graphql_permission(info, "audit:log:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            logs = await service.get_by_trace_id(trace_id, str(tenant_id))
            return [_to_audit_log_type(log) for log in logs]

    @strawberry.field
    async def audit_taxonomy(self, info: Info) -> TaxonomyResponseGQL:
        """Return the full event taxonomy tree."""
        from app.services.audit.taxonomy import TAXONOMY

        categories = []
        for cat, entries in TAXONOMY.items():
            categories.append(TaxonomyCategoryGQL(
                category=cat.value,
                label=cat.value.replace("_", " ").title(),
                event_types=[
                    TaxonomyEventTypeGQL(
                        key=e["key"],
                        label=e["label"],
                        description=e["description"],
                        default_priority=e["default_priority"],
                    )
                    for e in entries
                ],
            ))
        return TaxonomyResponseGQL(categories=categories)

    @strawberry.field
    async def retention_policy(
        self, info: Info, tenant_id: uuid.UUID
    ) -> RetentionPolicyType:
        """Get the retention policy for a tenant, including per-category overrides."""
        await check_graphql_permission(info, "audit:retention:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.retention import RetentionService

        async with async_session_factory() as db:
            service = RetentionService(db)
            policy = await service.get_or_create_policy(str(tenant_id))
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

    @strawberry.field
    async def redaction_rules(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[RedactionRuleType]:
        """List redaction rules for a tenant."""
        await check_graphql_permission(info, "audit:redaction:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.redaction import RedactionService

        async with async_session_factory() as db:
            service = RedactionService(db)
            rules = await service.list_rules(str(tenant_id))
            return [
                RedactionRuleType(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    field_pattern=r.field_pattern,
                    replacement=r.replacement,
                    is_active=r.is_active,
                    priority=r.priority,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in rules
            ]

    @strawberry.field
    async def saved_queries(
        self, info: Info, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[SavedQueryType]:
        """List saved queries for a user (own + shared)."""
        await check_graphql_permission(info, "audit:query:read", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.query import AuditQueryService

        async with async_session_factory() as db:
            service = AuditQueryService(db)
            queries = await service.list_saved_queries(str(tenant_id), str(user_id))
            return [
                SavedQueryType(
                    id=q.id,
                    tenant_id=q.tenant_id,
                    user_id=q.user_id,
                    name=q.name,
                    query_params=q.query_params,
                    is_shared=q.is_shared,
                    created_at=q.created_at,
                    updated_at=q.updated_at,
                )
                for q in queries
            ]

    @strawberry.field
    async def verify_audit_chain(
        self, info: Info, tenant_id: uuid.UUID, start: int = 0, limit: int = 1000
    ) -> VerifyChainResultType:
        """Verify the hash chain integrity for a tenant."""
        await check_graphql_permission(info, "audit:chain:verify", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.audit.hash_chain import HashChainService

        async with async_session_factory() as db:
            service = HashChainService(db)
            result = await service.verify_chain(str(tenant_id), start=start, limit=limit)
            return VerifyChainResultType(
                valid=result.valid,
                total_checked=result.total_checked,
                broken_links=result.broken_links,
            )


def _to_audit_log_type(log) -> AuditLogType:
    """Convert an AuditLog ORM instance to a Strawberry type."""
    from app.api.graphql.types.audit import (
        ActorTypeGQL,
        AuditActionGQL,
        AuditPriorityGQL,
        EventCategoryGQL,
    )

    event_category = None
    if log.event_category:
        event_category = EventCategoryGQL(log.event_category.value)

    actor_type = None
    if log.actor_type:
        actor_type = ActorTypeGQL(log.actor_type.value)

    return AuditLogType(
        id=log.id,
        tenant_id=log.tenant_id,
        actor_id=log.actor_id,
        actor_email=log.actor_email,
        actor_ip=log.actor_ip,
        action=AuditActionGQL(log.action.value),
        event_category=event_category,
        event_type=log.event_type,
        actor_type=actor_type,
        impersonator_id=log.impersonator_id,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_name=log.resource_name,
        old_values=log.old_values,
        new_values=log.new_values,
        trace_id=log.trace_id,
        priority=AuditPriorityGQL(log.priority.value),
        hash=log.hash,
        previous_hash=log.previous_hash,
        metadata=log.metadata_,
        user_agent=log.user_agent,
        request_method=log.request_method,
        request_path=log.request_path,
        request_body=log.request_body,
        response_status=log.response_status,
        response_body=log.response_body,
        archived_at=log.archived_at,
        created_at=log.created_at,
    )
