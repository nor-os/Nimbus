"""
Overview: GraphQL queries for cloud backends — list, detail, IAM mappings, credential/scope schemas.
Architecture: GraphQL query resolvers for cloud backend management (Section 11)
Dependencies: strawberry, app.services.cloud.backend_service
Concepts: Read-only queries with permission checks. Credential schemas returned for dynamic forms.
"""

import uuid

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.cloud_backend import (
    CloudBackendIAMMappingType,
    CloudBackendType,
)


def _backend_to_gql(b) -> CloudBackendType:
    provider = b.provider
    active_mappings = [m for m in (b.iam_mappings or []) if m.deleted_at is None]
    return CloudBackendType(
        id=b.id,
        tenant_id=b.tenant_id,
        provider_id=b.provider_id,
        provider_name=provider.name if provider else "",
        provider_display_name=provider.display_name if provider else "",
        provider_icon=provider.icon if provider else None,
        name=b.name,
        description=b.description,
        status=b.status,
        has_credentials=b.credentials_encrypted is not None,
        credentials_schema_version=b.credentials_schema_version,
        scope_config=b.scope_config,
        endpoint_url=b.endpoint_url,
        is_shared=b.is_shared,
        last_connectivity_check=b.last_connectivity_check,
        last_connectivity_status=b.last_connectivity_status,
        last_connectivity_error=b.last_connectivity_error,
        iam_mapping_count=len(active_mappings),
        created_by=b.created_by,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


def _iam_mapping_to_gql(m) -> CloudBackendIAMMappingType:
    return CloudBackendIAMMappingType(
        id=m.id,
        backend_id=m.backend_id,
        role_id=m.role_id,
        role_name=m.role.name if m.role else "",
        cloud_identity=m.cloud_identity,
        description=m.description,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@strawberry.type
class CloudBackendQuery:
    @strawberry.field
    async def cloud_backends(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        include_shared: bool = False,
        status: str | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> list[CloudBackendType]:
        """List cloud backends for a tenant."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            backends = await service.list_backends(
                tenant_id,
                include_shared=include_shared,
                status=status,
                provider_id=provider_id,
            )
            return [_backend_to_gql(b) for b in backends]

    @strawberry.field
    async def tenant_backend(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> CloudBackendType | None:
        """Get the single cloud backend for a tenant (1:1 mapping)."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            backend = await service.get_tenant_backend(tenant_id)
            if not backend:
                return None
            return _backend_to_gql(backend)

    @strawberry.field
    async def cloud_backend(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> CloudBackendType | None:
        """Get a single cloud backend by ID."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            backend = await service.get_backend(id, tenant_id)
            if not backend:
                return None
            return _backend_to_gql(backend)

    @strawberry.field
    async def cloud_backend_iam_mappings(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        backend_id: uuid.UUID,
    ) -> list[CloudBackendIAMMappingType]:
        """List IAM mappings for a cloud backend."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            mappings = await service.list_iam_mappings(backend_id, tenant_id)
            return [_iam_mapping_to_gql(m) for m in mappings]

    @strawberry.field
    async def cloud_credential_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the credential JSON Schema for a provider (for dynamic forms)."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_credential_schema

        return get_credential_schema(provider_name)

    @strawberry.field
    async def cloud_scope_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the scope JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_scope_schema

        return get_scope_schema(provider_name)

    @strawberry.field
    async def backend_network_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (hub) network config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_network_schema

        return get_foundation_network_schema(provider_name)

    @strawberry.field
    async def foundation_network_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (hub) network config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_network_schema

        return get_foundation_network_schema(provider_name)

    @strawberry.field
    async def backend_iam_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (org) IAM config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_iam_schema

        return get_foundation_iam_schema(provider_name)

    @strawberry.field
    async def foundation_iam_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (org) IAM config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_iam_schema

        return get_foundation_iam_schema(provider_name)

    @strawberry.field
    async def backend_security_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (shared services) security config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_security_schema

        return get_foundation_security_schema(provider_name)

    @strawberry.field
    async def foundation_security_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the foundation (shared services) security config JSON Schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_foundation_security_schema

        return get_foundation_security_schema(provider_name)

    # ── Environment config schemas ────────────────────────────────

    @strawberry.field
    async def env_network_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the environment (spoke) network config schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_env_network_schema

        return get_env_network_schema(provider_name)

    @strawberry.field
    async def env_iam_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the environment access control schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_env_iam_schema

        return get_env_iam_schema(provider_name)

    @strawberry.field
    async def env_security_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the environment security config schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_env_security_schema

        return get_env_security_schema(provider_name)

    @strawberry.field
    async def env_monitoring_config_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the environment monitoring config schema for a provider."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_env_monitoring_schema

        return get_env_monitoring_schema(provider_name)

    @strawberry.field
    async def cloud_iam_identity_schema(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> JSON | None:
        """Get the IAM identity schema for a provider (for dynamic forms)."""
        await check_graphql_permission(info, "cloud:backend:read", str(tenant_id))

        from app.services.cloud.credential_schemas import get_iam_identity_schema

        return get_iam_identity_schema(provider_name)
