"""
Overview: Create deployments table linking topologies to tenant environments.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: Deployment lifecycle, topology-to-environment binding, permission seeding
"""

revision = "061"
down_revision = "060"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


def upgrade() -> None:
    # ── 1. Enum type ──────────────────────────────────────────────────────
    vals = ", ".join(
        f"'{v}'" for v in (
            "PLANNED", "PENDING_APPROVAL", "APPROVED",
            "DEPLOYING", "DEPLOYED", "FAILED", "ROLLED_BACK",
        )
    )
    op.execute(sa.text(f"""
        DO $$ BEGIN
            CREATE TYPE deployment_status AS ENUM ({vals});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$
    """))

    # ── 2. Table ──────────────────────────────────────────────────────────
    op.create_table(
        "deployments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=False),
        sa.Column("topology_id", UUID(as_uuid=True), sa.ForeignKey("architecture_topologies.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", ENUM("PLANNED", "PENDING_APPROVAL", "APPROVED", "DEPLOYING", "DEPLOYED", "FAILED", "ROLLED_BACK", name="deployment_status", create_type=False), nullable=False, server_default="PLANNED"),
        sa.Column("parameters", JSONB, nullable=True),
        sa.Column("deployed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 3. Indexes ────────────────────────────────────────────────────────
    op.create_index("ix_deployments_tenant", "deployments", ["tenant_id"])
    op.create_index("ix_deployments_environment", "deployments", ["environment_id"])
    op.create_index("ix_deployments_tenant_status", "deployments", ["tenant_id", "status"])

    # ── 4. Permissions ────────────────────────────────────────────────────
    conn = op.get_bind()

    permissions = [
        ("deployment", "deployment", "read", "View deployments"),
        ("deployment", "deployment", "create", "Create deployments"),
        ("deployment", "deployment", "update", "Update deployments"),
        ("deployment", "deployment", "delete", "Delete deployments"),
    ]

    for domain, resource, action, description in permissions:
        conn.execute(sa.text("""
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), :domain, :resource, :action, :description, true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """), {"domain": domain, "resource": resource, "action": action, "description": description})

    # ── 5. Role-permission assignments ────────────────────────────────────

    # Provider Admin + Tenant Admin — all 4 permissions
    for role_name in ("Provider Admin", "Tenant Admin"):
        conn.execute(sa.text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r CROSS JOIN permissions p
            WHERE r.name = :role_name
              AND p.domain = 'deployment'
            ON CONFLICT DO NOTHING
        """), {"role_name": role_name})

    # User — read only
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'User'
          AND p.domain = 'deployment'
          AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """))

    # Read-Only — read only
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Read-Only'
          AND p.domain = 'deployment'
          AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Remove role-permission assignments
    conn.execute(sa.text("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'deployment'
        )
    """))

    # Remove permissions
    conn.execute(sa.text("""
        DELETE FROM permissions WHERE domain = 'deployment'
    """))

    op.drop_table("deployments")

    op.execute(sa.text("DROP TYPE IF EXISTS deployment_status"))
