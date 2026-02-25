"""
Overview: Event system tables — event_types, event_subscriptions, event_log, event_deliveries.
Architecture: Core data layer for hybrid event bus (Section 11.6)
Dependencies: 086_seed_builtin_activities
Concepts: Event-driven architecture, subscription dispatch, delivery tracking
"""

"""event system tables

Revision ID: 087
Revises: 086
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- event_types -----------------------------------------------------------
    op.create_table(
        "event_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("payload_schema", postgresql.JSONB, nullable=True),
        sa.Column("source_validators", postgresql.JSONB, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- event_subscriptions ---------------------------------------------------
    op.create_table(
        "event_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("event_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_types.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("handler_type", sa.String(20), nullable=False),
        sa.Column("handler_config", postgresql.JSONB, nullable=False),
        sa.Column("filter_expression", sa.Text, nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- event_log -------------------------------------------------------------
    op.create_table(
        "event_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("event_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_types.id"), nullable=False),
        sa.Column("event_type_name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("emitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
    )

    # Composite index for event log queries
    op.create_index(
        "ix_event_log_tenant_type_time",
        "event_log",
        ["tenant_id", "event_type_name", "emitted_at"],
    )

    # -- event_deliveries ------------------------------------------------------
    op.create_table(
        "event_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_log.id"), nullable=False, index=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_subscriptions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("handler_output", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Index for delivery status queries
    op.create_index(
        "ix_event_deliveries_log_status",
        "event_deliveries",
        ["event_log_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_deliveries_log_status", table_name="event_deliveries")
    op.drop_table("event_deliveries")
    op.drop_index("ix_event_log_tenant_type_time", table_name="event_log")
    op.drop_table("event_log")
    op.drop_table("event_subscriptions")
    op.drop_table("event_types")
