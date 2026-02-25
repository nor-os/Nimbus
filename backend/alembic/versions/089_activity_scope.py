"""
Overview: Add activity_scope column to automated_activities, reclassify existing activities,
    and seed workflow builtin activities.
Architecture: Migration (Section 11.5)
Dependencies: alembic, sqlalchemy
Concepts: Activity scope categorization (COMPONENT vs WORKFLOW), builtin workflow activities
"""

revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # 1. Add scope column with default WORKFLOW
    op.add_column(
        "automated_activities",
        sa.Column("scope", sa.String(20), nullable=False, server_default="WORKFLOW"),
    )
    op.create_index("ix_automated_activities_scope", "automated_activities", ["scope"])

    # 2. Reclassify existing activities: infrastructure day-2 ops → COMPONENT
    component_slugs = [
        "disk-resize",
        "create-snapshot",
        "restore-snapshot",
        "run-backup",
        "apply-patch",
        "scale-resource",
        "rotate-credentials",
        "restart-service",
    ]
    op.execute(
        sa.text(
            "UPDATE automated_activities SET scope = 'COMPONENT' "
            "WHERE slug = ANY(:slugs) AND is_system = true"
        ).bindparams(slugs=component_slugs)
    )
    # validate-connectivity and export-config remain WORKFLOW (the default)

    # 3. Seed new workflow builtin activities
    now = datetime.now(timezone.utc).isoformat()
    activities = [
        {
            "name": "Send Email",
            "slug": "send-email",
            "description": "Send an email notification via configured SMTP or webhook endpoint.",
            "category": "notification",
            "operation_kind": "UPDATE",
            "implementation_type": "HTTP_WEBHOOK",
            "idempotent": True,
            "timeout_seconds": 30,
            "source_code": None,
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (HTML or plain text)"},
                    "cc": {"type": "string", "description": "CC addresses (comma-separated)"},
                },
                "required": ["to", "subject", "body"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            "runtime_config": '{"webhook_url": "", "headers": {"Content-Type": "application/json"}}',
        },
        {
            "name": "Send Notification",
            "slug": "send-notification",
            "description": "Send an in-app notification via the Nimbus notification system.",
            "category": "notification",
            "operation_kind": "UPDATE",
            "implementation_type": "PYTHON_SCRIPT",
            "idempotent": True,
            "timeout_seconds": 30,
            "source_code": (
                "import json, sys\n"
                "input_data = json.load(sys.stdin)\n"
                "# Dispatched internally via NotificationService\n"
                "json.dump({'status': 'dispatched', 'channel': input_data.get('channel', 'in_app')}, sys.stdout)\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Target user ID"},
                    "title": {"type": "string", "description": "Notification title"},
                    "message": {"type": "string", "description": "Notification body"},
                    "channel": {"type": "string", "description": "Channel: in_app, email, webhook"},
                    "severity": {"type": "string", "description": "Severity: info, warning, error, critical"},
                },
                "required": ["user_id", "title", "message"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "channel": {"type": "string"},
                },
            },
            "runtime_config": None,
        },
        {
            "name": "HTTP Request",
            "slug": "http-request",
            "description": "Make a generic HTTP request to an external endpoint.",
            "category": "integration",
            "operation_kind": "UPDATE",
            "implementation_type": "HTTP_WEBHOOK",
            "idempotent": False,
            "timeout_seconds": 60,
            "source_code": None,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target URL"},
                    "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)"},
                    "headers": {"type": "object", "description": "Request headers"},
                    "body": {"type": "object", "description": "Request body (JSON)"},
                },
                "required": ["url"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "status_code": {"type": "integer"},
                    "body": {"type": "object"},
                    "headers": {"type": "object"},
                },
            },
            "runtime_config": '{"webhook_url": "", "headers": {}}',
        },
        {
            "name": "Log Audit Entry",
            "slug": "log-audit-entry",
            "description": "Write a custom entry to the audit log.",
            "category": "observability",
            "operation_kind": "UPDATE",
            "implementation_type": "PYTHON_SCRIPT",
            "idempotent": True,
            "timeout_seconds": 15,
            "source_code": (
                "import json, sys\n"
                "input_data = json.load(sys.stdin)\n"
                "# Dispatched internally via AuditService\n"
                "json.dump({'status': 'logged', 'action': input_data.get('action', 'custom')}, sys.stdout)\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Action name"},
                    "resource_type": {"type": "string", "description": "Resource type"},
                    "resource_id": {"type": "string", "description": "Resource ID"},
                    "details": {"type": "object", "description": "Additional details"},
                    "severity": {"type": "string", "description": "Severity: info, warning, error"},
                },
                "required": ["action"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "action": {"type": "string"},
                },
            },
            "runtime_config": None,
        },
    ]

    import json

    for act in activities:
        activity_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())

        op.execute(
            sa.text(
                "INSERT INTO automated_activities "
                "(id, tenant_id, name, slug, description, category, "
                "operation_kind, implementation_type, idempotent, timeout_seconds, "
                "scope, is_system, created_at, updated_at) "
                "VALUES (CAST(:id AS uuid), NULL, :name, :slug, :description, :category, "
                ":operation_kind, :implementation_type, :idempotent, :timeout_seconds, "
                "'WORKFLOW', true, CAST(:now AS timestamptz), CAST(:now AS timestamptz))"
            ).bindparams(
                id=activity_id,
                name=act["name"],
                slug=act["slug"],
                description=act["description"],
                category=act["category"],
                operation_kind=act["operation_kind"],
                implementation_type=act["implementation_type"],
                idempotent=act["idempotent"],
                timeout_seconds=act["timeout_seconds"],
                now=now,
            )
        )

        op.execute(
            sa.text(
                "INSERT INTO automated_activity_versions "
                "(id, activity_id, version, source_code, input_schema, output_schema, "
                "config_mutations, rollback_mutations, changelog, published_at, runtime_config, "
                "created_at, updated_at) "
                "VALUES (CAST(:id AS uuid), CAST(:activity_id AS uuid), 1, :source_code, "
                "CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), "
                "NULL, NULL, 'Initial version', CAST(:now AS timestamptz), "
                "CAST(:runtime_config AS jsonb), CAST(:now AS timestamptz), CAST(:now AS timestamptz))"
            ).bindparams(
                id=version_id,
                activity_id=activity_id,
                source_code=act["source_code"],
                input_schema=json.dumps(act["input_schema"]),
                output_schema=json.dumps(act["output_schema"]),
                runtime_config=act["runtime_config"],
                now=now,
            )
        )


def downgrade() -> None:
    # Remove seeded workflow builtins
    op.execute(
        sa.text(
            "DELETE FROM automated_activity_versions WHERE activity_id IN "
            "(SELECT id FROM automated_activities WHERE slug IN "
            "('send-email', 'send-notification', 'http-request', 'log-audit-entry') "
            "AND is_system = true)"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM automated_activities WHERE slug IN "
            "('send-email', 'send-notification', 'http-request', 'log-audit-entry') "
            "AND is_system = true"
        )
    )

    # Reset all to default (no scope distinction)
    op.execute(sa.text("UPDATE automated_activities SET scope = 'WORKFLOW'"))

    op.drop_index("ix_automated_activities_scope", table_name="automated_activities")
    op.drop_column("automated_activities", "scope")
