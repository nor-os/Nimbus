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
    # Columns already added by migration 033 (catalog redesign).
    pass


def downgrade() -> None:
    # Nothing to undo — columns managed by migration 033.
    pass
