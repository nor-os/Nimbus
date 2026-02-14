"""Add versioning columns to price_lists, create tenant_price_list_pins table.

Adds group_id, version_major, version_minor, status, delivery_region_id,
parent_version_id to price_lists. Creates tenant_price_list_pins for pinning
tenants to specific price list versions. Backfills group_id = id for existing rows.

Revision ID: 032
Revises: 031
Create Date: 2026-02-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add versioning columns to price_lists ────────────────────────
    op.add_column(
        "price_lists",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "price_lists",
        sa.Column("version_major", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "price_lists",
        sa.Column("version_minor", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "price_lists",
        sa.Column("status", sa.String(20), server_default="published", nullable=False),
    )
    op.add_column(
        "price_lists",
        sa.Column(
            "delivery_region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "price_lists",
        sa.Column(
            "parent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("price_lists.id"),
            nullable=True,
        ),
    )

    # Backfill: set group_id = id for all existing price lists
    op.execute("UPDATE price_lists SET group_id = id WHERE group_id IS NULL")

    # Indexes
    op.create_index("ix_price_lists_group_id", "price_lists", ["group_id"])
    op.create_index(
        "ix_price_lists_group_version_unique",
        "price_lists",
        ["group_id", "version_major", "version_minor"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── Create tenant_price_list_pins table ──────────────────────────
    op.create_table(
        "tenant_price_list_pins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("price_list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("price_lists.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenant_price_list_pins_tenant_id", "tenant_price_list_pins", ["tenant_id"])
    op.create_index(
        "ix_tenant_price_list_pins_unique",
        "tenant_price_list_pins",
        ["tenant_id", "price_list_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("tenant_price_list_pins")
    op.drop_index("ix_price_lists_group_version_unique", table_name="price_lists")
    op.drop_index("ix_price_lists_group_id", table_name="price_lists")
    op.drop_column("price_lists", "parent_version_id")
    op.drop_column("price_lists", "delivery_region_id")
    op.drop_column("price_lists", "status")
    op.drop_column("price_lists", "version_minor")
    op.drop_column("price_lists", "version_major")
    op.drop_column("price_lists", "group_id")
