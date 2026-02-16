"""
Overview: GraphQL mutations for workflow definitions and executions.
Architecture: Mutation resolvers for workflow editor (Section 7.2)
Dependencies: strawberry, app.services.workflow.*, app.api.graphql.auth
Concepts: Workflow CRUD, publish, clone, execution lifecycle
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.workflow import _definition_to_type, _execution_to_type
from app.api.graphql.types.workflow import (
    GenerateDeploymentWorkflowInput,
    WorkflowDefinitionCreateInput,
    WorkflowDefinitionType,
    WorkflowDefinitionUpdateInput,
    WorkflowExecutionStartInput,
    WorkflowExecutionType,
)

logger = logging.getLogger(__name__)


@strawberry.type
class WorkflowMutation:

    @strawberry.mutation
    async def create_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: WorkflowDefinitionCreateInput,
    ) -> WorkflowDefinitionType:
        """Create a new draft workflow definition."""
        user_id = await check_graphql_permission(
            info, "workflow:definition:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            data = {
                "name": input.name,
                "description": input.description,
                "graph": input.graph,
                "timeout_seconds": input.timeout_seconds,
                "max_concurrent": input.max_concurrent,
            }
            if input.workflow_type:
                data["workflow_type"] = input.workflow_type
            if input.applicable_semantic_type_id is not None:
                data["applicable_semantic_type_id"] = str(input.applicable_semantic_type_id)
            if input.applicable_provider_id is not None:
                data["applicable_provider_id"] = str(input.applicable_provider_id)
            d = await svc.create(str(tenant_id), str(user_id), data)
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def update_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
        input: WorkflowDefinitionUpdateInput,
    ) -> WorkflowDefinitionType | None:
        """Update a draft workflow definition."""
        await check_graphql_permission(
            info, "workflow:definition:update", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            data = {}
            if input.name is not None:
                data["name"] = input.name
            if input.description is not None:
                data["description"] = input.description
            if input.graph is not None:
                data["graph"] = input.graph
            if input.timeout_seconds is not None:
                data["timeout_seconds"] = input.timeout_seconds
            if input.max_concurrent is not None:
                data["max_concurrent"] = input.max_concurrent
            if input.applicable_semantic_type_id is not strawberry.UNSET:
                val = input.applicable_semantic_type_id
                data["applicable_semantic_type_id"] = (
                    str(val) if val else None
                )
            if input.applicable_provider_id is not strawberry.UNSET:
                data["applicable_provider_id"] = (
                    str(input.applicable_provider_id) if input.applicable_provider_id else None
                )

            d = await svc.update(str(tenant_id), str(definition_id), data)
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def publish_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
    ) -> WorkflowDefinitionType:
        """Validate and publish a draft workflow definition."""
        await check_graphql_permission(
            info, "workflow:definition:publish", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            d = await svc.publish(str(tenant_id), str(definition_id))
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def archive_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
    ) -> WorkflowDefinitionType:
        """Archive a workflow definition."""
        await check_graphql_permission(
            info, "workflow:definition:update", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            d = await svc.archive(str(tenant_id), str(definition_id))
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def clone_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
    ) -> WorkflowDefinitionType:
        """Clone a workflow definition as a new draft."""
        user_id = await check_graphql_permission(
            info, "workflow:definition:create", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            d = await svc.clone(str(tenant_id), str(definition_id), str(user_id))
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def delete_workflow_definition(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a workflow definition."""
        await check_graphql_permission(
            info, "workflow:definition:delete", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            result = await svc.delete(str(tenant_id), str(definition_id))
            await db.commit()
            return result

    @strawberry.mutation
    async def start_workflow_execution(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: WorkflowExecutionStartInput,
    ) -> WorkflowExecutionType:
        """Start a workflow execution."""
        user_id = await check_graphql_permission(
            info, "workflow:execution:start", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            e = await svc.start(
                tenant_id=str(tenant_id),
                started_by=str(user_id),
                definition_id=str(input.definition_id),
                input_data=input.input,
                is_test=input.is_test,
                mock_configs=input.mock_configs,
            )
            result = _execution_to_type(e)
            await db.commit()
            return result

    @strawberry.mutation
    async def cancel_workflow_execution(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        execution_id: uuid.UUID,
    ) -> WorkflowExecutionType:
        """Cancel a running workflow execution."""
        await check_graphql_permission(
            info, "workflow:execution:cancel", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            e = await svc.cancel(str(tenant_id), str(execution_id))
            result = _execution_to_type(e)
            await db.commit()
            return result

    @strawberry.mutation
    async def retry_workflow_execution(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        execution_id: uuid.UUID,
    ) -> WorkflowExecutionType:
        """Retry a failed workflow execution."""
        user_id = await check_graphql_permission(
            info, "workflow:execution:start", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            e = await svc.retry(str(tenant_id), str(execution_id), str(user_id))
            result = _execution_to_type(e)
            await db.commit()
            return result

    @strawberry.mutation
    async def generate_deployment_workflow(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: GenerateDeploymentWorkflowInput,
    ) -> WorkflowDefinitionType:
        """Generate a deployment workflow from a published topology."""
        user_id = await check_graphql_permission(
            info, "workflow:deployment:generate", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.deployment_generator import (
            DeploymentWorkflowGenerator,
            GeneratorOptions,
        )

        async with async_session_factory() as db:
            generator = DeploymentWorkflowGenerator(db)
            options = GeneratorOptions(
                add_approval_gates=input.add_approval_gates,
                add_notifications=input.add_notifications,
            )
            d = await generator.generate_from_topology(
                tenant_id=str(tenant_id),
                topology_id=str(input.topology_id),
                created_by=str(user_id),
                options=options,
            )
            result = _definition_to_type(d)
            await db.commit()
            return result

    @strawberry.mutation
    async def seed_system_workflows(
        self,
        info: Info,
        tenant_id: uuid.UUID,
    ) -> list[WorkflowDefinitionType]:
        """Seed system workflow templates for a tenant (idempotent)."""
        user_id = await check_graphql_permission(
            info, "workflow:system:manage", str(tenant_id)
        )

        from app.db.session import async_session_factory
        from app.services.workflow.system_workflow_seeder import SystemWorkflowSeeder

        async with async_session_factory() as db:
            seeder = SystemWorkflowSeeder(db)
            created = await seeder.seed_for_tenant(str(tenant_id), str(user_id))
            await db.flush()
            # Refresh objects to load server-generated columns (created_at, updated_at)
            # before converting — accessing them lazily fails in async context
            for d in created:
                await db.refresh(d)
            result = [_definition_to_type(d) for d in created]
            await db.commit()
            return result
