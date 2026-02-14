"""Extend relationship_types with domain/entity/semantic constraints, create semantic_activity_types,
add FKs to activity_templates and ci_class_activity_associations, seed operational types.

Revision ID: 030
Revises: 029
Create Date: 2026-02-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add domain/entity/semantic constraint columns to relationship_types ──
    op.add_column(
        "relationship_types",
        sa.Column("domain", sa.String(20), nullable=False, server_default="infrastructure"),
    )
    op.add_column(
        "relationship_types",
        sa.Column("source_entity_type", sa.String(20), nullable=False, server_default="ci"),
    )
    op.add_column(
        "relationship_types",
        sa.Column("target_entity_type", sa.String(20), nullable=False, server_default="ci"),
    )
    op.add_column(
        "relationship_types",
        sa.Column("source_semantic_types", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "relationship_types",
        sa.Column("target_semantic_types", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "relationship_types",
        sa.Column("source_semantic_categories", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "relationship_types",
        sa.Column("target_semantic_categories", postgresql.JSONB(), nullable=True),
    )

    # ── 2. Populate constraints on existing infrastructure types ──
    op.execute("""
        UPDATE relationship_types SET source_semantic_categories = '["security"]'::jsonb
        WHERE name = 'secures' AND is_system = true
    """)
    op.execute("""
        UPDATE relationship_types SET source_semantic_categories = '["monitoring"]'::jsonb
        WHERE name = 'monitors' AND is_system = true
    """)
    op.execute("""
        UPDATE relationship_types
        SET source_semantic_categories = '["storage"]'::jsonb,
            target_semantic_categories = '["compute","database","storage"]'::jsonb
        WHERE name = 'backs_up' AND is_system = true
    """)

    # ── 3. Seed 6 operational relationship types ──
    op.execute("""
        INSERT INTO relationship_types (id, name, display_name, inverse_name, description, domain,
            source_entity_type, target_entity_type, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'performed_on', 'Performed On', 'has_performed', 'Activity is performed on a CI',
             'operational', 'activity', 'ci', true, now(), now()),
            (gen_random_uuid(), 'performed_by', 'Performed By', 'performs', 'Activity is performed by an actor',
             'operational', 'activity', 'any', true, now(), now()),
            (gen_random_uuid(), 'triggers', 'Triggers', 'triggered_by', 'An event or CI triggers an activity',
             'operational', 'any', 'activity', true, now(), now()),
            (gen_random_uuid(), 'produces', 'Produces', 'produced_by', 'Activity produces a CI artifact',
             'operational', 'activity', 'ci', true, now(), now()),
            (gen_random_uuid(), 'consumes', 'Consumes', 'consumed_by', 'Activity consumes a CI resource',
             'operational', 'activity', 'ci', true, now(), now()),
            (gen_random_uuid(), 'remediates', 'Remediates', 'remediated_by', 'Activity remediates a CI issue',
             'operational', 'activity', 'ci', true, now(), now())
    """)

    # ── 4. Create semantic_activity_types table ──
    op.create_table(
        "semantic_activity_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("applicable_semantic_categories", postgresql.JSONB(), nullable=True),
        sa.Column("applicable_semantic_types", postgresql.JSONB(), nullable=True),
        sa.Column("default_relationship_kind_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("relationship_types.id"), nullable=True),
        sa.Column("properties_schema", postgresql.JSONB(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 5. Add semantic_activity_type_id FK to activity_templates ──
    op.add_column(
        "activity_templates",
        sa.Column(
            "semantic_activity_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_activity_types.id"),
            nullable=True,
        ),
    )

    # ── 6. Add relationship_type_id FK to ci_class_activity_associations ──
    op.add_column(
        "ci_class_activity_associations",
        sa.Column(
            "relationship_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relationship_types.id"),
            nullable=True,
        ),
    )

    # ── 7. Seed 10 activity types ──
    # First get the performed_on relationship type id for default
    op.execute("""
        INSERT INTO semantic_activity_types (id, name, display_name, category, description, icon,
            applicable_semantic_categories, default_relationship_kind_id, is_system, sort_order,
            created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'provisioning', 'Provisioning', 'lifecycle',
             'Deploy and configure new infrastructure resources', 'rocket',
             '["compute","storage","network","database"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 1, now(), now()),
            (gen_random_uuid(), 'decommission', 'Decommission', 'lifecycle',
             'Retire and remove infrastructure resources', 'trash',
             '["compute","storage","network","database"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 2, now(), now()),
            (gen_random_uuid(), 'backup', 'Backup', 'data_protection',
             'Create and manage data backups', 'shield',
             '["compute","database","storage"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 3, now(), now()),
            (gen_random_uuid(), 'patch_management', 'Patch Management', 'maintenance',
             'Apply security patches and software updates', 'wrench',
             '["compute","database"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 4, now(), now()),
            (gen_random_uuid(), 'security_hardening', 'Security Hardening', 'security',
             'Apply security baselines and hardening configurations', 'lock',
             '["compute","network","database"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 5, now(), now()),
            (gen_random_uuid(), 'monitoring_setup', 'Monitoring Setup', 'observability',
             'Configure monitoring agents and alerting rules', 'eye',
             '["compute","network","database","storage"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 6, now(), now()),
            (gen_random_uuid(), 'incident_response', 'Incident Response', 'operations',
             'Respond to and remediate operational incidents', 'alert-triangle',
             NULL,
             (SELECT id FROM relationship_types WHERE name = 'remediates' LIMIT 1),
             true, 7, now(), now()),
            (gen_random_uuid(), 'capacity_review', 'Capacity Review', 'planning',
             'Review resource utilization and plan capacity changes', 'bar-chart',
             '["compute","storage","database"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 8, now(), now()),
            (gen_random_uuid(), 'certificate_management', 'Certificate Management', 'security',
             'Manage TLS/SSL certificates lifecycle', 'key',
             '["network","compute"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 9, now(), now()),
            (gen_random_uuid(), 'network_configuration', 'Network Configuration', 'network',
             'Configure network routing, firewall rules, and connectivity', 'globe',
             '["network"]'::jsonb,
             (SELECT id FROM relationship_types WHERE name = 'performed_on' LIMIT 1),
             true, 10, now(), now())
    """)

    # ── 8. Assign permissions ──
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'semantic', 'activity-type', 'read', 'View semantic activity types', now(), now()),
            (gen_random_uuid(), 'semantic', 'activity-type', 'manage', 'Manage semantic activity types', now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    # Assign read to all roles, manage to Tenant Admin and Provider Admin
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.domain = 'semantic' AND p.resource = 'activity-type' AND p.action = 'read'
          AND r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
          AND r.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.domain = 'semantic' AND p.resource = 'activity-type' AND p.action = 'manage'
          AND r.name IN ('Tenant Admin', 'Provider Admin')
          AND r.deleted_at IS NULL
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Drop FK columns
    op.drop_column("ci_class_activity_associations", "relationship_type_id")
    op.drop_column("activity_templates", "semantic_activity_type_id")

    # Drop semantic_activity_types table
    op.drop_table("semantic_activity_types")

    # Remove seeded operational relationship types
    op.execute("""
        DELETE FROM relationship_types
        WHERE name IN ('performed_on', 'performed_by', 'triggers', 'produces', 'consumes', 'remediates')
          AND is_system = true
    """)

    # Drop domain/entity/semantic columns from relationship_types
    op.drop_column("relationship_types", "target_semantic_categories")
    op.drop_column("relationship_types", "source_semantic_categories")
    op.drop_column("relationship_types", "target_semantic_types")
    op.drop_column("relationship_types", "source_semantic_types")
    op.drop_column("relationship_types", "target_entity_type")
    op.drop_column("relationship_types", "source_entity_type")
    op.drop_column("relationship_types", "domain")

    # Remove permissions
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'semantic' AND resource = 'activity-type'
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE domain = 'semantic' AND resource = 'activity-type'
    """)
