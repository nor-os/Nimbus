"""
Overview: Tests for the workflow execution service — start, cancel, retry, status queries.
Architecture: Unit tests for execution service (Section 5)
Dependencies: pytest, unittest.mock, app.services.workflow.execution_service
Concepts: Execution lifecycle, Temporal integration (mocked), concurrent limit, tenant isolation
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.workflow_definition import WorkflowDefinition, WorkflowDefinitionStatus
from app.models.workflow_execution import (
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowNodeExecution,
)
from app.services.workflow.execution_service import (
    WorkflowExecutionError,
    WorkflowExecutionService,
)


# ── Helpers ──────────────────────────────────────────────


def _make_definition(
    *,
    tenant_id="t1",
    status=WorkflowDefinitionStatus.ACTIVE,
    version=1,
    graph=None,
    max_concurrent=10,
):
    defn = MagicMock(spec=WorkflowDefinition)
    defn.id = uuid.uuid4()
    defn.tenant_id = tenant_id
    defn.name = "Test Workflow"
    defn.version = version
    defn.graph = graph or {
        "nodes": [
            {"id": "s", "type": "start", "config": {}},
            {"id": "e", "type": "end", "config": {}},
        ],
        "connections": [{"source": "s", "target": "e"}],
    }
    defn.status = status
    defn.timeout_seconds = 3600
    defn.max_concurrent = max_concurrent
    defn.deleted_at = None
    return defn


def _make_execution(
    *,
    tenant_id="t1",
    status=WorkflowExecutionStatus.RUNNING,
    definition_id=None,
    is_test=False,
    input_data=None,
):
    execution = MagicMock(spec=WorkflowExecution)
    execution.id = uuid.uuid4()
    execution.tenant_id = tenant_id
    execution.definition_id = definition_id or uuid.uuid4()
    execution.definition_version = 1
    execution.temporal_workflow_id = f"wf-{uuid.uuid4()}"
    execution.status = status
    execution.input = input_data or {}
    execution.output = None
    execution.error = None
    execution.started_by = "user1"
    execution.started_at = datetime.now(UTC)
    execution.completed_at = None
    execution.is_test = is_test
    execution.node_executions = []
    return execution


# ── Start Tests ──────────────────────────────────────────


class TestExecutionStart:
    @pytest.mark.asyncio
    async def test_start_creates_execution(self):
        defn = _make_definition()
        db = AsyncMock()

        # Mock: first execute returns definition, second returns running count
        def_result = MagicMock()
        def_result.scalar_one_or_none.return_value = defn
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        db.execute.side_effect = [def_result, count_result]

        service = WorkflowExecutionService(db)

        # Mock Temporal client
        with patch("app.services.workflow.execution_service.WorkflowCompiler") as MockCompiler:
            mock_plan = MagicMock()
            mock_plan.to_json.return_value = "{}"
            MockCompiler.return_value.compile.return_value = mock_plan
            service._compiler = MockCompiler.return_value

            # Patch temporal import
            with patch(
                "app.services.workflow.execution_service.WorkflowExecutionService.start",
                wraps=service.start,
            ):
                # We'll test at a higher level — the start method should create a record
                result = await service.start(
                    tenant_id="t1",
                    started_by="user1",
                    definition_id=str(defn.id),
                    input_data={"key": "value"},
                )

                assert result.tenant_id == "t1"
                assert result.status == WorkflowExecutionStatus.PENDING
                db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_not_found(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="not found"):
            await service.start(
                tenant_id="t1",
                started_by="user1",
                definition_id="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_start_not_active_fails(self):
        defn = _make_definition(status=WorkflowDefinitionStatus.DRAFT)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = defn
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="active"):
            await service.start(
                tenant_id="t1",
                started_by="user1",
                definition_id=str(defn.id),
            )

    @pytest.mark.asyncio
    async def test_start_concurrent_limit(self):
        defn = _make_definition(max_concurrent=2)
        db = AsyncMock()

        def_result = MagicMock()
        def_result.scalar_one_or_none.return_value = defn
        count_result = MagicMock()
        count_result.scalar.return_value = 2  # at limit
        db.execute.side_effect = [def_result, count_result]

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="Concurrent execution limit"):
            await service.start(
                tenant_id="t1",
                started_by="user1",
                definition_id=str(defn.id),
            )

    @pytest.mark.asyncio
    async def test_start_test_skips_active_check(self):
        """Test runs skip the active status check."""
        defn = _make_definition(status=WorkflowDefinitionStatus.DRAFT)
        db = AsyncMock()

        def_result = MagicMock()
        def_result.scalar_one_or_none.return_value = defn
        db.execute.return_value = def_result

        service = WorkflowExecutionService(db)
        mock_plan = MagicMock()
        mock_plan.to_json.return_value = "{}"
        service._compiler.compile = MagicMock(return_value=mock_plan)

        result = await service.start(
            tenant_id="t1",
            started_by="user1",
            definition_id=str(defn.id),
            is_test=True,
        )

        assert result.is_test is True
        assert result.status == WorkflowExecutionStatus.PENDING

    @pytest.mark.asyncio
    async def test_start_no_graph_fails(self):
        defn = MagicMock()
        defn.id = uuid.uuid4()
        defn.tenant_id = "t1"
        defn.status = WorkflowDefinitionStatus.ACTIVE
        defn.max_concurrent = 10
        defn.graph = None  # No graph
        defn.deleted_at = None
        db = AsyncMock()

        def_result = MagicMock()
        def_result.scalar_one_or_none.return_value = defn
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        db.execute.side_effect = [def_result, count_result]

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="no graph"):
            await service.start(
                tenant_id="t1",
                started_by="user1",
                definition_id=str(defn.id),
            )


# ── Cancel Tests ─────────────────────────────────────────


class TestExecutionCancel:
    @pytest.mark.asyncio
    async def test_cancel_running(self):
        execution = _make_execution(status=WorkflowExecutionStatus.RUNNING)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = execution
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        # Patch temporal
        with patch("app.core.temporal.get_temporal_client", new_callable=AsyncMock) as mock_client:
            mock_handle = AsyncMock()
            mock_client.return_value.get_workflow_handle.return_value = mock_handle

            result = await service.cancel(
                tenant_id="t1", execution_id=str(execution.id)
            )

            assert result is execution
            assert execution.status == WorkflowExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_pending(self):
        execution = _make_execution(status=WorkflowExecutionStatus.PENDING)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = execution
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with patch("app.core.temporal.get_temporal_client", new_callable=AsyncMock):
            result = await service.cancel(
                tenant_id="t1", execution_id=str(execution.id)
            )
            assert execution.status == WorkflowExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_fails(self):
        execution = _make_execution(status=WorkflowExecutionStatus.COMPLETED)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = execution
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="pending or running"):
            await service.cancel(
                tenant_id="t1", execution_id=str(execution.id)
            )

    @pytest.mark.asyncio
    async def test_cancel_not_found(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="not found"):
            await service.cancel(
                tenant_id="t1", execution_id="nonexistent"
            )


# ── Retry Tests ──────────────────────────────────────────


class TestExecutionRetry:
    @pytest.mark.asyncio
    async def test_retry_non_failed_fails(self):
        execution = _make_execution(status=WorkflowExecutionStatus.RUNNING)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = execution
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)

        with pytest.raises(WorkflowExecutionError, match="failed"):
            await service.retry(
                tenant_id="t1",
                execution_id=str(execution.id),
                started_by="user1",
            )


# ── Get/List Tests ───────────────────────────────────────


class TestExecutionQueries:
    @pytest.mark.asyncio
    async def test_get_execution(self):
        execution = _make_execution()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = execution
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)
        result = await service.get(tenant_id="t1", execution_id=str(execution.id))

        assert result is execution

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)
        result = await service.get(tenant_id="t1", execution_id="nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_executions(self):
        executions = [_make_execution(), _make_execution()]
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = executions
        db.execute.return_value = result_mock

        service = WorkflowExecutionService(db)
        results = await service.list(tenant_id="t1")

        assert len(results) == 2
