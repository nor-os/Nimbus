"""Seed enterprise demo data: backend regions, landing zones, environments, address spaces.

Creates a fully-linked enterprise setup so the full chain
CloudBackend -> BackendRegion -> LandingZone -> TenantEnvironment is exercised
with realistic configuration for all 5 providers.

Revision ID: 084
Revises: 083
Create Date: 2026-02-17
"""

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "084"
down_revision: Union[str, None] = "083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Pre-generated stable UUIDs ────────────────────────────────────────

# Backend regions (AWS)
REG_AWS_EUC1 = str(uuid.uuid4())
REG_AWS_EUW1 = str(uuid.uuid4())
REG_AWS_USE1 = str(uuid.uuid4())

# Backend regions (Azure)
REG_AZ_WESTEU = str(uuid.uuid4())
REG_AZ_NORTHEU = str(uuid.uuid4())
REG_AZ_GERMWC = str(uuid.uuid4())

# Backend regions (GCP)
REG_GCP_EUW1 = str(uuid.uuid4())
REG_GCP_EUW3 = str(uuid.uuid4())
REG_GCP_USC1 = str(uuid.uuid4())

# Backend regions (OCI)
REG_OCI_FRA = str(uuid.uuid4())
REG_OCI_AMS = str(uuid.uuid4())
REG_OCI_LON = str(uuid.uuid4())

# Backend regions (Proxmox)
REG_PVE_DC1 = str(uuid.uuid4())
REG_PVE_DC2 = str(uuid.uuid4())

# Landing zones
LZ_AWS = str(uuid.uuid4())
LZ_AZURE = str(uuid.uuid4())
LZ_GCP = str(uuid.uuid4())
LZ_OCI = str(uuid.uuid4())
LZ_PVE = str(uuid.uuid4())

# Environments (AWS)
ENV_AWS_DEV = str(uuid.uuid4())
ENV_AWS_STAGING = str(uuid.uuid4())
ENV_AWS_PROD = str(uuid.uuid4())
ENV_AWS_DR = str(uuid.uuid4())

# Environments (Azure)
ENV_AZ_DEV = str(uuid.uuid4())
ENV_AZ_STAGING = str(uuid.uuid4())
ENV_AZ_PROD = str(uuid.uuid4())

# Environments (GCP)
ENV_GCP_DEV = str(uuid.uuid4())
ENV_GCP_PROD = str(uuid.uuid4())

# Environments (OCI)
ENV_OCI_PROD = str(uuid.uuid4())
ENV_OCI_DR = str(uuid.uuid4())

# Address spaces
AS_AWS_HUB = str(uuid.uuid4())
AS_AWS_INSPECT = str(uuid.uuid4())
AS_AWS_SPOKE = str(uuid.uuid4())
AS_AZ_HUB = str(uuid.uuid4())
AS_AZ_SPOKE = str(uuid.uuid4())
AS_GCP_HUB = str(uuid.uuid4())
AS_GCP_SVC = str(uuid.uuid4())
AS_OCI_HUB = str(uuid.uuid4())
AS_OCI_SPOKE = str(uuid.uuid4())
AS_PVE_MGMT = str(uuid.uuid4())
AS_PVE_PROD = str(uuid.uuid4())
AS_PVE_DEV = str(uuid.uuid4())


def upgrade() -> None:
    conn = op.get_bind()

    # ── Resolve root tenant + first admin user ────────────────────────
    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if not row:
        return
    tid = str(row[0])

    user_row = conn.execute(
        sa.text("""
            SELECT u.id FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            WHERE r.name = 'Provider Admin' AND u.deleted_at IS NULL
            LIMIT 1
        """)
    ).fetchone()
    if not user_row:
        # Fallback: any active user
        user_row = conn.execute(
            sa.text("SELECT id FROM users WHERE deleted_at IS NULL LIMIT 1")
        ).fetchone()
    if not user_row:
        return
    uid = str(user_row[0])

    # ── Resolve cloud backends by name ────────────────────────────────
    backends = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM cloud_backends WHERE deleted_at IS NULL")
    ):
        backends[r[0]] = str(r[1])

    cb_aws = backends.get("AWS Production (eu-central-1)")
    cb_azure = backends.get("Azure Enterprise (West Europe)")
    cb_gcp = backends.get("GCP Analytics (europe-west1)")
    cb_oci = backends.get("OCI Database (eu-frankfurt-1)")
    cb_pve = backends.get("Proxmox Lab Cluster")

    if not all([cb_aws, cb_azure, cb_gcp, cb_oci, cb_pve]):
        return

    # ══════════════════════════════════════════════════════════════════
    # 1. BACKEND REGIONS
    # ══════════════════════════════════════════════════════════════════

    def _insert_region(reg_id, backend_id, identifier, display, code, azs):
        conn.execute(
            sa.text("""
                INSERT INTO backend_regions
                    (id, tenant_id, backend_id, region_identifier, display_name,
                     provider_region_code, is_enabled, availability_zones,
                     created_at, updated_at)
                VALUES (:id, :tid, :bid, :ident, :display,
                        :code, true, :azs,
                        now(), now())
                ON CONFLICT DO NOTHING
            """),
            {"id": reg_id, "tid": tid, "bid": backend_id, "ident": identifier,
             "display": display, "code": code, "azs": json.dumps(azs)},
        )

    # AWS regions
    _insert_region(REG_AWS_EUC1, cb_aws, "eu-central-1", "Europe (Frankfurt)", "eu-central-1",
                   ["eu-central-1a", "eu-central-1b", "eu-central-1c"])
    _insert_region(REG_AWS_EUW1, cb_aws, "eu-west-1", "Europe (Ireland)", "eu-west-1",
                   ["eu-west-1a", "eu-west-1b", "eu-west-1c"])
    _insert_region(REG_AWS_USE1, cb_aws, "us-east-1", "US East (N. Virginia)", "us-east-1",
                   ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d", "us-east-1e", "us-east-1f"])

    # Azure regions
    _insert_region(REG_AZ_WESTEU, cb_azure, "westeurope", "West Europe (Netherlands)", "westeurope",
                   ["1", "2", "3"])
    _insert_region(REG_AZ_NORTHEU, cb_azure, "northeurope", "North Europe (Ireland)", "northeurope",
                   ["1", "2", "3"])
    _insert_region(REG_AZ_GERMWC, cb_azure, "germanywestcentral", "Germany West Central (Frankfurt)", "germanywestcentral",
                   ["1", "2", "3"])

    # GCP regions
    _insert_region(REG_GCP_EUW1, cb_gcp, "europe-west1", "Europe West 1 (Belgium)", "europe-west1",
                   ["europe-west1-b", "europe-west1-c", "europe-west1-d"])
    _insert_region(REG_GCP_EUW3, cb_gcp, "europe-west3", "Europe West 3 (Frankfurt)", "europe-west3",
                   ["europe-west3-a", "europe-west3-b", "europe-west3-c"])
    _insert_region(REG_GCP_USC1, cb_gcp, "us-central1", "US Central 1 (Iowa)", "us-central1",
                   ["us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f"])

    # OCI regions
    _insert_region(REG_OCI_FRA, cb_oci, "eu-frankfurt-1", "EU Frankfurt", "eu-frankfurt-1",
                   ["XHZJ:EU-FRANKFURT-1-AD-1", "XHZJ:EU-FRANKFURT-1-AD-2", "XHZJ:EU-FRANKFURT-1-AD-3"])
    _insert_region(REG_OCI_AMS, cb_oci, "eu-amsterdam-1", "EU Amsterdam", "eu-amsterdam-1",
                   ["XHZJ:EU-AMSTERDAM-1-AD-1"])
    _insert_region(REG_OCI_LON, cb_oci, "uk-london-1", "UK London", "uk-london-1",
                   ["XHZJ:UK-LONDON-1-AD-1"])

    # Proxmox "regions" (datacenters)
    _insert_region(REG_PVE_DC1, cb_pve, "dc1", "Primary Datacenter", "dc1",
                   ["rack-a", "rack-b"])
    _insert_region(REG_PVE_DC2, cb_pve, "dc2", "DR Datacenter", "dc2",
                   ["rack-a"])

    # ══════════════════════════════════════════════════════════════════
    # 2. SCOPE_CONFIG on each backend
    # ══════════════════════════════════════════════════════════════════

    def _set_scope(backend_id, scope):
        conn.execute(
            sa.text("UPDATE cloud_backends SET scope_config = :scope WHERE id = :bid"),
            {"bid": backend_id, "scope": json.dumps(scope)},
        )

    _set_scope(cb_aws, {
        "account_id": "123456789012",
        "regions": ["eu-central-1", "eu-west-1", "us-east-1"],
        "organization_id": "o-abc123def4",
        "sso_start_url": "https://nimbus-demo.awsapps.com/start",
    })
    _set_scope(cb_azure, {
        "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "subscription_ids": ["sub-prod-001", "sub-dev-001", "sub-conn-001"],
        "regions": ["westeurope", "northeurope", "germanywestcentral"],
        "management_group": "mg-nimbus-root",
    })
    _set_scope(cb_gcp, {
        "organization_id": "987654321",
        "billing_account": "012345-6789AB-CDEF01",
        "regions": ["europe-west1", "europe-west3", "us-central1"],
        "folder_id": "folders/123456789",
    })
    _set_scope(cb_oci, {
        "tenancy_ocid": "ocid1.tenancy.oc1..aaaaaaaaexample",
        "regions": ["eu-frankfurt-1", "eu-amsterdam-1", "uk-london-1"],
        "compartment_ocid": "ocid1.compartment.oc1..aaaaaaaaexample",
    })
    _set_scope(cb_pve, {
        "cluster_name": "pve-lab-cluster",
        "nodes": ["pve01", "pve02", "pve03"],
        "datacenters": ["dc1", "dc2"],
    })

    # ══════════════════════════════════════════════════════════════════
    # 3. LANDING ZONES (one per backend, enterprise-grade)
    # ══════════════════════════════════════════════════════════════════

    def _insert_lz(lz_id, backend_id, region_id, name, desc, status, hierarchy, nc, ic, sc, nmc):
        conn.execute(
            sa.text("""
                INSERT INTO landing_zones
                    (id, tenant_id, backend_id, region_id, name, description,
                     status, version, hierarchy,
                     network_config, iam_config, security_config, naming_config,
                     created_by, created_at, updated_at)
                VALUES (:id, :tid, :bid, :rid, :name, :desc,
                        :status, 1, :hierarchy,
                        :nc, :ic, :sc, :nmc,
                        :uid, now(), now())
            """),
            {"id": lz_id, "tid": tid, "bid": backend_id, "rid": region_id,
             "name": name, "desc": desc, "status": status, "uid": uid,
             "hierarchy": json.dumps(hierarchy),
             "nc": json.dumps(nc), "ic": json.dumps(ic),
             "sc": json.dumps(sc), "nmc": json.dumps(nmc)},
        )

    # AWS Enterprise LZ (hub = eu-central-1)
    _insert_lz(
        LZ_AWS, cb_aws, REG_AWS_EUC1,
        "AWS Enterprise Landing Zone",
        "Full AWS enterprise landing zone with multi-account, Network Firewall, Security Hub, and KMS.",
        "PUBLISHED",
        {"nodes": [
            {"id": "org", "label": "Nimbus Organization", "typeId": "organization", "parentId": None, "properties": {}},
            {"id": "ou_security", "label": "Security", "typeId": "ou", "parentId": "org", "properties": {}},
            {"id": "ou_infra", "label": "Infrastructure", "typeId": "ou", "parentId": "org", "properties": {}},
            {"id": "ou_workloads", "label": "Workloads", "typeId": "ou", "parentId": "org", "properties": {}},
            {"id": "ou_prod", "label": "Production", "typeId": "ou", "parentId": "ou_workloads", "properties": {}},
            {"id": "ou_nonprod", "label": "Non-Production", "typeId": "ou", "parentId": "ou_workloads", "properties": {}},
            {"id": "acct_security", "label": "Security Account", "typeId": "account", "parentId": "ou_security", "properties": {}},
            {"id": "acct_log", "label": "Log Archive Account", "typeId": "account", "parentId": "ou_security", "properties": {}},
            {"id": "acct_network", "label": "Network Hub Account", "typeId": "account", "parentId": "ou_infra", "properties": {}},
            {"id": "acct_shared", "label": "Shared Services Account", "typeId": "account", "parentId": "ou_infra", "properties": {}},
            {"id": "acct_prod", "label": "Production Account", "typeId": "account", "parentId": "ou_prod", "properties": {}},
            {"id": "acct_staging", "label": "Staging Account", "typeId": "account", "parentId": "ou_nonprod", "properties": {}},
            {"id": "acct_dev", "label": "Development Account", "typeId": "account", "parentId": "ou_nonprod", "properties": {}},
            {"id": "vpc_hub", "label": "Hub VPC", "typeId": "vpc", "parentId": "acct_network", "properties": {"ipam": {"cidr": "10.0.0.0/16"}}},
            {"id": "vpc_inspect", "label": "Inspection VPC", "typeId": "vpc", "parentId": "acct_network", "properties": {"ipam": {"cidr": "100.64.0.0/16"}}},
            {"id": "vpc_prod", "label": "Production VPC", "typeId": "vpc", "parentId": "acct_prod", "properties": {"ipam": {"cidr": "10.1.0.0/16"}}},
            {"id": "vpc_staging", "label": "Staging VPC", "typeId": "vpc", "parentId": "acct_staging", "properties": {"ipam": {"cidr": "10.2.0.0/16"}}},
            {"id": "vpc_dev", "label": "Development VPC", "typeId": "vpc", "parentId": "acct_dev", "properties": {"ipam": {"cidr": "10.3.0.0/16"}}},
        ]},
        {"hub_vpc_cidr": "10.0.0.0/16", "inspection_vpc_cidr": "100.64.0.0/16",
         "transit_gateway": True, "network_firewall": True, "dns_resolver": True, "vpn": True, "azs": 3},
        {"cloudtrail": True, "org_trail": True, "scps": True, "kms_custom_keys": True,
         "password_policy": True, "access_analyzer": True},
        {"guardduty": True, "security_hub": True, "network_firewall": True,
         "config_rules": True, "dns_firewall": True},
        {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    )

    # Azure Enterprise LZ (hub = westeurope)
    _insert_lz(
        LZ_AZURE, cb_azure, REG_AZ_WESTEU,
        "Azure Enterprise Landing Zone",
        "Full Azure CAF landing zone with Sentinel, Premium Firewall, and ExpressRoute.",
        "PUBLISHED",
        {"nodes": [
            {"id": "org", "label": "Nimbus Organization", "typeId": "organization", "parentId": None, "properties": {}},
            {"id": "mg_platform", "label": "Platform", "typeId": "management_group", "parentId": "org", "properties": {}},
            {"id": "mg_connectivity", "label": "Connectivity", "typeId": "management_group", "parentId": "mg_platform", "properties": {}},
            {"id": "mg_identity", "label": "Identity", "typeId": "management_group", "parentId": "mg_platform", "properties": {}},
            {"id": "mg_management", "label": "Management", "typeId": "management_group", "parentId": "mg_platform", "properties": {}},
            {"id": "mg_landing", "label": "Landing Zones", "typeId": "management_group", "parentId": "org", "properties": {}},
            {"id": "mg_prod", "label": "Production", "typeId": "management_group", "parentId": "mg_landing", "properties": {}},
            {"id": "mg_nonprod", "label": "Non-Production", "typeId": "management_group", "parentId": "mg_landing", "properties": {}},
            {"id": "sub_conn", "label": "Connectivity Subscription", "typeId": "subscription", "parentId": "mg_connectivity", "properties": {}},
            {"id": "sub_identity", "label": "Identity Subscription", "typeId": "subscription", "parentId": "mg_identity", "properties": {}},
            {"id": "sub_mgmt", "label": "Management Subscription", "typeId": "subscription", "parentId": "mg_management", "properties": {}},
            {"id": "sub_prod", "label": "Production Subscription", "typeId": "subscription", "parentId": "mg_prod", "properties": {}},
            {"id": "sub_staging", "label": "Staging Subscription", "typeId": "subscription", "parentId": "mg_nonprod", "properties": {}},
            {"id": "sub_dev", "label": "Development Subscription", "typeId": "subscription", "parentId": "mg_nonprod", "properties": {}},
            {"id": "rg_hub", "label": "Hub Network RG", "typeId": "resource_group", "parentId": "sub_conn", "properties": {}},
            {"id": "vnet_hub", "label": "Hub VNet", "typeId": "vnet", "parentId": "rg_hub", "properties": {"ipam": {"cidr": "10.0.0.0/16"}}},
        ]},
        {"hub_vnet_cidr": "10.0.0.0/16", "firewall_premium": True, "expressroute": True,
         "bastion": True, "ddos_protection": True},
        {"sentinel": True, "pim": True, "azure_policy": True, "conditional_access": True},
        {"firewall_premium": True, "sentinel": True, "keyvault_hsm": True, "defender_plans": "all"},
        {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    )

    # GCP Enterprise LZ (hub = europe-west1)
    _insert_lz(
        LZ_GCP, cb_gcp, REG_GCP_EUW1,
        "GCP Analytics Landing Zone",
        "GCP landing zone with VPC Service Controls, Cloud KMS, and centralized logging.",
        "PUBLISHED",
        {"nodes": [
            {"id": "org", "label": "Nimbus Organization", "typeId": "organization", "parentId": None, "properties": {}},
            {"id": "folder_common", "label": "Common", "typeId": "folder", "parentId": "org", "properties": {}},
            {"id": "folder_prod", "label": "Production", "typeId": "folder", "parentId": "org", "properties": {}},
            {"id": "folder_nonprod", "label": "Non-Production", "typeId": "folder", "parentId": "org", "properties": {}},
            {"id": "proj_network", "label": "Network Hub", "typeId": "project", "parentId": "folder_common", "properties": {}},
            {"id": "proj_security", "label": "Security", "typeId": "project", "parentId": "folder_common", "properties": {}},
            {"id": "proj_prod", "label": "Production", "typeId": "project", "parentId": "folder_prod", "properties": {}},
            {"id": "proj_dev", "label": "Development", "typeId": "project", "parentId": "folder_nonprod", "properties": {}},
            {"id": "vpc_hub", "label": "Shared VPC", "typeId": "vpc", "parentId": "proj_network", "properties": {"ipam": {"cidr": "10.0.0.0/16"}}},
            {"id": "vpc_prod", "label": "Production VPC", "typeId": "vpc", "parentId": "proj_prod", "properties": {"ipam": {"cidr": "10.1.0.0/16"}}},
        ]},
        {"shared_vpc": True, "interconnect": True, "cloud_dns": True, "vpc_service_controls": True},
        {"org_policies": True, "access_context_manager": True, "binary_authorization": True},
        {"scc_premium": True, "vpc_sc": True, "kms_hsm": True, "assured_workloads": True},
        {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    )

    # OCI Enterprise LZ (hub = eu-frankfurt-1)
    _insert_lz(
        LZ_OCI, cb_oci, REG_OCI_FRA,
        "OCI Database Landing Zone",
        "OCI landing zone with Cloud Guard, VPrivate Vault, and FastConnect for Oracle workloads.",
        "PUBLISHED",
        {"nodes": [
            {"id": "tenancy", "label": "Nimbus Tenancy", "typeId": "tenancy", "parentId": None, "properties": {}},
            {"id": "comp_security", "label": "Security", "typeId": "compartment", "parentId": "tenancy", "properties": {}},
            {"id": "comp_network", "label": "Network", "typeId": "compartment", "parentId": "tenancy", "properties": {}},
            {"id": "comp_prod", "label": "Production", "typeId": "compartment", "parentId": "tenancy", "properties": {}},
            {"id": "comp_nonprod", "label": "Non-Production", "typeId": "compartment", "parentId": "tenancy", "properties": {}},
            {"id": "vcn_hub", "label": "Hub VCN", "typeId": "vcn", "parentId": "comp_network", "properties": {"ipam": {"cidr": "10.0.0.0/16"}}},
            {"id": "vcn_prod", "label": "Production VCN", "typeId": "vcn", "parentId": "comp_prod", "properties": {"ipam": {"cidr": "10.1.0.0/16"}}},
        ]},
        {"hub_vcn_cidr": "10.0.0.0/16", "drg": True, "fastconnect": True,
         "network_firewall": True, "bastion": True},
        {"compartments": True, "cloud_guard": True, "events": True, "notifications": True},
        {"cloud_guard": True, "vprivate_vault": True, "network_firewall": True, "bastion": True},
        {"template": "{org}-{env}-{region}-{service}-{resource}", "separator": "-"},
    )

    # Proxmox Enterprise LZ (hub = dc1)
    _insert_lz(
        LZ_PVE, cb_pve, REG_PVE_DC1,
        "Proxmox Enterprise Cluster",
        "SDN-enabled Proxmox with VXLAN/EVPN, multi-tenant pools, and tiered Ceph storage.",
        "PUBLISHED",
        {"nodes": [
            {"id": "dc1", "label": "Enterprise Datacenter", "typeId": "datacenter", "parentId": None, "properties": {}},
            {"id": "cl1", "label": "Primary Cluster", "typeId": "cluster", "parentId": "dc1", "properties": {}},
            {"id": "cl2", "label": "DR Cluster", "typeId": "cluster", "parentId": "dc1", "properties": {}},
            {"id": "pool_mgmt", "label": "Management", "typeId": "pool", "parentId": "cl1", "properties": {}},
            {"id": "pool_prod", "label": "Production", "typeId": "pool", "parentId": "cl1", "properties": {}},
            {"id": "pool_dev", "label": "Development", "typeId": "pool", "parentId": "cl1", "properties": {}},
            {"id": "pool_dr", "label": "DR Pool", "typeId": "pool", "parentId": "cl2", "properties": {}},
            {"id": "br_mgmt", "label": "SDN Mgmt", "typeId": "bridge", "parentId": "pool_mgmt", "properties": {"ipam": {"cidr": "10.0.0.0/24"}}},
            {"id": "br_prod", "label": "SDN Production", "typeId": "bridge", "parentId": "pool_prod", "properties": {"ipam": {"cidr": "10.100.0.0/16"}}},
            {"id": "br_dev", "label": "SDN Development", "typeId": "bridge", "parentId": "pool_dev", "properties": {"ipam": {"cidr": "10.200.0.0/16"}}},
            {"id": "br_dr", "label": "SDN DR", "typeId": "bridge", "parentId": "pool_dr", "properties": {"ipam": {"cidr": "10.250.0.0/16"}}},
        ]},
        {"sdn_type": "vxlan", "evpn": True, "bridge_type": "ovs", "mtu": 9000},
        {"api_token_isolation": True, "ldap_realm": True, "two_factor": True, "pve_realm": "ldap"},
        {"firewall_enabled": True, "per_pool_policies": True, "audit_logging": True,
         "backup_schedule": "hourly_snapshots", "offsite_backup": True},
        {"template": "{tenant}-{env}-{region}-{resource}-{index}", "separator": "-"},
    )

    # ══════════════════════════════════════════════════════════════════
    # 4. TAG POLICIES (enterprise standard set per LZ)
    # ══════════════════════════════════════════════════════════════════

    def _insert_tag(lz_id, key, display, required, allowed=None, default=None, inherited=True):
        conn.execute(
            sa.text("""
                INSERT INTO landing_zone_tag_policies
                    (id, landing_zone_id, tag_key, display_name, is_required,
                     allowed_values, default_value, inherited, created_at, updated_at)
                VALUES (gen_random_uuid(), :lz_id, :key, :display, :req,
                        :allowed, :default, :inherited, now(), now())
                ON CONFLICT ON CONSTRAINT uq_lz_tag_key DO NOTHING
            """),
            {"lz_id": lz_id, "key": key, "display": display, "req": required,
             "allowed": json.dumps(allowed) if allowed else None,
             "default": default, "inherited": inherited},
        )

    # Standard enterprise tags for all LZs
    for lz_id in [LZ_AWS, LZ_AZURE, LZ_GCP, LZ_OCI, LZ_PVE]:
        _insert_tag(lz_id, "Environment", "Environment", True,
                    ["dev", "staging", "prod", "dr"])
        _insert_tag(lz_id, "Owner", "Owner", True)
        _insert_tag(lz_id, "CostCenter", "Cost Center", True)
        _insert_tag(lz_id, "Project", "Project", True)
        _insert_tag(lz_id, "DataClassification", "Data Classification", True,
                    ["public", "internal", "confidential", "restricted"], "internal")

    # Extra cloud-specific tags
    for lz_id in [LZ_AWS, LZ_AZURE, LZ_GCP, LZ_OCI]:
        _insert_tag(lz_id, "Compliance", "Compliance", False,
                    ["sox", "hipaa", "pci", "gdpr", "iso27001"])
    _insert_tag(LZ_AWS, "aws:backup-plan", "Backup Plan", False)
    _insert_tag(LZ_AZURE, "ms-resource-usage", "Resource Usage", False)

    # ══════════════════════════════════════════════════════════════════
    # 5. TENANT ENVIRONMENTS
    # ══════════════════════════════════════════════════════════════════

    def _insert_env(env_id, lz_id, name, display, desc, status, region_id,
                    dr_source=None, dr_cfg=None, nc=None, ic=None, sc=None, mc=None):
        conn.execute(
            sa.text("""
                INSERT INTO tenant_environments
                    (id, tenant_id, landing_zone_id, name, display_name, description,
                     status, region_id, dr_source_env_id, dr_config,
                     network_config, iam_config, security_config, monitoring_config,
                     tags, policies, created_by, created_at, updated_at)
                VALUES (:id, :tid, :lz_id, :name, :display, :desc,
                        :status, :rid, :dr_src, :dr_cfg,
                        :nc, :ic, :sc, :mc,
                        :tags, :policies, :uid, now(), now())
            """),
            {"id": env_id, "tid": tid, "lz_id": lz_id, "name": name,
             "display": display, "desc": desc, "status": status,
             "rid": region_id, "dr_src": dr_source,
             "dr_cfg": json.dumps(dr_cfg) if dr_cfg else None,
             "nc": json.dumps(nc) if nc else None,
             "ic": json.dumps(ic) if ic else None,
             "sc": json.dumps(sc) if sc else None,
             "mc": json.dumps(mc) if mc else None,
             "tags": json.dumps({"Environment": name, "Owner": "platform-team", "CostCenter": "IT-001"}),
             "policies": json.dumps({}),
             "uid": uid},
        )

    # ── AWS environments ──────────────────────────────────────────────
    _insert_env(ENV_AWS_DEV, LZ_AWS, "dev", "Development", "AWS development environment",
                "ACTIVE", REG_AWS_EUC1,
                nc={"vpc_cidr": "10.3.0.0/16", "azs": 2, "nat_gateway": True},
                ic={"scps": ["deny-root-account"]},
                sc={"guardduty": True},
                mc={"cloudwatch_alarms": True, "log_retention_days": 30})

    _insert_env(ENV_AWS_STAGING, LZ_AWS, "staging", "Staging", "AWS pre-production staging",
                "ACTIVE", REG_AWS_EUC1,
                nc={"vpc_cidr": "10.2.0.0/16", "azs": 3, "nat_gateway_ha": True},
                ic={"scps": ["deny-root-account", "restrict-regions"]},
                sc={"guardduty": True, "config_rules": True},
                mc={"cloudwatch_alarms": True, "log_retention_days": 90})

    _insert_env(ENV_AWS_PROD, LZ_AWS, "prod", "Production", "AWS production environment (EU primary)",
                "ACTIVE", REG_AWS_EUC1,
                nc={"vpc_cidr": "10.1.0.0/16", "azs": 3, "nat_gateway_ha": True, "flow_logs": True},
                ic={"scps": ["deny-root-account", "restrict-regions", "require-imdsv2"]},
                sc={"guardduty": True, "security_hub": True, "config_rules": True},
                mc={"cloudwatch_alarms": True, "xray_tracing": True, "log_retention_days": 365})

    _insert_env(ENV_AWS_DR, LZ_AWS, "dr", "Disaster Recovery", "AWS DR environment (EU-West failover)",
                "ACTIVE", REG_AWS_EUW1,
                dr_source=ENV_AWS_PROD,
                dr_cfg={"failoverMode": "warm_standby", "rpoHours": 1, "rtoHours": 4,
                         "replicationConfig": {"s3_crr": True, "rds_read_replica": True, "dynamodb_global_tables": True},
                         "failoverPriority": 1,
                         "healthCheckUrl": "https://prod.nimbus-demo.eu/health"},
                nc={"vpc_cidr": "10.4.0.0/16", "azs": 3, "nat_gateway_ha": True, "flow_logs": True},
                ic={"scps": ["deny-root-account", "restrict-regions"]},
                sc={"guardduty": True, "security_hub": True},
                mc={"cloudwatch_alarms": True, "log_retention_days": 365})

    # ── Azure environments ────────────────────────────────────────────
    _insert_env(ENV_AZ_DEV, LZ_AZURE, "dev", "Development", "Azure development environment",
                "ACTIVE", REG_AZ_WESTEU,
                nc={"vnet_cidr": "10.3.0.0/16", "peering_to_hub": True},
                sc={"defender": True, "nsg_flow_logs": True},
                mc={"log_analytics": True, "retention_days": 30})

    _insert_env(ENV_AZ_STAGING, LZ_AZURE, "staging", "Staging", "Azure staging environment",
                "ACTIVE", REG_AZ_NORTHEU,
                nc={"vnet_cidr": "10.2.0.0/16", "peering_to_hub": True},
                sc={"defender": True, "nsg_flow_logs": True, "keyvault": True},
                mc={"log_analytics": True, "retention_days": 90})

    _insert_env(ENV_AZ_PROD, LZ_AZURE, "prod", "Production", "Azure production environment",
                "ACTIVE", REG_AZ_WESTEU,
                nc={"vnet_cidr": "10.1.0.0/16", "peering_to_hub": True, "private_endpoints": True},
                sc={"defender": True, "sentinel": True, "keyvault_hsm": True, "nsg_flow_logs": True},
                mc={"log_analytics": True, "retention_days": 365, "application_insights": True})

    # ── GCP environments ──────────────────────────────────────────────
    _insert_env(ENV_GCP_DEV, LZ_GCP, "dev", "Development", "GCP analytics development",
                "ACTIVE", REG_GCP_EUW1,
                nc={"shared_vpc_service_project": True, "cloud_nat": True},
                sc={"scc": True},
                mc={"cloud_logging": True, "retention_days": 30})

    _insert_env(ENV_GCP_PROD, LZ_GCP, "prod", "Production", "GCP analytics production (BigQuery, Dataflow)",
                "ACTIVE", REG_GCP_EUW3,
                nc={"shared_vpc_service_project": True, "cloud_nat": True, "vpc_sc_perimeter": True},
                sc={"scc_premium": True, "vpc_sc": True, "kms_hsm": True},
                mc={"cloud_logging": True, "cloud_monitoring": True, "retention_days": 365})

    # ── OCI environments ──────────────────────────────────────────────
    _insert_env(ENV_OCI_PROD, LZ_OCI, "prod", "Production", "OCI production for Autonomous DB workloads",
                "ACTIVE", REG_OCI_FRA,
                nc={"vcn_cidr": "10.1.0.0/16", "drg_attachment": True, "service_gateway": True},
                sc={"cloud_guard": True, "vault": True, "bastion": True},
                mc={"logging_analytics": True, "retention_days": 365})

    _insert_env(ENV_OCI_DR, LZ_OCI, "dr", "Disaster Recovery", "OCI DR in Amsterdam for Oracle workloads",
                "ACTIVE", REG_OCI_AMS,
                dr_source=ENV_OCI_PROD,
                dr_cfg={"failoverMode": "active_passive", "rpoHours": 0.5, "rtoHours": 2,
                         "replicationConfig": {"data_guard": True, "autonomous_dg": True},
                         "failoverPriority": 1,
                         "healthCheckUrl": "https://prod.nimbus-demo.eu/oci-health"},
                nc={"vcn_cidr": "10.5.0.0/16", "drg_attachment": True, "service_gateway": True},
                sc={"cloud_guard": True, "vault": True},
                mc={"logging_analytics": True, "retention_days": 365})

    # ══════════════════════════════════════════════════════════════════
    # 6. ADDRESS SPACES (IPAM)
    # ══════════════════════════════════════════════════════════════════

    def _insert_addr(as_id, lz_id, region_id, name, desc, cidr):
        conn.execute(
            sa.text("""
                INSERT INTO address_spaces
                    (id, landing_zone_id, region_id, name, description, cidr,
                     ip_version, status, created_at, updated_at)
                VALUES (:id, :lz_id, :rid, :name, :desc, :cidr,
                        4, 'ACTIVE', now(), now())
                ON CONFLICT ON CONSTRAINT uq_addr_space_lz_cidr DO NOTHING
            """),
            {"id": as_id, "lz_id": lz_id, "rid": region_id,
             "name": name, "desc": desc, "cidr": cidr},
        )

    # AWS address spaces
    _insert_addr(AS_AWS_HUB, LZ_AWS, REG_AWS_EUC1,
                 "Hub VPC", "Shared services hub network", "10.0.0.0/16")
    _insert_addr(AS_AWS_INSPECT, LZ_AWS, REG_AWS_EUC1,
                 "Inspection VPC", "Network Firewall inspection VPC (RFC 6598)", "100.64.0.0/16")
    _insert_addr(AS_AWS_SPOKE, LZ_AWS, REG_AWS_EUC1,
                 "Spoke Pool", "Spoke VPC CIDR pool for workload accounts", "10.1.0.0/12")

    # Azure address spaces
    _insert_addr(AS_AZ_HUB, LZ_AZURE, REG_AZ_WESTEU,
                 "Hub VNet", "Hub network with Azure Firewall and Bastion", "10.0.0.0/16")
    _insert_addr(AS_AZ_SPOKE, LZ_AZURE, REG_AZ_WESTEU,
                 "Spoke Pool", "Spoke VNet CIDR pool for landing zone subscriptions", "10.1.0.0/12")

    # GCP address spaces
    _insert_addr(AS_GCP_HUB, LZ_GCP, REG_GCP_EUW1,
                 "Shared VPC", "Shared VPC host project hub network", "10.0.0.0/16")
    _insert_addr(AS_GCP_SVC, LZ_GCP, REG_GCP_EUW1,
                 "Service Projects", "Service project VPC CIDR pool", "10.1.0.0/12")

    # OCI address spaces
    _insert_addr(AS_OCI_HUB, LZ_OCI, REG_OCI_FRA,
                 "Hub VCN", "Hub VCN with DRG and FastConnect gateway", "10.0.0.0/16")
    _insert_addr(AS_OCI_SPOKE, LZ_OCI, REG_OCI_FRA,
                 "Spoke Pool", "Spoke VCN CIDR pool for workload compartments", "10.1.0.0/12")

    # Proxmox address spaces
    _insert_addr(AS_PVE_MGMT, LZ_PVE, REG_PVE_DC1,
                 "Management", "Management SDN overlay network", "10.0.0.0/24")
    _insert_addr(AS_PVE_PROD, LZ_PVE, REG_PVE_DC1,
                 "Production", "Production SDN overlay network", "10.100.0.0/16")
    _insert_addr(AS_PVE_DEV, LZ_PVE, REG_PVE_DC1,
                 "Development", "Development SDN overlay network", "10.200.0.0/16")


def downgrade() -> None:
    conn = op.get_bind()

    # Delete in reverse dependency order
    for as_id in [AS_PVE_DEV, AS_PVE_PROD, AS_PVE_MGMT,
                  AS_OCI_SPOKE, AS_OCI_HUB, AS_GCP_SVC, AS_GCP_HUB,
                  AS_AZ_SPOKE, AS_AZ_HUB, AS_AWS_SPOKE, AS_AWS_INSPECT, AS_AWS_HUB]:
        conn.execute(sa.text("DELETE FROM address_spaces WHERE id = :id"), {"id": as_id})

    for env_id in [ENV_OCI_DR, ENV_OCI_PROD, ENV_GCP_PROD, ENV_GCP_DEV,
                   ENV_AZ_PROD, ENV_AZ_STAGING, ENV_AZ_DEV,
                   ENV_AWS_DR, ENV_AWS_PROD, ENV_AWS_STAGING, ENV_AWS_DEV]:
        conn.execute(sa.text("DELETE FROM tenant_environments WHERE id = :id"), {"id": env_id})

    # Delete tag policies for our LZs
    for lz_id in [LZ_PVE, LZ_OCI, LZ_GCP, LZ_AZURE, LZ_AWS]:
        conn.execute(sa.text("DELETE FROM landing_zone_tag_policies WHERE landing_zone_id = :id"), {"id": lz_id})

    for lz_id in [LZ_PVE, LZ_OCI, LZ_GCP, LZ_AZURE, LZ_AWS]:
        conn.execute(sa.text("DELETE FROM landing_zones WHERE id = :id"), {"id": lz_id})

    for reg_id in [REG_PVE_DC2, REG_PVE_DC1, REG_OCI_LON, REG_OCI_AMS, REG_OCI_FRA,
                   REG_GCP_USC1, REG_GCP_EUW3, REG_GCP_EUW1,
                   REG_AZ_GERMWC, REG_AZ_NORTHEU, REG_AZ_WESTEU,
                   REG_AWS_USE1, REG_AWS_EUW1, REG_AWS_EUC1]:
        conn.execute(sa.text("DELETE FROM backend_regions WHERE id = :id"), {"id": reg_id})

    # Reset scope_config
    conn.execute(sa.text("UPDATE cloud_backends SET scope_config = NULL WHERE deleted_at IS NULL"))
