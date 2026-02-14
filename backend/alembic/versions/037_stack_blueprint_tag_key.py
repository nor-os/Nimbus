"""Add stack_tag_key to service_clusters for tag-based stack identification.

Blueprints (service clusters) can define which tag key on CIs identifies
deployed instances (stacks) of that blueprint.

Revision ID: 037
Revises: 036
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "037"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_clusters",
        sa.Column(
            "stack_tag_key",
            sa.String(100),
            nullable=True,
            comment="Tag key on CIs that identifies deployments of this blueprint",
        ),
    )


def downgrade() -> None:
    op.drop_column("service_clusters", "stack_tag_key")
