"""Add event taxonomy columns (event_category, event_type, actor_type) and request context fields.

Revision ID: 011
Revises: 010
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mapping from old action enum values -> (event_type, event_category)
ACTION_MIGRATION_MAP = {
    "CREATE": ("data.create", "DATA"),
    "READ": ("data.read", "DATA"),
    "UPDATE": ("data.update", "DATA"),
    "DELETE": ("data.delete", "DATA"),
    "LOGIN": ("auth.login", "AUTH"),
    "LOGOUT": ("auth.logout", "AUTH"),
    "PERMISSION_CHANGE": ("permission.role.assign", "PERMISSION"),
    "BREAK_GLASS": ("security.breakglass.activate", "SECURITY"),
    "EXPORT": ("data.export", "DATA"),
    "ARCHIVE": ("data.archive", "DATA"),
    "SYSTEM": ("system.config.update", "SYSTEM"),
    # IMPERSONATE and OVERRIDE are excluded: they were added to the audit_action
    # enum in migration 010 and can't be referenced until that transaction commits.
    # No rows with those actions can exist yet on a fresh database.
}

BATCH_SIZE = 10000


def upgrade() -> None:
    # 1. Create new enum types
    audit_event_category = sa.Enum(
        "API", "AUTH", "DATA", "PERMISSION", "SYSTEM", "SECURITY", "TENANT", "USER",
        name="audit_event_category",
    )
    audit_event_category.create(op.get_bind(), checkfirst=True)

    audit_actor_type = sa.Enum(
        "USER", "SYSTEM", "SERVICE", "ANONYMOUS",
        name="audit_actor_type",
    )
    audit_actor_type.create(op.get_bind(), checkfirst=True)

    # 2. Add DEBUG and CRITICAL to existing audit_priority enum
    op.execute("ALTER TYPE audit_priority ADD VALUE IF NOT EXISTS 'DEBUG' BEFORE 'INFO'")
    op.execute("ALTER TYPE audit_priority ADD VALUE IF NOT EXISTS 'CRITICAL' AFTER 'ERR'")

    # 3. Add new columns (nullable initially for backfill)
    op.add_column("audit_logs", sa.Column(
        "event_category",
        sa.Enum("API", "AUTH", "DATA", "PERMISSION", "SYSTEM", "SECURITY", "TENANT", "USER",
                name="audit_event_category", create_type=False),
        nullable=True,
    ))
    op.add_column("audit_logs", sa.Column("event_type", sa.String(255), nullable=True))
    op.add_column("audit_logs", sa.Column(
        "actor_type",
        sa.Enum("USER", "SYSTEM", "SERVICE", "ANONYMOUS",
                name="audit_actor_type", create_type=False),
        nullable=True,
    ))
    op.add_column("audit_logs", sa.Column("impersonator_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column("audit_logs", sa.Column("request_method", sa.String(10), nullable=True))
    op.add_column("audit_logs", sa.Column("request_path", sa.String(2048), nullable=True))
    op.add_column("audit_logs", sa.Column("request_body", sa.dialects.postgresql.JSONB, nullable=True))
    op.add_column("audit_logs", sa.Column("response_status", sa.Integer, nullable=True))
    op.add_column("audit_logs", sa.Column("response_body", sa.dialects.postgresql.JSONB, nullable=True))
    op.add_column("audit_logs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))

    # 4. Backfill in batches
    conn = op.get_bind()

    # Build CASE expression for event_type
    event_type_cases = " ".join(
        f"WHEN action = '{action}' THEN '{et}'"
        for action, (et, _) in ACTION_MIGRATION_MAP.items()
    )
    event_category_cases = " ".join(
        f"WHEN action = '{action}' THEN '{cat}'::audit_event_category"
        for action, (_, cat) in ACTION_MIGRATION_MAP.items()
    )

    # Special handling: rows with resource_type='http_request' are API requests
    conn.execute(sa.text(f"""
        UPDATE audit_logs
        SET
            event_type = 'api.request',
            event_category = 'API'::audit_event_category,
            actor_type = CASE
                WHEN actor_id IS NOT NULL THEN 'USER'::audit_actor_type
                ELSE 'ANONYMOUS'::audit_actor_type
            END
        WHERE resource_type = 'http_request' AND event_type IS NULL
    """))

    # Backfill remaining rows using action -> event_type/category mapping
    conn.execute(sa.text(f"""
        UPDATE audit_logs
        SET
            event_type = CASE {event_type_cases} ELSE 'data.create' END,
            event_category = CASE {event_category_cases} ELSE 'DATA'::audit_event_category END,
            actor_type = CASE
                WHEN actor_id IS NOT NULL THEN 'USER'::audit_actor_type
                ELSE 'SYSTEM'::audit_actor_type
            END
        WHERE event_type IS NULL
    """))

    # 5. Create indexes
    op.create_index("ix_audit_logs_event_category", "audit_logs", ["event_category"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_actor_type", "audit_logs", ["actor_type"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_audit_logs_actor_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_category", table_name="audit_logs")

    # Drop columns
    op.drop_column("audit_logs", "archived_at")
    op.drop_column("audit_logs", "response_body")
    op.drop_column("audit_logs", "response_status")
    op.drop_column("audit_logs", "request_body")
    op.drop_column("audit_logs", "request_path")
    op.drop_column("audit_logs", "request_method")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "impersonator_id")
    op.drop_column("audit_logs", "actor_type")
    op.drop_column("audit_logs", "event_type")
    op.drop_column("audit_logs", "event_category")

    # Drop enum types
    sa.Enum(name="audit_actor_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audit_event_category").drop(op.get_bind(), checkfirst=True)

    # Note: DEBUG and CRITICAL values cannot be easily removed from audit_priority enum
