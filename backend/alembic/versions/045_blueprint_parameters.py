"""Add stack_blueprint_parameters table and remove semantic_type_id from service_clusters.

Blueprint parameters define what inputs a stack blueprint accepts. Parameters can be
auto-derived from slot semantic types or manually added as custom parameters.

Revision ID: 045
Revises: 044
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "045"
down_revision: Union[str, None] = "044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stack_blueprint_parameters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parameter_schema", JSONB, nullable=True, comment="JSON Schema for parameter validation"),
        sa.Column("default_value", JSONB, nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="custom",
                  comment="slot_derived or custom"),
        sa.Column("source_slot_id", UUID(as_uuid=True), sa.ForeignKey("service_cluster_slots.id"), nullable=True),
        sa.Column("source_property_path", sa.String(200), nullable=True,
                  comment="JSON path within slot semantic type properties_schema"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cluster_id", "name", name="uq_blueprint_param_name"),
    )

    # Remove semantic_type_id from service_clusters
    op.drop_constraint("service_clusters_semantic_type_id_fkey", "service_clusters", type_="foreignkey")
    op.drop_column("service_clusters", "semantic_type_id")

    # Seed permissions
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cmdb', 'blueprint_param', 'read', NULL,
             'View stack blueprint parameter definitions', true, now(), now()),
            (gen_random_uuid(), 'cmdb', 'blueprint_param', 'manage', NULL,
             'Create, update, delete blueprint parameters', true, now(), now())
        ON CONFLICT (domain, resource, action, subtype) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE p.domain = 'cmdb' AND p.resource = 'blueprint_param' AND p.action = 'read'
          AND r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE p.domain = 'cmdb' AND p.resource = 'blueprint_param' AND p.action = 'manage'
          AND r.name IN ('Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Restore semantic_type_id column
    op.add_column(
        "service_clusters",
        sa.Column("semantic_type_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "service_clusters_semantic_type_id_fkey",
        "service_clusters", "semantic_resource_types",
        ["semantic_type_id"], ["id"],
    )

    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE domain = 'cmdb' AND resource = 'blueprint_param');")
    op.execute("DELETE FROM permissions WHERE domain = 'cmdb' AND resource = 'blueprint_param';")
    op.drop_table("stack_blueprint_parameters")
