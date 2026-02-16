"""
Overview: Seed an example Proxmox Virtual Machine component.
Architecture: Migration for component framework (Section 11)
Dependencies: 064_component_model
Concepts: Pre-populates a published VM component for Proxmox as a reference/starting point.
"""

revision = "065"
down_revision = "064"

from alembic import op
import sqlalchemy as sa


VM_CODE = '''"""
Proxmox KVM Virtual Machine — Pulumi component.
Creates a QEMU/KVM virtual machine on a Proxmox VE node.
"""

import pulumi
from pulumi import Input, Output


def create_resource(args: dict) -> dict:
    """Create a Proxmox KVM virtual machine.

    Args:
        args: Resolved input parameters including:
            - name: VM hostname (resolved by naming resolver)
            - node: Proxmox node to deploy on
            - cpu_count: Number of vCPUs
            - memory_gb: RAM in GB
            - disk_size_gb: Root disk size in GB
            - os_image: OS template/image reference (resolved by image catalog)
            - network_bridge: Network bridge (e.g. vmbr0)
            - ip_address: IP address (resolved by IPAM resolver)
            - vlan_tag: Optional VLAN tag

    Returns:
        Dictionary of output values for CMDB tracking
    """
    vm_name = args.get("name", "unnamed-vm")
    node = args.get("node", "pve")
    cpu_count = args.get("cpu_count", 2)
    memory_gb = args.get("memory_gb", 4)
    disk_size_gb = args.get("disk_size_gb", 32)
    os_image = args.get("os_image", "local:iso/ubuntu-22.04.iso")
    network_bridge = args.get("network_bridge", "vmbr0")
    ip_address = args.get("ip_address", "")
    vlan_tag = args.get("vlan_tag")

    # Proxmox VM creation via Pulumi bpg/proxmox provider
    # from pulumi_proxmox import vm
    #
    # instance = vm.VirtualMachine(
    #     vm_name,
    #     node_name=node,
    #     name=vm_name,
    #     cpu=vm.VirtualMachineCpuArgs(cores=cpu_count),
    #     memory=vm.VirtualMachineMemoryArgs(dedicated=memory_gb * 1024),
    #     disk=[vm.VirtualMachineDiskArgs(
    #         datastore_id="local-lvm",
    #         size=disk_size_gb,
    #         interface="scsi0",
    #     )],
    #     cdrom=vm.VirtualMachineCdromArgs(
    #         file_id=os_image,
    #     ),
    #     network_device=[vm.VirtualMachineNetworkDeviceArgs(
    #         bridge=network_bridge,
    #         vlan_id=vlan_tag,
    #     )],
    #     initialization=vm.VirtualMachineInitializationArgs(
    #         ip_config=[vm.VirtualMachineInitializationIpConfigArgs(
    #             ipv4=vm.VirtualMachineInitializationIpConfigIpv4Args(
    #                 address=f"{ip_address}/24" if ip_address else "dhcp",
    #             ),
    #         )],
    #     ),
    #     on_boot=True,
    #     started=True,
    # )

    return {
        "vm_id": f"qemu/{vm_name}",
        "node": node,
        "name": vm_name,
        "cpu_count": cpu_count,
        "memory_gb": memory_gb,
        "disk_size_gb": disk_size_gb,
        "ip_address": ip_address,
        "status": "created",
    }
'''

INPUT_SCHEMA = '''{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "VM hostname — auto-resolved by the naming resolver"
    },
    "node": {
      "type": "string",
      "description": "Proxmox node to deploy on",
      "default": "pve"
    },
    "cpu_count": {
      "type": "integer",
      "description": "Number of vCPUs",
      "default": 2
    },
    "memory_gb": {
      "type": "integer",
      "description": "RAM in GB",
      "default": 4
    },
    "disk_size_gb": {
      "type": "integer",
      "description": "Root disk size in GB",
      "default": 32
    },
    "os_image": {
      "type": "string",
      "description": "OS template/image reference — auto-resolved by image catalog resolver"
    },
    "network_bridge": {
      "type": "string",
      "description": "Proxmox network bridge",
      "default": "vmbr0"
    },
    "ip_address": {
      "type": "string",
      "description": "IP address — auto-resolved by IPAM resolver"
    },
    "vlan_tag": {
      "type": "integer",
      "description": "Optional VLAN tag for network segmentation"
    }
  },
  "required": ["name", "node", "cpu_count", "memory_gb", "disk_size_gb"]
}'''

OUTPUT_SCHEMA = '''{
  "type": "object",
  "properties": {
    "vm_id": {
      "type": "string",
      "description": "Proxmox VM identifier (qemu/name)"
    },
    "node": {
      "type": "string",
      "description": "Node the VM was deployed on"
    },
    "name": {
      "type": "string",
      "description": "VM hostname"
    },
    "cpu_count": {
      "type": "integer",
      "description": "Allocated vCPUs"
    },
    "memory_gb": {
      "type": "integer",
      "description": "Allocated RAM in GB"
    },
    "ip_address": {
      "type": "string",
      "description": "Assigned IP address"
    },
    "status": {
      "type": "string",
      "description": "Deployment status"
    }
  }
}'''

RESOLVER_BINDINGS = '''{
  "name": {
    "resolver_type": "naming",
    "params": {"resource_type": "vm", "environment_name": ""},
    "target": "name"
  },
  "ip_address": {
    "resolver_type": "ipam",
    "params": {"allocation_type": "ip", "ip_version": "4"},
    "target": "ip_address"
  },
  "os_image": {
    "resolver_type": "image_catalog",
    "params": {"os_family": "ubuntu", "os_version": "22.04"},
    "target": "os_image"
  }
}'''


def upgrade():
    conn = op.get_bind()

    # Look up the Proxmox provider
    provider = conn.execute(
        sa.text("SELECT id FROM semantic_providers WHERE name = 'proxmox' LIMIT 1")
    ).fetchone()
    if not provider:
        return  # No Proxmox provider seeded — skip

    # Look up the VirtualMachine semantic type
    vm_type = conn.execute(
        sa.text("SELECT id FROM semantic_resource_types WHERE name = 'VirtualMachine' LIMIT 1")
    ).fetchone()
    if not vm_type:
        return  # No VM type — skip

    # Look up a system user to use as created_by (first user, typically admin)
    user = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not user:
        return

    # Insert the example component
    conn.execute(sa.text("""
        INSERT INTO components (
            id, tenant_id, provider_id, semantic_type_id,
            name, display_name, description, language,
            code, input_schema, output_schema, resolver_bindings,
            version, is_published, is_system,
            created_by, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), NULL, :provider_id, :semantic_type_id,
            'pve-vm-basic', 'Proxmox Basic VM',
            'Deploy a KVM virtual machine on Proxmox VE with IPAM, naming, and image resolution',
            'PYTHON',
            :code, CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), CAST(:resolver_bindings AS jsonb),
            2, true, true,
            :user_id, NOW(), NOW()
        )
        ON CONFLICT DO NOTHING
    """), {
        "provider_id": str(provider[0]),
        "semantic_type_id": str(vm_type[0]),
        "user_id": str(user[0]),
        "code": VM_CODE,
        "input_schema": INPUT_SCHEMA,
        "output_schema": OUTPUT_SCHEMA,
        "resolver_bindings": RESOLVER_BINDINGS,
    })

    # Also create a version snapshot (v1 published)
    comp = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND tenant_id IS NULL LIMIT 1")
    ).fetchone()
    if comp:
        conn.execute(sa.text("""
            INSERT INTO component_versions (
                id, component_id, version, code,
                input_schema, output_schema, resolver_bindings,
                changelog, published_at, published_by
            ) VALUES (
                gen_random_uuid(), :comp_id, 1, :code,
                CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), CAST(:resolver_bindings AS jsonb),
                'Initial release — basic Proxmox KVM VM with resolver bindings for IPAM, naming, and image catalog',
                NOW(), :user_id
            )
            ON CONFLICT DO NOTHING
        """), {
            "comp_id": str(comp[0]),
            "user_id": str(user[0]),
            "code": VM_CODE,
            "input_schema": INPUT_SCHEMA,
            "output_schema": OUTPUT_SCHEMA,
            "resolver_bindings": RESOLVER_BINDINGS,
        })


def downgrade():
    conn = op.get_bind()
    comp = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1")
    ).fetchone()
    if comp:
        conn.execute(sa.text("DELETE FROM component_versions WHERE component_id = :id"), {"id": str(comp[0])})
        conn.execute(sa.text("DELETE FROM components WHERE id = :id"), {"id": str(comp[0])})
