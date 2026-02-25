"""
Overview: GraphQL request context with shared DB session, permission cache, and dataloaders.
Architecture: Per-request context passed to all resolvers via Strawberry Info (Section 7.2)
Dependencies: strawberry, sqlalchemy, app.db.session, app.services
Concepts: Shared session eliminates per-resolver connection overhead. Permission cache avoids
    redundant DB lookups. Dataloaders batch N+1 queries into single bulk fetches.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext

from app.db.session import async_session_factory

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.websockets import WebSocket


@dataclass
class NimbusContext(BaseContext):
    """Per-request GraphQL context with shared resources.

    Provides:
    - A single AsyncSession shared across all resolvers in one request
    - A permission cache to avoid repeated permission DB queries
    - Dataloaders for batch-fetching related entities
    """

    _session: AsyncSession | None = field(default=None, init=False, repr=False)
    _permission_cache: dict[str, bool] = field(default_factory=dict, init=False, repr=False)
    _loaders: dict[str, DataLoader] = field(default_factory=dict, init=False, repr=False)

    async def session(self) -> AsyncSession:
        """Lazily create and return the shared DB session for this request."""
        if self._session is None:
            self._session = async_session_factory()
        return self._session

    async def close(self) -> None:
        """Close the shared session at the end of the request."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    # ── Permission cache ──────────────────────────────────────────────

    def permission_cache_key(self, user_id: str, permission_key: str, tenant_id: str) -> str:
        return f"{user_id}:{permission_key}:{tenant_id}"

    async def check_permission_cached(
        self, user_id: str, permission_key: str, tenant_id: str
    ) -> bool:
        """Check permission, returning cached result if already checked this request."""
        cache_key = self.permission_cache_key(user_id, permission_key, tenant_id)
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        from app.services.permission.engine import PermissionEngine

        db = await self.session()
        engine = PermissionEngine(db)
        allowed, _source = await engine.check_permission(user_id, permission_key, tenant_id)
        self._permission_cache[cache_key] = allowed
        return allowed

    # ── Dataloaders ───────────────────────────────────────────────────

    @property
    def ci_class_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load CI classes by ID."""
        if "ci_class" not in self._loaders:
            self._loaders["ci_class"] = DataLoader(load_fn=self._load_ci_classes)
        return self._loaders["ci_class"]

    @property
    def backend_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load cloud backends by ID."""
        if "backend" not in self._loaders:
            self._loaders["backend"] = DataLoader(load_fn=self._load_backends)
        return self._loaders["backend"]

    @property
    def user_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load users by ID."""
        if "user" not in self._loaders:
            self._loaders["user"] = DataLoader(load_fn=self._load_users)
        return self._loaders["user"]

    @property
    def relationship_type_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load relationship types by ID."""
        if "rel_type" not in self._loaders:
            self._loaders["rel_type"] = DataLoader(load_fn=self._load_relationship_types)
        return self._loaders["rel_type"]

    @property
    def ci_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load CIs by ID (for relationship source/target resolution)."""
        if "ci" not in self._loaders:
            self._loaders["ci"] = DataLoader(load_fn=self._load_cis)
        return self._loaders["ci"]

    @property
    def semantic_type_loader(self) -> DataLoader[uuid.UUID, object | None]:
        """Batch-load semantic types by ID."""
        if "semantic_type" not in self._loaders:
            self._loaders["semantic_type"] = DataLoader(load_fn=self._load_semantic_types)
        return self._loaders["semantic_type"]

    # ── Batch-load implementations ────────────────────────────────────

    async def _load_ci_classes(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.cmdb.ci_class import CIClass

        db = await self.session()
        result = await db.execute(select(CIClass).where(CIClass.id.in_(keys)))
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]

    async def _load_backends(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.cloud_backend import CloudBackend

        db = await self.session()
        result = await db.execute(select(CloudBackend).where(CloudBackend.id.in_(keys)))
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]

    async def _load_users(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.user import User

        db = await self.session()
        result = await db.execute(select(User).where(User.id.in_(keys)))
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]

    async def _load_relationship_types(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.cmdb.relationship_type import RelationshipType

        db = await self.session()
        result = await db.execute(select(RelationshipType).where(RelationshipType.id.in_(keys)))
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]

    async def _load_cis(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.cmdb.configuration_item import ConfigurationItem

        db = await self.session()
        result = await db.execute(
            select(ConfigurationItem)
            .options(selectinload(ConfigurationItem.ci_class))
            .where(ConfigurationItem.id.in_(keys))
        )
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]

    async def _load_semantic_types(self, keys: list[uuid.UUID]) -> list[object | None]:
        from app.models.semantic import SemanticType

        db = await self.session()
        result = await db.execute(select(SemanticType).where(SemanticType.id.in_(keys)))
        by_id = {row.id: row for row in result.scalars().all()}
        return [by_id.get(k) for k in keys]


async def get_context(request: Request = None, websocket: WebSocket = None) -> NimbusContext:
    """Strawberry context getter — creates a NimbusContext per request."""
    ctx = NimbusContext()
    # Strawberry's BaseContext sets request/websocket automatically
    return ctx
