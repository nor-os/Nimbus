"""
Overview: SCIM v2 protocol endpoints for user and group provisioning.
Architecture: SCIM API mounted at /scim/v2 (Section 7.1)
Dependencies: fastapi, app.services.scim
Concepts: SCIM v2 protocol, provisioning, bearer token auth
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.scim.service import SCIMError, SCIMService
from app.services.scim.token_service import SCIMTokenService

router = APIRouter(tags=["scim"])

SCIM_CONTENT_TYPE = "application/scim+json"


async def _get_scim_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[AsyncSession, str]:
    """Authenticate via SCIM bearer token and return (db, tenant_id)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    raw_token = auth_header[7:]
    token_service = SCIMTokenService(db)
    token = await token_service.validate_token(raw_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SCIM token",
        )

    return db, str(token.tenant_id)


def _scim_response(data: dict | list, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status_code, media_type=SCIM_CONTENT_TYPE)


def _scim_error(message: str, status_code: int, scim_type: str | None = None) -> JSONResponse:
    body = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "detail": message,
        "status": str(status_code),
    }
    if scim_type:
        body["scimType"] = scim_type
    return JSONResponse(content=body, status_code=status_code, media_type=SCIM_CONTENT_TYPE)


# ── Discovery ───────────────────────────────────────────────────────


@router.get("/ServiceProviderConfig")
async def service_provider_config() -> JSONResponse:
    """SCIM ServiceProviderConfig discovery endpoint."""
    return _scim_response({
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://nimbus.dev/docs/scim",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "SCIM bearer token authentication",
                "specUri": "https://tools.ietf.org/html/rfc6750",
            }
        ],
    })


@router.get("/Schemas")
async def schemas() -> JSONResponse:
    """SCIM Schemas discovery endpoint."""
    return _scim_response({
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {"id": "urn:ietf:params:scim:schemas:core:2.0:User", "name": "User"},
            {"id": "urn:ietf:params:scim:schemas:core:2.0:Group", "name": "Group"},
        ],
    })


@router.get("/ResourceTypes")
async def resource_types() -> JSONResponse:
    """SCIM ResourceTypes discovery endpoint."""
    return _scim_response({
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/scim/v2/Users",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": "/scim/v2/Groups",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            },
        ],
    })


# ── Users ────────────────────────────────────────────────────────────


@router.get("/Users")
async def list_users(
    request: Request,
    filter: str | None = None,
    startIndex: int = 1,
    count: int = 100,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """List users with optional SCIM filter."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        users, total = await service.list_users(filter, startIndex, count)
        return _scim_response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": total,
            "startIndex": startIndex,
            "itemsPerPage": count,
            "Resources": users,
        })
    except Exception as e:
        return _scim_error(str(e), 400)


@router.get("/Users/{user_id}")
async def get_user(
    user_id: str,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Get a single user."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        user = await service.get_user(user_id)
        return _scim_response(user)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.post("/Users", status_code=201)
async def create_user(
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Create a new user."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        service = SCIMService(db, tenant_id)
        user = await service.create_user(body)
        return _scim_response(user, 201)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.put("/Users/{user_id}")
async def replace_user(
    user_id: str,
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Full replace a user."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        service = SCIMService(db, tenant_id)
        user = await service.update_user(user_id, body)
        return _scim_response(user)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.patch("/Users/{user_id}")
async def patch_user(
    user_id: str,
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Patch a user with SCIM PatchOp."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        operations = body.get("Operations", [])
        service = SCIMService(db, tenant_id)
        user = await service.patch_user(user_id, operations)
        return _scim_response(user)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.delete("/Users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    ctx: tuple = Depends(_get_scim_context),
) -> None:
    """Delete (deactivate) a user."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        await service.delete_user(user_id)
    except SCIMError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


# ── Groups ───────────────────────────────────────────────────────────


@router.get("/Groups")
async def list_groups(
    request: Request,
    filter: str | None = None,
    startIndex: int = 1,
    count: int = 100,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """List groups with optional SCIM filter."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        groups, total = await service.list_groups(filter, startIndex, count)
        return _scim_response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": total,
            "startIndex": startIndex,
            "itemsPerPage": count,
            "Resources": groups,
        })
    except Exception as e:
        return _scim_error(str(e), 400)


@router.get("/Groups/{group_id}")
async def get_group(
    group_id: str,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Get a single group."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        group = await service.get_group(group_id)
        return _scim_response(group)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.post("/Groups", status_code=201)
async def create_group(
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Create a new group."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        service = SCIMService(db, tenant_id)
        group = await service.create_group(body)
        return _scim_response(group, 201)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.put("/Groups/{group_id}")
async def replace_group(
    group_id: str,
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Full replace a group."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        service = SCIMService(db, tenant_id)
        group = await service.update_group(group_id, body)
        return _scim_response(group)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.patch("/Groups/{group_id}")
async def patch_group(
    group_id: str,
    request: Request,
    ctx: tuple = Depends(_get_scim_context),
) -> JSONResponse:
    """Patch a group with SCIM PatchOp."""
    db, tenant_id = ctx
    try:
        body = await request.json()
        operations = body.get("Operations", [])
        service = SCIMService(db, tenant_id)
        group = await service.patch_group(group_id, operations)
        return _scim_response(group)
    except SCIMError as e:
        return _scim_error(e.message, e.status, e.scim_type)


@router.delete("/Groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    ctx: tuple = Depends(_get_scim_context),
) -> None:
    """Delete a group."""
    db, tenant_id = ctx
    try:
        service = SCIMService(db, tenant_id)
        await service.delete_group(group_id)
    except SCIMError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
