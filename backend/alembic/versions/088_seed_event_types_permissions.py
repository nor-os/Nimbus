"""
Overview: Seed system event types and event permissions with role assignments.
Architecture: Data seeding for event system (Section 11.6)
Dependencies: 087_event_system
Concepts: System event types, permission seeding, role assignment
"""

"""seed event types and permissions

Revision ID: 088
Revises: 087
Create Date: 2026-02-17
"""

from alembic import op

revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None

SYSTEM_EVENT_TYPES = [
    ("auth.login.succeeded", "AUTHENTICATION", "User successfully logged in", '["auth_service"]'),
    ("auth.login.failed", "AUTHENTICATION", "Login attempt failed", '["auth_service"]'),
    ("impersonation.requested", "AUTHENTICATION", "Impersonation session requested", '["impersonation_service"]'),
    ("impersonation.activated", "AUTHENTICATION", "Impersonation session activated", '["impersonation_service"]'),
    ("impersonation.ended", "AUTHENTICATION", "Impersonation session ended", '["impersonation_service"]'),
    ("approval.requested", "APPROVAL", "New approval request created", '["approval_service"]'),
    ("approval.decided", "APPROVAL", "Approval step decided", '["approval_service"]'),
    ("approval.expired", "APPROVAL", "Approval request expired", '["approval_service"]'),
    ("approval.cancelled", "APPROVAL", "Approval request cancelled", '["approval_service"]'),
    ("deployment.status_changed", "DEPLOYMENT", "Deployment status changed", '["deployment_service"]'),
    ("deployment.config_changed", "DEPLOYMENT", "Deployment configuration mutated", '["mutation_engine"]'),
    ("environment.status_changed", "ENVIRONMENT", "Environment status changed", '["environment_service"]'),
    ("cmdb.ci.created", "CMDB", "Configuration item created", '["cmdb_service"]'),
    ("cmdb.ci.updated", "CMDB", "Configuration item updated", '["cmdb_service"]'),
    ("cmdb.ci.deleted", "CMDB", "Configuration item deleted", '["cmdb_service"]'),
    ("activity.execution.started", "AUTOMATION", "Activity execution started", '["execution_service"]'),
    ("activity.execution.completed", "AUTOMATION", "Activity execution completed", '["execution_service"]'),
    ("activity.execution.failed", "AUTOMATION", "Activity execution failed", '["execution_service"]'),
    ("activity.version.published", "AUTOMATION", "Activity version published", '["activity_service"]'),
    ("workflow.execution.started", "WORKFLOW", "Workflow execution started", '["workflow_execution_service"]'),
    ("workflow.execution.completed", "WORKFLOW", "Workflow execution completed", '["workflow_execution_service"]'),
    ("workflow.execution.failed", "WORKFLOW", "Workflow execution failed", '["workflow_execution_service"]'),
]

PERMISSIONS = [
    ("events", "type", "read", None, "View event types"),
    ("events", "type", "create", None, "Create custom event types"),
    ("events", "type", "update", None, "Update custom event types"),
    ("events", "type", "delete", None, "Delete custom event types"),
    ("events", "subscription", "read", None, "View event subscriptions"),
    ("events", "subscription", "create", None, "Create event subscriptions"),
    ("events", "subscription", "update", None, "Update event subscriptions"),
    ("events", "subscription", "delete", None, "Delete event subscriptions"),
    ("events", "log", "read", None, "View event log"),
]

# Permission tier assignments
# Provider Admin + Tenant Admin: all permissions
# User: read + subscription:create
# Read-Only: reads only
ADMIN_PERMS = [
    ("events", "type", "read"),
    ("events", "type", "create"),
    ("events", "type", "update"),
    ("events", "type", "delete"),
    ("events", "subscription", "read"),
    ("events", "subscription", "create"),
    ("events", "subscription", "update"),
    ("events", "subscription", "delete"),
    ("events", "log", "read"),
]

USER_PERMS = [
    ("events", "type", "read"),
    ("events", "subscription", "read"),
    ("events", "subscription", "create"),
    ("events", "log", "read"),
]

READONLY_PERMS = [
    ("events", "type", "read"),
    ("events", "subscription", "read"),
    ("events", "log", "read"),
]


def upgrade() -> None:
    # 1. Seed system event types
    for name, category, description, source_validators in SYSTEM_EVENT_TYPES:
        op.execute(f"""
            INSERT INTO event_types (id, tenant_id, name, description, category, source_validators, is_system, is_active)
            VALUES (gen_random_uuid(), NULL, '{name}', '{description}', '{category}', '{source_validators}'::jsonb, true, true)
            ON CONFLICT (name) DO NOTHING
        """)

    # 2. Seed permissions
    for domain, resource, action, subtype, description in PERMISSIONS:
        sub_clause = f"'{subtype}'" if subtype else "NULL"
        op.execute(f"""
            INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system)
            VALUES (gen_random_uuid(), '{domain}', '{resource}', '{action}', {sub_clause}, '{description}', true)
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """)

    # 3. Assign permissions to roles
    # Provider Admin + Tenant Admin
    for domain, resource, action in ADMIN_PERMS:
        op.execute(f"""
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT gen_random_uuid(), r.id, p.id
            FROM roles r, permissions p
            WHERE r.name IN ('Provider Admin', 'Tenant Admin')
              AND p.domain = '{domain}' AND p.resource = '{resource}' AND p.action = '{action}'
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
        """)

    # User role
    for domain, resource, action in USER_PERMS:
        op.execute(f"""
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT gen_random_uuid(), r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'User'
              AND p.domain = '{domain}' AND p.resource = '{resource}' AND p.action = '{action}'
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
        """)

    # Read-Only role
    for domain, resource, action in READONLY_PERMS:
        op.execute(f"""
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT gen_random_uuid(), r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'Read-Only'
              AND p.domain = '{domain}' AND p.resource = '{resource}' AND p.action = '{action}'
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
        """)


def downgrade() -> None:
    # Remove role_permissions for event permissions
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'events'
        )
    """)
    # Remove permissions
    op.execute("DELETE FROM permissions WHERE domain = 'events'")
    # Remove event types
    op.execute("DELETE FROM event_types WHERE is_system = true")
