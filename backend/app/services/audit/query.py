"""
Overview: Audit log query service for searching, filtering, and saved queries.
Architecture: Audit read path (Section 8)
Dependencies: sqlalchemy, app.models.audit
Concepts: Paginated search, multi-field filtering, saved queries, trace grouping, event taxonomy
"""

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditLog, AuditPriority, SavedQuery


class AuditQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        tenant_id: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        actor_id: str | None = None,
        action: AuditAction | None = None,
        event_categories: list[str] | None = None,
        event_types: list[str] | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        priority: AuditPriority | None = None,
        trace_id: str | None = None,
        full_text: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Search audit logs with filtering and pagination."""
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)

        if date_from:
            query = query.where(AuditLog.created_at >= date_from)
            count_query = count_query.where(AuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AuditLog.created_at <= date_to)
            count_query = count_query.where(AuditLog.created_at <= date_to)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
            count_query = count_query.where(AuditLog.actor_id == actor_id)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if event_categories:
            cat_filter = AuditLog.event_category.in_(event_categories)
            query = query.where(cat_filter)
            count_query = count_query.where(cat_filter)
        if event_types:
            # Support prefix matching: "auth.*" matches all auth.* event types
            type_conditions = []
            for et in event_types:
                if et.endswith(".*"):
                    prefix = et[:-1]  # "auth." from "auth.*"
                    type_conditions.append(AuditLog.event_type.like(f"{prefix}%"))
                else:
                    type_conditions.append(AuditLog.event_type == et)
            if type_conditions:
                combined = or_(*type_conditions)
                query = query.where(combined)
                count_query = count_query.where(combined)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
            count_query = count_query.where(AuditLog.resource_id == resource_id)
        if priority:
            query = query.where(AuditLog.priority == priority)
            count_query = count_query.where(AuditLog.priority == priority)
        if trace_id:
            query = query.where(AuditLog.trace_id == trace_id)
            count_query = count_query.where(AuditLog.trace_id == trace_id)
        if full_text:
            text_filter = or_(
                AuditLog.actor_email.ilike(f"%{full_text}%"),
                AuditLog.resource_name.ilike(f"%{full_text}%"),
                AuditLog.resource_type.ilike(f"%{full_text}%"),
                AuditLog.resource_id.ilike(f"%{full_text}%"),
                AuditLog.event_type.ilike(f"%{full_text}%"),
            )
            query = query.where(text_filter)
            count_query = count_query.where(text_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def get_by_id(self, log_id: str, tenant_id: str) -> AuditLog | None:
        result = await self.db.execute(
            select(AuditLog).where(
                AuditLog.id == log_id,
                AuditLog.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_trace_id(self, trace_id: str, tenant_id: str) -> list[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.trace_id == trace_id,
                AuditLog.tenant_id == tenant_id,
            )
            .order_by(AuditLog.created_at.asc())
        )
        return list(result.scalars().all())

    # ── Saved Queries ───────────────────────────────

    async def create_saved_query(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        query_params: dict,
        is_shared: bool = False,
    ) -> SavedQuery:
        query = SavedQuery(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            query_params=query_params,
            is_shared=is_shared,
        )
        self.db.add(query)
        await self.db.flush()
        return query

    async def list_saved_queries(self, tenant_id: str, user_id: str) -> list[SavedQuery]:
        result = await self.db.execute(
            select(SavedQuery)
            .where(
                SavedQuery.tenant_id == tenant_id,
                SavedQuery.deleted_at.is_(None),
                or_(
                    SavedQuery.user_id == user_id,
                    SavedQuery.is_shared.is_(True),
                ),
            )
            .order_by(SavedQuery.name.asc())
        )
        return list(result.scalars().all())

    async def delete_saved_query(self, query_id: str, tenant_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            select(SavedQuery).where(
                SavedQuery.id == query_id,
                SavedQuery.tenant_id == tenant_id,
                SavedQuery.user_id == user_id,
                SavedQuery.deleted_at.is_(None),
            )
        )
        query = result.scalar_one_or_none()
        if not query:
            return False
        query.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
