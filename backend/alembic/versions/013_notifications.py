"""Add notifications, notification_preferences, notification_templates, webhook_configs,
webhook_deliveries tables and notification permissions.

Revision ID: 013
Revises: 012
Create Date: 2026-02-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOTIFICATION_PERMISSIONS = [
    ("notification:notification:read", "View notifications"),
    ("notification:preference:manage", "Manage notification preferences"),
    ("notification:template:read", "View notification templates"),
    ("notification:template:manage", "Manage notification templates"),
    ("notification:webhook:read", "View webhook configurations"),
    ("notification:webhook:manage", "Manage webhook configurations"),
]


def upgrade() -> None:
    # -- Enums (created via raw SQL to avoid SQLAlchemy auto-create conflicts) --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE notification_category AS ENUM "
        "('APPROVAL','SECURITY','SYSTEM','AUDIT','DRIFT','WORKFLOW','USER'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE notification_channel AS ENUM ('EMAIL','IN_APP','WEBHOOK'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE webhook_auth_type AS ENUM ('NONE','API_KEY','BASIC','BEARER'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE webhook_delivery_status AS ENUM "
        "('PENDING','DELIVERED','FAILED','DEAD_LETTER'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    notification_category = postgresql.ENUM(
        "APPROVAL", "SECURITY", "SYSTEM", "AUDIT", "DRIFT", "WORKFLOW", "USER",
        name="notification_category",
        create_type=False,
    )
    notification_channel = postgresql.ENUM(
        "EMAIL", "IN_APP", "WEBHOOK",
        name="notification_channel",
        create_type=False,
    )
    webhook_auth_type = postgresql.ENUM(
        "NONE", "API_KEY", "BASIC", "BEARER",
        name="webhook_auth_type",
        create_type=False,
    )
    webhook_delivery_status = postgresql.ENUM(
        "PENDING", "DELIVERED", "FAILED", "DEAD_LETTER",
        name="webhook_delivery_status",
        create_type=False,
    )

    # -- 1. notifications table ------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("category", notification_category, nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("related_resource_type", sa.String(255), nullable=True),
        sa.Column("related_resource_id", sa.String(255), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index("ix_notifications_tenant_user", "notifications", ["tenant_id", "user_id"])
    op.create_index("ix_notifications_category", "notifications", ["category"])
    op.create_index(
        "ix_notifications_is_read", "notifications", ["tenant_id", "user_id", "is_read"]
    )
    op.create_index("ix_notifications_created", "notifications", ["tenant_id", "created_at"])

    # -- 2. notification_preferences table -------------------------------------
    op.create_table(
        "notification_preferences",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("category", notification_category, nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
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
            "tenant_id", "user_id", "category", "channel",
            name="uq_notification_pref_user_cat_chan",
        ),
    )

    # -- 3. notification_templates table ---------------------------------------
    op.create_table(
        "notification_templates",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
        sa.Column("category", notification_category, nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("subject_template", sa.String(1000), nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_notification_templates_unique_active "
        "ON notification_templates (tenant_id, category, event_type, channel) "
        "WHERE deleted_at IS NULL"
    )

    # -- 4. webhook_configs table ----------------------------------------------
    op.create_table(
        "webhook_configs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("auth_type", webhook_auth_type, nullable=False, server_default="NONE"),
        sa.Column("auth_config", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("event_filter", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("batch_size", sa.Integer, nullable=False, server_default="1"),
        sa.Column("batch_interval_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("secret", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    )
    op.create_index("ix_webhook_configs_tenant", "webhook_configs", ["tenant_id"])
    op.create_index("ix_webhook_configs_active", "webhook_configs", ["tenant_id", "is_active"])

    # -- 5. webhook_deliveries table -------------------------------------------
    op.create_table(
        "webhook_deliveries",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "webhook_config_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("webhook_configs.id"),
            nullable=False,
        ),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "status", webhook_delivery_status, nullable=False, server_default="PENDING"
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="5"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index("ix_webhook_deliveries_config", "webhook_deliveries", ["webhook_config_id"])
    op.create_index(
        "ix_webhook_deliveries_status", "webhook_deliveries", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_webhook_deliveries_next_retry", "webhook_deliveries", ["status", "next_retry_at"]
    )

    # -- 6. Seed notification permissions and assign to tenant_admin -----------
    conn = op.get_bind()
    for key, description in NOTIFICATION_PERMISSIONS:
        parts = key.split(":")
        domain = parts[0]
        resource = parts[1]
        action = parts[2]
        subtype = parts[3] if len(parts) > 3 else None

        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, domain, resource, action, subtype, description,
                                         is_system, created_at, updated_at)
                VALUES (gen_random_uuid(), :domain, :resource, :action, :subtype,
                        :description, true, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
                """
            ),
            {
                "domain": domain,
                "resource": resource,
                "action": action,
                "subtype": subtype,
                "description": description,
            },
        )

    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'notification'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove notification role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'notification'
            )
            """
        )
    )

    # Remove notification permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'notification'"))

    # Drop tables in reverse dependency order
    op.drop_index("ix_webhook_deliveries_next_retry", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_config", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("ix_webhook_configs_active", table_name="webhook_configs")
    op.drop_index("ix_webhook_configs_tenant", table_name="webhook_configs")
    op.drop_table("webhook_configs")

    op.execute("DROP INDEX IF EXISTS ix_notification_templates_unique_active")
    op.drop_table("notification_templates")

    op.drop_table("notification_preferences")

    op.drop_index("ix_notifications_created", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_category", table_name="notifications")
    op.drop_index("ix_notifications_tenant_user", table_name="notifications")
    op.drop_table("notifications")

    # Drop enums
    sa.Enum(name="webhook_delivery_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="webhook_auth_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_channel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_category").drop(op.get_bind(), checkfirst=True)
