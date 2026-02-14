"""
Overview: Create OS image catalog tables — os_images and os_image_provider_mappings.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: OS image catalog with per-provider mappings, permission seeding, VM properties update.
"""

revision = "055"
down_revision = "054"

import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # -- os_images table --
    op.create_table(
        "os_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("os_family", sa.String(50), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("architecture", sa.String(20), nullable=False, server_default="x86_64"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_os_images_name", "os_images", ["name"], unique=True)

    # -- os_image_provider_mappings table --
    op.create_table(
        "os_image_provider_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("os_image_id", UUID(as_uuid=True), sa.ForeignKey("os_images.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=False),
        sa.Column("image_reference", sa.String(500), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_os_image_provider_mappings_image", "os_image_provider_mappings", ["os_image_id"])
    op.create_index("ix_os_image_provider_mappings_provider", "os_image_provider_mappings", ["provider_id"])
    op.create_index(
        "uq_os_image_provider_active",
        "os_image_provider_mappings",
        ["os_image_id", "provider_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    conn = op.get_bind()

    # -- Seed 10 system OS images --
    images = [
        ("ubuntu-2204", "Ubuntu 22.04 LTS", "linux", "22.04 LTS", "x86_64", "Ubuntu 22.04 Jammy Jellyfish LTS", "ubuntu", 1),
        ("ubuntu-2404", "Ubuntu 24.04 LTS", "linux", "24.04 LTS", "x86_64", "Ubuntu 24.04 Noble Numbat LTS", "ubuntu", 2),
        ("debian-12", "Debian 12", "linux", "12", "x86_64", "Debian 12 Bookworm", "debian", 3),
        ("rhel-9", "RHEL 9", "linux", "9", "x86_64", "Red Hat Enterprise Linux 9", "redhat", 4),
        ("rocky-9", "Rocky Linux 9", "linux", "9", "x86_64", "Rocky Linux 9", "rocky", 5),
        ("almalinux-9", "AlmaLinux 9", "linux", "9", "x86_64", "AlmaLinux 9", "almalinux", 6),
        ("centos-stream-9", "CentOS Stream 9", "linux", "Stream 9", "x86_64", "CentOS Stream 9", "centos", 7),
        ("windows-server-2022", "Windows Server 2022", "windows", "Server 2022", "x86_64", "Windows Server 2022 Datacenter", "windows", 8),
        ("windows-server-2025", "Windows Server 2025", "windows", "Server 2025", "x86_64", "Windows Server 2025 Datacenter", "windows", 9),
        ("windows-11", "Windows 11", "windows", "11", "x86_64", "Windows 11 Enterprise", "windows", 10),
    ]

    for name, display, family, version, arch, desc, icon, order in images:
        conn.execute(
            sa.text("""
                INSERT INTO os_images (id, name, display_name, os_family, version, architecture, description, icon, sort_order, is_system)
                VALUES (gen_random_uuid(), :name, :display_name, :os_family, :version, :architecture, :description, :icon, :sort_order, true)
            """),
            {
                "name": name, "display_name": display, "os_family": family,
                "version": version, "architecture": arch, "description": desc,
                "icon": icon, "sort_order": order,
            },
        )

    # -- Seed permissions --
    conn.execute(
        sa.text("""
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES
                (gen_random_uuid(), 'semantic', 'image', 'read', 'View OS image catalog', true, now(), now()),
                (gen_random_uuid(), 'semantic', 'image', 'manage', 'Create, update, delete OS images and provider mappings', true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """)
    )

    # Grant read to all roles
    conn.execute(
        sa.text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'semantic' AND p.resource = 'image' AND p.action = 'read'
            ON CONFLICT DO NOTHING
        """)
    )

    # Grant manage to Provider Admin and Tenant Admin
    conn.execute(
        sa.text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'semantic' AND p.resource = 'image' AND p.action = 'manage'
              AND r.name IN ('Provider Admin', 'Tenant Admin')
            ON CONFLICT DO NOTHING
        """)
    )

    # -- Update VirtualMachine properties_schema: replace os_type + os_version with os_image --
    new_properties = json.dumps([
        {
            "name": "cpu_count", "display_name": "CPU Count", "data_type": "integer",
            "required": True, "default_value": None, "unit": "vCPU", "description": "",
            "allowed_values": None,
        },
        {
            "name": "memory_gb", "display_name": "Memory", "data_type": "float",
            "required": True, "default_value": None, "unit": "GB", "description": "",
            "allowed_values": None,
        },
        {
            "name": "storage_gb", "display_name": "Storage", "data_type": "float",
            "required": False, "default_value": None, "unit": "GB", "description": "",
            "allowed_values": None,
        },
        {
            "name": "os_image", "display_name": "OS Image", "data_type": "os_image",
            "required": True, "default_value": None, "unit": None,
            "description": "Operating system image from the catalog",
            "allowed_values": None,
        },
        {
            "name": "availability_zone", "display_name": "Availability Zone", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
        {
            "name": "public_ip", "display_name": "Public IP", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
        {
            "name": "private_ip", "display_name": "Private IP", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
    ])

    conn.execute(
        sa.text("""
            UPDATE semantic_resource_types
            SET properties_schema = CAST(:props AS jsonb),
                updated_at = now()
            WHERE name = 'VirtualMachine'
        """),
        {"props": new_properties},
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Restore old VirtualMachine properties_schema with os_type + os_version
    old_properties = json.dumps([
        {
            "name": "cpu_count", "display_name": "CPU Count", "data_type": "integer",
            "required": True, "default_value": None, "unit": "vCPU", "description": "",
            "allowed_values": None,
        },
        {
            "name": "memory_gb", "display_name": "Memory", "data_type": "float",
            "required": True, "default_value": None, "unit": "GB", "description": "",
            "allowed_values": None,
        },
        {
            "name": "storage_gb", "display_name": "Storage", "data_type": "float",
            "required": False, "default_value": None, "unit": "GB", "description": "",
            "allowed_values": None,
        },
        {
            "name": "os_type", "display_name": "OS Type", "data_type": "string",
            "required": True, "default_value": None, "unit": None, "description": "",
            "allowed_values": ["Linux", "Windows", "macOS", "BSD", "Other"],
        },
        {
            "name": "os_version", "display_name": "OS Version", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": [
                "Ubuntu 22.04", "Ubuntu 24.04", "Debian 12", "RHEL 9", "Rocky 9",
                "AlmaLinux 9", "CentOS Stream 9", "Windows Server 2022",
                "Windows Server 2025", "Windows 11", "Other",
            ],
        },
        {
            "name": "availability_zone", "display_name": "Availability Zone", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
        {
            "name": "public_ip", "display_name": "Public IP", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
        {
            "name": "private_ip", "display_name": "Private IP", "data_type": "string",
            "required": False, "default_value": None, "unit": None, "description": "",
            "allowed_values": None,
        },
    ])

    conn.execute(
        sa.text("""
            UPDATE semantic_resource_types
            SET properties_schema = CAST(:props AS jsonb),
                updated_at = now()
            WHERE name = 'VirtualMachine'
        """),
        {"props": old_properties},
    )

    # Remove permissions
    conn.execute(sa.text("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE key IN ('semantic:image:read', 'semantic:image:manage')
        )
    """))
    conn.execute(sa.text("""
        DELETE FROM permissions WHERE key IN ('semantic:image:read', 'semantic:image:manage')
    """))

    op.drop_table("os_image_provider_mappings")
    op.drop_table("os_images")
