"""Resolver model restructure — add lifecycle columns and provider compatibility.

Revision ID: 076
Revises: 075
Create Date: 2026-02-15
"""

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    conn = op.get_bind()

    # Add new columns to resolvers table
    op.add_column("resolvers", sa.Column(
        "instance_config_schema", sa.JSON(), nullable=True,
    ))
    op.add_column("resolvers", sa.Column(
        "category", sa.String(100), nullable=True,
    ))
    op.add_column("resolvers", sa.Column(
        "supports_release", sa.Boolean(), nullable=False, server_default="false",
    ))
    op.add_column("resolvers", sa.Column(
        "supports_update", sa.Boolean(), nullable=False, server_default="false",
    ))

    # Create resolver_provider_compatibility table
    op.create_table(
        "resolver_provider_compatibility",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resolver_id", UUID(as_uuid=True), sa.ForeignKey("resolvers.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("resolver_id", "provider_id", name="uq_resolver_provider_compat"),
    )
    op.create_index("ix_resolver_compat_resolver", "resolver_provider_compatibility", ["resolver_id"])
    op.create_index("ix_resolver_compat_provider", "resolver_provider_compatibility", ["provider_id"])

    # Populate instance_config_schema for existing resolvers
    conn.execute(sa.text("""
        UPDATE resolvers SET
            instance_config_schema = '{"type": "object", "properties": {"address_space_id": {"type": "string", "format": "uuid", "title": "Address Space", "description": "UUID of the default address space"}, "default_allocation_type": {"type": "string", "enum": ["subnet", "ip"], "title": "Default Allocation Type", "default": "subnet"}, "ip_version": {"type": "integer", "enum": [4, 6], "title": "IP Version", "default": 4}}, "required": ["address_space_id"]}'::jsonb,
            category = 'networking',
            supports_release = true,
            supports_update = true
        WHERE resolver_type = 'ipam'
    """))

    conn.execute(sa.text("""
        UPDATE resolvers SET
            instance_config_schema = '{"type": "object", "properties": {"pattern": {"type": "string", "title": "Naming Pattern", "description": "Pattern with placeholders: {env}, {type}, {seq:03d}", "default": "{env}-{type}-{seq:03d}"}, "domain": {"type": "string", "title": "Domain", "description": "Domain suffix for FQDN generation"}, "counter_scope": {"type": "string", "enum": ["environment", "global"], "title": "Counter Scope", "default": "environment"}}, "required": ["pattern"]}'::jsonb,
            category = 'naming',
            supports_release = true,
            supports_update = true
        WHERE resolver_type = 'naming'
    """))

    conn.execute(sa.text("""
        UPDATE resolvers SET
            instance_config_schema = '{"type": "object", "properties": {"default_architecture": {"type": "string", "title": "Default Architecture", "description": "Default CPU architecture for image lookups", "default": "x86_64", "enum": ["x86_64", "aarch64"]}}, "required": []}'::jsonb,
            category = 'compute',
            supports_release = false,
            supports_update = true
        WHERE resolver_type = 'image_catalog'
    """))

    # Seed compatibility rows linking all 3 resolvers to all semantic_providers
    conn.execute(sa.text("""
        INSERT INTO resolver_provider_compatibility (id, resolver_id, provider_id, created_at)
        SELECT gen_random_uuid(), r.id, sp.id, now()
        FROM resolvers r
        CROSS JOIN semantic_providers sp
        WHERE r.resolver_type IN ('ipam', 'naming', 'image_catalog')
          AND r.deleted_at IS NULL
          AND sp.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    op.drop_index("ix_resolver_compat_provider")
    op.drop_index("ix_resolver_compat_resolver")
    op.drop_table("resolver_provider_compatibility")
    op.drop_column("resolvers", "supports_update")
    op.drop_column("resolvers", "supports_release")
    op.drop_column("resolvers", "category")
    op.drop_column("resolvers", "instance_config_schema")
