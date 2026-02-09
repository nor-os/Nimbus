"""
Overview: Base node executor — abstract base class and context for node execution.
Architecture: Foundation for all workflow node type executors (Section 5)
Dependencies: None
Concepts: Node execution, execution context, node output, abstract executor
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeOutput:
    """Result of executing a single node."""
    data: dict[str, Any] = field(default_factory=dict)
    next_port: str | None = None  # Which output port to follow (for branching)
    next_ports: list[str] | None = None  # Multiple ports (for parallel fan-out)
    error: str | None = None


@dataclass
class NodeExecutionContext:
    """Runtime context passed to each node executor."""
    node_id: str
    node_type: str
    config: dict[str, Any] = field(default_factory=dict)
    input_data: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    node_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    loop_context: dict[str, Any] | None = None
    workflow_input: dict[str, Any] = field(default_factory=dict)
    tenant_id: str = ""
    execution_id: str = ""
    is_test: bool = False
    mock_config: dict[str, Any] | None = None


class BaseNodeExecutor(abc.ABC):
    """Abstract base class for all node type executors."""

    @abc.abstractmethod
    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        """Execute the node logic and return the output."""
        ...
