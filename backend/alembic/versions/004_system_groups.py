"""Add is_system column to groups table.

Revision ID: 004
Revises: 003
Create Date: 2026-02-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column(
            "is_system", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade() -> None:
    op.drop_column("groups", "is_system")
