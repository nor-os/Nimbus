"""
Overview: Add partial unique constraint on cloud_backends.tenant_id for 1:1 tenant-to-backend mapping.
Architecture: Migration for cloud backend tenant uniqueness (Section 11)
Dependencies: alembic, sqlalchemy
Concepts: Partial unique index — only active (non-deleted) backends count, soft-deleted ones don't conflict.
    Pre-step soft-deletes duplicate backends per tenant, keeping the most recently updated one.
"""

"""unique backend per tenant

Revision ID: 063
Revises: 062
Create Date: 2026-02-14
"""

from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Soft-delete duplicate backends per tenant, keeping the one with the latest updated_at
    op.execute("""
        UPDATE cloud_backends
        SET deleted_at = NOW()
        WHERE deleted_at IS NULL
          AND id NOT IN (
            SELECT DISTINCT ON (tenant_id) id
            FROM cloud_backends
            WHERE deleted_at IS NULL
            ORDER BY tenant_id, updated_at DESC NULLS LAST
          )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_cloud_backends_tenant_id
        ON cloud_backends (tenant_id)
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cloud_backends_tenant_id")
