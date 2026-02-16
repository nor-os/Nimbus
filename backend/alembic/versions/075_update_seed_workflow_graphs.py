"""
Overview: Update seed workflow graphs to use real node types (cloud_api, ssh_exec, delay, script)
    and add sourcePort/targetPort to all connections so the editor renders them correctly.
Architecture: Data migration for seeded workflow definitions (Section 11)
Dependencies: 074_landing_zone_hierarchy
Concepts: Replaces placeholder 'action' node types with real executable node types.
"""
# ruff: noqa: E501, E402, I001

revision = "075"
down_revision = "074"

from alembic import op
import sqlalchemy as sa


# ── PVE workflow graphs ──────────────────────────────────────────────────────

PVE_GRAPHS = {
    "PVE VM: Extend Disk": """{
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
}""",
    "PVE VM: Create Snapshot": """{
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
}""",
    "PVE VM: Restart": """{
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
}""",
}

# ── OCI workflow graphs ──────────────────────────────────────────────────────

OCI_GRAPHS = {
    "OCI Flex VM: Resize": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "validate_shape", "type": "script", "label": "Validate Shape Limits", "position": {"x": 200, "y": 0},
     "config": {
       "assignments": [
         {"variable": "mem_per_ocpu", "expression": "$input.new_memory_gb / $input.new_ocpus"},
         {"variable": "is_valid", "expression": "$input.new_ocpus >= 1 && $input.new_memory_gb >= 1 && ($input.new_memory_gb / $input.new_ocpus) <= 64"}
       ]
     }},
    {"id": "stop_instance", "type": "cloud_api", "label": "Stop Instance", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"STOP\\"}"
     }},
    {"id": "update_shape", "type": "cloud_api", "label": "Update Shape Config", "position": {"x": 600, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "PUT",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"shapeConfig\\": {\\"ocpus\\": ${$input.new_ocpus}, \\"memoryInGBs\\": ${$input.new_memory_gb}}}"
     }},
    {"id": "resize_boot_vol", "type": "cloud_api", "label": "Resize Boot Volume", "position": {"x": 800, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "PUT",
       "path": "/20160918/bootVolumes/${$input.boot_volume_id}",
       "body": "{\\"sizeInGBs\\": ${$input.new_boot_volume_gb}}"
     }},
    {"id": "start_instance", "type": "cloud_api", "label": "Start Instance", "position": {"x": 1000, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"START\\"}"
     }},
    {"id": "verify", "type": "cloud_api", "label": "Verify Shape", "position": {"x": 1200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/instances/${$input.instance_id}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1400, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "validate_shape", "sourcePort": "out", "targetPort": "in"},
    {"source": "validate_shape", "target": "stop_instance", "sourcePort": "out", "targetPort": "in"},
    {"source": "stop_instance", "target": "update_shape", "sourcePort": "out", "targetPort": "in"},
    {"source": "update_shape", "target": "resize_boot_vol", "sourcePort": "out", "targetPort": "in"},
    {"source": "resize_boot_vol", "target": "start_instance", "sourcePort": "out", "targetPort": "in"},
    {"source": "start_instance", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
    "OCI Flex VM: Stop / Start": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "check_state", "type": "cloud_api", "label": "Check Current State", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/instances/${$input.instance_id}"
     }},
    {"id": "perform_action", "type": "cloud_api", "label": "Stop or Start", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"${$input.action}\\"}"
     }},
    {"id": "wait_state", "type": "delay", "label": "Wait for State", "position": {"x": 600, "y": 0},
     "config": {"seconds": 10}},
    {"id": "verify", "type": "cloud_api", "label": "Verify State", "position": {"x": 800, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/instances/${$input.instance_id}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1000, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "check_state", "sourcePort": "out", "targetPort": "in"},
    {"source": "check_state", "target": "perform_action", "sourcePort": "out", "targetPort": "in"},
    {"source": "perform_action", "target": "wait_state", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_state", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
    "OCI Flex VM: Create Custom Image": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "stop_instance", "type": "cloud_api", "label": "Stop Instance", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"STOP\\"}"
     }},
    {"id": "create_image", "type": "cloud_api", "label": "Create Custom Image", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/images",
       "body": "{\\"compartmentId\\": \\"${$input.compartment_id}\\", \\"displayName\\": \\"${$input.image_name}\\", \\"instanceId\\": \\"${$input.instance_id}\\"}"
     }},
    {"id": "wait_image", "type": "delay", "label": "Wait for Image", "position": {"x": 600, "y": 0},
     "config": {"seconds": 30}},
    {"id": "start_instance", "type": "cloud_api", "label": "Start Instance", "position": {"x": 800, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"START\\"}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1000, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "stop_instance", "sourcePort": "out", "targetPort": "in"},
    {"source": "stop_instance", "target": "create_image", "sourcePort": "out", "targetPort": "in"},
    {"source": "create_image", "target": "wait_image", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_image", "target": "start_instance", "sourcePort": "out", "targetPort": "in"},
    {"source": "start_instance", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
    "OCI Flex VM: Restart": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "send_reset", "type": "cloud_api", "label": "Send Reset Action", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/instances/${$input.instance_id}",
       "body": "{\\"action\\": \\"${$input.reset_type}\\"}"
     }},
    {"id": "wait_restart", "type": "delay", "label": "Wait for Restart", "position": {"x": 400, "y": 0},
     "config": {"seconds": 10}},
    {"id": "verify", "type": "cloud_api", "label": "Verify Running", "position": {"x": 600, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/instances/${$input.instance_id}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 800, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "send_reset", "sourcePort": "out", "targetPort": "in"},
    {"source": "send_reset", "target": "wait_restart", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_restart", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
    "OCI Flex VM: Update Network": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "get_vnic", "type": "cloud_api", "label": "List VNIC Attachments", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/vnicAttachments",
       "query_params": {"compartmentId": "${$input.compartment_id}", "instanceId": "${$input.instance_id}"}
     }},
    {"id": "update_vnic", "type": "cloud_api", "label": "Update VNIC", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "PUT",
       "path": "/20160918/vnics/${$input.vnic_id}",
       "body": "{\\"nsgIds\\": ${$input.new_nsg_ids}, \\"skipSourceDestCheck\\": ${$input.skip_source_dest_check}, \\"hostnameLabel\\": \\"${$input.new_hostname_label}\\"}"
     }},
    {"id": "verify", "type": "cloud_api", "label": "Verify VNIC", "position": {"x": 600, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/vnics/${$input.vnic_id}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 800, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "get_vnic", "sourcePort": "out", "targetPort": "in"},
    {"source": "get_vnic", "target": "update_vnic", "sourcePort": "out", "targetPort": "in"},
    {"source": "update_vnic", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
    "OCI Flex VM: Create Backup": """{
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "position": {"x": 0, "y": 0}},
    {"id": "get_boot_vol", "type": "cloud_api", "label": "List Boot Volume Attachments", "position": {"x": 200, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/bootVolumeAttachments",
       "query_params": {"compartmentId": "${$input.compartment_id}", "instanceId": "${$input.instance_id}", "availabilityDomain": "${$input.availability_domain}"}
     }},
    {"id": "create_backup", "type": "cloud_api", "label": "Create Backup", "position": {"x": 400, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "POST",
       "path": "/20160918/bootVolumeBackups",
       "body": "{\\"bootVolumeId\\": \\"${$nodes.get_boot_vol.body[0].bootVolumeId}\\", \\"displayName\\": \\"${$input.backup_name}\\", \\"type\\": \\"${$input.backup_type}\\"}"
     }},
    {"id": "wait_backup", "type": "delay", "label": "Wait for Backup", "position": {"x": 600, "y": 0},
     "config": {"seconds": 15}},
    {"id": "verify", "type": "cloud_api", "label": "Verify Backup", "position": {"x": 800, "y": 0},
     "config": {
       "backend_id": "${$input.backend_id}",
       "method": "GET",
       "path": "/20160918/bootVolumeBackups/${$nodes.create_backup.body.id}"
     }},
    {"id": "end", "type": "end", "label": "End", "position": {"x": 1000, "y": 0}}
  ],
  "connections": [
    {"source": "start", "target": "get_boot_vol", "sourcePort": "out", "targetPort": "in"},
    {"source": "get_boot_vol", "target": "create_backup", "sourcePort": "out", "targetPort": "in"},
    {"source": "create_backup", "target": "wait_backup", "sourcePort": "out", "targetPort": "in"},
    {"source": "wait_backup", "target": "verify", "sourcePort": "out", "targetPort": "in"},
    {"source": "verify", "target": "end", "sourcePort": "out", "targetPort": "in"}
  ]
}""",
}


def upgrade():
    conn = op.get_bind()

    all_graphs = {**PVE_GRAPHS, **OCI_GRAPHS}

    for wf_name, graph_json in all_graphs.items():
        conn.execute(
            sa.text("""
                UPDATE workflow_definitions
                SET graph = CAST(:graph AS jsonb),
                    updated_at = NOW()
                WHERE name = :name
            """),
            {"name": wf_name, "graph": graph_json},
        )


def downgrade():
    # No rollback — the old 'action' node type graphs are non-functional anyway.
    pass
