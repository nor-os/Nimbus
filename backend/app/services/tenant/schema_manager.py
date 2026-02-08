"""
Overview: Manages per-tenant PostgreSQL schemas (create, drop, check existence).
Architecture: Dynamic schema management for tenant isolation (Section 4.2)
Dependencies: sqlalchemy, app.db.session
Concepts: Schema-per-tenant isolation, dynamic DDL
"""

import re
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _validate_tenant_id(tenant_id: str) -> str:
    """Validate and normalize a tenant ID for use in schema names."""
    parsed = uuid.UUID(tenant_id)
    return str(parsed).replace("-", "_")


def get_schema_name(tenant_id: str) -> str:
    """Get the PostgreSQL schema name for a tenant."""
    normalized = _validate_tenant_id(tenant_id)
    schema_name = f"nimbus_tenant_{normalized}"
    if not re.match(r"^nimbus_tenant_[0-9a-f_]+$", schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")
    return schema_name


class SchemaManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant_schema(self, tenant_id: str) -> str:
        """Create a new PostgreSQL schema for the tenant."""
        schema_name = get_schema_name(tenant_id)
        await self.db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        return schema_name

    async def drop_tenant_schema(self, tenant_id: str) -> None:
        """Drop a tenant's PostgreSQL schema and all its objects."""
        schema_name = get_schema_name(tenant_id)
        await self.db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))

    async def schema_exists(self, tenant_id: str) -> bool:
        """Check if a tenant's schema exists."""
        schema_name = get_schema_name(tenant_id)
        result = await self.db.execute(
            text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = :name"
            ).bindparams(name=schema_name)
        )
        return result.scalar_one_or_none() is not None
