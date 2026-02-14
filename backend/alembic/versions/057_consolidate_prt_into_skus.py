"""
Overview: Consolidate provider resource types and type mappings into provider SKUs.
Architecture: Database migration — removes PRT/TypeMapping tables, adds semantic_type_id to SKUs (Section 5, 8)
Dependencies: alembic, sqlalchemy
Concepts: Removes the intermediate PRT/TypeMapping abstraction layer. SKUs gain direct semantic type linkage.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to provider_skus
    op.add_column(
        "provider_skus",
        sa.Column("semantic_type_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "provider_skus",
        sa.Column("resource_type", sa.String(200), nullable=True),
    )
    op.create_foreign_key(
        "fk_provider_skus_semantic_type",
        "provider_skus",
        "semantic_resource_types",
        ["semantic_type_id"],
        ["id"],
    )
    op.create_index(
        "ix_provider_skus_semantic_type", "provider_skus", ["semantic_type_id"]
    )
    op.create_index(
        "ix_provider_skus_resource_type", "provider_skus", ["resource_type"]
    )

    # Backfill semantic_type_id from ci_class_id where ci_class.name matches semantic_resource_types.name
    op.execute("""
        UPDATE provider_skus ps
        SET semantic_type_id = srt.id
        FROM ci_classes cc, semantic_resource_types srt
        WHERE ps.ci_class_id = cc.id
          AND lower(cc.name) = lower(srt.name)
          AND srt.deleted_at IS NULL
    """)

    # Drop type_mappings first (references PRTs)
    op.drop_table("semantic_type_mappings")

    # Drop provider_resource_types
    op.drop_table("semantic_provider_resource_types")

    # Remove permissions that are no longer needed
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE key IN (
                'semantic:provider_resource_type:read',
                'semantic:provider_resource_type:manage',
                'semantic:type_mapping:read',
                'semantic:type_mapping:manage',
                'semantic:mapping:read',
                'semantic:mapping:manage'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE key IN (
            'semantic:provider_resource_type:read',
            'semantic:provider_resource_type:manage',
            'semantic:type_mapping:read',
            'semantic:type_mapping:manage',
            'semantic:mapping:read',
            'semantic:mapping:manage'
        )
    """)


def downgrade() -> None:
    # Recreate semantic_provider_resource_types
    op.create_table(
        "semantic_provider_resource_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_type", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("documentation_url", sa.String(500), nullable=True),
        sa.Column("parameter_schema", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), server_default="available", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["semantic_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "api_type", name="uq_provider_resource_type_provider_api"),
    )

    # Recreate semantic_type_mappings
    op.create_table(
        "semantic_type_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_resource_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_mapping", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["provider_resource_type_id"], ["semantic_provider_resource_types.id"]),
        sa.ForeignKeyConstraint(["semantic_type_id"], ["semantic_resource_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_resource_type_id", "semantic_type_id", name="uq_type_mapping_prt_semantic"),
    )

    # Remove new columns from provider_skus
    op.drop_index("ix_provider_skus_resource_type", table_name="provider_skus")
    op.drop_index("ix_provider_skus_semantic_type", table_name="provider_skus")
    op.drop_constraint("fk_provider_skus_semantic_type", "provider_skus", type_="foreignkey")
    op.drop_column("provider_skus", "resource_type")
    op.drop_column("provider_skus", "semantic_type_id")
