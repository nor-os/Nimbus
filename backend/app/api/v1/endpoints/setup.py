"""
Overview: REST API endpoints for the first-run setup wizard.
Architecture: Setup endpoints — unprotected, only work before setup completes (Section 7.1)
Dependencies: fastapi, app.services.setup, app.services.auth, app.schemas.setup
Concepts: First-run setup, admin bootstrap, initial tokens
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import TokenResponse
from app.schemas.setup import SetupInitializeRequest, SetupStatusResponse
from app.services.auth.service import AuthService
from app.services.setup.service import SetupError, SetupService

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatusResponse:
    """Check if the initial setup has been completed."""
    service = SetupService(db)
    return SetupStatusResponse(is_complete=await service.is_setup_complete())


@router.post("/initialize", response_model=TokenResponse)
async def initialize(
    body: SetupInitializeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Complete the first-run setup and return initial auth tokens."""
    setup_service = SetupService(db)

    try:
        _provider, user = await setup_service.initialize(
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            organization_name=body.organization_name,
        )
    except SetupError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Auto-login the admin
    auth_service = AuthService(db)
    result = await auth_service._create_session(
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(**result)
