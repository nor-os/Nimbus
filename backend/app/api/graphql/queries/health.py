"""
Overview: GraphQL health and version queries for system status.
Architecture: GraphQL query resolvers (Section 7.2)
Dependencies: strawberry, app.core.config
Concepts: Health checks, GraphQL queries
"""

import strawberry

from app.core.config import get_settings


@strawberry.type
class HealthQuery:
    @strawberry.field
    def health(self) -> str:
        """Basic health check."""
        return "ok"

    @strawberry.field
    def version(self) -> str:
        """Application version."""
        return get_settings().app_version
