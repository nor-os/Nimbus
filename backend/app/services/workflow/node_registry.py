"""
Overview: Node type registry — singleton registry for workflow node type definitions and executors.
Architecture: Extensible node type system for visual workflow editor (Section 5)
Dependencies: None
Concepts: Node types, port definitions, registry pattern, categories
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.workflow.node_types.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class PortDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class PortType(str, Enum):
    FLOW = "FLOW"
    DATA = "DATA"


class NodeCategory(str, Enum):
    FLOW_CONTROL = "Flow Control"
    ACTION = "Action"
    ACTIVITY = "Activity"
    INTEGRATION = "Integration"
    DATA = "Data"
    UTILITY = "Utility"
    DEPLOYMENT = "Deployment"


@dataclass
class PortDef:
    name: str
    direction: PortDirection
    port_type: PortType = PortType.FLOW
    label: str = ""
    required: bool = True
    multiple: bool = False

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.name


@dataclass
class NodeTypeDefinition:
    type_id: str
    label: str
    category: NodeCategory
    description: str = ""
    icon: str = ""
    ports: list[PortDef] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    executor_class: type[BaseNodeExecutor] | None = None
    is_marker: bool = False  # True for Loop/Parallel — handled by executor, not directly


class NodeTypeRegistry:
    """Singleton registry for all workflow node types."""

    _instance: NodeTypeRegistry | None = None
    _definitions: dict[str, NodeTypeDefinition]
    _initialized: bool

    def __new__(cls) -> NodeTypeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._definitions = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, definition: NodeTypeDefinition) -> None:
        if definition.type_id in self._definitions:
            logger.warning("Overwriting node type '%s'", definition.type_id)
        self._definitions[definition.type_id] = definition
        logger.debug("Registered node type '%s'", definition.type_id)

    def get(self, type_id: str) -> NodeTypeDefinition | None:
        return self._definitions.get(type_id)

    def list_all(self) -> list[NodeTypeDefinition]:
        return list(self._definitions.values())

    def list_by_category(self, category: NodeCategory) -> list[NodeTypeDefinition]:
        return [d for d in self._definitions.values() if d.category == category]

    def has(self, type_id: str) -> bool:
        return type_id in self._definitions

    def clear(self) -> None:
        """Clear all registrations (useful for testing)."""
        self._definitions.clear()
        self._initialized = False


def get_registry() -> NodeTypeRegistry:
    """Get the global node type registry singleton."""
    return NodeTypeRegistry()
