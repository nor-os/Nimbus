"""Add cloned_from_catalog_id to service_catalogs for clone tracking.

Tracks which source catalog a tenant-specific clone was created from,
enabling diff views and assignment management.

Revision ID: 041
Revises: 040
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "041"
down_revision: Union[str, None] = "040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_catalogs",
        sa.Column(
            "cloned_from_catalog_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_catalogs.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_service_catalogs_cloned_from",
        "service_catalogs",
        ["cloned_from_catalog_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_catalogs_cloned_from", table_name="service_catalogs")
    op.drop_column("service_catalogs", "cloned_from_catalog_id")
