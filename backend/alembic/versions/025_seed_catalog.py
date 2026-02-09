"""Seed service catalog with IT service provider offerings, activity templates,
service processes, and process assignments. Populates the catalog for the root
tenant with a full automated MSP portfolio.

Revision ID: 025
Revises: 024
Create Date: 2026-02-09
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | None = None
depends_on: str | None = None

# ── Pre-generated UUIDs for cross-referencing ─────────────────────────

# Activity template IDs
AT_INFRA_PROVISION = str(uuid.uuid4())
AT_DB_SETUP = str(uuid.uuid4())
AT_MONITORING_ONBOARD = str(uuid.uuid4())
AT_BACKUP_CONFIG = str(uuid.uuid4())
AT_SECURITY_HARDEN = str(uuid.uuid4())
AT_NETWORK_CONFIG = str(uuid.uuid4())
AT_PATCH_MGMT = str(uuid.uuid4())
AT_INCIDENT_TRIAGE = str(uuid.uuid4())
AT_INCIDENT_RESOLVE = str(uuid.uuid4())
AT_CHANGE_ASSESS = str(uuid.uuid4())
AT_CHANGE_IMPL = str(uuid.uuid4())
AT_DECOMMISSION = str(uuid.uuid4())
AT_USER_ONBOARD = str(uuid.uuid4())
AT_SSL_CERT = str(uuid.uuid4())
AT_CAPACITY_REVIEW = str(uuid.uuid4())
AT_DR_TEST = str(uuid.uuid4())
AT_CONTAINER_DEPLOY = str(uuid.uuid4())
AT_COMPLIANCE_AUDIT = str(uuid.uuid4())
AT_FIREWALL_RULES = str(uuid.uuid4())
AT_VPN_SETUP = str(uuid.uuid4())

# Service process IDs
SP_STANDARD_PROV = str(uuid.uuid4())
SP_DB_PROV = str(uuid.uuid4())
SP_INCIDENT_MGMT = str(uuid.uuid4())
SP_CHANGE_MGMT = str(uuid.uuid4())
SP_DECOMMISSION = str(uuid.uuid4())
SP_USER_LIFECYCLE = str(uuid.uuid4())
SP_SECURITY_OPS = str(uuid.uuid4())
SP_CAPACITY_MGMT = str(uuid.uuid4())
SP_DR_MGMT = str(uuid.uuid4())
SP_CONTAINER_DELIVERY = str(uuid.uuid4())

# Service offering IDs
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


def upgrade() -> None:
    conn = op.get_bind()

    # Find root tenant (parent_id IS NULL)
    result = conn.execute(
        sa.text(
            "SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1"
        )
    )
    row = result.fetchone()
    if not row:
        return  # No tenants yet — skip seeding
    tenant_id = str(row[0])

    # Resolve staff profile IDs by name
    profiles = {}
    for r in conn.execute(
        sa.text(
            "SELECT name, id FROM staff_profiles WHERE is_system = true AND deleted_at IS NULL"
        )
    ):
        profiles[r[0]] = str(r[1])

    jr = profiles.get("junior_engineer")
    eng = profiles.get("engineer")
    sr = profiles.get("senior_engineer")
    con = profiles.get("consultant")
    sc = profiles.get("senior_consultant")
    arch = profiles.get("architect")

    if not all([jr, eng, sr, con, sc, arch]):
        return  # Staff profiles not seeded yet

    # ── 1. Activity Templates + Definitions ────────────────────────────

    _seed_activity_templates(conn, tenant_id, jr, eng, sr, con, sc, arch)

    # ── 2. Service Processes + Activity Links ──────────────────────────

    _seed_service_processes(conn, tenant_id)

    # ── 3. Service Offerings ───────────────────────────────────────────

    _seed_service_offerings(conn, tenant_id)

    # ── 4. Process Assignments ─────────────────────────────────────────

    _seed_process_assignments(conn, tenant_id)


def _insert_template(conn, tid, at_id, name, desc):
    conn.execute(
        sa.text("""
            INSERT INTO activity_templates (id, tenant_id, name, description, version, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, 1, now(), now())
        """),
        {"id": at_id, "tid": tid, "name": name, "desc": desc},
    )


def _insert_definition(conn, template_id, name, profile_id, hours, sort, optional=False):
    conn.execute(
        sa.text("""
            INSERT INTO activity_definitions (id, template_id, name, staff_profile_id, estimated_hours, sort_order, is_optional, created_at, updated_at)
            VALUES (gen_random_uuid(), :tmpl, :name, :profile, :hours, :sort, :opt, now(), now())
        """),
        {"tmpl": template_id, "name": name, "profile": profile_id, "hours": hours, "sort": sort, "opt": optional},
    )


def _seed_activity_templates(conn, tid, jr, eng, sr, con, sc, arch):
    # ── Infrastructure Provisioning ──
    _insert_template(conn, tid, AT_INFRA_PROVISION, "Infrastructure Provisioning",
                     "End-to-end provisioning of compute, storage, and network resources")
    _insert_definition(conn, AT_INFRA_PROVISION, "Gather requirements & sizing",        con, 2.0,  1)
    _insert_definition(conn, AT_INFRA_PROVISION, "Provision compute resources",          eng, 1.0,  2)
    _insert_definition(conn, AT_INFRA_PROVISION, "Configure storage",                   eng, 0.5,  3)
    _insert_definition(conn, AT_INFRA_PROVISION, "Configure networking",                sr,  1.0,  4)
    _insert_definition(conn, AT_INFRA_PROVISION, "Apply security baseline",             sr,  1.0,  5)
    _insert_definition(conn, AT_INFRA_PROVISION, "Smoke test & validation",             eng, 0.5,  6)
    _insert_definition(conn, AT_INFRA_PROVISION, "Handover documentation",              jr,  0.5,  7)

    # ── Database Setup ──
    _insert_template(conn, tid, AT_DB_SETUP, "Database Provisioning",
                     "Deploy and configure managed database instances with HA and backups")
    _insert_definition(conn, AT_DB_SETUP, "Capacity planning & sizing",                con,  1.5, 1)
    _insert_definition(conn, AT_DB_SETUP, "Instance provisioning",                     eng,  1.0, 2)
    _insert_definition(conn, AT_DB_SETUP, "Schema & user creation",                    eng,  0.5, 3)
    _insert_definition(conn, AT_DB_SETUP, "Configure replication / HA",                sr,   2.0, 4)
    _insert_definition(conn, AT_DB_SETUP, "Backup schedule & retention policy",        eng,  0.5, 5)
    _insert_definition(conn, AT_DB_SETUP, "Performance baseline tuning",               sr,   1.0, 6)
    _insert_definition(conn, AT_DB_SETUP, "Connection pool & driver validation",       eng,  0.5, 7)
    _insert_definition(conn, AT_DB_SETUP, "Documentation",                             jr,   0.5, 8)

    # ── Monitoring Onboarding ──
    _insert_template(conn, tid, AT_MONITORING_ONBOARD, "Monitoring Onboarding",
                     "Install agents, create dashboards, configure alerts and escalation paths")
    _insert_definition(conn, AT_MONITORING_ONBOARD, "Agent / exporter installation",   eng, 0.5,  1)
    _insert_definition(conn, AT_MONITORING_ONBOARD, "Dashboard creation",              eng, 1.0,  2)
    _insert_definition(conn, AT_MONITORING_ONBOARD, "Alert rule configuration",        sr,  1.0,  3)
    _insert_definition(conn, AT_MONITORING_ONBOARD, "Escalation path setup",           con, 0.5,  4)
    _insert_definition(conn, AT_MONITORING_ONBOARD, "Synthetic check validation",      eng, 0.5,  5)

    # ── Backup Configuration ──
    _insert_template(conn, tid, AT_BACKUP_CONFIG, "Backup Configuration",
                     "Define policies, configure agents, test recovery procedures")
    _insert_definition(conn, AT_BACKUP_CONFIG, "Define backup policy & RPO/RTO",       con, 1.0,  1)
    _insert_definition(conn, AT_BACKUP_CONFIG, "Agent / snapshot configuration",       eng, 1.0,  2)
    _insert_definition(conn, AT_BACKUP_CONFIG, "Schedule & retention setup",           eng, 0.5,  3)
    _insert_definition(conn, AT_BACKUP_CONFIG, "Recovery test execution",              sr,  1.5,  4)
    _insert_definition(conn, AT_BACKUP_CONFIG, "Document recovery runbook",            jr,  0.5,  5)

    # ── Security Hardening ──
    _insert_template(conn, tid, AT_SECURITY_HARDEN, "Security Hardening",
                     "Apply CIS benchmarks, configure access controls, validate compliance")
    _insert_definition(conn, AT_SECURITY_HARDEN, "Vulnerability scan",                eng,  0.5, 1)
    _insert_definition(conn, AT_SECURITY_HARDEN, "CIS benchmark application",         sr,   1.5, 2)
    _insert_definition(conn, AT_SECURITY_HARDEN, "Firewall / security group rules",   sr,   1.0, 3)
    _insert_definition(conn, AT_SECURITY_HARDEN, "Access control & key management",   sc,   1.0, 4)
    _insert_definition(conn, AT_SECURITY_HARDEN, "Encryption at rest & in transit",   sr,   0.5, 5)
    _insert_definition(conn, AT_SECURITY_HARDEN, "Compliance validation report",      con,  0.5, 6)

    # ── Network Configuration ──
    _insert_template(conn, tid, AT_NETWORK_CONFIG, "Network Configuration",
                     "Subnet, VLAN, routing, DNS, and firewall setup for new environments")
    _insert_definition(conn, AT_NETWORK_CONFIG, "IP plan & subnet allocation",        sr,   1.0, 1)
    _insert_definition(conn, AT_NETWORK_CONFIG, "VLAN / VPC provisioning",            eng,  0.5, 2)
    _insert_definition(conn, AT_NETWORK_CONFIG, "Routing & gateway configuration",    sr,   1.0, 3)
    _insert_definition(conn, AT_NETWORK_CONFIG, "DNS record creation",                eng,  0.25, 4)
    _insert_definition(conn, AT_NETWORK_CONFIG, "Firewall rule implementation",       sr,   0.5, 5)
    _insert_definition(conn, AT_NETWORK_CONFIG, "Connectivity validation",            eng,  0.5, 6)

    # ── Patch Management Setup ──
    _insert_template(conn, tid, AT_PATCH_MGMT, "Patch Management",
                     "Recurring OS and application patching with maintenance windows")
    _insert_definition(conn, AT_PATCH_MGMT, "Patch policy definition",                con,  0.5, 1)
    _insert_definition(conn, AT_PATCH_MGMT, "Maintenance window scheduling",          eng,  0.25, 2)
    _insert_definition(conn, AT_PATCH_MGMT, "Patch staging & testing",                eng,  1.0, 3)
    _insert_definition(conn, AT_PATCH_MGMT, "Production rollout",                     sr,   1.0, 4)
    _insert_definition(conn, AT_PATCH_MGMT, "Rollback plan validation",               sr,   0.5, 5)
    _insert_definition(conn, AT_PATCH_MGMT, "Post-patch health check",                eng,  0.5, 6)

    # ── Incident Triage ──
    _insert_template(conn, tid, AT_INCIDENT_TRIAGE, "Incident Triage",
                     "Initial assessment, classification, and communication for incidents")
    _insert_definition(conn, AT_INCIDENT_TRIAGE, "Initial assessment & severity",      eng, 0.25, 1)
    _insert_definition(conn, AT_INCIDENT_TRIAGE, "Impact analysis",                    sr,  0.5,  2)
    _insert_definition(conn, AT_INCIDENT_TRIAGE, "Stakeholder communication",          con, 0.25, 3)
    _insert_definition(conn, AT_INCIDENT_TRIAGE, "Escalation decision",                sr,  0.25, 4)
    _insert_definition(conn, AT_INCIDENT_TRIAGE, "Incident log documentation",         jr,  0.25, 5)

    # ── Incident Resolution ──
    _insert_template(conn, tid, AT_INCIDENT_RESOLVE, "Incident Resolution",
                     "Root cause analysis, fix, verification, and post-mortem")
    _insert_definition(conn, AT_INCIDENT_RESOLVE, "Root cause analysis",               sr,  2.0, 1)
    _insert_definition(conn, AT_INCIDENT_RESOLVE, "Implement fix / workaround",        sr,  1.5, 2)
    _insert_definition(conn, AT_INCIDENT_RESOLVE, "Service verification testing",      eng, 0.5, 3)
    _insert_definition(conn, AT_INCIDENT_RESOLVE, "Customer confirmation",             con, 0.25, 4)
    _insert_definition(conn, AT_INCIDENT_RESOLVE, "Post-mortem report",                sr,  1.0, 5, optional=True)

    # ── Change Assessment ──
    _insert_template(conn, tid, AT_CHANGE_ASSESS, "Change Assessment",
                     "Impact, risk, and rollback analysis for planned changes")
    _insert_definition(conn, AT_CHANGE_ASSESS, "Change scope documentation",          con, 0.5, 1)
    _insert_definition(conn, AT_CHANGE_ASSESS, "Impact & dependency analysis",        sr,  1.0, 2)
    _insert_definition(conn, AT_CHANGE_ASSESS, "Risk assessment & mitigation",        sc,  1.0, 3)
    _insert_definition(conn, AT_CHANGE_ASSESS, "Rollback plan preparation",           sr,  0.5, 4)
    _insert_definition(conn, AT_CHANGE_ASSESS, "CAB approval preparation",            con, 0.5, 5)

    # ── Change Implementation ──
    _insert_template(conn, tid, AT_CHANGE_IMPL, "Change Implementation",
                     "Execute, test, and validate planned changes")
    _insert_definition(conn, AT_CHANGE_IMPL, "Pre-change snapshot / backup",          eng, 0.5, 1)
    _insert_definition(conn, AT_CHANGE_IMPL, "Execute change steps",                  sr,  2.0, 2)
    _insert_definition(conn, AT_CHANGE_IMPL, "Post-change testing",                   eng, 1.0, 3)
    _insert_definition(conn, AT_CHANGE_IMPL, "Service health verification",           eng, 0.5, 4)
    _insert_definition(conn, AT_CHANGE_IMPL, "Update CMDB & documentation",           jr,  0.5, 5)

    # ── Service Decommission ──
    _insert_template(conn, tid, AT_DECOMMISSION, "Service Decommission",
                     "Safely remove services with data protection and cleanup")
    _insert_definition(conn, AT_DECOMMISSION, "Final data export / backup",           eng, 1.0, 1)
    _insert_definition(conn, AT_DECOMMISSION, "Dependency impact check",              sr,  0.5, 2)
    _insert_definition(conn, AT_DECOMMISSION, "Resource removal",                     eng, 0.5, 3)
    _insert_definition(conn, AT_DECOMMISSION, "DNS & networking cleanup",             eng, 0.25, 4)
    _insert_definition(conn, AT_DECOMMISSION, "License deallocation",                 jr,  0.25, 5)
    _insert_definition(conn, AT_DECOMMISSION, "CMDB update & closure report",         jr,  0.5, 6)

    # ── User Onboarding ──
    _insert_template(conn, tid, AT_USER_ONBOARD, "User Onboarding",
                     "Provision accounts, devices, email, and access for new users")
    _insert_definition(conn, AT_USER_ONBOARD, "Identity & account creation",          jr,  0.25, 1)
    _insert_definition(conn, AT_USER_ONBOARD, "Device provisioning & imaging",        eng, 1.0,  2)
    _insert_definition(conn, AT_USER_ONBOARD, "Email & collaboration setup",          jr,  0.25, 3)
    _insert_definition(conn, AT_USER_ONBOARD, "Access & permission provisioning",     eng, 0.5,  4)
    _insert_definition(conn, AT_USER_ONBOARD, "Security awareness briefing",          con, 0.5,  5, optional=True)
    _insert_definition(conn, AT_USER_ONBOARD, "Welcome kit & handover",               jr,  0.25, 6)

    # ── SSL / Certificate Management ──
    _insert_template(conn, tid, AT_SSL_CERT, "SSL / Certificate Management",
                     "Provision, install, monitor, and renew TLS certificates")
    _insert_definition(conn, AT_SSL_CERT, "CSR generation & validation",              eng, 0.25, 1)
    _insert_definition(conn, AT_SSL_CERT, "Certificate provisioning (CA / ACME)",     eng, 0.25, 2)
    _insert_definition(conn, AT_SSL_CERT, "Certificate installation & binding",       sr,  0.5,  3)
    _insert_definition(conn, AT_SSL_CERT, "Expiry monitoring setup",                  eng, 0.25, 4)
    _insert_definition(conn, AT_SSL_CERT, "Auto-renewal configuration",               sr,  0.5,  5, optional=True)

    # ── Capacity Review ──
    _insert_template(conn, tid, AT_CAPACITY_REVIEW, "Capacity Review",
                     "Analyse utilisation trends and recommend scaling actions")
    _insert_definition(conn, AT_CAPACITY_REVIEW, "Utilisation data collection",       eng, 0.5, 1)
    _insert_definition(conn, AT_CAPACITY_REVIEW, "Trend analysis & forecasting",      sc,  1.5, 2)
    _insert_definition(conn, AT_CAPACITY_REVIEW, "Scaling recommendation",            sc,  1.0, 3)
    _insert_definition(conn, AT_CAPACITY_REVIEW, "Execute resize / scale action",     sr,  1.0, 4)
    _insert_definition(conn, AT_CAPACITY_REVIEW, "Post-scaling validation",           eng, 0.5, 5)

    # ── Disaster Recovery Test ──
    _insert_template(conn, tid, AT_DR_TEST, "Disaster Recovery Test",
                     "Planned failover and failback exercises with validation")
    _insert_definition(conn, AT_DR_TEST, "DR test plan & scheduling",                 sc,  1.0, 1)
    _insert_definition(conn, AT_DR_TEST, "Failover execution",                        sr,  2.0, 2)
    _insert_definition(conn, AT_DR_TEST, "Service validation in DR site",             sr,  1.0, 3)
    _insert_definition(conn, AT_DR_TEST, "Failback execution",                        sr,  1.5, 4)
    _insert_definition(conn, AT_DR_TEST, "DR test report & gap analysis",             con, 1.0, 5)

    # ── Container Deployment ──
    _insert_template(conn, tid, AT_CONTAINER_DEPLOY, "Container Platform Deployment",
                     "Provision Kubernetes clusters with networking, RBAC, and observability")
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Cluster provisioning",             sr,   1.5, 1)
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Namespace & RBAC setup",           sr,   1.0, 2)
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Ingress & service mesh config",    arch, 2.0, 3)
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Registry & image policy",          sr,   0.5, 4)
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Logging & metrics pipeline",       sr,   1.0, 5)
    _insert_definition(conn, AT_CONTAINER_DEPLOY, "Smoke test & documentation",       eng,  0.5, 6)

    # ── Compliance Audit ──
    _insert_template(conn, tid, AT_COMPLIANCE_AUDIT, "Compliance Audit",
                     "Scope, collect evidence, analyse gaps, and produce audit reports")
    _insert_definition(conn, AT_COMPLIANCE_AUDIT, "Audit scope definition",           sc,  1.0, 1)
    _insert_definition(conn, AT_COMPLIANCE_AUDIT, "Evidence collection",              con, 2.0, 2)
    _insert_definition(conn, AT_COMPLIANCE_AUDIT, "Gap analysis",                     sc,  2.0, 3)
    _insert_definition(conn, AT_COMPLIANCE_AUDIT, "Remediation plan",                 sc,  1.5, 4)
    _insert_definition(conn, AT_COMPLIANCE_AUDIT, "Audit report generation",          con, 1.0, 5)

    # ── Firewall Rule Management ──
    _insert_template(conn, tid, AT_FIREWALL_RULES, "Firewall Rule Management",
                     "Design, implement, test, and document firewall policies")
    _insert_definition(conn, AT_FIREWALL_RULES, "Requirement & traffic analysis",     sr,  0.5, 1)
    _insert_definition(conn, AT_FIREWALL_RULES, "Rule design & peer review",          sr,  0.5, 2)
    _insert_definition(conn, AT_FIREWALL_RULES, "Rule implementation",                eng, 0.5, 3)
    _insert_definition(conn, AT_FIREWALL_RULES, "Connectivity testing",               eng, 0.5, 4)
    _insert_definition(conn, AT_FIREWALL_RULES, "Rule documentation & audit trail",   jr,  0.25, 5)

    # ── VPN Setup ──
    _insert_template(conn, tid, AT_VPN_SETUP, "VPN Configuration",
                     "Site-to-site or client VPN tunnel provisioning and testing")
    _insert_definition(conn, AT_VPN_SETUP, "Tunnel design & parameters",              sr,  0.5, 1)
    _insert_definition(conn, AT_VPN_SETUP, "Authentication & certificate setup",      sr,  0.5, 2)
    _insert_definition(conn, AT_VPN_SETUP, "Tunnel implementation",                   eng, 0.5, 3)
    _insert_definition(conn, AT_VPN_SETUP, "Routing & split tunnel config",           sr,  0.5, 4)
    _insert_definition(conn, AT_VPN_SETUP, "End-to-end testing",                      eng, 0.5, 5)
    _insert_definition(conn, AT_VPN_SETUP, "Client deployment guide",                 jr,  0.5, 6)


def _insert_process(conn, tid, sp_id, name, desc, sort):
    conn.execute(
        sa.text("""
            INSERT INTO service_processes (id, tenant_id, name, description, version, sort_order, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, 1, :sort, now(), now())
        """),
        {"id": sp_id, "tid": tid, "name": name, "desc": desc, "sort": sort},
    )


def _link_activity(conn, process_id, template_id, sort, required=True):
    conn.execute(
        sa.text("""
            INSERT INTO process_activity_links (id, process_id, activity_template_id, sort_order, is_required, created_at, updated_at)
            VALUES (gen_random_uuid(), :pid, :atid, :sort, :req, now(), now())
        """),
        {"pid": process_id, "atid": template_id, "sort": sort, "req": required},
    )


def _seed_service_processes(conn, tid):
    # ── Standard Provisioning ──
    _insert_process(conn, tid, SP_STANDARD_PROV, "Standard Provisioning",
                    "Full lifecycle for provisioning infrastructure resources including networking, security, monitoring, and backup", 1)
    _link_activity(conn, SP_STANDARD_PROV, AT_INFRA_PROVISION,     1)
    _link_activity(conn, SP_STANDARD_PROV, AT_NETWORK_CONFIG,      2)
    _link_activity(conn, SP_STANDARD_PROV, AT_SECURITY_HARDEN,     3)
    _link_activity(conn, SP_STANDARD_PROV, AT_MONITORING_ONBOARD,  4)
    _link_activity(conn, SP_STANDARD_PROV, AT_BACKUP_CONFIG,       5)

    # ── Database Provisioning ──
    _insert_process(conn, tid, SP_DB_PROV, "Database Provisioning",
                    "Deploy managed database with HA, security hardening, monitoring, and backup", 2)
    _link_activity(conn, SP_DB_PROV, AT_DB_SETUP,           1)
    _link_activity(conn, SP_DB_PROV, AT_SECURITY_HARDEN,    2)
    _link_activity(conn, SP_DB_PROV, AT_MONITORING_ONBOARD, 3)
    _link_activity(conn, SP_DB_PROV, AT_BACKUP_CONFIG,      4)

    # ── Incident Management ──
    _insert_process(conn, tid, SP_INCIDENT_MGMT, "Incident Management",
                    "ITIL-aligned incident lifecycle from triage through resolution and post-mortem", 3)
    _link_activity(conn, SP_INCIDENT_MGMT, AT_INCIDENT_TRIAGE,   1)
    _link_activity(conn, SP_INCIDENT_MGMT, AT_INCIDENT_RESOLVE,  2)

    # ── Change Management ──
    _insert_process(conn, tid, SP_CHANGE_MGMT, "Change Management",
                    "Structured change lifecycle with impact assessment, approval, implementation, and validation", 4)
    _link_activity(conn, SP_CHANGE_MGMT, AT_CHANGE_ASSESS, 1)
    _link_activity(conn, SP_CHANGE_MGMT, AT_CHANGE_IMPL,   2)

    # ── Service Decommission ──
    _insert_process(conn, tid, SP_DECOMMISSION, "Service Decommission",
                    "Controlled decommission with data protection, dependency checks, and cleanup", 5)
    _link_activity(conn, SP_DECOMMISSION, AT_DECOMMISSION, 1)

    # ── User Lifecycle Management ──
    _insert_process(conn, tid, SP_USER_LIFECYCLE, "User Lifecycle Management",
                    "Onboarding, provisioning, and access management for end users", 6)
    _link_activity(conn, SP_USER_LIFECYCLE, AT_USER_ONBOARD, 1)

    # ── Security Operations ──
    _insert_process(conn, tid, SP_SECURITY_OPS, "Security Operations",
                    "Ongoing security hardening, certificate management, firewall governance, and compliance", 7)
    _link_activity(conn, SP_SECURITY_OPS, AT_SECURITY_HARDEN,   1)
    _link_activity(conn, SP_SECURITY_OPS, AT_SSL_CERT,           2)
    _link_activity(conn, SP_SECURITY_OPS, AT_FIREWALL_RULES,     3)
    _link_activity(conn, SP_SECURITY_OPS, AT_COMPLIANCE_AUDIT,   4, required=False)

    # ── Capacity Management ──
    _insert_process(conn, tid, SP_CAPACITY_MGMT, "Capacity Management",
                    "Periodic capacity review, trend forecasting, and right-sizing", 8)
    _link_activity(conn, SP_CAPACITY_MGMT, AT_CAPACITY_REVIEW, 1)

    # ── Disaster Recovery Management ──
    _insert_process(conn, tid, SP_DR_MGMT, "Disaster Recovery Management",
                    "Backup validation, planned DR tests, and recovery runbook maintenance", 9)
    _link_activity(conn, SP_DR_MGMT, AT_BACKUP_CONFIG, 1)
    _link_activity(conn, SP_DR_MGMT, AT_DR_TEST,       2)

    # ── Container Service Delivery ──
    _insert_process(conn, tid, SP_CONTAINER_DELIVERY, "Container Service Delivery",
                    "Kubernetes cluster provisioning with security, monitoring, and networking", 10)
    _link_activity(conn, SP_CONTAINER_DELIVERY, AT_CONTAINER_DEPLOY,    1)
    _link_activity(conn, SP_CONTAINER_DELIVERY, AT_SECURITY_HARDEN,     2)
    _link_activity(conn, SP_CONTAINER_DELIVERY, AT_MONITORING_ONBOARD,  3)


def _insert_offering(conn, tid, so_id, name, desc, category, unit, stype, op_model=None, coverage=None):
    conn.execute(
        sa.text("""
            INSERT INTO service_offerings (id, tenant_id, name, description, category, measuring_unit, service_type, operating_model, default_coverage_model, is_active, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :cat, :unit, :stype, :opm, :cov, true, now(), now())
        """),
        {"id": so_id, "tid": tid, "name": name, "desc": desc, "cat": category,
         "unit": unit, "stype": stype, "opm": op_model, "cov": coverage},
    )


def _seed_service_offerings(conn, tid):
    # ── Infrastructure ──
    _insert_offering(conn, tid, SO_VM_STANDARD,
                     "Virtual Machine — Standard", "General-purpose VM with shared CPU and SSD storage",
                     "Infrastructure", "instance", "resource", "regional")
    _insert_offering(conn, tid, SO_VM_HIGHPERF,
                     "Virtual Machine — High Performance", "Dedicated-CPU VM for compute-intensive workloads",
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
                     "Block Storage — SSD", "High-performance SSD block volumes for VMs",
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

    # ── Security ──
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

    # ── Managed Services ──
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
                     "Incident Response — Business Hours", "ITIL incident management during business hours",
                     "Managed Services", "instance", "labor", "regional", "business_hours")
    _insert_offering(conn, tid, SO_INCIDENT_247,
                     "Incident Response — 24/7", "ITIL incident management with 24/7 coverage and SLA",
                     "Managed Services", "instance", "labor", "follow_the_sun", "24x7")

    # ── End User Services ──
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
                     "Help Desk — Business Hours", "L1/L2 end-user support during business hours",
                     "End User Services", "user", "labor", "regional", "business_hours")
    _insert_offering(conn, tid, SO_HELPDESK_EXT,
                     "Help Desk — Extended Hours", "L1/L2 end-user support with extended coverage",
                     "End User Services", "user", "labor", "regional", "extended")

    # ── DevOps & Automation ──
    _insert_offering(conn, tid, SO_CICD,
                     "CI/CD Pipeline", "Managed build, test, and deployment pipeline per application",
                     "DevOps & Automation", "instance", "resource", "global")
    _insert_offering(conn, tid, SO_IAC_MGMT,
                     "Infrastructure as Code Management", "Pulumi/Terraform IaC authoring, review, and execution",
                     "DevOps & Automation", "hour", "labor", "global")
    _insert_offering(conn, tid, SO_MANAGED_DNS,
                     "Managed DNS", "Authoritative DNS hosting with DNSSEC and geo-routing",
                     "DevOps & Automation", "instance", "resource", "global")


def _assign_process(conn, tid, so_id, sp_id, coverage=None, is_default=False):
    conn.execute(
        sa.text("""
            INSERT INTO service_process_assignments (id, tenant_id, service_offering_id, process_id, coverage_model, is_default, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :soid, :spid, :cov, :dflt, now(), now())
        """),
        {"tid": tid, "soid": so_id, "spid": sp_id, "cov": coverage, "dflt": is_default},
    )


def _seed_process_assignments(conn, tid):
    # ── Infrastructure offerings → processes ──
    for so in [SO_VM_STANDARD, SO_VM_HIGHPERF]:
        _assign_process(conn, tid, so, SP_STANDARD_PROV,    is_default=True)
        _assign_process(conn, tid, so, SP_INCIDENT_MGMT)
        _assign_process(conn, tid, so, SP_CHANGE_MGMT)
        _assign_process(conn, tid, so, SP_DECOMMISSION)
        _assign_process(conn, tid, so, SP_CAPACITY_MGMT)
        _assign_process(conn, tid, so, SP_DR_MGMT)

    for so in [SO_DB_POSTGRES, SO_DB_MYSQL]:
        _assign_process(conn, tid, so, SP_DB_PROV,          is_default=True)
        _assign_process(conn, tid, so, SP_INCIDENT_MGMT)
        _assign_process(conn, tid, so, SP_CHANGE_MGMT)
        _assign_process(conn, tid, so, SP_DECOMMISSION)
        _assign_process(conn, tid, so, SP_CAPACITY_MGMT)
        _assign_process(conn, tid, so, SP_DR_MGMT)

    for so in [SO_OBJ_STORAGE, SO_BLOCK_STORAGE]:
        _assign_process(conn, tid, so, SP_STANDARD_PROV,    is_default=True)
        _assign_process(conn, tid, so, SP_INCIDENT_MGMT)
        _assign_process(conn, tid, so, SP_CHANGE_MGMT)
        _assign_process(conn, tid, so, SP_DECOMMISSION)
        _assign_process(conn, tid, so, SP_CAPACITY_MGMT)

    _assign_process(conn, tid, SO_LOAD_BALANCER, SP_STANDARD_PROV,  is_default=True)
    _assign_process(conn, tid, SO_LOAD_BALANCER, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_LOAD_BALANCER, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_LOAD_BALANCER, SP_DECOMMISSION)

    _assign_process(conn, tid, SO_K8S_CLUSTER, SP_CONTAINER_DELIVERY, is_default=True)
    _assign_process(conn, tid, SO_K8S_CLUSTER, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_K8S_CLUSTER, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_K8S_CLUSTER, SP_DECOMMISSION)
    _assign_process(conn, tid, SO_K8S_CLUSTER, SP_CAPACITY_MGMT)

    _assign_process(conn, tid, SO_VIRTUAL_NETWORK, SP_STANDARD_PROV, is_default=True)
    _assign_process(conn, tid, SO_VIRTUAL_NETWORK, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_VIRTUAL_NETWORK, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_VIRTUAL_NETWORK, SP_DECOMMISSION)

    # ── Security offerings → processes ──
    _assign_process(conn, tid, SO_MANAGED_FIREWALL, SP_SECURITY_OPS, is_default=True)
    _assign_process(conn, tid, SO_MANAGED_FIREWALL, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_MANAGED_FIREWALL, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_MANAGED_FIREWALL, SP_DECOMMISSION)

    _assign_process(conn, tid, SO_ENDPOINT_PROT, SP_SECURITY_OPS, is_default=True)
    _assign_process(conn, tid, SO_ENDPOINT_PROT, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_ENDPOINT_PROT, SP_CHANGE_MGMT)

    _assign_process(conn, tid, SO_VULN_SCAN, SP_SECURITY_OPS, is_default=True)
    _assign_process(conn, tid, SO_VULN_SCAN, SP_INCIDENT_MGMT)

    _assign_process(conn, tid, SO_SSL_MGMT, SP_SECURITY_OPS, is_default=True)
    _assign_process(conn, tid, SO_SSL_MGMT, SP_INCIDENT_MGMT)

    _assign_process(conn, tid, SO_SIEM, SP_SECURITY_OPS, is_default=True)
    _assign_process(conn, tid, SO_SIEM, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_SIEM, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_SIEM, SP_CAPACITY_MGMT)

    # ── Managed Services → processes ──
    _assign_process(conn, tid, SO_MONITORING, SP_STANDARD_PROV, is_default=True)
    _assign_process(conn, tid, SO_MONITORING, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_MONITORING, SP_CHANGE_MGMT)

    _assign_process(conn, tid, SO_BACKUP_DR, SP_DR_MGMT,       is_default=True)
    _assign_process(conn, tid, SO_BACKUP_DR, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_BACKUP_DR, SP_CHANGE_MGMT)

    _assign_process(conn, tid, SO_PATCH_MGMT, SP_CHANGE_MGMT,  is_default=True)
    _assign_process(conn, tid, SO_PATCH_MGMT, SP_INCIDENT_MGMT)

    for so in [SO_INCIDENT_BH, SO_INCIDENT_247]:
        _assign_process(conn, tid, so, SP_INCIDENT_MGMT, is_default=True)
        _assign_process(conn, tid, so, SP_CHANGE_MGMT)

    # ── End User Services → processes ──
    _assign_process(conn, tid, SO_MANAGED_DESKTOP, SP_USER_LIFECYCLE, is_default=True)
    _assign_process(conn, tid, SO_MANAGED_DESKTOP, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_MANAGED_DESKTOP, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_MANAGED_DESKTOP, SP_DECOMMISSION)

    _assign_process(conn, tid, SO_EMAIL_COLLAB, SP_USER_LIFECYCLE, is_default=True)
    _assign_process(conn, tid, SO_EMAIL_COLLAB, SP_INCIDENT_MGMT)

    _assign_process(conn, tid, SO_VPN_ACCESS, SP_USER_LIFECYCLE, is_default=True)
    _assign_process(conn, tid, SO_VPN_ACCESS, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_VPN_ACCESS, SP_CHANGE_MGMT)

    for so in [SO_HELPDESK_BH, SO_HELPDESK_EXT]:
        _assign_process(conn, tid, so, SP_INCIDENT_MGMT, is_default=True)

    # ── DevOps & Automation → processes ──
    _assign_process(conn, tid, SO_CICD, SP_STANDARD_PROV,   is_default=True)
    _assign_process(conn, tid, SO_CICD, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_CICD, SP_CHANGE_MGMT)
    _assign_process(conn, tid, SO_CICD, SP_DECOMMISSION)

    _assign_process(conn, tid, SO_IAC_MGMT, SP_CHANGE_MGMT, is_default=True)
    _assign_process(conn, tid, SO_IAC_MGMT, SP_INCIDENT_MGMT)

    _assign_process(conn, tid, SO_MANAGED_DNS, SP_STANDARD_PROV, is_default=True)
    _assign_process(conn, tid, SO_MANAGED_DNS, SP_INCIDENT_MGMT)
    _assign_process(conn, tid, SO_MANAGED_DNS, SP_CHANGE_MGMT)


def downgrade() -> None:
    conn = op.get_bind()

    # Find root tenant
    result = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        return
    tenant_id = str(row[0])

    # Delete in reverse dependency order
    conn.execute(sa.text("DELETE FROM service_process_assignments WHERE tenant_id = :tid"), {"tid": tenant_id})
    conn.execute(sa.text("DELETE FROM process_activity_links WHERE process_id IN (SELECT id FROM service_processes WHERE tenant_id = :tid)"), {"tid": tenant_id})
    conn.execute(sa.text("DELETE FROM service_processes WHERE tenant_id = :tid"), {"tid": tenant_id})
    conn.execute(sa.text("DELETE FROM activity_definitions WHERE template_id IN (SELECT id FROM activity_templates WHERE tenant_id = :tid)"), {"tid": tenant_id})
    conn.execute(sa.text("DELETE FROM activity_templates WHERE tenant_id = :tid"), {"tid": tenant_id})
    conn.execute(sa.text("DELETE FROM service_offerings WHERE tenant_id = :tid"), {"tid": tenant_id})
