"""
Overview: Add bootstrap configuration columns to landing_zones and unique partial index on backend_id.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: Landing zone bootstrap — network, IAM, security, naming config as JSONB columns. One LZ per backend.
"""

revision = "060"
down_revision = "059"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    # Add 4 JSONB bootstrap configuration columns
    op.add_column("landing_zones", sa.Column("network_config", JSONB, nullable=True))
    op.add_column("landing_zones", sa.Column("iam_config", JSONB, nullable=True))
    op.add_column("landing_zones", sa.Column("security_config", JSONB, nullable=True))
    op.add_column("landing_zones", sa.Column("naming_config", JSONB, nullable=True))

    # Unique partial index: one active landing zone per backend
    op.execute(sa.text("""
        CREATE UNIQUE INDEX uq_landing_zones_backend_active
        ON landing_zones (backend_id)
        WHERE deleted_at IS NULL
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_landing_zones_backend_active"))
    op.drop_column("landing_zones", "naming_config")
    op.drop_column("landing_zones", "security_config")
    op.drop_column("landing_zones", "iam_config")
    op.drop_column("landing_zones", "network_config")
