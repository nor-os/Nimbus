"""Add tenant_tags table for environment-variable-like configuration indirection.

Tags provide typed, per-tenant key-value configuration that can be referenced
by stack parameter overrides in topology graphs.

Revision ID: 044
Revises: 043
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "044"
down_revision: Union[str, None] = "043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("value_schema", JSONB, nullable=True, comment="JSON Schema for value validation"),
        sa.Column("value", JSONB, nullable=True),
        sa.Column("is_secret", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "key", name="uq_tenant_tag_key"),
    )

    # Seed permissions for tenant tags
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'settings', 'tag', 'read', NULL, 'View tenant tag configuration', true, now(), now()),
            (gen_random_uuid(), 'settings', 'tag', 'create', NULL, 'Create new tenant tags', true, now(), now()),
            (gen_random_uuid(), 'settings', 'tag', 'update', NULL, 'Modify existing tenant tags', true, now(), now()),
            (gen_random_uuid(), 'settings', 'tag', 'delete', NULL, 'Remove tenant tags', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING;
    """)

    # Grant read to all roles, write to Tenant Admin and Provider Admin
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE p.domain = 'settings' AND p.resource = 'tag' AND p.action = 'read'
          AND r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE p.domain = 'settings' AND p.resource = 'tag'
          AND p.action IN ('create', 'update', 'delete')
          AND r.name IN ('Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'settings' AND resource = 'tag'
        )
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE domain = 'settings' AND resource = 'tag'
        """
    )
    op.drop_table("tenant_tags")
