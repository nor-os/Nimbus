"""
Overview: Add HA/DR config columns to stack instances.
Architecture: Alembic migration for instance-level HA/DR configuration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Deployed instances store resolved HA/DR settings (blueprint defaults merged
    with user overrides).

Revision ID: 106
Revises: 105
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "106"
down_revision = "105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stack_instances", sa.Column("ha_config", JSONB, nullable=True))
    op.add_column("stack_instances", sa.Column("dr_config", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("stack_instances", "dr_config")
    op.drop_column("stack_instances", "ha_config")
