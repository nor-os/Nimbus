"""
Overview: GraphQL mutations for cloud backend CRUD, connectivity testing, and IAM mapping management.
Architecture: GraphQL mutation resolvers for cloud backend management (Section 11)
Dependencies: strawberry, app.services.cloud.backend_service
Concepts: Create/update/delete with permission checks. Credentials are write-only — encrypted on
    save, never returned. Test connectivity decrypts and validates against provider.
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.cloud_backend import _backend_to_gql, _iam_mapping_to_gql
from app.api.graphql.types.cloud_backend import (
    CloudBackendIAMMappingInput,
    CloudBackendIAMMappingType,
    CloudBackendIAMMappingUpdateInput,
    CloudBackendInput,
    CloudBackendType,
    CloudBackendUpdateInput,
    ConnectivityTestResult,
)


@strawberry.type
class CloudBackendMutation:
    # -- Backend CRUD -------------------------------------------------------

    @strawberry.mutation
    async def create_cloud_backend(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: CloudBackendInput,
    ) -> CloudBackendType:
        """Create a new cloud backend connection."""
        await check_graphql_permission(info, "cloud:backend:create", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        # Extract user ID from context if available
        user_id = None
        request = info.context.get("request")
        if request and hasattr(request, "state") and hasattr(request.state, "user_id"):
            user_id = request.state.user_id

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            backend = await service.create_backend(
                tenant_id,
                provider_id=input.provider_id,
                name=input.name,
                description=input.description,
                status=input.status,
                credentials=input.credentials,
                scope_config=input.scope_config,
                endpoint_url=input.endpoint_url,
                is_shared=input.is_shared,
                created_by=user_id,
            )
            await db.commit()
            # Re-fetch with relationships
            backend = await service.get_backend(backend.id, tenant_id)
            return _backend_to_gql(backend)

    @strawberry.mutation
    async def update_cloud_backend(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
        input: CloudBackendUpdateInput,
    ) -> CloudBackendType | None:
        """Update a cloud backend connection."""
        await check_graphql_permission(info, "cloud:backend:update", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.status is not None:
            kwargs["status"] = input.status
        if input.credentials is not strawberry.UNSET:
            kwargs["credentials"] = input.credentials
        if input.scope_config is not strawberry.UNSET:
            kwargs["scope_config"] = input.scope_config
        if input.endpoint_url is not strawberry.UNSET:
            kwargs["endpoint_url"] = input.endpoint_url
        if input.is_shared is not None:
            kwargs["is_shared"] = input.is_shared

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            backend = await service.update_backend(id, tenant_id, **kwargs)
            if not backend:
                return None
            await db.commit()
            return _backend_to_gql(backend)

    @strawberry.mutation
    async def delete_cloud_backend(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> bool:
        """Delete a cloud backend (soft delete)."""
        await check_graphql_permission(info, "cloud:backend:delete", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            deleted = await service.delete_backend(id, tenant_id)
            await db.commit()
            return deleted

    # -- Connectivity testing -----------------------------------------------

    @strawberry.mutation
    async def test_cloud_backend_connectivity(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        id: uuid.UUID,
    ) -> ConnectivityTestResult:
        """Test connectivity to a cloud backend."""
        await check_graphql_permission(info, "cloud:backend:test", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            result = await service.test_connectivity(id, tenant_id)
            await db.commit()
            return ConnectivityTestResult(
                success=result["success"],
                message=result["message"],
                checked_at=result.get("checked_at"),
            )

    # -- IAM Mapping CRUD ---------------------------------------------------

    @strawberry.mutation
    async def create_cloud_backend_iam_mapping(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        backend_id: uuid.UUID,
        input: CloudBackendIAMMappingInput,
    ) -> CloudBackendIAMMappingType | None:
        """Create an IAM mapping for a cloud backend."""
        await check_graphql_permission(info, "cloud:backend:manage_iam", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            mapping = await service.create_iam_mapping(
                backend_id,
                tenant_id,
                role_id=input.role_id,
                cloud_identity=input.cloud_identity,
                description=input.description,
                is_active=input.is_active,
            )
            if not mapping:
                return None
            await db.commit()
            await db.refresh(mapping, ["role"])
            return _iam_mapping_to_gql(mapping)

    @strawberry.mutation
    async def update_cloud_backend_iam_mapping(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        backend_id: uuid.UUID,
        id: uuid.UUID,
        input: CloudBackendIAMMappingUpdateInput,
    ) -> CloudBackendIAMMappingType | None:
        """Update an IAM mapping."""
        await check_graphql_permission(info, "cloud:backend:manage_iam", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        kwargs = {}
        if input.cloud_identity is not strawberry.UNSET:
            kwargs["cloud_identity"] = input.cloud_identity
        if input.description is not strawberry.UNSET:
            kwargs["description"] = input.description
        if input.is_active is not None:
            kwargs["is_active"] = input.is_active

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            mapping = await service.update_iam_mapping(
                id, backend_id, tenant_id, **kwargs
            )
            if not mapping:
                return None
            await db.commit()
            return _iam_mapping_to_gql(mapping)

    @strawberry.mutation
    async def delete_cloud_backend_iam_mapping(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        backend_id: uuid.UUID,
        id: uuid.UUID,
    ) -> bool:
        """Delete an IAM mapping (soft delete)."""
        await check_graphql_permission(info, "cloud:backend:manage_iam", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.cloud.backend_service import CloudBackendService

        async with async_session_factory() as db:
            service = CloudBackendService(db)
            deleted = await service.delete_iam_mapping(id, backend_id, tenant_id)
            await db.commit()
            return deleted
