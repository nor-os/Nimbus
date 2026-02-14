"""
Overview: Add price_list_id FK to service_estimations for price list integration.
Architecture: Schema migration for estimation-pricing engine harmonization
Dependencies: alembic, sqlalchemy
Concepts: Estimations can now reference a specific price list for sell price resolution.
"""

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.add_column(
        "service_estimations",
        sa.Column(
            "price_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("price_lists.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_service_estimations_price_list_id",
        "service_estimations",
        ["price_list_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_estimations_price_list_id",
        table_name="service_estimations",
    )
    op.drop_column("service_estimations", "price_list_id")
