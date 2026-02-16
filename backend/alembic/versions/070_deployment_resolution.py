"""Add resolution columns to deployments table.

Revision ID: 070
Revises: 069
Create Date: 2026-02-15
"""

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.add_column("deployments", sa.Column("resolved_parameters", postgresql.JSONB(), nullable=True))
    op.add_column("deployments", sa.Column("resolution_status", sa.String(20), nullable=True, server_default="PENDING"))
    op.add_column("deployments", sa.Column("resolution_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("deployments", "resolution_error")
    op.drop_column("deployments", "resolution_status")
    op.drop_column("deployments", "resolved_parameters")
