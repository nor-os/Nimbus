"""
Overview: Seed example day-2 operations for the OCI Flex Compute Instance component.
Architecture: Migration for component operations (Section 11)
Dependencies: 072_workflow_applicability
Concepts: Creates workflow definitions and component operations for resize, stop/start,
    create_custom_image, restart, update_network, and create_backup on the oci-vm-flex component.
"""

revision = "073"
down_revision = "072"

from alembic import op
import sqlalchemy as sa


# ── Operation input/output schemas ───────────────────────────────────────────

RESIZE_INPUT = """{
  "type": "object",
  "properties": {
    "new_ocpus": {
      "type": "number",
      "description": "New OCPU count for the Flex shape (e.g. 1, 2, 4, 8)"
    },
    "new_memory_gb": {
      "type": "number",
      "description": "New memory in GB (must be between 1-64 GB per OCPU)"
    },
    "new_boot_volume_gb": {
      "type": "integer",
      "description": "New boot volume size in GB (can only increase, not decrease)"
    }
  },
  "required": ["new_ocpus", "new_memory_gb"]
}"""

RESIZE_OUTPUT = """{
  "type": "object",
  "properties": {
    "old_ocpus": { "type": "number", "description": "Previous OCPU count" },
    "new_ocpus": { "type": "number", "description": "New OCPU count" },
    "old_memory_gb": { "type": "number", "description": "Previous memory in GB" },
    "new_memory_gb": { "type": "number", "description": "New memory in GB" },
    "boot_volume_resized": { "type": "boolean", "description": "Whether boot volume was resized" },
    "reboot_required": { "type": "boolean", "description": "Whether a reboot was needed" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

STOP_START_INPUT = """{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "description": "Action to perform",
      "enum": ["stop", "start"]
    },
    "force": {
      "type": "boolean",
      "description": "Force stop (HARD reset) if graceful shutdown fails",
      "default": false
    },
    "preserve_boot_volume": {
      "type": "boolean",
      "description": "Keep boot volume attached when stopping (billed as storage only)",
      "default": true
    }
  },
  "required": ["action"]
}"""

STOP_START_OUTPUT = """{
  "type": "object",
  "properties": {
    "previous_state": { "type": "string", "description": "Instance lifecycle state before action" },
    "current_state": { "type": "string", "description": "Instance lifecycle state after action" },
    "action_performed": { "type": "string", "description": "stop or start" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

CUSTOM_IMAGE_INPUT = """{
  "type": "object",
  "properties": {
    "image_name": {
      "type": "string",
      "description": "Display name for the custom image"
    },
    "compartment_id": {
      "type": "string",
      "description": "Target compartment OCID for the image (defaults to instance compartment)"
    },
    "freeform_tags": {
      "type": "object",
      "description": "Freeform tags to apply to the image"
    }
  },
  "required": ["image_name"]
}"""

CUSTOM_IMAGE_OUTPUT = """{
  "type": "object",
  "properties": {
    "image_id": { "type": "string", "description": "OCID of the created custom image" },
    "image_name": { "type": "string", "description": "Image display name" },
    "size_gb": { "type": "number", "description": "Image size in GB" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

RESTART_INPUT = """{
  "type": "object",
  "properties": {
    "reset_type": {
      "type": "string",
      "description": "Restart method: SOFTRESET (ACPI) or RESET (hard)",
      "enum": ["SOFTRESET", "RESET"],
      "default": "SOFTRESET"
    },
    "timeout_seconds": {
      "type": "integer",
      "description": "Seconds to wait for the instance to reach RUNNING state",
      "default": 300
    }
  }
}"""

RESTART_OUTPUT = """{
  "type": "object",
  "properties": {
    "previous_state": { "type": "string", "description": "Instance state before restart" },
    "current_state": { "type": "string", "description": "Instance state after restart" },
    "reset_type": { "type": "string", "description": "SOFTRESET or RESET" },
    "duration_seconds": { "type": "integer", "description": "Total restart duration" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

UPDATE_NETWORK_INPUT = """{
  "type": "object",
  "properties": {
    "vnic_id": {
      "type": "string",
      "description": "OCID of the VNIC to update (defaults to primary VNIC)"
    },
    "new_nsg_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Replacement list of Network Security Group OCIDs"
    },
    "skip_source_dest_check": {
      "type": "boolean",
      "description": "Disable source/destination check on the VNIC (required for NAT/routing instances)"
    },
    "new_hostname_label": {
      "type": "string",
      "description": "New DNS hostname label for the VNIC"
    }
  }
}"""

UPDATE_NETWORK_OUTPUT = """{
  "type": "object",
  "properties": {
    "vnic_id": { "type": "string", "description": "OCID of the updated VNIC" },
    "private_ip": { "type": "string", "description": "Private IP address" },
    "nsg_ids": { "type": "array", "items": { "type": "string" }, "description": "Applied NSG OCIDs" },
    "hostname_label": { "type": "string", "description": "Updated hostname label" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""

CREATE_BACKUP_INPUT = """{
  "type": "object",
  "properties": {
    "backup_name": {
      "type": "string",
      "description": "Display name for the boot volume backup"
    },
    "backup_type": {
      "type": "string",
      "description": "FULL or INCREMENTAL backup",
      "enum": ["FULL", "INCREMENTAL"],
      "default": "INCREMENTAL"
    },
    "freeform_tags": {
      "type": "object",
      "description": "Freeform tags to apply to the backup"
    }
  },
  "required": ["backup_name"]
}"""

CREATE_BACKUP_OUTPUT = """{
  "type": "object",
  "properties": {
    "backup_id": { "type": "string", "description": "OCID of the boot volume backup" },
    "backup_name": { "type": "string", "description": "Backup display name" },
    "backup_type": { "type": "string", "description": "FULL or INCREMENTAL" },
    "size_gb": { "type": "number", "description": "Backup size in GB" },
    "status": { "type": "string", "description": "Operation result status" }
  }
}"""


# ── Workflow graphs (Rete.js DAGs with real node types and port connections) ──

RESIZE_GRAPH = """{
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
}"""

STOP_START_GRAPH = """{
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
}"""

CUSTOM_IMAGE_GRAPH = """{
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
}"""

RESTART_GRAPH = """{
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
}"""

UPDATE_NETWORK_GRAPH = """{
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
}"""

CREATE_BACKUP_GRAPH = """{
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
}"""


# ── Migration ────────────────────────────────────────────────────────────────

def upgrade():
    conn = op.get_bind()

    # Find OCI Flex VM component
    oci = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND is_system = true LIMIT 1")
    ).fetchone()
    if not oci:
        return

    # Find a user for created_by and a tenant for workflow defs
    user = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not user:
        return

    tenant = conn.execute(
        sa.text("SELECT id FROM tenants ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not tenant:
        return

    # Find OCI provider and VirtualMachine semantic type for workflow applicability
    oci_provider = conn.execute(
        sa.text("SELECT id FROM semantic_providers WHERE name = 'oci' LIMIT 1")
    ).fetchone()

    vm_type = conn.execute(
        sa.text("SELECT id FROM semantic_resource_types WHERE name = 'VirtualMachine' LIMIT 1")
    ).fetchone()

    operations = [
        {
            "op_name": "resize",
            "op_display": "Resize Instance",
            "op_desc": "Change the OCPU and memory allocation of the Flex shape. "
                       "Requires a brief stop/start cycle — the instance will be offline during reconfiguration.",
            "op_input": RESIZE_INPUT,
            "op_output": RESIZE_OUTPUT,
            "op_destructive": False,
            "op_approval": True,
            "op_downtime": "BRIEF",
            "op_order": 1,
            "wf_name": "OCI Flex VM: Resize",
            "wf_desc": "Validate shape limits → stop instance → update shape config → resize boot volume → start → verify",
            "wf_graph": RESIZE_GRAPH,
        },
        {
            "op_name": "stop_start",
            "op_display": "Stop / Start",
            "op_desc": "Stop or start the compute instance. Stopped instances are not billed for OCPU/memory (storage charges still apply).",
            "op_input": STOP_START_INPUT,
            "op_output": STOP_START_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "BRIEF",
            "op_order": 2,
            "wf_name": "OCI Flex VM: Stop / Start",
            "wf_desc": "Check current state → perform stop or start action → wait for target state → verify",
            "wf_graph": STOP_START_GRAPH,
        },
        {
            "op_name": "create_custom_image",
            "op_display": "Create Custom Image",
            "op_desc": "Capture a custom image from the instance boot volume. "
                       "The instance is stopped during capture to ensure consistency, then restarted.",
            "op_input": CUSTOM_IMAGE_INPUT,
            "op_output": CUSTOM_IMAGE_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "EXTENDED",
            "op_order": 3,
            "wf_name": "OCI Flex VM: Create Custom Image",
            "wf_desc": "Stop instance → create image from boot volume → wait until available → restart instance",
            "wf_graph": CUSTOM_IMAGE_GRAPH,
        },
        {
            "op_name": "restart",
            "op_display": "Restart Instance",
            "op_desc": "Restart the compute instance using SOFTRESET (ACPI signal) or RESET (hard reboot).",
            "op_input": RESTART_INPUT,
            "op_output": RESTART_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "BRIEF",
            "op_order": 4,
            "wf_name": "OCI Flex VM: Restart",
            "wf_desc": "Send reset action → wait for stopping → wait for running → verify health",
            "wf_graph": RESTART_GRAPH,
        },
        {
            "op_name": "update_network",
            "op_display": "Update Network Config",
            "op_desc": "Update VNIC settings: reassign Network Security Groups, change hostname label, "
                       "or toggle source/destination check. No downtime — changes apply immediately.",
            "op_input": UPDATE_NETWORK_INPUT,
            "op_output": UPDATE_NETWORK_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "NONE",
            "op_order": 5,
            "wf_name": "OCI Flex VM: Update Network",
            "wf_desc": "Resolve VNIC attachment → update VNIC configuration → verify settings",
            "wf_graph": UPDATE_NETWORK_GRAPH,
        },
        {
            "op_name": "create_backup",
            "op_display": "Create Backup",
            "op_desc": "Create a boot volume backup (full or incremental). "
                       "Backups run in the background — no instance downtime required.",
            "op_input": CREATE_BACKUP_INPUT,
            "op_output": CREATE_BACKUP_OUTPUT,
            "op_destructive": False,
            "op_approval": False,
            "op_downtime": "NONE",
            "op_order": 6,
            "wf_name": "OCI Flex VM: Create Backup",
            "wf_desc": "Get boot volume OCID → create backup → wait until available → verify",
            "wf_graph": CREATE_BACKUP_GRAPH,
        },
    ]

    for op_def in operations:
        # Create workflow definition
        wf_params = {
            "tenant_id": str(tenant[0]),
            "name": op_def["wf_name"],
            "desc": op_def["wf_desc"],
            "graph": op_def["wf_graph"],
            "user_id": str(user[0]),
        }

        # Add applicability columns if we found the provider/type
        if oci_provider and vm_type:
            conn.execute(sa.text("""
                INSERT INTO workflow_definitions (
                    id, tenant_id, name, description, workflow_type,
                    graph, status, version,
                    applicable_semantic_type_id, applicable_provider_id,
                    created_by, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :tenant_id, :name, :desc, 'AUTOMATION',
                    CAST(:graph AS jsonb), 'ACTIVE', 1,
                    :semantic_type_id, :provider_id,
                    :user_id, NOW(), NOW()
                )
                ON CONFLICT DO NOTHING
            """), {
                **wf_params,
                "semantic_type_id": str(vm_type[0]),
                "provider_id": str(oci_provider[0]),
            })
        else:
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
            """), wf_params)

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
            "comp_id": str(oci[0]),
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

    # Remove operations for oci-vm-flex
    oci = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND is_system = true LIMIT 1")
    ).fetchone()
    if oci:
        conn.execute(
            sa.text("DELETE FROM component_operations WHERE component_id = :id"),
            {"id": str(oci[0])},
        )

    # Remove seed workflow definitions
    for wf_name in [
        'OCI Flex VM: Resize',
        'OCI Flex VM: Stop / Start',
        'OCI Flex VM: Create Custom Image',
        'OCI Flex VM: Restart',
        'OCI Flex VM: Update Network',
        'OCI Flex VM: Create Backup',
    ]:
        conn.execute(
            sa.text("DELETE FROM workflow_definitions WHERE name = :name"),
            {"name": wf_name},
        )
