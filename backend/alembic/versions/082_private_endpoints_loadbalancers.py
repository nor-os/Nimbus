"""Private endpoints and load balancer tables.

Revision ID: 082
Revises: 081
Create Date: 2026-02-17
"""

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # private_endpoint_policies (LZ-level templates)
    op.create_table(
        "private_endpoint_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("service_name", sa.String(500), nullable=False),
        sa.Column("endpoint_type", sa.String(50), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pe_policies_tenant", "private_endpoint_policies", ["tenant_id"])
    op.create_index("ix_pe_policies_lz", "private_endpoint_policies", ["landing_zone_id"])

    # environment_private_endpoints (per-env instances)
    op.create_table(
        "environment_private_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=False),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("private_endpoint_policies.id"), nullable=True),
        sa.Column("service_name", sa.String(500), nullable=False),
        sa.Column("endpoint_type", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("cloud_resource_id", sa.String(500), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_env_pe_tenant", "environment_private_endpoints", ["tenant_id"])
    op.create_index("ix_env_pe_environment", "environment_private_endpoints", ["environment_id"])

    # shared_load_balancers (LZ-level)
    op.create_table(
        "shared_load_balancers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lb_type", sa.String(50), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("cloud_resource_id", sa.String(500), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shared_lb_tenant", "shared_load_balancers", ["tenant_id"])
    op.create_index("ix_shared_lb_lz", "shared_load_balancers", ["landing_zone_id"])

    # environment_load_balancers (per-env)
    op.create_table(
        "environment_load_balancers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=False),
        sa.Column("shared_lb_id", UUID(as_uuid=True), sa.ForeignKey("shared_load_balancers.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lb_type", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("cloud_resource_id", sa.String(500), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_env_lb_tenant", "environment_load_balancers", ["tenant_id"])
    op.create_index("ix_env_lb_environment", "environment_load_balancers", ["environment_id"])

    # Seed permissions
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cloud', 'privateendpoint', 'create', 'Create private endpoint configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'privateendpoint', 'read', 'View private endpoint configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'privateendpoint', 'update', 'Modify private endpoint configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'privateendpoint', 'delete', 'Remove private endpoint configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'loadbalancer', 'create', 'Create load balancer configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'loadbalancer', 'read', 'View load balancer configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'loadbalancer', 'update', 'Modify load balancer configs', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'loadbalancer', 'delete', 'Remove load balancer configs', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Provider Admin', 'Tenant Admin')
            AND p.domain = 'cloud'
            AND p.resource IN ('privateendpoint', 'loadbalancer')
            AND p.action IN ('create', 'read', 'update', 'delete')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_env_lb_environment", "environment_load_balancers")
    op.drop_index("ix_env_lb_tenant", "environment_load_balancers")
    op.drop_table("environment_load_balancers")
    op.drop_index("ix_shared_lb_lz", "shared_load_balancers")
    op.drop_index("ix_shared_lb_tenant", "shared_load_balancers")
    op.drop_table("shared_load_balancers")
    op.drop_index("ix_env_pe_environment", "environment_private_endpoints")
    op.drop_index("ix_env_pe_tenant", "environment_private_endpoints")
    op.drop_table("environment_private_endpoints")
    op.drop_index("ix_pe_policies_lz", "private_endpoint_policies")
    op.drop_index("ix_pe_policies_tenant", "private_endpoint_policies")
    op.drop_table("private_endpoint_policies")
