"""Add approver_group_ids column to approval_policies.

Revision ID: 015
Revises: 014
Create Date: 2026-02-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "approval_policies",
        sa.Column("approver_group_ids", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approval_policies", "approver_group_ids")
