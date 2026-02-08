"""
Overview: Tenant-aware database session factories that set search_path and RLS variables.
Architecture: Tenant-scoped session management (Section 3.1, 4.2)
Dependencies: sqlalchemy, app.db.session, app.services.tenant.schema_manager
Concepts: Multi-tenancy, PostgreSQL search_path, RLS session variables
"""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.services.tenant.schema_manager import get_schema_name


async def get_tenant_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session scoped to a specific tenant via search_path and RLS variable."""
    uuid.UUID(tenant_id)  # Validate
    schema_name = get_schema_name(tenant_id)

    async with async_session_factory() as session:
        try:
            await session.execute(
                text(f'SET search_path TO "{schema_name}", public')
            )
            await session.execute(
                text("SET app.current_tenant_id = :tid").bindparams(tid=tenant_id)
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_provider_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a session with provider-level access (bypasses RLS)."""
    async with async_session_factory() as session:
        try:
            await session.execute(text("SET app.is_provider_context = 'true'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
