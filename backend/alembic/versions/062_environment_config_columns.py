"""
Overview: Add environment config JSONB columns to tenant_environments.
Architecture: Migration for environment-level config (network, IAM, security, monitoring)
Dependencies: alembic, sqlalchemy
Concepts: Additive migration — new nullable JSONB columns for per-environment configuration
"""

"""add environment config columns

Revision ID: 062
Revises: 061
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_environments", sa.Column("network_config", postgresql.JSONB(), nullable=True))
    op.add_column("tenant_environments", sa.Column("iam_config", postgresql.JSONB(), nullable=True))
    op.add_column("tenant_environments", sa.Column("security_config", postgresql.JSONB(), nullable=True))
    op.add_column("tenant_environments", sa.Column("monitoring_config", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_environments", "monitoring_config")
    op.drop_column("tenant_environments", "security_config")
    op.drop_column("tenant_environments", "iam_config")
    op.drop_column("tenant_environments", "network_config")
