"""
Overview: Update VirtualMachine properties_schema — add allowed_values for OS Type/Version dropdowns,
    remove runtime 'state' property, add allowed_values field to all property defs.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: Semantic type properties should define allowed_values for dropdown fields.
    Runtime state is not a design-time property and does not belong in topology planning.
"""

revision = "054"
down_revision = "053"

import json
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    conn = op.get_bind()

    new_properties = json.dumps([
        {
            "name": "cpu_count",
            "display_name": "CPU Count",
            "data_type": "integer",
            "required": True,
            "default_value": None,
            "unit": "vCPU",
            "description": "",
            "allowed_values": None,
        },
        {
            "name": "memory_gb",
            "display_name": "Memory",
            "data_type": "float",
            "required": True,
            "default_value": None,
            "unit": "GB",
            "description": "",
            "allowed_values": None,
        },
        {
            "name": "storage_gb",
            "display_name": "Storage",
            "data_type": "float",
            "required": False,
            "default_value": None,
            "unit": "GB",
            "description": "",
            "allowed_values": None,
        },
        {
            "name": "os_type",
            "display_name": "OS Type",
            "data_type": "string",
            "required": True,
            "default_value": None,
            "unit": None,
            "description": "",
            "allowed_values": ["Linux", "Windows", "macOS", "BSD", "Other"],
        },
        {
            "name": "os_version",
            "display_name": "OS Version",
            "data_type": "string",
            "required": False,
            "default_value": None,
            "unit": None,
            "description": "",
            "allowed_values": [
                "Ubuntu 22.04",
                "Ubuntu 24.04",
                "Debian 12",
                "RHEL 9",
                "Rocky 9",
                "AlmaLinux 9",
                "CentOS Stream 9",
                "Windows Server 2022",
                "Windows Server 2025",
                "Windows 11",
                "Other",
            ],
        },
        {
            "name": "availability_zone",
            "display_name": "Availability Zone",
            "data_type": "string",
            "required": False,
            "default_value": None,
            "unit": None,
            "description": "",
            "allowed_values": None,
        },
        {
            "name": "public_ip",
            "display_name": "Public IP",
            "data_type": "string",
            "required": False,
            "default_value": None,
            "unit": None,
            "description": "",
            "allowed_values": None,
        },
        {
            "name": "private_ip",
            "display_name": "Private IP",
            "data_type": "string",
            "required": False,
            "default_value": None,
            "unit": None,
            "description": "",
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

    old_properties = json.dumps([
        {"name": "cpu_count", "display_name": "CPU Count", "data_type": "integer",
         "required": True, "default_value": None, "unit": "vCPU", "description": ""},
        {"name": "memory_gb", "display_name": "Memory", "data_type": "float",
         "required": True, "default_value": None, "unit": "GB", "description": ""},
        {"name": "storage_gb", "display_name": "Storage", "data_type": "float",
         "required": False, "default_value": None, "unit": "GB", "description": ""},
        {"name": "os_type", "display_name": "OS Type", "data_type": "string",
         "required": False, "default_value": None, "unit": None,
         "description": "linux, windows, other"},
        {"name": "os_version", "display_name": "OS Version", "data_type": "string",
         "required": False, "default_value": None, "unit": None, "description": ""},
        {"name": "state", "display_name": "State", "data_type": "string",
         "required": True, "default_value": None, "unit": None,
         "description": "running, stopped, suspended"},
        {"name": "availability_zone", "display_name": "Availability Zone", "data_type": "string",
         "required": False, "default_value": None, "unit": None, "description": ""},
        {"name": "public_ip", "display_name": "Public IP", "data_type": "string",
         "required": False, "default_value": None, "unit": None, "description": ""},
        {"name": "private_ip", "display_name": "Private IP", "data_type": "string",
         "required": False, "default_value": None, "unit": None, "description": ""},
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
