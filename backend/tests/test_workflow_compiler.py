"""
Overview: Tests for the workflow compiler — topological sort, parallel groups, loops, branches.
Architecture: Unit tests for graph-to-execution-plan compilation (Section 5)
Dependencies: pytest, app.services.workflow.compiler, app.services.workflow.execution_plan
Concepts: Topological sort, parallel groups, loop body extraction, branch detection, deterministic output
"""

import pytest

from app.services.workflow.compiler import CompilationError, WorkflowCompiler
from app.services.workflow.execution_plan import ExecutionPlan, ExecutionStep


def _make_graph(nodes, connections=None):
    return {"nodes": nodes, "connections": connections or []}


def _node(node_id, node_type, config=None):
    return {"id": node_id, "type": node_type, "config": config or {}}


def _conn(source, target, source_port="out", target_port="in"):
    return {
        "source": source,
        "target": target,
        "source_port": source_port,
        "target_port": target_port,
    }


class TestLinearCompilation:
    def test_linear_graph(self):
        """Start → Script → End compiles to 3 steps in order."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("sc", "script"),
                _node("e", "end"),
            ],
            connections=[_conn("s", "sc"), _conn("sc", "e")],
        )
        compiler = WorkflowCompiler()
        plan = compiler.compile("def1", 1, graph)

        assert isinstance(plan, ExecutionPlan)
        assert plan.definition_id == "def1"
        assert plan.definition_version == 1
        assert len(plan.steps) == 3

        step_ids = [s.node_id for s in plan.steps]
        assert step_ids.index("s") < step_ids.index("sc")
        assert step_ids.index("sc") < step_ids.index("e")

    def test_step_dependencies(self):
        """Each step has correct dependencies."""
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "e")],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        start_step = next(s for s in plan.steps if s.node_id == "s")
        end_step = next(s for s in plan.steps if s.node_id == "e")

        assert start_step.dependencies == []
        assert "s" in end_step.dependencies

    def test_deterministic_output(self):
        """Same graph always produces same step order."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("a", "script"),
                _node("b", "script"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "a"),
                _conn("s", "b"),
                _conn("a", "e"),
                _conn("b", "e"),
            ],
        )
        compiler = WorkflowCompiler()
        plan1 = compiler.compile("def1", 1, graph)
        plan2 = compiler.compile("def1", 1, graph)

        ids1 = [s.node_id for s in plan1.steps]
        ids2 = [s.node_id for s in plan2.steps]
        assert ids1 == ids2


class TestParallelCompilation:
    def test_parallel_group_detection(self):
        """Nodes between Parallel and Merge get a parallel_group."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("p", "parallel"),
                _node("a", "script"),
                _node("b", "script"),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "p"),
                _conn("p", "a", source_port="branch_0"),
                _conn("p", "b", source_port="branch_1"),
                _conn("a", "m"),
                _conn("b", "m"),
                _conn("m", "e"),
            ],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        p_step = next(s for s in plan.steps if s.node_id == "p")
        a_step = next(s for s in plan.steps if s.node_id == "a")
        b_step = next(s for s in plan.steps if s.node_id == "b")
        m_step = next(s for s in plan.steps if s.node_id == "m")

        # All should share the same parallel group
        assert p_step.parallel_group is not None
        assert a_step.parallel_group == p_step.parallel_group
        assert b_step.parallel_group == p_step.parallel_group
        assert m_step.parallel_group == p_step.parallel_group

    def test_non_parallel_nodes_no_group(self):
        """Nodes outside Parallel/Merge should have no parallel_group."""
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "e")],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        for step in plan.steps:
            assert step.parallel_group is None


class TestConditionalCompilation:
    def test_branch_detection(self):
        """Nodes after condition ports get branch_key."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("c", "condition"),
                _node("t", "script"),
                _node("f", "script"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "c"),
                _conn("c", "t", source_port="true"),
                _conn("c", "f", source_port="false"),
                _conn("t", "e"),
                _conn("f", "e"),
            ],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        t_step = next(s for s in plan.steps if s.node_id == "t")
        f_step = next(s for s in plan.steps if s.node_id == "f")

        assert t_step.branch_key == "c:true"
        assert f_step.branch_key == "c:false"

    def test_switch_branch_detection(self):
        """Switch node ports also get branch keys."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("sw", "switch"),
                _node("a", "script"),
                _node("b", "script"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "sw"),
                _conn("sw", "a", source_port="case_0"),
                _conn("sw", "b", source_port="default"),
                _conn("a", "e"),
                _conn("b", "e"),
            ],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        a_step = next(s for s in plan.steps if s.node_id == "a")
        b_step = next(s for s in plan.steps if s.node_id == "b")

        assert a_step.branch_key == "sw:case_0"
        assert b_step.branch_key == "sw:default"


class TestLoopCompilation:
    def test_loop_body_detection(self):
        """Nodes connected via 'body' port of forEach are tagged with loop_parent."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("loop", "forEach"),
                _node("body1", "script"),
                _node("body2", "script"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "loop"),
                _conn("loop", "body1", source_port="body"),
                _conn("body1", "body2"),
                # Note: loop-back edge (body2 → loop) is NOT included in the graph
                # for compilation — the executor handles iteration internally.
                _conn("loop", "e", source_port="done"),
            ],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)

        body1_step = next(s for s in plan.steps if s.node_id == "body1")
        body2_step = next(s for s in plan.steps if s.node_id == "body2")
        loop_step = next(s for s in plan.steps if s.node_id == "loop")

        assert body1_step.loop_parent == "loop"
        assert body2_step.loop_parent == "loop"
        assert loop_step.loop_parent is None


class TestCycleDetection:
    def test_cycle_raises_error(self):
        """Cycles in the graph raise CompilationError."""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("a", "script"),
                _node("b", "script"),
            ],
            connections=[
                _conn("s", "a"),
                _conn("a", "b"),
                _conn("b", "a"),  # cycle
            ],
        )
        compiler = WorkflowCompiler()
        with pytest.raises(CompilationError, match="Cycle detected"):
            compiler.compile("def1", 1, graph)


class TestEmptyGraph:
    def test_empty_graph_raises(self):
        graph = _make_graph(nodes=[])
        with pytest.raises(CompilationError, match="no nodes"):
            WorkflowCompiler().compile("def1", 1, graph)


class TestExecutionPlanSerialization:
    def test_to_dict_and_back(self):
        step = ExecutionStep(
            node_id="n1",
            node_type="script",
            config={"key": "value"},
            dependencies=["n0"],
            parallel_group="pg1",
            loop_parent="loop1",
            branch_key="c:true",
        )
        plan = ExecutionPlan(
            definition_id="def1",
            definition_version=2,
            steps=[step],
            variables={"x": 1},
            timeout_seconds=1800,
        )

        d = plan.to_dict()
        restored = ExecutionPlan.from_dict(d)

        assert restored.definition_id == "def1"
        assert restored.definition_version == 2
        assert len(restored.steps) == 1
        assert restored.steps[0].node_id == "n1"
        assert restored.steps[0].config == {"key": "value"}
        assert restored.steps[0].parallel_group == "pg1"
        assert restored.steps[0].loop_parent == "loop1"
        assert restored.steps[0].branch_key == "c:true"
        assert restored.variables == {"x": 1}
        assert restored.timeout_seconds == 1800

    def test_to_json_and_back(self):
        plan = ExecutionPlan(
            definition_id="def1",
            definition_version=1,
            steps=[ExecutionStep(node_id="n1", node_type="start")],
        )
        json_str = plan.to_json()
        restored = ExecutionPlan.from_json(json_str)
        assert restored.definition_id == "def1"
        assert len(restored.steps) == 1

    def test_mixed_graph_compilation(self):
        """Complex graph: Start → Condition → (Parallel → Merge) | Script → End"""
        graph = _make_graph(
            nodes=[
                _node("s", "start"),
                _node("c", "condition"),
                _node("p", "parallel"),
                _node("a", "script"),
                _node("b", "script"),
                _node("m", "merge"),
                _node("sc", "script"),
                _node("e", "end"),
            ],
            connections=[
                _conn("s", "c"),
                _conn("c", "p", source_port="true"),
                _conn("c", "sc", source_port="false"),
                _conn("p", "a", source_port="branch_0"),
                _conn("p", "b", source_port="branch_1"),
                _conn("a", "m"),
                _conn("b", "m"),
                _conn("m", "e"),
                _conn("sc", "e"),
            ],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph)
        step_ids = [s.node_id for s in plan.steps]

        # s must come before c
        assert step_ids.index("s") < step_ids.index("c")
        # c must come before p and sc
        assert step_ids.index("c") < step_ids.index("p")
        assert step_ids.index("c") < step_ids.index("sc")
        # p must come before a and b
        assert step_ids.index("p") < step_ids.index("a")
        assert step_ids.index("p") < step_ids.index("b")
        # a and b must come before m
        assert step_ids.index("a") < step_ids.index("m")
        assert step_ids.index("b") < step_ids.index("m")
        # m and sc must come before e
        assert step_ids.index("m") < step_ids.index("e")
        assert step_ids.index("sc") < step_ids.index("e")

    def test_timeout_passthrough(self):
        graph = _make_graph(
            nodes=[_node("s", "start"), _node("e", "end")],
            connections=[_conn("s", "e")],
        )
        plan = WorkflowCompiler().compile("def1", 1, graph, timeout_seconds=7200)
        assert plan.timeout_seconds == 7200
