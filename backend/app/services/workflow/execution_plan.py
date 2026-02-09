"""
Overview: Execution plan data structures — compiled representation of a workflow graph.
Architecture: Intermediate representation between graph and Temporal execution (Section 5)
Dependencies: None
Concepts: Execution steps, dependency ordering, parallel groups, loop bodies, branch keys
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    node_id: str
    node_type: str
    config: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    parallel_group: str | None = None
    loop_parent: str | None = None
    branch_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "config": self.config,
            "dependencies": self.dependencies,
            "parallel_group": self.parallel_group,
            "loop_parent": self.loop_parent,
            "branch_key": self.branch_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionStep:
        return cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            config=data.get("config", {}),
            dependencies=data.get("dependencies", []),
            parallel_group=data.get("parallel_group"),
            loop_parent=data.get("loop_parent"),
            branch_key=data.get("branch_key"),
        )


@dataclass
class ExecutionPlan:
    """Compiled execution plan ready for Temporal execution."""
    definition_id: str
    definition_version: int
    steps: list[ExecutionStep] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "timeout_seconds": self.timeout_seconds,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionPlan:
        return cls(
            definition_id=data.get("definition_id", ""),
            definition_version=data.get("definition_version", 0),
            steps=[ExecutionStep.from_dict(s) for s in data.get("steps", [])],
            variables=data.get("variables", {}),
            timeout_seconds=data.get("timeout_seconds", 3600),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ExecutionPlan:
        return cls.from_dict(json.loads(json_str))
