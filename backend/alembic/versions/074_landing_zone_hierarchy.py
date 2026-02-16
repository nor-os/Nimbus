"""Landing zone hierarchy column and nullable topology_id.

Revision ID: 074
Revises: 073
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hierarchy JSONB column to landing_zones
    op.add_column(
        "landing_zones",
        sa.Column("hierarchy", JSONB, nullable=True),
    )

    # Make topology_id nullable (landing zones no longer require a topology)
    op.alter_column(
        "landing_zones",
        "topology_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "landing_zones",
        "topology_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    op.drop_column("landing_zones", "hierarchy")
