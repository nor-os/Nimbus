"""Add domain mappings, tenant slug, LOCAL IdP uniqueness.

Revision ID: 008
Revises: 007
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add slug column to tenants
    op.add_column(
        "tenants",
        sa.Column("slug", sa.String(63), nullable=True),
    )
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])

    # Backfill: slugify name (lowercase, replace non-alphanumeric with hyphens, trim dashes)
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE tenants
            SET slug = lower(
                trim(
                    both '-' from regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g')
                )
            )
            WHERE deleted_at IS NULL AND slug IS NULL
            """
        )
    )

    # Handle collisions by appending a numeric suffix
    conn.execute(
        sa.text(
            """
            WITH dupes AS (
                SELECT id, slug,
                       ROW_NUMBER() OVER (PARTITION BY slug ORDER BY created_at) AS rn
                FROM tenants
                WHERE slug IS NOT NULL AND deleted_at IS NULL
            )
            UPDATE tenants t
            SET slug = t.slug || '-' || (d.rn - 1)::text
            FROM dupes d
            WHERE t.id = d.id AND d.rn > 1
            """
        )
    )

    # 2. Create domain_mappings table
    op.create_table(
        "domain_mappings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_provider_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["identity_provider_id"], ["identity_providers.id"]),
        sa.UniqueConstraint("domain", name="uq_domain_mappings_domain"),
    )
    op.create_index("ix_domain_mappings_tenant_id", "domain_mappings", ["tenant_id"])
    op.create_index("ix_domain_mappings_domain", "domain_mappings", ["domain"])

    # 3. Partial unique index: max one LOCAL IdP per tenant (only non-deleted)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_one_local_per_tenant
        ON identity_providers (tenant_id)
        WHERE idp_type = 'local' AND deleted_at IS NULL
        """
    )

    # 4. Backfill domain_mappings from existing users' email domains.
    #    For each unique email domain, map it to the tenant the user belongs to.
    #    If the same domain appears in multiple tenants, the first tenant (by
    #    earliest user_tenants.joined_at) wins — the UNIQUE on domain prevents
    #    duplicates. Marked is_verified=true since these are known existing users.
    conn.execute(
        sa.text(
            """
            INSERT INTO domain_mappings (domain, tenant_id, is_verified)
            SELECT DISTINCT ON (domain) domain, tenant_id, true
            FROM (
                SELECT
                    lower(split_part(u.email, '@', 2)) AS domain,
                    ut.tenant_id,
                    min(ut.joined_at) AS first_seen
                FROM users u
                JOIN user_tenants ut ON u.id = ut.user_id
                WHERE u.deleted_at IS NULL
                  AND u.email LIKE '%@%.%'
                GROUP BY lower(split_part(u.email, '@', 2)), ut.tenant_id
            ) sub
            ORDER BY domain, first_seen
            ON CONFLICT (domain) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_one_local_per_tenant")
    op.drop_index("ix_domain_mappings_domain", table_name="domain_mappings")
    op.drop_index("ix_domain_mappings_tenant_id", table_name="domain_mappings")
    op.drop_table("domain_mappings")
    op.drop_constraint("uq_tenants_slug", "tenants", type_="unique")
    op.drop_column("tenants", "slug")
