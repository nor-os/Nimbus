"""
Overview: Update Proxmox VM example with real code, add OCI VM example component.
Architecture: Migration for component framework (Section 11)
Dependencies: 065_seed_example_vm_component
Concepts: Seed realistic Pulumi components with working code for Proxmox and OCI providers.
"""

revision = "066"
down_revision = "065"

from alembic import op
import sqlalchemy as sa


# ── Proxmox VM ────────────────────────────────────────────────────────────────

PVE_CODE = '''"""
Proxmox KVM Virtual Machine — Pulumi component.
Creates a QEMU/KVM virtual machine on a Proxmox VE node
using the bpg/proxmox Pulumi provider.
"""

import pulumi
import pulumi_proxmoxve as proxmox


def create_resource(args: dict) -> dict:
    """Create a Proxmox KVM virtual machine.

    Args:
        args: Resolved input parameters (after resolver pre-processing).

    Returns:
        Dictionary of output values to store in CMDB.
    """
    vm = proxmox.vm.VirtualMachine(
        args["name"],
        node_name=args.get("node", "pve"),
        name=args["name"],
        description=args.get("description", "Managed by Nimbus"),
        tags=["nimbus-managed"],

        # CPU
        cpu=proxmox.vm.VirtualMachineCpuArgs(
            cores=args.get("cpu_count", 2),
            sockets=1,
            type="host",
        ),

        # Memory
        memory=proxmox.vm.VirtualMachineMemoryArgs(
            dedicated=args.get("memory_gb", 4) * 1024,
        ),

        # Disk
        disks=[proxmox.vm.VirtualMachineDiskArgs(
            datastore_id=args.get("datastore", "local-lvm"),
            size=args.get("disk_size_gb", 32),
            interface="scsi0",
            file_format="raw",
        )],

        # OS image / cloud-init template
        clone=proxmox.vm.VirtualMachineCloneArgs(
            vm_id=int(args["os_image"]),
            full=True,
        ) if args.get("os_image", "").isdigit() else None,

        # Network
        network_devices=[proxmox.vm.VirtualMachineNetworkDeviceArgs(
            bridge=args.get("network_bridge", "vmbr0"),
            model="virtio",
            vlan_id=args.get("vlan_tag"),
        )],

        # Cloud-init IP config
        initialization=proxmox.vm.VirtualMachineInitializationArgs(
            type="nocloud",
            ip_configs=[proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                    address=f"{args['ip_address']}/24" if args.get("ip_address") else "dhcp",
                    gateway=args.get("gateway"),
                ),
            )],
            user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                username=args.get("admin_user", "nimbus"),
                keys=args.get("ssh_keys", []),
            ),
        ),

        on_boot=True,
        started=True,
    )

    return {
        "vm_id": vm.vm_id,
        "node": args.get("node", "pve"),
        "name": vm.name,
        "ip_address": args.get("ip_address", ""),
        "status": "running",
    }
'''

PVE_INPUT_SCHEMA = '''{
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
    "datastore": {
      "type": "string",
      "description": "Proxmox storage for VM disk",
      "default": "local-lvm"
    },
    "os_image": {
      "type": "string",
      "description": "Template VM ID or image — auto-resolved by image catalog resolver"
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
    "gateway": {
      "type": "string",
      "description": "Default gateway IP"
    },
    "vlan_tag": {
      "type": "integer",
      "description": "Optional VLAN tag for network segmentation"
    },
    "admin_user": {
      "type": "string",
      "description": "Cloud-init admin username",
      "default": "nimbus"
    },
    "ssh_keys": {
      "type": "array",
      "description": "SSH public keys for cloud-init"
    },
    "description": {
      "type": "string",
      "description": "VM description / notes"
    }
  },
  "required": ["name", "node", "cpu_count", "memory_gb", "disk_size_gb", "os_image"]
}'''

PVE_OUTPUT_SCHEMA = '''{
  "type": "object",
  "properties": {
    "vm_id": { "type": "string", "description": "Proxmox VM ID" },
    "node": { "type": "string", "description": "Node the VM was deployed on" },
    "name": { "type": "string", "description": "VM hostname" },
    "ip_address": { "type": "string", "description": "Assigned IP address" },
    "status": { "type": "string", "description": "VM power state" }
  }
}'''

PVE_RESOLVER_BINDINGS = '''{
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


# ── OCI VM ────────────────────────────────────────────────────────────────────

OCI_CODE = '''"""
OCI Compute Instance — Pulumi component.
Creates a virtual machine instance in Oracle Cloud Infrastructure
using the pulumi-oci provider.
"""

import pulumi
import pulumi_oci as oci


def create_resource(args: dict) -> dict:
    """Create an OCI Compute instance.

    Args:
        args: Resolved input parameters (after resolver pre-processing).

    Returns:
        Dictionary of output values to store in CMDB.
    """
    instance = oci.core.Instance(
        args["name"],
        availability_domain=args["availability_domain"],
        compartment_id=args["compartment_id"],
        display_name=args["name"],
        shape=args.get("shape", "VM.Standard.E4.Flex"),

        shape_config=oci.core.InstanceShapeConfigArgs(
            ocpus=args.get("cpu_count", 2),
            memory_in_gbs=args.get("memory_gb", 16),
        ),

        source_details=oci.core.InstanceSourceDetailsArgs(
            source_type="image",
            source_id=args["os_image"],
            boot_volume_size_in_gbs=args.get("boot_volume_gb", 50),
        ),

        create_vnic_details=oci.core.InstanceCreateVnicDetailsArgs(
            subnet_id=args["subnet_id"],
            display_name=f"{args['name']}-vnic",
            assign_public_ip=args.get("assign_public_ip", False),
            private_ip=args.get("ip_address"),
            nsg_ids=args.get("nsg_ids", []),
        ),

        metadata={
            "ssh_authorized_keys": args.get("ssh_public_key", ""),
            "user_data": args.get("user_data", ""),
        },

        freeform_tags={
            "managed-by": "nimbus",
            "environment": args.get("environment", ""),
        },
    )

    return {
        "instance_id": instance.id,
        "name": instance.display_name,
        "private_ip": instance.create_vnic_details.private_ip,
        "public_ip": instance.public_ip,
        "availability_domain": instance.availability_domain,
        "shape": instance.shape,
        "status": "running",
    }
'''

OCI_INPUT_SCHEMA = '''{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Instance display name — auto-resolved by the naming resolver"
    },
    "compartment_id": {
      "type": "string",
      "description": "OCI compartment OCID for the instance"
    },
    "availability_domain": {
      "type": "string",
      "description": "OCI availability domain (e.g. EU-FRANKFURT-1-AD-1)"
    },
    "shape": {
      "type": "string",
      "description": "Compute shape",
      "default": "VM.Standard.E4.Flex",
      "enum": [
        "VM.Standard.E4.Flex",
        "VM.Standard.E5.Flex",
        "VM.Standard3.Flex",
        "VM.Standard.A1.Flex",
        "VM.Optimized3.Flex"
      ]
    },
    "cpu_count": {
      "type": "integer",
      "description": "Number of OCPUs (flex shapes)",
      "default": 2
    },
    "memory_gb": {
      "type": "integer",
      "description": "Memory in GB (flex shapes)",
      "default": 16
    },
    "os_image": {
      "type": "string",
      "description": "Image OCID — auto-resolved by image catalog resolver"
    },
    "boot_volume_gb": {
      "type": "integer",
      "description": "Boot volume size in GB",
      "default": 50
    },
    "subnet_id": {
      "type": "string",
      "description": "VCN subnet OCID for the VNIC"
    },
    "ip_address": {
      "type": "string",
      "description": "Private IP — auto-resolved by IPAM resolver"
    },
    "assign_public_ip": {
      "type": "boolean",
      "description": "Assign a public IP to the instance",
      "default": false
    },
    "nsg_ids": {
      "type": "array",
      "description": "Network Security Group OCIDs"
    },
    "ssh_public_key": {
      "type": "string",
      "description": "SSH public key for instance access"
    },
    "user_data": {
      "type": "string",
      "description": "Base64-encoded cloud-init user data"
    },
    "environment": {
      "type": "string",
      "description": "Environment tag (dev, staging, prod)"
    }
  },
  "required": ["name", "compartment_id", "availability_domain", "os_image", "subnet_id"]
}'''

OCI_OUTPUT_SCHEMA = '''{
  "type": "object",
  "properties": {
    "instance_id": { "type": "string", "description": "OCI instance OCID" },
    "name": { "type": "string", "description": "Instance display name" },
    "private_ip": { "type": "string", "description": "Private IP address" },
    "public_ip": { "type": "string", "description": "Public IP (if assigned)" },
    "availability_domain": { "type": "string", "description": "Availability domain" },
    "shape": { "type": "string", "description": "Compute shape used" },
    "status": { "type": "string", "description": "Instance lifecycle state" }
  }
}'''

OCI_RESOLVER_BINDINGS = '''{
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
    "params": {"os_family": "oracle-linux", "os_version": "9"},
    "target": "os_image"
  }
}'''


def upgrade():
    conn = op.get_bind()

    # ── Update Proxmox VM with real code ──────────────────────────────
    pve = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1")
    ).fetchone()
    if pve:
        conn.execute(sa.text("""
            UPDATE components SET
                code = :code,
                input_schema = CAST(:input_schema AS jsonb),
                output_schema = CAST(:output_schema AS jsonb),
                resolver_bindings = CAST(:resolver_bindings AS jsonb),
                updated_at = NOW()
            WHERE id = :id
        """), {
            "id": str(pve[0]),
            "code": PVE_CODE,
            "input_schema": PVE_INPUT_SCHEMA,
            "output_schema": PVE_OUTPUT_SCHEMA,
            "resolver_bindings": PVE_RESOLVER_BINDINGS,
        })

        # Also update the version snapshot
        conn.execute(sa.text("""
            UPDATE component_versions SET
                code = :code,
                input_schema = CAST(:input_schema AS jsonb),
                output_schema = CAST(:output_schema AS jsonb),
                resolver_bindings = CAST(:resolver_bindings AS jsonb)
            WHERE component_id = :comp_id AND version = 1
        """), {
            "comp_id": str(pve[0]),
            "code": PVE_CODE,
            "input_schema": PVE_INPUT_SCHEMA,
            "output_schema": PVE_OUTPUT_SCHEMA,
            "resolver_bindings": PVE_RESOLVER_BINDINGS,
        })

    # ── Create OCI VM component ───────────────────────────────────────
    oci_provider = conn.execute(
        sa.text("SELECT id FROM semantic_providers WHERE name = 'oci' LIMIT 1")
    ).fetchone()
    if not oci_provider:
        return

    vm_type = conn.execute(
        sa.text("SELECT id FROM semantic_resource_types WHERE name = 'VirtualMachine' LIMIT 1")
    ).fetchone()
    if not vm_type:
        return

    user = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not user:
        return

    conn.execute(sa.text("""
        INSERT INTO components (
            id, tenant_id, provider_id, semantic_type_id,
            name, display_name, description, language,
            code, input_schema, output_schema, resolver_bindings,
            version, is_published, is_system,
            created_by, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), NULL, :provider_id, :semantic_type_id,
            'oci-vm-flex', 'OCI Flex Compute Instance',
            'Deploy a flexible compute instance on Oracle Cloud Infrastructure with shape config, VNIC, and cloud-init',
            'PYTHON',
            :code, CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), CAST(:resolver_bindings AS jsonb),
            2, true, true,
            :user_id, NOW(), NOW()
        )
        ON CONFLICT DO NOTHING
    """), {
        "provider_id": str(oci_provider[0]),
        "semantic_type_id": str(vm_type[0]),
        "user_id": str(user[0]),
        "code": OCI_CODE,
        "input_schema": OCI_INPUT_SCHEMA,
        "output_schema": OCI_OUTPUT_SCHEMA,
        "resolver_bindings": OCI_RESOLVER_BINDINGS,
    })

    # Create version snapshot for OCI
    oci_comp = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND tenant_id IS NULL LIMIT 1")
    ).fetchone()
    if oci_comp:
        conn.execute(sa.text("""
            INSERT INTO component_versions (
                id, component_id, version, code,
                input_schema, output_schema, resolver_bindings,
                changelog, published_at, published_by
            ) VALUES (
                gen_random_uuid(), :comp_id, 1, :code,
                CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb), CAST(:resolver_bindings AS jsonb),
                'Initial release — OCI flex compute instance with IPAM, naming, and image catalog resolvers',
                NOW(), :user_id
            )
            ON CONFLICT DO NOTHING
        """), {
            "comp_id": str(oci_comp[0]),
            "user_id": str(user[0]),
            "code": OCI_CODE,
            "input_schema": OCI_INPUT_SCHEMA,
            "output_schema": OCI_OUTPUT_SCHEMA,
            "resolver_bindings": OCI_RESOLVER_BINDINGS,
        })


def downgrade():
    conn = op.get_bind()
    # Remove OCI component
    oci_comp = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND is_system = true LIMIT 1")
    ).fetchone()
    if oci_comp:
        conn.execute(sa.text("DELETE FROM component_versions WHERE component_id = :id"), {"id": str(oci_comp[0])})
        conn.execute(sa.text("DELETE FROM components WHERE id = :id"), {"id": str(oci_comp[0])})
