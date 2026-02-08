"""
Overview: Thread-safe tenant context using contextvars for request-scoped tenant isolation.
Architecture: Tenant context propagation (Section 4.2, 5.5)
Dependencies: contextvars
Concepts: Multi-tenancy, request-scoped context, async-safe state
"""

import uuid
from contextvars import ContextVar

_tenant_context_var: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> str | None:
    """Get the current tenant ID from the context."""
    return _tenant_context_var.get()


def set_current_tenant_id(tenant_id: str) -> None:
    """Set the current tenant ID in the context. Validates UUID format."""
    uuid.UUID(tenant_id)  # Raises ValueError if invalid
    _tenant_context_var.set(tenant_id)


def clear_tenant_context() -> None:
    """Clear the tenant context."""
    _tenant_context_var.set(None)
