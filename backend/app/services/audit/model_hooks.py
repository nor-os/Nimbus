"""
Overview: SQLAlchemy event hooks for automatic data change auditing.
Architecture: ORM-level audit integration (Section 8)
Dependencies: sqlalchemy, app.models.audit, app.core.tenant_context, app.services.audit.taxonomy
Concepts: After-flush inspection, attribute history, change detection, infinite loop prevention, event taxonomy
"""

import asyncio
import logging
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.services.audit.taxonomy import TABLE_TO_RESOURCE_TYPE, derive_event_type_from_table

logger = logging.getLogger(__name__)

# Models to skip (prevent infinite loop)
_SKIP_MODELS = {AuditLog.__tablename__}


def register_audit_hooks(engine: AsyncEngine) -> None:
    """Register SQLAlchemy event hooks on the sync engine for data change auditing."""
    sync_engine = engine.sync_engine
    event.listen(Session, "after_flush", _after_flush)
    logger.info("Audit model hooks registered on engine: %s", sync_engine.url)


def _after_flush(session: Session, flush_context: Any) -> None:
    """Inspect session changes after flush and queue audit entries for after_commit."""
    changes: list[dict] = []

    for obj in session.new:
        table_name = getattr(obj.__class__, "__tablename__", None)
        if not table_name or table_name in _SKIP_MODELS:
            continue
        resource_type = TABLE_TO_RESOURCE_TYPE.get(table_name, table_name)
        event_type = derive_event_type_from_table(table_name, "CREATE")
        changes.append({
            "action": AuditAction.CREATE,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": _get_id(obj),
            "resource_name": _get_name(obj),
            "new_values": _get_values(obj),
            "tenant_id": _get_tenant_id(obj),
        })

    for obj in session.dirty:
        table_name = getattr(obj.__class__, "__tablename__", None)
        if not table_name or table_name in _SKIP_MODELS:
            continue
        if not session.is_modified(obj):
            continue
        old_values, new_values = _get_changes(obj)
        if not old_values and not new_values:
            continue

        # Detect soft-delete
        action = AuditAction.UPDATE
        action_str = "UPDATE"
        if "deleted_at" in new_values and new_values["deleted_at"] is not None:
            action = AuditAction.DELETE
            action_str = "DELETE"

        resource_type = TABLE_TO_RESOURCE_TYPE.get(table_name, table_name)
        event_type = derive_event_type_from_table(table_name, action_str)
        changes.append({
            "action": action,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": _get_id(obj),
            "resource_name": _get_name(obj),
            "old_values": old_values,
            "new_values": new_values,
            "tenant_id": _get_tenant_id(obj),
        })

    for obj in session.deleted:
        table_name = getattr(obj.__class__, "__tablename__", None)
        if not table_name or table_name in _SKIP_MODELS:
            continue
        resource_type = TABLE_TO_RESOURCE_TYPE.get(table_name, table_name)
        event_type = derive_event_type_from_table(table_name, "DELETE")
        changes.append({
            "action": AuditAction.DELETE,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": _get_id(obj),
            "resource_name": _get_name(obj),
            "old_values": _get_values(obj),
            "tenant_id": _get_tenant_id(obj),
        })

    if changes:
        if not hasattr(session.info, "get"):
            return
        existing = session.info.get("_audit_changes", [])
        session.info["_audit_changes"] = existing + changes

        # Register after_commit listener if not already registered
        if not session.info.get("_audit_commit_registered"):
            event.listen(session, "after_commit", _after_commit, once=True)
            session.info["_audit_commit_registered"] = True


def _after_commit(session: Session) -> None:
    """Write queued audit entries after transaction commit."""
    changes = session.info.pop("_audit_changes", [])
    session.info.pop("_audit_commit_registered", None)

    if not changes:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_write_changes(changes))
    except RuntimeError:
        # No running event loop — skip
        logger.debug("No event loop available for audit change logging")


async def _write_changes(changes: list[dict]) -> None:
    """Write audit entries for data changes in a separate session."""
    try:
        from app.db.session import async_session_factory
        from app.services.audit.service import AuditService

        async with async_session_factory() as db:
            service = AuditService(db)
            for change in changes:
                tenant_id = change.get("tenant_id")
                if not tenant_id:
                    continue
                await service.log(
                    tenant_id=str(tenant_id),
                    action=change["action"],
                    event_type=change.get("event_type"),
                    actor_type="SYSTEM",
                    resource_type=change.get("resource_type"),
                    resource_id=change.get("resource_id"),
                    resource_name=change.get("resource_name"),
                    old_values=change.get("old_values"),
                    new_values=change.get("new_values"),
                )
            await db.commit()
    except Exception:
        logger.exception("Failed to write audit change entries")


def _get_id(obj: Any) -> str | None:
    """Extract the primary key as a string."""
    pk = getattr(obj, "id", None)
    return str(pk) if pk is not None else None


def _get_name(obj: Any) -> str | None:
    """Extract a human-readable name from the object."""
    for attr in ("name", "email", "key", "slug"):
        val = getattr(obj, attr, None)
        if val:
            return str(val)
    return None


def _get_tenant_id(obj: Any) -> str | None:
    """Extract tenant_id from the object or context."""
    tid = getattr(obj, "tenant_id", None)
    if tid:
        return str(tid)
    from app.core.tenant_context import get_current_tenant_id

    return get_current_tenant_id()


def _get_values(obj: Any) -> dict:
    """Get all column values as a serializable dict."""
    insp = inspect(obj)
    result = {}
    for col in insp.mapper.column_attrs:
        try:
            val = getattr(obj, col.key)
            result[col.key] = str(val) if val is not None else None
        except Exception:
            continue
    return result


def _get_changes(obj: Any) -> tuple[dict, dict]:
    """Get old and new values for modified attributes."""
    insp = inspect(obj)
    old_values = {}
    new_values = {}
    for col in insp.mapper.column_attrs:
        hist = insp.attrs[col.key].history
        if hist.has_changes():
            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else None
            old_values[col.key] = str(old) if old is not None else None
            new_values[col.key] = str(new) if new is not None else None
    return old_values, new_values
