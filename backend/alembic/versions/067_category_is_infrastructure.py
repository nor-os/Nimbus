"""
Overview: Add is_infrastructure flag to semantic_categories.
Architecture: Schema migration for semantic layer (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: Infrastructure categories (compute, network, storage, database, security, tenancy)
    are allowed for component creation. Non-infrastructure (application, services, monitoring) are not.
"""

revision = "067b"
down_revision = "068"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    # Add column defaulting to true (most categories are infrastructure)
    op.add_column(
        "semantic_categories",
        sa.Column(
            "is_infrastructure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Set non-infrastructure categories
    op.execute(
        sa.text("""
            UPDATE semantic_categories
            SET is_infrastructure = false
            WHERE name IN ('application', 'services', 'monitoring')
        """)
    )


def downgrade() -> None:
    op.drop_column("semantic_categories", "is_infrastructure")
