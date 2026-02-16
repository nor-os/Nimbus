"""
Overview: Seed example day-2 operations for the Proxmox VM component.
Architecture: Migration for component operations (Section 11)
Dependencies: 067_component_operations
Concepts: Creates workflow definitions and component operations for extend_disk, create_snapshot,
    and restart on the pve-vm-basic component.
"""

revision = "068"
down_revision = "067"

from alembic import op
import sqlalchemy as sa


EXTEND_DISK_INPUT = """{
  "type": "object",
  "properties": {
    "new_size_gb": {
      "type": "integer",
      "description": "New total disk size in GB (must be larger than current)"
    },
    "extend_filesystem": {
      "type": "boolean",
      "description": "Automatically extend the filesystem after resizing the block device",
      "default": true
    },
    "disk_interface": {
      "type": "string",
      "description": "Disk interface to resize",
      "default": "scsi0"
    }
  },
  "required": ["new_size_gb"]
}"""

EXTEND_DISK_OUTPUT = """{
  "type": "object",
  "properties": {
    "old_size_gb": { "type": "integer", "description": "Previous disk size" },
    "new_size_gb": { "type": "integer", "description": "New disk size" },
    "filesystem_extended": { "type": "boolean", "description": "Whether filesystem was extended" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

SNAPSHOT_INPUT = """{
  "type": "object",
  "properties": {
    "snapshot_name": {
      "type": "string",
      "description": "Name for the snapshot"
    },
    "description": {
      "type": "string",
      "description": "Snapshot description"
    },
    "include_ram": {
      "type": "boolean",
      "description": "Include VM RAM state in snapshot",
      "default": false
    }
  },
  "required": ["snapshot_name"]
}"""

SNAPSHOT_OUTPUT = """{
  "type": "object",
  "properties": {
    "snapshot_id": { "type": "string", "description": "Snapshot identifier" },
    "snapshot_name": { "type": "string", "description": "Snapshot name" },
    "created_at": { "type": "string", "description": "Snapshot creation timestamp" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

RESTART_INPUT = """{
  "type": "object",
  "properties": {
    "force": {
      "type": "boolean",
      "description": "Force restart (hard reset) if graceful shutdown fails",
      "default": false
    },
    "timeout_seconds": {
      "type": "integer",
      "description": "Seconds to wait for graceful shutdown before force restart",
      "default": 120
    }
  }
}"""

RESTART_OUTPUT = """{
  "type": "object",
  "properties": {
    "previous_state": { "type": "string", "description": "VM state before restart" },
    "current_state": { "type": "string", "description": "VM state after restart" },
    "restart_method": { "type": "string", "description": "graceful or forced" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""


# Workflow definition graph templates (DAGs using real node types with proper ports)
EXTEND_DISK_GRAPH = """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "resize_block", "type": "cloud_api", "label": "Resize Block Device", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "PUT",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/resize",
       "body": "{\\"disk\\": \\"${$input.disk_interface}\\", \\"size\\": \\"${$input.new_size_gb}G\\"}"
     }},
    {"id": "wait_resize", "type": "delay", "label": "Wait for Resize", "position": {"x": 400, "y": 0},
     "config": {"seconds": 5}},
    {"id": "extend_fs", "type": "ssh_exec", "label": "Extend Filesystem", "position": {"x": 600, "y": 0},
     "config": {
       "host": "${$input.vm_ip}",
       "username": "${$input.ssh_user}",
       "private_key_secret_id": "${$input.ssh_key_backend_id}",
       "command": "growpart /dev/sda 1 && resize2fs /dev/sda1"
     }},
    {"id": "verify", "type": "ssh_exec", "label": "Verify Size", "position": {"x": 800, "y": 0},
     "config": {
       "host": "${$input.vm_ip}",
       "username": "${$input.ssh_user}",
       "private_key_secret_id": "${$input.ssh_key_backend_id}",
       "command": "df -h / --output=size | tail -1"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1000, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "resize_block", "sourcePort": "out", "targetPort": "in"},
    {"source": "resize_block", "target": "wait_resize", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_resize", "target": "extend_fs", "sourcePort": "out", "targetPort": "in"},
    {"source": "extend_fs", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}"""

SNAPSHOT_GRAPH = """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "create_snap", "type": "cloud_api", "label": "Create Snapshot", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/snapshot",
       "body": "{\\"snapname\\": \\"${$input.snapshot_name}\\", \\"description\\": \\"${$input.description}\\", \\"vmstate\\": ${$input.include_ram}}"
     }},
    {"id": "verify", "type": "cloud_api", "label": "Verify Snapshot", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/snapshot"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "create_snap", "sourcePort": "out", "targetPort": "in"},
    {"source": "create_snap", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}"""

RESTART_GRAPH = """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "shutdown", "type": "cloud_api", "label": "Graceful Shutdown", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/status/shutdown"
     }},
    {"id": "wait_down", "type": "delay", "label": "Wait for Shutdown", "position": {"x": 400, "y": 0},
     "config": {"seconds": 5}},
    {"id": "boot", "type": "cloud_api", "label": "Start VM", "position": {"x": 600, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/status/start"
     }},
    {"id": "verify", "type": "cloud_api", "label": "Verify Running", "position": {"x": 800, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/api2/json/nodes/${$input.node}/qemu/${$input.vmid}/status/current"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1000, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "shutdown", "sourcePort": "out", "targetPort": "in"},
    {"source": "shutdown", "target": "wait_down", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_down", "target": "boot", "sourcePort": "out", "targetPort": "in"},
    {"source": "boot", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}"""


def upgrade():
    conn = op.get_bind()

    # Find Proxmox VM component
    pve = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1")
    ).fetchone()
    if not pve:
        return

    # Find a user for created_by and a tenant for workflow defs
    user = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not user:
        return

    # Use first tenant for workflow definitions (operations workflows are templates)
    tenant = conn.execute(
        sa.text("SELECT id FROM tenants ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not tenant:
        return

    operations = [
        {
            "op_name": "extend_disk",
            "op_display": "Extend Disk",
            "op_desc": "Resize a virtual disk and optionally extend the filesystem. "
                       "First extends the block device on the hypervisor, then SSHes into the VM to grow the partition and filesystem.",
            "op_input": EXTEND_DISK_INPUT,
            "op_output": EXTEND_DISK_OUTPUT,
            "op_destructive": False,
            "op_approval": True,
            "op_downtime": "BRIEF",
            "op_order": 1,
            "wf_name": "PVE VM: Extend Disk",
            "wf_desc": "Multi-step workflow: resize Proxmox block device → extend guest filesystem",
            "wf_graph": EXTEND_DISK_GRAPH,
        },
        {
            "op_name": "create_snapshot",
            "op_display": "Create Snapshot",
            "op_desc": "Create a point-in-time snapshot of the virtual machine, optionally including RAM state.",
            "op_input": SNAPSHOT_INPUT,
            "op_output": SNAPSHOT_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "NONE",
            "op_order": 2,
            "wf_name": "PVE VM: Create Snapshot",
            "wf_desc": "Create and verify a Proxmox VM snapshot",
            "wf_graph": SNAPSHOT_GRAPH,
        },
        {
            "op_name": "restart",
            "op_display": "Restart VM",
            "op_desc": "Gracefully restart the virtual machine. Sends ACPI shutdown, waits, then boots.",
            "op_input": RESTART_INPUT,
            "op_output": RESTART_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "BRIEF",
            "op_order": 3,
            "wf_name": "PVE VM: Restart",
            "wf_desc": "Graceful shutdown → boot → verify running",
            "wf_graph": RESTART_GRAPH,
        },
    ]

    for op_def in operations:
        # Create workflow definition
        conn.execute(sa.text("""
            INSERT INTO workflow_definitions (
                id, tenant_id, name, description, workflow_type,
                graph, status, version,
                created_by, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :tenant_id, :name, :desc, 'AUTOMATION',
                CAST(:graph AS jsonb), 'ACTIVE', 1,
                :user_id, NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
        """), {
            "tenant_id": str(tenant[0]),
            "name": op_def["wf_name"],
            "desc": op_def["wf_desc"],
            "graph": op_def["wf_graph"],
            "user_id": str(user[0]),
        })

        # Look up the workflow we just created
        wf = conn.execute(
            sa.text("SELECT id FROM workflow_definitions WHERE name = :name LIMIT 1"),
            {"name": op_def["wf_name"]},
        ).fetchone()
        if not wf:
            continue

        # Create the component operation
        conn.execute(sa.text("""
            INSERT INTO component_operations (
                id, component_id, name, display_name, description,
                input_schema, output_schema, workflow_definition_id,
                is_destructive, requires_approval, estimated_downtime,
                sort_order, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :comp_id, :name, :display_name, :description,
                CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), :wf_id,
                :is_destructive, :requires_approval, :downtime,
                :sort_order, NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
        """), {
            "comp_id": str(pve[0]),
            "name": op_def["op_name"],
            "display_name": op_def["op_display"],
            "description": op_def["op_desc"],
            "input_schema": op_def["op_input"],
            "output_schema": op_def["op_output"],
            "wf_id": str(wf[0]),
            "is_destructive": op_def["op_destructive"],
            "requires_approval": op_def["op_approval"],
            "downtime": op_def["op_downtime"],
            "sort_order": op_def["op_order"],
        })


def downgrade():
    conn = op.get_bind()

    # Remove operations for pve-vm-basic
    pve = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1")
    ).fetchone()
    if pve:
        conn.execute(
            sa.text("DELETE FROM component_operations WHERE component_id = :id"),
            {"id": str(pve[0])},
        )

    # Remove seed workflow definitions
    for wf_name in ['PVE VM: Extend Disk', 'PVE VM: Create Snapshot', 'PVE VM: Restart']:
        conn.execute(
            sa.text("DELETE FROM workflow_definitions WHERE name = :name"),
            {"name": wf_name},
        )
