"""
Overview: Update deployment workflow templates from script nodes to activity nodes.
Architecture: Data migration for deployment template graphs (Section 11)
Dependencies: 092_seed_deployment_activities
Concepts: Activity nodes replace script placeholders, activity_slug for template-time reference,
    parameter_bindings map workflow inputs to activity inputs, CMDB record nodes for state tracking
"""

import json

from alembic import op
import sqlalchemy as sa

revision: str = "093"
down_revision: str = "092"
branch_labels = None
depends_on = None


# New activity-node-based graphs for each deployment template
TEMPLATE_GRAPHS = {
    "deployment:deploy": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "deploy_activity", "type": "activity", "label": "Deploy Resource",
                "position": {"x": 350, "y": 200},
                "data": {
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
                "id": "cmdb_record", "type": "script", "label": "Record Deployment in CMDB",
                "position": {"x": 600, "y": 200},
                "data": {"script": "# Record deployment result in CMDB\noutput = {'recorded': True}"},
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 850, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "deploy_activity", "targetInput": "in"},
            {"id": "c2", "source": "deploy_activity", "sourceOutput": "out", "target": "cmdb_record", "targetInput": "in"},
            {"id": "c3", "source": "deploy_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
            {"id": "c4", "source": "cmdb_record", "sourceOutput": "out", "target": "end", "targetInput": "in"},
        ],
    },
    "deployment:decommission": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "decommission_activity", "type": "activity", "label": "Decommission Resource",
                "position": {"x": 350, "y": 200},
                "data": {
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
                "id": "cmdb_record", "type": "script", "label": "Mark Decommissioned in CMDB",
                "position": {"x": 600, "y": 200},
                "data": {"script": "# Mark resource as decommissioned in CMDB\noutput = {'decommissioned': True}"},
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 850, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "decommission_activity", "targetInput": "in"},
            {"id": "c2", "source": "decommission_activity", "sourceOutput": "out", "target": "cmdb_record", "targetInput": "in"},
            {"id": "c3", "source": "decommission_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
            {"id": "c4", "source": "cmdb_record", "sourceOutput": "out", "target": "end", "targetInput": "in"},
        ],
    },
    "deployment:rollback": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "rollback_activity", "type": "activity", "label": "Rollback Resource",
                "position": {"x": 350, "y": 200},
                "data": {
                    "activity_slug": "rollback-resource",
                    "activity_id": None,
                    "parameter_bindings": {
                        "component_id": "$input.component_id",
                        "target_version": "$input.target_version",
                        "stack_name": "$input.stack_name",
                    },
                },
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "rollback_activity", "targetInput": "in"},
            {"id": "c2", "source": "rollback_activity", "sourceOutput": "out", "target": "end", "targetInput": "in"},
            {"id": "c3", "source": "rollback_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
        ],
    },
    "deployment:upgrade": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "upgrade_activity", "type": "activity", "label": "Upgrade Resource",
                "position": {"x": 350, "y": 200},
                "data": {
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
                "id": "cmdb_record", "type": "script", "label": "Update Version in CMDB",
                "position": {"x": 600, "y": 200},
                "data": {"script": "# Update resource version in CMDB\noutput = {'version_updated': True}"},
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 850, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "upgrade_activity", "targetInput": "in"},
            {"id": "c2", "source": "upgrade_activity", "sourceOutput": "out", "target": "cmdb_record", "targetInput": "in"},
            {"id": "c3", "source": "upgrade_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
            {"id": "c4", "source": "cmdb_record", "sourceOutput": "out", "target": "end", "targetInput": "in"},
        ],
    },
    "deployment:validate": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "validate_activity", "type": "activity", "label": "Validate Resource",
                "position": {"x": 350, "y": 200},
                "data": {
                    "activity_slug": "validate-resource",
                    "activity_id": None,
                    "parameter_bindings": {
                        "component_id": "$input.component_id",
                        "stack_name": "$input.stack_name",
                    },
                },
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "validate_activity", "targetInput": "in"},
            {"id": "c2", "source": "validate_activity", "sourceOutput": "out", "target": "end", "targetInput": "in"},
            {"id": "c3", "source": "validate_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
        ],
    },
    "deployment:dry-run": {
        "nodes": [
            {"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}},
            {
                "id": "dryrun_activity", "type": "activity", "label": "Dry Run",
                "position": {"x": 350, "y": 200},
                "data": {
                    "activity_slug": "dry-run-resource",
                    "activity_id": None,
                    "parameter_bindings": {
                        "component_id": "$input.component_id",
                        "parameters": "$input.parameters",
                        "stack_name": "$input.stack_name",
                    },
                },
            },
            {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}},
            {"id": "end_error", "type": "end", "label": "Error End", "position": {"x": 600, "y": 400}, "data": {}},
        ],
        "connections": [
            {"id": "c1", "source": "start", "sourceOutput": "out", "target": "dryrun_activity", "targetInput": "in"},
            {"id": "c2", "source": "dryrun_activity", "sourceOutput": "out", "target": "end", "targetInput": "in"},
            {"id": "c3", "source": "dryrun_activity", "sourceOutput": "error", "target": "end_error", "targetInput": "in"},
        ],
    },
}


def upgrade() -> None:
    for template_name, graph in TEMPLATE_GRAPHS.items():
        op.execute(
            sa.text(
                """
                UPDATE workflow_definitions
                SET graph = CAST(:graph AS jsonb), updated_at = NOW()
                WHERE is_template = true AND is_system = true
                  AND workflow_type = 'DEPLOYMENT' AND name = :name
                """
            ).bindparams(
                name=template_name,
                graph=json.dumps(graph),
            )
        )


def downgrade() -> None:
    # Revert to original script-based graphs
    old_graphs = {
        "deployment:deploy": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "deploy", "type": "script", "label": "Deploy Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Deploy logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "deploy", "targetInput": "in"}, {"id": "c2", "source": "deploy", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        "deployment:decommission": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "decommission", "type": "script", "label": "Decommission Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Decommission logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "decommission", "targetInput": "in"}, {"id": "c2", "source": "decommission", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        "deployment:rollback": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "rollback", "type": "script", "label": "Rollback Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Rollback logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "rollback", "targetInput": "in"}, {"id": "c2", "source": "rollback", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        "deployment:upgrade": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "upgrade", "type": "script", "label": "Upgrade Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Upgrade logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "upgrade", "targetInput": "in"}, {"id": "c2", "source": "upgrade", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        "deployment:validate": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "validate", "type": "script", "label": "Validate Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Validation logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "validate", "targetInput": "in"}, {"id": "c2", "source": "validate", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        "deployment:dry-run": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "dryrun", "type": "script", "label": "Dry Run", "position": {"x": 350, "y": 200}, "data": {"script": "# Dry-run logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "dryrun", "targetInput": "in"}, {"id": "c2", "source": "dryrun", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
    }
    for template_name, graph_json in old_graphs.items():
        op.execute(
            sa.text(
                """
                UPDATE workflow_definitions
                SET graph = CAST(:graph AS jsonb), updated_at = NOW()
                WHERE is_template = true AND is_system = true
                  AND workflow_type = 'DEPLOYMENT' AND name = :name
                """
            ).bindparams(name=template_name, graph=graph_json)
        )
