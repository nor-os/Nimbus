"""
Overview: Remove APPLICATION blueprint category, recategorize to COMPUTE.
Architecture: Alembic migration for blueprint category cleanup (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: APPLICATION is not a valid infrastructure category — stacks are infrastructure-only.

Revision ID: 103
Revises: 102
"""

from alembic import op

revision = "103"
down_revision = "102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE service_clusters SET category = 'COMPUTE' "
        "WHERE category = 'APPLICATION' AND deleted_at IS NULL"
    )


def downgrade() -> None:
    pass
