"""Add clone tracking to price lists — cloned_from_price_list_id column
with self-referential FK and index for reverse lookups.

Revision ID: 043
Revises: 042
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "043"
down_revision: Union[str, None] = "042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_lists",
        sa.Column(
            "cloned_from_price_list_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("price_lists.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_price_lists_cloned_from",
        "price_lists",
        ["cloned_from_price_list_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_lists_cloned_from", table_name="price_lists")
    op.drop_column("price_lists", "cloned_from_price_list_id")
