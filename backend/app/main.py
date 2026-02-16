"""
Overview: FastAPI application entry point with health endpoints and middleware.
Architecture: Application bootstrap, mounts REST + GraphQL routers (Section 2, 7)
Dependencies: fastapi, app.core.config, app.core.middleware
Concepts: Application lifecycle, health checks, API routing
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.api.graphql.schema import schema
from app.api.v1.router import router as api_v1_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import get_settings
from app.core.middleware import SecurityHeadersMiddleware, TenantContextMiddleware, TraceIDMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    # Startup — register audit model hooks
    from app.db.session import engine as db_engine
    from app.services.audit.model_hooks import register_audit_hooks

    register_audit_hooks(db_engine)

    from app.services.resolver.setup import setup_resolvers

    setup_resolvers()

    yield
    # Shutdown
    from app.db.session import engine

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Middleware: last add_middleware = outermost wrapper (runs first on request)
# CORS must be outermost to handle preflight and attach headers to error responses
# AuditMiddleware is innermost — runs after auth/tenant context is established
app.add_middleware(AuditMiddleware)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────
app.include_router(api_v1_router)

from app.api.v1.endpoints.scim import router as scim_router

app.include_router(scim_router, prefix="/scim/v2")

graphql_app = GraphQLRouter(schema, graphiql=settings.debug)
app.include_router(graphql_app, prefix="/graphql")


# ── Health endpoints ──────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    """Basic health check — is the process running?"""
    return {"status": "ok", "version": settings.app_version}


@app.get("/ready")
async def ready() -> dict:
    """Readiness check — can the app serve traffic?

    Returns structured status:
      ready     — database and Temporal both healthy
      degraded  — database OK, Temporal unreachable (API works, workflows don't)
      not_ready — database unreachable
    """
    from sqlalchemy import text

    from app.core.temporal import check_temporal_health
    from app.db.session import async_session_factory

    # --- Database ---
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_check = {"status": "ok"}
    except Exception as e:
        db_check = {"status": "error", "detail": str(e)}

    # --- Temporal ---
    temporal_ok, temporal_detail = await check_temporal_health()
    temporal_check = {"status": "ok", "detail": temporal_detail} if temporal_ok else {
        "status": "error", "detail": temporal_detail
    }

    # --- Overall ---
    if db_check["status"] != "ok":
        overall = "not_ready"
    elif temporal_check["status"] != "ok":
        overall = "degraded"
    else:
        overall = "ready"

    return {
        "status": overall,
        "checks": {
            "database": db_check,
            "temporal": temporal_check,
        },
    }


@app.get("/live")
async def live() -> dict:
    """Liveness check — is the process healthy?"""
    return {"status": "alive"}
