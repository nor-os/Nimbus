"""Connectivity configs and peering configs tables.

Revision ID: 081
Revises: 080
Create Date: 2026-02-17
"""

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # connectivity_configs
    op.create_table(
        "connectivity_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("connectivity_type", sa.String(50), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("remote_config", JSONB, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_connectivity_configs_tenant", "connectivity_configs", ["tenant_id"])
    op.create_index("ix_connectivity_configs_lz", "connectivity_configs", ["landing_zone_id"])

    # peering_configs
    op.create_table(
        "peering_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("peering_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("hub_config", JSONB, nullable=True),
        sa.Column("spoke_config", JSONB, nullable=True),
        sa.Column("routing_config", JSONB, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_peering_configs_tenant", "peering_configs", ["tenant_id"])
    op.create_index("ix_peering_configs_lz", "peering_configs", ["landing_zone_id"])

    # Seed permissions
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cloud', 'connectivity', 'create', 'Create connectivity configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'connectivity', 'read', 'View connectivity configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'connectivity', 'update', 'Modify connectivity configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'connectivity', 'delete', 'Remove connectivity configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'peering', 'create', 'Create peering configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'peering', 'read', 'View peering configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'peering', 'update', 'Modify peering configurations', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'peering', 'delete', 'Remove peering configurations', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Provider Admin', 'Tenant Admin')
            AND p.domain = 'cloud'
            AND p.resource IN ('connectivity', 'peering')
            AND p.action IN ('create', 'read', 'update', 'delete')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_peering_configs_lz", "peering_configs")
    op.drop_index("ix_peering_configs_tenant", "peering_configs")
    op.drop_table("peering_configs")
    op.drop_index("ix_connectivity_configs_lz", "connectivity_configs")
    op.drop_index("ix_connectivity_configs_tenant", "connectivity_configs")
    op.drop_table("connectivity_configs")
