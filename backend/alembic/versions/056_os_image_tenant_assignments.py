"""
Overview: Create os_image_tenant_assignments table for tenant-scoped image availability.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: OS images are assigned to specific tenants. No assignment = not visible (except to admins).
"""

revision = "056"
down_revision = "055"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    op.create_table(
        "os_image_tenant_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("os_image_id", UUID(as_uuid=True), sa.ForeignKey("os_images.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("os_image_id", "tenant_id", name="uq_os_image_tenant_assignment"),
    )
    op.create_index("ix_os_image_tenant_assignments_image", "os_image_tenant_assignments", ["os_image_id"])
    op.create_index("ix_os_image_tenant_assignments_tenant", "os_image_tenant_assignments", ["tenant_id"])

    conn = op.get_bind()

    # No seed — images start with no tenant assignments.
    # Admins assign tenants to individual images via the UI.

    # Add semantic:image:assign permission
    conn.execute(
        sa.text("""
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), 'semantic', 'image', 'assign', 'Assign OS images to tenants', true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """)
    )

    # Grant assign to Provider Admin and Tenant Admin
    conn.execute(
        sa.text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'semantic' AND p.resource = 'image' AND p.action = 'assign'
              AND r.name IN ('Provider Admin', 'Tenant Admin')
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'semantic' AND resource = 'image' AND action = 'assign'
        )
    """))
    conn.execute(sa.text("""
        DELETE FROM permissions WHERE domain = 'semantic' AND resource = 'image' AND action = 'assign'
    """))

    op.drop_table("os_image_tenant_assignments")
