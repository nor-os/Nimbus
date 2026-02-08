"""
Overview: Core audit logging service — creates immutable log entries with hash chain.
Architecture: Audit write path (Section 8)
Dependencies: sqlalchemy, app.models.audit, app.services.audit.hash_chain, app.services.audit.taxonomy
Concepts: Non-blocking audit writes, hash chain, fire-and-forget logging, event taxonomy
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ActorType, AuditAction, AuditLog, AuditPriority, EventCategory
from app.services.audit.hash_chain import HashChainService
from app.services.audit.taxonomy import (
    get_category_for_event_type,
    validate_event_type,
)

logger = logging.getLogger(__name__)

# Map event_type prefix -> legacy AuditAction for backward compat
_EVENT_TYPE_TO_ACTION = {
    "auth.login": AuditAction.LOGIN,
    "auth.logout": AuditAction.LOGOUT,
    "data.create": AuditAction.CREATE,
    "data.read": AuditAction.READ,
    "data.update": AuditAction.UPDATE,
    "data.delete": AuditAction.DELETE,
    "data.export": AuditAction.EXPORT,
    "data.archive": AuditAction.ARCHIVE,
    "permission": AuditAction.PERMISSION_CHANGE,
    "system": AuditAction.SYSTEM,
    "security.breakglass": AuditAction.BREAK_GLASS,
    "security.impersonate": AuditAction.IMPERSONATE,
    "security.override": AuditAction.OVERRIDE,
    "api": AuditAction.READ,
    "tenant": AuditAction.UPDATE,
    "user": AuditAction.UPDATE,
}


def _derive_action_from_event_type(event_type: str) -> AuditAction:
    """Derive a legacy AuditAction from an event_type string."""
    for prefix, action in _EVENT_TYPE_TO_ACTION.items():
        if event_type.startswith(prefix):
            return action
    return AuditAction.SYSTEM


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.hash_chain = HashChainService(db)

    async def log(
        self,
        *,
        tenant_id: str,
        action: AuditAction | None = None,
        event_type: str | None = None,
        event_category: EventCategory | str | None = None,
        actor_type: ActorType | str | None = None,
        actor_id: str | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        impersonator_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        trace_id: str | None = None,
        priority: AuditPriority = AuditPriority.INFO,
        metadata: dict | None = None,
        impersonation_context: dict | None = None,
        user_agent: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        request_body: dict | None = None,
        response_status: int | None = None,
        response_body: dict | None = None,
    ) -> AuditLog:
        """Create an audit log entry with hash chain integrity.

        Supports both old-style (action=) and new-style (event_type=) calls.
        - If event_type is provided: auto-derive event_category and action.
        - If only action is provided: backward compatible, no taxonomy fields.
        """
        if impersonation_context:
            metadata = metadata or {}
            metadata["real_actor"] = impersonation_context.get("original_user")
            metadata["impersonating_as"] = impersonation_context.get("session_id")

        # Resolve event_category from event_type
        resolved_category = None
        if event_type:
            if isinstance(event_category, str):
                try:
                    resolved_category = EventCategory(event_category)
                except ValueError:
                    resolved_category = None
            elif isinstance(event_category, EventCategory):
                resolved_category = event_category

            if resolved_category is None:
                cat = get_category_for_event_type(event_type)
                resolved_category = cat

        # Resolve actor_type
        resolved_actor_type = None
        if isinstance(actor_type, str):
            try:
                resolved_actor_type = ActorType(actor_type)
            except ValueError:
                resolved_actor_type = None
        elif isinstance(actor_type, ActorType):
            resolved_actor_type = actor_type

        # Auto-derive action from event_type for backward compatibility
        if action is None and event_type:
            action = _derive_action_from_event_type(event_type)
        elif action is None:
            action = AuditAction.SYSTEM

        previous_hash = await self.hash_chain.get_previous_hash(tenant_id)

        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            action=action,
            event_type=event_type,
            event_category=resolved_category,
            actor_type=resolved_actor_type,
            impersonator_id=impersonator_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_values,
            new_values=new_values,
            trace_id=trace_id,
            priority=priority,
            previous_hash=previous_hash,
            metadata_=metadata,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            request_body=request_body,
            response_status=response_status,
            response_body=response_body,
        )

        # Compute hash from entry data
        entry_data = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "action": action.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "old_values": old_values,
            "new_values": new_values,
            "trace_id": trace_id,
            "priority": priority.value,
            "created_at": str(entry.created_at) if entry.created_at else None,
        }
        if event_type:
            entry_data["event_type"] = event_type
        if resolved_category:
            entry_data["event_category"] = resolved_category.value
        entry.hash = HashChainService.compute_hash(entry_data, previous_hash)

        self.db.add(entry)
        await self.db.flush()
        return entry

    @staticmethod
    def log_async(
        *,
        tenant_id: str,
        action: AuditAction | None = None,
        event_type: str | None = None,
        event_category: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        impersonator_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        trace_id: str | None = None,
        priority: AuditPriority = AuditPriority.INFO,
        metadata: dict | None = None,
        user_agent: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        request_body: dict | None = None,
        response_status: int | None = None,
        response_body: dict | None = None,
    ) -> None:
        """Fire-and-forget audit log — never crashes the calling request."""
        asyncio.create_task(
            _log_in_background(
                tenant_id=tenant_id,
                action=action,
                event_type=event_type,
                event_category=event_category,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_email=actor_email,
                actor_ip=actor_ip,
                impersonator_id=impersonator_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                old_values=old_values,
                new_values=new_values,
                trace_id=trace_id,
                priority=priority,
                metadata=metadata,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                request_body=request_body,
                response_status=response_status,
                response_body=response_body,
            )
        )


async def _log_in_background(
    *,
    tenant_id: str,
    action: AuditAction | None = None,
    event_type: str | None = None,
    event_category: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    actor_email: str | None = None,
    actor_ip: str | None = None,
    impersonator_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    trace_id: str | None = None,
    priority: AuditPriority = AuditPriority.INFO,
    metadata: dict | None = None,
    user_agent: str | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    request_body: dict | None = None,
    response_status: int | None = None,
    response_body: dict | None = None,
) -> None:
    """Background task for fire-and-forget audit logging."""
    try:
        from app.db.session import async_session_factory

        async with async_session_factory() as db:
            service = AuditService(db)
            await service.log(
                tenant_id=tenant_id,
                action=action,
                event_type=event_type,
                event_category=event_category,
                actor_type=actor_type,
                actor_id=actor_id,
                actor_email=actor_email,
                actor_ip=actor_ip,
                impersonator_id=impersonator_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                old_values=old_values,
                new_values=new_values,
                trace_id=trace_id,
                priority=priority,
                metadata=metadata,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                request_body=request_body,
                response_status=response_status,
                response_body=response_body,
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to write audit log entry")
