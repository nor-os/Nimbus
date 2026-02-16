"""Create naming_sequences table for durable resolver counters.

Revision ID: 069
Revises: 068
Create Date: 2026-02-15
"""

revision = "069"
down_revision = "067b"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "naming_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_key", sa.String(512), nullable=False),
        sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "scope_key", name="uq_naming_sequences_tenant_scope"),
    )
    op.create_index("ix_naming_sequences_tenant", "naming_sequences", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_naming_sequences_tenant")
    op.drop_table("naming_sequences")
