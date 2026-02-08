"""Add group_memberships junction table and remove parent_id from groups.

Revision ID: 005
Revises: 004
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create group_memberships junction table
    op.create_table(
        "group_memberships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "parent_group_id",
            UUID(as_uuid=True),
            sa.ForeignKey("groups.id"),
            nullable=False,
        ),
        sa.Column(
            "child_group_id",
            UUID(as_uuid=True),
            sa.ForeignKey("groups.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("parent_group_id", "child_group_id"),
        sa.CheckConstraint("parent_group_id != child_group_id"),
    )

    op.create_index(
        "ix_group_memberships_parent",
        "group_memberships",
        ["parent_group_id"],
    )
    op.create_index(
        "ix_group_memberships_child",
        "group_memberships",
        ["child_group_id"],
    )

    # Migrate existing parent_id data into group_memberships
    op.execute(
        """
        INSERT INTO group_memberships (id, parent_group_id, child_group_id, created_at, updated_at)
        SELECT gen_random_uuid(), parent_id, id, NOW(), NOW()
        FROM groups
        WHERE parent_id IS NOT NULL AND deleted_at IS NULL
        """
    )

    # Drop parent_id column
    op.drop_index("ix_groups_parent_id", table_name="groups", if_exists=True)
    op.drop_column("groups", "parent_id")


def downgrade() -> None:
    # Re-add parent_id column
    op.add_column(
        "groups",
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_groups_parent_id", "groups", ["parent_id"])
    op.create_foreign_key(None, "groups", "groups", ["parent_id"], ["id"])

    # Migrate data back from group_memberships
    op.execute(
        """
        UPDATE groups g
        SET parent_id = gm.parent_group_id
        FROM group_memberships gm
        WHERE gm.child_group_id = g.id
        """
    )

    # Drop group_memberships table
    op.drop_index("ix_group_memberships_child", table_name="group_memberships")
    op.drop_index("ix_group_memberships_parent", table_name="group_memberships")
    op.drop_table("group_memberships")
