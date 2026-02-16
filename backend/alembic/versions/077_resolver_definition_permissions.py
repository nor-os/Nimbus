"""Seed resolver definition CRUD permissions.

Revision ID: 077
Revises: 076
Create Date: 2026-02-15
"""

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    conn = op.get_bind()

    # Insert resolver definition permissions
    conn.execute(sa.text("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'resolver', 'definition', 'read', 'View resolver definitions', true, now(), now()),
            (gen_random_uuid(), 'resolver', 'definition', 'create', 'Create resolver definitions', true, now(), now()),
            (gen_random_uuid(), 'resolver', 'definition', 'update', 'Update resolver definitions', true, now(), now()),
            (gen_random_uuid(), 'resolver', 'definition', 'delete', 'Delete resolver definitions', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """))

    # Assign read to Tenant Admin + Provider Admin
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'resolver' AND p.resource = 'definition'
          AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """))

    # Assign CUD to Provider Admin only
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Provider Admin'
          AND p.domain = 'resolver' AND p.resource = 'definition'
          AND p.action IN ('create', 'update', 'delete')
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'resolver' AND resource = 'definition'
              AND action IN ('read', 'create', 'update', 'delete')
        )
    """))

    conn.execute(sa.text("""
        DELETE FROM permissions
        WHERE domain = 'resolver' AND resource = 'definition'
          AND action IN ('read', 'create', 'update', 'delete')
    """))
