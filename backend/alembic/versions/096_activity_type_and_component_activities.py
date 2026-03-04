"""
Overview: Redesign deployment operations — activity-centric model with per-component activities.
Architecture: Schema + data migration for deployment activity restructuring (Section 11.5)
Dependencies: 095_case_insensitive_email
Concepts: ActivityType replaces ActivityScope, component_id for per-component activities,
    template_activity_id for clone tracking, 3 workflow templates (not 6),
    rollback/validate/dry-run become activities within workflows
"""

import json

from alembic import op
import sqlalchemy as sa

revision: str = "096"
down_revision: str = "095"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# New template graphs — 3 workflows with embedded activity nodes
# ---------------------------------------------------------------------------

DEPLOY_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 250}, "config": {}},
        {
            "id": "dryrun_activity", "type": "activity", "label": "Dry Run",
            "position": {"x": 250, "y": 250},
            "config": {
                "activity_slug": "dry-run-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "parameters": "$input.parameters",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {
            "id": "approval_gate", "type": "approval_gate", "label": "Approval Gate",
            "position": {"x": 450, "y": 250},
            "config": {"approval_policy": "default"},
        },
        {
            "id": "deploy_activity", "type": "activity", "label": "Deploy Resource",
            "position": {"x": 650, "y": 250},
            "config": {
                "activity_slug": "deploy-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "provider_id": "$input.provider_id",
                    "semantic_type_id": "$input.semantic_type_id",
                    "parameters": "$input.parameters",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {
            "id": "validate_activity", "type": "activity", "label": "Validate Resource",
            "position": {"x": 850, "y": 250},
            "config": {
                "activity_slug": "validate-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1050, "y": 250}, "config": {}},
        {
            "id": "rollback_activity", "type": "activity", "label": "Rollback Resource",
            "position": {"x": 850, "y": 450},
            "config": {
                "activity_slug": "rollback-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "target_version": "$input.target_version",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 1050, "y": 450}, "config": {}},
    ],
    "connections": [
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "dryrun_activity", "targetPort": "in"},
        {"id": "c2", "source": "dryrun_activity", "sourcePort": "out", "target": "approval_gate", "targetPort": "in"},
        {"id": "c3", "source": "approval_gate", "sourcePort": "approved", "target": "deploy_activity", "targetPort": "in"},
        {"id": "c4", "source": "deploy_activity", "sourcePort": "out", "target": "validate_activity", "targetPort": "in"},
        {"id": "c5", "source": "validate_activity", "sourcePort": "out", "target": "end", "targetPort": "in"},
        {"id": "c6", "source": "deploy_activity", "sourcePort": "error", "target": "rollback_activity", "targetPort": "in"},
        {"id": "c7", "source": "rollback_activity", "sourcePort": "out", "target": "end_error", "targetPort": "in"},
        {"id": "c8", "source": "rollback_activity", "sourcePort": "error", "target": "end_error", "targetPort": "in"},
    ],
}

DECOMMISSION_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 250}, "config": {}},
        {
            "id": "dryrun_activity", "type": "activity", "label": "Dry Run",
            "position": {"x": 250, "y": 250},
            "config": {
                "activity_slug": "dry-run-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {
            "id": "approval_gate", "type": "approval_gate", "label": "Approval Gate",
            "position": {"x": 450, "y": 250},
            "config": {"approval_policy": "default"},
        },
        {
            "id": "decommission_activity", "type": "activity", "label": "Decommission Resource",
            "position": {"x": 650, "y": 250},
            "config": {
                "activity_slug": "decommission-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "stack_name": "$input.stack_name",
                    "confirm_name": "$input.confirm_name",
                },
            },
        },
        {
            "id": "validate_activity", "type": "activity", "label": "Validate Resource",
            "position": {"x": 850, "y": 250},
            "config": {
                "activity_slug": "validate-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1050, "y": 250}, "config": {}},
        {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 850, "y": 450}, "config": {}},
    ],
    "connections": [
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "dryrun_activity", "targetPort": "in"},
        {"id": "c2", "source": "dryrun_activity", "sourcePort": "out", "target": "approval_gate", "targetPort": "in"},
        {"id": "c3", "source": "approval_gate", "sourcePort": "approved", "target": "decommission_activity", "targetPort": "in"},
        {"id": "c4", "source": "decommission_activity", "sourcePort": "out", "target": "validate_activity", "targetPort": "in"},
        {"id": "c5", "source": "validate_activity", "sourcePort": "out", "target": "end", "targetPort": "in"},
        {"id": "c6", "source": "decommission_activity", "sourcePort": "error", "target": "end_error", "targetPort": "in"},
    ],
}

UPGRADE_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "label": "Start", "position": {"x": 50, "y": 250}, "config": {}},
        {
            "id": "dryrun_activity", "type": "activity", "label": "Dry Run",
            "position": {"x": 250, "y": 250},
            "config": {
                "activity_slug": "dry-run-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "parameters": "$input.parameters",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {
            "id": "approval_gate", "type": "approval_gate", "label": "Approval Gate",
            "position": {"x": 450, "y": 250},
            "config": {"approval_policy": "default"},
        },
        {
            "id": "upgrade_activity", "type": "activity", "label": "Upgrade Resource",
            "position": {"x": 650, "y": 250},
            "config": {
                "activity_slug": "upgrade-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "parameters": "$input.parameters",
                    "stack_name": "$input.stack_name",
                    "target_version": "$input.target_version",
                },
            },
        },
        {
            "id": "validate_activity", "type": "activity", "label": "Validate Resource",
            "position": {"x": 850, "y": 250},
            "config": {
                "activity_slug": "validate-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {"id": "end", "type": "end", "label": "End", "position": {"x": 1050, "y": 250}, "config": {}},
        {
            "id": "rollback_activity", "type": "activity", "label": "Rollback Resource",
            "position": {"x": 850, "y": 450},
            "config": {
                "activity_slug": "rollback-resource",
                "activity_id": None,
                "parameter_bindings": {
                    "component_id": "$input.component_id",
                    "target_version": "$input.target_version",
                    "stack_name": "$input.stack_name",
                },
            },
        },
        {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 1050, "y": 450}, "config": {}},
    ],
    "connections": [
        {"id": "c1", "source": "start", "sourcePort": "out", "target": "dryrun_activity", "targetPort": "in"},
        {"id": "c2", "source": "dryrun_activity", "sourcePort": "out", "target": "approval_gate", "targetPort": "in"},
        {"id": "c3", "source": "approval_gate", "sourcePort": "approved", "target": "upgrade_activity", "targetPort": "in"},
        {"id": "c4", "source": "upgrade_activity", "sourcePort": "out", "target": "validate_activity", "targetPort": "in"},
        {"id": "c5", "source": "validate_activity", "sourcePort": "out", "target": "end", "targetPort": "in"},
        {"id": "c6", "source": "upgrade_activity", "sourcePort": "error", "target": "rollback_activity", "targetPort": "in"},
        {"id": "c7", "source": "rollback_activity", "sourcePort": "out", "target": "end_error", "targetPort": "in"},
        {"id": "c8", "source": "rollback_activity", "sourcePort": "error", "target": "end_error", "targetPort": "in"},
    ],
}


def upgrade() -> None:
    # ── 1. Add activity_type column ──
    op.add_column(
        "automated_activities",
        sa.Column("activity_type", sa.String(20), nullable=True),
    )

    # ── 2. Add component_id column ──
    op.add_column(
        "automated_activities",
        sa.Column("component_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_automated_activities_component_id",
        "automated_activities",
        "components",
        ["component_id"],
        ["id"],
    )
    op.create_index(
        "ix_automated_activities_component_id",
        "automated_activities",
        ["component_id"],
    )

    # ── 3. Add template_activity_id column ──
    op.add_column(
        "automated_activities",
        sa.Column("template_activity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_automated_activities_template_activity_id",
        "automated_activities",
        "automated_activities",
        ["template_activity_id"],
        ["id"],
    )

    # ── 4. Migrate scope → activity_type ──
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET activity_type = CASE
            WHEN scope = 'WORKFLOW' THEN 'DEPLOYMENT'
            WHEN scope = 'COMPONENT' THEN 'DAY2'
            ELSE 'DEPLOYMENT'
        END
        WHERE activity_type IS NULL
    """))

    # Set NOT NULL + default after data migration
    op.alter_column(
        "automated_activities",
        "activity_type",
        nullable=False,
        server_default="DEPLOYMENT",
    )

    # ── 5. Soft-delete rollback, validate, dry-run workflow templates ──
    conn.execute(sa.text("""
        UPDATE workflow_definitions
        SET deleted_at = NOW()
        WHERE is_template = true AND is_system = true
          AND workflow_type = 'DEPLOYMENT'
          AND name IN ('deployment:rollback', 'deployment:validate', 'deployment:dry-run')
          AND deleted_at IS NULL
    """))

    # ── 6. Update 3 remaining template graphs with full activity pipelines ──
    template_graphs = {
        "deployment:deploy": DEPLOY_GRAPH,
        "deployment:decommission": DECOMMISSION_GRAPH,
        "deployment:upgrade": UPGRADE_GRAPH,
    }
    for template_name, graph in template_graphs.items():
        conn.execute(
            sa.text("""
                UPDATE workflow_definitions
                SET graph = CAST(:graph AS jsonb), updated_at = NOW()
                WHERE is_template = true AND is_system = true
                  AND workflow_type = 'DEPLOYMENT' AND name = :name
                  AND deleted_at IS NULL
            """).bindparams(
                name=template_name,
                graph=json.dumps(graph),
            )
        )

    # ── 7. Fix graph format in all existing workflow definitions (data→config, sourceOutput→sourcePort) ──
    conn.execute(sa.text("""
        UPDATE workflow_definitions
        SET graph = (
            SELECT jsonb_build_object(
                'nodes', (
                    SELECT jsonb_agg(
                        CASE
                            WHEN n ? 'data' AND NOT (n ? 'config')
                            THEN (n - 'data') || jsonb_build_object('config', n->'data')
                            ELSE n
                        END
                    )
                    FROM jsonb_array_elements(graph->'nodes') AS n
                ),
                'connections', (
                    SELECT jsonb_agg(
                        CASE
                            WHEN c ? 'sourceOutput'
                            THEN (c - 'sourceOutput' - 'targetInput')
                                || jsonb_build_object(
                                    'sourcePort', c->'sourceOutput',
                                    'targetPort', c->'targetInput'
                                )
                            ELSE c
                        END
                    )
                    FROM jsonb_array_elements(graph->'connections') AS c
                )
            )
        ),
        updated_at = NOW()
        WHERE graph IS NOT NULL
          AND deleted_at IS NULL
          AND (
              EXISTS (SELECT 1 FROM jsonb_array_elements(graph->'nodes') AS n WHERE n ? 'data' AND NOT (n ? 'config'))
              OR EXISTS (SELECT 1 FROM jsonb_array_elements(graph->'connections') AS c WHERE c ? 'sourceOutput')
          )
    """))

    # ── 8. Soft-delete ComponentOperation records for rollback, validate, dry-run ──
    conn.execute(sa.text("""
        UPDATE component_operations
        SET deleted_at = NOW()
        WHERE name IN ('rollback', 'validate', 'dry-run')
          AND operation_category = 'DEPLOYMENT'
          AND deleted_at IS NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Restore soft-deleted component operations
    conn.execute(sa.text("""
        UPDATE component_operations
        SET deleted_at = NULL
        WHERE name IN ('rollback', 'validate', 'dry-run')
          AND operation_category = 'DEPLOYMENT'
    """))

    # Restore soft-deleted workflow templates
    conn.execute(sa.text("""
        UPDATE workflow_definitions
        SET deleted_at = NULL
        WHERE is_template = true AND is_system = true
          AND workflow_type = 'DEPLOYMENT'
          AND name IN ('deployment:rollback', 'deployment:validate', 'deployment:dry-run')
    """))

    # Remove activity_type default and column
    op.alter_column("automated_activities", "activity_type", server_default=None)

    op.drop_constraint("fk_automated_activities_template_activity_id", "automated_activities", type_="foreignkey")
    op.drop_column("automated_activities", "template_activity_id")

    op.drop_index("ix_automated_activities_component_id", table_name="automated_activities")
    op.drop_constraint("fk_automated_activities_component_id", "automated_activities", type_="foreignkey")
    op.drop_column("automated_activities", "component_id")

    op.drop_column("automated_activities", "activity_type")
