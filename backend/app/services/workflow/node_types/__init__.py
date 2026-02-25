"""
Overview: Node types package — auto-registers all built-in node types on import.
Architecture: Node type auto-discovery and registration (Section 5)
Dependencies: All node type modules in this package
Concepts: Auto-registration, node type discovery
"""

from app.services.workflow.node_types import (
    activity,
    approval_gate,
    audit_log,
    cloud_api,
    cmdb_record,
    condition,
    delay,
    deployment_gate,
    event_trigger,
    http_request,
    loop,
    notification,
    parallel,
    script,
    ssh_exec,
    stack_deploy,
    stack_destroy,
    start_end,
    subworkflow,
    switch_node,
    topology_resolve,
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
    # Cloud provider nodes
    cloud_api.register()
    ssh_exec.register()
    # Deployment nodes
    topology_resolve.register()
    stack_deploy.register()
    stack_destroy.register()
    cmdb_record.register()
    deployment_gate.register()
    # Activity node
    activity.register()
    # Event trigger node
    event_trigger.register()


# Auto-register on import
register_all()
