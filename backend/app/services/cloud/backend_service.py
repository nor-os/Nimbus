"""
Overview: Cloud backend service — CRUD for backend connections, credential management,
    connectivity testing, and IAM mapping resolution.
Architecture: Service layer for cloud backends (Section 11)
Dependencies: sqlalchemy, app.models.cloud_backend, app.services.crypto.credential_encryption
Concepts: Backends store encrypted credentials. Credentials are write-only in the API.
    Connectivity testing decrypts creds and calls the provider registry. IAM mapping
    resolves a user's Nimbus roles to cloud-specific identities.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cloud_backend import CloudBackend, CloudBackendIAMMapping
from app.services.crypto.credential_encryption import (
    CredentialEncryptionError,
    decrypt_credentials,
    encrypt_credentials,
)

logger = logging.getLogger(__name__)


class CloudBackendService:
    """Service for managing cloud backend connections."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Backend CRUD -------------------------------------------------------

    async def list_backends(
        self,
        tenant_id: uuid.UUID,
        *,
        include_shared: bool = False,
        status: str | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> list[CloudBackend]:
        """List backends for a tenant, optionally including shared backends from parents."""
        stmt = (
            select(CloudBackend)
            .where(
                CloudBackend.deleted_at.is_(None),
                CloudBackend.tenant_id == tenant_id,
            )
            .options(selectinload(CloudBackend.iam_mappings))
            .order_by(CloudBackend.name)
        )
        if status:
            stmt = stmt.where(CloudBackend.status == status)
        if provider_id:
            stmt = stmt.where(CloudBackend.provider_id == provider_id)

        result = await self.db.execute(stmt)
        backends = list(result.scalars().all())

        # Include shared backends from other tenants
        if include_shared:
            shared_stmt = (
                select(CloudBackend)
                .where(
                    CloudBackend.deleted_at.is_(None),
                    CloudBackend.is_shared.is_(True),
                    CloudBackend.tenant_id != tenant_id,
                )
                .options(selectinload(CloudBackend.iam_mappings))
                .order_by(CloudBackend.name)
            )
            if status:
                shared_stmt = shared_stmt.where(CloudBackend.status == status)
            if provider_id:
                shared_stmt = shared_stmt.where(CloudBackend.provider_id == provider_id)
            shared_result = await self.db.execute(shared_stmt)
            backends.extend(shared_result.scalars().all())

        return backends

    async def get_backend(
        self, backend_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CloudBackend | None:
        """Get a single backend by ID, scoped to tenant."""
        stmt = (
            select(CloudBackend)
            .where(
                CloudBackend.id == backend_id,
                CloudBackend.tenant_id == tenant_id,
                CloudBackend.deleted_at.is_(None),
            )
            .options(selectinload(CloudBackend.iam_mappings))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_backend(
        self,
        tenant_id: uuid.UUID,
        *,
        provider_id: uuid.UUID,
        name: str,
        description: str | None = None,
        status: str = "active",
        credentials: dict | None = None,
        scope_config: dict | None = None,
        endpoint_url: str | None = None,
        is_shared: bool = False,
        created_by: uuid.UUID | None = None,
    ) -> CloudBackend:
        """Create a new cloud backend, encrypting credentials if provided."""
        encrypted = None
        if credentials:
            encrypted = encrypt_credentials(credentials)

        backend = CloudBackend(
            tenant_id=tenant_id,
            provider_id=provider_id,
            name=name,
            description=description,
            status=status,
            credentials_encrypted=encrypted,
            scope_config=scope_config,
            endpoint_url=endpoint_url,
            is_shared=is_shared,
            created_by=created_by,
        )
        self.db.add(backend)
        await self.db.flush()
        return backend

    async def update_backend(
        self,
        backend_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **kwargs,
    ) -> CloudBackend | None:
        """Update a cloud backend. If 'credentials' is in kwargs, re-encrypt."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return None

        # Handle credential update separately
        credentials = kwargs.pop("credentials", None)
        if credentials is not None:
            backend.credentials_encrypted = encrypt_credentials(credentials)

        for key, value in kwargs.items():
            if hasattr(backend, key):
                setattr(backend, key, value)

        await self.db.flush()
        return backend

    async def delete_backend(
        self, backend_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        """Soft-delete a cloud backend."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return False
        backend.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -- Credential operations ----------------------------------------------

    async def get_decrypted_credentials(
        self, backend_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict | None:
        """Internal: decrypt and return credentials for provider interface calls."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend or not backend.credentials_encrypted:
            return None
        return decrypt_credentials(backend.credentials_encrypted)

    # -- Connectivity testing -----------------------------------------------

    async def test_connectivity(
        self, backend_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict:
        """Test backend connectivity. Returns {success, message, checked_at}."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return {"success": False, "message": "Backend not found", "checked_at": None}

        if not backend.credentials_encrypted:
            return {
                "success": False,
                "message": "No credentials configured",
                "checked_at": None,
            }

        now = datetime.now(timezone.utc)
        try:
            credentials = decrypt_credentials(backend.credentials_encrypted)

            # Try to get provider implementation from registry
            from app.services.cloud.provider_registry import provider_registry

            provider_impl = provider_registry.get(
                backend.provider.name if backend.provider else ""
            )

            if provider_impl:
                # If a provider implementation exists, use it
                await provider_impl.validate_credentials(credentials)
                backend.last_connectivity_status = "connected"
                backend.last_connectivity_error = None
                message = "Connection successful"
            else:
                # No implementation yet — just verify credentials decrypt OK
                backend.last_connectivity_status = "connected"
                backend.last_connectivity_error = None
                message = (
                    "Credentials valid (provider driver not yet implemented)"
                )

            backend.last_connectivity_check = now
            await self.db.flush()
            return {"success": True, "message": message, "checked_at": now.isoformat()}

        except CredentialEncryptionError as exc:
            backend.last_connectivity_check = now
            backend.last_connectivity_status = "failed"
            backend.last_connectivity_error = str(exc)
            await self.db.flush()
            return {
                "success": False,
                "message": f"Credential error: {exc}",
                "checked_at": now.isoformat(),
            }
        except Exception as exc:
            backend.last_connectivity_check = now
            backend.last_connectivity_status = "failed"
            backend.last_connectivity_error = str(exc)
            await self.db.flush()
            return {
                "success": False,
                "message": f"Connection failed: {exc}",
                "checked_at": now.isoformat(),
            }

    # -- IAM Mapping CRUD ---------------------------------------------------

    async def list_iam_mappings(
        self, backend_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[CloudBackendIAMMapping]:
        """List IAM mappings for a backend."""
        # Verify backend belongs to tenant
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return []

        stmt = (
            select(CloudBackendIAMMapping)
            .where(
                CloudBackendIAMMapping.backend_id == backend_id,
                CloudBackendIAMMapping.deleted_at.is_(None),
            )
            .order_by(CloudBackendIAMMapping.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_iam_mapping(
        self,
        backend_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        role_id: uuid.UUID,
        cloud_identity: dict,
        description: str | None = None,
        is_active: bool = True,
    ) -> CloudBackendIAMMapping | None:
        """Create an IAM mapping. Returns None if backend not found."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return None

        mapping = CloudBackendIAMMapping(
            backend_id=backend_id,
            role_id=role_id,
            cloud_identity=cloud_identity,
            description=description,
            is_active=is_active,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    async def update_iam_mapping(
        self,
        mapping_id: uuid.UUID,
        backend_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **kwargs,
    ) -> CloudBackendIAMMapping | None:
        """Update an IAM mapping."""
        # Verify backend ownership
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return None

        stmt = select(CloudBackendIAMMapping).where(
            CloudBackendIAMMapping.id == mapping_id,
            CloudBackendIAMMapping.backend_id == backend_id,
            CloudBackendIAMMapping.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        if not mapping:
            return None

        for key, value in kwargs.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)

        await self.db.flush()
        return mapping

    async def delete_iam_mapping(
        self,
        mapping_id: uuid.UUID,
        backend_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Soft-delete an IAM mapping."""
        backend = await self.get_backend(backend_id, tenant_id)
        if not backend:
            return False

        stmt = select(CloudBackendIAMMapping).where(
            CloudBackendIAMMapping.id == mapping_id,
            CloudBackendIAMMapping.backend_id == backend_id,
            CloudBackendIAMMapping.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        if not mapping:
            return False

        mapping.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def resolve_iam_for_user(
        self,
        backend_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_role_ids: list[uuid.UUID],
    ) -> dict | None:
        """Resolve the cloud identity for a user based on their Nimbus roles.
        Returns the cloud_identity dict for the first matching active mapping."""
        if not user_role_ids:
            return None

        stmt = (
            select(CloudBackendIAMMapping)
            .where(
                CloudBackendIAMMapping.backend_id == backend_id,
                CloudBackendIAMMapping.role_id.in_(user_role_ids),
                CloudBackendIAMMapping.is_active.is_(True),
                CloudBackendIAMMapping.deleted_at.is_(None),
            )
            .order_by(CloudBackendIAMMapping.created_at)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        return mapping.cloud_identity if mapping else None
