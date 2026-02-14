"""Remove Service Cluster and Service Group from semantic resource types.

These are internal service constructs, not infrastructure resource types.
They should not appear in the semantic type catalog.

Revision ID: 036
Revises: 035
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TYPES_TO_REMOVE = list(("ServiceCluster", "ServiceGroup"))


def upgrade() -> None:
    conn = op.get_bind()

    # Soft-delete type mappings that reference these types
    conn.execute(
        sa.text(
            """
            UPDATE semantic_type_mappings
            SET deleted_at = now()
            WHERE deleted_at IS NULL
              AND semantic_type_id IN (
                  SELECT id FROM semantic_resource_types
                  WHERE name = ANY(:names) AND deleted_at IS NULL
              )
            """
        ),
        {"names": TYPES_TO_REMOVE},
    )

    # Soft-delete the semantic resource types themselves
    conn.execute(
        sa.text(
            """
            UPDATE semantic_resource_types
            SET deleted_at = now()
            WHERE name = ANY(:names) AND deleted_at IS NULL
            """
        ),
        {"names": TYPES_TO_REMOVE},
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Restore the types
    conn.execute(
        sa.text(
            """
            UPDATE semantic_resource_types
            SET deleted_at = NULL
            WHERE name = ANY(:names)
            """
        ),
        {"names": TYPES_TO_REMOVE},
    )

    # Restore type mappings
    conn.execute(
        sa.text(
            """
            UPDATE semantic_type_mappings
            SET deleted_at = NULL
            WHERE semantic_type_id IN (
                SELECT id FROM semantic_resource_types WHERE name = ANY(:names)
            )
            """
        ),
        {"names": TYPES_TO_REMOVE},
    )
