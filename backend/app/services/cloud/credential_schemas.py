"""
Overview: Per-provider JSON Schema definitions for credential validation and scope configuration.
Architecture: Schema definitions for CloudBackendService credential validation (Section 11)
Dependencies: None (pure data module)
Concepts: Each provider defines one or more auth types with JSON Schema for credential fields.
    Scope schemas define per-provider configuration (regions, accounts, projects, etc.).
    Foundation schemas define hub/org/global settings for landing zones.
    Environment schemas define per-environment spoke/access/security/monitoring settings.
"""

from __future__ import annotations

# -- Credential schemas per provider ----------------------------------------

CREDENTIAL_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["api_token", "password"],
                "description": "Authentication method",
            },
            "cluster_url": {
                "type": "string",
                "format": "uri",
                "description": "Proxmox cluster URL (e.g. https://pve.example.com:8006)",
            },
            "token_id": {
                "type": "string",
                "description": "API token ID (e.g. user@pam!token-name)",
            },
            "secret": {
                "type": "string",
                "description": "API token secret",
            },
            "username": {
                "type": "string",
                "description": "Username (e.g. root@pam)",
            },
            "password": {
                "type": "string",
                "description": "Password",
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Verify SSL certificates",
            },
        },
        "required": ["auth_type", "cluster_url"],
        "allOf": [
            {
                "if": {"properties": {"auth_type": {"const": "api_token"}}},
                "then": {"required": ["token_id", "secret"]},
            },
            {
                "if": {"properties": {"auth_type": {"const": "password"}}},
                "then": {"required": ["username", "password"]},
            },
        ],
    },
    "aws": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["access_key", "assume_role"],
                "description": "Authentication method",
            },
            "access_key_id": {
                "type": "string",
                "description": "AWS access key ID",
            },
            "secret_access_key": {
                "type": "string",
                "description": "AWS secret access key",
            },
            "region": {
                "type": "string",
                "description": "Default AWS region (e.g. us-east-1)",
            },
            "role_arn": {
                "type": "string",
                "description": "ARN of IAM role to assume",
            },
            "external_id": {
                "type": "string",
                "description": "External ID for cross-account role assumption",
            },
        },
        "required": ["auth_type"],
        "allOf": [
            {
                "if": {"properties": {"auth_type": {"const": "access_key"}}},
                "then": {"required": ["access_key_id", "secret_access_key", "region"]},
            },
            {
                "if": {"properties": {"auth_type": {"const": "assume_role"}}},
                "then": {"required": ["role_arn"]},
            },
        ],
    },
    "azure": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["service_principal"],
                "description": "Authentication method",
            },
            "tenant_id": {
                "type": "string",
                "format": "uuid",
                "description": "Azure AD tenant ID",
            },
            "client_id": {
                "type": "string",
                "format": "uuid",
                "description": "Application (client) ID",
            },
            "client_secret": {
                "type": "string",
                "description": "Client secret",
            },
            "subscription_id": {
                "type": "string",
                "format": "uuid",
                "description": "Default subscription ID",
            },
        },
        "required": ["auth_type", "tenant_id", "client_id", "client_secret", "subscription_id"],
    },
    "gcp": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["service_account"],
                "description": "Authentication method",
            },
            "service_account_json": {
                "type": "string",
                "description": "Service account JSON key (full content)",
            },
            "project_id": {
                "type": "string",
                "description": "Default GCP project ID",
            },
        },
        "required": ["auth_type", "service_account_json", "project_id"],
    },
    "oci": {
        "type": "object",
        "properties": {
            "auth_type": {
                "type": "string",
                "enum": ["api_key"],
                "description": "Authentication method",
            },
            "user_ocid": {
                "type": "string",
                "description": "User OCID",
            },
            "tenancy_ocid": {
                "type": "string",
                "description": "Tenancy OCID",
            },
            "fingerprint": {
                "type": "string",
                "description": "API key fingerprint",
            },
            "private_key": {
                "type": "string",
                "description": "PEM-encoded private key",
            },
            "region": {
                "type": "string",
                "description": "Default OCI region (e.g. us-ashburn-1)",
            },
        },
        "required": ["auth_type", "user_ocid", "tenancy_ocid", "fingerprint", "private_key", "region"],
    },
}

# -- Scope schemas per provider ---------------------------------------------

SCOPE_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific Proxmox nodes (empty = all)",
            },
            "pools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific resource pools",
            },
        },
    },
    "aws": {
        "type": "object",
        "properties": {
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "AWS regions to manage (e.g. ['us-east-1', 'eu-west-1'])",
            },
            "account_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "AWS account IDs to manage",
            },
        },
    },
    "azure": {
        "type": "object",
        "properties": {
            "subscriptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Azure subscription IDs",
            },
            "resource_groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit to specific resource groups",
            },
        },
    },
    "gcp": {
        "type": "object",
        "properties": {
            "projects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "GCP project IDs to manage",
            },
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "GCP regions (e.g. ['us-central1'])",
            },
        },
    },
    "oci": {
        "type": "object",
        "properties": {
            "compartments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OCI compartment OCIDs",
            },
            "regions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OCI regions",
            },
        },
    },
}


# -- IAM identity schemas per provider ---------------------------------------
# These define the cloud-side identity fields that Nimbus roles map to.
# Each provider has different concepts for identity (ARNs, usernames, OCIDs, etc.).

IAM_IDENTITY_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Identity",
        "properties": {
            "username": {
                "type": "string",
                "title": "Username",
                "description": "Proxmox user (e.g. deploy@pve or admin@pam)",
                "placeholder": "deploy@pve",
            },
            "pool": {
                "type": "string",
                "title": "Resource Pool",
                "description": "Optional resource pool to restrict access",
                "placeholder": "production",
            },
        },
        "required": ["username"],
    },
    "aws": {
        "type": "object",
        "title": "AWS Identity",
        "properties": {
            "identity_type": {
                "type": "string",
                "title": "Identity Type",
                "enum": ["role", "user"],
                "enumLabels": ["IAM Role (recommended)", "IAM User"],
                "description": "Type of AWS IAM identity",
            },
            "role_arn": {
                "type": "string",
                "title": "Role ARN",
                "description": "ARN of the IAM role to assume",
                "placeholder": "arn:aws:iam::123456789012:role/NimbusAdmin",
                "showWhen": {"identity_type": "role"},
            },
            "user_arn": {
                "type": "string",
                "title": "User ARN",
                "description": "ARN of the IAM user",
                "placeholder": "arn:aws:iam::123456789012:user/nimbus-svc",
                "showWhen": {"identity_type": "user"},
            },
            "external_id": {
                "type": "string",
                "title": "External ID",
                "description": "External ID for cross-account role assumption",
                "placeholder": "nimbus-external-id-12345",
            },
        },
        "required": ["identity_type"],
    },
    "azure": {
        "type": "object",
        "title": "Azure Identity",
        "properties": {
            "identity_type": {
                "type": "string",
                "title": "Identity Type",
                "enum": ["service_principal", "managed_identity", "user"],
                "enumLabels": [
                    "Service Principal (recommended)",
                    "Managed Identity",
                    "Azure AD User",
                ],
                "description": "Type of Azure AD identity",
            },
            "object_id": {
                "type": "string",
                "title": "Object ID",
                "description": "Azure AD object ID of the principal",
                "placeholder": "00000000-0000-0000-0000-000000000000",
            },
            "role_definition": {
                "type": "string",
                "title": "Azure Role",
                "description": "Built-in or custom role name",
                "placeholder": "Contributor",
            },
            "scope": {
                "type": "string",
                "title": "Scope",
                "description": "Resource scope for the role assignment",
                "placeholder": "/subscriptions/{sub-id}/resourceGroups/{rg}",
            },
        },
        "required": ["identity_type", "object_id"],
    },
    "gcp": {
        "type": "object",
        "title": "GCP Identity",
        "properties": {
            "identity_type": {
                "type": "string",
                "title": "Identity Type",
                "enum": ["service_account", "user"],
                "enumLabels": ["Service Account (recommended)", "Google User"],
                "description": "Type of GCP identity",
            },
            "email": {
                "type": "string",
                "title": "Email",
                "description": "Service account or user email",
                "placeholder": "nimbus-admin@project.iam.gserviceaccount.com",
            },
            "roles": {
                "type": "string",
                "title": "IAM Roles",
                "description": "Comma-separated GCP IAM roles",
                "placeholder": "roles/editor, roles/compute.admin",
            },
        },
        "required": ["identity_type", "email"],
    },
    "oci": {
        "type": "object",
        "title": "OCI Identity",
        "properties": {
            "identity_type": {
                "type": "string",
                "title": "Identity Type",
                "enum": ["user", "group", "dynamic_group"],
                "enumLabels": ["IAM User", "IAM Group", "Dynamic Group"],
                "description": "Type of OCI identity",
            },
            "ocid": {
                "type": "string",
                "title": "OCID",
                "description": "OCI identifier for the user, group, or dynamic group",
                "placeholder": "ocid1.user.oc1..aaaa...",
            },
            "compartment_ocid": {
                "type": "string",
                "title": "Compartment OCID",
                "description": "Compartment scope for permissions",
                "placeholder": "ocid1.compartment.oc1..aaaa...",
            },
        },
        "required": ["identity_type", "ocid"],
    },
}


# ==========================================================================
# Foundation schemas — hub/org/global settings for landing zones
# ==========================================================================

FOUNDATION_NETWORK_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Hub Network",
        "properties": {
            "linux_bridge": {
                "type": "object",
                "title": "Linux Bridge",
                "properties": {
                    "name": {"type": "string", "title": "Bridge Name", "description": "e.g. vmbr0"},
                    "cidr": {"type": "string", "title": "CIDR", "format": "cidr", "description": "Bridge IP/CIDR"},
                    "gateway": {"type": "string", "title": "Gateway", "description": "Default gateway IP"},
                    "autostart": {"type": "boolean", "title": "Autostart", "default": True},
                    "vlan_aware": {"type": "boolean", "title": "VLAN Aware", "default": True},
                },
            },
            "vlan_range": {
                "type": "string",
                "title": "VLAN Range",
                "description": "Allowed VLAN ID range (e.g. 100-200)",
            },
            "mtu": {
                "type": "integer",
                "title": "MTU",
                "description": "Maximum transmission unit",
                "default": 1500,
            },
            "dns_servers": {
                "type": "array",
                "items": {"type": "string"},
                "title": "DNS Servers",
                "description": "Default DNS servers for provisioned VMs",
            },
            "ntp_servers": {
                "type": "array",
                "items": {"type": "string"},
                "title": "NTP Servers",
                "description": "Default NTP servers",
            },
            "sdn": {
                "type": "object",
                "title": "SDN Configuration",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable SDN", "default": False},
                    "zone_type": {"type": "string", "title": "Zone Type", "enum": ["simple", "vlan", "vxlan", "evpn"]},
                    "zone_name": {"type": "string", "title": "Zone Name"},
                },
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Hub Network",
        "properties": {
            "hub_vpc": {
                "type": "object",
                "title": "Hub VPC",
                "properties": {
                    "cidr": {"type": "string", "title": "CIDR", "format": "cidr", "description": "Primary VPC CIDR block"},
                    "name": {"type": "string", "title": "VPC Name"},
                    "enable_dns_support": {"type": "boolean", "title": "DNS Support", "default": True},
                    "enable_dns_hostnames": {"type": "boolean", "title": "DNS Hostnames", "default": True},
                    "secondary_cidrs": {"type": "array", "items": {"type": "string"}, "title": "Secondary CIDRs"},
                },
            },
            "hub_subnets": {
                "type": "array",
                "title": "Hub Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "az": {"type": "string", "title": "Availability Zone"},
                        "type": {"type": "string", "title": "Type", "enum": ["public", "private", "firewall", "tgw_attachment"]},
                    },
                },
            },
            "transit_gateway": {
                "type": "object",
                "title": "Transit Gateway",
                "description": "Central routing hub connecting VPCs",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Transit Gateway", "default": True},
                    "amazon_side_asn": {"type": "integer", "title": "Amazon Side ASN", "default": 64512},
                    "auto_accept_shared_attachments": {"type": "boolean", "title": "Auto-Accept Attachments", "default": True},
                    "default_route_table_association": {"type": "boolean", "title": "Default Route Table Association", "default": True},
                    "default_route_table_propagation": {"type": "boolean", "title": "Default Route Table Propagation", "default": True},
                    "cidr_blocks": {"type": "array", "items": {"type": "string"}, "title": "TGW CIDR Blocks"},
                },
            },
            "nat_gateways": {
                "type": "object",
                "title": "NAT Gateways",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable NAT Gateways", "default": True},
                    "one_per_az": {"type": "boolean", "title": "One Per AZ", "description": "Deploy one NAT GW per AZ for HA", "default": True},
                },
            },
            "network_firewall": {
                "type": "object",
                "title": "AWS Network Firewall",
                "description": "Managed stateful inspection firewall",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Network Firewall", "default": False},
                    "firewall_name": {"type": "string", "title": "Firewall Name"},
                    "alert_mode": {"type": "string", "title": "Alert Mode", "enum": ["STRICT", "DROP", "ALERT"]},
                    "stateless_default_actions": {"type": "string", "title": "Default Action", "enum": ["aws:forward_to_sfe", "aws:drop", "aws:pass"]},
                },
            },
            "dns_resolver": {
                "type": "object",
                "title": "Route 53 Resolver",
                "description": "Hybrid DNS resolution for on-premises and cloud",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable DNS Resolver", "default": False},
                    "inbound_enabled": {"type": "boolean", "title": "Inbound Endpoint", "default": True},
                    "outbound_enabled": {"type": "boolean", "title": "Outbound Endpoint", "default": True},
                    "forwarding_rules": {
                        "type": "array",
                        "title": "Forwarding Rules",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain_name": {"type": "string", "title": "Domain Name"},
                                "target_ips": {"type": "array", "items": {"type": "string"}, "title": "Target IPs"},
                            },
                        },
                    },
                },
            },
            "vpn_gateway": {
                "type": "object",
                "title": "VPN Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable VPN Gateway", "default": False},
                    "type": {"type": "string", "title": "Type", "enum": ["ipsec.1"]},
                    "amazon_side_asn": {"type": "integer", "title": "Amazon Side ASN", "default": 65000},
                },
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Hub Network",
        "properties": {
            "hub_vnet": {
                "type": "object",
                "title": "Hub VNet",
                "properties": {
                    "name": {"type": "string", "title": "VNet Name"},
                    "cidr": {"type": "string", "title": "Address Space", "format": "cidr"},
                    "region": {"type": "string", "title": "Region", "description": "Azure region (e.g. eastus)"},
                },
            },
            "hub_subnets": {
                "type": "array",
                "title": "Hub Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "type": {"type": "string", "title": "Type", "enum": [
                            "default", "GatewaySubnet", "AzureFirewallSubnet",
                            "AzureBastionSubnet", "RouteServerSubnet",
                        ]},
                    },
                },
            },
            "azure_firewall": {
                "type": "object",
                "title": "Azure Firewall",
                "description": "Cloud-native network security",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Azure Firewall", "default": False},
                    "name": {"type": "string", "title": "Firewall Name"},
                    "sku_tier": {"type": "string", "title": "SKU Tier", "enum": ["Standard", "Premium", "Basic"]},
                    "threat_intel_mode": {"type": "string", "title": "Threat Intel Mode", "enum": ["Off", "Alert", "Deny"]},
                },
            },
            "gateway": {
                "type": "object",
                "title": "Virtual Network Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Gateway", "default": False},
                    "type": {"type": "string", "title": "Type", "enum": ["Vpn", "ExpressRoute"]},
                    "sku": {"type": "string", "title": "SKU", "enum": [
                        "VpnGw1", "VpnGw2", "VpnGw3", "VpnGw4", "VpnGw5",
                        "ErGw1AZ", "ErGw2AZ", "ErGw3AZ",
                    ]},
                    "vpn_type": {"type": "string", "title": "VPN Type", "enum": ["RouteBased", "PolicyBased"]},
                },
            },
            "private_dns_zones": {
                "type": "array",
                "title": "Private DNS Zones",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Zone Name"},
                        "auto_registration": {"type": "boolean", "title": "Auto Registration", "default": False},
                    },
                },
            },
            "bastion_host": {
                "type": "object",
                "title": "Bastion Host",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Bastion", "default": False},
                    "sku": {"type": "string", "title": "SKU", "enum": ["Basic", "Standard"]},
                },
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Hub Network",
        "properties": {
            "shared_vpc": {
                "type": "object",
                "title": "Shared VPC",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Shared VPC", "default": True},
                    "host_project_name": {"type": "string", "title": "Host Project Name"},
                },
            },
            "vpc_network": {
                "type": "object",
                "title": "VPC Network",
                "properties": {
                    "name": {"type": "string", "title": "Network Name"},
                    "routing_mode": {"type": "string", "title": "Routing Mode", "enum": ["REGIONAL", "GLOBAL"], "default": "GLOBAL"},
                    "auto_create_subnetworks": {"type": "boolean", "title": "Auto-Create Subnets", "default": False},
                    "mtu": {"type": "integer", "title": "MTU", "default": 1460},
                },
            },
            "hub_subnets": {
                "type": "array",
                "title": "Hub Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "region": {"type": "string", "title": "Region"},
                        "private_google_access": {"type": "boolean", "title": "Private Google Access", "default": True},
                    },
                },
            },
            "cloud_nat": {
                "type": "object",
                "title": "Cloud NAT",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Cloud NAT", "default": True},
                    "router_name": {"type": "string", "title": "Cloud Router Name"},
                    "min_ports_per_vm": {"type": "integer", "title": "Min Ports Per VM", "default": 64},
                    "log_config_enabled": {"type": "boolean", "title": "Enable Logging", "default": True},
                },
            },
            "cloud_dns": {
                "type": "object",
                "title": "Cloud DNS",
                "properties": {
                    "managed_zones": {
                        "type": "array",
                        "title": "Managed Zones",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "title": "Zone Name"},
                                "dns_name": {"type": "string", "title": "DNS Name"},
                                "visibility": {"type": "string", "title": "Visibility", "enum": ["private", "public"]},
                            },
                        },
                    },
                },
            },
            "interconnect": {
                "type": "object",
                "title": "Interconnect",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Interconnect", "default": False},
                    "type": {"type": "string", "title": "Type", "enum": [
                        "ha_vpn", "classic_vpn", "dedicated_interconnect", "partner_interconnect",
                    ]},
                },
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Hub Network",
        "properties": {
            "drg": {
                "type": "object",
                "title": "Dynamic Routing Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable DRG", "default": True},
                    "display_name": {"type": "string", "title": "Display Name"},
                },
            },
            "hub_vcn": {
                "type": "object",
                "title": "Hub VCN",
                "properties": {
                    "display_name": {"type": "string", "title": "Display Name"},
                    "cidr_blocks": {"type": "array", "items": {"type": "string"}, "title": "CIDR Blocks"},
                    "dns_label": {"type": "string", "title": "DNS Label"},
                },
            },
            "hub_subnets": {
                "type": "array",
                "title": "Hub Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "display_name": {"type": "string", "title": "Display Name"},
                        "cidr_block": {"type": "string", "title": "CIDR Block", "format": "cidr"},
                        "type": {"type": "string", "title": "Type", "enum": ["public", "private"]},
                        "dns_label": {"type": "string", "title": "DNS Label"},
                    },
                },
            },
            "service_gateway": {
                "type": "object",
                "title": "Service Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Service Gateway", "default": True},
                },
            },
            "nat_gateway": {
                "type": "object",
                "title": "NAT Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable NAT Gateway", "default": True},
                    "block_traffic": {"type": "boolean", "title": "Block Traffic", "default": False},
                },
            },
            "internet_gateway": {
                "type": "object",
                "title": "Internet Gateway",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Internet Gateway", "default": True},
                },
            },
            "dns_resolver": {
                "type": "object",
                "title": "DNS Resolver",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable DNS Resolver", "default": False},
                },
            },
        },
    },
}

FOUNDATION_IAM_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Organization Policies",
        "properties": {
            "realm": {
                "type": "object",
                "title": "Authentication Realm",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Configure Realm", "default": False},
                    "type": {"type": "string", "title": "Realm Type", "enum": ["pam", "pve", "ldap", "ad"]},
                    "server": {"type": "string", "title": "Server", "description": "LDAP/AD server address"},
                    "base_dn": {"type": "string", "title": "Base DN", "description": "LDAP base DN"},
                },
            },
            "resource_pools": {
                "type": "array",
                "title": "Resource Pools",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Pool Name"},
                        "comment": {"type": "string", "title": "Comment"},
                    },
                },
            },
            "api_token_expiry_days": {
                "type": "integer",
                "title": "Token Expiry (days)",
                "description": "Default API token expiration in days (0 = never)",
                "default": 90,
            },
            "enforce_2fa": {
                "type": "boolean",
                "title": "Enforce 2FA",
                "description": "Require two-factor authentication for all users",
                "default": False,
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Organization Policies",
        "properties": {
            "password_policy": {
                "type": "object",
                "title": "Password Policy",
                "properties": {
                    "min_length": {"type": "integer", "title": "Min Length", "default": 14},
                    "require_uppercase": {"type": "boolean", "title": "Require Uppercase", "default": True},
                    "require_numbers": {"type": "boolean", "title": "Require Numbers", "default": True},
                    "require_symbols": {"type": "boolean", "title": "Require Symbols", "default": True},
                    "max_age_days": {"type": "integer", "title": "Max Age (days)", "default": 90},
                    "history_count": {"type": "integer", "title": "History Count", "default": 12},
                },
            },
            "enforce_mfa": {
                "type": "boolean",
                "title": "Enforce MFA",
                "description": "Require MFA for all IAM users",
                "default": True,
            },
            "permissions_boundary": {
                "type": "object",
                "title": "Permissions Boundary",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Permissions Boundary", "default": False},
                    "policy_name": {"type": "string", "title": "Policy Name"},
                    "policy_statements": {
                        "type": "array",
                        "title": "Policy Statements",
                        "items": {
                            "type": "object",
                            "properties": {
                                "effect": {"type": "string", "title": "Effect", "enum": ["Allow", "Deny"]},
                                "actions": {"type": "array", "items": {"type": "string"}, "title": "Actions"},
                                "resources": {"type": "array", "items": {"type": "string"}, "title": "Resources"},
                            },
                        },
                    },
                },
            },
            "scps": {
                "type": "array",
                "title": "Service Control Policies",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                        "effect": {"type": "string", "title": "Effect", "enum": ["Allow", "Deny"]},
                        "actions": {"type": "array", "items": {"type": "string"}, "title": "Actions"},
                        "resources": {"type": "array", "items": {"type": "string"}, "title": "Resources"},
                    },
                },
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Organization Policies",
        "properties": {
            "management_group": {
                "type": "object",
                "title": "Management Group",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Create Management Group", "default": False},
                    "display_name": {"type": "string", "title": "Display Name"},
                },
            },
            "custom_roles": {
                "type": "array",
                "title": "Custom Roles",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Role Name"},
                        "description": {"type": "string", "title": "Description"},
                        "permissions": {"type": "array", "items": {"type": "string"}, "title": "Permissions"},
                        "not_actions": {"type": "array", "items": {"type": "string"}, "title": "Not Actions"},
                    },
                },
            },
            "pim": {
                "type": "object",
                "title": "Privileged Identity Management",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable PIM", "default": False},
                    "require_justification": {"type": "boolean", "title": "Require Justification", "default": True},
                    "require_approval": {"type": "boolean", "title": "Require Approval", "default": True},
                    "max_duration_hours": {"type": "integer", "title": "Max Duration (hours)", "default": 8},
                },
            },
            "conditional_access": {
                "type": "object",
                "title": "Conditional Access",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Conditional Access", "default": False},
                    "require_mfa": {"type": "boolean", "title": "Require MFA", "default": True},
                    "block_legacy_auth": {"type": "boolean", "title": "Block Legacy Auth", "default": True},
                    "require_compliant_device": {"type": "boolean", "title": "Require Compliant Device", "default": False},
                },
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Organization Policies",
        "properties": {
            "org_id": {
                "type": "string",
                "title": "Organization ID",
                "description": "GCP organization numeric ID (required to target the org)",
            },
            "org_policies": {
                "type": "array",
                "title": "Organization Policies",
                "items": {
                    "type": "object",
                    "properties": {
                        "constraint": {"type": "string", "title": "Constraint"},
                        "enforcement": {"type": "string", "title": "Enforcement", "enum": ["enforce", "deny_all", "allow_all"]},
                    },
                },
            },
            "workload_identity_pool": {
                "type": "object",
                "title": "Workload Identity Pool",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Pool", "default": False},
                    "display_name": {"type": "string", "title": "Display Name"},
                },
            },
            "custom_roles": {
                "type": "array",
                "title": "Custom Roles",
                "items": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "title": "Role ID"},
                        "title": {"type": "string", "title": "Title"},
                        "permissions": {"type": "array", "items": {"type": "string"}, "title": "Permissions"},
                    },
                },
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Organization Policies",
        "properties": {
            "compartments": {
                "type": "array",
                "title": "Compartments",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                        "parent": {"type": "string", "title": "Parent Compartment"},
                    },
                },
            },
            "policies": {
                "type": "array",
                "title": "IAM Policies",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Policy Name"},
                        "compartment": {"type": "string", "title": "Compartment"},
                        "statements": {"type": "array", "items": {"type": "string"}, "title": "Statements"},
                    },
                },
            },
            "dynamic_groups": {
                "type": "array",
                "title": "Dynamic Groups",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                        "matching_rule": {"type": "string", "title": "Matching Rule"},
                    },
                },
            },
        },
    },
}

FOUNDATION_SECURITY_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Shared Services",
        "properties": {
            "firewall_enabled": {
                "type": "boolean",
                "title": "Firewall",
                "description": "Enable Proxmox firewall by default on new VMs",
                "default": True,
            },
            "default_firewall_rules": {
                "type": "array",
                "title": "Default Firewall Rules",
                "description": "Default firewall rules applied to new VMs",
                "items": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["IN", "OUT"], "title": "Direction"},
                        "action": {"type": "string", "enum": ["ACCEPT", "DROP", "REJECT"], "title": "Action"},
                        "source": {"type": "string", "title": "Source"},
                        "dest": {"type": "string", "title": "Destination"},
                        "proto": {"type": "string", "title": "Protocol"},
                        "dport": {"type": "string", "title": "Dest Port"},
                        "comment": {"type": "string", "title": "Comment"},
                    },
                },
            },
            "backup_jobs": {
                "type": "array",
                "title": "Backup Jobs",
                "items": {
                    "type": "object",
                    "properties": {
                        "schedule": {"type": "string", "title": "Schedule", "description": "Cron format (e.g. 0 2 * * *)"},
                        "storage": {"type": "string", "title": "Storage Target"},
                        "mode": {"type": "string", "title": "Mode", "enum": ["snapshot", "suspend", "stop"]},
                        "compress": {"type": "string", "title": "Compression", "enum": ["none", "lzo", "gzip", "zstd"]},
                        "mailnotification": {"type": "string", "title": "Notification", "enum": ["always", "failure"]},
                    },
                },
            },
            "storage_config": {
                "type": "array",
                "title": "Storage Configuration",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "type": {"type": "string", "title": "Type", "enum": ["dir", "nfs", "cifs", "zfspool", "lvm", "lvmthin", "ceph"]},
                        "path": {"type": "string", "title": "Path"},
                        "content_types": {"type": "array", "items": {"type": "string"}, "title": "Content Types"},
                    },
                },
            },
            "ha_groups": {
                "type": "array",
                "title": "HA Groups",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "nodes": {"type": "array", "items": {"type": "string"}, "title": "Nodes"},
                        "restricted": {"type": "boolean", "title": "Restricted", "default": False},
                    },
                },
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Shared Services",
        "properties": {
            "central_logging_bucket": {
                "type": "object",
                "title": "Central Logging Bucket",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Central Logging", "default": True},
                    "bucket_name_prefix": {"type": "string", "title": "Bucket Name Prefix"},
                    "lifecycle_days": {"type": "integer", "title": "Lifecycle (days)", "default": 365},
                    "glacier_days": {"type": "integer", "title": "Glacier Transition (days)", "default": 90},
                },
            },
            "cloudtrail": {
                "type": "object",
                "title": "CloudTrail",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable CloudTrail", "default": True},
                    "trail_name": {"type": "string", "title": "Trail Name"},
                    "is_multi_region": {"type": "boolean", "title": "Multi-Region", "default": True},
                    "enable_log_file_validation": {"type": "boolean", "title": "Log File Validation", "default": True},
                    "include_global_events": {"type": "boolean", "title": "Global Service Events", "default": True},
                },
            },
            "guardduty": {
                "type": "object",
                "title": "GuardDuty",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable GuardDuty", "default": True},
                    "auto_enable_org_members": {"type": "boolean", "title": "Auto-Enable for Org Members", "default": True},
                    "enable_s3_protection": {"type": "boolean", "title": "S3 Protection", "default": True},
                    "enable_eks_protection": {"type": "boolean", "title": "EKS Protection", "default": False},
                },
            },
            "aws_config": {
                "type": "object",
                "title": "AWS Config",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable AWS Config", "default": True},
                    "include_global_resources": {"type": "boolean", "title": "Include Global Resources", "default": True},
                },
            },
            "kms_keys": {
                "type": "array",
                "title": "KMS Keys",
                "items": {
                    "type": "object",
                    "properties": {
                        "alias": {"type": "string", "title": "Alias"},
                        "description": {"type": "string", "title": "Description"},
                        "key_usage": {"type": "string", "title": "Key Usage", "enum": ["ENCRYPT_DECRYPT", "SIGN_VERIFY"]},
                        "enable_key_rotation": {"type": "boolean", "title": "Key Rotation", "default": True},
                    },
                },
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Shared Services",
        "properties": {
            "log_analytics_workspace": {
                "type": "object",
                "title": "Log Analytics Workspace",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Log Analytics", "default": True},
                    "name": {"type": "string", "title": "Workspace Name"},
                    "sku": {"type": "string", "title": "SKU", "enum": ["Free", "PerGB2018", "Standalone", "PerNode"]},
                    "retention_days": {"type": "integer", "title": "Retention (days)", "default": 90},
                },
            },
            "defender": {
                "type": "object",
                "title": "Microsoft Defender",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Defender", "default": True},
                    "plans": {"type": "array", "items": {"type": "string"}, "title": "Defender Plans",
                              "description": "e.g. VirtualMachines, SqlServers, AppServices, StorageAccounts"},
                },
            },
            "sentinel": {
                "type": "object",
                "title": "Azure Sentinel",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Sentinel", "default": False},
                    "data_connectors": {"type": "array", "items": {"type": "string"}, "title": "Data Connectors",
                                         "description": "e.g. AzureActiveDirectory, Office365, ThreatIntelligence"},
                },
            },
            "diagnostics_storage": {
                "type": "object",
                "title": "Diagnostics Storage",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Diagnostics Storage", "default": False},
                    "name": {"type": "string", "title": "Storage Account Name"},
                    "sku": {"type": "string", "title": "SKU", "enum": ["Standard_LRS", "Standard_GRS", "Standard_ZRS"]},
                },
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Shared Services",
        "properties": {
            "org_log_sink": {
                "type": "object",
                "title": "Organization Log Sink",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Org Log Sink", "default": True},
                    "destination_type": {"type": "string", "title": "Destination Type", "enum": ["bigquery", "storage", "pubsub"]},
                    "bucket_name": {"type": "string", "title": "Bucket/Dataset Name"},
                    "filter": {"type": "string", "title": "Log Filter"},
                },
            },
            "security_command_center": {
                "type": "object",
                "title": "Security Command Center",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable SCC", "default": True},
                    "tier": {"type": "string", "title": "Tier", "enum": ["STANDARD", "PREMIUM"]},
                },
            },
            "vpc_service_controls": {
                "type": "object",
                "title": "VPC Service Controls",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable VPC-SC", "default": False},
                    "perimeter_name": {"type": "string", "title": "Perimeter Name"},
                },
            },
            "access_transparency": {
                "type": "boolean",
                "title": "Access Transparency",
                "description": "Enable Access Transparency logging",
                "default": False,
            },
            "kms": {
                "type": "object",
                "title": "Cloud KMS",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable KMS", "default": False},
                    "keyring_name": {"type": "string", "title": "Key Ring Name"},
                    "location": {"type": "string", "title": "Location"},
                },
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Shared Services",
        "properties": {
            "cloud_guard": {
                "type": "object",
                "title": "Cloud Guard",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Cloud Guard", "default": True},
                    "reporting_region": {"type": "string", "title": "Reporting Region"},
                },
            },
            "audit_bucket": {
                "type": "object",
                "title": "Audit Bucket",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Audit Bucket", "default": True},
                    "bucket_name": {"type": "string", "title": "Bucket Name"},
                    "compartment_name": {"type": "string", "title": "Compartment Name"},
                },
            },
            "vault": {
                "type": "object",
                "title": "OCI Vault",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Vault", "default": False},
                    "display_name": {"type": "string", "title": "Display Name"},
                    "vault_type": {"type": "string", "title": "Vault Type", "enum": ["DEFAULT", "VIRTUAL_PRIVATE"]},
                },
            },
            "notifications": {
                "type": "object",
                "title": "Notifications",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Notifications", "default": False},
                    "topic_name": {"type": "string", "title": "Topic Name"},
                    "subscription_email": {"type": "string", "title": "Subscription Email"},
                },
            },
            "events_rules": {
                "type": "array",
                "title": "Events Rules",
                "items": {
                    "type": "object",
                    "properties": {
                        "display_name": {"type": "string", "title": "Display Name"},
                        "condition": {"type": "string", "title": "Condition"},
                        "is_enabled": {"type": "boolean", "title": "Enabled", "default": True},
                    },
                },
            },
        },
    },
}

# Backward-compatible aliases (old names point to foundation schemas)
NETWORK_CONFIG_SCHEMAS = FOUNDATION_NETWORK_SCHEMAS
IAM_CONFIG_SCHEMAS = FOUNDATION_IAM_SCHEMAS
SECURITY_CONFIG_SCHEMAS = FOUNDATION_SECURITY_SCHEMAS


# ==========================================================================
# Environment schemas — per-environment spoke/access/security/monitoring
# ==========================================================================

ENV_NETWORK_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Environment Network",
        "properties": {
            "vlan_id": {
                "type": "integer",
                "title": "VLAN ID",
                "description": "Dedicated VLAN for this environment",
            },
            "bridge_override": {
                "type": "string",
                "title": "Bridge Override",
                "description": "Override the default bridge for this environment",
            },
            "ip_pool_cidr": {
                "type": "string",
                "title": "IP Pool CIDR",
                "format": "cidr",
                "description": "IP address pool for VMs in this environment",
                "placeholder": "10.1.0.0/24",
            },
            "subnets": {
                "type": "array",
                "title": "Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "gateway": {"type": "string", "title": "Gateway"},
                    },
                },
                "description": "Subnet definitions for this environment",
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Spoke Network",
        "properties": {
            "vpc_cidr": {
                "type": "string",
                "title": "VPC CIDR",
                "format": "cidr",
                "description": "Primary VPC CIDR block for this environment",
                "placeholder": "10.1.0.0/16",
            },
            "availability_zones": {
                "type": "array",
                "items": {"type": "string"},
                "title": "Availability Zones",
                "description": "AZs to use (e.g. us-east-1a, us-east-1b)",
            },
            "enable_dns_hostnames": {
                "type": "boolean",
                "title": "DNS Hostnames",
                "description": "Enable DNS hostnames in VPC",
                "default": True,
            },
            "enable_nat_gateway": {
                "type": "boolean",
                "title": "NAT Gateway",
                "description": "Deploy NAT gateway for private subnets",
                "default": True,
            },
            "subnets": {
                "type": "array",
                "title": "Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "az": {"type": "string", "title": "Availability Zone"},
                        "type": {"type": "string", "title": "Type", "enum": ["public", "private", "isolated"]},
                    },
                },
                "description": "Subnet definitions for this environment",
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Spoke Network",
        "properties": {
            "vnet_cidr": {
                "type": "string",
                "title": "VNet CIDR",
                "format": "cidr",
                "description": "Spoke virtual network address space",
                "placeholder": "10.1.0.0/16",
            },
            "dns_servers": {
                "type": "array",
                "items": {"type": "string"},
                "title": "DNS Servers",
                "description": "Custom DNS servers (empty = Azure-provided)",
            },
            "enable_ddos_protection": {
                "type": "boolean",
                "title": "DDoS Protection",
                "description": "Enable Azure DDoS Protection Standard",
                "default": False,
            },
            "subnets": {
                "type": "array",
                "title": "Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "service_endpoints": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Service Endpoints",
                        },
                    },
                },
                "description": "Subnet definitions for this spoke",
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Environment Network",
        "properties": {
            "vpc_cidr": {
                "type": "string",
                "title": "Primary Range CIDR",
                "format": "cidr",
                "description": "Primary IP range for the environment subnet",
                "placeholder": "10.1.0.0/16",
            },
            "subnets": {
                "type": "array",
                "title": "Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "region": {"type": "string", "title": "Region"},
                        "private_google_access": {"type": "boolean", "title": "Private Google Access", "default": True},
                    },
                },
                "description": "Subnet definitions for this environment",
            },
            "enable_private_google_access": {
                "type": "boolean",
                "title": "Private Google Access",
                "description": "Enable private access to Google APIs",
                "default": True,
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Environment Network",
        "properties": {
            "vcn_cidr": {
                "type": "string",
                "title": "VCN CIDR",
                "format": "cidr",
                "description": "Spoke VCN CIDR block",
                "placeholder": "10.1.0.0/16",
            },
            "dns_label": {
                "type": "string",
                "title": "DNS Label",
                "description": "DNS label for the VCN",
                "placeholder": "envdev",
            },
            "subnets": {
                "type": "array",
                "title": "Subnets",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "cidr": {"type": "string", "title": "CIDR", "format": "cidr"},
                        "type": {"type": "string", "title": "Type", "enum": ["public", "private"]},
                        "security_list": {"type": "string", "title": "Security List"},
                    },
                },
                "description": "Subnet definitions",
            },
            "enable_internet_gateway": {
                "type": "boolean",
                "title": "Internet Gateway",
                "description": "Create an internet gateway",
                "default": True,
            },
            "enable_nat_gateway": {
                "type": "boolean",
                "title": "NAT Gateway",
                "description": "Create a NAT gateway for private subnets",
                "default": True,
            },
        },
    },
}

ENV_IAM_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Environment Access",
        "properties": {
            "pool_name": {
                "type": "string",
                "title": "Resource Pool",
                "description": "Proxmox resource pool for this environment",
            },
            "acl_entries": {
                "type": "array",
                "title": "ACL Entries",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "title": "Path"},
                        "role": {"type": "string", "title": "Role"},
                        "propagate": {"type": "boolean", "title": "Propagate", "default": True},
                    },
                },
                "description": "Access control list entries for this environment",
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Environment Access Control",
        "properties": {
            "iam_roles": {
                "type": "array",
                "title": "IAM Roles",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Role Name"},
                        "description": {"type": "string", "title": "Description"},
                        "managed_policy_names": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Managed Policy Names",
                            "description": "AWS-managed policy names (e.g. ReadOnlyAccess, PowerUserAccess)",
                        },
                        "inline_policies": {
                            "type": "array",
                            "title": "Inline Policies",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "title": "Policy Name"},
                                    "effect": {"type": "string", "title": "Effect", "enum": ["Allow", "Deny"]},
                                    "actions": {"type": "array", "items": {"type": "string"}, "title": "Actions"},
                                    "resources": {"type": "array", "items": {"type": "string"}, "title": "Resources"},
                                },
                            },
                        },
                    },
                },
                "description": "IAM roles to create in this environment",
            },
            "service_accounts": {
                "type": "array",
                "title": "Service Accounts",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                    },
                },
                "description": "Service accounts for workloads in this environment",
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Environment Access Control",
        "properties": {
            "role_assignments": {
                "type": "array",
                "title": "Role Assignments",
                "items": {
                    "type": "object",
                    "properties": {
                        "principal_name": {"type": "string", "title": "Principal Name"},
                        "role_definition": {"type": "string", "title": "Role Definition"},
                        "scope": {"type": "string", "title": "Scope"},
                    },
                },
                "description": "Azure role assignments for this environment",
            },
            "managed_identities": {
                "type": "array",
                "title": "Managed Identities",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "type": {"type": "string", "title": "Type", "enum": ["user_assigned", "system_assigned"]},
                    },
                },
                "description": "Managed identities for workloads",
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Environment Access Control",
        "properties": {
            "iam_bindings": {
                "type": "array",
                "title": "IAM Bindings",
                "items": {
                    "type": "object",
                    "properties": {
                        "member": {"type": "string", "title": "Member"},
                        "role": {"type": "string", "title": "Role"},
                    },
                },
                "description": "IAM bindings for this environment",
            },
            "service_accounts": {
                "type": "array",
                "title": "Service Accounts",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                        "roles": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Roles",
                        },
                    },
                },
                "description": "Service accounts for workloads",
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Environment Access Control",
        "properties": {
            "compartment_policies": {
                "type": "array",
                "title": "Compartment Policies",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Policy Name"},
                        "statements": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Statements",
                        },
                    },
                },
                "description": "IAM policies for this environment's compartment",
            },
            "instance_principals": {
                "type": "array",
                "title": "Instance Principals",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "matching_rules": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Matching Rules",
                        },
                    },
                },
                "description": "Dynamic group instance principals",
            },
        },
    },
}

ENV_SECURITY_SCHEMAS: dict[str, dict] = {
    "proxmox": {
        "type": "object",
        "title": "Proxmox Environment Security",
        "properties": {
            "firewall_rules": {
                "type": "array",
                "title": "Firewall Rules",
                "items": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["IN", "OUT"], "title": "Direction"},
                        "action": {"type": "string", "enum": ["ACCEPT", "DROP", "REJECT"], "title": "Action"},
                        "source": {"type": "string", "title": "Source"},
                        "dest": {"type": "string", "title": "Destination"},
                        "proto": {"type": "string", "title": "Protocol"},
                        "dport": {"type": "string", "title": "Dest Port"},
                    },
                },
                "description": "Firewall rules for this environment",
            },
            "backup_schedule": {
                "type": "string",
                "title": "Backup Schedule",
                "description": "Backup schedule override (cron format)",
                "placeholder": "0 3 * * *",
            },
            "backup_storage": {
                "type": "string",
                "title": "Backup Storage",
                "description": "Storage target for backups",
            },
        },
    },
    "aws": {
        "type": "object",
        "title": "AWS Environment Security",
        "properties": {
            "security_groups": {
                "type": "array",
                "title": "Security Groups",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "description": {"type": "string", "title": "Description"},
                        "inbound_rules": {
                            "type": "array",
                            "title": "Inbound Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "protocol": {"type": "string", "title": "Protocol", "enum": ["tcp", "udp", "icmp", "-1"]},
                                    "port_range": {"type": "string", "title": "Port Range", "placeholder": "443"},
                                    "source": {"type": "string", "title": "Source CIDR", "placeholder": "0.0.0.0/0"},
                                    "description": {"type": "string", "title": "Description"},
                                },
                            },
                        },
                        "outbound_rules": {
                            "type": "array",
                            "title": "Outbound Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "protocol": {"type": "string", "title": "Protocol", "enum": ["tcp", "udp", "icmp", "-1"]},
                                    "port_range": {"type": "string", "title": "Port Range"},
                                    "destination": {"type": "string", "title": "Dest CIDR", "placeholder": "0.0.0.0/0"},
                                    "description": {"type": "string", "title": "Description"},
                                },
                            },
                        },
                    },
                },
                "description": "Security groups for this environment",
            },
            "kms_key_alias": {
                "type": "string",
                "title": "KMS Key Alias",
                "description": "KMS key alias for this environment's encryption",
                "placeholder": "alias/env-key",
            },
            "default_encryption": {
                "type": "string",
                "title": "Default Encryption",
                "enum": ["aws:kms", "AES256"],
                "description": "Default encryption type for storage",
                "default": "aws:kms",
            },
            "s3_block_public_access": {
                "type": "boolean",
                "title": "S3 Block Public Access",
                "description": "Block public access on all S3 buckets",
                "default": True,
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Environment Security",
        "properties": {
            "nsgs": {
                "type": "array",
                "title": "Network Security Groups",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "NSG Name"},
                        "inbound_rules": {
                            "type": "array",
                            "title": "Inbound Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "priority": {"type": "integer", "title": "Priority"},
                                    "direction": {"type": "string", "title": "Direction", "default": "Inbound"},
                                    "access": {"type": "string", "title": "Access", "enum": ["Allow", "Deny"]},
                                    "protocol": {"type": "string", "title": "Protocol", "enum": ["Tcp", "Udp", "Icmp", "*"]},
                                    "source_range": {"type": "string", "title": "Source Range"},
                                    "dest_port_range": {"type": "string", "title": "Dest Port Range"},
                                    "description": {"type": "string", "title": "Description"},
                                },
                            },
                        },
                        "outbound_rules": {
                            "type": "array",
                            "title": "Outbound Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "priority": {"type": "integer", "title": "Priority"},
                                    "access": {"type": "string", "title": "Access", "enum": ["Allow", "Deny"]},
                                    "protocol": {"type": "string", "title": "Protocol", "enum": ["Tcp", "Udp", "Icmp", "*"]},
                                    "source_range": {"type": "string", "title": "Source Range"},
                                    "dest_port_range": {"type": "string", "title": "Dest Port Range"},
                                    "description": {"type": "string", "title": "Description"},
                                },
                            },
                        },
                    },
                },
                "description": "NSGs for this environment",
            },
            "key_vault_name": {
                "type": "string",
                "title": "Key Vault Name",
                "description": "Azure Key Vault for this environment",
            },
            "enable_key_vault": {
                "type": "boolean",
                "title": "Enable Key Vault",
                "description": "Create a Key Vault for secrets management",
                "default": True,
            },
            "nsg_default_deny": {
                "type": "boolean",
                "title": "NSG Default Deny",
                "description": "Default deny all inbound on NSGs",
                "default": True,
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Environment Security",
        "properties": {
            "firewall_rules": {
                "type": "array",
                "title": "Firewall Rules",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "direction": {"type": "string", "title": "Direction", "enum": ["INGRESS", "EGRESS"]},
                        "priority": {"type": "integer", "title": "Priority", "default": 1000},
                        "source_ranges": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Source Ranges",
                        },
                        "target_tags": {
                            "type": "array", "items": {"type": "string"},
                            "title": "Target Tags",
                        },
                        "allowed": {
                            "type": "array",
                            "title": "Allowed",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "protocol": {"type": "string", "title": "Protocol"},
                                    "ports": {
                                        "type": "array", "items": {"type": "string"},
                                        "title": "Ports",
                                    },
                                },
                            },
                        },
                    },
                },
                "description": "VPC firewall rules for this environment",
            },
            "enable_vpc_flow_logs": {
                "type": "boolean",
                "title": "VPC Flow Logs",
                "description": "Enable VPC flow logs for all subnets",
                "default": True,
            },
            "enable_binary_authorization": {
                "type": "boolean",
                "title": "Binary Authorization",
                "description": "Enable Binary Authorization for GKE",
                "default": False,
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Environment Security",
        "properties": {
            "security_lists": {
                "type": "array",
                "title": "Security Lists",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "ingress_rules": {
                            "type": "array",
                            "title": "Ingress Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "protocol": {"type": "string", "title": "Protocol"},
                                    "source": {"type": "string", "title": "Source CIDR"},
                                    "tcp_options": {"type": "string", "title": "TCP Options"},
                                },
                            },
                        },
                        "egress_rules": {
                            "type": "array",
                            "title": "Egress Rules",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "protocol": {"type": "string", "title": "Protocol"},
                                    "destination": {"type": "string", "title": "Destination"},
                                },
                            },
                        },
                    },
                },
                "description": "Security lists for this environment",
            },
            "enable_vault": {
                "type": "boolean",
                "title": "OCI Vault",
                "description": "Create an OCI Vault for key management",
                "default": True,
            },
            "vault_name": {
                "type": "string",
                "title": "Vault Name",
                "description": "Name for the OCI Vault",
            },
            "security_list_default_deny": {
                "type": "boolean",
                "title": "Default Deny",
                "description": "Default deny all inbound on security lists",
                "default": True,
            },
        },
    },
}

ENV_MONITORING_SCHEMAS: dict[str, dict] = {
    "proxmox": None,  # Proxmox has no cloud-native monitoring config
    "aws": {
        "type": "object",
        "title": "AWS Environment Monitoring",
        "properties": {
            "budget_limit": {
                "type": "number",
                "title": "Budget Limit (USD)",
                "description": "Monthly budget limit for this environment",
            },
            "alert_email": {
                "type": "string",
                "title": "Alert Email",
                "description": "Email for budget and anomaly alerts",
            },
            "enable_cost_anomaly_detection": {
                "type": "boolean",
                "title": "Cost Anomaly Detection",
                "description": "Enable AWS Cost Anomaly Detection",
                "default": False,
            },
        },
    },
    "azure": {
        "type": "object",
        "title": "Azure Environment Monitoring",
        "properties": {
            "budget_limit": {
                "type": "number",
                "title": "Budget Limit (USD)",
                "description": "Monthly budget limit for this environment",
            },
            "action_group_email": {
                "type": "string",
                "title": "Action Group Email",
                "description": "Email for budget action group notifications",
            },
        },
    },
    "gcp": {
        "type": "object",
        "title": "GCP Environment Monitoring",
        "properties": {
            "budget_amount": {
                "type": "number",
                "title": "Budget Amount (USD)",
                "description": "Monthly budget amount for this environment",
            },
            "notification_channels": {
                "type": "array",
                "title": "Notification Channels",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "title": "Type", "enum": ["email", "slack", "pagerduty", "pubsub"]},
                        "display_name": {"type": "string", "title": "Display Name"},
                        "address": {"type": "string", "title": "Address", "description": "Email, Slack channel, PagerDuty key, or Pub/Sub topic"},
                    },
                },
                "description": "Notification channels for budget alerts",
            },
        },
    },
    "oci": {
        "type": "object",
        "title": "OCI Environment Monitoring",
        "properties": {
            "budget_amount": {
                "type": "number",
                "title": "Budget Amount (USD)",
                "description": "Monthly budget amount for this environment",
            },
            "alarm_topic": {
                "type": "object",
                "title": "Alarm Topic",
                "properties": {
                    "enabled": {"type": "boolean", "title": "Enable Alarm Topic", "default": False},
                    "name": {"type": "string", "title": "Topic Name"},
                    "subscription_email": {"type": "string", "title": "Subscription Email"},
                },
            },
        },
    },
}


# ==========================================================================
# Accessor functions
# ==========================================================================

def get_credential_schema(provider_name: str) -> dict | None:
    """Get the credential JSON Schema for a provider (case-insensitive)."""
    return CREDENTIAL_SCHEMAS.get(provider_name.lower())


def get_scope_schema(provider_name: str) -> dict | None:
    """Get the scope JSON Schema for a provider (case-insensitive)."""
    return SCOPE_SCHEMAS.get(provider_name.lower())


def get_iam_identity_schema(provider_name: str) -> dict | None:
    """Get the IAM identity JSON Schema for a provider (case-insensitive)."""
    return IAM_IDENTITY_SCHEMAS.get(provider_name.lower())


# Foundation schema accessors
def get_foundation_network_schema(provider_name: str) -> dict | None:
    """Get the foundation (hub) network config schema for a provider."""
    return FOUNDATION_NETWORK_SCHEMAS.get(provider_name.lower())


def get_foundation_iam_schema(provider_name: str) -> dict | None:
    """Get the foundation (org) IAM config schema for a provider."""
    return FOUNDATION_IAM_SCHEMAS.get(provider_name.lower())


def get_foundation_security_schema(provider_name: str) -> dict | None:
    """Get the foundation (shared services) security config schema for a provider."""
    return FOUNDATION_SECURITY_SCHEMAS.get(provider_name.lower())


# Environment schema accessors
def get_env_network_schema(provider_name: str) -> dict | None:
    """Get the environment (spoke) network config schema for a provider."""
    return ENV_NETWORK_SCHEMAS.get(provider_name.lower())


def get_env_iam_schema(provider_name: str) -> dict | None:
    """Get the environment access control schema for a provider."""
    return ENV_IAM_SCHEMAS.get(provider_name.lower())


def get_env_security_schema(provider_name: str) -> dict | None:
    """Get the environment security config schema for a provider."""
    return ENV_SECURITY_SCHEMAS.get(provider_name.lower())


def get_env_monitoring_schema(provider_name: str) -> dict | None:
    """Get the environment monitoring config schema for a provider."""
    return ENV_MONITORING_SCHEMAS.get(provider_name.lower())


# Backward-compatible aliases
get_network_config_schema = get_foundation_network_schema
get_iam_config_schema = get_foundation_iam_schema
get_security_config_schema = get_foundation_security_schema


def get_foundation_schemas(provider_name: str) -> dict[str, dict | None]:
    """Get all foundation schemas for a provider."""
    return {
        "network": get_foundation_network_schema(provider_name),
        "iam": get_foundation_iam_schema(provider_name),
        "security": get_foundation_security_schema(provider_name),
    }


def get_env_schemas(provider_name: str) -> dict[str, dict | None]:
    """Get all environment schemas for a provider."""
    return {
        "network": get_env_network_schema(provider_name),
        "iam": get_env_iam_schema(provider_name),
        "security": get_env_security_schema(provider_name),
        "monitoring": get_env_monitoring_schema(provider_name),
    }
