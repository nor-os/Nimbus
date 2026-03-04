"""
Overview: Stack Blueprints schema evolution — versioning, components, instances, governance, DR.
Architecture: Alembic migration for stack blueprint PaaS-grade infrastructure (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Evolve service_clusters into full stack blueprints with versioning, variable wiring,
    stack workflows, runtime instances, governance, and DR reservations.

Revision ID: 102
Revises: 101
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── ALTER service_clusters ─────────────────────────────────────────
    op.add_column("service_clusters", sa.Column(
        "provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "category", sa.String(20), nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "icon", sa.String(100), nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "input_schema", JSONB, nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "output_schema", JSONB, nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "version", sa.Integer, server_default="1", nullable=False,
    ))
    op.add_column("service_clusters", sa.Column(
        "is_published", sa.Boolean, server_default="false", nullable=False,
    ))
    op.add_column("service_clusters", sa.Column(
        "is_system", sa.Boolean, server_default="false", nullable=False,
    ))
    op.add_column("service_clusters", sa.Column(
        "display_name", sa.String(255), nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True,
    ))

    # Make tenant_id nullable on service_clusters (system blueprints have no tenant)
    op.alter_column("service_clusters", "tenant_id", nullable=True)

    op.create_index("ix_sc_provider_id", "service_clusters", ["provider_id"])
    op.create_index("ix_sc_category", "service_clusters", ["category"])
    op.create_index("ix_sc_is_published", "service_clusters", ["is_published"])

    # ── ALTER service_cluster_slots ────────────────────────────────────
    op.add_column("service_cluster_slots", sa.Column(
        "component_id", UUID(as_uuid=True), sa.ForeignKey("components.id"), nullable=True,
    ))
    op.add_column("service_cluster_slots", sa.Column(
        "default_parameters", JSONB, nullable=True,
    ))
    op.add_column("service_cluster_slots", sa.Column(
        "depends_on", JSONB, nullable=True,
    ))

    # ── CREATE stack_blueprint_versions ────────────────────────────────
    op.create_table(
        "stack_blueprint_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("input_schema", JSONB, nullable=True),
        sa.Column("output_schema", JSONB, nullable=True),
        sa.Column("component_graph", JSONB, nullable=True),
        sa.Column("variable_bindings", JSONB, nullable=True),
        sa.Column("changelog", sa.Text, nullable=True),
        sa.Column("published_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("blueprint_id", "version", name="uq_blueprint_version"),
    )

    # ── CREATE stack_blueprint_components ──────────────────────────────
    op.create_table(
        "stack_blueprint_components",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("component_id", UUID(as_uuid=True), sa.ForeignKey("components.id"), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("is_optional", sa.Boolean, server_default="false", nullable=False),
        sa.Column("default_parameters", JSONB, nullable=True),
        sa.Column("depends_on", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("blueprint_id", "node_id", name="uq_blueprint_component_node"),
    )

    # ── CREATE stack_variable_bindings ─────────────────────────────────
    op.create_table(
        "stack_variable_bindings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("variable_name", sa.String(255), nullable=False),
        sa.Column("target_node_id", sa.String(100), nullable=False),
        sa.Column("target_parameter", sa.String(255), nullable=False),
        sa.Column("transform_expression", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── CREATE stack_blueprint_governance ──────────────────────────────
    op.create_table(
        "stack_blueprint_governance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("is_allowed", sa.Boolean, server_default="true", nullable=False),
        sa.Column("parameter_constraints", JSONB, nullable=True),
        sa.Column("max_instances", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("blueprint_id", "tenant_id", name="uq_blueprint_governance_tenant"),
    )

    # ── CREATE stack_workflows ─────────────────────────────────────────
    op.create_table(
        "stack_workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("workflow_definition_id", UUID(as_uuid=True), sa.ForeignKey("workflow_definitions.id"), nullable=False),
        sa.Column("workflow_kind", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_required", sa.Boolean, server_default="false", nullable=False),
        sa.Column("trigger_conditions", JSONB, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── CREATE stack_instances ─────────────────────────────────────────
    op.create_table(
        "stack_instances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, index=True),
        sa.Column("blueprint_version", sa.Integer, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="PLANNED", nullable=False),
        sa.Column("input_values", JSONB, nullable=True),
        sa.Column("output_values", JSONB, nullable=True),
        sa.Column("component_states", JSONB, nullable=True),
        sa.Column("health_status", sa.String(20), server_default="UNKNOWN", nullable=False),
        sa.Column("deployed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "environment_id", "name", name="uq_stack_instance_tenant_env_name"),
    )

    # ── CREATE stack_instance_components ───────────────────────────────
    op.create_table(
        "stack_instance_components",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stack_instance_id", UUID(as_uuid=True), sa.ForeignKey("stack_instances.id"), nullable=False, index=True),
        sa.Column("blueprint_component_id", UUID(as_uuid=True), sa.ForeignKey("stack_blueprint_components.id"), nullable=True),
        sa.Column("component_id", UUID(as_uuid=True), sa.ForeignKey("components.id"), nullable=False),
        sa.Column("component_version", sa.Integer, nullable=True),
        sa.Column("ci_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=True),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=True),
        sa.Column("status", sa.String(30), server_default="PENDING", nullable=False),
        sa.Column("resolved_parameters", JSONB, nullable=True),
        sa.Column("outputs", JSONB, nullable=True),
        sa.Column("pulumi_state_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── CREATE stack_reservations ──────────────────────────────────────
    op.create_table(
        "stack_reservations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stack_instance_id", UUID(as_uuid=True), sa.ForeignKey("stack_instances.id"), nullable=False, index=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("reservation_type", sa.String(30), nullable=False),
        sa.Column("target_environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=True),
        sa.Column("target_provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=True),
        sa.Column("reserved_resources", JSONB, nullable=True),
        sa.Column("rto_seconds", sa.Integer, nullable=True),
        sa.Column("rpo_seconds", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("cost_per_hour", sa.Numeric(12, 4), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_result", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── CREATE reservation_sync_policies ───────────────────────────────
    op.create_table(
        "reservation_sync_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reservation_id", UUID(as_uuid=True), sa.ForeignKey("stack_reservations.id"), nullable=False, index=True),
        sa.Column("source_node_id", sa.String(100), nullable=False),
        sa.Column("target_node_id", sa.String(100), nullable=False),
        sa.Column("sync_method", sa.String(30), nullable=False),
        sa.Column("sync_interval_seconds", sa.Integer, nullable=True),
        sa.Column("sync_workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflow_definitions.id"), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_lag_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Seed permissions ──────────────────────────────────────────────
    permissions = [
        ("infrastructure", "blueprint", "read", "View stack blueprints"),
        ("infrastructure", "blueprint", "manage", "Create and manage stack blueprints"),
        ("infrastructure", "blueprint", "deploy", "Deploy stack instances from blueprints"),
        ("infrastructure", "blueprint", "destroy", "Destroy stack instances"),
        ("infrastructure", "reservation", "read", "View DR reservations"),
        ("infrastructure", "reservation", "manage", "Create and manage DR reservations"),
        ("infrastructure", "reservation", "test", "Test DR failover"),
    ]

    for domain, resource, action, description in permissions:
        conn.execute(sa.text("""
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), :domain, :resource, :action, :description, true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """), {"domain": domain, "resource": resource, "action": action, "description": description})

    # Read Only → read permissions
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Read-Only'
          AND p.domain = 'infrastructure'
          AND p.resource IN ('blueprint', 'reservation')
          AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """))

    # User → read + deploy
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'User'
          AND p.domain = 'infrastructure'
          AND p.resource IN ('blueprint', 'reservation')
          AND p.action IN ('read', 'deploy')
        ON CONFLICT DO NOTHING
    """))

    # Tenant Admin + Provider Admin → all
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'infrastructure'
          AND p.resource IN ('blueprint', 'reservation')
        ON CONFLICT DO NOTHING
    """))

    # ── Seed stack event types ────────────────────────────────────────
    event_types = [
        ("stack.provisioned", "Stack instance provisioned successfully"),
        ("stack.provision.failed", "Stack instance provisioning failed"),
        ("stack.decommissioned", "Stack instance decommissioned"),
        ("stack.failover.started", "Stack DR failover started"),
        ("stack.failover.completed", "Stack DR failover completed"),
        ("stack.failover.failed", "Stack DR failover failed"),
        ("stack.health.degraded", "Stack health degraded"),
        ("stack.health.recovered", "Stack health recovered"),
        ("stack.reservation.claimed", "DR reservation claimed"),
        ("stack.reservation.released", "DR reservation released"),
        ("stack.blueprint.published", "Stack blueprint published"),
    ]

    for name, description in event_types:
        conn.execute(sa.text("""
            INSERT INTO event_types (id, name, description, category, is_system, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), :name, :description, 'STACK', true, true, now(), now())
            ON CONFLICT (name) DO NOTHING
        """), {"name": name, "description": description})


def downgrade() -> None:
    conn = op.get_bind()

    # Remove event types
    conn.execute(sa.text("""
        DELETE FROM event_types WHERE category = 'STACK'
    """))

    # Remove role_permissions
    conn.execute(sa.text("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'infrastructure'
              AND resource IN ('blueprint', 'reservation')
        )
    """))

    # Remove permissions
    conn.execute(sa.text("""
        DELETE FROM permissions
        WHERE domain = 'infrastructure'
          AND resource IN ('blueprint', 'reservation')
    """))

    # Drop new tables
    op.drop_table("reservation_sync_policies")
    op.drop_table("stack_reservations")
    op.drop_table("stack_instance_components")
    op.drop_table("stack_instances")
    op.drop_table("stack_workflows")
    op.drop_table("stack_blueprint_governance")
    op.drop_table("stack_variable_bindings")
    op.drop_table("stack_blueprint_components")
    op.drop_table("stack_blueprint_versions")

    # Remove added columns from service_cluster_slots
    op.drop_column("service_cluster_slots", "depends_on")
    op.drop_column("service_cluster_slots", "default_parameters")
    op.drop_column("service_cluster_slots", "component_id")

    # Remove indexes from service_clusters
    op.drop_index("ix_sc_is_published", "service_clusters")
    op.drop_index("ix_sc_category", "service_clusters")
    op.drop_index("ix_sc_provider_id", "service_clusters")

    # Restore tenant_id to non-nullable
    op.alter_column("service_clusters", "tenant_id", nullable=False)

    # Remove added columns from service_clusters
    op.drop_column("service_clusters", "created_by")
    op.drop_column("service_clusters", "display_name")
    op.drop_column("service_clusters", "is_system")
    op.drop_column("service_clusters", "is_published")
    op.drop_column("service_clusters", "version")
    op.drop_column("service_clusters", "output_schema")
    op.drop_column("service_clusters", "input_schema")
    op.drop_column("service_clusters", "icon")
    op.drop_column("service_clusters", "category")
    op.drop_column("service_clusters", "provider_id")
