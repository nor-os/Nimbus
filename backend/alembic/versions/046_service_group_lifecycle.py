"""
Overview: Add lifecycle status to service groups — replaces is_active with draft/published/archived status.
Architecture: Database migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Service group lifecycle (draft -> published -> archived)
"""

"""add service group lifecycle status

Revision ID: 046
Revises: 045
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column with default 'draft'
    op.add_column(
        "service_groups",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
    )

    # Migrate existing data: is_active=true -> published, is_active=false -> archived
    op.execute(
        "UPDATE service_groups SET status = 'published' WHERE is_active = true"
    )
    op.execute(
        "UPDATE service_groups SET status = 'archived' WHERE is_active = false"
    )

    # Drop is_active column
    op.drop_column("service_groups", "is_active")


def downgrade() -> None:
    # Re-add is_active column
    op.add_column(
        "service_groups",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )

    # Migrate back: published -> active, draft/archived -> inactive
    op.execute(
        "UPDATE service_groups SET is_active = true WHERE status = 'published'"
    )
    op.execute(
        "UPDATE service_groups SET is_active = false WHERE status IN ('draft', 'archived')"
    )

    # Drop status column
    op.drop_column("service_groups", "status")
