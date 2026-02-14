"""Add semantic_category_id and semantic_type_id to service_cluster_slots.

Allows each slot in a stack blueprint to specify the kind (semantic category)
and specific type (semantic resource type) of resource it expects.

Revision ID: 040
Revises: 039
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "040"
down_revision: Union[str, None] = "039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_cluster_slots",
        sa.Column(
            "semantic_category_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_categories.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "service_cluster_slots",
        sa.Column(
            "semantic_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("service_cluster_slots", "semantic_type_id")
    op.drop_column("service_cluster_slots", "semantic_category_id")
