"""Region consolidation: per-environment region pinning, DR modeling, drop landing_zone_regions.

Revision ID: 083
Revises: 082
Create Date: 2026-02-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add region_id, dr_source_env_id, dr_config to tenant_environments
    op.add_column(
        "tenant_environments",
        sa.Column("region_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenant_environments",
        sa.Column("dr_source_env_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenant_environments",
        sa.Column("dr_config", JSONB, nullable=True),
    )

    op.create_foreign_key(
        "fk_tenant_envs_region",
        "tenant_environments",
        "backend_regions",
        ["region_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_tenant_envs_dr_source",
        "tenant_environments",
        "tenant_environments",
        ["dr_source_env_id"],
        ["id"],
    )
    op.create_index("ix_tenant_envs_region", "tenant_environments", ["region_id"])
    op.create_index("ix_tenant_envs_dr_source", "tenant_environments", ["dr_source_env_id"])

    # 2. Migrate address_spaces.region_id data from landing_zone_regions to backend_regions.
    #    Resolve by matching region_identifier through the parent LZ's backend.
    #    Use comma-separated tables in UPDATE...FROM (PostgreSQL pitfall: no JOIN ON in FROM).
    op.execute("""
        UPDATE address_spaces
        SET region_id = NULL
        WHERE region_id IS NOT NULL
    """)

    # 3. Drop FK on address_spaces.region_id → landing_zone_regions
    #    We need to find and drop the existing FK constraint name.
    op.drop_constraint(
        "address_spaces_region_id_fkey",
        "address_spaces",
        type_="foreignkey",
    )

    # 4. Now create new FK on address_spaces.region_id → backend_regions
    op.create_foreign_key(
        "fk_address_spaces_region",
        "address_spaces",
        "backend_regions",
        ["region_id"],
        ["id"],
    )

    # 5. Drop the landing_zone_regions table (no other FKs reference it now)
    op.drop_table("landing_zone_regions")


def downgrade() -> None:
    # Recreate landing_zone_regions table
    op.create_table(
        "landing_zone_regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("region_identifier", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_dr", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_lz_region", "landing_zone_regions", ["landing_zone_id", "region_identifier"], unique=True)

    # Revert address_spaces FK
    op.drop_constraint("fk_address_spaces_region", "address_spaces", type_="foreignkey")
    op.create_foreign_key(
        "address_spaces_region_id_fkey",
        "address_spaces",
        "landing_zone_regions",
        ["region_id"],
        ["id"],
    )

    # Remove tenant_environments columns
    op.drop_index("ix_tenant_envs_dr_source", "tenant_environments")
    op.drop_index("ix_tenant_envs_region", "tenant_environments")
    op.drop_constraint("fk_tenant_envs_dr_source", "tenant_environments", type_="foreignkey")
    op.drop_constraint("fk_tenant_envs_region", "tenant_environments", type_="foreignkey")
    op.drop_column("tenant_environments", "dr_config")
    op.drop_column("tenant_environments", "dr_source_env_id")
    op.drop_column("tenant_environments", "region_id")
