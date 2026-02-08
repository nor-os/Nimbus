"""Replace users.email unique constraint with partial unique index (exclude soft-deleted).

Revision ID: 012
Revises: 011
Create Date: 2026-02-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique index on email
    op.drop_index("ix_users_email", table_name="users")

    # Create partial unique index: email must be unique only among non-deleted rows
    op.execute(
        "CREATE UNIQUE INDEX ix_users_email_active ON users (email) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_email_active")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
