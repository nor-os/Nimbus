"""
Overview: Add STACK workflow type and seed 4 system stack lifecycle workflow templates.
Architecture: Alembic migration for stack lifecycle workflows (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Stack lifecycle templates (provision, deprovision, upgrade, failover) using
    existing stack node types. Templates are cloned per-blueprint when provisioned.

Revision ID: 105
Revises: 104
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "105"
down_revision = "104"
branch_labels = None
depends_on = None


def _make_graph(nodes, connections):
    """Build a workflow graph dict from nodes and connections."""
    return {"nodes": nodes, "connections": connections}


PROVISION_GRAPH = _make_graph(
    nodes=[
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 200}, "config": {}},
        {"id": "validate", "type": "script", "label": "Validate Inputs", "position": {"x": 250, "y": 200},
         "config": {"language": "javascript", "code": "// Validate stack input_values against blueprint schema\ncontext.validated = true;\nreturn { validated: true };"}},
        {"id": "deploy_components", "type": "stack_component_action", "label": "Provision Components", "position": {"x": 500, "y": 200},
         "config": {"action": "provision", "order": "depends_on", "parallel": False}},
        {"id": "health_check", "type": "stack_health_check", "label": "Health Check", "position": {"x": 750, "y": 200},
         "config": {"check_type": "post_deploy", "timeout_seconds": 300}},
        {"id": "register_outputs", "type": "script", "label": "Register Outputs", "position": {"x": 1000, "y": 200},
         "config": {"language": "javascript", "code": "// Collect outputs from provisioned components\nreturn { outputs_registered: true };"}},
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1200, "y": 200}, "config": {}},
    ],
    connections=[
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "validate", "targetPort": "in"},
        {"id": "c2", "source": "validate", "sourcePort": "out", "target": "deploy_components", "targetPort": "in"},
        {"id": "c3", "source": "deploy_components", "sourcePort": "out", "target": "health_check", "targetPort": "in"},
        {"id": "c4", "source": "health_check", "sourcePort": "out", "target": "register_outputs", "targetPort": "in"},
        {"id": "c5", "source": "register_outputs", "sourcePort": "out", "target": "end", "targetPort": "in"},
    ],
)

DEPROVISION_GRAPH = _make_graph(
    nodes=[
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 200}, "config": {}},
        {"id": "drain", "type": "script", "label": "Drain Workloads", "position": {"x": 250, "y": 200},
         "config": {"language": "javascript", "code": "// Drain active workloads before teardown\nreturn { drained: true };"}},
        {"id": "destroy_components", "type": "stack_component_action", "label": "Destroy Components", "position": {"x": 500, "y": 200},
         "config": {"action": "destroy", "order": "reverse_depends_on", "parallel": False}},
        {"id": "release_reservations", "type": "stack_reservation_release", "label": "Release Reservations", "position": {"x": 750, "y": 200},
         "config": {}},
        {"id": "deregister", "type": "script", "label": "Deregister Stack", "position": {"x": 1000, "y": 200},
         "config": {"language": "javascript", "code": "// Mark stack as decommissioned in CMDB\nreturn { deregistered: true };"}},
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1200, "y": 200}, "config": {}},
    ],
    connections=[
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "drain", "targetPort": "in"},
        {"id": "c2", "source": "drain", "sourcePort": "out", "target": "destroy_components", "targetPort": "in"},
        {"id": "c3", "source": "destroy_components", "sourcePort": "out", "target": "release_reservations", "targetPort": "in"},
        {"id": "c4", "source": "release_reservations", "sourcePort": "out", "target": "deregister", "targetPort": "in"},
        {"id": "c5", "source": "deregister", "sourcePort": "out", "target": "end", "targetPort": "in"},
    ],
)

UPGRADE_GRAPH = _make_graph(
    nodes=[
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 200}, "config": {}},
        {"id": "pre_check", "type": "stack_health_check", "label": "Pre-Upgrade Health Check", "position": {"x": 250, "y": 200},
         "config": {"check_type": "pre_upgrade", "timeout_seconds": 120}},
        {"id": "snapshot", "type": "stack_snapshot", "label": "Create Snapshot", "position": {"x": 450, "y": 200},
         "config": {"snapshot_type": "pre_upgrade"}},
        {"id": "rolling_upgrade", "type": "stack_component_action", "label": "Rolling Upgrade", "position": {"x": 700, "y": 200},
         "config": {"action": "upgrade", "order": "depends_on", "strategy": "rolling"}},
        {"id": "post_check", "type": "stack_health_check", "label": "Post-Upgrade Validation", "position": {"x": 950, "y": 200},
         "config": {"check_type": "post_upgrade", "timeout_seconds": 300}},
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1150, "y": 200}, "config": {}},
    ],
    connections=[
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "pre_check", "targetPort": "in"},
        {"id": "c2", "source": "pre_check", "sourcePort": "out", "target": "snapshot", "targetPort": "in"},
        {"id": "c3", "source": "snapshot", "sourcePort": "out", "target": "rolling_upgrade", "targetPort": "in"},
        {"id": "c4", "source": "rolling_upgrade", "sourcePort": "out", "target": "post_check", "targetPort": "in"},
        {"id": "c5", "source": "post_check", "sourcePort": "out", "target": "end", "targetPort": "in"},
    ],
)

FAILOVER_GRAPH = _make_graph(
    nodes=[
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 200}, "config": {}},
        {"id": "claim_reservation", "type": "stack_reservation_claim", "label": "Claim DR Reservation", "position": {"x": 250, "y": 200},
         "config": {}},
        {"id": "snapshot_primary", "type": "stack_snapshot", "label": "Snapshot Primary", "position": {"x": 500, "y": 200},
         "config": {"snapshot_type": "pre_failover"}},
        {"id": "promote_standby", "type": "stack_component_action", "label": "Promote Standby", "position": {"x": 750, "y": 200},
         "config": {"action": "promote", "target": "standby"}},
        {"id": "switch_traffic", "type": "script", "label": "Switch Traffic", "position": {"x": 1000, "y": 200},
         "config": {"language": "javascript", "code": "// Update DNS/LB to point to promoted standby\nreturn { traffic_switched: true };"}},
        {"id": "health_check", "type": "stack_health_check", "label": "Health Check", "position": {"x": 1250, "y": 200},
         "config": {"check_type": "post_failover", "timeout_seconds": 300}},
        {"id": "release_old", "type": "stack_reservation_release", "label": "Release Old Primary", "position": {"x": 1500, "y": 200},
         "config": {}},
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1700, "y": 200}, "config": {}},
    ],
    connections=[
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "claim_reservation", "targetPort": "in"},
        {"id": "c2", "source": "claim_reservation", "sourcePort": "out", "target": "snapshot_primary", "targetPort": "in"},
        {"id": "c3", "source": "snapshot_primary", "sourcePort": "out", "target": "promote_standby", "targetPort": "in"},
        {"id": "c4", "source": "promote_standby", "sourcePort": "out", "target": "switch_traffic", "targetPort": "in"},
        {"id": "c5", "source": "switch_traffic", "sourcePort": "out", "target": "health_check", "targetPort": "in"},
        {"id": "c6", "source": "health_check", "sourcePort": "out", "target": "release_old", "targetPort": "in"},
        {"id": "c7", "source": "release_old", "sourcePort": "out", "target": "end", "targetPort": "in"},
    ],
)


TEMPLATES = [
    {
        "name": "stack:provision",
        "description": "Provision a stack instance — validate inputs, deploy components in dependency order, health check, register outputs.",
        "graph": PROVISION_GRAPH,
        "input_schema": {"type": "object", "properties": {"stack_instance_id": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"outputs": {"type": "object"}}},
    },
    {
        "name": "stack:deprovision",
        "description": "Deprovision a stack instance — drain workloads, destroy components in reverse order, release reservations, deregister.",
        "graph": DEPROVISION_GRAPH,
        "input_schema": {"type": "object", "properties": {"stack_instance_id": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"deregistered": {"type": "boolean"}}},
    },
    {
        "name": "stack:upgrade",
        "description": "Upgrade a stack instance — pre-check, snapshot, rolling upgrade per component, post-validation.",
        "graph": UPGRADE_GRAPH,
        "input_schema": {"type": "object", "properties": {"stack_instance_id": {"type": "string"}, "target_version": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"upgraded": {"type": "boolean"}}},
    },
    {
        "name": "stack:failover",
        "description": "Failover to DR — claim reservation, snapshot primary, promote standby, switch traffic, health check, release old.",
        "graph": FAILOVER_GRAPH,
        "input_schema": {"type": "object", "properties": {"stack_instance_id": {"type": "string"}, "reservation_id": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"failover_complete": {"type": "boolean"}}},
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    # Add STACK to workflow_type enum
    conn.execute(sa.text("ALTER TYPE workflow_type ADD VALUE IF NOT EXISTS 'STACK'"))
    conn.execute(sa.text("COMMIT"))

    # Get root tenant ID
    row = conn.execute(sa.text(
        "SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1"
    )).fetchone()
    if not row:
        return
    tenant_id = str(row[0])

    # Get admin user
    user_row = conn.execute(sa.text(
        "SELECT id FROM users WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
    )).fetchone()
    if not user_row:
        return
    user_id = str(user_row[0])

    for tmpl in TEMPLATES:
        # Skip if already exists
        existing = conn.execute(sa.text(
            "SELECT id FROM workflow_definitions WHERE name = :name "
            "AND tenant_id = :tid AND deleted_at IS NULL LIMIT 1"
        ), {"name": tmpl["name"], "tid": tenant_id}).fetchone()
        if existing:
            continue

        conn.execute(sa.text("""
            INSERT INTO workflow_definitions (
                id, tenant_id, name, description, version, graph,
                input_schema, output_schema,
                status, created_by, workflow_type,
                is_system, is_template,
                timeout_seconds, max_concurrent,
                created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :tenant_id, :name, :description, 1,
                CAST(:graph AS jsonb),
                CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb),
                'ACTIVE', :user_id, 'STACK',
                true, true,
                3600, 1,
                NOW(), NOW()
            )
        """), {
            "tenant_id": tenant_id,
            "name": tmpl["name"],
            "description": tmpl["description"],
            "graph": json.dumps(tmpl["graph"]),
            "input_schema": json.dumps(tmpl["input_schema"]),
            "output_schema": json.dumps(tmpl["output_schema"]),
            "user_id": user_id,
        })


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM workflow_definitions WHERE name LIKE 'stack:%' "
        "AND is_system = true AND is_template = true"
    ))
