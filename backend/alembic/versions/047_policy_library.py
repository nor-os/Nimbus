"""
Overview: Add policy_library table, policy permissions, and seed system policy templates.
Architecture: Database migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Policy library for reusable IAM policy definitions, seeded system policies
"""

"""Add policy_library table and policy permissions.

Revision ID: 047
Revises: 046
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "047"
down_revision: Union[str, None] = "046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_PERMISSIONS = [
    ("policy:library:read", "View policy library entries"),
    ("policy:library:manage", "Manage policy library entries"),
    ("policy:resolution:read", "View resolved compartment policies"),
]

# policy:library:read + policy:resolution:read → all roles
ALL_ROLE_PERMISSIONS = [
    "policy:library:read",
    "policy:resolution:read",
]

# policy:library:manage → admin roles only
ADMIN_PERMISSIONS = [
    "policy:library:manage",
]

SYSTEM_POLICIES = [
    {
        "name": "require-encryption",
        "display_name": "Require Encryption at Rest",
        "description": "Deny creation of storage resources without encryption enabled.",
        "category": "ENCRYPTION",
        "severity": "HIGH",
        "statements": [
            {
                "sid": "deny-unencrypted-storage",
                "effect": "deny",
                "actions": ["storage:create"],
                "resources": ["BlockStorage", "ObjectStorage"],
                "principals": ["*"],
                "condition": "resource.encryption_enabled == false",
            }
        ],
        "variables": None,
        "tags": ["security", "compliance", "encryption"],
    },
    {
        "name": "deny-wildcard-actions",
        "display_name": "Deny Wildcard Action Grants",
        "description": "Prevent granting wildcard (*:*) action permissions to any principal.",
        "category": "IAM",
        "severity": "CRITICAL",
        "statements": [
            {
                "sid": "deny-wildcard-iam",
                "effect": "deny",
                "actions": ["*:*"],
                "resources": ["*"],
                "principals": ["*"],
                "condition": None,
            }
        ],
        "variables": None,
        "tags": ["security", "iam", "least-privilege"],
    },
    {
        "name": "require-resource-tagging",
        "display_name": "Require Resource Tagging",
        "description": "Deny resource creation without required tags (environment, owner).",
        "category": "TAGGING",
        "severity": "MEDIUM",
        "statements": [
            {
                "sid": "deny-untagged-resources",
                "effect": "deny",
                "actions": ["compute:create", "storage:create", "network:create"],
                "resources": ["*"],
                "principals": ["*"],
                "condition": "resource.tags.environment == null or resource.tags.owner == null",
            }
        ],
        "variables": {
            "required_tags": {
                "type": "array",
                "default": ["environment", "owner"],
                "description": "Tag keys that must be present on all resources",
            }
        },
        "tags": ["governance", "tagging", "compliance"],
    },
]


def upgrade() -> None:
    # -- Enums --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE policy_category AS ENUM ('IAM','NETWORK','ENCRYPTION','TAGGING','COST'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE policy_severity AS ENUM ('CRITICAL','HIGH','MEDIUM','LOW','INFO'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    policy_category = postgresql.ENUM(
        "IAM", "NETWORK", "ENCRYPTION", "TAGGING", "COST",
        name="policy_category",
        create_type=False,
    )
    policy_severity = postgresql.ENUM(
        "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO",
        name="policy_severity",
        create_type=False,
    )

    # -- policy_library table --
    op.create_table(
        "policy_library",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", policy_category, nullable=False),
        sa.Column("statements", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("variables", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column(
            "severity", policy_severity,
            nullable=False, server_default="MEDIUM",
        ),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "name",
            name="uq_policy_library_tenant_name",
        ),
    )
    op.create_index(
        "ix_policy_library_tenant", "policy_library", ["tenant_id"]
    )
    op.create_index(
        "ix_policy_library_category", "policy_library",
        ["tenant_id", "category"],
    )
    op.create_index(
        "ix_policy_library_created_by", "policy_library", ["created_by"]
    )

    # -- Seed policy permissions --
    conn = op.get_bind()
    for key, description in POLICY_PERMISSIONS:
        parts = key.split(":")
        domain = parts[0]
        resource = parts[1]
        action = parts[2]

        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, domain, resource, action, subtype, description,
                                         is_system, created_at, updated_at)
                VALUES (gen_random_uuid(), :domain, :resource, :action, NULL,
                        :description, true, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
                """
            ),
            {
                "domain": domain,
                "resource": resource,
                "action": action,
                "description": description,
            },
        )

    # Provider Admin & Tenant Admin get all policy permissions
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'policy'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )

    # User + Read-Only roles: library:read + resolution:read
    for perm_key in ALL_ROLE_PERMISSIONS:
        parts = perm_key.split(":")
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r
                CROSS JOIN permissions p
                WHERE r.name IN ('User', 'Read-Only')
                  AND p.domain = :domain AND p.resource = :resource AND p.action = :action
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissions rp
                      WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  )
                """
            ),
            {"domain": parts[0], "resource": parts[1], "action": parts[2]},
        )

    # -- Seed 3 system policy templates --
    # Use a system UUID for created_by (all-zeros)
    system_user_id = "00000000-0000-0000-0000-000000000000"
    for policy in SYSTEM_POLICIES:
        import json

        conn.execute(
            sa.text(
                """
                INSERT INTO policy_library (
                    id, tenant_id, name, display_name, description,
                    category, statements, variables, severity,
                    is_system, tags, created_by, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), NULL, :name, :display_name, :description,
                    :category, CAST(:statements AS jsonb), CAST(:variables AS jsonb), :severity,
                    true, :tags, :created_by, now(), now()
                )
                ON CONFLICT ON CONSTRAINT uq_policy_library_tenant_name DO NOTHING
                """
            ),
            {
                "name": policy["name"],
                "display_name": policy["display_name"],
                "description": policy["description"],
                "category": policy["category"],
                "statements": json.dumps(policy["statements"]),
                "variables": json.dumps(policy["variables"]) if policy["variables"] else None,
                "severity": policy["severity"],
                "tags": policy["tags"],
                "created_by": system_user_id,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove policy role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'policy'
            )
            """
        )
    )

    # Remove policy permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'policy'"))

    # Drop indexes and table
    op.drop_index("ix_policy_library_created_by", table_name="policy_library")
    op.drop_index("ix_policy_library_category", table_name="policy_library")
    op.drop_index("ix_policy_library_tenant", table_name="policy_library")
    op.drop_table("policy_library")

    # Drop enums
    sa.Enum(name="policy_severity").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="policy_category").drop(op.get_bind(), checkfirst=True)
