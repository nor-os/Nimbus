"""
Overview: Event type and subscription registries — singleton in-memory stores for system event definitions.
Architecture: Registry pattern for event type discovery (Section 11.6)
Dependencies: None
Concepts: Singleton registry, event type definitions, subscription definitions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EventTypeDefinition:
    """In-memory definition of a system event type."""
    name: str
    category: str
    description: str = ""
    payload_schema: dict[str, Any] | None = None
    source_validators: list[str] = field(default_factory=list)


@dataclass
class SubscriptionDefinition:
    """In-memory definition of a system subscription."""
    event_type_name: str
    name: str
    handler_type: str
    handler_config: dict[str, Any] = field(default_factory=dict)
    filter_expression: str | None = None
    priority: int = 100


class EventTypeRegistry:
    """Singleton registry for system event type definitions."""

    _instance: EventTypeRegistry | None = None
    _definitions: dict[str, EventTypeDefinition]

    def __new__(cls) -> EventTypeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._definitions = {}
        return cls._instance

    def register(self, definition: EventTypeDefinition) -> None:
        if definition.name in self._definitions:
            logger.warning("Overwriting event type '%s'", definition.name)
        self._definitions[definition.name] = definition
        logger.debug("Registered event type '%s'", definition.name)

    def get(self, name: str) -> EventTypeDefinition | None:
        return self._definitions.get(name)

    def list_all(self) -> list[EventTypeDefinition]:
        return list(self._definitions.values())

    def has(self, name: str) -> bool:
        return name in self._definitions

    def clear(self) -> None:
        self._definitions.clear()


class SubscriptionRegistry:
    """Singleton registry for system (code-defined) subscriptions."""

    _instance: SubscriptionRegistry | None = None
    _subscriptions: list[SubscriptionDefinition]

    def __new__(cls) -> SubscriptionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscriptions = []
        return cls._instance

    def register(self, definition: SubscriptionDefinition) -> None:
        self._subscriptions.append(definition)
        logger.debug("Registered system subscription for '%s'", definition.event_type_name)

    def get_for_event(self, event_type_name: str) -> list[SubscriptionDefinition]:
        return [s for s in self._subscriptions if s.event_type_name == event_type_name]

    def list_all(self) -> list[SubscriptionDefinition]:
        return list(self._subscriptions)

    def clear(self) -> None:
        self._subscriptions.clear()


def get_event_type_registry() -> EventTypeRegistry:
    return EventTypeRegistry()


def get_subscription_registry() -> SubscriptionRegistry:
    return SubscriptionRegistry()
