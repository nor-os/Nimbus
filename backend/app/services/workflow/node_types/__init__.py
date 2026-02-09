"""
Overview: Node types package — auto-registers all built-in node types on import.
Architecture: Node type auto-discovery and registration (Section 5)
Dependencies: All node type modules in this package
Concepts: Auto-registration, node type discovery
"""

from app.services.workflow.node_types import (
    approval_gate,
    audit_log,
    condition,
    delay,
    http_request,
    loop,
    notification,
    parallel,
    script,
    start_end,
    subworkflow,
    switch_node,
    variables,
)


def register_all() -> None:
    """Register all built-in node types."""
    start_end.register()
    condition.register()
    switch_node.register()
    loop.register()
    parallel.register()
    delay.register()
    subworkflow.register()
    approval_gate.register()
    notification.register()
    http_request.register()
    script.register()
    audit_log.register()
    variables.register()


# Auto-register on import
register_all()
