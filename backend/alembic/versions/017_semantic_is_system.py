"""Add is_system flag to semantic tables and mark seeded records.

Revision ID: 017
Revises: 016
Create Date: 2026-02-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEMANTIC_TABLES = [
    "semantic_categories",
    "semantic_resource_types",
    "semantic_relationship_kinds",
    "semantic_provider_mappings",
]


def upgrade() -> None:
    # Add is_system column to all semantic tables
    for table in SEMANTIC_TABLES:
        op.add_column(
            table,
            sa.Column(
                "is_system",
                sa.Boolean,
                nullable=False,
                server_default="false",
            ),
        )

    # Mark all existing seeded records as system records
    conn = op.get_bind()
    for table in SEMANTIC_TABLES:
        conn.execute(
            sa.text(f"UPDATE {table} SET is_system = true WHERE deleted_at IS NULL")
        )


def downgrade() -> None:
    for table in reversed(SEMANTIC_TABLES):
        op.drop_column(table, "is_system")
