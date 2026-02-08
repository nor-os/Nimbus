"""
Overview: REST API endpoints for impersonation session management.
Architecture: Impersonation REST endpoints (Section 7.1)
Dependencies: fastapi, app.services.impersonation, app.schemas.impersonation
Concepts: Impersonation lifecycle, approval workflow, Temporal signals
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_not_impersonating
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.impersonation import (
    ImpersonationApprovalRequest,
    ImpersonationConfigResponse,
    ImpersonationConfigUpdate,
    ImpersonationExtendRequest,
    ImpersonationModeEnum,
    ImpersonationRequest,
    ImpersonationSessionListResponse,
    ImpersonationSessionResponse,
    ImpersonationStatusResponse,
    ImpersonationTokenResponse,
)
from app.services.impersonation.service import ImpersonationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/impersonation", tags=["impersonation"])


@router.post("/request", response_model=ImpersonationSessionResponse)
async def request_impersonation(
    body: ImpersonationRequest,
    request: Request,
    current_user: User = Depends(require_not_impersonating),
    _perm: User = Depends(require_permission("impersonation:session:create")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationSessionResponse:
    """Create an impersonation request (starts Temporal workflow)."""
    from app.core.config import get_settings
    from app.core.temporal import get_temporal_client
    from app.services.impersonation.config import ImpersonationConfigService
    from app.services.impersonation.service import ImpersonationService
    from app.workflows.impersonation import ImpersonationWorkflow, ImpersonationWorkflowInput

    try:
        service = ImpersonationService(db)
        session = await service.request_impersonation(
            requester_id=str(current_user.id),
            target_user_id=str(body.target_user_id),
            tenant_id=str(body.tenant_id),
            mode=body.mode.value,
            reason=body.reason,
            password=body.password,
        )
        await db.commit()

        # Get config for this tenant
        config_service = ImpersonationConfigService(db)
        config = await config_service.get_config(str(body.tenant_id))

        mode_key = "standard" if body.mode == ImpersonationModeEnum.STANDARD else "override"
        requires_approval = config[f"{mode_key}_requires_approval"]
        duration_minutes = config[f"{mode_key}_duration_minutes"]

        # Start Temporal workflow
        settings = get_settings()
        try:
            client = await get_temporal_client()
            workflow_id = f"impersonation-{session.id}"
            await client.start_workflow(
                ImpersonationWorkflow.run,
                ImpersonationWorkflowInput(
                    session_id=str(session.id),
                    mode=body.mode.value,
                    requires_approval=requires_approval,
                    duration_minutes=duration_minutes,
                    max_duration_minutes=config["max_duration_minutes"],
                ),
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
            )

            # Update session with workflow ID
            session.workflow_id = workflow_id
            await db.commit()
        except Exception:
            # Temporal unavailable — session stays in PENDING_APPROVAL
            logger.warning(
                "Failed to start impersonation workflow for session %s",
                session.id,
                exc_info=True,
            )

        await db.refresh(session)
        return ImpersonationSessionResponse.model_validate(session)

    except ImpersonationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            if e.code != "PERMISSION_DENIED"
            else status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/{session_id}/approve", response_model=ImpersonationSessionResponse)
async def approve_impersonation(
    session_id: uuid.UUID,
    body: ImpersonationApprovalRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationSessionResponse:
    """Approve or reject a pending impersonation request (sends Temporal signal)."""
    from app.services.impersonation.service import ImpersonationService
    from app.services.permission.engine import PermissionEngine

    # Check approval permission
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if tenant_id:
        engine = PermissionEngine(db)
        allowed, _ = await engine.check_permission(
            str(current_user.id), "impersonation:approval:decide", tenant_id
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "impersonation:approval:decide permission required",
                        "trace_id": getattr(request.state, "trace_id", None),
                    }
                },
            )

    try:
        service = ImpersonationService(db)
        session = await service.process_approval(
            session_id=str(session_id),
            approver_id=str(current_user.id),
            decision=body.decision,
            reason=body.reason,
        )
        await db.commit()

        # Send Temporal signal
        if session.workflow_id:
            try:
                from app.core.temporal import get_temporal_client
                from app.workflows.impersonation import ImpersonationWorkflow

                client = await get_temporal_client()
                handle = client.get_workflow_handle(session.workflow_id)
                await handle.signal(
                    ImpersonationWorkflow.approval_decision,
                    body.decision,
                    body.reason,
                )
            except Exception:
                logger.warning(
                    "Failed to send approval signal to workflow %s",
                    session.workflow_id,
                    exc_info=True,
                )

        await db.refresh(session)
        return ImpersonationSessionResponse.model_validate(session)

    except ImpersonationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_impersonation(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """End an active impersonation session (sends Temporal signal)."""
    from app.services.impersonation.service import ImpersonationService

    service = ImpersonationService(db)
    session = await service.get_session(str(session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Impersonation session not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Allow requester or impersonating user to end
    impersonating = getattr(request.state, "impersonating", None)
    is_requester = str(current_user.id) == str(session.requester_id)
    is_impersonating_self = (
        impersonating and impersonating.get("session_id") == str(session_id)
    )
    if not is_requester and not is_impersonating_self:
        # Check permission
        tenant_id = getattr(request.state, "current_tenant_id", None)
        if tenant_id:
            from app.services.permission.engine import PermissionEngine

            engine = PermissionEngine(db)
            allowed, _ = await engine.check_permission(
                str(current_user.id), "impersonation:session:read", tenant_id
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "PERMISSION_DENIED",
                            "message": "Cannot end this session",
                            "trace_id": getattr(request.state, "trace_id", None),
                        }
                    },
                )

    # Send Temporal signal
    if session.workflow_id:
        try:
            from app.core.temporal import get_temporal_client
            from app.workflows.impersonation import ImpersonationWorkflow

            client = await get_temporal_client()
            handle = client.get_workflow_handle(session.workflow_id)
            await handle.signal(ImpersonationWorkflow.end_session)
        except Exception:
            logger.warning(
                "Failed to send end signal to workflow %s, falling back to direct DB update",
                session.workflow_id,
                exc_info=True,
            )
            # Fallback: end directly
            await service.end_session(str(session_id), "manual")
            await db.commit()
    else:
        await service.end_session(str(session_id), "manual")
        await db.commit()


@router.post("/{session_id}/extend", response_model=ImpersonationSessionResponse)
async def extend_impersonation(
    session_id: uuid.UUID,
    body: ImpersonationExtendRequest,
    request: Request,
    current_user: User = Depends(require_permission("impersonation:session:create")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationSessionResponse:
    """Extend an active impersonation session."""
    from app.services.impersonation.service import ImpersonationService

    service = ImpersonationService(db)
    session = await service.get_session(str(session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Impersonation session not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Send Temporal signal
    if session.workflow_id:
        try:
            from app.core.temporal import get_temporal_client
            from app.workflows.impersonation import ImpersonationWorkflow

            client = await get_temporal_client()
            handle = client.get_workflow_handle(session.workflow_id)
            await handle.signal(ImpersonationWorkflow.extend_session, body.minutes)
        except Exception:
            logger.warning(
                "Failed to send extend signal to workflow %s",
                session.workflow_id,
                exc_info=True,
            )

    # Also extend in DB directly
    try:
        await service.extend_session(str(session_id), body.minutes)
        await db.commit()
    except ImpersonationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    await db.refresh(session)
    return ImpersonationSessionResponse.model_validate(session)


@router.get("/sessions", response_model=ImpersonationSessionListResponse)
async def list_sessions(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_permission("impersonation:session:read")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationSessionListResponse:
    """List impersonation sessions in the current tenant."""
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NO_TENANT_CONTEXT",
                    "message": "No tenant context",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    from app.services.impersonation.service import ImpersonationService

    service = ImpersonationService(db)
    sessions, total = await service.get_sessions(tenant_id, offset, limit)
    return ImpersonationSessionListResponse(
        items=[ImpersonationSessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.get("/sessions/{session_id}", response_model=ImpersonationSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permission("impersonation:session:read")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationSessionResponse:
    """Get impersonation session details."""
    from app.services.impersonation.service import ImpersonationService

    service = ImpersonationService(db)
    session = await service.get_session(str(session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Impersonation session not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return ImpersonationSessionResponse.model_validate(session)


@router.get("/config", response_model=ImpersonationConfigResponse)
async def get_config(
    request: Request,
    current_user: User = Depends(require_permission("impersonation:session:read")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationConfigResponse:
    """Get impersonation config for the current tenant."""
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NO_TENANT_CONTEXT",
                    "message": "No tenant context",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    from app.services.impersonation.config import ImpersonationConfigService

    service = ImpersonationConfigService(db)
    config = await service.get_config(tenant_id)
    return ImpersonationConfigResponse(**config)


@router.put("/config", response_model=ImpersonationConfigResponse)
async def update_config(
    body: ImpersonationConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationConfigResponse:
    """Update impersonation config for the current tenant."""
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NO_TENANT_CONTEXT",
                    "message": "No tenant context",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Check permission
    from app.services.permission.engine import PermissionEngine

    engine = PermissionEngine(db)
    allowed, _ = await engine.check_permission(
        str(current_user.id), "impersonation:config:manage", tenant_id
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "impersonation:config:manage permission required",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    from app.services.impersonation.config import ImpersonationConfigService

    service = ImpersonationConfigService(db)
    config = await service.update_config(
        tenant_id, body.model_dump(exclude_none=True)
    )
    await db.commit()
    return ImpersonationConfigResponse(**config)


@router.get("/me", response_model=ImpersonationStatusResponse)
async def check_impersonation_status(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ImpersonationStatusResponse:
    """Check if the current token is an impersonation token."""
    impersonating = getattr(request.state, "impersonating", None)
    if not impersonating:
        return ImpersonationStatusResponse(is_impersonating=False)

    return ImpersonationStatusResponse(
        is_impersonating=True,
        session_id=impersonating.get("session_id"),
        original_user_id=impersonating.get("original_user"),
        original_tenant_id=impersonating.get("original_tenant"),
        started_at=impersonating.get("started_at"),
        expires_at=impersonating.get("expires_at"),
    )
