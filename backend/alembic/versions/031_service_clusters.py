"""Add service_clusters, service_cluster_slots, and service_cluster_members tables.

Supports logical grouping of CIs into service units with role-based slots,
class constraints, and member assignment tracking. Adds 'services' semantic
category with service-oriented types that bridge infrastructure assets and
business service delivery.

Revision ID: 031
Revises: 030
Create Date: 2026-02-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Seed 'services' semantic category ─────────────────────────────
    op.execute("""
        INSERT INTO semantic_categories (id, name, display_name, description, icon, sort_order, created_at, updated_at)
        VALUES (
            gen_random_uuid(), 'services', 'Services',
            'Business and managed services — the bridge between infrastructure assets and service delivery',
            'briefcase', 8, now(), now()
        )
        ON CONFLICT (name) DO NOTHING;
    """)

    # ── Seed service semantic types ───────────────────────────────────
    op.execute("""
        INSERT INTO semantic_resource_types
            (id, category_id, name, display_name, description, icon, properties_schema, allowed_relationship_kinds, sort_order, created_at, updated_at)
        SELECT
            gen_random_uuid(), c.id, v.name, v.display_name, v.description, v.icon,
            v.props::jsonb, v.rels::jsonb, v.sort_order, now(), now()
        FROM semantic_categories c,
        (VALUES
            ('ServiceCluster', 'Service Cluster',
             'A logical group of resources forming a service unit with defined role slots',
             'layers',
             '[{"name":"cluster_type","display_name":"Cluster Type","data_type":"string","required": true},{"name":"target_size","display_name":"Target Size","data_type":"integer"},{"name":"sla_target","display_name":"SLA Target","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 1),
            ('ServiceGroup', 'Service Group',
             'A logical grouping of related services for organizational purposes',
             'folder',
             '[{"name":"group_purpose","display_name":"Group Purpose","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 2),
            ('ManagedService', 'Managed Service',
             'A fully managed service delivered to tenants (e.g., Managed Firewall, Managed Backup)',
             'briefcase',
             '[{"name":"service_category","display_name":"Service Category","data_type":"string","required": true},{"name":"operating_model","display_name":"Operating Model","data_type":"string"},{"name":"coverage_model","display_name":"Coverage Model","data_type":"string"},{"name":"sla_tier","display_name":"SLA Tier","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 3),
            ('SecurityService', 'Security Service',
             'Security-focused service (SIEM, vulnerability management, WAF, SOC)',
             'shield',
             '[{"name":"security_domain","display_name":"Security Domain","data_type":"string","required": true},{"name":"compliance_frameworks","display_name":"Compliance Frameworks","data_type":"string"},{"name":"coverage_model","display_name":"Coverage Model","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","secures","monitored_by"]', 4),
            ('ConsultingService', 'Consulting Service',
             'Advisory and consulting service (architecture review, migration planning, optimization)',
             'users',
             '[{"name":"consulting_type","display_name":"Consulting Type","data_type":"string","required": true},{"name":"delivery_model","display_name":"Delivery Model","data_type":"string"},{"name":"measuring_unit","display_name":"Measuring Unit","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on"]', 5),
            ('SupportService', 'Support Service',
             'Operational support service (helpdesk, L1/L2/L3, incident response, on-call)',
             'headphones',
             '[{"name":"support_tier","display_name":"Support Tier","data_type":"string","required": true},{"name":"coverage_model","display_name":"Coverage Model","data_type":"string"},{"name":"response_time_minutes","display_name":"Response Time","data_type":"integer"},{"name":"resolution_time_hours","display_name":"Resolution Time","data_type":"integer"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 6),
            ('IncidentManagement', 'Incident Management',
             'Incident management process service (detection, triage, resolution, post-mortem)',
             'alert-triangle',
             '[{"name":"process_scope","display_name":"Process Scope","data_type":"string","required": true},{"name":"severity_levels","display_name":"Severity Levels","data_type":"string"},{"name":"escalation_policy","display_name":"Escalation Policy","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 7),
            ('PlatformService', 'Platform Service',
             'Platform-level service (CI/CD, container orchestration, API gateway, service mesh)',
             'grid',
             '[{"name":"platform_type","display_name":"Platform Type","data_type":"string","required": true},{"name":"target_environment","display_name":"Target Environment","data_type":"string"},{"name":"state","display_name":"State","data_type":"string","required": true}]',
             '["contains","connects_to","depends_on","monitored_by"]', 8)
        ) AS v(name, display_name, description, icon, props, rels, sort_order)
        WHERE c.name = 'services'
        ON CONFLICT DO NOTHING;
    """)

    # ── Seed CI classes for each service semantic type ────────────────
    op.execute("""
        INSERT INTO ci_classes (id, tenant_id, name, display_name, semantic_type_id, icon, is_system, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), NULL, srt.name, srt.display_name, srt.id, srt.icon, true, true, now(), now()
        FROM semantic_resource_types srt
        JOIN semantic_categories sc ON srt.category_id = sc.id
        WHERE sc.name = 'services'
          AND NOT EXISTS (
              SELECT 1 FROM ci_classes cc WHERE cc.name = srt.name AND cc.is_system = true
          );
    """)

    # ── service_clusters ──────────────────────────────────────────────
    op.create_table(
        "service_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cluster_type", sa.String(50), nullable=False,
                  server_default="service_cluster"),
        sa.Column("semantic_type_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("semantic_resource_types.id"), nullable=True),
        sa.Column("architecture_topology_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("architecture_topologies.id"), nullable=True),
        sa.Column("topology_node_id", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "name",
                            name="uq_service_cluster_tenant_name"),
    )
    op.create_index("ix_sc_tenant_id", "service_clusters", ["tenant_id"])
    op.create_index("ix_sc_tenant_type", "service_clusters",
                    ["tenant_id", "cluster_type"])
    op.create_index("ix_sc_semantic_type", "service_clusters", ["semantic_type_id"])

    # ── service_cluster_slots ─────────────────────────────────────────
    op.create_table(
        "service_cluster_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_clusters.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("allowed_ci_class_ids", postgresql.JSONB, nullable=True),
        sa.Column("min_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("max_count", sa.Integer, nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=False,
                  server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cluster_id", "name",
                            name="uq_slot_cluster_name"),
    )
    op.create_index("ix_scs_cluster_id", "service_cluster_slots", ["cluster_id"])

    # ── service_cluster_members ───────────────────────────────────────
    op.create_table(
        "service_cluster_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_clusters.id"), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_cluster_slots.id"), nullable=False),
        sa.Column("ci_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("configuration_items.id"), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cluster_id", "slot_id", "ci_id",
                            name="uq_member_cluster_slot_ci"),
    )
    op.create_index("ix_scm_cluster_id", "service_cluster_members", ["cluster_id"])
    op.create_index("ix_scm_slot_id", "service_cluster_members", ["slot_id"])
    op.create_index("ix_scm_ci_id", "service_cluster_members", ["ci_id"])

    # ── Seed permissions ──────────────────────────────────────────────
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cmdb', 'cluster', 'read',   'View service clusters',               now(), now()),
            (gen_random_uuid(), 'cmdb', 'cluster', 'create', 'Create service clusters',             now(), now()),
            (gen_random_uuid(), 'cmdb', 'cluster', 'update', 'Update service clusters',             now(), now()),
            (gen_random_uuid(), 'cmdb', 'cluster', 'delete', 'Soft-delete service clusters',       now(), now()),
            (gen_random_uuid(), 'cmdb', 'cluster', 'manage', 'Full management of service clusters', now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING;
    """)

    # Assign read to all 4 roles, write perms to Tenant Admin + Provider Admin
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.domain = 'cmdb' AND p.resource = 'cluster' AND p.action = 'read'
          AND r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.domain = 'cmdb' AND p.resource = 'cluster'
          AND p.action IN ('create', 'update', 'delete', 'manage')
          AND r.name IN ('Tenant Admin', 'Provider Admin')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Remove role_permissions
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'cmdb' AND resource = 'cluster'
        );
    """)
    op.execute("DELETE FROM permissions WHERE domain = 'cmdb' AND resource = 'cluster';")

    op.drop_table("service_cluster_members")
    op.drop_table("service_cluster_slots")
    op.drop_table("service_clusters")

    # Remove CI classes for service semantic types
    op.execute("""
        DELETE FROM ci_classes
        WHERE is_system = true AND semantic_type_id IN (
            SELECT srt.id FROM semantic_resource_types srt
            JOIN semantic_categories sc ON srt.category_id = sc.id
            WHERE sc.name = 'services'
        );
    """)
    # Remove service semantic types
    op.execute("""
        DELETE FROM semantic_resource_types
        WHERE category_id IN (SELECT id FROM semantic_categories WHERE name = 'services');
    """)
    op.execute("DELETE FROM semantic_categories WHERE name = 'services';")
