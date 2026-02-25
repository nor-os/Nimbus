"""Seed the full service catalog demo portfolio: service offerings,
process assignments, service groups, service catalogs, price lists,
rate cards. Idempotent — creates offerings only if migration 025
failed to insert them (e.g. due to schema timing).

Revision ID: 038
Revises: 037
Create Date: 2026-02-13
"""

import uuid
from datetime import date
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "038"
down_revision: Union[str, None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Pre-generated UUIDs ──────────────────────────────────────────────

# Service offering IDs (same names as migration 025 but new UUIDs since
# the originals were never persisted)
SO_VM_STANDARD = str(uuid.uuid4())
SO_VM_HIGHPERF = str(uuid.uuid4())
SO_DB_POSTGRES = str(uuid.uuid4())
SO_DB_MYSQL = str(uuid.uuid4())
SO_OBJ_STORAGE = str(uuid.uuid4())
SO_BLOCK_STORAGE = str(uuid.uuid4())
SO_LOAD_BALANCER = str(uuid.uuid4())
SO_K8S_CLUSTER = str(uuid.uuid4())
SO_VIRTUAL_NETWORK = str(uuid.uuid4())
SO_MANAGED_FIREWALL = str(uuid.uuid4())
SO_ENDPOINT_PROT = str(uuid.uuid4())
SO_VULN_SCAN = str(uuid.uuid4())
SO_SSL_MGMT = str(uuid.uuid4())
SO_SIEM = str(uuid.uuid4())
SO_MONITORING = str(uuid.uuid4())
SO_BACKUP_DR = str(uuid.uuid4())
SO_PATCH_MGMT = str(uuid.uuid4())
SO_INCIDENT_BH = str(uuid.uuid4())
SO_INCIDENT_247 = str(uuid.uuid4())
SO_MANAGED_DESKTOP = str(uuid.uuid4())
SO_EMAIL_COLLAB = str(uuid.uuid4())
SO_VPN_ACCESS = str(uuid.uuid4())
SO_HELPDESK_BH = str(uuid.uuid4())
SO_HELPDESK_EXT = str(uuid.uuid4())
SO_CICD = str(uuid.uuid4())
SO_IAC_MGMT = str(uuid.uuid4())
SO_MANAGED_DNS = str(uuid.uuid4())

# Service groups
SG_CORE_INFRA = str(uuid.uuid4())
SG_SECURITY_BUNDLE = str(uuid.uuid4())
SG_MANAGED_OPS = str(uuid.uuid4())
SG_END_USER = str(uuid.uuid4())
SG_DEVOPS = str(uuid.uuid4())

# Service catalogs
SC_ENTERPRISE = str(uuid.uuid4())
SC_SMB = str(uuid.uuid4())

# Price lists
PL_STANDARD_EMEA = str(uuid.uuid4())
PL_STANDARD_AMER = str(uuid.uuid4())
PL_PREMIUM = str(uuid.uuid4())


def upgrade() -> None:
    conn = op.get_bind()

    # ── Resolve root tenant ──────────────────────────────────────────
    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if not row:
        return
    tid = str(row[0])

    # ── 0. Seed offerings if migration 025 failed to insert them ─────
    existing = conn.execute(
        sa.text("SELECT count(*) FROM service_offerings WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar()
    if not existing:
        _seed_service_offerings(conn, tid)
        _seed_process_assignments(conn, tid)

    # ── Resolve offering IDs by name ─────────────────────────────────
    offerings = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM service_offerings WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ):
        offerings[r[0]] = str(r[1])

    if not offerings:
        return

    # ── Resolve delivery region IDs by code ──────────────────────────
    regions = {}
    for r in conn.execute(
        sa.text("SELECT code, id FROM delivery_regions WHERE is_system = true AND deleted_at IS NULL")
    ):
        regions[r[0]] = str(r[1])

    # ── Resolve staff profile IDs by name ────────────────────────────
    profiles = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM staff_profiles WHERE is_system = true AND deleted_at IS NULL")
    ):
        profiles[r[0]] = str(r[1])

    # ── Resolve activity definition IDs for price list items ─────────
    activity_defs = {}
    for r in conn.execute(
        sa.text("""
            SELECT ad.name, ad.id
            FROM activity_definitions ad
            JOIN activity_templates at ON ad.template_id = at.id
            WHERE at.tenant_id = :tid AND ad.deleted_at IS NULL AND at.deleted_at IS NULL
        """),
        {"tid": tid},
    ):
        activity_defs[r[0]] = str(r[1])

    # ── 1. Service Groups + Items ────────────────────────────────────
    _seed_service_groups(conn, tid, offerings)

    # ── 2. Service Catalogs + Items ──────────────────────────────────
    _seed_service_catalogs(conn, tid, offerings)

    # ── 3. Internal Rate Cards ───────────────────────────────────────
    _seed_rate_cards(conn, tid, profiles, regions)

    # ── 4. Price Lists + Items ───────────────────────────────────────
    _seed_price_lists(conn, tid, offerings, activity_defs, regions)


# ── Service Offerings (backfill from migration 025) ──────────────────


def _insert_offering(conn, tid, so_id, name, desc, category, unit, stype,
                     op_model=None, coverage=None, status="published"):
    conn.execute(
        sa.text("""
            INSERT INTO service_offerings
                (id, tenant_id, name, description, category, measuring_unit,
                 service_type, operating_model, default_coverage_model,
                 is_active, status, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :cat, :unit, :stype, :opm,
                    :cov, true, :status, now(), now())
        """),
        {"id": so_id, "tid": tid, "name": name, "desc": desc, "cat": category,
         "unit": unit, "stype": stype, "opm": op_model, "cov": coverage,
         "status": status},
    )


def _seed_service_offerings(conn, tid):
    # Infrastructure
    _insert_offering(conn, tid, SO_VM_STANDARD,
                     "Virtual Machine \u2014 Standard", "General-purpose VM with shared CPU and SSD storage",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_VM_HIGHPERF,
                     "Virtual Machine \u2014 High Performance", "Dedicated-CPU VM for compute-intensive workloads",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_DB_POSTGRES,
                     "Managed PostgreSQL", "Fully managed PostgreSQL with automated backups and HA",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_DB_MYSQL,
                     "Managed MySQL", "Fully managed MySQL / MariaDB with automated backups and HA",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_OBJ_STORAGE,
                     "Object Storage", "S3-compatible object storage with configurable redundancy",
                     "Infrastructure", "gb", "resource", "global")
    _insert_offering(conn, tid, SO_BLOCK_STORAGE,
                     "Block Storage \u2014 SSD", "High-performance SSD block volumes for VMs",
                     "Infrastructure", "gb", "resource", "regional")
    _insert_offering(conn, tid, SO_LOAD_BALANCER,
                     "Load Balancer", "L4/L7 load balancer with SSL termination and health checks",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_K8S_CLUSTER,
                     "Kubernetes Cluster", "Managed Kubernetes with auto-scaling node pools",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_VIRTUAL_NETWORK,
                     "Virtual Network", "Isolated network with subnets, routing, and peering",
                     "Infrastructure", "instance", "resource", "regional")

    # Security
    _insert_offering(conn, tid, SO_MANAGED_FIREWALL,
                     "Managed Firewall", "Next-gen firewall with IDS/IPS, managed rule sets, and logging",
                     "Security", "instance", "resource", "regional", "24x7")
    _insert_offering(conn, tid, SO_ENDPOINT_PROT,
                     "Endpoint Protection", "EDR/antimalware per user with central management console",
                     "Security", "user", "resource", "global")
    _insert_offering(conn, tid, SO_VULN_SCAN,
                     "Vulnerability Scanning", "Automated vulnerability scanning with prioritised remediation",
                     "Security", "instance", "resource", "global")
    _insert_offering(conn, tid, SO_SSL_MGMT,
                     "SSL Certificate Management", "Automated provisioning, renewal, and monitoring of TLS certificates",
                     "Security", "instance", "resource", "global")
    _insert_offering(conn, tid, SO_SIEM,
                     "SIEM / Log Monitoring", "Centralized log ingestion, correlation, and alerting",
                     "Security", "gb", "resource", "global", "24x7")

    # Managed Services
    _insert_offering(conn, tid, SO_MONITORING,
                     "24/7 Infrastructure Monitoring", "Round-the-clock monitoring with SLA-backed response times",
                     "Managed Services", "instance", "resource", "follow_the_sun", "24x7")
    _insert_offering(conn, tid, SO_BACKUP_DR,
                     "Backup & Disaster Recovery", "Automated backups with defined RPO/RTO and periodic DR tests",
                     "Managed Services", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_PATCH_MGMT,
                     "Patch Management", "OS and application patching with scheduled maintenance windows",
                     "Managed Services", "instance", "resource", "regional", "business_hours")
    _insert_offering(conn, tid, SO_INCIDENT_BH,
                     "Incident Response \u2014 Business Hours", "ITIL incident management during business hours",
                     "Managed Services", "instance", "labor", "regional", "business_hours")
    _insert_offering(conn, tid, SO_INCIDENT_247,
                     "Incident Response \u2014 24/7", "ITIL incident management with 24/7 coverage and SLA",
                     "Managed Services", "instance", "labor", "follow_the_sun", "24x7")

    # End User Services
    _insert_offering(conn, tid, SO_MANAGED_DESKTOP,
                     "Managed Desktop", "Fully managed Windows/macOS desktop with remote management",
                     "End User Services", "user", "resource", "regional", "business_hours")
    _insert_offering(conn, tid, SO_EMAIL_COLLAB,
                     "Email & Collaboration Suite", "Microsoft 365 or Google Workspace managed license with support",
                     "End User Services", "user", "resource", "global")
    _insert_offering(conn, tid, SO_VPN_ACCESS,
                     "VPN Access", "Secure remote access VPN with MFA integration",
                     "End User Services", "user", "resource", "regional")
    _insert_offering(conn, tid, SO_HELPDESK_BH,
                     "Help Desk \u2014 Business Hours", "L1/L2 end-user support during business hours",
                     "End User Services", "user", "labor", "regional", "business_hours")
    _insert_offering(conn, tid, SO_HELPDESK_EXT,
                     "Help Desk \u2014 Extended Hours", "L1/L2 end-user support with extended coverage",
                     "End User Services", "user", "labor", "regional", "extended")

    # DevOps & Automation
    _insert_offering(conn, tid, SO_CICD,
                     "CI/CD Pipeline", "Managed build, test, and deployment pipeline per application",
                     "DevOps & Automation", "instance", "resource", "global")
    _insert_offering(conn, tid, SO_IAC_MGMT,
                     "Infrastructure as Code Management", "Pulumi/Terraform IaC authoring, review, and execution",
                     "DevOps & Automation", "hour", "labor", "global")
    _insert_offering(conn, tid, SO_MANAGED_DNS,
                     "Managed DNS", "Authoritative DNS hosting with DNSSEC and geo-routing",
                     "DevOps & Automation", "instance", "resource", "global")


# ── Process Assignments (backfill from migration 025) ────────────────


def _assign_process(conn, tid, so_name, sp_name, coverage=None, is_default=False):
    """Assign a process to an offering by name (resilient to missing data)."""
    conn.execute(
        sa.text("""
            INSERT INTO service_process_assignments
                (id, tenant_id, service_offering_id, process_id, coverage_model,
                 is_default, created_at, updated_at)
            SELECT gen_random_uuid(), :tid, so.id, sp.id, :cov, :dflt, now(), now()
            FROM service_offerings so, service_processes sp
            WHERE so.name = :so_name AND so.tenant_id = :tid AND so.deleted_at IS NULL
              AND sp.name = :sp_name AND sp.tenant_id = :tid AND sp.deleted_at IS NULL
        """),
        {"tid": tid, "so_name": so_name, "sp_name": sp_name,
         "cov": coverage, "dflt": is_default},
    )


def _seed_process_assignments(conn, tid):
    # Infrastructure offerings
    for so in ["Virtual Machine \u2014 Standard", "Virtual Machine \u2014 High Performance"]:
        _assign_process(conn, tid, so, "Standard Provisioning", is_default=True)
        _assign_process(conn, tid, so, "Incident Management")
        _assign_process(conn, tid, so, "Change Management")
        _assign_process(conn, tid, so, "Service Decommission")
        _assign_process(conn, tid, so, "Capacity Management")
        _assign_process(conn, tid, so, "Disaster Recovery Management")

    for so in ["Managed PostgreSQL", "Managed MySQL"]:
        _assign_process(conn, tid, so, "Database Provisioning", is_default=True)
        _assign_process(conn, tid, so, "Incident Management")
        _assign_process(conn, tid, so, "Change Management")
        _assign_process(conn, tid, so, "Service Decommission")
        _assign_process(conn, tid, so, "Capacity Management")
        _assign_process(conn, tid, so, "Disaster Recovery Management")

    for so in ["Object Storage", "Block Storage \u2014 SSD"]:
        _assign_process(conn, tid, so, "Standard Provisioning", is_default=True)
        _assign_process(conn, tid, so, "Incident Management")
        _assign_process(conn, tid, so, "Change Management")
        _assign_process(conn, tid, so, "Service Decommission")
        _assign_process(conn, tid, so, "Capacity Management")

    _assign_process(conn, tid, "Load Balancer", "Standard Provisioning", is_default=True)
    _assign_process(conn, tid, "Load Balancer", "Incident Management")
    _assign_process(conn, tid, "Load Balancer", "Change Management")
    _assign_process(conn, tid, "Load Balancer", "Service Decommission")

    _assign_process(conn, tid, "Kubernetes Cluster", "Container Service Delivery", is_default=True)
    _assign_process(conn, tid, "Kubernetes Cluster", "Incident Management")
    _assign_process(conn, tid, "Kubernetes Cluster", "Change Management")
    _assign_process(conn, tid, "Kubernetes Cluster", "Service Decommission")
    _assign_process(conn, tid, "Kubernetes Cluster", "Capacity Management")

    _assign_process(conn, tid, "Virtual Network", "Standard Provisioning", is_default=True)
    _assign_process(conn, tid, "Virtual Network", "Incident Management")
    _assign_process(conn, tid, "Virtual Network", "Change Management")
    _assign_process(conn, tid, "Virtual Network", "Service Decommission")

    # Security offerings
    _assign_process(conn, tid, "Managed Firewall", "Security Operations", is_default=True)
    _assign_process(conn, tid, "Managed Firewall", "Incident Management")
    _assign_process(conn, tid, "Managed Firewall", "Change Management")
    _assign_process(conn, tid, "Managed Firewall", "Service Decommission")

    _assign_process(conn, tid, "Endpoint Protection", "Security Operations", is_default=True)
    _assign_process(conn, tid, "Endpoint Protection", "Incident Management")
    _assign_process(conn, tid, "Endpoint Protection", "Change Management")

    _assign_process(conn, tid, "Vulnerability Scanning", "Security Operations", is_default=True)
    _assign_process(conn, tid, "Vulnerability Scanning", "Incident Management")

    _assign_process(conn, tid, "SSL Certificate Management", "Security Operations", is_default=True)
    _assign_process(conn, tid, "SSL Certificate Management", "Incident Management")

    _assign_process(conn, tid, "SIEM / Log Monitoring", "Security Operations", is_default=True)
    _assign_process(conn, tid, "SIEM / Log Monitoring", "Incident Management")
    _assign_process(conn, tid, "SIEM / Log Monitoring", "Change Management")
    _assign_process(conn, tid, "SIEM / Log Monitoring", "Capacity Management")

    # Managed Services
    _assign_process(conn, tid, "24/7 Infrastructure Monitoring", "Standard Provisioning", is_default=True)
    _assign_process(conn, tid, "24/7 Infrastructure Monitoring", "Incident Management")
    _assign_process(conn, tid, "24/7 Infrastructure Monitoring", "Change Management")

    _assign_process(conn, tid, "Backup & Disaster Recovery", "Disaster Recovery Management", is_default=True)
    _assign_process(conn, tid, "Backup & Disaster Recovery", "Incident Management")
    _assign_process(conn, tid, "Backup & Disaster Recovery", "Change Management")

    _assign_process(conn, tid, "Patch Management", "Change Management", is_default=True)
    _assign_process(conn, tid, "Patch Management", "Incident Management")

    for so in ["Incident Response \u2014 Business Hours", "Incident Response \u2014 24/7"]:
        _assign_process(conn, tid, so, "Incident Management", is_default=True)
        _assign_process(conn, tid, so, "Change Management")

    # End User Services
    _assign_process(conn, tid, "Managed Desktop", "User Lifecycle Management", is_default=True)
    _assign_process(conn, tid, "Managed Desktop", "Incident Management")
    _assign_process(conn, tid, "Managed Desktop", "Change Management")
    _assign_process(conn, tid, "Managed Desktop", "Service Decommission")

    _assign_process(conn, tid, "Email & Collaboration Suite", "User Lifecycle Management", is_default=True)
    _assign_process(conn, tid, "Email & Collaboration Suite", "Incident Management")

    _assign_process(conn, tid, "VPN Access", "User Lifecycle Management", is_default=True)
    _assign_process(conn, tid, "VPN Access", "Incident Management")
    _assign_process(conn, tid, "VPN Access", "Change Management")

    for so in ["Help Desk \u2014 Business Hours", "Help Desk \u2014 Extended Hours"]:
        _assign_process(conn, tid, so, "Incident Management", is_default=True)

    # DevOps & Automation
    _assign_process(conn, tid, "CI/CD Pipeline", "Standard Provisioning", is_default=True)
    _assign_process(conn, tid, "CI/CD Pipeline", "Incident Management")
    _assign_process(conn, tid, "CI/CD Pipeline", "Change Management")
    _assign_process(conn, tid, "CI/CD Pipeline", "Service Decommission")

    _assign_process(conn, tid, "Infrastructure as Code Management", "Change Management", is_default=True)
    _assign_process(conn, tid, "Infrastructure as Code Management", "Incident Management")

    _assign_process(conn, tid, "Managed DNS", "Standard Provisioning", is_default=True)
    _assign_process(conn, tid, "Managed DNS", "Incident Management")
    _assign_process(conn, tid, "Managed DNS", "Change Management")


# ── Service Groups ───────────────────────────────────────────────────


def _insert_group(conn, tid, gid, name, display, desc):
    conn.execute(
        sa.text("""
            INSERT INTO service_groups (id, tenant_id, name, display_name, description, status, created_at, updated_at)
            VALUES (:id, :tid, :name, :display, :desc, 'published', now(), now())
        """),
        {"id": gid, "tid": tid, "name": name, "display": display, "desc": desc},
    )


def _insert_group_item(conn, gid, offering_id, required=True, sort=0):
    conn.execute(
        sa.text("""
            INSERT INTO service_group_items (id, group_id, service_offering_id, is_required, sort_order, created_at, updated_at)
            VALUES (gen_random_uuid(), :gid, :oid, :req, :sort, now(), now())
        """),
        {"gid": gid, "oid": offering_id, "req": required, "sort": sort},
    )


def _seed_service_groups(conn, tid, o):
    # ── Core Infrastructure Bundle ──
    _insert_group(conn, tid, SG_CORE_INFRA, "core-infrastructure",
                  "Core Infrastructure", "Compute, storage, networking, and load balancing essentials")
    for i, name in enumerate([
        "Virtual Machine — Standard", "Block Storage — SSD", "Virtual Network",
        "Load Balancer", "Managed DNS",
    ], 1):
        if name in o:
            _insert_group_item(conn, SG_CORE_INFRA, o[name], required=True, sort=i)

    # ── Security Bundle ──
    _insert_group(conn, tid, SG_SECURITY_BUNDLE, "security-essentials",
                  "Security Essentials", "Firewall, endpoint protection, vulnerability scanning, SSL, and SIEM")
    for i, name in enumerate([
        "Managed Firewall", "Endpoint Protection", "Vulnerability Scanning",
        "SSL Certificate Management", "SIEM / Log Monitoring",
    ], 1):
        if name in o:
            _insert_group_item(conn, SG_SECURITY_BUNDLE, o[name], required=(i <= 2), sort=i)

    # ── Managed Operations Bundle ──
    _insert_group(conn, tid, SG_MANAGED_OPS, "managed-operations",
                  "Managed Operations", "Monitoring, backup, patching, and incident response")
    for i, name in enumerate([
        "24/7 Infrastructure Monitoring", "Backup & Disaster Recovery",
        "Patch Management", "Incident Response — Business Hours",
    ], 1):
        if name in o:
            _insert_group_item(conn, SG_MANAGED_OPS, o[name], required=True, sort=i)

    # ── End User Productivity ──
    _insert_group(conn, tid, SG_END_USER, "end-user-productivity",
                  "End User Productivity", "Desktop, email, VPN, and help desk for end users")
    for i, name in enumerate([
        "Managed Desktop", "Email & Collaboration Suite", "VPN Access",
        "Help Desk — Business Hours",
    ], 1):
        if name in o:
            _insert_group_item(conn, SG_END_USER, o[name], required=(i <= 2), sort=i)

    # ── DevOps Toolchain ──
    _insert_group(conn, tid, SG_DEVOPS, "devops-toolchain",
                  "DevOps Toolchain", "CI/CD pipelines, IaC management, and container orchestration")
    for i, name in enumerate([
        "CI/CD Pipeline", "Infrastructure as Code Management",
        "Kubernetes Cluster",
    ], 1):
        if name in o:
            _insert_group_item(conn, SG_DEVOPS, o[name], required=(i == 1), sort=i)


# ── Service Catalogs ─────────────────────────────────────────────────


def _insert_catalog(conn, tid, cid, name, desc, status="published"):
    conn.execute(
        sa.text("""
            INSERT INTO service_catalogs
                (id, tenant_id, name, description, group_id, version_major, version_minor,
                 status, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :id, 1, 0, :status, now(), now())
        """),
        {"id": cid, "tid": tid, "name": name, "desc": desc, "status": status},
    )


def _insert_catalog_item(conn, catalog_id, offering_id=None, group_id=None, sort=0):
    conn.execute(
        sa.text("""
            INSERT INTO service_catalog_items
                (id, catalog_id, service_offering_id, service_group_id, sort_order, created_at, updated_at)
            VALUES (gen_random_uuid(), :cid, :oid, :gid, :sort, now(), now())
        """),
        {"cid": catalog_id, "oid": offering_id, "gid": group_id, "sort": sort},
    )


def _seed_service_catalogs(conn, tid, o):
    # ── Enterprise Catalog (full portfolio) ──
    _insert_catalog(conn, tid, SC_ENTERPRISE, "Enterprise Service Catalog",
                    "Complete IT service portfolio for enterprise customers including all infrastructure, security, managed services, and end-user offerings")

    # Add all 5 service groups
    _insert_catalog_item(conn, SC_ENTERPRISE, group_id=SG_CORE_INFRA, sort=1)
    _insert_catalog_item(conn, SC_ENTERPRISE, group_id=SG_SECURITY_BUNDLE, sort=2)
    _insert_catalog_item(conn, SC_ENTERPRISE, group_id=SG_MANAGED_OPS, sort=3)
    _insert_catalog_item(conn, SC_ENTERPRISE, group_id=SG_END_USER, sort=4)
    _insert_catalog_item(conn, SC_ENTERPRISE, group_id=SG_DEVOPS, sort=5)

    # Also add high-performance offerings as standalone items
    for i, name in enumerate([
        "Virtual Machine — High Performance", "Managed PostgreSQL",
        "Managed MySQL", "Object Storage", "Incident Response — 24/7",
        "Help Desk — Extended Hours",
    ], 10):
        if name in o:
            _insert_catalog_item(conn, SC_ENTERPRISE, offering_id=o[name], sort=i)

    # ── SMB Catalog (essentials only) ──
    _insert_catalog(conn, tid, SC_SMB, "SMB Essentials Catalog",
                    "Streamlined service catalog for small and medium businesses with core infrastructure, basic security, and standard support")

    # Infrastructure essentials (individual offerings, no groups)
    smb_offerings = [
        "Virtual Machine — Standard", "Block Storage — SSD", "Virtual Network",
        "Managed Firewall", "Endpoint Protection",
        "24/7 Infrastructure Monitoring", "Backup & Disaster Recovery",
        "Patch Management", "Incident Response — Business Hours",
        "Managed Desktop", "Email & Collaboration Suite",
        "Help Desk — Business Hours",
    ]
    for i, name in enumerate(smb_offerings, 1):
        if name in o:
            _insert_catalog_item(conn, SC_SMB, offering_id=o[name], sort=i)


# ── Internal Rate Cards ──────────────────────────────────────────────


def _seed_rate_cards(conn, tid, profiles, regions):
    # Rate table: (profile_name, region_code, hourly_cost, currency)
    rate_data = [
        # EMEA-FRA (Germany — higher rates)
        ("junior_engineer",    "EMEA-FRA",  55.00, "EUR"),
        ("engineer",           "EMEA-FRA",  85.00, "EUR"),
        ("senior_engineer",    "EMEA-FRA", 120.00, "EUR"),
        ("consultant",         "EMEA-FRA", 140.00, "EUR"),
        ("senior_consultant",  "EMEA-FRA", 175.00, "EUR"),
        ("architect",          "EMEA-FRA", 220.00, "EUR"),

        # APAC-MNL (Manila — lower cost center)
        ("junior_engineer",    "APAC-MNL",  35.00, "EUR"),
        ("engineer",           "APAC-MNL",  50.00, "EUR"),
        ("senior_engineer",    "APAC-MNL",  70.00, "EUR"),
        ("consultant",         "APAC-MNL",  80.00, "EUR"),
        ("senior_consultant",  "APAC-MNL", 100.00, "EUR"),
        ("architect",          "APAC-MNL", 130.00, "EUR"),

        # APAC-BLR (Bangalore)
        ("junior_engineer",    "APAC-BLR",  38.00, "EUR"),
        ("engineer",           "APAC-BLR",  55.00, "EUR"),
        ("senior_engineer",    "APAC-BLR",  78.00, "EUR"),
        ("consultant",         "APAC-BLR",  88.00, "EUR"),
        ("senior_consultant",  "APAC-BLR", 110.00, "EUR"),
        ("architect",          "APAC-BLR", 140.00, "EUR"),

        # AMER-NYC (New York — premium rates)
        ("junior_engineer",    "AMER-NYC",  70.00, "USD"),
        ("engineer",           "AMER-NYC", 110.00, "USD"),
        ("senior_engineer",    "AMER-NYC", 155.00, "USD"),
        ("consultant",         "AMER-NYC", 180.00, "USD"),
        ("senior_consultant",  "AMER-NYC", 220.00, "USD"),
        ("architect",          "AMER-NYC", 275.00, "USD"),

        # AMER-GRU (São Paulo)
        ("junior_engineer",    "AMER-GRU",  42.00, "USD"),
        ("engineer",           "AMER-GRU",  60.00, "USD"),
        ("senior_engineer",    "AMER-GRU",  85.00, "USD"),
        ("consultant",         "AMER-GRU",  95.00, "USD"),
        ("senior_consultant",  "AMER-GRU", 120.00, "USD"),
        ("architect",          "AMER-GRU", 150.00, "USD"),
    ]

    for profile_name, region_code, cost, currency in rate_data:
        pid = profiles.get(profile_name)
        rid = regions.get(region_code)
        if not pid or not rid:
            continue
        conn.execute(
            sa.text("""
                INSERT INTO internal_rate_cards
                    (id, tenant_id, staff_profile_id, delivery_region_id,
                     hourly_cost, currency, effective_from,
                     created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :pid, :rid, :cost,
                        :currency, :eff_date, now(), now())
            """),
            {"tid": tid, "pid": pid, "rid": rid, "cost": cost, "currency": currency,
             "eff_date": date(2026, 1, 1)},
        )


# ── Price Lists + Items ──────────────────────────────────────────────


def _insert_price_list(conn, tid, plid, name, is_default, eff_from, region_id, status="published"):
    conn.execute(
        sa.text("""
            INSERT INTO price_lists
                (id, tenant_id, name, is_default, group_id,
                 version_major, version_minor, status, delivery_region_id,
                 created_at, updated_at)
            VALUES (:id, :tid, :name, :is_default, :id,
                    1, 0, :status, :rid, now(), now())
        """),
        {"id": plid, "tid": tid, "name": name, "is_default": is_default,
         "rid": region_id, "status": status},
    )


def _insert_price_item(conn, plid, offering_id=None, activity_id=None, region_id=None,
                        coverage=None, price=0, currency="EUR", markup=None):
    conn.execute(
        sa.text("""
            INSERT INTO price_list_items
                (id, price_list_id, service_offering_id, activity_definition_id,
                 delivery_region_id, coverage_model, price_per_unit, currency,
                 markup_percent, created_at, updated_at)
            VALUES (gen_random_uuid(), :plid, :oid, :aid, :rid, :cov,
                    :price, :currency, :markup, now(), now())
        """),
        {"plid": plid, "oid": offering_id, "aid": activity_id, "rid": region_id,
         "cov": coverage, "price": price, "currency": currency, "markup": markup},
    )


def _seed_price_lists(conn, tid, o, ad, regions):
    emea_rid = regions.get("EMEA-FRA")
    amer_rid = regions.get("AMER-NYC")

    # ══════════════════════════════════════════════════════════════════
    # Price List 1: Standard EMEA (default, EUR)
    # ══════════════════════════════════════════════════════════════════
    _insert_price_list(conn, tid, PL_STANDARD_EMEA, "Standard EMEA Price List",
                       True, date(2026, 1, 1), emea_rid)

    # Infrastructure (monthly per-unit)
    emea_infra = [
        ("Virtual Machine — Standard",       45.00),
        ("Virtual Machine — High Performance", 120.00),
        ("Managed PostgreSQL",                85.00),
        ("Managed MySQL",                     75.00),
        ("Object Storage",                     0.023),  # per GB
        ("Block Storage — SSD",                0.12),   # per GB
        ("Load Balancer",                     35.00),
        ("Kubernetes Cluster",               250.00),
        ("Virtual Network",                   15.00),
    ]
    for name, price in emea_infra:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_EMEA, offering_id=o[name],
                               price=price, currency="EUR", markup=20.0)

    # Security (monthly)
    emea_security = [
        ("Managed Firewall",         95.00, "24x7"),
        ("Endpoint Protection",       8.50, None),
        ("Vulnerability Scanning",   12.00, None),
        ("SSL Certificate Management", 5.00, None),
        ("SIEM / Log Monitoring",     0.85, "24x7"),  # per GB
    ]
    for name, price, cov in emea_security:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_EMEA, offering_id=o[name],
                               price=price, currency="EUR", coverage=cov, markup=25.0)

    # Managed Services (monthly)
    emea_managed = [
        ("24/7 Infrastructure Monitoring",  18.00, "24x7"),
        ("Backup & Disaster Recovery",      25.00, None),
        ("Patch Management",                12.00, "business_hours"),
        ("Incident Response — Business Hours", 35.00, "business_hours"),
        ("Incident Response — 24/7",        85.00, "24x7"),
    ]
    for name, price, cov in emea_managed:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_EMEA, offering_id=o[name],
                               price=price, currency="EUR", coverage=cov, markup=30.0)

    # End User Services (monthly per user)
    emea_enduser = [
        ("Managed Desktop",             45.00, "business_hours"),
        ("Email & Collaboration Suite",  15.00, None),
        ("VPN Access",                    8.00, None),
        ("Help Desk — Business Hours",  22.00, "business_hours"),
        ("Help Desk — Extended Hours",  38.00, "extended"),
    ]
    for name, price, cov in emea_enduser:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_EMEA, offering_id=o[name],
                               price=price, currency="EUR", coverage=cov, markup=25.0)

    # DevOps (monthly)
    emea_devops = [
        ("CI/CD Pipeline",                  65.00),
        ("Infrastructure as Code Management", 120.00),  # per hour
        ("Managed DNS",                       8.00),
    ]
    for name, price in emea_devops:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_EMEA, offering_id=o[name],
                               price=price, currency="EUR", markup=20.0)

    # Activity-based pricing (per estimated-hour activities → price per hour)
    emea_activities = [
        ("Gather requirements & sizing",   140.00),
        ("Provision compute resources",     85.00),
        ("Configure networking",           120.00),
        ("Apply security baseline",        120.00),
        ("Root cause analysis",            120.00),
        ("Implement fix / workaround",     120.00),
        ("Change scope documentation",      85.00),
        ("Impact & dependency analysis",   120.00),
        ("Risk assessment & mitigation",   175.00),
        ("Cluster provisioning",           120.00),
        ("Ingress & service mesh config",  220.00),
    ]
    for name, price in emea_activities:
        if name in ad:
            _insert_price_item(conn, PL_STANDARD_EMEA, activity_id=ad[name],
                               price=price, currency="EUR")

    # ══════════════════════════════════════════════════════════════════
    # Price List 2: Standard Americas (USD)
    # ══════════════════════════════════════════════════════════════════
    _insert_price_list(conn, tid, PL_STANDARD_AMER, "Standard Americas Price List",
                       False, date(2026, 1, 1), amer_rid)

    amer_infra = [
        ("Virtual Machine — Standard",        52.00),
        ("Virtual Machine — High Performance", 140.00),
        ("Managed PostgreSQL",                 98.00),
        ("Managed MySQL",                      88.00),
        ("Object Storage",                      0.026),
        ("Block Storage — SSD",                 0.14),
        ("Load Balancer",                      40.00),
        ("Kubernetes Cluster",                290.00),
        ("Virtual Network",                    18.00),
    ]
    for name, price in amer_infra:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_AMER, offering_id=o[name],
                               price=price, currency="USD", markup=22.0)

    amer_security = [
        ("Managed Firewall",         110.00, "24x7"),
        ("Endpoint Protection",       10.00, None),
        ("Vulnerability Scanning",    14.00, None),
        ("SSL Certificate Management",  6.00, None),
        ("SIEM / Log Monitoring",      1.00, "24x7"),
    ]
    for name, price, cov in amer_security:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_AMER, offering_id=o[name],
                               price=price, currency="USD", coverage=cov, markup=25.0)

    amer_managed = [
        ("24/7 Infrastructure Monitoring",  22.00, "24x7"),
        ("Backup & Disaster Recovery",      30.00, None),
        ("Patch Management",                14.00, "business_hours"),
        ("Incident Response — Business Hours", 42.00, "business_hours"),
        ("Incident Response — 24/7",       100.00, "24x7"),
    ]
    for name, price, cov in amer_managed:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_AMER, offering_id=o[name],
                               price=price, currency="USD", coverage=cov, markup=30.0)

    amer_enduser = [
        ("Managed Desktop",             52.00, "business_hours"),
        ("Email & Collaboration Suite",  18.00, None),
        ("VPN Access",                   10.00, None),
        ("Help Desk — Business Hours",  26.00, "business_hours"),
        ("Help Desk — Extended Hours",  45.00, "extended"),
    ]
    for name, price, cov in amer_enduser:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_AMER, offering_id=o[name],
                               price=price, currency="USD", coverage=cov, markup=25.0)

    amer_devops = [
        ("CI/CD Pipeline",                  75.00),
        ("Infrastructure as Code Management", 140.00),
        ("Managed DNS",                      10.00),
    ]
    for name, price in amer_devops:
        if name in o:
            _insert_price_item(conn, PL_STANDARD_AMER, offering_id=o[name],
                               price=price, currency="USD", markup=20.0)

    # ══════════════════════════════════════════════════════════════════
    # Price List 3: Premium 24/7 (global, higher prices, extended SLAs)
    # ══════════════════════════════════════════════════════════════════
    _insert_price_list(conn, tid, PL_PREMIUM, "Premium 24/7 Price List",
                       False, date(2026, 1, 1), None)

    premium_items = [
        ("Virtual Machine — Standard",        65.00, "24x7"),
        ("Virtual Machine — High Performance", 175.00, "24x7"),
        ("Managed PostgreSQL",                125.00, "24x7"),
        ("Managed MySQL",                     110.00, "24x7"),
        ("Kubernetes Cluster",                380.00, "24x7"),
        ("Load Balancer",                      55.00, "24x7"),
        ("Virtual Network",                    22.00, "24x7"),
        ("Managed Firewall",                  145.00, "24x7"),
        ("Endpoint Protection",                12.00, "24x7"),
        ("SIEM / Log Monitoring",               1.25, "24x7"),
        ("24/7 Infrastructure Monitoring",     28.00, "24x7"),
        ("Backup & Disaster Recovery",         40.00, "24x7"),
        ("Patch Management",                   20.00, "24x7"),
        ("Incident Response — 24/7",          120.00, "24x7"),
        ("Help Desk — Extended Hours",         55.00, "24x7"),
    ]
    for name, price, cov in premium_items:
        if name in o:
            _insert_price_item(conn, PL_PREMIUM, offering_id=o[name],
                               price=price, currency="EUR", coverage=cov, markup=35.0)


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if not row:
        return
    tid = str(row[0])

    # Price list items + price lists
    for plid in [PL_STANDARD_EMEA, PL_STANDARD_AMER, PL_PREMIUM]:
        conn.execute(sa.text("DELETE FROM price_list_items WHERE price_list_id = :id"), {"id": plid})
        conn.execute(sa.text("DELETE FROM price_lists WHERE id = :id"), {"id": plid})

    # Catalog items + catalogs
    for cid in [SC_ENTERPRISE, SC_SMB]:
        conn.execute(sa.text("DELETE FROM service_catalog_items WHERE catalog_id = :id"), {"id": cid})
        conn.execute(sa.text("DELETE FROM service_catalogs WHERE id = :id"), {"id": cid})

    # Group items + groups
    for gid in [SG_CORE_INFRA, SG_SECURITY_BUNDLE, SG_MANAGED_OPS, SG_END_USER, SG_DEVOPS]:
        conn.execute(sa.text("DELETE FROM service_group_items WHERE group_id = :id"), {"id": gid})
        conn.execute(sa.text("DELETE FROM service_groups WHERE id = :id"), {"id": gid})

    # Rate cards
    conn.execute(sa.text("DELETE FROM internal_rate_cards WHERE tenant_id = :tid"), {"tid": tid})

    # Process assignments + offerings (backfilled from 025)
    conn.execute(sa.text("DELETE FROM service_process_assignments WHERE tenant_id = :tid"), {"tid": tid})
    conn.execute(sa.text("DELETE FROM service_offerings WHERE tenant_id = :tid"), {"tid": tid})
