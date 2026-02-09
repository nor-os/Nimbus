"""
Overview: Add profile_id, cost_center override, and default cost rate fields to staff_profiles.
Architecture: Staff profile enhancement migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Staff profiles gain a human-readable profile ID, cost center override
    (inherits from org unit when NULL), and default hourly cost/currency for rate card defaults.
"""

revision: str = "026"
down_revision: str | None = "025"
branch_labels: str | None = None
depends_on: str | None = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("staff_profiles", sa.Column("profile_id", sa.String(50), nullable=True))
    op.add_column("staff_profiles", sa.Column("cost_center", sa.String(100), nullable=True))
    op.add_column("staff_profiles", sa.Column("default_hourly_cost", sa.Numeric(12, 4), nullable=True))
    op.add_column("staff_profiles", sa.Column("default_currency", sa.String(3), nullable=True, server_default="EUR"))

    op.create_index("ix_staff_profiles_profile_id", "staff_profiles", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_staff_profiles_profile_id")
    op.drop_column("staff_profiles", "default_currency")
    op.drop_column("staff_profiles", "default_hourly_cost")
    op.drop_column("staff_profiles", "cost_center")
    op.drop_column("staff_profiles", "profile_id")
