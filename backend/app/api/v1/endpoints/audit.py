"""
Overview: REST API endpoints for audit log viewing, export, retention, redaction, and chain verification.
Architecture: Audit REST endpoints (Section 7.1)
Dependencies: fastapi, app.services.audit, app.schemas.audit, app.api.deps
Concepts: Audit logging, data export, retention policies, redaction rules, hash chain
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import (
    ArchiveResponse,
    AuditLoggingConfigResponse,
    AuditLoggingConfigUpdate,
    AuditLogListResponse,
    AuditLogResponse,
    AuditSearchParams,
    CategoryRetentionOverrideResponse,
    CategoryRetentionOverrideUpsert,
    ExportRequest,
    ExportResponse,
    ExportStatusResponse,
    RedactionRuleCreate,
    RedactionRuleResponse,
    RedactionRuleUpdate,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    SavedQueryCreate,
    SavedQueryResponse,
    TaxonomyCategoryResponse,
    TaxonomyEventTypeResponse,
    TaxonomyResponse,
    VerifyChainRequest,
    VerifyChainResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Logging Config ─────────────────────────────────────


@router.get("/logging-config", response_model=AuditLoggingConfigResponse)
async def get_logging_config(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:log:read")),
    db: AsyncSession = Depends(get_db),
) -> AuditLoggingConfigResponse:
    """Get the audit logging configuration for the current tenant."""
    from app.services.audit.logging_config import AuditLoggingConfigService

    service = AuditLoggingConfigService(db)
    config = await service.get_config(tenant_id)
    return AuditLoggingConfigResponse(**config)


@router.put("/logging-config", response_model=AuditLoggingConfigResponse)
async def update_logging_config(
    body: AuditLoggingConfigUpdate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:retention:update")),
    db: AsyncSession = Depends(get_db),
) -> AuditLoggingConfigResponse:
    """Update the audit logging configuration for the current tenant."""
    from app.services.audit.logging_config import AuditLoggingConfigService

    service = AuditLoggingConfigService(db)
    config = await service.update_config(
        tenant_id, body.model_dump(exclude_none=True)
    )
    return AuditLoggingConfigResponse(**config)


# ── Taxonomy ───────────────────────────────────────────


@router.get("/taxonomy", response_model=TaxonomyResponse)
async def get_taxonomy(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> TaxonomyResponse:
    """Return the full event taxonomy tree for the filter UI."""
    from app.services.audit.taxonomy import TAXONOMY

    categories = []
    for cat, entries in TAXONOMY.items():
        categories.append(TaxonomyCategoryResponse(
            category=cat.value,
            label=cat.value.replace("_", " ").title(),
            event_types=[
                TaxonomyEventTypeResponse(
                    key=e["key"],
                    label=e["label"],
                    description=e["description"],
                    default_priority=e["default_priority"],
                )
                for e in entries
            ],
        ))
    return TaxonomyResponse(categories=categories)


# ── Audit Logs ──────────────────────────────────────────


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    request: Request,
    params: AuditSearchParams = Depends(),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:log:read")),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Search audit logs with filtering and pagination."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    logs, total = await service.search(
        tenant_id,
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
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:log:read")),
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    """Get a single audit log entry."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    log = await service.get_by_id(log_id, tenant_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "AUDIT_LOG_NOT_FOUND",
                    "message": "Audit log entry not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return AuditLogResponse.model_validate(log)


@router.get("/logs/trace/{trace_id}", response_model=list[AuditLogResponse])
async def get_audit_logs_by_trace(
    trace_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:log:read")),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    """Get all audit log entries for a trace ID."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    logs = await service.get_by_trace_id(trace_id, tenant_id)
    return [AuditLogResponse.model_validate(log) for log in logs]


# ── Archives ────────────────────────────────────────────


@router.get("/archives", response_model=list[ArchiveResponse])
async def list_archives(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:archive:read")),
) -> list[ArchiveResponse]:
    """List available audit log archives."""
    from app.services.audit.archive import ArchiveService

    service = ArchiveService()
    archives = service.list_archives(tenant_id)
    return [ArchiveResponse(**a) for a in archives]


@router.get("/archives/{key:path}")
async def download_archive(
    key: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:archive:read")),
) -> dict:
    """Get a presigned download URL for an archive."""
    from app.services.audit.archive import ArchiveService

    # Ensure the key belongs to the requesting tenant
    if not key.startswith(f"{tenant_id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "Archive does not belong to current tenant",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    service = ArchiveService()
    try:
        url = service.get_download_url(key)
        return {"download_url": url}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "ARCHIVE_NOT_FOUND",
                    "message": "Archive not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


# ── Export ───────────────────────────────────────────────


@router.post("/export", response_model=ExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    body: ExportRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:export:create")),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Start an asynchronous audit log export."""
    from app.services.audit.export import AuditExportService

    service = AuditExportService(db)
    export_id = await service.start_export(
        tenant_id,
        format=body.format,
        filters=body.model_dump(exclude={"format"}, exclude_none=True),
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
                tenant_id=tenant_id,
                export_id=export_id,
                format=body.format,
                filters=body.model_dump(exclude={"format"}, exclude_none=True),
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
        warnings.append("Workflow engine unavailable — export will need to be retried")

    return ExportResponse(
        export_id=export_id, status="pending", warnings=warnings or None
    )


@router.get("/export/{export_id}", response_model=ExportStatusResponse)
async def get_export_status(
    export_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:export:read")),
    db: AsyncSession = Depends(get_db),
) -> ExportStatusResponse:
    """Get the status of an export."""
    from app.services.audit.export import AuditExportService

    service = AuditExportService(db)
    download_url = service.get_download_url(tenant_id, export_id)
    if download_url:
        return ExportStatusResponse(
            export_id=export_id, status="completed", download_url=download_url
        )
    return ExportStatusResponse(export_id=export_id, status="pending")


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:export:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a presigned download URL for a completed export."""
    from app.services.audit.export import AuditExportService

    service = AuditExportService(db)
    download_url = service.get_download_url(tenant_id, export_id)
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "EXPORT_NOT_FOUND",
                    "message": "Export not found or not yet ready",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return {"download_url": download_url}


# ── Retention ───────────────────────────────────────────


@router.get("/retention", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:retention:read")),
    db: AsyncSession = Depends(get_db),
) -> RetentionPolicyResponse:
    """Get the retention policy for the current tenant, including per-category overrides."""
    from app.services.audit.retention import RetentionService

    service = RetentionService(db)
    policy = await service.get_or_create_policy(tenant_id)
    overrides = await service.list_category_overrides(tenant_id)
    return RetentionPolicyResponse(
        id=policy.id,
        tenant_id=policy.tenant_id,
        hot_days=policy.hot_days,
        cold_days=policy.cold_days,
        archive_enabled=policy.archive_enabled,
        category_overrides=[
            CategoryRetentionOverrideResponse.model_validate(ov) for ov in overrides
        ],
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.put("/retention", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    body: RetentionPolicyUpdate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:retention:update")),
    db: AsyncSession = Depends(get_db),
) -> RetentionPolicyResponse:
    """Update the retention policy for the current tenant."""
    from app.services.audit.retention import RetentionService

    service = RetentionService(db)
    policy = await service.update_policy(
        tenant_id,
        hot_days=body.hot_days,
        cold_days=body.cold_days,
        archive_enabled=body.archive_enabled,
    )
    overrides = await service.list_category_overrides(tenant_id)
    return RetentionPolicyResponse(
        id=policy.id,
        tenant_id=policy.tenant_id,
        hot_days=policy.hot_days,
        cold_days=policy.cold_days,
        archive_enabled=policy.archive_enabled,
        category_overrides=[
            CategoryRetentionOverrideResponse.model_validate(ov) for ov in overrides
        ],
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


# ── Category Retention Overrides ───────────────────────


@router.put(
    "/retention/categories/{event_category}",
    response_model=CategoryRetentionOverrideResponse,
)
async def upsert_category_retention_override(
    event_category: str,
    body: CategoryRetentionOverrideUpsert,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:retention:update")),
    db: AsyncSession = Depends(get_db),
) -> CategoryRetentionOverrideResponse:
    """Create or update a per-category retention override."""
    from app.services.audit.retention import RetentionService

    service = RetentionService(db)
    try:
        override = await service.upsert_category_override(
            tenant_id,
            event_category=event_category,
            hot_days=body.hot_days,
            cold_days=body.cold_days,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_CATEGORY",
                    "message": f"Invalid event category: {event_category}",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return CategoryRetentionOverrideResponse.model_validate(override)


@router.delete(
    "/retention/categories/{event_category}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category_retention_override(
    event_category: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:retention:update")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a per-category retention override (reverts to global default)."""
    from app.services.audit.retention import RetentionService

    service = RetentionService(db)
    try:
        deleted = await service.delete_category_override(tenant_id, event_category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_CATEGORY",
                    "message": f"Invalid event category: {event_category}",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "OVERRIDE_NOT_FOUND",
                    "message": "No override found for this category",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


# ── Redaction Rules ─────────────────────────────────────


@router.get("/redaction-rules", response_model=list[RedactionRuleResponse])
async def list_redaction_rules(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:redaction:read")),
    db: AsyncSession = Depends(get_db),
) -> list[RedactionRuleResponse]:
    """List redaction rules for the current tenant."""
    from app.services.audit.redaction import RedactionService

    service = RedactionService(db)
    rules = await service.list_rules(tenant_id)
    return [RedactionRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/redaction-rules",
    response_model=RedactionRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_redaction_rule(
    body: RedactionRuleCreate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:redaction:create")),
    db: AsyncSession = Depends(get_db),
) -> RedactionRuleResponse:
    """Create a new redaction rule."""
    from app.services.audit.redaction import RedactionService

    service = RedactionService(db)
    rule = await service.create_rule(
        tenant_id,
        field_pattern=body.field_pattern,
        replacement=body.replacement,
        is_active=body.is_active,
        priority=body.priority,
    )
    return RedactionRuleResponse.model_validate(rule)


@router.patch("/redaction-rules/{rule_id}", response_model=RedactionRuleResponse)
async def update_redaction_rule(
    rule_id: str,
    body: RedactionRuleUpdate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:redaction:update")),
    db: AsyncSession = Depends(get_db),
) -> RedactionRuleResponse:
    """Update a redaction rule."""
    from app.services.audit.redaction import RedactionService

    service = RedactionService(db)
    rule = await service.update_rule(
        rule_id, tenant_id, **body.model_dump(exclude_unset=True)
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": "Redaction rule not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return RedactionRuleResponse.model_validate(rule)


@router.delete("/redaction-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_redaction_rule(
    rule_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:redaction:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a redaction rule (soft delete)."""
    from app.services.audit.redaction import RedactionService

    service = RedactionService(db)
    deleted = await service.delete_rule(rule_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": "Redaction rule not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


# ── Saved Queries ───────────────────────────────────────


@router.get("/saved-queries", response_model=list[SavedQueryResponse])
async def list_saved_queries(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:query:read")),
    db: AsyncSession = Depends(get_db),
) -> list[SavedQueryResponse]:
    """List saved queries (own + shared)."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    queries = await service.list_saved_queries(tenant_id, str(current_user.id))
    return [SavedQueryResponse.model_validate(q) for q in queries]


@router.post(
    "/saved-queries",
    response_model=SavedQueryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_saved_query(
    body: SavedQueryCreate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:query:create")),
    db: AsyncSession = Depends(get_db),
) -> SavedQueryResponse:
    """Create a saved query."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    query = await service.create_saved_query(
        tenant_id,
        str(current_user.id),
        name=body.name,
        query_params=body.query_params,
        is_shared=body.is_shared,
    )
    return SavedQueryResponse.model_validate(query)


@router.delete("/saved-queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_query(
    query_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:query:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a saved query (soft delete)."""
    from app.services.audit.query import AuditQueryService

    service = AuditQueryService(db)
    deleted = await service.delete_saved_query(query_id, tenant_id, str(current_user.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "QUERY_NOT_FOUND",
                    "message": "Saved query not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


# ── Chain Verification ──────────────────────────────────


@router.post("/verify-chain", response_model=VerifyChainResponse)
async def verify_chain(
    body: VerifyChainRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("audit:chain:verify")),
    db: AsyncSession = Depends(get_db),
) -> VerifyChainResponse:
    """Verify the hash chain integrity for the current tenant."""
    from app.services.audit.hash_chain import HashChainService

    service = HashChainService(db)
    result = await service.verify_chain(tenant_id, start=body.start, limit=body.limit)
    return VerifyChainResponse(
        valid=result.valid,
        total_checked=result.total_checked,
        broken_links=result.broken_links,
    )
