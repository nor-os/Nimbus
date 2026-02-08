"""
Overview: Manages PostgreSQL Row-Level Security policies for tenant isolation.
Architecture: RLS enforcement layer (Section 4.2, 5.5)
Dependencies: sqlalchemy
Concepts: Row-level security, tenant isolation, provider bypass
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Tables that get RLS policies (tenant-scoped data)
RLS_TABLES = [
    "tenant_settings",
    "tenant_quotas",
    "compartments",
    "roles",
    "user_roles",
]


class RLSManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enable_rls_on_table(self, table_name: str) -> None:
        """Enable RLS on a table (forces policies even for table owner)."""
        await self.db.execute(
            text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        )
        await self.db.execute(
            text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        )

    async def create_tenant_policies(self, table_name: str) -> None:
        """Create SELECT/INSERT/UPDATE/DELETE policies scoped to current tenant."""
        tenant_check = "tenant_id::text = current_setting('app.current_tenant_id', true)"
        provider_check = "current_setting('app.is_provider_context', true) = 'true'"

        # SELECT: tenant users see own data, providers see all
        await self.db.execute(
            text(
                f"CREATE POLICY {table_name}_tenant_select ON {table_name} "
                f"FOR SELECT USING ({tenant_check} OR {provider_check})"
            )
        )

        # INSERT: tenant users insert into own tenant, providers can insert anywhere
        await self.db.execute(
            text(
                f"CREATE POLICY {table_name}_tenant_insert ON {table_name} "
                f"FOR INSERT WITH CHECK ({tenant_check} OR {provider_check})"
            )
        )

        # UPDATE: tenant users update own data, providers can update anywhere
        await self.db.execute(
            text(
                f"CREATE POLICY {table_name}_tenant_update ON {table_name} "
                f"FOR UPDATE USING ({tenant_check} OR {provider_check})"
            )
        )

        # DELETE: tenant users delete own data, providers can delete anywhere
        await self.db.execute(
            text(
                f"CREATE POLICY {table_name}_tenant_delete ON {table_name} "
                f"FOR DELETE USING ({tenant_check} OR {provider_check})"
            )
        )

    async def drop_policies(self, table_name: str) -> None:
        """Drop all tenant RLS policies from a table."""
        for op in ("select", "insert", "update", "delete"):
            await self.db.execute(
                text(
                    f"DROP POLICY IF EXISTS {table_name}_tenant_{op} ON {table_name}"
                )
            )

    async def setup_rls_for_all_tenant_tables(self) -> None:
        """Enable RLS and create policies for all tenant-scoped tables (idempotent)."""
        for table in RLS_TABLES:
            await self.enable_rls_on_table(table)
            await self.drop_policies(table)
            await self.create_tenant_policies(table)
