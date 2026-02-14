"""Add category_retention_overrides table for per-category retention.

Revision ID: 028
Revises: 027
Create Date: 2026-02-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_retention_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "event_category",
            postgresql.ENUM(
                "API", "AUTH", "DATA", "PERMISSION", "SYSTEM", "SECURITY", "TENANT", "USER",
                name="audit_event_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("hot_days", sa.Integer(), nullable=False),
        sa.Column("cold_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_category_retention_tenant_cat",
        "category_retention_overrides",
        ["tenant_id", "event_category"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_category_retention_tenant_cat", table_name="category_retention_overrides")
    op.drop_table("category_retention_overrides")
