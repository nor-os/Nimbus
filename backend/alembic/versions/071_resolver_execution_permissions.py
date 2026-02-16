"""Seed deployment execute and preview permissions.

Revision ID: 071
Revises: 070
Create Date: 2026-02-15
"""

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    conn = op.get_bind()

    # Insert permissions
    conn.execute(sa.text("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'deployment', 'deployment', 'execute', 'Start a deployment execution workflow', true, now(), now()),
            (gen_random_uuid(), 'deployment', 'deployment', 'preview', 'Preview resolved parameters without side effects', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """))

    # Assign to Tenant Admin and Provider Admin roles
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'deployment' AND p.resource = 'deployment'
          AND p.action IN ('execute', 'preview')
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'deployment' AND resource = 'deployment'
              AND action IN ('execute', 'preview')
        )
    """))

    conn.execute(sa.text("""
        DELETE FROM permissions
        WHERE domain = 'deployment' AND resource = 'deployment'
          AND action IN ('execute', 'preview')
    """))
