"""
Overview: Async SQLAlchemy engine and session factory for database access.
Architecture: Database layer providing sessions to services (Section 3.1, 4)
Dependencies: sqlalchemy[asyncio], asyncpg, app.core.config
Concepts: Async database access, connection pooling, session management
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_pool_stats() -> dict:
    """Return connection pool statistics for health/monitoring endpoints."""
    pool = engine.pool
    if isinstance(pool, AsyncAdaptedQueuePool):
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.status(),
        }
    return {"status": str(pool.status())}
