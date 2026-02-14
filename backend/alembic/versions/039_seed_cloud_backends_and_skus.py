"""Seed cloud backends (one per provider for the root tenant) and
provider SKUs with realistic catalog entries for Proxmox, AWS, Azure,
GCP, and OCI.

Revision ID: 039
Revises: 038
Create Date: 2026-02-13
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "039"
down_revision: Union[str, None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Pre-generated UUIDs for cloud backends ───────────────────────────

CB_PROXMOX = str(uuid.uuid4())
CB_AWS = str(uuid.uuid4())
CB_AZURE = str(uuid.uuid4())
CB_GCP = str(uuid.uuid4())
CB_OCI = str(uuid.uuid4())


def upgrade() -> None:
    conn = op.get_bind()

    # ── Resolve root tenant ──────────────────────────────────────────
    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if not row:
        return
    tid = str(row[0])

    # ── Resolve semantic providers by name ───────────────────────────
    providers = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM semantic_providers WHERE deleted_at IS NULL")
    ):
        providers[r[0]] = str(r[1])

    if len(providers) < 5:
        return

    # ── Resolve CI classes by name ───────────────────────────────────
    ci = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM ci_classes WHERE is_system = true AND deleted_at IS NULL")
    ):
        ci[r[0]] = str(r[1])

    # ── 1. Cloud Backends ────────────────────────────────────────────
    _seed_cloud_backends(conn, tid, providers)

    # ── 2. Provider SKUs ─────────────────────────────────────────────
    _seed_provider_skus(conn, providers, ci)


# ── Cloud Backends ───────────────────────────────────────────────────


def _insert_backend(conn, tid, cb_id, provider_id, name, desc, endpoint=None, status="active"):
    conn.execute(
        sa.text("""
            INSERT INTO cloud_backends
                (id, tenant_id, provider_id, name, description,
                 status, endpoint_url, is_shared,
                 credentials_schema_version, created_at, updated_at)
            VALUES (:id, :tid, :pid, :name, :desc,
                    :status, :endpoint, false,
                    1, now(), now())
        """),
        {"id": cb_id, "tid": tid, "pid": provider_id, "name": name,
         "desc": desc, "status": status, "endpoint": endpoint},
    )


def _seed_cloud_backends(conn, tid, p):
    _insert_backend(conn, tid, CB_PROXMOX, p["proxmox"],
                    "Proxmox Lab Cluster",
                    "On-premises Proxmox VE cluster for development and staging workloads",
                    endpoint="https://pve01.lab.internal:8006")
    _insert_backend(conn, tid, CB_AWS, p["aws"],
                    "AWS Production (eu-central-1)",
                    "Primary AWS account for European production workloads")
    _insert_backend(conn, tid, CB_AZURE, p["azure"],
                    "Azure Enterprise (West Europe)",
                    "Azure EA subscription for enterprise services and hybrid connectivity")
    _insert_backend(conn, tid, CB_GCP, p["gcp"],
                    "GCP Analytics (europe-west1)",
                    "GCP project for big data, ML pipelines, and analytics workloads")
    _insert_backend(conn, tid, CB_OCI, p["oci"],
                    "OCI Database (eu-frankfurt-1)",
                    "Oracle Cloud for Autonomous Database and Oracle workloads")


# ── Provider SKUs ────────────────────────────────────────────────────


def _insert_sku(conn, provider_id, sku_id, name, display_name, desc,
                ci_class_id, unit, category, cost, currency="EUR"):
    conn.execute(
        sa.text("""
            INSERT INTO provider_skus
                (id, provider_id, external_sku_id, name, display_name,
                 description, ci_class_id, measuring_unit, category,
                 unit_cost, cost_currency, is_active,
                 created_at, updated_at)
            VALUES (gen_random_uuid(), :pid, :sku_id, :name, :display,
                    :desc, :ci_class, :unit, :cat,
                    :cost, :currency, true,
                    now(), now())
        """),
        {"pid": provider_id, "sku_id": sku_id, "name": name,
         "display": display_name, "desc": desc,
         "ci_class": ci_class_id, "unit": unit, "cat": category,
         "cost": cost, "currency": currency},
    )


def _seed_provider_skus(conn, p, ci):
    # ══════════════════════════════════════════════════════════════════
    # Proxmox SKUs
    # ══════════════════════════════════════════════════════════════════
    px = p["proxmox"]
    _insert_sku(conn, px, "pve-vm-small", "PVE VM Small",
                "Proxmox VM \u2014 Small (2 vCPU / 4 GB)",
                "KVM virtual machine: 2 vCPU, 4 GB RAM, 40 GB local SSD",
                ci.get("VirtualMachine"), "instance", "Compute", 12.00)
    _insert_sku(conn, px, "pve-vm-medium", "PVE VM Medium",
                "Proxmox VM \u2014 Medium (4 vCPU / 8 GB)",
                "KVM virtual machine: 4 vCPU, 8 GB RAM, 80 GB local SSD",
                ci.get("VirtualMachine"), "instance", "Compute", 28.00)
    _insert_sku(conn, px, "pve-vm-large", "PVE VM Large",
                "Proxmox VM \u2014 Large (8 vCPU / 32 GB)",
                "KVM virtual machine: 8 vCPU, 32 GB RAM, 200 GB local SSD",
                ci.get("VirtualMachine"), "instance", "Compute", 65.00)
    _insert_sku(conn, px, "pve-lxc-small", "PVE Container Small",
                "Proxmox LXC \u2014 Small (1 vCPU / 1 GB)",
                "LXC container: 1 vCPU, 1 GB RAM, 20 GB storage",
                ci.get("Container"), "instance", "Compute", 5.00)
    _insert_sku(conn, px, "pve-lxc-medium", "PVE Container Medium",
                "Proxmox LXC \u2014 Medium (2 vCPU / 4 GB)",
                "LXC container: 2 vCPU, 4 GB RAM, 40 GB storage",
                ci.get("Container"), "instance", "Compute", 10.00)
    _insert_sku(conn, px, "pve-storage-local", "PVE Local Storage",
                "Proxmox Local SSD Storage (per GB)",
                "ZFS local SSD storage on Proxmox node",
                ci.get("BlockStorage"), "gb", "Storage", 0.05)
    _insert_sku(conn, px, "pve-storage-ceph", "PVE Ceph Storage",
                "Proxmox Ceph Distributed Storage (per GB)",
                "Ceph RBD distributed storage with 3x replication",
                ci.get("BlockStorage"), "gb", "Storage", 0.08)
    _insert_sku(conn, px, "pve-backup", "PVE Backup",
                "Proxmox Backup Server (per VM slot)",
                "Automated VM/CT backup with deduplication via PBS",
                ci.get("Backup"), "instance", "Backup", 3.00)
    _insert_sku(conn, px, "pve-vnet", "PVE SDN VNet",
                "Proxmox SDN Virtual Network",
                "Software-defined virtual network with VLAN/VXLAN isolation",
                ci.get("VirtualNetwork"), "instance", "Network", 0.00)
    _insert_sku(conn, px, "pve-firewall", "PVE Firewall",
                "Proxmox Built-in Firewall (per VM)",
                "Host-based firewall rules per VM/CT",
                ci.get("SecurityGroup"), "instance", "Security", 0.00)

    # ══════════════════════════════════════════════════════════════════
    # AWS SKUs
    # ══════════════════════════════════════════════════════════════════
    aw = p["aws"]
    _insert_sku(conn, aw, "ec2-t3.medium", "EC2 t3.medium",
                "EC2 t3.medium (2 vCPU / 4 GB)",
                "Burstable general-purpose instance: 2 vCPU, 4 GiB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 30.37, "USD")
    _insert_sku(conn, aw, "ec2-m6i.xlarge", "EC2 m6i.xlarge",
                "EC2 m6i.xlarge (4 vCPU / 16 GB)",
                "General-purpose instance: 4 vCPU, 16 GiB RAM, EBS-optimized",
                ci.get("VirtualMachine"), "instance", "Compute", 140.16, "USD")
    _insert_sku(conn, aw, "ec2-c6i.2xlarge", "EC2 c6i.2xlarge",
                "EC2 c6i.2xlarge (8 vCPU / 16 GB)",
                "Compute-optimized instance: 8 vCPU, 16 GiB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 248.20, "USD")
    _insert_sku(conn, aw, "rds-postgres-db.m6g.large", "RDS PostgreSQL db.m6g.large",
                "RDS PostgreSQL \u2014 db.m6g.large",
                "Managed PostgreSQL: 2 vCPU, 8 GiB RAM, Multi-AZ available",
                ci.get("RelationalDatabase"), "instance", "Database", 133.59, "USD")
    _insert_sku(conn, aw, "rds-mysql-db.m6g.large", "RDS MySQL db.m6g.large",
                "RDS MySQL \u2014 db.m6g.large",
                "Managed MySQL: 2 vCPU, 8 GiB RAM, Multi-AZ available",
                ci.get("RelationalDatabase"), "instance", "Database", 125.56, "USD")
    _insert_sku(conn, aw, "s3-standard", "S3 Standard",
                "S3 Standard Storage (per GB)",
                "S3 standard-class object storage, first 50 TB tier",
                ci.get("ObjectStorage"), "gb", "Storage", 0.023, "USD")
    _insert_sku(conn, aw, "ebs-gp3", "EBS gp3",
                "EBS gp3 Volume (per GB)",
                "General-purpose SSD volume: 3000 baseline IOPS, 125 MB/s throughput",
                ci.get("BlockStorage"), "gb", "Storage", 0.08, "USD")
    _insert_sku(conn, aw, "efs-standard", "EFS Standard",
                "EFS Standard Storage (per GB)",
                "Elastic File System, standard access tier",
                ci.get("FileStorage"), "gb", "Storage", 0.30, "USD")
    _insert_sku(conn, aw, "alb", "Application Load Balancer",
                "Application Load Balancer (ALB)",
                "Layer 7 load balancer: fixed hourly + LCU charges",
                ci.get("LoadBalancer"), "instance", "Network", 16.43, "USD")
    _insert_sku(conn, aw, "vpc", "VPC",
                "Amazon VPC",
                "Virtual Private Cloud with internet gateway",
                ci.get("VirtualNetwork"), "instance", "Network", 0.00, "USD")
    _insert_sku(conn, aw, "route53-zone", "Route 53 Hosted Zone",
                "Route 53 Hosted Zone",
                "Authoritative DNS hosted zone (per zone per month)",
                ci.get("DNS"), "instance", "Network", 0.50, "USD")
    _insert_sku(conn, aw, "eks-cluster", "EKS Cluster",
                "Amazon EKS Cluster",
                "Managed Kubernetes control plane (per cluster per hour)",
                None, "instance", "Compute", 73.00, "USD")
    _insert_sku(conn, aw, "lambda-requests", "Lambda Requests",
                "Lambda Invocations (per million)",
                "Serverless function invocations",
                ci.get("ServerlessFunction"), "request", "Compute", 0.20, "USD")
    _insert_sku(conn, aw, "acm-cert", "ACM Certificate",
                "ACM Public Certificate",
                "Free public SSL/TLS certificate via AWS Certificate Manager",
                ci.get("Certificate"), "instance", "Security", 0.00, "USD")

    # ══════════════════════════════════════════════════════════════════
    # Azure SKUs
    # ══════════════════════════════════════════════════════════════════
    az = p["azure"]
    _insert_sku(conn, az, "vm-b2s", "Azure VM B2s",
                "Azure VM B2s (2 vCPU / 4 GB)",
                "Burstable VM: 2 vCPU, 4 GiB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 30.37, "EUR")
    _insert_sku(conn, az, "vm-d4s-v5", "Azure VM D4s v5",
                "Azure VM D4s v5 (4 vCPU / 16 GB)",
                "General-purpose VM: 4 vCPU, 16 GiB RAM, temp SSD",
                ci.get("VirtualMachine"), "instance", "Compute", 140.16, "EUR")
    _insert_sku(conn, az, "vm-f8s-v2", "Azure VM F8s v2",
                "Azure VM F8s v2 (8 vCPU / 16 GB)",
                "Compute-optimized VM: 8 vCPU, 16 GiB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 248.20, "EUR")
    _insert_sku(conn, az, "psql-flexible-gp-2vc", "Azure PostgreSQL Flexible GP 2vC",
                "Azure DB for PostgreSQL \u2014 Flexible (GP, 2 vCores)",
                "Flexible Server: General Purpose, 2 vCores, burstable storage",
                ci.get("RelationalDatabase"), "instance", "Database", 117.53, "EUR")
    _insert_sku(conn, az, "mysql-flexible-gp-2vc", "Azure MySQL Flexible GP 2vC",
                "Azure DB for MySQL \u2014 Flexible (GP, 2 vCores)",
                "Flexible Server: General Purpose, 2 vCores",
                ci.get("RelationalDatabase"), "instance", "Database", 109.94, "EUR")
    _insert_sku(conn, az, "blob-hot-lrs", "Azure Blob Hot LRS",
                "Azure Blob Storage \u2014 Hot LRS (per GB)",
                "Blob storage, hot access tier, locally-redundant",
                ci.get("ObjectStorage"), "gb", "Storage", 0.0184, "EUR")
    _insert_sku(conn, az, "disk-p10", "Azure Managed Disk P10",
                "Azure Managed Disk P10 (128 GB SSD)",
                "Premium SSD managed disk: 128 GiB, 500 IOPS, 100 MB/s",
                ci.get("BlockStorage"), "instance", "Storage", 17.92, "EUR")
    _insert_sku(conn, az, "files-premium", "Azure Files Premium",
                "Azure Files Premium (per GB)",
                "Premium file share with SMB/NFS support",
                ci.get("FileStorage"), "gb", "Storage", 0.16, "EUR")
    _insert_sku(conn, az, "appgw-v2", "Azure Application Gateway v2",
                "Application Gateway v2",
                "Layer 7 load balancer with WAF capability",
                ci.get("LoadBalancer"), "instance", "Network", 179.58, "EUR")
    _insert_sku(conn, az, "vnet", "Azure VNet",
                "Azure Virtual Network",
                "Virtual network with subnets and NSG support",
                ci.get("VirtualNetwork"), "instance", "Network", 0.00, "EUR")
    _insert_sku(conn, az, "dns-zone", "Azure DNS Zone",
                "Azure DNS Public Zone",
                "Authoritative DNS hosting (per zone per month)",
                ci.get("DNS"), "instance", "Network", 0.50, "EUR")
    _insert_sku(conn, az, "aks-cluster", "AKS Cluster",
                "Azure Kubernetes Service",
                "Managed Kubernetes control plane (free tier, pay for nodes)",
                None, "instance", "Compute", 0.00, "EUR")
    _insert_sku(conn, az, "keyvault-standard", "Azure Key Vault Standard",
                "Azure Key Vault \u2014 Standard",
                "Secrets, keys, and certificates management",
                ci.get("KeyVault"), "instance", "Security", 0.03, "EUR")

    # ══════════════════════════════════════════════════════════════════
    # GCP SKUs
    # ══════════════════════════════════════════════════════════════════
    gc = p["gcp"]
    _insert_sku(conn, gc, "ce-e2-medium", "GCE e2-medium",
                "Compute Engine e2-medium (2 vCPU / 4 GB)",
                "Cost-optimized shared-core instance: 2 vCPU, 4 GB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 24.46, "USD")
    _insert_sku(conn, gc, "ce-n2-standard-4", "GCE n2-standard-4",
                "Compute Engine n2-standard-4 (4 vCPU / 16 GB)",
                "General-purpose instance: 4 vCPU, 16 GB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 139.78, "USD")
    _insert_sku(conn, gc, "ce-c2-standard-8", "GCE c2-standard-8",
                "Compute Engine c2-standard-8 (8 vCPU / 32 GB)",
                "Compute-optimized instance: 8 vCPU, 32 GB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 278.58, "USD")
    _insert_sku(conn, gc, "csql-postgres", "Cloud SQL PostgreSQL",
                "Cloud SQL for PostgreSQL (db-g1-small)",
                "Managed PostgreSQL: shared vCPU, 1.7 GB RAM",
                ci.get("RelationalDatabase"), "instance", "Database", 25.55, "USD")
    _insert_sku(conn, gc, "csql-mysql", "Cloud SQL MySQL",
                "Cloud SQL for MySQL (db-g1-small)",
                "Managed MySQL: shared vCPU, 1.7 GB RAM",
                ci.get("RelationalDatabase"), "instance", "Database", 25.55, "USD")
    _insert_sku(conn, gc, "gcs-standard", "GCS Standard",
                "Cloud Storage Standard (per GB)",
                "Multi-regional standard-class storage",
                ci.get("ObjectStorage"), "gb", "Storage", 0.026, "USD")
    _insert_sku(conn, gc, "pd-ssd", "Persistent Disk SSD",
                "SSD Persistent Disk (per GB)",
                "Zonal SSD persistent disk",
                ci.get("BlockStorage"), "gb", "Storage", 0.17, "USD")
    _insert_sku(conn, gc, "filestore-basic", "Filestore Basic",
                "Filestore Basic HDD (per GB)",
                "Managed NFS file share, basic tier",
                ci.get("FileStorage"), "gb", "Storage", 0.20, "USD")
    _insert_sku(conn, gc, "lb-global", "GCP Global LB",
                "Global External HTTP(S) Load Balancer",
                "Global L7 load balancer with SSL and CDN integration",
                ci.get("LoadBalancer"), "instance", "Network", 18.26, "USD")
    _insert_sku(conn, gc, "vpc-network", "GCP VPC",
                "Virtual Private Cloud Network",
                "VPC network with global subnets and firewall rules",
                ci.get("VirtualNetwork"), "instance", "Network", 0.00, "USD")
    _insert_sku(conn, gc, "cloud-dns-zone", "Cloud DNS Zone",
                "Cloud DNS Managed Zone",
                "Authoritative DNS hosting (per zone per month)",
                ci.get("DNS"), "instance", "Network", 0.20, "USD")
    _insert_sku(conn, gc, "gke-cluster", "GKE Cluster",
                "Google Kubernetes Engine",
                "Managed Kubernetes control plane (standard tier)",
                None, "instance", "Compute", 73.00, "USD")
    _insert_sku(conn, gc, "cloud-functions", "Cloud Functions",
                "Cloud Functions Invocations (per million)",
                "Serverless function invocations",
                ci.get("ServerlessFunction"), "request", "Compute", 0.40, "USD")

    # ══════════════════════════════════════════════════════════════════
    # OCI SKUs
    # ══════════════════════════════════════════════════════════════════
    oc = p["oci"]
    _insert_sku(conn, oc, "vm-standard-e4-flex-2", "OCI VM.Standard.E4.Flex 2 OCPU",
                "OCI VM.Standard.E4.Flex (2 OCPU / 32 GB)",
                "AMD flexible VM: 2 OCPU, 32 GB RAM (16 GB/OCPU)",
                ci.get("VirtualMachine"), "instance", "Compute", 44.64, "USD")
    _insert_sku(conn, oc, "vm-standard-e4-flex-4", "OCI VM.Standard.E4.Flex 4 OCPU",
                "OCI VM.Standard.E4.Flex (4 OCPU / 64 GB)",
                "AMD flexible VM: 4 OCPU, 64 GB RAM",
                ci.get("VirtualMachine"), "instance", "Compute", 89.28, "USD")
    _insert_sku(conn, oc, "bm-standard-e4-128", "OCI BM.Standard.E4.128",
                "OCI BM.Standard.E4.128 Bare Metal",
                "Bare metal: 128 OCPU, 2048 GB RAM, 2x NVMe",
                ci.get("BareMetalServer"), "instance", "Compute", 4714.56, "USD")
    _insert_sku(conn, oc, "adb-ecpu", "Autonomous Database eCPU",
                "Autonomous Database \u2014 per eCPU per hour",
                "Autonomous Transaction Processing or Data Warehouse",
                ci.get("RelationalDatabase"), "hour", "Database", 0.336, "USD")
    _insert_sku(conn, oc, "dbcs-vm-standard", "DBCS VM.Standard",
                "DB System VM.Standard (2 OCPU)",
                "Oracle Database Cloud Service VM: 2 OCPU, RAC optional",
                ci.get("RelationalDatabase"), "instance", "Database", 292.00, "USD")
    _insert_sku(conn, oc, "os-standard", "OCI Object Storage Standard",
                "Object Storage \u2014 Standard (per GB)",
                "Standard-tier object storage, first 10 TB free",
                ci.get("ObjectStorage"), "gb", "Storage", 0.0255, "USD")
    _insert_sku(conn, oc, "bv-perf-10", "OCI Block Volume Performance 10",
                "Block Volume \u2014 Balanced (per GB)",
                "Block volume with balanced performance (10 VPU/GB)",
                ci.get("BlockStorage"), "gb", "Storage", 0.025, "USD")
    _insert_sku(conn, oc, "fss", "OCI File Storage",
                "File Storage Service (per GB)",
                "Managed NFS file system with snapshots",
                ci.get("FileStorage"), "gb", "Storage", 0.30, "USD")
    _insert_sku(conn, oc, "lbaas-flex-100", "OCI LBaaS Flexible 100 Mbps",
                "Load Balancer \u2014 Flexible (100 Mbps)",
                "Flexible load balancer shape: 100 Mbps bandwidth",
                ci.get("LoadBalancer"), "instance", "Network", 29.20, "USD")
    _insert_sku(conn, oc, "vcn", "OCI VCN",
                "Virtual Cloud Network",
                "VCN with subnets, route tables, security lists",
                ci.get("VirtualNetwork"), "instance", "Network", 0.00, "USD")
    _insert_sku(conn, oc, "dns-zone", "OCI DNS Zone",
                "OCI DNS Zone",
                "Authoritative DNS zone (per zone per month)",
                ci.get("DNS"), "instance", "Network", 0.50, "USD")
    _insert_sku(conn, oc, "oke-cluster", "OKE Cluster",
                "Oracle Kubernetes Engine",
                "Managed Kubernetes control plane (always free for enhanced clusters)",
                None, "instance", "Compute", 0.00, "USD")
    _insert_sku(conn, oc, "vault-key", "OCI Vault Key",
                "Vault Key Management (per key version)",
                "HSM-backed key management service",
                ci.get("KeyVault"), "instance", "Security", 0.53, "USD")


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if not row:
        return
    tid = str(row[0])

    # Delete cloud backends (cascade won't affect SKUs since they're independent)
    for cb_id in [CB_PROXMOX, CB_AWS, CB_AZURE, CB_GCP, CB_OCI]:
        conn.execute(sa.text("DELETE FROM cloud_backends WHERE id = :id"), {"id": cb_id})

    # Delete all provider SKUs (there's no tenant_id, delete by provider)
    providers = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM semantic_providers WHERE deleted_at IS NULL")
    ):
        providers[r[0]] = str(r[1])

    for name in ["proxmox", "aws", "azure", "gcp", "oci"]:
        pid = providers.get(name)
        if pid:
            conn.execute(
                sa.text("DELETE FROM provider_skus WHERE provider_id = :pid"),
                {"pid": pid},
            )
