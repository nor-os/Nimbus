"""
Overview: Make email addresses case-insensitive — lowercase existing data and rebuild unique index.
Architecture: Schema migration for users table (Section 4.2)
Dependencies: alembic, sqlalchemy
Concepts: Case-insensitive email, partial unique index, data normalization
"""

"""case insensitive email

Revision ID: 095
Revises: 094
Create Date: 2026-02-25
"""

from alembic import op

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Lowercase all existing email addresses
    op.execute("UPDATE users SET email = lower(email) WHERE email != lower(email)")

    # 2. Drop the old case-sensitive partial unique index
    op.execute("DROP INDEX IF EXISTS ix_users_email_active")

    # 3. Create a case-insensitive partial unique index using lower()
    op.execute(
        "CREATE UNIQUE INDEX ix_users_email_active "
        "ON users (lower(email)) WHERE deleted_at IS NULL"
    )

    # 4. Drop the plain b-tree index on email and recreate with lower()
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("CREATE INDEX ix_users_email ON users (lower(email))")


def downgrade() -> None:
    # Restore original case-sensitive indexes
    op.execute("DROP INDEX IF EXISTS ix_users_email_active")
    op.execute(
        "CREATE UNIQUE INDEX ix_users_email_active "
        "ON users (email) WHERE deleted_at IS NULL"
    )

    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("CREATE INDEX ix_users_email ON users (email)")
