"""Add code TEXT column to resolvers table for handler source/documentation.

Revision ID: 079
Revises: 078
Create Date: 2026-02-15
"""

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("resolvers", sa.Column("code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("resolvers", "code")
