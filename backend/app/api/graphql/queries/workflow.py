"""
Overview: GraphQL queries for workflow definitions, executions, node types, and validation.
Architecture: Query resolvers for workflow editor (Section 7.2)
Dependencies: strawberry, app.services.workflow.*, app.api.graphql.auth
Concepts: Workflow queries, definition listing, execution monitoring, node type discovery
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.workflow import (
    NodeTypeInfoType,
    PortDefType,
    ValidationErrorType,
    ValidationResultType,
    WorkflowDefinitionStatusGQL,
    WorkflowDefinitionType,
    WorkflowExecutionStatusGQL,
    WorkflowExecutionType,
    WorkflowNodeExecutionStatusGQL,
    WorkflowNodeExecutionType,
)


def _definition_to_type(d) -> WorkflowDefinitionType:
    return WorkflowDefinitionType(
        id=d.id,
        tenant_id=d.tenant_id,
        name=d.name,
        description=d.description,
        version=d.version,
        graph=d.graph,
        status=WorkflowDefinitionStatusGQL(d.status.value),
        created_by=d.created_by,
        timeout_seconds=d.timeout_seconds,
        max_concurrent=d.max_concurrent,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _node_execution_to_type(ne) -> WorkflowNodeExecutionType:
    return WorkflowNodeExecutionType(
        id=ne.id,
        execution_id=ne.execution_id,
        node_id=ne.node_id,
        node_type=ne.node_type,
        status=WorkflowNodeExecutionStatusGQL(ne.status.value),
        input=ne.input,
        output=ne.output,
        error=ne.error,
        started_at=ne.started_at,
        completed_at=ne.completed_at,
        attempt=ne.attempt,
    )


def _execution_to_type(e) -> WorkflowExecutionType:
    return WorkflowExecutionType(
        id=e.id,
        tenant_id=e.tenant_id,
        definition_id=e.definition_id,
        definition_version=e.definition_version,
        temporal_workflow_id=e.temporal_workflow_id,
        status=WorkflowExecutionStatusGQL(e.status.value),
        input=e.input,
        output=e.output,
        error=e.error,
        started_by=e.started_by,
        started_at=e.started_at,
        completed_at=e.completed_at,
        is_test=e.is_test,
        node_executions=[
            _node_execution_to_type(ne) for ne in (e.node_executions or [])
        ],
    )


@strawberry.type
class WorkflowQuery:

    @strawberry.field
    async def workflow_definitions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[WorkflowDefinitionType]:
        """List workflow definitions for a tenant."""
        await check_graphql_permission(info, "workflow:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            definitions = await svc.list(str(tenant_id), status, offset, limit)
            return [_definition_to_type(d) for d in definitions]

    @strawberry.field
    async def workflow_definition(
        self, info: Info, tenant_id: uuid.UUID, definition_id: uuid.UUID
    ) -> WorkflowDefinitionType | None:
        """Get a workflow definition by ID."""
        await check_graphql_permission(info, "workflow:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            d = await svc.get(str(tenant_id), str(definition_id))
            return _definition_to_type(d) if d else None

    @strawberry.field
    async def workflow_definition_versions(
        self, info: Info, tenant_id: uuid.UUID, name: str
    ) -> list[WorkflowDefinitionType]:
        """Get all versions of a workflow definition by name."""
        await check_graphql_permission(info, "workflow:definition:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.workflow.definition_service import WorkflowDefinitionService

        async with async_session_factory() as db:
            svc = WorkflowDefinitionService(db)
            versions = await svc.get_versions(str(tenant_id), name)
            return [_definition_to_type(d) for d in versions]

    @strawberry.field
    async def workflow_executions(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[WorkflowExecutionType]:
        """List workflow executions for a tenant."""
        await check_graphql_permission(info, "workflow:execution:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            executions = await svc.list(
                str(tenant_id),
                str(definition_id) if definition_id else None,
                status,
                offset,
                limit,
            )
            return [_execution_to_type(e) for e in executions]

    @strawberry.field
    async def workflow_execution(
        self, info: Info, tenant_id: uuid.UUID, execution_id: uuid.UUID
    ) -> WorkflowExecutionType | None:
        """Get a workflow execution by ID with node executions."""
        await check_graphql_permission(info, "workflow:execution:read", str(tenant_id))

        from app.db.session import async_session_factory
        from app.services.workflow.execution_service import WorkflowExecutionService

        async with async_session_factory() as db:
            svc = WorkflowExecutionService(db)
            e = await svc.get(str(tenant_id), str(execution_id))
            return _execution_to_type(e) if e else None

    @strawberry.field
    async def node_types(self, info: Info) -> list[NodeTypeInfoType]:
        """List all registered workflow node types."""
        from app.services.workflow.node_registry import get_registry

        # Ensure node types are registered
        import app.services.workflow.node_types  # noqa: F401

        registry = get_registry()
        result: list[NodeTypeInfoType] = []
        for defn in registry.list_all():
            result.append(NodeTypeInfoType(
                type_id=defn.type_id,
                label=defn.label,
                category=defn.category.value,
                description=defn.description,
                icon=defn.icon,
                ports=[
                    PortDefType(
                        name=p.name,
                        direction=p.direction.value,
                        port_type=p.port_type.value,
                        label=p.label,
                        required=p.required,
                        multiple=p.multiple,
                    )
                    for p in defn.ports
                ],
                config_schema=defn.config_schema,
                is_marker=defn.is_marker,
            ))
        return result

    @strawberry.field
    async def validate_workflow_graph(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        graph: strawberry.scalars.JSON,
    ) -> ValidationResultType:
        """Validate a workflow graph without saving it."""
        await check_graphql_permission(info, "workflow:definition:read", str(tenant_id))

        from app.services.workflow.graph_validator import GraphValidator

        validator = GraphValidator()
        result = validator.validate(graph)
        return ValidationResultType(
            valid=result.valid,
            errors=[
                ValidationErrorType(
                    node_id=e.node_id, message=e.message, severity=e.severity
                )
                for e in result.errors
            ],
            warnings=[
                ValidationErrorType(
                    node_id=w.node_id, message=w.message, severity=w.severity
                )
                for w in result.warnings
            ],
        )
