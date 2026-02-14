"""
Overview: Migration 034 — Add minimum charge columns to service_offerings.
Architecture: Database schema migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Per-offering minimum billing thresholds (amount, currency, period).

Revision ID: 034
Revises: 033
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_offerings",
        sa.Column("minimum_amount", sa.Numeric(12, 4), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("minimum_currency", sa.String(3), server_default="EUR", nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("minimum_period", sa.String(20), nullable=True),
    )

    # Backfill demo data with realistic minimums
    op.execute("""
        UPDATE service_offerings
        SET minimum_amount = 200.0000, minimum_currency = 'EUR', minimum_period = 'monthly'
        WHERE name = 'Virtual Machine Hosting' AND deleted_at IS NULL;
    """)
    op.execute("""
        UPDATE service_offerings
        SET minimum_amount = 300.0000, minimum_currency = 'EUR', minimum_period = 'monthly'
        WHERE name = 'Managed Database' AND deleted_at IS NULL;
    """)
    op.execute("""
        UPDATE service_offerings
        SET minimum_amount = 10.0000, minimum_currency = 'EUR', minimum_period = 'monthly'
        WHERE name = 'Block Storage' AND deleted_at IS NULL;
    """)
    op.execute("""
        UPDATE service_offerings
        SET minimum_amount = 500.0000, minimum_currency = 'EUR', minimum_period = 'monthly'
        WHERE name = 'L2 Support' AND deleted_at IS NULL;
    """)
    op.execute("""
        UPDATE service_offerings
        SET minimum_amount = 25.0000, minimum_currency = 'EUR', minimum_period = 'monthly'
        WHERE name = 'Network Monitoring' AND deleted_at IS NULL;
    """)


def downgrade() -> None:
    op.drop_column("service_offerings", "minimum_period")
    op.drop_column("service_offerings", "minimum_currency")
    op.drop_column("service_offerings", "minimum_amount")
